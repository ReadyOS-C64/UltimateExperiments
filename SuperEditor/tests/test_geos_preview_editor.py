"""Public 6510 preview raster integration against canonical/raw-font oracle.

SEO imports and cold font IEC are explicit CPU transport seams; native tests
exercise those ROM paths. Appearance fixture bytes are validated host inputs,
not emitted product layout. Separate frontend gate proves actual settings keys.
"""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace
import argparse,ctypes as C,hashlib,json,shutil,sys,zipfile
import test_geos_editor as geos
from geos_preview_model import render,FontCatalog,with_chrome
import editor_settings as settings
ROOT=geos.ROOT

DIVERSE=geos.native_text('# **Title**\rPlain **bold** *italic* ***both*** @@code@@.\r'
 '- A bullet\r12. Numbered item\r## Small heading\rEscaped \\*star\\* and **unclosed.\r'
 ':::basic\r10 PRINT "Hi":REM note\r20 DATA 1,2,"a:b":PRINT 42\r:::\r'
 ':::asm\rloop: lda #$2A ; comment\r .byte "string",$FF\r:::\rEnd.')

# The actual CPU provider has256physicalbanks in these fixtures. The generic
# grid harness exports a2MiB snapshot for old gates; this gate must guard all16.
class Fixture(geos.Fixture):
 def __init__(self,out,frozen,dll,colored=False):
  super().__init__(out,frozen,dll,colored)
  with zipfile.ZipFile(frozen/'product-sources.zip') as z:
   contract=z.read('src/render/geos/preview.inc')
   self.glyph_cache_span=None
   if b'.include "render/geos/preview-glyph-cache.inc"' in contract:
    layout=z.read('src/render/geos/preview-glyph-cache.inc')
    for field in (b'PGC_VERSION=3',b'PGC_BASE=$EB69',b'PGC_END=$FBA9',b'PGC_BYTES=4160'):assert field in layout,('unexpected glyph cache ABI',field)
    assert len(self.assets['geosfontrow'])-36==4095,'packaged R23 extent differs from reviewed ABI'
    self.glyph_cache_span=(0xEB69,0xFBA9)
 def source(self,data,banks=2,physical=256):
  return super().source(data,banks,physical)
 def reu(self):
  out=C.create_string_buffer(16*1024*1024)
  self.dll.gm_reu(self.m.handle,len(out),out)
  return out.raw


def guard_preview_reu(f,before,after,tag):
 """Only declared preview cache writes in a checked, current typed FE bank.

 Source rowpackets0..B1FF, D0F0..EA87 (including source backup/edit/font tails),
 The frozen production ABI may additionally declare EB69..FBA8 glyph records;
 FBA9..FFFF and every other physical bank remain exact. No whole-bank mask.
 Packed preview body differs from R27's8000+1000-byte source-cache layout.
 """
 assert len(before)==len(after)==16*1024*1024,(tag,'whole16MiB snapshot')
 handle=f.get('se_gc_handle',1)
 assert handle and not f.get('se_reu_retired',1),(tag,'liveFEhandle')
 assert f.get('se_gc_epoch',2)==f.get('se_reu_epoch',2),(tag,'FEepoch')
 assert f.m.read(f.s['se_reu_logical_owner']+handle)==0xFE,(tag,'FElogicalowner')
 physical=f.m.read(f.s['se_reu_map']+handle)
 assert physical and f.m.read(f.s['se_reu_physical_owner']+physical)==0xFE,(tag,'FEphysicalowner')
 base=physical*65536
 relative=[(0xB200,0xD0F0),(0xEA88,0xEB69)]
 if f.glyph_cache_span:relative.append(f.glyph_cache_span)
 allowed=[(base+a,base+b)for a,b in relative]
 cursor=0
 for start,end in allowed:
  assert after[cursor:start]==before[cursor:start],(tag,'noncacheREUwrite',cursor,start)
  cursor=end
 assert after[cursor:]==before[cursor:],(tag,'noncacheREUtailwrite',cursor)
 return dict(snapshot_bytes=len(after),physical_FE_bank=physical,
  allowed_relative_half_open=[list(span)for span in relative],
  allowed_bytes=sum(end-start for start,end in allowed),
  changed_cache_bytes=sum(a!=b for start,end in allowed for a,b in zip(before[start:end],after[start:end])))


def run(out,previous=None):
 frozen,identity=geos.freeze(out,previous)
 if not (frozen/'genuine').exists():shutil.copytree(ROOT/'build/geos-font-catalog',frozen/'genuine')
 if not (frozen/'build/editor-settings').exists():shutil.copytree(ROOT/'build/editor-settings',frozen/'build/editor-settings')
 verification=[Path(__file__),ROOT/'tests/test_geos_editor.py',ROOT/'tests/test_grid_modes.py',ROOT/'tools/geos_preview_model.py',ROOT/'tools/supermark_model.py',ROOT/'tools/editor_fixture.py',ROOT/'tools/cpu_editor.py',ROOT/'tools/font_fixture.py']
 with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as archive:
  for path in verification:archive.write(path,path.relative_to(ROOT))
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);f=Fixture(out,frozen,dll,True)
 fonts=FontCatalog(frozen/'genuine/catalog.json',native=(frozen/'fonts/native8.bin').read_bytes())
 defaults=(frozen/'build/editor-settings/editor-defaults.bin').read_bytes()
 active=defaults;frames=[];data=b'';base=None;catalog=None;reu=None
 def source(raw,appearance=defaults,pending=False):
  nonlocal data,active,base,catalog,reu
  data=bytes(raw);active=bytes(appearance)
  settings.decode(active)
  f.source(data);f.command(99);f.render()
  if pending:
   f.key(geos.native_text('Q')[0]);data=geos.native_text('Q')+data
  f.m.load(f.s['se_editor_settings'],active)
  base=f.canonical();catalog=f.catalog();reu=f.reu()
  f.command(102)
 def check(tag):
  f.render()
  assert f.get('se_e_ui',1)==4 and f.get('se_r_presentation',1)==1,(tag,'preview')
  assert f.canonical()==base and f.catalog()==catalog,(tag,'source/history/catalog')
  reu_guard=guard_preview_reu(f,reu,f.reu(),tag)
  assert f.read(0xC600,1024)==f.shim,(tag,'ReadyOS')
  assert f.merged()==data,(tag,'actual canonical read after preview')
  assert f.read(f.s['se_editor_settings'],64)==active,(tag,'settings')
  expected=render(data,active,catalog=fonts,top=f.get('se_v_top'))
  bits,attrs=f.read(0x6000,8000),f.read(0x4000,1000)
  matrix,colors,popup=geos.grid.logical_ui(f,data);assert popup is None
  eb,ea=with_chrome(expected.bitmap,expected.attrs,matrix,colors,fonts.native)
  if bits!=eb or attrs!=ea:
   (out/(tag+'-actual.bin')).write_bytes(bits+attrs);(out/(tag+'-expected.bin')).write_bytes(eb+ea)
   geos.png(bits,attrs,out/(tag+'-actual.png'));geos.png(eb,ea,out/(tag+'-expected.png'))
   raise AssertionError((tag,'pixel/attr mismatch',[(i,a,b)for i,(a,b)in enumerate(zip(bits,eb))if a!=b][:12],[(i,a,b)for i,(a,b)in enumerate(zip(attrs,ea))if a!=b][:12]))
  assert f.read(0xCC07,3)==expected.bottom.to_bytes(3,'little'),(tag,'canonical bottom',f.read(0xCC07,3).hex(),expected.bottom)
  assert [int.from_bytes(f.read(f.s['se_v_rows']+i*3,3),'little')for i in range(len(expected.anchors))]==list(expected.anchors),(tag,'page anchors')
  geos.png(bits,attrs,out/(tag+'.png'))
  frames.append(dict(tag=tag,top=f.get('se_v_top'),bottom=expected.bottom,rows=len(expected.rows),bitmap_sha256=hashlib.sha256(bits).hexdigest(),settings=active.hex(),reu_guard=reu_guard))
  (out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
  return expected
 def edit_profiles(**changes):
  session=settings.SessionSettings(defaults)
  for name,values in changes.items():session.update(name,**values)
  return session.active
 try:
  source(DIVERSE);check('diverse-defaults')
  f.key(13);f.render();assert f.get('se_e_ui',1)==0 and not f.get('se_r_presentation',1)
  assert f.merged()==data
  source(DIVERSE,pending=True);check('pending-source')
  for command in ('paste','cut','delete','undo','redo','clear undo'):
   f.typed(geos.native_text(command));check('readonly-'+command.replace(' ','-'))
  source(b'');check('empty')
  source(geos.native_text('Last\r'));check('trailing-cr')
  source(geos.native_text('**bold** *italic* ***both*** @@fixed@@ \\*escaped\\* **open'))
  check('inline-controls')
  source(geos.native_text(':::region **Group**\rItem\r:::end\rAfter.'));check('regions')
  source(geos.native_text(':::basic\r10 PRINT "'+('ABcd'*60)+'":REM '+('tail '*40)+'\r:::\r'))
  check('long-code-160-window')
  # Every genuine selectable face travels through actual C27/R23/fetch/raster.
  sample=geos.native_text('Wim **bold** *italic* ***both*** @@code@@.\rgjpqy '+chr(0xA4))
  for face in settings.supported_fonts():
   appearance=edit_profiles(body=dict(origin=face.origin,family=face.family,size=face.size,styles=7,foreground=3,background=6))
   source(sample,appearance);check('face-'+face.name+'-'+str(face.size))
  profiles={}
  for name,family,size in [('heading1',3,24),('heading2',2,18),('heading3',5,24),('heading4',1,14),('heading5',4,18),('heading6',27,12)]:
   profiles[name]=dict(origin=1,family=family,size=size,styles=5,foreground=6,background=7)
  profiles['code']=dict(origin=1,family=26,size=10,styles=7,foreground=14,background=6)
  appearance=edit_profiles(**profiles)
  source(geos.native_text('# Big heading\r## California\r### Cory\r#### University\r##### Dwinelle\r###### Laser Roma\r:::asm\rloop: lda #$01\r:::\r'),appearance)
  check('heading-fonts-highlight')
  source(geos.native_text(':::basic\r10 PRINT "Hi":REM note\r20 DATA 12,42\r:::\r'),appearance)
  check('genuine-code-fixed-biu')
  # Actual page keys choose the independently predicted canonical boundary.
  source(geos.native_text(''.join('Line '+str(i)+' **bold**\r'for i in range(90))))
  first=check('page-0');tops=[0]
  for page in range(1,5):
   top=first.bottom;f.key(0x87);assert f.get('se_v_top')==top
   tops.append(top);first=check('page-'+str(page))
  for page in range(3,-1,-1):
   f.key(0x86);assert f.get('se_v_top')==tops[page];check('back-'+str(page))
  f.command(98);f.render();assert f.get('se_mode',1)==2 and not f.get('se_r_presentation',1)
  assert f.merged()==data and f.canonical()==base
  f.command(99);f.render();assert f.merged()==data
  result=dict(status='passed',identity=identity,frames=frames,pixels_checked=len(frames)*64000,attributes_checked=len(frames)*1000,whole_reu_bytes_per_guard=16*1024*1024,configured_physical_banks=256,
   declared_preview_cache_bytes=7920+225+(4160 if f.glyph_cache_span else 0),guarded_unchanged_bytes_per_frame=16*1024*1024-7920-225-(4160 if f.glyph_cache_span else 0),
   scope='Actual public preview + canonical SuperMark/rawfont pixel oracle; appearance fixture inputs validated separately; actual CPU transport seams disclosed; native VIC proof separate.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
 except BaseException:
  (out/'failure-ram.bin').write_bytes(f.read(0,65536));print('FAILDEBUG',f.debug(),f.read(0xCBC0,64).hex(),flush=True);raise
 finally:f.close()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');ap.add_argument('--previous',type=Path);args=ap.parse_args()
 if not args.run:print('Prepared; --run freezes and executes actual integrated preview.');return
 out=ROOT/'build/geos-preview-editor'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN '+str(out),flush=True);run(out,args.previous)
if __name__=='__main__':main()
