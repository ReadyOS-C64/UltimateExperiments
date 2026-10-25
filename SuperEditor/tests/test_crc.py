"""Table-free CCITT update against Python's independent C implementation."""
import binascii
import json
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
r=json.loads((ROOT/'build/overlay-probe-report.json').read_text());s=r['symbols'];m=Machine()
result_path=ROOT/'build/crc-test-result.json';result_path.unlink(missing_ok=True)
try:
 m.load(0x801,(ROOT/'build/overlay-probe.prg').read_bytes()[2:]);address=s['se_crc_value']
 m.write(address-1,0xA5);m.write(address+2,0x5A)
 shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim)
 rng=random.Random(0xCC17);cases=[(seed,byte) for seed in [0,1,0x8000,0xFFFF,0x29B1] for byte in range(256)]
 cases += [(rng.randrange(65536),rng.randrange(256)) for _ in range(4096)]
 counts=[]
 for seed,byte in cases:
  m.load(address,seed.to_bytes(2,'little'));regs,used=m.call(s['se_crc_byte'],a=byte,y=0x5A)
  actual=m.read(address)|(m.read(address+1)<<8)
  assert actual==binascii.crc_hqx(bytes([byte]),seed),(seed,byte,actual)
  assert regs.y==0x5A and m.read(address-1)==0xA5 and m.read(address+2)==0x5A
  counts.append(used)
 m.call(s['se_crc_init'])
 for byte in b'123456789':m.call(s['se_crc_byte'],a=byte)
 assert m.read(address)|(m.read(address+1)<<8)==0x29B1
 assert len(set(counts))==1
 assert bytes(m.read(0xC600+i) for i in range(1024))==shim
 result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=r['sha256'],update_cases=len(cases),
  independent_reference='binascii.crc_hqx',published_vector='29b1',preserved_y=True,
  instructions_per_update=min(counts),constant_instruction_count=len(set(counts))==1,
  tables_and_extra_scratch_bytes=0,shim_bytes_verified=1024)
 result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:m.close()
