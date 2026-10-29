"""Checked REU provider and DMA tests on emitted 6510 code in Peddle."""
from pathlib import Path
import json
import random
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine

report=json.loads((ROOT/'build/memory-probe-report.json').read_text())
s=report['symbols']
image=(ROOT/'build/memory-probe.prg').read_bytes()
m=Machine()


def word(name,value):
    m.write(s[name],value&255)
    m.write(s[name]+1,value>>8)


def request(logical,host,offset,length,direction):
    m.write(s['se_reu_logical'],logical)
    word('se_reu_c64',host)
    word('se_reu_offset',offset)
    word('se_reu_length',length)
    return m.call(s['se_reu_copy'],a=direction)[0]


try:
    m.load(int.from_bytes(image[:2],'little'),image[2:])
    m.call(s['se_clear_state'])
    word('se_reu_banks',256)
    sentinel=bytes((i*73+29)&255 for i in range(1024))
    m.load(0xC600,sentinel)
    m.call(s['se_memory_probe'])
    assert m.read(s['se_memory_result'])==1
    assert m.read(s['se_memory_cases'])==14
    assert m.read(s['se_reu_dma_calls'])==6
    assert bytes(m.read(s['se_reu_dma_bytes']+i) for i in range(3))==b'\x02\x0c\0'
    assert m.read(s['se_reu_map']+20)==3 and m.read(s['se_reu_map']+21)==6
    assert all(m.read(s['se_reu_logical_owner']+i)==0 for i in range(1,256))
    for physical,offset,length in [(3,0xFC00,1024),(6,0x100,257),(6,0xFF00,256)]:
        actual=bytes(m.lib.zeropage_peddle_read_reu(m.handle,(physical<<16)+offset+i) for i in range(length))
        assert actual==bytes((i&255)^0xA5 for i in range(length))
    for logical,physical in [(1,31),(2,7),(3,255)]:
        regs,_=m.call(s['se_reu_bind'],a=4,x=logical,y=physical)
        assert not regs.p&1 and regs.a==logical
    # Exercise every supported shape without copying the service implementation.
    rng=random.Random(0xC64)
    for case in range(200):
        logical,physical=[(1,31),(2,7),(3,255)][case%3]
        length=[1,255,256,257,1024,4096,8192][case%7]
        offset=rng.randrange(0x10001-length)
        payload=bytes(rng.randrange(256) for _ in range(length))
        m.load(0x5000,payload)
        regs=request(logical,0x5000,offset,length,0)
        assert not regs.p&1
        assert bytes(m.lib.zeropage_peddle_read_reu(m.handle,(physical<<16)+offset+i) for i in range(length))==payload
        m.load(0x9000,bytes([0xCC])*length)
        regs=request(logical,0x9000,offset,length,1)
        assert not regs.p&1
        assert bytes(m.read(0x9000+i) for i in range(length))==payload
    rejects=[(1,0x5000,0,0,0,2),(1,0x3FFF,0,1,1,3),
             (1,0xC600,0,1,1,3),(1,0x1000,0,256,1,3),
             (1,0x0100,0,1,1,3),(1,0xD000,0,16,1,3),
             (1,0xBFFF,0,2,1,3),(1,0xFFF0,0,32,1,3),
             (1,0x5000,0xFFFF,2,1,3),(19,0x5000,0,1,1,4),
             (1,0x5000,0,1,3,5)]
    for logical,host,offset,length,direction,error in rejects:
        registers=bytes(m.read(0xDF00+i) for i in range(11))
        calls=bytes(m.read(s['se_reu_dma_calls']+i) for i in range(2))
        regs=request(logical,host,offset,length,direction)
        assert regs.p&1 and regs.a==error
        assert bytes(m.read(0xDF00+i) for i in range(11))==registers
        assert bytes(m.read(s['se_reu_dma_calls']+i) for i in range(2))==calls
    # Exact exclusive ends on both memory domains are permitted.
    m.load(0xBFFF,b'\xE7')
    regs=request(3,0xBFFF,0xFFFF,1,0)
    assert not regs.p&1
    assert m.lib.zeropage_peddle_read_reu(m.handle,0xFFFFFF)==0xE7
    # Eight-bank profile: logical identity is independent of physical bank count.
    word('se_reu_banks',8)
    m.call(s['se_reu_provider_init'])
    regs,_=m.call(s['se_reu_bind'],a=4,x=200,y=6)
    assert not regs.p&1 and regs.a==200
    regs,_=m.call(s['se_reu_bind'],a=4,x=201,y=8)
    assert regs.p&1
    allocated=[]
    while True:
        regs,_=m.call(s['se_reu_alloc'],a=4)
        if regs.p&1:
            assert regs.a==1
            break
        allocated.append(regs.a)
        assert len(allocated)<=6
    assert len(allocated)==6  # seven data banks minus the explicit binding
    regs,_=m.call(s['se_reu_free'],x=0)
    assert regs.p&1
    # Missing REU admits no allocations, including explicit bindings.
    word('se_reu_banks',0)
    regs,_=m.call(s['se_reu_provider_init'])
    assert regs.p&1
    regs,_=m.call(s['se_reu_alloc'],a=4)
    assert regs.p&1
    assert bytes(m.read(0xC600+i) for i in range(1024))==sentinel
    result=dict(status='passed',engine='Peddle MOS_6510',probe_cases=14,
                randomized_roundtrips=200,invalid_dma_requests=len(rejects),
                noncontiguous_physical_banks=[31,7,255],profiles=[256,8,0],
                prg_sha256=report['sha256'],shim_bytes_verified=1024,
                limitations='C64 integration is covered separately by the VICE memory probe')
    (ROOT/'build/reu-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
finally:
    m.close()
