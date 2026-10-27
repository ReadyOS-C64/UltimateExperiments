"""CPU-only product route audit for selected-range/R32 hot-load coexistence."""
from pathlib import Path
from datetime import datetime, timezone
import json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_semantic_consumer as c
import test_geos_checkpoint_refresh_hook as hook

def run(out):
 frozen,identity=hook.freeze_project(out,ROOT)
 c.geos.grid.editor_fixture.ROOT=c.geos.grid.cpu_editor.ROOT=frozen
 c.geos.grid.editor_fixture.NAMES=c.geos.grid.cpu_editor.NAMES=identity['names']
 dll=c.geos.grid.runner(out);f=c.Fixture(out,frozen,dll,True)
 try:
  data=c.geos.native_text('alpha beta gamma\rsecond row\rtail')
  f.source(data)
  # Existing R32 op1 with no selected-range ownership remains W_LOAD.
  assert f.get('se_snapshot_busy',1)==0
  f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=32,x=0)
  assert not r.p&1 and r.a in (0,1),(r.a,r.p)
  while f.get('se_e_job',1):f.call('se_editor_service')
  base_locks=f.get('se_doc_read_locks',1)

  # Create an owner-6 destination and exercise the resident trampoline into
  # relocated R32 BEGIN/STEP, including its exact ownership discriminator.
  r,_=f.fast_call(f.s['se_object_create'],a=6,x=1);assert not r.p&1
  token=f.read(f.s['se_object_id'],5)
  f.m.load(f.s['se_object_id'],token);f.put('se_object_offset',4096);assert not f.call('se_object_resize').p&1
  f.m.load(f.s['se_range_token'],token);f.put('se_range_offset',0);f.put('se_range_position',2);f.put('se_range_length',20)
  before=(f.canonical(),f.catalog(),f.reu())
  r,n0=f.fast_call(f.s['se_range_begin']);assert not r.p&1 and r.a==1
  assert f.get('se_snapshot_busy',1)==2 and f.get('se_doc_read_locks',1)==base_locks+1,(f.get('se_snapshot_busy',1),f.get('se_doc_read_locks',1),base_locks,hex(f.s['se_range_begin']))
  steps=0;used=0
  while f.get('se_snapshot_busy',1):
   r,n=f.fast_call(f.s['se_range_step']);assert not r.p&1;used+=n;steps+=1;assert steps<64
  assert f.get('se_doc_read_locks',1)==base_locks and f.get('se_range_bytes',2)>0
  assert f.canonical()==before[0] and f.catalog()==before[1]
  # REU differs only through the explicitly selected owner-6 destination.
  assert f.read(0xc600,1024)==f.shim
  result=dict(status='passed',hot_load_instructions=n,range_begin_instructions=n0,
              range_steps=steps,range_step_instructions=used,range_bytes=f.get('se_range_bytes',2),
              scope='Actual resident range trampoline and R32 hot-loader discriminator in packaged product')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',result)
  return result
 finally:f.close()

if __name__=='__main__':
 out=ROOT/'build/r32-range-route'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
 print('RUN',out);print('RESULT',run(out)['status'])
