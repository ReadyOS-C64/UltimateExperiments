"""Range reference-splice producer conservation and scheduler continuation."""
import json
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from engine_test_profile import Profile
profile=Profile('clipboard-probe','refs')
r=profile.report;s=r['symbols']
result_path=profile.result_path;result_path.unlink(missing_ok=True)
m=Machine()
max_read_instructions=0
def read(a,n):return bytes(m.read(a+i) for i in range(n))
def put(n,v,w=3):m.load(s[n],v.to_bytes(w,'little'))
def call(n,a=0,x=0,y=0,error=None):
 global max_read_instructions
 regs,instructions=m.call(s[n],a=a,x=x,y=y,limit=5_000_000 if n=='se_doc_read' else 1_000_000)
 if n=='se_doc_read':max_read_instructions=max(max_read_instructions,instructions)
 assert bool(regs.p&1)==(error is not None),(n,hex(regs.a),regs.p)
 if error is not None:assert regs.a==error,(n,hex(regs.a),error)
 return regs

def token(n):return read(s[n],5)
def write_obj(t,offset,data):
 m.load(s['se_object_id'],t);m.load(0x8000,data);put('se_object_offset',offset)
 put('se_object_length',len(data),2);put('se_object_c64',0x8000,2);call('se_object_copy',a=0)
def load(t,data):
 for i in range(0,len(data),1024):write_obj(t,i,data[i:i+1024])
def resize(t,length):m.load(s['se_object_id'],t);put('se_object_offset',length);call('se_object_resize')
def setup(data,banks=2):
 put('se_reu_banks',256,2);call('se_reu_provider_init');call('se_object_init');call('se_doc_init',a=banks)
 load(token('se_doc_original'),data);put('se_doc_source_length',len(data));call('se_doc_adopt_original');profile.import_engine(m,s)
 call('se_object_create',a=6,x=1);j=token('se_object_id');resize(j,65536);return j

def doc_read(offset,count):
 put('se_doc_offset',offset);put('se_doc_count',count,2);put('se_doc_c64',0x8000,2);call('se_doc_read');return read(0x8000,count)
def document(n):return b''.join(doc_read(i,min(1024,n-i)) for i in range(0,n,1024))
def published():
 app=token('se_doc_append')[0]
 return read(s['se_doc_roots'],256)+read(s['se_doc_length'],3)+read(s['se_doc_generation'],2)+bytes(m.read(s[n]+app) for n in ['object_size_lo','object_size_mid','object_size_hi'])
def record(t,offset,length):return t[:3]+offset.to_bytes(3,'little')+length.to_bytes(3,'little')
def refs(j,pos,delete,records,length,old,expected,error=None):
 body=b''.join(records)
 for i in range(0,len(body),1024):write_obj(j,0xB800+i,body[i:i+1024])
 put('se_doc_edit_position',pos);put('se_doc_edit_delete',delete);put('se_doc_edit_insert',length)
 m.load(s['se_doc_refs_token'],j);put('se_doc_refs_offset',0xB800);put('se_doc_refs_pieces',len(records),2)
 before=published();call('se_doc_splice_refs_begin');steps=0
 if m.read(s['se_doc_busy']):call('se_doc_splice_feed',error=0x41)
 while m.read(s['se_doc_busy']):
  regs,_=m.call(s['se_doc_splice_step']);steps+=1;assert steps<600
  if regs.p&1:
   assert error is not None and regs.a==error,(hex(regs.a),error)
   assert published()==before and not m.read(s['se_doc_busy']);return steps
  if regs.a==1:
   assert published()==before
   if old and steps%3==0:
    at=(steps*83)%len(old);assert doc_read(at,min(29,len(old)-at))==old[at:at+29]
 assert error is None and published()[-3:]==before[-3:]
 assert document(len(expected))==expected
 return steps

def byte_splice(old,pos,delete,data):
 put('se_doc_edit_position',pos);put('se_doc_edit_delete',delete);put('se_doc_edit_insert',len(data));call('se_doc_splice_begin')
 for i in range(0,len(data),1024):
  chunk=data[i:i+1024];m.load(0x8000,chunk);put('se_doc_count',len(chunk),2);put('se_doc_c64',0x8000,2);call('se_doc_splice_feed')
 while m.read(s['se_doc_busy']):call('se_doc_splice_step')
 return old[:pos]+data+old[pos+delete:]
try:
 image=profile.image;m.load(0x0801,image[2:]);m.call(s['se_clear_state'])
 shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim)
 rng=random.Random(0x524546)
 original=rng.randbytes(17000);j=setup(original);orig=token('se_doc_original')
 model=original
 # Insert many references in the middle of one old piece, with interleaved
 # reads. Saved old boundary descriptor must survive packet decoding.
 data=b''.join(original[i*31:i*31+7] for i in range(40))
 records=[record(orig,i*31,7) for i in range(40)]
 steps=refs(j,500,33,records,len(data),model,model[:500]+data+model[533:])
 model=model[:500]+data+model[533:];assert steps>=7
 for case in range(100):
  pos=rng.randrange(len(model)+1);delete=rng.randrange(min(60,len(model)-pos)+1)
  records=[];data=b''
  for _ in range(rng.randrange(1,19)):
   at=rng.randrange(len(original)-25);length=rng.randrange(1,26)
   records.append(record(orig,at,length));data+=original[at:at+length]
  expected=model[:pos]+data+model[pos+delete:]
  refs(j,pos,delete,records,len(data),model,expected);model=expected
 refs(j,0,100,[],0,model,model[100:]);model=model[100:]
 # Existing operation mode must survive a rejected nested begin.
 put('se_doc_edit_position',0);put('se_doc_edit_delete',0);put('se_doc_edit_insert',1);call('se_doc_splice_begin')
 call('se_doc_splice_refs_begin',error=0x41)
 m.load(0x8000,b'Q');put('se_doc_count',1,2);put('se_doc_c64',0x8000,2);call('se_doc_splice_feed')
 while m.read(s['se_doc_busy']):call('se_doc_splice_step')
 model=b'Q'+model;assert document(len(model))==model
 # Wrong reference totals and last-source corruption cannot publish.
 refs(j,5,1,[record(orig,0,3)],2,model,model,error=0x42)
 refs(j,5,1,[record(orig,0,3)],4,model,model,error=0x42)
 bad=[record(orig,i*7,3) for i in range(70)];bad[-1]=b'\xff'+bad[-1][1:]
 refs(j,0,0,bad,210,model,model,error=0x42)
 # Replacement at the1MiB ceiling with completely full append storage.
 original=rng.randbytes(1048576);j=setup(original,banks=16);orig=token('se_doc_original')
 model=byte_splice(original,0,len(original),rng.randbytes(1048576))
 before=published();assert before[-3:]==(1048576).to_bytes(3,'little')
 data=original[500000:570001]
 expected=model[:65530]+data+model[135531:]
 refs(j,65530,70001,[record(orig,500000,70001)],70001,model,expected);model=expected
 assert len(model)==1048576
 # Empty document and EOF insert use the same resumable reference engine.
 refs(j,0,len(model),[],0,model,b'');model=b''
 refs(j,0,0,[record(orig,0,100)],100,model,original[:100]);model=original[:100]
 #2048 packed records land exactly at the journal bank end. Late corruption
 #after31 candidate leaves cannot publish or grow the already full append.
 records=[record(orig,0,1) for _ in range(2048)];expected=original[:1]*2048
 refs(j,0,len(model),records,2048,model,expected);model=expected
 bad=records.copy();bad[-1]=b'\xff'+bad[-1][1:]
 refs(j,0,len(model),bad,2048,model,model,error=0x42)
 assert document(len(model))==model
 # Packed bank end and capacity admission.
 put('se_doc_refs_pieces',2049,2);call('se_doc_splice_refs_begin',error=0x43)
 assert read(0xC600,1024)==shim
 result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=r['sha256'],
  randomized_reference_splices=100,packet_continuation=True,full_append_bytes=1048576,
  range_replacement_bytes=70001,malformed_total_and_source_rollback=True,
  rejected_begin_preserves_active_mode=True,packed_records=2048,exact_journal_bank_end=True,
  late_record_rollback=True,max_read_instructions=max_read_instructions,shim_bytes_verified=1024)
 result.update(profile.identity);result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:m.close()
