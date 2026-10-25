"""Atomic producer edits against Python bytes; interruption/capacity rollback."""
import json
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from engine_test_profile import Profile
profile=Profile('splice-probe','splice')
r=profile.report;s=r['symbols']
result_path=profile.result_path;result_path.unlink(missing_ok=True)
max_step_instructions=0
m=Machine()
def read(address,length):
    return bytes(m.read(address+i) for i in range(length))
def put(name,value,width=3):
    m.load(s[name],value.to_bytes(width,'little'))
def call(name,a=0,x=0,y=0,error=None):
    regs,_=m.call(s[name],a=a,x=x,y=y)
    assert bool(regs.p&1)==(error is not None),(name,hex(regs.a),regs.p)
    if error is not None:assert regs.a==error,(name,hex(regs.a),error)
    return regs

def token(name):return read(s[name],5)
def object_write(t,offset,payload,host=0x8000):
    m.load(s['se_object_id'],t);m.load(host,payload)
    put('se_object_offset',offset);put('se_object_length',len(payload),2);put('se_object_c64',host,2)
    call('se_object_copy',a=0)
def object_size(t,size):
    m.load(s['se_object_id'],t);put('se_object_offset',size);call('se_object_resize')
def load_source(t,data):
    for offset in range(0,len(data),1024):object_write(t,offset,data[offset:offset+1024])
def setup(data,banks=2):
    put('se_reu_banks',256,2);call('se_reu_provider_init');call('se_object_init');call('se_doc_init',a=banks)
    load_source(token('se_doc_original'),data)
    put('se_doc_source_length',len(data));call('se_doc_adopt_original');profile.import_engine(m,s)
def doc_read(offset,length):
    put('se_doc_offset',offset);put('se_doc_count',length,2);put('se_doc_c64',0x8000,2)
    call('se_doc_read');return read(0x8000,length)
def reconstruct(size):
    return b''.join(doc_read(offset,min(1024,size-offset)) for offset in range(0,size,1024))
def published():
    append=token('se_doc_append')[0]
    return (read(s['se_doc_roots'],256),read(s['se_doc_length'],3),
            read(s['se_doc_generation'],2),m.read(s['se_doc_root_count']),
            bytes(m.read(s[name]+append) for name in ['object_size_lo','object_size_mid','object_size_hi']))
def begin(pos,delete,insert,error=None):
    put('se_doc_edit_position',pos);put('se_doc_edit_delete',delete);put('se_doc_edit_insert',insert)
    request=read(s['se_doc_edit_position'],9)
    regs=call('se_doc_splice_begin',error=error)
    assert read(s['se_doc_edit_position'],9)==request
    return regs.a

def feed(data):
    for offset in range(0,len(data),1024):
        chunk=data[offset:offset+1024];m.load(0x8000,chunk)
        put('se_doc_count',len(chunk),2);put('se_doc_c64',0x8000,2)
        request=read(s['se_doc_count'],4)
        call('se_doc_splice_feed')
        assert read(s['se_doc_count'],4)==request
def finish(old,model,error=None,interleave=True):
    global max_step_instructions
    steps=0
    while m.read(s['se_doc_busy']):
        regs,instructions=m.call(s['se_doc_splice_step']);steps+=1
        max_step_instructions=max(max_step_instructions,instructions)
        assert steps<=300,'splice did not finish its bounded walk'
        if regs.p&1:
            assert error is not None and regs.a==error,(hex(regs.a),error)
            assert published()==old
            assert not m.read(s['se_doc_busy'])
            return steps
        if regs.a==1:
            assert published()==old,'partial transaction became visible'
            if model and interleave and steps%4==0:
                at=(steps*107)%len(model);length=min(31,len(model)-at)
                assert doc_read(at,length)==model[at:at+length]
        else:
            assert regs.a==0 and not m.read(s['se_doc_busy'])
            assert error is None
    return steps

def splice(model,pos,delete,data):
    old=published();begun=begin(pos,delete,len(data))
    if not begun:
        assert not delete and not data and published()==old
        return model,0
    feed(data)
    assert published()==old
    steps=finish(old,model)
    expected=model[:pos]+data+model[pos+delete:]
    assert reconstruct(len(expected))==expected
    assert int.from_bytes(read(s['se_doc_length'],3),'little')==len(expected)
    return expected,steps

try:
    image=profile.image
    m.load(int.from_bytes(image[:2],'little'),image[2:]);m.call(s['se_clear_state'])
    shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim)
    rng=random.Random(0x534d44)
    model=b'';setup(model)
    model,_=splice(model,0,0,b'hello\rSuperEditor')
    model,_=splice(model,5,1,b' C64\r')
    model,_=splice(model,0,len(model),b'')
    model,_=splice(model,0,0,b'')
    call('se_doc_splice_step',error=0x40)
    # Cancellation and recoverable incomplete/invalid feed keep every old field.
    model=b'old text';setup(model)
    old=published();begin(3,2,5)
    begin(0,0,1,error=0x41)
    call('se_doc_adopt_original',error=0x41)
    call('se_doc_splice_step',error=0x45)
    put('se_doc_count',6,2);put('se_doc_c64',0x8000,2)
    call('se_doc_splice_feed',error=0x32)
    put('se_doc_count',1,2);put('se_doc_c64',0x8400,2)
    call('se_doc_splice_feed',error=0x33)
    put('se_doc_count',0,2);call('se_doc_splice_feed',error=0x36)
    feed(b'12');call('se_doc_splice_cancel')
    assert published()==old and reconstruct(len(model))==model
    model,_=splice(model,3,2,b'ABCDE')
    for pos,delete,insert in [(len(model)+1,0,1),(0,len(model)+1,0),(0,0,131073),(0xFFFFFF,2,0)]:
        before=published();begin(pos,delete,insert,error=0x32);assert published()==before
    # Sequential typing should merge into one append run, not one piece/key.
    model=b'<> ';setup(model)
    for i in range(120):model,_=splice(model,1+i,0,bytes([65+i%26]))
    assert m.read(s['se_doc_root_count'])==1 and m.read(s['se_doc_roots']+1)==3
    model,_=splice(model,1,120,b'')
    assert model==b'<> ' and m.read(s['se_doc_roots']+1)==1
    # All edit shapes over long source runs, with exact model after every commit.
    model=rng.randbytes(17000);setup(model)
    max_steps=0
    for case in range(220):
        pos=rng.randrange(len(model)+1);delete=rng.randrange(min(100,len(model)-pos)+1)
        data=rng.randbytes(rng.randrange(71))
        model,steps=splice(model,pos,delete,data);max_steps=max(max_steps,steps)
    # Staged insert itself spans64KiB; object storage and logical source differ.
    model=rng.randbytes(70000);setup(model,banks=4)
    data=rng.randbytes(70000)
    model,_=splice(model,65530,17,data)
    assert len(model)==139983
    # Source quota failure leaves doc and append publication untouched.
    old=published();begin(0,len(model),262145-70000,error=0x32);assert published()==old
    # The configured1MiB document ceiling is exercised by real producer
    # replacement and full reconstruction, not inferred from the object store.
    model=rng.randbytes(1048576);setup(model,banks=16)
    model,_=splice(model,524000,65537,rng.randbytes(65537))
    assert len(model)==1048576
    old=published();begin(0,0,1,error=0x32);assert published()==old
    model,_=splice(model,0,len(model),b'')
    assert not model and m.read(s['se_doc_root_count'])==0
    # Full32-leaf input fixture. The actual splice producer emits all2048
    # records, checks sums/lifetimes and writes its own32 new COW leaves.
    original=rng.randbytes(32768);added=rng.randbytes(32768);setup(original)
    orig=token('se_doc_original');app=token('se_doc_append');meta=token('se_doc_meta')
    load_source(app,added);object_size(app,len(added))
    roots=bytearray();model=bytearray();old_leaves=[]
    for page in range(32):
        leaf=bytearray(1024)
        for record in range(64):
            index=page*64+record;source=orig if index%2==0 else app;data=original if index%2==0 else added
            offset=(index*17)%(len(data)-8)
            at=record*16;leaf[at:at+3]=source[:3];leaf[at+3:at+6]=offset.to_bytes(3,'little')
            leaf[at+6:at+9]=(8).to_bytes(3,'little');leaf[at+9:at+12]=b'\xff'*3
            model.extend(data[offset:offset+8])
        slot=63-2*page;object_write(meta,slot*1024,bytes(leaf),host=0x8400);old_leaves.append((slot,bytes(leaf)))
        roots.extend(bytes([slot,64])+(512).to_bytes(3,'little')+b'\xff'*3)
    m.load(s['se_doc_roots'],bytes(roots));m.write(s['se_doc_root_count'],32)
    put('se_doc_length',len(model));put('se_doc_generation',3,2);m.call(s['se_doc_invalidate'])
    model=bytes(model);assert reconstruct(len(model))==model
    old=published();begin(1,0,1);feed(b'X');steps=finish(old,model,error=0x43)
    assert reconstruct(len(model))==model
    assert steps>=250 # failure reaches actual descriptor limit, not an early guard
    model,steps=splice(model,40,8,b'REPLACED')
    assert m.read(s['se_doc_root_count'])==32
    assert all(m.read(s['se_doc_roots']+i*8+1)==64 for i in range(32))
    assert set(m.read(s['se_doc_roots']+i*8) for i in range(32)).isdisjoint(slot for slot,_ in old_leaves)
    full_steps=steps
    model,steps=splice(model,len(model)-8,8,b'ENDTEXT!')
    assert set(m.read(s['se_doc_roots']+i*8) for i in range(32))==set(range(1,64,2))
    assert m.read(s['se_doc_roots']+31*8)==63 # FC00+0400 exact metadata-bank end
    # Cancel after candidate metadata has already been stashed, then retry.
    old=published();begin(0,8,8);feed(b'canceled')
    for _ in range(12):
        regs=call('se_doc_splice_step');assert regs.a==1
    call('se_doc_splice_cancel');assert published()==old and reconstruct(len(model))==model
    # Failure on the last source record occurs after31 new COW pages have
    # already been written. Repair the injected corruption, then verify old text.
    last_slot=m.read(s['se_doc_roots']+31*8)
    m.load(s['se_object_id'],meta);put('se_object_offset',last_slot*1024)
    put('se_object_length',1024,2);put('se_object_c64',0x8800,2);call('se_object_copy',a=1)
    saved_leaf=read(0x8800,1024);bad=bytearray(saved_leaf);bad[63*16+12]=1
    object_write(meta,last_slot*1024,bytes(bad),host=0x8400);m.call(s['se_doc_invalidate'])
    old=published();begin(0,8,8);feed(b'ROLLBACK')
    late_steps=finish(old,model,error=0x42,interleave=False);assert late_steps>=250
    object_write(meta,last_slot*1024,saved_leaf,host=0x8400);m.call(s['se_doc_invalidate'])
    assert reconstruct(len(model))==model
    model,_=splice(model,0,len(model),b'clean slate\r')
    assert m.read(s['se_doc_root_count'])==1 and m.read(s['se_doc_roots']+1)==1
    assert read(0xC600,1024)==shim
    result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=r['sha256'],
        randomized_splices=220,sequential_typing=120,large_insert_bytes=70000,maximum_document_bytes=1048576,maximum_document_replacement=65537,
        full_producer_pieces=2048,full_producer_leaves=32,full_producer_steps=full_steps,metadata_exact_bank_end=True,
        max_random_steps=max_steps,max_step_instructions=max_step_instructions,
        timing="Instruction counts only; no measured C64 cycle/frame timing",capacity_and_fragment_rollback=True,
        pending_reads_and_cancel_verified=True,late_corruption_rollback_steps=late_steps,shim_bytes_verified=1024)
    result.update(profile.identity);result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:
    m.close()
