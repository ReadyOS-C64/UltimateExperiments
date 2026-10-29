"""Bounded piece reads and clipboard slices over pathological fragmentation."""
import json
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
r=json.loads((ROOT/'build/clipboard-probe-report.json').read_text());s=r['symbols']
result_path=ROOT/'build/read-some-test-result.json';result_path.unlink(missing_ok=True)
m=Machine();max_some=0;max_copy=0;max_full=0

def read(a,n):return bytes(m.read(a+i) for i in range(n))
def put(n,v,w=3):m.load(s[n],v.to_bytes(w,'little'))
def get(n,w=3):return int.from_bytes(read(s[n],w),'little')
def call(n,a=0,x=0,y=0,error=None):
 global max_some,max_copy,max_full
 regs,used=m.call(s[n],a=a,x=x,y=y,limit=5_000_000 if n=='se_doc_read' else 1_000_000)
 assert bool(regs.p&1)==(error is not None),(n,hex(regs.a),regs.p)
 if error is not None:assert regs.a==error,(n,hex(regs.a),error)
 if n=='se_doc_read_some':max_some=max(max_some,used)
 if n=='se_clip_copy_step':max_copy=max(max_copy,used)
 if n=='se_doc_read':max_full=max(max_full,used)
 return regs

def token(n):return read(s[n],5)
def obj_write(t,offset,data,host=0x8000):
 m.load(s['se_object_id'],t);m.load(host,data);put('se_object_offset',offset)
 put('se_object_length',len(data),2);put('se_object_c64',host,2);call('se_object_copy',a=0)
def load(t,data):
 for i in range(0,len(data),4096):obj_write(t,i,data[i:i+4096])
def obj_read(t,offset,count):
 m.load(s['se_object_id'],t);put('se_object_offset',offset);put('se_object_length',count,2);put('se_object_c64',0x8000,2)
 call('se_object_copy',a=1);return read(0x8000,count)
def resize(t,length):m.load(s['se_object_id'],t);put('se_object_offset',length);call('se_object_resize')
def doc_request(offset,count,host=0x8000):put('se_doc_offset',offset);put('se_doc_count',count,2);put('se_doc_c64',host,2)
def doc_read(offset,count):doc_request(offset,count);call('se_doc_read');assert get('se_doc_read_done',2)==count;return read(0x8000,count)
def published():return read(s['se_doc_roots'],256)+read(s['se_doc_length'],3)+read(s['se_doc_generation'],2)
def clip_published():return token('se_clip_token')+read(s['se_clip_length'],3)+read(s['se_clip_generation'],2)+read(s['se_clip_active'],1)

try:
 image=(ROOT/'build/clipboard-probe.prg').read_bytes();m.load(0x801,image[2:]);m.call(s['se_clear_state'])
 shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim)
 put('se_reu_banks',256,2);call('se_reu_provider_init');call('se_object_init');call('se_doc_init',a=16);call('se_clip_init')
 rng=random.Random(0x5244534D);orig_data=rng.randbytes(1048576);app_data=rng.randbytes(1048576)
 orig=token('se_doc_original');app=token('se_doc_append');meta=token('se_doc_meta')
 load(orig,orig_data);put('se_doc_source_length',len(orig_data));call('se_doc_adopt_original')
 load(app,app_data);resize(app,len(app_data))
 def fixture(lengths):
  roots=bytearray();model=bytearray();leaves=[]
  for page in range(32):
   leaf=bytearray(1024);total=0
   for rec in range(64):
    index=page*64+rec;length=lengths[index];source=orig if index%2==0 else app;data=orig_data if index%2==0 else app_data
    offset=(index*65537+65535)%(len(data)-length+1)
    at=rec*16;leaf[at:at+3]=source[:3];leaf[at+3:at+6]=offset.to_bytes(3,'little');leaf[at+6:at+9]=length.to_bytes(3,'little');leaf[at+9:at+12]=b'\xff'*3
    model.extend(data[offset:offset+length]);total+=length
   slot=63-2*page;obj_write(meta,slot*1024,leaf,host=0x8400);leaves.append(bytes(leaf))
   roots.extend(bytes([slot,64])+total.to_bytes(3,'little')+b'\xff'*3)
  m.load(s['se_doc_roots'],roots);put('se_doc_root_count',32,1);put('se_doc_length',len(model));put('se_doc_generation',get('se_doc_generation',2)+1,2);m.call(s['se_doc_invalidate'])
  return bytes(model),bytes(roots),leaves
 model,roots,leaves=fixture([1]*2048);before=published()
 assert doc_read(0,1024)==model[:1024]
 fragmented_full_instructions=max_full
 at=0;slices=0
 while at<len(model):
  count=min(1024,len(model)-at);doc_request(at,count);req=read(s['se_doc_offset'],7)
  # Sentinels around an unaligned output range; only actual bytes may change.
  m.load(0x8000,b'\xcc'*1024);put('se_doc_c64',0x8001,2);count=min(count,1023);put('se_doc_count',count,2);req=read(s['se_doc_offset'],7)
  regs=call('se_doc_read_some');done=get('se_doc_read_done',2)
  assert done==min(8,count) and regs.a==(1 if done<count else 0)
  assert read(s['se_doc_offset'],7)==req and published()==before
  assert read(0x8001,done)==model[at:at+done] and m.read(0x8000)==0xCC
  assert read(0x8001+done,1023-done)==b'\xcc'*(1023-done)
  at+=done;slices+=1
  # Deliberately evict the leaf. No pointer/state is retained between calls.
  assert doc_read(2047,1)==model[-1:]
 assert slices==256
 # Zero/range/buffer errors clear output count and perform no DMA.
 for offset,count,host,error in [(0,0,0x8000,0x36),(0,1025,0x8000,0x33),(2048,1,0x8000,0x32),(0,1,0x8400,0x33)]:
  doc_request(offset,count,host);old=read(s['se_reu_dma_calls'],5);call('se_doc_read_some',error=error)
  assert get('se_doc_read_done',2)==0 and read(s['se_reu_dma_calls'],5)==old
 # Unaligned reads across variable-length pieces, leaves and physical bank ends.
 lengths=[1+(i*17)%37 for i in range(2048)];model,roots,leaves=fixture(lengths)
 starts=[0]
 for length in lengths:starts.append(starts[-1]+length)
 import bisect
 for _ in range(150):
  at=rng.randrange(len(model));count=min(rng.randrange(1,1025),len(model)-at)
  doc_request(at,count);regs=call('se_doc_read_some');done=get('se_doc_read_done',2)
  first=bisect.bisect_right(starts,at)-1;expected=min(count,starts[min(first+8,len(lengths))]-at)
  assert done==expected and regs.a==(1 if done<count else 0)
  assert read(0x8000,done)==model[at:at+done]
 # All pieces2 bytes from$FFFF cross a physical bank boundary independently.
 # Replace the first leaf, whose byte total then becomes128.
 leaf=bytearray(leaves[0]);cross_model=bytearray()
 for index in range(64):
  at=index*16;leaf[at+3:at+6]=(65535).to_bytes(3,'little');leaf[at+6:at+9]=(2).to_bytes(3,'little')
  cross_model.extend((orig_data if index%2==0 else app_data)[65535:65537])
 obj_write(meta,63*1024,leaf,host=0x8400);m.load(s['se_doc_roots']+2,(128).to_bytes(3,'little'));m.call(s['se_doc_invalidate'])
 doc_request(0,32);old_calls=get('se_reu_dma_calls',2);regs=call('se_doc_read_some')
 assert regs.a==1 and get('se_doc_read_done',2)==16 and read(0x8000,16)==cross_model[:16]
 assert (get('se_reu_dma_calls',2)-old_calls)&65535==17 #1 leaf +8 split source copies
 # Root/data disagreement is rejected while advancing within/crossing a leaf.
 model,roots,leaves=fixture([1]*2048);stable=published()
 for root_bytes in [63,65]:
  m.load(s['se_doc_roots']+2,root_bytes.to_bytes(3,'little'));doc_request(60,8)
  call('se_doc_read_some',error=0x42)
  m.load(s['se_doc_roots'],roots)
 # Clipboard publication across256 slices; old private clipboard survives
 # cancel and a malformed later source. Source lease blocks all mutation.
 put('se_clip_position',0);put('se_clip_span',8);call('se_clip_copy_begin');call('se_clip_copy_step')
 old_clip=clip_published();old_token=token('se_clip_token')
 put('se_clip_span',2048);call('se_clip_copy_begin')
 put('se_doc_edit_position',0);put('se_doc_edit_delete',0);put('se_doc_edit_insert',1);call('se_doc_splice_begin',error=0x41)
 steps=0
 while get('se_clip_busy',1):
  regs=call('se_clip_copy_step');steps+=1
  if regs.a==1:
   assert clip_published()==old_clip and get('se_doc_read_locks',1)==1
   assert doc_read(2047,1)==model[-1:]
 assert steps==256 and get('se_doc_read_locks',1)==0
 new_clip=token('se_clip_token');assert new_clip!=old_token
 assert obj_read(new_clip,0,1024)+obj_read(new_clip,1024,1024)==model
 old_clip=clip_published();owners=read(s['se_reu_logical_owner'],512)
 put('se_clip_span',2048);call('se_clip_copy_begin');call('se_clip_copy_step');call('se_clip_copy_cancel')
 assert clip_published()==old_clip and get('se_doc_read_locks',1)==0 and read(s['se_reu_logical_owner'],512)==owners
 put('se_clip_span',2048);call('se_clip_copy_begin');call('se_clip_copy_step')
 bad=bytearray(leaves[0]);bad[8*16+1:8*16+3]=b'\xff\xff';obj_write(meta,63*1024,bad,host=0x8400);m.call(s['se_doc_invalidate'])
 call('se_clip_copy_step',error=0x31)
 assert clip_published()==old_clip and get('se_doc_read_locks',1)==0 and read(s['se_reu_logical_owner'],512)==owners
 obj_write(meta,63*1024,leaves[0],host=0x8400);m.call(s['se_doc_invalidate'])
 assert published()==stable
 assert read(0xC600,1024)==shim
 assert max_some<50000 and max_copy<60000
 assert fragmented_full_instructions<3274184//2
 result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=r['sha256'],pieces=2048,source_extents=16,
  partial_piece_limit=8,one_byte_read_slices=slices,clipboard_copy_slices=steps,random_variable_reads=150,
  cross_bank_source_dmas=16,full_fragmented_read_instructions=fragmented_full_instructions,
  previous_full_fragmented_read_instructions=3274184,max_partial_read_instructions=max_some,max_clipboard_step_instructions=max_copy,
  byte_exact=True,root_sum_errors=True,source_leases_cancel_rollback=True,shim_bytes_verified=1024,
  timing='Instruction counts only; no C64 cycle/frame acceptance')
 result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:m.close()
