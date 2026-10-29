"""Paged byte-reader tests. Root fixtures are host-built; mutations remain open."""
import json
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
r=json.loads((ROOT/'build/document-probe-report.json').read_text());s=r['symbols']
(ROOT/'build/document-test-result.json').unlink(missing_ok=True)
m=Machine()
def read(address,length):
    return bytes(m.read(address+i) for i in range(length))
def put(name,value,width=2):
    m.load(s[name],value.to_bytes(width,'little'))
def call(name,a=0,x=0,y=0,error=None):
    regs,_=m.call(s[name],a=a,x=x,y=y)
    assert bool(regs.p&1)==(error is not None),(name,hex(regs.a),regs.p)
    if error is not None:
        assert regs.a==error,(name,hex(regs.a),error)
    return regs

def object_write(token,offset,payload,host=0x8000):
    m.load(s['se_object_id'],token)
    m.load(host,payload)
    put('se_object_offset',offset,3);put('se_object_length',len(payload));put('se_object_c64',host)
    call('se_object_copy',a=0)
def object_commit(token,length):
    m.load(s['se_object_id'],token);put('se_object_offset',length,3);call('se_object_resize')
def doc_read(offset,length,host=0x8000,error=None):
    put('se_doc_offset',offset,3);put('se_doc_count',length);put('se_doc_c64',host)
    request=read(s['se_doc_offset'],7)
    call('se_doc_read',error=error)
    assert read(s['se_doc_offset'],7)==request
    return read(host,length) if error is None else None

def reset(banks):
    put('se_reu_banks',banks);call('se_reu_provider_init');call('se_object_init')

try:
    image=(ROOT/'build/document-probe.prg').read_bytes()
    m.load(int.from_bytes(image[:2],'little'),image[2:]);m.call(s['se_clear_state'])
    shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim)
    put('se_reu_banks',8)
    m.call(s['se_doc_probe'])
    assert read(s['se_doc_result'],2)==b'\x01\x09',(read(s['se_doc_result'],3),m.read(s['se_doc_error']))
    reset(8)
    before=read(s['se_reu_logical_owner'],512)
    call('se_doc_init',a=4,error=1) # partial original/append allocation rollback
    assert read(s['se_reu_logical_owner'],512)==before
    assert m.read(s['se_doc_ready'])==0
    call('se_doc_init',a=1)
    put('se_doc_source_length',0,3);call('se_doc_adopt_original')
    assert read(s['se_doc_length'],3)==b'\0\0\0' and m.read(s['se_doc_root_count'])==0
    doc_read(0,1,error=0x32)
    call('se_doc_adopt_original',error=0x40)
    reset(256)
    call('se_doc_init',a=16)
    call('se_doc_init',a=16,error=0x40)
    original=read(s['se_doc_original'],5);append=read(s['se_doc_append'],5);meta=read(s['se_doc_meta'],5)
    put('se_doc_source_length',1048577,3)
    previous=read(s['se_reu_dma_calls'],5)
    call('se_doc_adopt_original',error=0x32)
    assert read(s['se_reu_dma_calls'],5)==previous
    rng=random.Random(0x504554)
    original_bytes=bytearray(rng.randbytes(1048576))
    original_bytes[10000:16000]=b'A'*6000 # long CR-free source run
    for offset in range(0,len(original_bytes),4096):
        object_write(original,offset,bytes(original_bytes[offset:offset+4096]))
    put('se_doc_source_length',len(original_bytes),3)
    call('se_doc_adopt_original')
    assert int.from_bytes(read(s['se_doc_length'],3),'little')==1048576
    assert m.read(s['se_doc_root_count'])==1
    assert doc_read(65500,1024)==original_bytes[65500:66524]
    assert doc_read(10000,1024)==b'A'*1024
    assert doc_read(1047552,1024)==original_bytes[-1024:]
    for offset in range(0,len(original_bytes),1024):
        assert doc_read(offset,1024)==original_bytes[offset:offset+1024]
    append_bytes=rng.randbytes(1048576)
    for offset in range(0,len(append_bytes),4096):
        object_write(append,offset,append_bytes[offset:offset+4096])
    object_commit(append,len(append_bytes))
    # Independent fully populated2048-piece fixture, with permuted metadata
    # slots and alternating immutable sources; not an assembler edit result.
    model=bytearray();leaves=[];roots=bytearray()
    for page in range(32):
        leaf=bytearray(1024);slot=63-2*page
        for record in range(64):
            source=original if record%2==0 else append
            data=original_bytes if record%2==0 else append_bytes
            offset=rng.randrange(len(data)-512+1)
            at=record*16
            leaf[at:at+3]=source[:3]
            leaf[at+3:at+6]=offset.to_bytes(3,'little')
            leaf[at+6:at+9]=(512).to_bytes(3,'little')
            leaf[at+9:at+12]=b'\xff'*3
            model.extend(data[offset:offset+512])
        object_write(meta,slot*1024,bytes(leaf),host=0x8400)
        leaves.append(bytes(leaf))
        roots.extend(bytes([slot,64])+(32768).to_bytes(3,'little')+b'\xff'*3)
    m.load(s['se_doc_roots'],bytes(roots));m.write(s['se_doc_root_count'],32)
    put('se_doc_generation',3);m.call(s['se_doc_invalidate'])
    # Leaf cache must avoid redundant metadata DMA on a same-leaf read.
    before=int.from_bytes(read(s['se_reu_dma_calls'],2),'little')
    assert doc_read(0,1)==model[:1]
    after=int.from_bytes(read(s['se_reu_dma_calls'],2),'little')
    assert (after-before)&65535==2
    assert doc_read(1,1)==model[1:2]
    after2=int.from_bytes(read(s['se_reu_dma_calls'],2),'little')
    assert (after2-after)&65535==1
    assert doc_read(32767,2)==model[32767:32769]
    after3=int.from_bytes(read(s['se_reu_dma_calls'],2),'little')
    assert (after3-after2)&65535==3
    for case in range(300):
        length=[1,255,256,257,512,1024][case%6]
        offset=rng.randrange(len(model)-length+1)
        assert doc_read(offset,length)==model[offset:offset+length]
    for offset in range(0,len(model),1024):
        assert doc_read(offset,1024)==model[offset:offset+1024]
    invalid=[(0,0,0x8000,0x36),(0,1,0x7FFF,0x33),(0,1,0x8400,0x33),
        (0,2,0x83FF,0x33),(0,1025,0x8000,0x33),
        (1048576,1,0x8000,0x32),(0xFFFFFF,2,0x8000,0x32)]
    for offset,length,host,error in invalid:
        before=read(s['se_reu_dma_calls'],5)
        doc_read(offset,length,host,error)
        assert read(s['se_reu_dma_calls'],5)==before
    for index,value in [(0,64),(1,0),(1,65)]:
        m.write(s['se_doc_roots']+index,value)
        doc_read(0,1,error=0x42)
        m.load(s['se_doc_roots'],bytes(roots))
    for field,value,error in [(6,bytes(3),0x42),(0,bytes([meta[0]]),0x42),(1,b'\xff\xff',0x31)]:
        leaf=bytearray(leaves[0]);leaf[field:field+len(value)]=value
        object_write(meta,63*1024,bytes(leaf),host=0x8400)
        m.call(s['se_doc_invalidate']);doc_read(0,1,error=error)
    reset(256)
    call('se_doc_read',error=0x40)
    assert read(0xC600,1024)==shim
    result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=r['sha256'],
        guest_probe_cases=9,imported_bytes=1048576,paged_fixture_bytes=len(model),pieces=2048,leaves=32,
        randomized_reads=300,long_source_run=6000,leaf_cache_dma_verified=True,
        creation_rollback=True,invalid_reads=len(invalid),corrupt_root_or_piece_cases=6,
        shim_bytes_verified=1024,
        limitations='Reader fixture is host-built; producer edits are covered separately by test_splice.py. Line indexes remain pending.')
    (ROOT/'build/document-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
finally:
    m.close()
