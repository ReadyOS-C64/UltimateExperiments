"""Execute emitted overlay cache/trampolines and independently wrapped images."""
import binascii
import json
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from overlays import wrap as make_image, HEADER
r=json.loads((ROOT/'build/overlay-probe-report.json').read_text());s=r['symbols']
digest=bytes.fromhex(r['resident_binding']['digest'])
capacity=s['se_overlay_capacity']
(ROOT/'build/overlay-test-result.json').unlink(missing_ok=True)
def wrap(payload,slot,identity,entry=16):
    if len(payload)<4096:payload=digest+payload
    return make_image(payload,slot,identity,entry,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=digest)
m=Machine()

def read(address,length):
    return bytes(m.read(address+i) for i in range(length))
def word(name,value):
    m.load(s[name],value.to_bytes(2,'little'))
def call(name,a=0,x=0,y=0,error=None):
    regs,_=m.call(s[name],a=a,x=x,y=y)
    if error is None:
        assert not regs.p&1,(name,hex(regs.a))
    else:
        assert regs.p&1 and regs.a==error,(name,hex(regs.a),error)
    return regs.a

def import_image(image,error=None):
    m.load(s['se_overlay_header'],bytes(image[:HEADER]));m.load(0x5000,bytes(image[HEADER:]))
    return call('se_overlay_import',error=error)

try:
    image=(ROOT/'build/overlay-probe.prg').read_bytes()
    m.load(int.from_bytes(image[:2],'little'),image[2:])
    m.call(s['se_clear_state']);word('se_reu_banks',256)
    sentinel=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,sentinel)
    call('se_reu_provider_init')
    call('se_reu_bind',4,200,1) # force asset logical1 -> physical2
    call('se_overlay_init')
    assert m.read(s['se_overlay_asset'])==1 and m.read(s['se_reu_map']+1)==2
    call('se_overlay_init',error=0x18)
    # Independent published CRC vector.
    m.call(s['se_crc_init'])
    for b in b'123456789':
        m.call(s['se_crc_byte'],a=b)
    assert read(s['se_crc_value'],2)==b'\xb1\x29'
    for name in ['rone','rtwo','cone','rnest']:
        import_image((ROOT/f'build/overlays/{name}.seo').read_bytes())
    assert call('se_overlay_call',1,0)==0x41
    assert call('se_overlay_call',1,0)==0x41
    assert call('se_overlay_call',2,0)==0x42
    assert call('se_overlay_call',1,1,error=0x43)==0x43
    assert call('se_overlay_call',3,0)==0x44
    assert read(s['se_overlay_frame'],5)==bytes([2,2,1,0x19,0x19])
    assert read(s['se_overlay_busy'],2)==b'\0\0'
    assert read(s['se_overlay_loads'],2)==b'\x04\0'
    assert read(s['se_overlay_hits'],2)==b'\x02\0'
    assert read(s['se_overlay_calls'],2)==b'\x06\0'
    call('se_overlay_call',99,0,error=0x17)
    call('se_overlay_call',0,0,error=0x12)
    call('se_overlay_call',1,2,error=0x12)
    m.write(s['se_overlay_busy']+1,1)
    call('se_overlay_call',1,1,error=0x19)
    import_image(wrap(b'\x60',0,90),error=0x19)
    m.write(s['se_overlay_busy']+1,0)
    import_image((ROOT/'build/overlays/rone.seo').read_bytes(),error=0x16)
    invalid=[]
    base=wrap(b'\x60',0,90)
    for offset,value,error in [(0,0,0x10),(4,3,0x11),(5,2,0x12),(6,0,0x12),
        (7,1,0x10),(14,1,0x10),(15,1,0x10),(8,0,0x13),
        (9,0x11,0x13),(10,1,0x13),(11,1,0x13),(12,0,0x10),(16,0,0x11),(19,0,0x11)]:
        bad=bytearray(base);bad[offset]=value
        previous=read(s['se_reu_dma_calls'],2)
        import_image(bad,error=error)
        assert read(s['se_reu_dma_calls'],2)==previous
        invalid.append(offset)
    for offset in range(20,36):
        bad=bytearray(base);bad[offset]^=1
        previous=read(s['se_reu_dma_calls'],2);import_image(bad,error=0x11)
        assert read(s['se_reu_dma_calls'],2)==previous
        invalid.append(offset)
    # A foreign compiled payload cannot acquire our seal by a new header/CRC.
    bad=bytearray(base);bad[HEADER]^=1
    bad[12:14]=binascii.crc_hqx(bad[HEADER:],0xFFFF).to_bytes(2,'little')
    bad[14:16]=binascii.crc_hqx(bad[:14]+bad[16:HEADER],0xFFFF).to_bytes(2,'little')
    previous=read(s['se_reu_dma_calls'],2);import_image(bad,error=0x11)
    assert read(s['se_reu_dma_calls'],2)==previous
    # Semantically valid corrupted metadata cannot redirect a valid payload.
    for offset,value in [(5,1),(6,91)]:
        bad=bytearray(base);bad[offset]=value
        import_image(bad,error=0x10)
        invalid.append(offset)
    # 4096-byte full slot, nonzero entry, no off-by-one at BFFF or 5FFF.
    rng=random.Random(6502)
    payload=bytearray(rng.randbytes(4096));payload[:16]=digest;payload[-4:]=b'\xA9\x45\x18\x60'
    import_image(wrap(payload,1,90,4092))
    m.write(0xC000,0x53)
    assert call('se_overlay_call',90,1)==0x45
    assert read(0xB000,4096)==payload
    assert m.read(0xC000)==0x53 and m.read(0x6000)==0
    # Corrupt cached inactive RONE through the checked REU API. Failed load
    # must leave RNEST and its active tag intact, and cannot execute bad code.
    previous=read(0xA000,4096);active=read(s['se_overlay_active'],2)
    m.write(0x5000,0)
    m.write(s['se_reu_logical'],m.read(s['se_overlay_asset']))
    word('se_reu_c64',0x5000);word('se_reu_length',1);word('se_reu_offset',16)
    call('se_reu_copy',0)
    call('se_overlay_call',1,0,error=0x14)
    assert read(0xA000,4096)==previous and read(s['se_overlay_active'],2)==active
    assert call('se_overlay_call',3,0)==0x44
    for identity in range(100,100+capacity-5):
        import_image(wrap(b'\x60',0,identity))
    before=read(s['se_reu_dma_calls'],2)
    import_image(wrap(b'\x60',0,200),error=0x15)
    assert read(s['se_reu_dma_calls'],2)==before
    # Old cache descriptors cannot survive a provider epoch transition.
    call('se_reu_provider_init')
    call('se_overlay_call',3,0,error=0x18)
    call('se_overlay_init')
    call('se_overlay_call',3,0,error=0x17)
    assert read(0xC600,1024)==sentinel
    result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=r['sha256'],
        invalid_headers_or_checksums=len(invalid),full_slot_bytes=4096,abi=2,
        complete_resident_binding=True,foreign_payload_rejected_before_dma=True,
        corruption_preserved_active_slot=True,nested_command_to_renderer=True,
        same_slot_and_renderer_to_command_rejected=True,provider_epoch_checked=True,
        catalog_capacity=capacity,nonidentity_asset_mapping=True,shim_bytes_verified=1024)
    (ROOT/'build/overlay-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
finally:
    m.close()
