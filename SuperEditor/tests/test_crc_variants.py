"""Assembled CRC variants against binascii, with an explicit CPU cycle audit."""
import binascii
import hashlib
import json
from pathlib import Path
import random
import sys
BASELINE_SOURCE_SHA256='269e946cd81a28290cc576ea184f67cf745cf06d39b72c523a578bc67d9ca410'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from crc_variants_probe import CRCProbe
from crc_variants_tables import generate
from peddle import VENDOR
OUT=ROOT/'build/crc_variants';result_path=OUT/'result.json';result_path.unlink(missing_ok=True)
p=CRCProbe();s=p.s;variants=['crc_baseline_byte','crc256_byte','crc64_byte','crc256_bad_byte']
rng=random.Random(0xCC17)
# Exact previous CRC regression corpus:1280 systematic plus4096 seeded random.
old=[(seed,byte) for seed in [0,1,0x8000,0xFFFF,0x29B1] for byte in range(256)]
old += [(rng.randrange(65536),rng.randrange(256)) for _ in range(4096)]
assert len(old)==5376
stats={name:dict(instructions=set(),cycles=set(),crossings=set(),calls=0) for name in variants}

def run(name,seed,byte,**kwargs):
 result=p.call(name,a=byte,seed=seed,**kwargs);regs=result['regs']
 assert p.value()==binascii.crc_hqx(bytes([byte]),seed),(name,seed,byte,p.value())
 assert regs.y==kwargs.get('y',0x5A),(name,'Y',regs.y)
 assert regs.sp==((kwargs.get('sp',0xFD)+2)&255),(name,'SP',regs.sp)
 assert regs.p&0x0C==(0x04|(kwargs.get('decimal',0)<<3)),(name,'D/I',regs.p)
 item=stats[name];item['instructions'].add(result['instructions']);item['cycles'].add(result['audited_cycles']);item['crossings'].add(result['indexed_read_crossings']);item['calls']+=1
 return result
try:
 # Verify the cloned baseline instruction sequence has not silently diverged.
 def ops(text):return [line.split(';')[0].strip() for line in text.splitlines() if line.split(';')[0].strip()]
 production=(ROOT/'src/overlay/crc.s').read_text().split('se_crc_byte:',1)[1]
 baseline=(ROOT/'probes/crc_variants/variants.s').read_text().split('crc_baseline_byte:',1)[1].split('crc_baseline_end:',1)[0]
 baseline_ops=ops(baseline.replace('crc_value','se_crc_value'))
 assert hashlib.sha256('\n'.join(baseline_ops).encode()).hexdigest()=='63556536a6f701ffcb6e5c0501af9fe89e2054c07666a0dc169f69a4f2b3a2b4'
 current_production_matches_baseline=ops(production)==baseline_ops
 assert (OUT/'tables.inc').read_text()==generate()
 # All generated entries independently match Python's CCITT implementation.
 for index in range(256):
  expected=binascii.crc_hqx(bytes([index]),0)
  for low,high in [('crc256_lo','crc256_hi'),('crc256_bad_lo','crc256_bad_hi')]:
   actual=p.m.read(s[low]+index)|(p.m.read(s[high]+index)<<8);assert actual==expected
 for index in range(16):
  for stem,value in [('low',index),('high',index<<4)]:
   expected=binascii.crc_hqx(bytes([value]),0)
   assert p.m.read(s['crc64_'+stem+'_lo']+index)|(p.m.read(s['crc64_'+stem+'_hi']+index)<<8)==expected
 assert s['crc256_tables_end']-s['crc256_tables_start']==512
 assert s['crc64_tables_end']-s['crc64_tables_start']==64
 assert s['crc256_lo']%256==s['crc256_hi']%256==0
 assert all(s['crc64_'+stem+'_'+part]%16==0 for stem in ['low','high'] for part in ['lo','hi'])
 assert s['crc256_bad_lo']%256==s['crc256_bad_hi']%256==1

 # Poison and later compare every nonstate, nonstack application byte.
 for address,length in [(0,256),(0x0200,0x7E00),(0xA000,0x2100),(0xC102,0x4FE),(0xC600,1024)]:
  p.m.load(address,bytes((i*73+29)&255 for i in range(length)))
 protected=[(a,p.read(a,n)) for a,n in [(0,256),(0x0200,0x7E00),(0x8000,0x2000),(0xA000,0x2100),(0xC102,0x4FE),(0xC600,1024)]]
 p.m.write(s['crc_value']-1,0xA5);p.m.write(s['crc_value']+2,0x5A)
 # Refresh snapshots after intentional CRC-neighbor guard writes.
 protected=[(a,p.read(a,len(value))) for a,value in protected]
 calibration=p.call('crc_clock_calibration',trace=True)
 assert calibration['instructions']==3 and calibration['audited_cycles']==10
 assert calibration['exposed_clock_delta']==0
 for name in variants:
  p.call('crc_init');assert p.value()==0xFFFF
  for index,(seed,byte) in enumerate(old):
   run(name,seed,byte,y=(index*73+29)&255,carry=index&1)
   assert p.m.read(s['crc_value']-1)==0xA5 and p.m.read(s['crc_value']+2)==0x5A
 print('All5376 original vectors pass for each assembled variant;Y and CRC guards intact.',flush=True)

 # Carry/decimal independence, all possible Y, and stack wrapping/depth boundaries.
 stack_cases=0
 for name in variants:
  for y in range(256):
   for carry in (0,1):
    for sp in [0,1,0x7F,0xFC,0xFD,0xFE,0xFF]:
     stack=bytes((i*11+y)&255 for i in range(256));p.m.load(0x100,stack)
     seed=((y*257)^0xBEEF)&65535;byte=(y*37+carry)&255
     result=run(name,seed,byte,y=y,carry=carry,sp=sp,decimal=y&1)
     expected=bytearray(stack);expected[(sp+1)&255]=0xFE;expected[(sp+2)&255]=0x02
     if name=='crc64_byte':
      # Its only extra stack write is PHA's partial low result at entry SP.
      expected[sp]=p.m.read(0x100+sp)
     assert p.read(0x100,256)==bytes(expected),(name,y,carry,sp,'unexpected stack write')
     stack_cases+=1
 print('Carry/decimal/Y, stack wrap and single transient nibble-stack-byte checks pass.',flush=True)

 # Large payload CRC, chunk boundaries and byte offsets around page/bank sizes.
 payload_lengths=[0,1,2,15,16,255,256,257,4095,4096,4097,65535,65536,65537]
 payload_checks=0;payload_bytes=0
 payload=bytes(((i*73+29)^(i>>8)^(i>>16))&255 for i in range(max(payload_lengths)))
 for name in variants[:3]:
  for length in payload_lengths:
   source=payload[:length];p.call('crc_init')
   offset=0
   # Alternate host chunks to hit both table indexes and input-page boundaries.
   for chunk in [1,255,256,4095,4096,65536]:
    stop=min(length,offset+chunk)
    for i in range(offset,stop):
     result=p.call(name,a=source[i],y=i&255,carry=i&1)
     assert result['regs'].y==(i&255)
     assert result['instructions']==next(iter(stats[name]['instructions']))
     assert result['audited_cycles']==next(iter(stats[name]['cycles']))
    offset=stop
   assert offset==length
   assert p.value()==binascii.crc_hqx(source,0xFFFF),(name,length,hex(p.value()))
   payload_checks+=1;payload_bytes+=length
  p.call('crc_init')
  for byte in b'123456789':p.call(name,a=byte)
  assert p.value()==0x29B1
 print('Published29B1 vector and payloads through65537 bytes pass across page/bank boundaries.',flush=True)

 # Trace every lookup index once. Aligned reads never incur a page-cross cycle.
 # Offset1 diagnostic incurs one extra cycle for each of the two reads at255.
 alignment={};traces={}
 for name in variants:
  per_index=[]
  for index in range(256):
   result=run(name,0,index,trace=index in (0,15,16,254,255))
   per_index.append(result['audited_cycles'])
   if result['trace']:traces[name+'_'+str(index)]=result['trace']
  alignment[name]=dict(min_cycles=min(per_index),max_cycles=max(per_index),page_cross_penalty_indexes=[i for i,c in enumerate(per_index) if c!=min(per_index)])
 assert alignment['crc256_bad_byte']['page_cross_penalty_indexes']==[255]
 assert stats['crc_baseline_byte']['instructions']=={34} and stats['crc_baseline_byte']['cycles']=={96}
 assert stats['crc256_byte']['instructions']=={8} and stats['crc256_byte']['cycles']=={32}
 assert stats['crc64_byte']['instructions']=={22} and stats['crc64_byte']['cycles']=={75}
 assert stats['crc256_bad_byte']['instructions']=={8} and stats['crc256_bad_byte']['cycles']=={32,34}
 for a,expected in protected:assert p.read(a,len(expected))==expected,hex(a)

 source_files=sorted([* (ROOT/'probes/crc_variants').glob('*'),* (ROOT/'tools').glob('crc_variants*.py'),Path(__file__).resolve()])
 code_bytes={name:s[name.replace('_byte','_end')]-s[name] for name in variants}
 measured={name:{'instructions':sorted(v['instructions']),'audited_cycles_including_rts':sorted(v['cycles']),'cycles_including_callers_jsr':sorted(c+6 for c in v['cycles']),'indexed_page_crossings':sorted(v['crossings']),'vector_and_stack_calls':v['calls'],'update_code_bytes':code_bytes[name],'table_bytes':0 if name=='crc_baseline_byte' else 64 if name=='crc64_byte' else 512,'additional_ram_scratch_bytes':0,'additional_zero_page_bytes':0,'additional_transient_stack_bytes':int(name=='crc64_byte')} for name,v in stats.items()}
 result=dict(status='passed',engine='Peddle MOS_6510',probe_sha256=hashlib.sha256((OUT/'probe.bin').read_bytes()).hexdigest(),source_sha256={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in source_files if f.is_file()},production_baseline_source_sha256=BASELINE_SOURCE_SHA256,current_production_source_sha256=hashlib.sha256((ROOT/'src/overlay/crc.s').read_bytes()).hexdigest(),current_production_matches_baseline=current_production_matches_baseline,peddle_wrapper_sha256=hashlib.sha256((VENDOR/'zeropage_peddle.cpp').read_bytes()).hexdigest(),reference='binascii.crc_hqx',old_vectors_per_variant=len(old),variants=measured,published_vector='29b1',large_payload_checks=payload_checks,large_payload_bytes=payload_bytes,large_payload_lengths=payload_lengths,stack_and_y_cases=stack_cases,protected_ram_bytes=sum(len(v) for _,v in protected),shim_bytes_verified=1024,clock_calibration=dict(instructions=calibration['instructions'],audited_cycles=calibration['audited_cycles'],exposed_clock_delta=calibration['exposed_clock_delta'],runtime_clock_usable=False),cycle_method='Exact static NMOS6502/6510 opcode/addressing-cycle audit of executed traces; RTS included, caller JSR separately +6, indexed page-cross read penalties included; no runtime cycle counter or VIC/DMA/IRQ stalls.',table_addresses={name:s[name] for name in ['crc256_lo','crc256_hi','crc64_low_lo','crc64_low_hi','crc64_high_lo','crc64_high_hi','crc256_bad_lo','crc256_bad_hi']},alignment=alignment,body_cycles_per_4096_bytes={'baseline':96*4096,'full_table':32*4096,'nibble_table':75*4096},limitations=['Standalone probe; production CRC not replaced.','512B table requires both array starts page-aligned; link padding excluded from code+table byte figures.','64B table requires16-byte alignment and one transient stack byte.','Static CPU-cycle audit does not measure native overlay latency.'])
 (OUT/'traces.json').write_text(json.dumps(traces,indent=2)+'\n');result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:p.close()
