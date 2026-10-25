"""Measured 12→16 overlay catalog proposal, isolated from the editor build.

Only a copied format.inc constant changes in the candidate. Actual cache/header/
fastCRC/provider/DMA code is assembled unchanged. This proves the one-bank edge,
not production integration, VICE or extra editor functionality.
"""
from pathlib import Path
import hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from overlays import wrap,HEADER
OUT=ROOT/'build/overlay-capacity';OUT.mkdir(exist_ok=True)
MODULES=['src/overlay/cache.s','src/overlay/header.s','src/overlay/crc_fast.s','src/reu/provider.s','src/reu/dma.s']
def command(args):subprocess.run(args,cwd=ROOT,check=True,capture_output=True,text=True)
def variant(capacity):
 out=OUT/str(capacity);(out/'include/overlay').mkdir(parents=True,exist_ok=True)
 fmt=(ROOT/'src/overlay/format.inc').read_text()
 fmt,count=re.subn(r'^OVL_LIMIT = [0-9]+$',f'OVL_LIMIT = {capacity}',fmt,flags=re.M);assert count==1
 (out/'include/overlay/format.inc').write_text(fmt)
 (out/'stub.s').write_text('''.setcpu "6502"
.export se_reu_banks,se_overlay_binding_digest
.segment "BSS"
se_reu_banks: .res 2
.segment "RODATA"
se_overlay_binding_digest: .byte 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
''')
 (out/'probe.cfg').write_text('''MEMORY {
 Z:file="",start=$0002,size=$001A,type=rw;
 C:file=%O,start=$1000,size=$3000,type=rw;
 S:file="",start=$C000,size=$0600,type=rw,define=yes;
}
SEGMENTS {
 ZEROPAGE:load=Z,type=zp;
 CODE:load=C,type=ro;
 RODATA:load=C,type=ro;
 CRC_TABLE:load=C,type=ro,align=$100;
 BSS:load=S,type=bss,define=yes;
}
''')
 objects=[]
 for i,name in enumerate(MODULES+[str(out/'stub.s')]):
  obj=out/f'{i}.o';command(['ca65','-g','-D','FAST_EDITOR_CRC=1','-I',str(out/'include'),'-I','src','-o',str(obj),name]);objects.append(obj)
 command(['ld65','-C',str(out/'probe.cfg'),'-o',str(out/'probe.bin'),'-Ln',str(out/'probe.lbl'),'-m',str(out/'probe.map'),*map(str,objects)])
 s={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(out/'probe.lbl').read_text())}
 m=Machine();m.load(0x1000,(out/'probe.bin').read_bytes())
 def read(address,count):return bytes(m.read(address+i) for i in range(count))
 def put(name,value,width=1):m.load(s[name],value.to_bytes(width,'little'))
 def get(name,width=1):return int.from_bytes(read(s[name],width),'little')
 def call(name,a=0,x=0,y=0,error=None):
  r,_=m.call(s[name],a=a,x=x,y=y,limit=2_000_000)
  assert bool(r.p&1)==(error is not None),(name,r.a,r.p,error)
  if error is not None:assert r.a==error,(name,r.a,error)
  return r.a
 def image(identity,slot):
  payload=bytes(range(16))+bytes((i*31+identity)&255 for i in range(16,4092))+bytes([0xA9,identity,0x18,0x60])
  return wrap(payload,slot,identity,4092,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes(range(16)))
 def imported(data,error=None):
  m.load(s['se_overlay_header'],data[:HEADER]);m.load(0x5000,data[HEADER:]);return call('se_overlay_import',error=error)
 try:
  shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim)
  put('se_reu_banks',8,2);call('se_reu_provider_init');call('se_reu_bind',4,200,1);call('se_overlay_init')
  assert get('se_overlay_asset')==1 and m.read(s['se_reu_map']+1)==2
  expected=bytearray(8*65536);images=[]
  for i in range(capacity):
   data=image(i+1,i&1);images.append(data);imported(data)
   expected[2*65536+i*4096:2*65536+(i+1)*4096]=data[HEADER:]
  assert read(s['se_overlay_ids'],capacity)==bytes(range(1,capacity+1))
  before=get('se_reu_dma_calls',2);imported(image(200,0),error=0x15);assert get('se_reu_dma_calls',2)==before
  for i in list(reversed(range(capacity)))+list(range(capacity)):
   slot=i&1;assert call('se_overlay_call',i+1,slot)==i+1
   assert read(0xA000+slot*4096,4096)==images[i][HEADER:]
  assert bytes(m.lib.zeropage_peddle_read_reu(m.handle,i) for i in range(8*65536))==expected
  # Last candidate reaches exactly65536, never the neighboring physical bank.
  offset=(capacity-1)*4096+4095
  put('se_reu_logical',get('se_overlay_asset'));put('se_reu_c64',0x7000,2);put('se_reu_offset',offset,2);put('se_reu_length',1,2)
  m.write(0x7000,images[-1][-1]^1);call('se_reu_copy')
  # Force another image into the same slot so the corrupted one must reload.
  call('se_overlay_call',capacity-2,(capacity-1)&1)
  active=read(s['se_overlay_active'],2);previous=read(0xA000+((capacity-1)&1)*4096,4096)
  call('se_overlay_call',capacity,(capacity-1)&1,error=0x14)
  assert read(s['se_overlay_active'],2)==active and read(0xA000+((capacity-1)&1)*4096,4096)==previous
  expected[2*65536+offset]^=1
  assert bytes(m.lib.zeropage_peddle_read_reu(m.handle,i) for i in range(8*65536))==expected
  assert read(0xC600,1024)==shim
  return dict(capacity=capacity,bss=s['__BSS_SIZE__'],probe_bytes=(out/'probe.bin').stat().st_size,
              code_sha256=hashlib.sha256((out/'probe.bin').read_bytes()).hexdigest(),
              last_slot_offset=(capacity-1)*4096,full_bank_end=capacity*4096,
              checked_reu_bytes=8*65536,shim_bytes=1024,corrupt_last_slot_preserves_active=True)
 finally:m.close()
results=[variant(12),variant(16)];assert results[1]['bss']-results[0]['bss']==32
production=json.loads((ROOT/'build/editor-report.json').read_text())
result=dict(ok=True,variants=results,additional_resident_state=32,
            baseline_editor_bss=production['state_bytes'],
            baseline_editor_catalog=production['symbols']['se_overlay_capacity'],
            projected_editor_bss=production['state_bytes']+(16-production['symbols']['se_overlay_capacity'])*8,
            projected_editor_bss_free=0x600-production['state_bytes']-(16-production['symbols']['se_overlay_capacity'])*8,
            source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in MODULES+['src/overlay/format.inc']},
            scope='Isolated constant-override12/16 comparison; production integration has its own report; no VICE')
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
