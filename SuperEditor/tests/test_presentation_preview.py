"""Actual preset switches, preview cache identity and independent pixel oracle.

Uses the packaged C25/C27 and normal public commands. CPU transport and ROM
font seams are the existing documented fixture; native evidence is separate.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, shutil
import test_geos_preview_editor as preview
from geos_preview_model import FontCatalog, render, with_chrome

geos=preview.geos
ROOT=geos.ROOT
DATA=geos.native_text('# **Heading**\rProse *italic* and @@fixed@@.\r'
 ':::basic\r10 PRINT "Hello":REM comment\r20 DATA 12,34\r:::\r'
 ':::asm\rloop: lda #$2A ; comment\r .byte "text",$FF\r:::\rTail.')


def run(out, previous=None):
 frozen,identity=geos.freeze(out,previous)
 for name,source in [('genuine',ROOT/'build/geos-font-catalog'),
                     ('build/editor-settings',ROOT/'build/editor-settings')]:
  if not (frozen/name).exists():shutil.copytree(source,frozen/name)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);f=preview.Fixture(out,frozen,dll,True)
 fonts=FontCatalog(frozen/'genuine/catalog.json',native=(frozen/'fonts/native8.bin').read_bytes())
 cases=[]
 try:
  f.source(DATA);f.command(99);f.render()
  canonical=f.canonical();session=f.read(f.s['se_editor_settings'],64)
  hashes={}
  # Repeated visits must not admit the old palette through a preview-body hit.
  for serial,(name,cap) in enumerate([('full',3),('markdown',1),('plain',0),
                                     ('full',3),('plain',0),('markdown',1)]):
   f.typed(geos.native_text('syntax '+name));f.command(102);f.render()
   assert f.get('se_render_caps',1)==cap
   assert f.get('se_r_presentation',1)==1 and f.get('se_e_ui',1)==4
   assert f.canonical()==canonical and f.merged()==DATA
   assert f.read(f.s['se_editor_settings'],64)==session
   expected=render(DATA,session,catalog=fonts,top=f.get('se_v_top'),code_coloring=bool(cap&2))
   matrix,colors,popup=geos.grid.logical_ui(f,DATA);assert popup is None
   bits,attrs=with_chrome(expected.bitmap,expected.attrs,matrix,colors,fonts.native)
   assert f.read(0x6000,8000)==bits,(name,'bitmap')
   assert f.read(0x4000,1000)==attrs,(name,'attributes')
   cache,_=f.raw_cache()
   assert cache[0xEA88:0xEA8B]==b'PV\1' and cache[0xEA8B]==cap
   assert cache[0xEA8D]==1,(name,'valid-last-preview-body')
   assert f.read(0xC600,1024)==f.shim
   digest=hashlib.sha256(bits+attrs).hexdigest()
   if cap in hashes:assert digest==hashes[cap],(name,'repeat-visit')
   hashes[cap]=digest
   # A warm repeat may reuse pixels but must preserve the same actual output.
   f.render();assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
   geos.png(bits,attrs,out/(str(serial)+'-'+name+'.png'))
   cases.append(dict(preset=name,capabilities=cap,bitmap_attributes_sha256=digest))
   print('PASS',cases[-1],flush=True)
  assert hashes[0]==hashes[1] and hashes[3]!=hashes[1], 'lexical on/off positive control'
  result=dict(status='passed',identity=identity,cases=cases,
   scope='Actual public presets and formatted preview; exact 8000 bitmap/1000 attribute bytes against independent canonical/font oracle; warm cache + cross-preset revisits; no native/physical-key claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);a=p.parse_args()
 out=ROOT/'build/presentation-preview'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
 out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)
