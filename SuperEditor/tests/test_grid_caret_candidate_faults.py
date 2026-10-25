"""Actual private48 root missing/badC33, opaqueFILE planner, layoutSTOP."""
from pathlib import Path
from datetime import datetime,timezone
import json,ctypes as C,shutil,hashlib
import test_geos_fold_editor as fold
import test_grid_modes as grid
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/grid-caret-integration/20261025T163000/fixture'
def run(out,base=BASE):
 frozen=out/'fixture';shutil.copytree(base,frozen);identity=json.load(open(frozen/'freeze.json'));grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=frozen;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=identity['names'];dll=fold.retention.runner(out);f=fold.Fixture(out,frozen,dll,True);cases=[]
 def ready():f.render();f.finish_style()
 def snap():return dict(canonical=f.canonical(),source=f.merged(),reu=f.reu(),phase=f.read(0x8d00,1152),bitmap=f.read(0x6000,8000),attrs=f.read(0x4000,1000),shim=f.read(0xc600,1024))
 def unchanged(b,tag,pixels=True,phase=True):
  assert f.canonical()==b['canonical'] and f.merged()==b['source'] and f.reu()==b['reu'] and f.read(0xc600,1024)==b['shim'],(tag,'canonical/source/history/clipboard/whole16MiB/shim')
  if phase:assert f.read(0x8d00,1152)==b['phase'],(tag,'phase')
  if pixels:assert f.read(0x6000,8000)==b['bitmap'] and f.read(0x4000,1000)==b['attrs'],(tag,'before-pixels')
 def call(op):f.put('se_overlay_frame',op,1);return f.fast_call(f.s['se_overlay_call'],a=33,x=1)
 def asset_byte(index,offset,value=None):
  handle=f.m.read(f.s['se_overlay_asset']+(index>>4));f.put('se_reu_logical',handle,1);f.put('se_reu_offset',(index&15)*4096+offset,2);f.put('se_reu_c64',0x8880,2);f.put('se_reu_length',1,2)
  if value is None:assert not f.call('se_reu_copy',1).p&1;return f.m.read(0x8880)
  f.m.write(0x8880,value);assert not f.call('se_reu_copy',0).p&1
 try:
  f.source(fold.TINY);f.command(98);f.position(3);f.command(115);ready();assert f.get('se_ef_valid',1)
  index=next(i for i in range(f.s['se_overlay_capacity']) if f.m.read(f.s['se_overlay_ids']+i)==33 and f.m.read(f.s['image_slot']+i)&1)
  for tag,bad in [('missing-C33-folded-layout',False),('bad-C33-checked-owner2-CRC',True)]:
   # Require the slow folded planner path, rather than only an optional TRY.
   f.put('se_l_need_wrap',1,1)
   if bad:
    old=asset_byte(index,16);asset_byte(index,16,old^1)
   else:f.m.write(f.s['se_overlay_ids']+index,0)
   before=snap();r=f.call('se_editor_render');expected=0x14 if bad else 0x17
   assert r.p&1 and f.get('se_e_error',1)==expected,(tag,r.a,r.p,f.debug());unchanged(before,tag);assert f.get('se_f_owner',1)==0 and f.get('se_doc_read_locks',1)==0
   cases.append(dict(tag=tag,error=expected,whole16MiB=True,phase=True,beforePixels=True));print('PASS',cases[-1],flush=True)
   if bad:asset_byte(index,16,old)
   else:f.m.write(f.s['se_overlay_ids']+index,33)
   f.put('se_e_error',0,1);ready();assert f.merged()==before['source']
  # The pure planner owns no phase: a genuine FileOpen claim may have an
  # outstanding real directory request. No ROM/DOS success is fabricated.
  f.source(grid.native_text('File modal source'));f.command(98);ready();f.put('se_e_error',0,1);r=f.call('se_editor_command',80)
  assert f.get('se_f_owner',1)==1 and f.get('se_e_ui',1)==3 and f.get('se_e_job',1)==9
  before=snap();workspace=f.read(0x8880,0x380);r,n=call(2);assert not r.p&1 and r.a in (0,1,2);unchanged(before,'actual-FileOpen-pendingDIR-planner');assert f.read(0x8880,0x380)==workspace and f.get('se_f_owner',1)==1
  cases.append(dict(tag='actual-FileOpen-pendingDIR-planner',result=r.a,instructions=n,scope='Real C12 owner/frame; no DOS or completed-cancel claim'));print('PASS',cases[-1],flush=True)
  # Explicit fresh fixture/source initialization discards that unserviced
  # transport case; independent real public C11 cancellation follows.
  f.source(grid.native_text('Long wrapped source '*12+'\rSecond'));f.command(98);ready();f.command(77);before=snap();r=f.call('se_editor_render');assert not r.p&1 and f.get('se_e_job',1)==7,(r.a,f.debug());assert f.get('se_f_owner',1)==0
  f.queued(3);f.call('se_editor_service');assert f.get('se_e_job',1)==0 and f.get('se_e_draw_busy',1)==0 and f.get('se_doc_read_locks',1)==0;unchanged(before,'actual-queuedSTOP-C11')
  cases.append(dict(tag='actual-queuedSTOP-C11',phase=True,source=True,whole16MiB=True,beforePixels=True));print('PASS',cases[-1],flush=True)
  f.command(0);ready();(bits,attrs),_,_,_=grid.expected(f,f.merged());assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
  fold.geos.png(bits,attrs,out/'after-layout-STOP-recovery.png');cases.append(dict(tag='layoutSTOP-render-recovery',pixels=64000,attrs=1000));print('PASS',cases[-1],flush=True)
  result=dict(status='passed',cases=cases,resident=identity['prg_sha256'],scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure-reu.bin').write_bytes(f.reu());raise
 finally:f.close()
if __name__=='__main__':
 out=ROOT/'build/grid-caret-faults'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
