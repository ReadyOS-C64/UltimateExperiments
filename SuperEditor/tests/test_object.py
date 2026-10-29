"""Generational REU object tests against an independent host byte model."""
import json
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
r=json.loads((ROOT/'build/object-probe-report.json').read_text());s=r['symbols']
(ROOT/'build/object-test-result.json').unlink(missing_ok=True)
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

def token():
    return read(s['se_object_id'],5)
def restore(t):
    m.load(s['se_object_id'],t)
def resize(length,error=None):
    put('se_object_offset',length,3)
    return call('se_object_resize',error=error)
def transfer(offset,length,host=0x8000,direction=1,error=None):
    put('se_object_offset',offset,3);put('se_object_length',length);put('se_object_c64',host)
    request=read(s['se_object_id'],12)
    result=call('se_object_copy',a=direction,error=error)
    assert read(s['se_object_id'],12)==request,'object API changed its request'
    return result

def owners():
    return read(s['se_reu_logical_owner'],256)+read(s['se_reu_physical_owner'],256)
def reset(banks):
    put('se_reu_banks',banks)
    regs,_=m.call(s['se_reu_provider_init'])
    assert bool(regs.p&1)==(banks==0)
    if banks:
        call('se_object_init')

try:
    image=(ROOT/'build/object-probe.prg').read_bytes()
    m.load(int.from_bytes(image[:2],'little'),image[2:]);m.call(s['se_clear_state'])
    sentinel=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,sentinel)
    put('se_reu_banks',256)
    m.call(s['se_object_probe'])
    assert read(s['se_object_result'],2)==b'\x01\x0e',read(s['se_object_result'],2)
    assert read(s['se_reu_dma_calls'],2)==(21).to_bytes(2,'little')
    assert read(s['se_reu_dma_bytes'],3)==(71680).to_bytes(3,'little')
    assert all(m.read(s['se_reu_logical_owner']+i)==0 for i in range(1,256))
    reset(256)
    call('se_object_init',error=0x30)
    # Force each consecutive logical extent onto nonconsecutive physical banks.
    for i in range(16):
        call('se_reu_bind',a=7,x=190+i,y=2*i+1)
    regs=call('se_object_create',a=4,x=16)
    assert regs.a==0 and (regs.x,regs.y)==(1,0)
    original=token()
    actual_banks=[m.read(s['se_reu_map']+m.read(s['object_extents']+i)) for i in range(16)]
    assert actual_banks==list(range(2,33,2))
    rng=random.Random(0x6510)
    model=bytearray(rng.randbytes(1048576))
    for offset in range(0,len(model),4096):
        m.load(0x8000,bytes(model[offset:offset+4096]))
        transfer(offset,4096,direction=0)
    resize(len(model))
    sizes=[1,2,255,256,257,1024,4096,6656]
    crossings=0
    for case in range(300):
        length=sizes[case%len(sizes)]
        if case%3==0:
            boundary=rng.randrange(1,16)*65536
            offset=boundary-rng.randrange(1,min(length,255)+1)
            crossings+=offset+length>boundary
        else:
            offset=rng.randrange(len(model)-length+1)
        payload=rng.randbytes(length)
        m.load(0x8000,payload)
        transfer(offset,length,direction=0)
        model[offset:offset+length]=payload
        m.load(0x8000,bytes([0xCC])*length)
        transfer(offset,length)
        assert read(0x8000,length)==model[offset:offset+length]
    # Every byte, including untouched portions after randomized writes, checked.
    for offset in range(0,len(model),4096):
        transfer(offset,4096)
        assert read(0x8000,4096)==model[offset:offset+4096]
    # Independently inspect physical storage so a consistent wrong mapping in
    # both read/write cannot hide behind the host-model round trip.
    for extent,physical in enumerate(actual_banks):
        for offset in [0,1,255,256,32767,65535]:
            assert m.lib.zeropage_peddle_read_reu(m.handle,physical*65536+offset)==model[extent*65536+offset]
    invalid=[(0,0,0x8000,0,0x36),(0,1,0x8000,2,0x36),
        (len(model),1,0x8000,0,0x32),(0xFFFFFF,2,0x8000,0,0x32),
        (0,1,0x7FFF,1,0x33),(0,1,0x9A00,1,0x33),
        (0,2,0x99FF,1,0x33),(0,6657,0x8000,1,0x33),
        (0,32,0xFFF0,1,0x33),(0,1,0xC600,1,0x33)]
    for offset,length,host,direction,error in invalid:
        before=read(s['se_reu_dma_calls'],5);registers=read(0xDF00,11)
        transfer(offset,length,host,direction,error)
        assert read(s['se_reu_dma_calls'],5)==before and read(0xDF00,11)==registers
    resize(1048577,error=0x32)
    resize(123)
    transfer(122,1)
    transfer(123,1,error=0x32)
    # Staged writes beyond committed end are allowed but cannot be read yet.
    transfer(1000,1,direction=0)
    transfer(1000,1,error=0x32)
    for at,value in [(0,8),(1,2),(3,0xFF)]:
        m.load(s['se_object_id'],original)
        m.write(s['se_object_id']+at,value)
        call('se_object_validate',error=0x31)
    restore(original)
    # A corrupt later extent must be caught before the first extent is written.
    bank=m.read(s['object_extents']+15)
    old_owner=m.read(s['se_reu_logical_owner']+bank)
    m.write(s['se_reu_logical_owner']+bank,0)
    before=read(s['se_reu_dma_calls'],5);state=owners()
    transfer(65535,2,direction=0,error=0x34)
    call('se_object_release',error=0x34)
    assert owners()==state and read(s['se_reu_dma_calls'],5)==before
    m.write(s['se_reu_logical_owner']+bank,old_owner)
    call('se_object_release')
    call('se_object_create',a=4,x=1)
    current=token();assert current[1:3]==b'\x02\0'
    restore(original);call('se_object_validate',error=0x31)
    restore(current);call('se_object_release')
    # Force last generation; release retires slot rather than reusing generation1.
    call('se_object_create',a=4,x=1)
    m.write(s['object_gen_lo'],255);m.write(s['object_gen_hi'],255)
    put('se_object_generation',65535)
    call('se_object_release');assert m.read(s['object_owner'])==255
    regs=call('se_object_create',a=4,x=1);assert regs.a==1
    previous_epoch=token()
    reset(256)
    call('se_object_create',a=4,x=1)
    call('se_object_create',a=4,x=1)
    assert token()[:3]==previous_epoch[:3] and token()[3:]!=previous_epoch[3:]
    restore(previous_epoch);call('se_object_validate',error=0x31)
    # Partial-bank allocation failure rolls back ownership without any DMA.
    reset(8)
    call('se_object_create',a=4,x=5)
    live=token();state=owners();before=read(s['se_reu_dma_calls'],5)
    call('se_object_create',a=5,x=3,error=1)
    assert owners()==state and token()==live and read(s['se_reu_dma_calls'],5)==before
    call('se_object_validate')
    call('se_object_release')
    reset(256)
    tokens=[]
    for i in range(8):
        regs=call('se_object_create',a=4,x=1);assert regs.a==i
        tokens.append(token())
    call('se_object_create',a=4,x=1,error=0x35)
    for t in reversed(tokens):
        restore(t);call('se_object_release')
    for owner,banks in [(2,1),(255,1),(4,0),(4,17)]:
        call('se_object_create',a=owner,x=banks,error=0x36)
    call('se_object_create',a=4,x=1)
    reset(0)
    call('object_service_valid',error=0x30)
    call('se_object_validate',error=0x30) # every reset invalidates old services
    call('se_object_create',a=4,x=1,error=0x30)
    # Provider epoch cannot wrap onto an earlier live-token incarnation.
    put('se_reu_banks',256);put('se_reu_epoch',65535)
    call('se_reu_provider_init',error=6)
    assert read(s['se_reu_epoch'],2)==b'\0\0' and m.read(s['se_reu_retired'])==1
    call('se_reu_provider_init',error=6)
    call('se_object_init',error=0x30)
    assert read(0xC600,1024)==sentinel
    result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=r['sha256'],
        guest_probe_cases=14,model_bytes=len(model),randomized_roundtrips=300,
        cross_bank_cases=crossings,all_model_bytes_checked=True,invalid_transfers=len(invalid),
        allocation_rollback=True,generation_retirement=True,stale_epoch_checked=True,provider_epoch_retirement=True,
        physical_extent_banks=actual_banks,shim_bytes_verified=1024)
    (ROOT/'build/object-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
finally:
    m.close()
