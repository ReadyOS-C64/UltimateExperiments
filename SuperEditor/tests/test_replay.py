"""Real packed snapshot production and reference replay, independent byte model."""
import json
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
r=json.loads((ROOT/'build/replay-probe-report.json').read_text());s=r['symbols']
result_path=ROOT/'build/replay-test-result.json';result_path.unlink(missing_ok=True)
m=Machine()
def read(address,length):return bytes(m.read(address+i) for i in range(length))
def put(name,value,width=3):m.load(s[name],value.to_bytes(width,'little'))
def call(name,a=0,x=0,y=0,error=None):
    regs,_=m.call(s[name],a=a,x=x,y=y)
    assert bool(regs.p&1)==(error is not None),(name,hex(regs.a),regs.p)
    if error is not None:assert regs.a==error,(name,hex(regs.a),error)
    return regs

def token(name):return read(s[name],5)
def object_write(t,offset,payload,host=0x8000):
    m.load(s['se_object_id'],t);m.load(host,payload);put('se_object_offset',offset)
    put('se_object_length',len(payload),2);put('se_object_c64',host,2);call('se_object_copy',a=0)
def object_read(t,offset,length):
    m.load(s['se_object_id'],t);put('se_object_offset',offset)
    put('se_object_length',length,2);put('se_object_c64',0x8000,2);call('se_object_copy',a=1)
    return read(0x8000,length)
def object_size(t,size):
    m.load(s['se_object_id'],t);put('se_object_offset',size);call('se_object_resize')
def setup(data,banks=2):
    put('se_reu_banks',256,2);call('se_reu_provider_init');call('se_object_init');call('se_doc_init',a=banks)
    orig=token('se_doc_original')
    for offset in range(0,len(data),1024):object_write(orig,offset,data[offset:offset+1024])
    put('se_doc_source_length',len(data));call('se_doc_adopt_original')
    call('se_object_create',a=6,x=1);journal=token('se_object_id');object_size(journal,65536)
    return journal

def doc_read(offset,length):
    put('se_doc_offset',offset);put('se_doc_count',length,2);put('se_doc_c64',0x8000,2)
    call('se_doc_read');return read(0x8000,length)
def document(size):return b''.join(doc_read(i,min(1024,size-i)) for i in range(0,size,1024))
def app_size():
    index=token('se_doc_append')[0]
    return bytes(m.read(s[n]+index) for n in ['object_size_lo','object_size_mid','object_size_hi'])
def published():return read(s['se_doc_roots'],256)+read(s['se_doc_length'],3)+read(s['se_doc_generation'],2)+app_size()
def snapshot(journal,offset,model):
    old=published();m.load(s['se_snapshot_token'],journal);put('se_snapshot_offset',offset)
    call('se_snapshot_begin');steps=0
    assert m.read(s['se_doc_read_locks'])==1
    while m.read(s['se_snapshot_busy']):
        regs=call('se_snapshot_step');steps+=1;assert steps<=257
        assert published()==old
        if model and steps%8==0:
            at=(steps*131)%len(model);assert doc_read(at,min(23,len(model)-at))==model[at:at+23]
    assert m.read(s['se_doc_read_locks'])==0
    pieces=int.from_bytes(read(s['se_snapshot_pieces'],2),'little')
    assert int.from_bytes(read(s['se_snapshot_bytes'],2),'little')==pieces*9
    assert int.from_bytes(read(s['se_snapshot_length'],3),'little')==len(model)
    return (journal,offset,pieces,len(model),steps)
def replay(saved,old_model,expected,error=None):
    journal,offset,pieces,length,_=saved
    m.load(s['se_replay_token'],journal);put('se_replay_offset',offset)
    put('se_replay_pieces',pieces,2);put('se_replay_length',length)
    old=published();call('se_replay_begin');steps=0
    call('se_doc_splice_step',error=0x40) # cannot hijack replay phase3
    call('se_doc_splice_feed',error=0x41)
    while m.read(s['se_doc_busy']):
        regs,_=m.call(s['se_replay_step']);steps+=1;assert steps<=256
        if regs.p&1:
            assert error is not None and regs.a==error,(hex(regs.a),error)
            assert published()==old and m.read(s['se_doc_busy'])==0
            return steps
        if regs.a==1:
            assert published()==old
            if old_model and steps%8==0:
                at=(steps*71)%len(old_model);assert doc_read(at,min(19,len(old_model)-at))==old_model[at:at+19]
    assert error is None and app_size()==old[-3:]
    assert document(len(expected))==expected
    return steps

def splice(model,pos,delete,data):
    put('se_doc_edit_position',pos);put('se_doc_edit_delete',delete);put('se_doc_edit_insert',len(data));call('se_doc_splice_begin')
    for offset in range(0,len(data),1024):
        chunk=data[offset:offset+1024];m.load(0x8000,chunk)
        put('se_doc_count',len(chunk),2);put('se_doc_c64',0x8000,2);call('se_doc_splice_feed')
    while m.read(s['se_doc_busy']):call('se_doc_splice_step')
    expected=model[:pos]+data+model[pos+delete:];assert document(len(expected))==expected;return expected
try:
    image=(ROOT/'build/replay-probe.prg').read_bytes();m.load(0x0801,image[2:]);m.call(s['se_clear_state'])
    shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim)
    rng=random.Random(0x554e444f)
    model=b'Original\rPETSCII source\r';journal=setup(model)
    before=snapshot(journal,0,model)
    packed=object_read(journal,0,9)
    assert packed==token('se_doc_original')[:3]+bytes(3)+len(model).to_bytes(3,'little')
    changed=splice(model,8,0,b' edited');after=snapshot(journal,256,changed)
    for _ in range(6):replay(before,changed,model);replay(after,model,changed)
    # Empty snapshots never send a zero-length transfer to hardware.
    journal=setup(b'');empty=snapshot(journal,65536,b'')
    model=splice(b'',0,0,b'first edit');filled=snapshot(journal,0,model)
    replay(empty,model,b'');replay(filled,b'',model)
    # Source read leases block writers, and an idle cancel cannot release a
    # lease owned by someone else or cancel another kind of transaction.
    call('se_doc_read_acquire');call('se_snapshot_cancel');assert m.read(s['se_doc_read_locks'])==1
    call('se_doc_read_release')
    put('se_doc_edit_position',0);put('se_doc_edit_delete',0);put('se_doc_edit_insert',1);call('se_doc_splice_begin')
    call('se_replay_cancel',error=0x41);call('se_doc_splice_cancel')
    # Full append quota: undo/redo replay allocates and appends no byte.
    model=rng.randbytes(1048576);journal=setup(model,banks=16)
    before=snapshot(journal,0,model)
    changed=splice(model,0,len(model),rng.randbytes(1048576));after=snapshot(journal,256,changed)
    assert app_size()==(1048576).to_bytes(3,'little')
    for _ in range(3):replay(before,changed,model);replay(after,model,changed)
    #2048 packed records end exactly at10000: real capture, then real replay.
    original=rng.randbytes(32768);added=rng.randbytes(32768);journal=setup(original)
    orig=token('se_doc_original');app=token('se_doc_append');meta=token('se_doc_meta')
    for offset in range(0,len(added),1024):object_write(app,offset,added[offset:offset+1024])
    object_size(app,len(added));roots=bytearray();model=bytearray();expected_packed=bytearray()
    for page in range(32):
        leaf=bytearray(1024)
        for rec in range(64):
            index=page*64+rec;source=orig if index%2==0 else app;data=original if index%2==0 else added
            offset=(index*17)%(len(data)-8);record=source[:3]+offset.to_bytes(3,'little')+(8).to_bytes(3,'little')
            leaf[rec*16:rec*16+9]=record;leaf[rec*16+9:rec*16+12]=b'\xff'*3
            expected_packed.extend(record);model.extend(data[offset:offset+8])
        object_write(meta,page*1024,bytes(leaf),host=0x8400)
        roots.extend(bytes([page,64])+(512).to_bytes(3,'little')+b'\xff'*3)
    m.load(s['se_doc_roots'],bytes(roots));put('se_doc_root_count',32,1);put('se_doc_length',len(model));put('se_doc_generation',3,2);m.call(s['se_doc_invalidate'])
    model=bytes(model);saved=snapshot(journal,0xB800,model)
    packed=b''.join(object_read(journal,0xB800+i,min(1024,len(expected_packed)-i)) for i in range(0,len(expected_packed),1024))
    assert packed==expected_packed and saved[2]==2048 and saved[4]==257
    # Cancel a capture after private journal writes, without changing source.
    m.load(s['se_snapshot_token'],journal);put('se_snapshot_offset',0);call('se_snapshot_begin');call('se_snapshot_step');call('se_snapshot_cancel')
    assert not m.read(s['se_doc_read_locks']) and document(len(model))==model
    changed=splice(model,0,8,b'REPLAY!!')
    steps=replay(saved,changed,model);assert steps==256
    # Corrupt final record: many new leaves can exist, but old roots survive.
    last=0x10000-9;object_write(journal,last,b'\xff')
    steps=replay(saved,model,model,error=0x42);assert steps==256
    object_write(journal,last,expected_packed[-9:-8])
    assert document(len(model))==model
    # Begin-time bounds/admission errors must not acquire a transaction.
    m.load(s['se_replay_token'],journal);put('se_replay_offset',0xFFFF);put('se_replay_pieces',1,2);put('se_replay_length',1)
    call('se_replay_begin',error=0x32)
    put('se_replay_pieces',2049,2);call('se_replay_begin',error=0x43)
    m.load(s['se_snapshot_token'],orig);put('se_snapshot_offset',0);call('se_snapshot_begin',error=0x42)
    assert not m.read(s['se_doc_busy']) and not m.read(s['se_doc_read_locks'])
    assert read(0xC600,1024)==shim
    result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=r['sha256'],
        undo_redo_replay_roundtrips=9,full_append_bytes=1048576,packed_records=2048,
        packed_bytes=18432,snapshot_steps=257,replay_steps=256,
        exact_journal_bank_end=True,late_corruption_rollback=True,
        cancellation_and_leases=True,shim_bytes_verified=1024,
        limitations='Snapshot/replay primitives; bounded history stack and user commands remain unimplemented.')
    result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:m.close()
