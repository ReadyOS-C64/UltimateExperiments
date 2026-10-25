"""Currentfourmode/publicmenus/help/prompts/Fileowner1 pixels forrowbatchpair."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib
import test_geos_chrome_rows as core
import test_geos_semantic_editor as sem
from overlays import wrap
ROOT=core.ROOT

def run(out,base):
 frozen,identity=core.public.geos.freeze(out,base);budget=core.build(out/'leaf',frozen);g=core.public.geos.grid;g.editor_fixture.ROOT=g.cpu_editor.ROOT=frozen;g.editor_fixture.NAMES=g.cpu_editor.NAMES=identity['names'];report=json.loads((frozen/'build/editor-report.json').read_text());s=report['symbols'];images={n:wrap((out/'leaf'/file).read_bytes(),slot,i,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(report['resident_binding']['digest']))for n,file,slot,i in [('geoscaret','r27.bin',0,27),('gridedit','c16.bin',1,16)]};dll=g.runner(out);data=core.public.DIVERSE;fonts={n:(frozen/'fonts'/n).read_bytes()for n in core.public.geos.GEOS_FONTS+('native8.bin',)};frames=[]
 for mode in range(4):
  f=core.public.Fixture(out,frozen,dll,True);f.assets.update(images);f.source(data);f.command(96+mode);f.render();canonical=f.canonical();catalog=f.catalog()
  def check(tag,modal=False,background=None):
   before=f.reu()
   if modal:
    phase=f.read(0x8d00,1152)
    for _ in range(8):
     seq=f.get('se_e_draw_sequence',2);assert not f.call('se_editor_render').p&1
     if f.get('se_e_job',1)==7:
      for __ in range(30000):
       if f.get('se_e_job',1)!=7:break
       f.call('se_editor_service')
      else:raise AssertionError('modalNAVunbounded')
      continue
     if f.get('se_e_draw_sequence',2)!=seq:break
    else:raise AssertionError('modalnotpublished')
    assert f.read(0x8d00,1152)==phase and f.get('se_f_owner',1)==1
   else:f.render()
   if mode==3:
    if background is None:bits,attrs,*_=sem.expected(f,data,fonts)
    else:
     matrix,colors,popup=g.logical_ui(f,data);bits,attrs=core.public.geos.with_chrome(*background,matrix,colors,fonts['native8.bin'],popup)
   else:
    (bits,attrs),*_=g.expected(f,data)
   if mode:
    assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'bitmapattrs');core.public.geos.png(bits,attrs,out/(tag+'.png'))
   else:assert f.read(0x4000,1000)==bits and bytes(v&15 for v in f.read(0xd800,1000))==attrs,(tag,'textcellscolors')
   assert f.canonical()==canonical and f.catalog()==catalog and f.merged()==data and f.read(0xc600,1024)==f.shim
   if modal:assert f.reu()==before,'modalpureUI changedREU'
   elif mode==3:
    # Existinggrid-onlyguard covers22x240narrowrows; literalGEOS has the
    # declaredheader/22x0800slots/body/edit/fonttail. No wholebankwhitelist.
    h=f.get('se_gc_handle',1);assert h and f.get('se_gc_epoch',2)==f.get('se_reu_epoch',2) and f.m.read(f.s['se_reu_logical_owner']+h)==0xfe;bank=f.m.read(f.s['se_reu_map']+h);assert bank and f.m.read(f.s['se_reu_physical_owner']+bank)==0xfe;after=f.reu();base=bank*65536;cursor=0
    for a,b in[(base,base+64),(base+0x200,base+0xea88)]:assert after[cursor:a]==before[cursor:a],(tag,'foreignREU');cursor=b
    assert after[cursor:]==before[cursor:],(tag,'FEtail/foreignREU')
   else:assert f.reu_safe(before,tag)
   frames.append(dict(tag=tag,mode=mode,owner=f.get('se_f_owner',1),ui=f.get('se_e_ui',1),bitmap_sha256=hashlib.sha256(f.read(0x6000,8000)).hexdigest()))
  try:
   check(f'm{mode}-body');f.key(0x85);f.key(core.public.geos.native_text('f')[0]);check(f'm{mode}-menu');f.key(3);f.key(0x8b);check(f'm{mode}-help');f.key(0x8b);check(f'm{mode}-restore');f.key(0x88)
   for b in core.public.geos.native_text('mode 80'):f.key(b)
   check(f'm{mode}-prompt');f.key(3);f.render();background=(f.read(0x6000,8000),f.read(0x4000,1000))
   f.hold_file_transport=True;f.put('se_e_key',15,1);f.put('se_e_mods',4,1);f.call('se_editor_input');assert f.get('se_e_ui',1)==3 and f.get('se_f_owner',1)==1;check(f'm{mode}-File-owner1',True,background);f.put('se_e_key',0x8b,1);f.put('se_e_mods',0,1);f.call('se_editor_input');check(f'm{mode}-File-help',True,background)
  finally:f.close()
 # CurrentfourmodeF8cycle is0→1→2→3→0, reverse follows0→3→2→1→0.
 f=core.public.Fixture(out,frozen,dll,True);f.assets.update(images);f.source(data);canonical=f.canonical();catalog=f.catalog()
 try:
  for mods,targets in[(0,[1,2,3,0]),(4,[3,2,1,0])]:
   for target in targets:
    f.key(0x8c,mods=mods);assert f.get('se_mode',1)==target;mode=target;check(f'F8-{mods}-{target}')
 finally:f.close()
 result=dict(status='passed',budget=budget,frames=frames,fourmodecycles=[0,1,2,3,0,3,2,1,0],scope='Current4modeactualpublicinput/render withindependentbody/menu/help/prompt/Filemodalpixels; FileproviderheldbeforeDOS, owner1phase1152exact/UIpureREUunchanged. ActualF8IRQbyte/modifierCPUinput, notphysicalchord. PrivateC16/R27paironly.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,len(frames),flush=True)
if __name__=='__main__':
 out=ROOT/'build/geos-chrome-rows-modes'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,Path(sys.argv[1]).resolve())
