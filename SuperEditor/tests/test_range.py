"""Selected immutable-reference capture for future bounded delta history."""
import json
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
r=json.loads((ROOT/'build/range-probe-report.json').read_text());s=r['symbols']
result_path=ROOT/'build/range-test-result.json';result_path.unlink(missing_ok=True)
m=Machine();maximum_step=0;maximum_dma=0

def read(a,n):return bytes(m.read(a+i) for i in range(n))
def put(n,v,w=3):m.load(s[n],v.to_bytes(w,'little'))
def get(n,w=3):return int.from_bytes(read(s[n],w),'little')
def call(n,a=0,x=0,y=0,error=None):
 global maximum_step,maximum_dma
 before=get('se_reu_dma_calls',2);regs,used=m.call(s[n],a=a,x=x,y=y)
 assert bool(regs.p&1)==(error is not None),(n,hex(regs.a),regs.p)
 if error is not None:assert regs.a==error,(n,hex(regs.a),error)
 if n=='se_range_step':
  maximum_step=max(maximum_step,used);maximum_dma=max(maximum_dma,(get('se_reu_dma_calls',2)-before)&65535)
 return regs

def token(n):return read(s[n],5)
def obj_write(t,offset,data,host=0x8000):
 m.load(s['se_object_id'],t);m.load(host,data);put('se_object_offset',offset);put('se_object_length',len(data),2);put('se_object_c64',host,2);call('se_object_copy',a=0)
def obj_read(t,offset,length):
 out=bytearray()
 for i in range(0,length,1024):
  count=min(1024,length-i);m.load(s['se_object_id'],t);put('se_object_offset',offset+i);put('se_object_length',count,2);put('se_object_c64',0x8000,2);call('se_object_copy',a=1);out.extend(read(0x8000,count))
 return bytes(out)
def resize(t,n):m.load(s['se_object_id'],t);put('se_object_offset',n);call('se_object_resize')
def load(t,data):
 for i in range(0,len(data),4096):obj_write(t,i,data[i:i+4096])
def published():return read(s['se_doc_roots'],256)+read(s['se_doc_length'],3)+read(s['se_doc_generation'],2)+read(s['se_doc_root_count'],1)
def request(j,start,length,offset=0xB800):
 m.load(s['se_range_token'],j);put('se_range_offset',offset);put('se_range_position',start);put('se_range_length',length)
def capture(j,start,length,offset=0xB800,error=None):
 global maximum_step,maximum_dma
 request(j,start,length,offset);before=published();req=read(s['se_range_token'],14);started=call('se_range_begin').a;steps=0
 if not length:
  assert started==0 and get('se_range_pieces',2)==0 and get('se_range_bytes',2)==0
  return b'',0
 assert started==1 and get('se_snapshot_busy',1)==2 and get('se_doc_read_locks',1)==1
 while get('se_snapshot_busy',1):
  old_count=get('se_range_pieces',2);dma_before=get('se_reu_dma_calls',2);regs,used=m.call(s['se_range_step']);steps+=1;assert steps<300
  maximum_step=max(maximum_step,used);maximum_dma=max(maximum_dma,(get('se_reu_dma_calls',2)-dma_before)&65535)
  if regs.p&1:
   assert error is not None and regs.a==error,(hex(regs.a),error)
   assert published()==before and get('se_snapshot_busy',1)==0 and get('se_doc_read_locks',1)==0
   return b'',steps
  assert get('se_range_pieces',2)-old_count<=8
  if regs.a==1:
   assert published()==before
   at=(steps*107)%get('se_doc_length');put('se_doc_offset',at);put('se_doc_count',1,2);put('se_doc_c64',0x8000,2);call('se_doc_read')
 assert error is None and published()==before and get('se_doc_read_locks',1)==0 and read(s['se_range_token'],14)==req
 packed=obj_read(j,offset,get('se_range_bytes',2));assert len(packed)==get('se_range_pieces',2)*9
 return packed,steps

def packed_expected(pieces,start,length):
 result=bytearray();pos=0;end=start+length
 for t,offset,count in pieces:
  left=max(pos,start);right=min(pos+count,end)
  if left<right:result.extend(t[:3]+(offset+left-pos).to_bytes(3,'little')+(right-left).to_bytes(3,'little'))
  pos+=count
 return bytes(result)
try:
 m.load(0x801,(ROOT/'build/range-probe.prg').read_bytes()[2:]);m.call(s['se_clear_state'])
 shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim)
 put('se_reu_banks',256,2);call('se_reu_provider_init');call('se_object_init');call('se_doc_init',a=16)
 rng=random.Random(0x52414E47);orig_data=rng.randbytes(1048576);app_data=rng.randbytes(1048576)
 orig=token('se_doc_original');app=token('se_doc_append');meta=token('se_doc_meta')
 load(orig,orig_data);put('se_doc_source_length',len(orig_data));call('se_doc_adopt_original');load(app,app_data);resize(app,len(app_data))
 call('se_object_create',a=6,x=1);journal=token('se_object_id');resize(journal,65536)
 pieces=[];roots=bytearray();leaves=[]
 for page in range(32):
  leaf=bytearray(1024)
  for rec in range(64):
   index=page*64+rec;t=orig if index%2==0 else app;offset=(index*65537+65500)%(1048576-512+1)
   pieces.append((t,offset,512));at=rec*16;leaf[at:at+3]=t[:3];leaf[at+3:at+6]=offset.to_bytes(3,'little');leaf[at+6:at+9]=(512).to_bytes(3,'little');leaf[at+9:at+12]=b'\xff'*3
  slot=63-page*2;obj_write(meta,slot*1024,leaf,host=0x8400);leaves.append(bytes(leaf));roots.extend(bytes([slot,64])+(32768).to_bytes(3,'little')+b'\xff'*3)
 m.load(s['se_doc_roots'],roots);put('se_doc_root_count',32,1);put('se_doc_length',1048576);put('se_doc_generation',3,2);m.call(s['se_doc_invalidate'])
 for _ in range(150):
  start=rng.randrange(1048577);length=rng.randrange(min(70000,1048576-start)+1)
  actual,steps=capture(journal,start,length);assert actual==packed_expected(pieces,start,length)
 # Full original/append quota is irrelevant: capture stores references only.
 packed,full_steps=capture(journal,0,1048576)
 assert packed==packed_expected(pieces,0,1048576) and len(packed)==18432 and full_steps==256
 # Small near-EOF capture skips whole roots rather than walking1984+ pieces.
 actual,tail_steps=capture(journal,1048575,1,65527);assert actual==packed_expected(pieces,1048575,1) and tail_steps<=12
 # Exactly one record fits at FFF7; two do not. Destination capacity may exceed
 # committed size, so the capture must check the latter before any stash.
 actual,_=capture(journal,511,2,65527,error=0x32)
 resize(journal,20);actual,_=capture(journal,511,2,9,error=0x32);resize(journal,65536)
 # Shared private walker ownership: full and range capture cannot cross-step
 # or cancel one another. Byte reads remain legal while either holds a lease.
 request(journal,123,10000);call('se_range_begin');locks=get('se_doc_read_locks',1)
 call('se_range_begin',error=0x41);call('se_snapshot_begin',error=0x41);call('se_snapshot_step',error=0x40);call('se_snapshot_cancel',error=0x41)
 assert get('se_snapshot_busy',1)==2 and get('se_doc_read_locks',1)==locks
 call('se_range_cancel');m.load(s['se_snapshot_token'],journal);put('se_snapshot_offset',0);call('se_snapshot_begin')
 call('se_range_begin',error=0x41);call('se_range_step',error=0x40);call('se_range_cancel',error=0x41)
 assert get('se_snapshot_busy',1)==1 and get('se_doc_read_locks',1)==1
 call('se_snapshot_cancel')
 # Cancellation and late source error preserve publication, leases and all
 # allocations. Idle cancellation must not cancel an unrelated writer.
 before=published();request(journal,0,1048576);call('se_range_begin')
 for _ in range(10):call('se_range_step')
 call('se_range_cancel');assert published()==before and get('se_doc_read_locks',1)==0
 put('se_doc_edit_position',0);put('se_doc_edit_delete',1);put('se_doc_edit_insert',0);call('se_doc_splice_begin')
 call('se_range_cancel');assert get('se_doc_busy',1)==1;call('se_doc_splice_cancel')
 request(journal,0,1048576);call('se_range_begin');call('se_range_step')
 bad=bytearray(leaves[-1]);bad[63*16+1:63*16+3]=b'\xff\xff';obj_write(meta,1024,bad,host=0x8400);m.call(s['se_doc_invalidate'])
 error_steps=1
 while get('se_snapshot_busy',1):
  regs,_=m.call(s['se_range_step']);error_steps+=1
  if regs.p&1:assert regs.a==0x31;break
 assert error_steps==256 and published()==before and get('se_doc_read_locks',1)==0
 obj_write(meta,1024,leaves[-1],host=0x8400);m.call(s['se_doc_invalidate'])
 # Generation drift is reported and clears only the owned lease.
 request(journal,0,1234);call('se_range_begin');put('se_doc_generation',4,2);call('se_range_step',error=0x52);put('se_doc_generation',3,2)
 assert get('se_doc_read_locks',1)==0
 # Explicitly measure bounded work, independently of the convenience loop.
 request(journal,31*32768+511,1000);call('se_range_begin')
 while get('se_snapshot_busy',1):call('se_range_step')
 for start,length,offset,error in [(1048577,0,0,0x32),(0xFFFFFF,1,0,0x32),(0,1,65537,0x32)]:
  request(journal,start,length,offset);call('se_range_begin',error=error)
 request(orig,0,1,0);call('se_range_begin',error=0x42)
 assert get('se_doc_read_locks',1)==0 and read(0xC600,1024)==shim
 assert maximum_step<30000 and maximum_dma<=3
 result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=r['sha256'],randomized_ranges=150,
  source_document_bytes=1048576,source_extents=16,packed_records=2048,packed_bytes=18432,
  full_capture_steps=full_steps,tail_capture_steps=tail_steps,late_source_error_steps=error_steps,
  max_sampled_step_instructions=maximum_step,max_sampled_step_dmas=maximum_dma,full_append_storage=True,
  exact_journal_bank_end=True,committed_journal_bounds=True,cross_capture_guards=True,
  publication_and_leases_preserved=True,shim_bytes_verified=1024,
  limitations='Range capture building block; history CRC/stack/controller and user undo still pending.')
 result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:m.close()
