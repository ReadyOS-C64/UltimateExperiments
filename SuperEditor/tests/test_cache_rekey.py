"""Private one-kind REKEY durable bridge. No production/shared build changes.

Actual pending edits, semantic baseline and trusted flush events produce every
positive fixture. C7 internal admission/phase invalidation is an explicit CPU
transport seam; no semantic result, source identity or journal entry is seeded.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,hashlib,binascii,ctypes as C
import test_cache_observer as observer
import test_plain_geos as plain
ROOT=observer.ROOT;BASE=ROOT/'build/cache-editor-product/20261026T031201729970Z/fixture'
DATA=observer.geos.native_text('Body **bold** text.\rTail.')
F=0x8D00

def load_builder():
 p=ROOT/'src/cache/rekey-probe/build.py';spec=importlib.util.spec_from_file_location('rekey_build',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def roots(raw):
 valid=[]
 for off in (0,128):
  h=raw[off:off+128]
  if h[:4]==b'BCA1'and h[5]==1 and binascii.crc_hqx(h[:5]+h[6:119]+h[121:],0xFFFF)==int.from_bytes(h[119:121],'little'):valid.append((int.from_bytes(h[18:22],'little'),off,h))
 assert valid;return sorted(valid)

class Test:
 def __init__(self,out,base):
  self.out=out;self.budget=load_builder().build(out/'build',base);self.g=observer.Gate(out/'gate',base);self.f=self.g.f;self.f.assets['rekey']=(out/'build/rekey.seo').read_bytes();self.positives=[];self.faults=[];self.calls=[]
  self.fonts={n:(self.g.frozen/'fonts'/n).read_bytes()for n in observer.geos.GEOS_FONTS+('native8.bin',)}
 def unread(self):
  f=self.f;raw=f.read(f.s['se_bc_arena'],17);return raw[:13]+raw[14:],f.read(f.s['se_bc_ring'],96)
 def arena(self):
  f=self.f;token=f.read(f.s['se_bc_arena'],5);oid=token[0];logical=f.m.read(f.s['object_extents']+oid*16);bank=f.m.read(f.s['se_reu_map']+logical);return token,bank,self.g.reu()[bank*65536:(bank+1)*65536]
 def invoke(self,op):
  f=self.f;f.put('se_overlay_frame',op,1);r,n=f.fast_call(f.s['se_overlay_call'],a=38,x=1);self.calls.append(dict(op=op,instructions=n,a=r.a,carry=r.p&1,phase=f.m.read(F+1),count=f.get('se_bc_count',1)));return r
 def baseline(self):
  f=self.f
  for name in ('se_i_ready','se_i_count','se_n_cache_count'):f.put(name,0,1)
  f.put('se_f_owner',4,1);f.put('se_overlay_frame',9,1);r,n=f.fast_call(f.s['se_overlay_call'],a=7,x=1);assert not r.p&1 and r.a==1 and f.read(0x9135,2)==bytes((34,0));f.put('se_e_job',11,1);f.settle();f.render()
 def setup(self,data=DATA,at=5,zero=False,baseline=True,slot=0,high=False):
  f=self.f;f.source(data);f.typed(observer.geos.native_text('syntax markdown'));f.command(99);f.render()
  if high:
   f.typed(observer.geos.native_text('goto 2'))
   for _ in range(at-f.get('se_hot_caret')):f.command(2)
   f.render();assert f.get('se_hot_caret')==at
  else:f.position(at)
  f.key(observer.Q);wanted=data[:at]+bytes([observer.Q])+data[at:]
  if zero:f.key(0x14);wanted=data
  assert f.merged()==wanted and f.get('se_hot_pending',1)
  if baseline:
   self.baseline();assert f.merged()==wanted and f.get('se_hot_pending',1)and f.get('se_bc_count',1)==0
   token,bank,old=self.arena();self.oldroot=roots(old)[-1];assert self.oldroot[2][62]==1
   if slot:
    # Empty queue topology models prior consumed slots. Real R32/R2 still emits
    # the actual event/CRC in the requested empty slot; no event bytes are seeded.
    f.put('se_bc_head',slot,1);f.put('se_bc_tail',slot,1)
  self.g.flush();assert f.merged()==wanted and f.document()==wanted and not f.get('se_hot_pending',1)
  self.wanted=wanted;self.token,self.bank,self.raw=self.arena();self.before=self.g.reu();self.stable=self.g.stable();self.queue=self.unread();self.ring=f.read(f.s['se_bc_ring'],96);self.ticket=f.get('se_bc_ticket',4)
  self.event=f.read(f.s['se_bc_ring']+f.get('se_bc_tail',1)*32,32);self.calls=[];f.put('se_f_owner',4,1)
  return wanted
 def allowed(self,after):
  want=bytearray(self.before);off=self.oldroot[1]^128
  for lo,hi in [(off,off+128),(0x900,0x920)]:want[self.bank*65536+lo:self.bank*65536+hi]=after[self.bank*65536+lo:self.bank*65536+hi]
  assert after==want,'whole16MiB outside exactalternate128Broot+32Bjournal'
  assert after[self.bank*65536+self.oldroot[1]:self.bank*65536+self.oldroot[1]+128]==self.oldroot[2]
 def pending(self,phase):
  r=self.invoke(0)
  for _ in range(32):
   if r.p&1 or r.a!=1:raise AssertionError(('pending',phase,r.a,r.p,self.calls))
   assert self.unread()==self.queue and self.g.stable()==self.stable;self.allowed(self.g.reu())
   if self.f.m.read(F+1)==phase:return
   r=self.invoke(1)
  raise AssertionError('phase not reached')
 def complete(self,started=False):
  f=self.f;r=self.invoke(1 if started else 0)
  for _ in range(32):
   if r.p&1 or r.a!=1:break
   assert self.unread()==self.queue and self.g.stable()==self.stable;after=self.g.reu();self.allowed(after)
   if f.m.read(F+1)==6:
    assert after[self.bank*65536+(self.oldroot[1]^128)+5]==0 and f.get('se_bc_count',1)==1
   r=self.invoke(1)
  assert not r.p&1 and r.a==0,('complete',r.a,r.p,self.calls)
  assert f.get('se_bc_count',1)==0 and f.get('se_bc_ticket',4)==self.ticket and not f.get('se_doc_read_locks',1)and not f.get('se_bc_flags',1)&8
  _,bank,raw=self.arena();assert bank==self.bank;newroot=roots(raw)[-1];assert newroot[0]==self.oldroot[0]+1 and newroot[1]==self.oldroot[1]^128
  assert raw[0x900:0x920]==self.event and raw[self.oldroot[1]:self.oldroot[1]+128]==self.oldroot[2]
  assert newroot[2][22:30]==self.oldroot[2][22:30]and newroot[2][30]==1 and newroot[2][91:119]==self.oldroot[2][91:119]
  assert newroot[2][32:91]==f.read(F+173+27,59);self.allowed(self.g.reu());assert f.read(f.s['se_bc_ring'],96)==self.ring and self.g.stable()==self.stable and f.read(0xC600,1024)==f.shim
  return newroot
 def render(self,tag):
  f=self.f;f.put('se_f_owner',0,1);targets=[('C24',0xB010,'geossema'),('C34',0xB010,'sema'),('C35',0xB010,'inln'),('C37',0xB010,'page')];dll=self.g.dll
  dll.pb_config(f.s['se_overlay_active'],len(targets),(C.c_uint16*len(targets))(*(x[1]for x in targets)),(C.c_uint8*len(targets))(*([2]*len(targets))),(C.c_uint8*len(targets))(*(self.g.identity['names'].index(x[2])+1 for x in targets)),(C.c_uint8*(16*len(targets)))());dll.pb_begin()
  f.put('se_gc_width',0,1);f.m.write(0xCF90,0);f.m.write(0xCFE8,0);f.put('se_l_valid',0,1);f.put('se_r_valid',0,1);f.put('se_l_need_wrap',1,1);start=f.total_instructions;f.render();cost=f.total_instructions-start;dll.pb_end();counts={x[0]:int(dll.pb_get(i))for i,x in enumerate(targets)};assert counts['C24']==counts['C34']==0 and counts['C35']>0
  bits,attrs,_=plain.expected(f,self.wanted,self.fonts,1);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs and f.merged()==self.wanted;observer.geos.png(bits,attrs,self.out/(tag+'.png'));return cost,counts
 def positive(self,tag,**kwargs):
  self.setup(**kwargs);assert self.f.get('se_bc_count',1)==1 and self.event[1]==2;root=self.complete();cost,counts=self.render(tag);item=dict(tag=tag,source_bytes=len(self.wanted),ticket=self.ticket,event=self.event.hex(),calls=self.calls,render_instructions=cost,counters=counts,root_sequence=root[0]);self.positives.append(item);print('POSITIVE PASS',tag,len(self.wanted),len(self.calls),counts,flush=True)
 def unchanged_failure(self,tag,op=1,expected=None):
  f=self.f;before=self.g.reu();queue=self.unread();stable=self.g.stable();r=self.invoke(op)
  for _ in range(32):
   if r.p&1 or r.a!=1:break
   assert self.unread()==queue and self.g.stable()==stable and self.g.reu()==before,(tag,'changed before refusal')
   r=self.invoke(1)
  assert (r.p&1)or r.a==2,(tag,'accepted',r.a,r.p)
  if expected is not None:assert r.a==expected,(tag,r.a,expected)
  assert self.unread()==queue and self.g.stable()==stable and self.g.reu()==before and f.read(0xC600,1024)==f.shim
  assert not f.get('se_doc_read_locks',1)and not f.get('se_bc_flags',1)&8
  self.faults.append(dict(tag=tag,a=r.a,carry=r.p&1));print('FAULT PASS',tag,hex(r.a),flush=True)
 def event_fault(self,tag,offset,mask=1,crc=True):
  self.setup();f=self.f;at=f.s['se_bc_ring']+f.get('se_bc_tail',1)*32;raw=bytearray(f.read(at,32));raw[offset]^=mask
  if crc:raw[29:31]=binascii.crc_hqx(raw[1:29]+raw[31:32],0xFFFF).to_bytes(2,'little')
  f.m.load(at,raw);self.unchanged_failure(tag,0)
 def run_faults(self):
  f=self.f
  for phase in range(1,7):
   self.setup();self.pending(phase);self.invoke(2);assert self.unread()==self.queue and self.g.stable()==self.stable and not f.get('se_doc_read_locks',1)and not f.get('se_bc_flags',1)&8;self.allowed(self.g.reu());self.complete();self.faults.append(dict(tag=f'cancel-phase{phase}-retry',reader_cleanup=True));print('CANCEL PASS',phase,flush=True)
  for tag,off,mask,crc in [('bad-marker',0,1,True),('SPLICE-not-REKEY',1,3,True),('reserved-flags',2,1,True),('reserved3',3,1,True),('reserved31',31,1,True),('CRC',16,1,False),('ticket',4,1,True),('generation-before',25,1,True),('generation-after',27,1,True),('revision-before',8,1,True),('revision-after',12,1,True),('24bit-position-overflow',18,128,True),('24bit-delete-overflow',21,128,True),('24bit-insert-overflow',24,128,True)]:self.event_fault(tag,off,mask,crc)
  self.setup(baseline=False);self.unchanged_failure('unread-SPLICE-before-REKEY',0,2)
  self.setup();self.pending(3);f.put('se_r_revision',f.get('se_r_revision',4)+1,4);self.unchanged_failure('source-revision-across-yield')
  self.setup();self.pending(3);idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==14 and f.m.read(f.s['image_slot']+i)&1==0);f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active'],0);self.unchanged_failure('missing-R14-during-owned-lease',expected=0x17)
  self.setup();self.pending(3);idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==38 and f.m.read(f.s['image_slot']+i)&1==1);f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active']+1,0);before=self.g.reu();queue=self.unread();stable=self.g.stable();f.put('se_e_job',11,1);f.m.load(0x9135,bytes((38,1)));f.call('se_editor_service');assert f.get('se_e_error',1)==0x17 and not any(f.get(n,1)for n in ('se_doc_read_locks','se_f_owner','se_e_job'))and not f.get('se_bc_flags',1)&8 and self.g.reu()==before and self.unread()==queue and self.g.stable()==stable;self.faults.append(dict(tag='missing-C38-resident-cleanup',a=0x17));print('FAULT PASS missing-C38',flush=True)
  self.setup();self.pending(3);f.put('se_e_job',11,1);f.m.load(0x9135,bytes((38,1)));f.queued(observer.Q);tail=f.get('se_input_tail',1);f.call('se_editor_service');assert f.get('se_input_tail',1)==tail and not f.get('se_doc_read_locks',1)and not f.get('se_bc_flags',1)&8 and self.unread()==self.queue;f.put('se_status',1,1);f.tick();f.settle();assert f.get('se_bc_count',1)==2;f.put('se_f_owner',4,1);self.unchanged_failure('queued-edit-cancels-then-unread-SPLICE-refuses',0,2)
  self.setup();frame=f.read(F,576);reu=self.g.reu()
  for owner in (0,1,2,3,5,255):
   f.put('se_f_owner',owner,1)
   for op in (0,1,2):r=self.invoke(op);assert r.p&1 and r.a==0xB2 and f.read(F,576)==frame and self.g.reu()==reu
  f.put('se_f_owner',4,1);self.faults.append(dict(tag='sixforeignowners-threeops',calls=18))
  self.setup();f.put('se_render_caps',0,1);frame=f.read(F,576);self.unchanged_failure('Plain-before-phase',0,2);assert f.read(F,576)==frame
 def close(self):self.f.close()

def run(out,base,smoke=False):
 t=Test(out,base)
 try:
  t.positive('insert')
  if not smoke:
   t.positive('netzero',zero=True);t.positive('ring-slot1',slot=1);t.positive('ring-slot2',slot=2);t.positive('above64KiB',data=b'A'*65530+observer.geos.native_text('\rTail ordinary text.'),at=65535,high=True);t.run_faults()
  result=dict(status='PASS',budget=t.budget,positives=t.positives,faults=t.faults,peak_bridge_call=max(c['instructions']for p in t.positives for c in p['calls']),scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('REKEY PASS',len(t.positives),len(t.faults),flush=True)
 except BaseException as e:
  (out/'failure.json').write_text(json.dumps(dict(error=repr(e),calls=t.calls,positives=t.positives,faults=t.faults),indent=2)+'\n');(out/'failure-ram.bin').write_bytes(t.f.read(0,65536));raise
 finally:t.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/cache-rekey'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture,a.smoke)
