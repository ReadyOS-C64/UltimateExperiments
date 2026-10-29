"""Local immutable-leaf reuse, reference continuation and full-repack fallback."""
import json
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from engine_test_profile import Profile
profile=Profile('clipboard-probe','local')
r=profile.report;s=r['symbols']
result_path=profile.result_path;result_path.unlink(missing_ok=True)
m=Machine()
def read(a,n):return bytes(m.read(a+i) for i in range(n))
def put(n,v,w=3):m.load(s[n],v.to_bytes(w,'little'))
def get(n,w=3):return int.from_bytes(read(s[n],w),'little')
def call(n,a=0,x=0,y=0,error=None):
 regs,instructions=m.call(s[n],a=a,x=x,y=y)
 assert bool(regs.p&1)==(error is not None),(n,hex(regs.a),regs.p)
 if error is not None:assert regs.a==error,(n,hex(regs.a),error)
 return regs

def token(n):return read(s[n],5)
def obj_write(t,offset,data,host=0x8000):
 m.load(s['se_object_id'],t);m.load(host,data);put('se_object_offset',offset)
 put('se_object_length',len(data),2);put('se_object_c64',host,2);call('se_object_copy',a=0)
def load(t,data):
 for i in range(0,len(data),1024):obj_write(t,i,data[i:i+1024])
def resize(t,length):m.load(s['se_object_id'],t);put('se_object_offset',length);call('se_object_resize')
def doc_read(offset,count):
 put('se_doc_offset',offset);put('se_doc_count',count,2);put('se_doc_c64',0x8000,2);call('se_doc_read');return read(0x8000,count)
def document(n):return b''.join(doc_read(i,min(1024,n-i)) for i in range(0,n,1024))
def published():
 app=token('se_doc_append')[0]
 return read(s['se_doc_roots'],256)+read(s['se_doc_length'],3)+read(s['se_doc_generation'],2)+bytes([get('se_doc_root_count',1)])+bytes(m.read(s[n]+app) for n in ['object_size_lo','object_size_mid','object_size_hi'])
def setup(pieces=2000,per_leaf=64):
 put('se_reu_banks',256,2);call('se_reu_provider_init');call('se_object_init');call('se_doc_init',a=2)
 original=bytes((i*37+11)&255 for i in range(32768));added=bytes((i*51+97)&255 for i in range(32768))
 orig=token('se_doc_original');app=token('se_doc_append');meta=token('se_doc_meta')
 load(orig,original);put('se_doc_source_length',len(original));call('se_doc_adopt_original');profile.import_engine(m,s)
 load(app,added);resize(app,len(added))
 roots=bytearray();model=bytearray();old_leaves=[]
 for page,start in enumerate(range(0,pieces,per_leaf)):
  count=min(per_leaf,pieces-start);leaf=bytearray(1024)
  for record in range(count):
   index=start+record;source=orig if index%2==0 else app;data=original if index%2==0 else added
   offset=(index*17)%(len(data)-8);at=record*16
   leaf[at:at+3]=source[:3];leaf[at+3:at+6]=offset.to_bytes(3,'little');leaf[at+6:at+9]=(8).to_bytes(3,'little');leaf[at+9:at+12]=b'\xff'*3
   model.extend(data[offset:offset+8])
  slot=63-2*page;obj_write(meta,slot*1024,leaf,host=0x8400);old_leaves.append((slot,bytes(leaf)))
  roots.extend(bytes([slot,count])+(count*8).to_bytes(3,'little')+b'\xff'*3)
 m.load(s['se_doc_roots'],roots+bytes(256-len(roots)));put('se_doc_root_count',len(old_leaves),1)
 put('se_doc_length',len(model));put('se_doc_generation',3,2);call('se_doc_invalidate')
 # Establish full integrity before using the trusted local path.
 m.call(s['se_doc_walk_reset']);count=0
 while True:
  regs,_=m.call(s['se_doc_walk_next'])
  if regs.p&1:assert regs.a==0;break
  count+=1
 assert count==pieces and document(len(model))==model
 return bytes(model),old_leaves

def request(pos,delete,length):
 put('se_doc_edit_position',pos);put('se_doc_edit_delete',delete);put('se_doc_edit_insert',length)
def feed(data):
 for i in range(0,len(data),1024):
  chunk=data[i:i+1024];m.load(0x8000,chunk);put('se_doc_count',len(chunk),2);put('se_doc_c64',0x8000,2);call('se_doc_splice_feed')
def finish(before,old,error=None):
 steps=0;instructions=0
 while get('se_doc_busy',1):
  regs,used=m.call(s['se_doc_splice_step']);steps+=1;instructions+=used;assert steps<650
  if regs.p&1:
   assert error is not None and regs.a==error,(hex(regs.a),error)
   assert published()==before and get('se_doc_busy',1)==0
   return steps,instructions
  if regs.a==1:
   assert published()==before
   if old and steps%3==0:
    at=(steps*83)%len(old);assert doc_read(at,min(29,len(old)-at))==old[at:at+29]
 assert error is None
 return steps,instructions

def edit(model,pos,delete,data,local=True,error=None):
 before=published();request(pos,delete,len(data));regs=call('se_doc_splice_local_begin' if local else 'se_doc_splice_begin')
 if regs.a==0:assert delete==0 and not data;return model,0,0
 feed(data);put('se_reu_dma_calls',0,2);put('se_reu_dma_bytes',0)
 steps,instructions=finish(before,model,error)
 dma=get('se_reu_dma_bytes')
 if error is not None:return model,steps,dma
 expected=model[:pos]+data+model[pos+delete:];assert document(len(expected))==expected
 return expected,steps,dma

def refs(model,pos,delete,body,length,error=None):
 call('se_object_create',a=6,x=1);j=token('se_object_id');resize(j,65536)
 for i in range(0,len(body),1024):obj_write(j,0xB800+i,body[i:i+1024])
 before=published();request(pos,delete,length);m.load(s['se_doc_refs_token'],j);put('se_doc_refs_offset',0xB800);put('se_doc_refs_pieces',len(body)//9,2)
 call('se_doc_splice_local_refs_begin');call('se_doc_splice_feed',error=0x41)
 steps,_=finish(before,model,error)
 m.load(s['se_object_id'],j);call('se_object_release')
 return steps

def record(t,offset,length):return t[:3]+offset.to_bytes(3,'little')+length.to_bytes(3,'little')
try:
 image=profile.image;m.load(0x0801,image[2:]);m.call(s['se_clear_state'])
 shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim)
 model,_=setup();full_model,full_steps,full_dma=edit(model,8000,8,b'REPLACE!',local=False)
 model,leaves=setup();local_model,local_steps,local_dma=edit(model,8000,8,b'REPLACE!')
 assert full_model==local_model and local_steps<full_steps//8,(local_steps,full_steps)
 assert get('se_doc_reused_roots',1)==31
 assert local_dma<full_dma//4,(local_dma,full_dma)
 old_slots={slot for slot,_ in leaves};new_slots={m.read(s['se_doc_roots']+i*8) for i in range(get('se_doc_root_count',1))}
 assert len(old_slots&new_slots)==31
 # Reused leaves are immutable, as is the replaced old leaf.
 meta=token('se_doc_meta')
 for slot,leaf in leaves:
  m.load(s['se_object_id'],meta);put('se_object_offset',slot*1024);put('se_object_length',1024,2);put('se_object_c64',0x8400,2);call('se_object_copy',a=1)
  assert read(0x8400,1024)==leaf
 print(f"2000-piece edit: full {full_steps} slices/{full_dma} DMA bytes, local {local_steps} slices/{local_dma} DMA bytes",flush=True)
 model,_=setup(512)
 # Local append coalesces sequential typing while other roots remain shared.
 for i in range(120):model,_,_=edit(model,1000+i,0,bytes([65+i%26]))
 # Rejected nested full/ref begins cannot silently disable current local mode.
 request(700,8,8);before=published();call('se_doc_splice_local_begin');assert get('tx_local_mode',1)==1
 call('se_doc_splice_begin',error=0x41);call('se_doc_splice_refs_begin',error=0x41)
 assert get('tx_local_mode',1)==1;feed(b'preserve');finish(before,model);model=model[:700]+b'preserve'+model[708:]
 assert document(len(model))==model
 print("Sequential typing and nested admission passed",flush=True)
 # A full affected leaf splits into two local leaves:32 roots would become33.
 # Global packing still fits2002 pieces, so restart instead of false rejection.
 model,_=setup();model,fallback_steps,_=edit(model,8001,0,b'fallback')
 assert get('tx_local_mode',1)==0 and get('se_doc_reused_roots',1)==0
 assert get('se_doc_root_count',1)==32
 # Reference packets must rewind too: fallback happens after all100 refs were
 # consumed once; repeat from private saved request without append growth.
 model,_=setup(32,1);orig=token('se_doc_original');before_append=published()[-3:]
 records=[record(orig,i*11,3) for i in range(100)]
 original=bytes((i*37+11)&255 for i in range(32768));data=b''.join(original[i*11:i*11+3] for i in range(100))
 ref_steps=refs(model,249,0,b''.join(records),len(data))
 expected=model[:249]+data+model[249:]
 assert document(len(expected))==expected and published()[-3:]==before_append
 assert get('tx_local_mode',1)==0 and ref_steps>20
 model=expected
 print("Byte and100-reference local repack fallback passed",flush=True)
 # Random local edits exercise roots with many partial pages and repeated
 # repacking. Compare actual bytes after every publication.
 model,_=setup(512);rng=random.Random(0x4C4F434C);fallbacks=0
 for _ in range(200):
  pos=rng.randrange(len(model)+1);delete=rng.randrange(min(40,len(model)-pos)+1);data=rng.randbytes(rng.randrange(30))
  model,_,_=edit(model,pos,delete,data)
  fallbacks+=get('tx_local_mode',1)==0
 # Cancellation after shared roots have been emitted preserves canonical state.
 before=published();request(len(model)-8,8,8);call('se_doc_splice_local_begin');feed(b'cancelme')
 for _ in range(2):assert call('se_doc_splice_step').a==1
 call('se_doc_splice_cancel');assert published()==before and document(len(model))==model
 # Integrity failures in the affected leaf still abort before publication.
 model,leaves=setup();slot=leaves[15][0];bad=bytearray(leaves[15][1]);bad[63*16+12]=1
 obj_write(token('se_doc_meta'),slot*1024,bad,host=0x8400);call('se_doc_invalidate')
 _,_,_=edit(model,15*512,8,b'badpiece',error=0x42)
 # Invalid reused root sums detected without touching the leaf data.
 model,_=setup();m.load(s['se_doc_roots']+2,b'\xff\xff\xff');before=published();request(8000,8,8);call('se_doc_splice_local_begin');feed(b'badroots')
 finish(before,model,error=0x42)
 # True fragment exhaustion must still fail after the one local-to-full retry.
 model,_=setup(2048);_,capacity_steps,_=edit(model,1,0,b'X',error=0x43)
 assert capacity_steps>257 and document(len(model))==model
 assert read(0xC600,1024)==shim
 result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=r['sha256'],canonical_pieces=2000,
  full_repack_steps=full_steps,local_steps=local_steps,full_dma_bytes_including_interleaved_reads=full_dma,
  local_dma_bytes_including_interleaved_reads=local_dma,reused_roots=31,sequential_typing=120,
  randomized_local_edits=200,random_repack_fallbacks=fallbacks,byte_repack_steps=fallback_steps,
  reference_repack_steps=ref_steps,reference_rewind=True,affected_corruption_rollback=True,
  true_capacity_rollback_steps=capacity_steps,
  shim_bytes_verified=1024,timing='Work slices and DMA counts; not normal-clock cycles or frames')
 result.update(profile.identity);result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:m.close()
