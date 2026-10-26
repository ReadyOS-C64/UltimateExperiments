"""Actual resident missing-cache cleanup and queued-key preemption.

The explicit admission seam opens a real R14 source lease, saves its86B frame,
then makes the outer cache capsule unavailable. No cache hit is fabricated.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,sys,hashlib
import test_cache_observer as observer

ROOT=observer.ROOT

def run(out,base):
 gate=observer.Gate(out,base);f=gate.f;cases=[]
 try:
  def setup(flags=9):
   f.source(observer.DATA);f.put('se_render_caps',0,1)
   f.put('se_f_owner',4,1)
   f.m.load(f.s['se_fs_state'],bytes(86));f.put('se_overlay_frame',0,1)
   r,_=f.fast_call(f.s['se_overlay_call'],a=14,x=0)
   assert not r.p&1 and f.get('se_doc_read_locks',1)==1
   saved=f.read(f.s['se_fs_state'],86);f.m.load(0x8DAD,saved)
   f.m.load(0x9040,bytes([0xE7])*86);f.m.load(f.s['se_fs_state'],bytes(86))
   f.put('se_bc_flags',flags,1);f.m.write(0x912C,0);f.m.write(0x912D,0)
   f.put('se_e_job',11,1);f.m.write(0x9135,35);f.m.write(0x9136,1)
   return gate.reu(),gate.stable()
  for flags in (9,10):
   before,stable=setup(flags)
   f.call('se_geos_cancel')
   assert f.get('se_doc_read_locks',1)==0 and f.get('se_f_owner',1)==0
   assert f.get('se_bc_flags',1)&15==flags&7
   assert f.get('se_fs_owned',1)==0 and f.get('se_fs_active',1)==0
   f.call('se_geos_cancel');gate.guards(before,'resident cancel',unchanged=stable)
   cases.append(dict(tag='resident-new-reader-cancel',flags=flags))
  for owner in (0,1,2,3):
   before,stable=setup();f.put('se_f_owner',owner,1)
   frame=f.read(0x8D00,1152);flags=f.get('se_bc_flags',1)
   f.call('se_geos_cancel')
   assert f.read(0x8D00,1152)==frame and f.get('se_bc_flags',1)==flags
   assert f.get('se_doc_read_locks',1)==1
   f.put('se_f_owner',4,1);f.call('se_geos_cancel')
   assert f.get('se_doc_read_locks',1)==0
   gate.guards(before,'foreign owner',unchanged=stable)
   cases.append(dict(tag='foreign-owner-opaque',owner=owner))
  for key,mod in ((81,0),(3,4)):
   before,stable=setup(10)
   f.put('se_input_tail',0,1);f.put('se_input_head',1,1)
   f.m.write(f.s['se_input_chars'],key);f.m.write(f.s['se_input_mods'],mod)
   f.m.write(f.s['se_input_matrix'],0x40)
   f.call('se_editor_service')
   assert f.get('se_input_tail',1)==0 and f.get('se_input_head',1)==1
   assert f.get('se_e_job',1)==0 and f.get('se_e_redraw',1)==0
   assert f.get('se_doc_read_locks',1)==0 and f.get('se_f_owner',1)==0
   r=f.call('se_input_get');assert (r.a,r.x)==(key,mod)
   gate.guards(before,'queued key preserved',unchanged=stable)
   cases.append(dict(tag='queued-key-preemption',key=key,mod=mod))
  # Change the provider epoch before outer admission: current foreign leases
  # must survive cleanup; restoring an old epoch before END would be unsafe.
  before,stable=setup();epoch=f.get('se_reu_epoch',2)
  f.put('se_reu_epoch',epoch+1,2);f.put('se_doc_read_locks',7,1)
  r,_=f.fast_call(f.s['se_overlay_call'],a=35,x=1)
  assert r.p&1 and r.a==0x18
  f.call('se_geos_cancel')
  assert f.get('se_doc_read_locks',1)==7 and f.get('se_fs_owned',1)==0
  assert f.get('se_bc_flags',1)&15==1
  gate.guards(before,'provider epoch foreign lease',unchanged=stable)
  cases.append(dict(tag='unavailable-outer-epoch-preserves-foreign-leases',error=r.a))
  result=dict(status='PASS',resident=f.report['sha256'],binding=f.report['resident_binding']['digest'],cases=cases,
   scope='Actual resident cancel/service, real R14 lease, explicit saved-frame admission seam. No renderer cache hit or native claim.',
   verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
 finally:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args()
 out=ROOT/'build/cache-dispatch'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
 print('RUN',out,flush=True);run(out,a.fixture.resolve())
