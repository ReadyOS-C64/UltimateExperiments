"""Private actualSPLICE one-line convergence and explicitbase/live mapping.

No production/sharedbuild. Public source/edit, realbaseline/R14/SuperMark. The
prototype format is deliberately rejected by unmodifiedproductqueries.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,binascii,hashlib
import test_cache_observer as ob
from supermark_model import blocks
ROOT=ob.ROOT;BASE=ROOT/'build/cache-editor-product/20261026T035310363807Z/fixture'
DATA=ob.geos.native_text('Alpha ordinary text.\rMiddle ordinary line.\rOmega tail.\r')
F=0x8D00

def builder():
 p=ROOT/'src/cache/splice-probe/build.py';s=importlib.util.spec_from_file_location('spbuild',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def roots(raw):
 out=[]
 for off in(0,128):
  h=raw[off:off+128]
  if h[:4]==b'BCA1'and h[5]==1 and binascii.crc_hqx(h[:5]+h[6:119]+h[121:],65535)==int.from_bytes(h[119:121],'little'):out.append((int.from_bytes(h[18:22],'little'),off,h))
 assert out;return max(out)

def run(out,base):
 images=builder().build(out/'build',base);g=ob.Gate(out/'gate',base);f=g.f
 for n,v in images.items():f.assets[n]=v
 calls=[]
 def arena():
  t=f.read(f.s['se_bc_arena'],5);logical=f.m.read(f.s['object_extents']+t[0]*16);bank=f.m.read(f.s['se_reu_map']+logical);return bank,g.reu()[bank*65536:(bank+1)*65536]
 def invoke(op):
  f.put('se_overlay_frame',op,1);r,n=f.fast_call(f.s['se_overlay_call'],a=40,x=1);calls.append(dict(op=op,a=r.a,carry=r.p&1,instructions=n,state=f.m.read(F+1),pub=f.m.read(F+53)));return r
 try:
  f.source(DATA);f.typed(ob.geos.native_text('syntax markdown'));f.command(99);f.render();assert f.get('se_bc_count',1)==0 and f.get('se_bc_flags',1)&1
  bank,raw=arena();old=roots(raw);at=DATA.index(ob.geos.native_text('ordinary'),25)+3;f.position(at);f.key(ob.Q);wanted=DATA[:at]+bytes([ob.Q])+DATA[at:];assert f.merged()==wanted and f.get('se_hot_pending',1)and f.get('se_bc_count',1)==1
  bank,raw=arena();old=roots(raw);before=g.reu();stable=g.stable();ring=f.read(f.s['se_bc_ring'],96);event=ring[f.get('se_bc_tail',1)*32:][:32];assert event==ob.event(f.get('se_bc_ticket',4),int.from_bytes(old[2][57:61],'little'),int.from_bytes(old[2][36:38],'little'),at,0,1)
  f.put('se_f_owner',4,1);r=invoke(0)
  for _ in range(200):
   assert not r.p&1,('bridge',r.a,calls)
   if r.a==0:break
   assert r.a==1
   assert g.stable()==stable and f.get('se_bc_count',1)==1 and f.read(f.s['se_bc_ring'],96)==ring
   after=g.reu();want=bytearray(before)
   for lo,hi in((old[1]^128,(old[1]^128)+128),(0x178,0x180),(0x900,0x920),(0xF000,0xF120)):want[bank*65536+lo:bank*65536+hi]=after[bank*65536+lo:bank*65536+hi]
   assert after==want and after[bank*65536+old[1]:bank*65536+old[1]+128]==old[2]
   r=invoke(1)
  assert r.a==0 and not r.p&1 and not f.get('se_doc_read_locks',1)and f.get('se_bc_count',1)==0
  final_reu=g.reu();final_wanted=bytearray(before)
  for lo,hi in((old[1]^128,(old[1]^128)+128),(0x178,0x180),(0x900,0x920),(0xF000,0xF120)):final_wanted[bank*65536+lo:bank*65536+hi]=final_reu[bank*65536+lo:bank*65536+hi]
  assert final_reu==final_wanted
  _,current=arena();new=roots(current);assert new[2][31]==3 and new[2][22:26]==f.read(f.s['se_bc_ticket'],4)and new[2][26:30]==old[2][22:26]
  assert current[0x900:0x920]==event and current[old[1]:old[1]+128]==old[2]and current[0x1000:0x2000]==raw[0x1000:0x2000]
  initial_proof=dict(old_root=old[2].hex(),new_root=new[2].hex(),manifest=current[0xF040:0xF0C0].hex(),dirty_record=current[0xF0C0:0xF120].hex(),baseline_CR_page_sha256=hashlib.sha256(raw[0x1000:0x2000]).hexdigest(),allowed_REU_spans=[[old[1]^128,(old[1]^128)+128],[0x178,0x180],[0x900,0x920],[0xF000,0xF120]])
  bridge_calls=list(calls);bridge_feeds=int.from_bytes(f.read(F+58,3),'little');query_results=[];readonly=g.reu();model=blocks(wanted)+[dict(kind=255,start=len(wanted),end=len(wanted),body=len(wanted),language=0,level=0)]
  for position in range(len(wanted)+1):
   f.m.load(0x8B20,position.to_bytes(3,'little'));r=invoke(3)
   for _ in range(128):
    assert not r.p&1,('query',position,r.a,calls[-20:])
    if r.a==0:break
    r=invoke(1)
   assert r.a==0 and not r.p&1 and not f.get('se_doc_read_locks',1)
   cr=f.read(F+291,96);start=int.from_bytes(cr[16:19],'little');end=start+int.from_bytes(cr[19:22],'little');body=start+int.from_bytes(cr[22:25],'little');expected=next(x for x in model if x['start']<=position<=x['end'])
   assert (cr[3],start,end,body,cr[69],cr[70])==(expected['kind'],expected['start'],expected['end'],expected['body'],expected['language'],expected['level']),(position,cr.hex(),expected)
   origin=f.m.read(F+54);ticket=int.from_bytes(cr[12:16],'little');assert ticket==(f.get('se_bc_ticket',4)if origin else int.from_bytes(old[2][22:26],'little'))
   query_results.append(dict(position=position,kind=cr[3],start=start,end=end,origin=origin,ticket=ticket))
  assert g.reu()==readonly and g.stable()==stable and f.merged()==wanted and f.read(0xC600,1024)==f.shim
  # Originalproductclassifier mustrefuse the explicitunknownrootfeature.
  f.m.write(0x8B40+21,0);f.m.load(0x8B40,bytes(3));f.put('se_overlay_frame',0,1);r,n=f.fast_call(f.s['se_overlay_call'],a=35,x=1)
  for _ in range(32):
   if r.p&1 or r.a!=1:break
   f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=35,x=1)
  assert r.p&1 and r.a==0xC2 and not f.get('se_doc_read_locks',1)
  standard_refused=r.a
  # Rebuild each fault precondition with the real public source/baseline/edit.
  faults=[];fault_bytes=b''
  def setup_fault(byte=ob.Q):
   nonlocal fault_bytes
   f.source(DATA);f.typed(ob.geos.native_text('syntax markdown'));f.command(99);f.render();f.position(at);f.key(byte)
   fault_bytes=f.merged();assert fault_bytes==DATA[:at]+bytes([byte])+DATA[at:]
   b,raw_=arena();root_=roots(raw_);full=g.reu();queue=(f.read(f.s['se_bc_arena'],13),f.read(f.s['se_bc_head'],3),f.read(f.s['se_bc_ring'],96));stable_=g.stable();f.put('se_f_owner',4,1);return b,raw_,root_,full,queue,stable_
  def queue_now():return(f.read(f.s['se_bc_arena'],13),f.read(f.s['se_bc_head'],3),f.read(f.s['se_bc_ring'],96))
  for state,pub in [(1,0),(2,0),(3,0),(4,0)]+[(5,n)for n in range(1,11)]:
   b,raw_,root_,full,queue,stable_=setup_fault();r=invoke(0)
   for _ in range(100):
    assert not r.p&1 and r.a==1
    if f.m.read(F+1)==state and(state!=5 or f.m.read(F+53)==pub):break
    r=invoke(1)
   assert f.m.read(F+1)==state and(state!=5 or f.m.read(F+53)==pub)
   r=invoke(2);assert not r.p&1 and r.a==0 and not f.get('se_doc_read_locks',1)and queue_now()==queue and g.stable()==stable_ and f.merged()==fault_bytes
   after=g.reu();wanted_=bytearray(full)
   for lo,hi in((root_[1]^128,(root_[1]^128)+128),(0x178,0x180),(0x900,0x920),(0xF000,0xF120)):wanted_[b*65536+lo:b*65536+hi]=after[b*65536+lo:b*65536+hi]
   assert after==wanted_ and after[b*65536+root_[1]:b*65536+root_[1]+128]==root_[2]
   faults.append(f'cancel-{state}-{pub}');print('CANCEL PASS',state,pub,flush=True)
  for label,byte in [('star',42),('inlinecode',64),('fencecolon',58),('CR',13)]:
   b,raw_,root_,full,queue,stable_=setup_fault(byte);r=invoke(0)
   for _ in range(100):
    if r.p&1 or r.a!=1:break
    r=invoke(1)
   assert r.p&1 or r.a==2,(label,'unsupported accepted')
   assert queue_now()==queue and g.stable()==stable_ and f.merged()==fault_bytes and g.reu()==full and not f.get('se_doc_read_locks',1)
   faults.append('refuse-'+label);print('REFUSAL PASS',label,flush=True)
  for ident,label in [(14,'missingR14'),(34,'missingR34'),(0,'sourceRevision'),(-1,'corruptOwnedState'),(-2,'PlainAcrossYield')]:
   b,raw_,root_,full,queue,stable_=setup_fault();r=invoke(0)
   for _ in range(100):
    assert not r.p&1 and r.a==1
    if f.m.read(F+1)==4:break
    r=invoke(1)
   if ident>0:
    idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)&1==0);f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active'],0)
   elif ident==0:f.put('se_r_revision',f.get('se_r_revision',4)+1,4)
   elif ident==-1:f.m.write(F+1,0)
   else:f.put('se_render_caps',0,1)
   for _ in range(100):
    r=invoke(1)
    if r.p&1 or r.a!=1:break
   assert r.p&1 and not f.get('se_doc_read_locks',1)and queue_now()==queue and g.stable()==stable_ and f.merged()==fault_bytes and g.reu()==full
   faults.append(label);print('FAULT PASS',label,flush=True)
  b,raw_,root_,full,queue,stable_=setup_fault();frame=f.read(F,576);extra=f.read(0x8880,0x2C0)
  for owner in(0,1,2,3,5,255):
   f.put('se_f_owner',owner,1)
   for op in(0,1,2,3):
    r=invoke(op);assert r.p&1 and r.a==0xB2 and f.read(F,576)==frame and f.read(0x8880,0x2C0)==extra and g.reu()==full
  faults.append('sixforeignowners-fourOps')
  f.put('se_f_owner',4,1);f.put('se_render_caps',0,1)
  for op in(0,3):
   r=invoke(op);assert not r.p&1 and r.a==2 and f.read(F,576)==frame and f.read(0x8880,0x2C0)==extra and g.reu()==full
  faults.append('Plain-before-frame')
  (out/'result.json').write_text(json.dumps(dict(status='PASS-private-ordinary-insert-and-mappedqueries',budget=json.loads((out/'build/budget.json').read_text()),initial_proof=initial_proof,calls=calls,queries=query_results,faults=faults,source_bytes=len(wanted),old_ticket=int.from_bytes(old[2][22:26],'little'),live_ticket=f.get('se_bc_ticket',4),whole16MiB_query_unchanged=True,standard_query_refuses_feature=hex(standard_refused),bridge_calls=bridge_calls,actual_dirty_line_parser_feeds=bridge_feeds),indent=2)+'\n');print('SPLICE PASS',out,len(query_results),'independentclassifications',flush=True)
 except BaseException as e:
  (out/'failure.json').write_text(json.dumps(dict(error=repr(e),calls=calls),indent=2)+'\n');(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--region',action='store_true');a=p.parse_args();
 if a.region:DATA=ob.geos.native_text(':::region Group\rAlpha ordinary text.\rMiddle ordinary line.\r:::end\rOmega tail.\r')
 out=ROOT/'build/cache-splice'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)
