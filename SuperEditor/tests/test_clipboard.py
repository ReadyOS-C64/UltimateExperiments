"""Private copy/paste service, source leases, cancellation and allocation failure."""
import json
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
r=json.loads((ROOT/'build/clipboard-probe-report.json').read_text());s=r['symbols']
result_path=ROOT/'build/clipboard-test-result.json';result_path.unlink(missing_ok=True)
m=Machine()
def read(address,length):return bytes(m.read(address+i) for i in range(length))
def put(name,value,width=3):m.load(s[name],value.to_bytes(width,'little'))
def call(name,a=0,x=0,y=0,error=None):
    regs,_=m.call(s[name],a=a,x=x,y=y)
    assert bool(regs.p&1)==(error is not None),(name,hex(regs.a),regs.p)
    if error is not None:assert regs.a==error,(name,hex(regs.a),error)
    return regs

def obj_token(name):return read(s[name],5)
def object_write(t,offset,payload):
    m.load(s['se_object_id'],t);m.load(0x8000,payload)
    put('se_object_offset',offset);put('se_object_length',len(payload),2);put('se_object_c64',0x8000,2)
    call('se_object_copy',a=0)
def object_read(t,offset,length):
    m.load(s['se_object_id'],t);put('se_object_offset',offset)
    put('se_object_length',length,2);put('se_object_c64',0x8000,2);call('se_object_copy',a=1)
    return read(0x8000,length)
def setup(data,banks=2,physical_banks=256):
    put('se_reu_banks',physical_banks,2);call('se_reu_provider_init');call('se_object_init')
    call('se_doc_init',a=banks);call('se_clip_init')
    t=obj_token('se_doc_original')
    for offset in range(0,len(data),1024):object_write(t,offset,data[offset:offset+1024])
    put('se_doc_source_length',len(data));call('se_doc_adopt_original')
def doc_read(offset,length):
    put('se_doc_offset',offset);put('se_doc_count',length,2);put('se_doc_c64',0x8000,2)
    call('se_doc_read');return read(0x8000,length)
def document(size):return b''.join(doc_read(i,min(1024,size-i)) for i in range(0,size,1024))
def clipboard(size):return b''.join(object_read(obj_token('se_clip_token'),i,min(1024,size-i)) for i in range(0,size,1024))
def clip_published():return (obj_token('se_clip_token') if m.read(s['se_clip_active']) else None,read(s['se_clip_length'],3),read(s['se_clip_generation'],2))
def doc_published():
    app=obj_token('se_doc_append')[0]
    return read(s['se_doc_roots'],256)+read(s['se_doc_length'],3)+read(s['se_doc_generation'],2)+bytes(m.read(s[n]+app) for n in ['object_size_lo','object_size_mid','object_size_hi'])
def request(pos,length):put('se_clip_position',pos);put('se_clip_span',length)
def copy(model,pos,length):
    old=clip_published();request(pos,length);req=read(s['se_clip_position'],6)
    started=call('se_clip_copy_begin').a
    assert read(s['se_clip_position'],6)==req
    if not length:
        assert not started and clip_published()==old;return b''
    assert started==1 and m.read(s['se_doc_read_locks'])==1
    steps=0
    while m.read(s['se_clip_busy']):
        regs=call('se_clip_copy_step');steps+=1;assert steps<=1100
        if regs.a==1:
            assert clip_published()==old
            at=(steps*131)%len(model)
            assert doc_read(at,min(17,len(model)-at))==model[at:at+17]
    assert m.read(s['se_doc_read_locks'])==0
    assert clipboard(length)==model[pos:pos+length]
    if old[0] is not None:assert obj_token('se_clip_token')!=old[0]
    return model[pos:pos+length]
def paste(model,clip,pos,delete):
    old_doc=doc_published();old_clip=clip_published();request(pos,delete)
    started=call('se_clip_paste_begin').a
    if not clip:
        assert started==0 and doc_published()==old_doc;return model
    assert started==1
    steps=0
    while m.read(s['se_clip_busy']):
        regs=call('se_clip_paste_step');steps+=1;assert steps<=1600
        if regs.a==1:
            assert doc_published()==old_doc
            if model and steps%8==0:
                at=(steps*73)%len(model);assert doc_read(at,min(31,len(model)-at))==model[at:at+31]
        assert clip_published()==old_clip
    expected=model[:pos]+clip+model[pos+delete:]
    assert document(len(expected))==expected and clipboard(len(clip))==clip
    return expected

try:
    image=(ROOT/'build/clipboard-probe.prg').read_bytes()
    m.load(0x0801,image[2:]);m.call(s['se_clear_state'])
    shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim)
    put('se_reu_banks',8,2);m.call(s['se_clip_probe'])
    assert read(s['se_clip_result'],2)==b'\x01\x0a' and m.read(s['se_clip_error'])==0
    rng=random.Random(0x434C50)
    model=b'Hello\r:::region\rHidden source\r:::end\r';setup(model)
    assert paste(model,b'',2,5)==model
    copy(model,0,0)
    clip=copy(model,7,len(model)-7)
    old=clip_published();call('se_clip_init');assert clip_published()==old
    model=paste(model,clip,0,5)
    # A read lease prevents a concurrent editor command from changing source.
    request(0,min(10,len(model)));call('se_clip_copy_begin')
    put('se_doc_edit_position',0);put('se_doc_edit_delete',0);put('se_doc_edit_insert',1)
    call('se_doc_splice_begin',error=0x41)
    call('se_clip_copy_begin',error=0x51);call('se_clip_paste_begin',error=0x51)
    call('se_clip_paste_cancel',error=0x51)
    call('se_clip_copy_cancel');assert m.read(s['se_doc_read_locks'])==0 and clip_published()==old
    # Idle cancels cannot cancel a different service's document transaction.
    call('se_doc_splice_begin');call('se_clip_copy_cancel');call('se_clip_paste_cancel')
    assert m.read(s['se_doc_busy'])==1;call('se_doc_splice_cancel')
    # Cancel after one copied chunk and one staged paste chunk.
    model=rng.randbytes(16000);setup(model);clip=copy(model,2000,5000);old=clip_published()
    request(0,12000);call('se_clip_copy_begin');call('se_clip_copy_step')
    call('se_clip_copy_cancel');assert clip_published()==old and clipboard(len(clip))==clip
    before=doc_published();request(0,100);call('se_clip_paste_begin');call('se_clip_paste_step')
    call('se_clip_copy_cancel',error=0x51);call('se_clip_paste_cancel')
    assert doc_published()==before and document(len(model))==model and clip_published()==old
    # Faults abort cleanly and release the source lease.
    request(0,5000);call('se_clip_copy_begin');put('se_doc_generation',7,2)
    call('se_clip_copy_step',error=0x52);assert not m.read(s['se_doc_read_locks'])
    put('se_doc_generation',2,2)
    request(0,1);call('se_clip_paste_begin');put('se_clip_generation',99,2)
    call('se_clip_paste_step',error=0x52);assert not m.read(s['se_doc_busy'])
    m.load(s['se_clip_generation'],old[2]);assert clipboard(len(clip))==clip
    current=obj_token('se_clip_token');m.load(s['se_clip_token'],obj_token('se_doc_meta'))
    call('se_clip_validate',error=0x54);m.load(s['se_clip_token'],current)
    # Random ranges and replacement pastes, with clipboard independent of edits.
    for case in range(90):
        start=rng.randrange(len(model));length=rng.randrange(1,min(700,len(model)-start)+1)
        clip=copy(model,start,length)
        pos=rng.randrange(len(model)+1);delete=rng.randrange(min(150,len(model)-pos)+1)
        model=paste(model,clip,pos,delete)
    # Full1MiB clipboard and replace-paste through nonzero high source positions.
    model=rng.randbytes(1048576);setup(model,banks=16)
    clip=copy(model,0,len(model));model=paste(model,clip,0,len(model))
    assert len(model)==1048576
    before=doc_published();request(0,len(model));call('se_clip_paste_begin',error=0x32)
    assert doc_published()==before and clipboard(len(clip))==clip
    #512KiB: insufficient space for the replacement's second bank must roll
    #back a first tentative allocation and retain old clipboard/source exactly.
    model=rng.randbytes(70000);setup(model,banks=2,physical_banks=8)
    clip=copy(model,65000,1000);old=clip_published()
    owners=read(s['se_reu_logical_owner'],512)
    request(0,len(model));call('se_clip_copy_begin',error=1)
    assert read(s['se_reu_logical_owner'],512)==owners and not m.read(s['se_doc_read_locks'])
    assert clip_published()==old and clipboard(len(clip))==clip and document(len(model))==model
    # Free all source objects to prove clipboard is not a borrowed source span.
    for name in ['se_doc_original','se_doc_append','se_doc_meta']:
        m.load(s['se_object_id'],obj_token(name));call('se_object_release')
    call('se_clip_validate');assert clipboard(len(clip))==clip
    # Provider transitions cannot be mistaken for a live clipboard incarnation.
    put('se_reu_banks',256,2);call('se_reu_provider_init');call('se_object_init')
    call('se_clip_validate',error=0x50)
    assert read(0xC600,1024)==shim
    result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=r['sha256'],
        guest_probe_cases=10,randomized_copy_pastes=90,maximum_clipboard_bytes=1048576,
        source_lease_and_cancel=True,independent_after_source_release=True,
        partial_allocation_rollback=True,profiles=[256,8],shim_bytes_verified=1024)
    result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:m.close()
