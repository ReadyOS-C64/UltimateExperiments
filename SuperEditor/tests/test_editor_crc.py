"""Verify fast CRC and page/tail admission loops in the actual sealed editor PRG.

No make, throwaway assembly, VICE, or production writes. Reference is independent
bitwise CCITT-FALSE. Reports remain separate from legacy CRC/probe artifacts.
"""
import hashlib
import json
from pathlib import Path
import random
import struct
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
OUT=ROOT/'build/editor-crc';OUT.mkdir(exist_ok=True);RESULT=OUT/'result.json';RESULT.unlink(missing_ok=True)
report=json.loads((ROOT/'build/editor-report.json').read_text());symbols=report['symbols'];prg=(ROOT/'build/editor.prg').read_bytes()
assert hashlib.sha256(prg).hexdigest()==report['sha256']
digest=bytes.fromhex(report['resident_binding']['digest'])

def ccitt(data,seed=0xFFFF):
 value=seed
 for byte in data:
  value^=byte<<8
  for _ in range(8):value=((value<<1)^0x1021 if value&0x8000 else value<<1)&65535
 return value

class Editor:
 def __init__(self):
  self.m=Machine();self.m.load(int.from_bytes(prg[:2],'little'),prg[2:]);self.page=symbols['se_overlay_crc_page_byte'];self.tail=symbols['se_overlay_crc_tail_byte']
 def close(self):self.m.close()
 def read(self,address,count):return bytes(self.m.read(address+i) for i in range(count))
 def get(self,name,size=1):return int.from_bytes(self.read(symbols[name],size),'little')
 def put(self,name,value,size=1):self.m.load(symbols[name],value.to_bytes(size,'little'))
 def call(self,name,a=0,x=0,y=0x5A,carry=0,sp=0xFD,monitor=False,error=None):
  for field,value in [('a',a),('x',x),('y',y),('p',0x24|carry),('sp',sp),('pc',symbols[name])]:getattr(self.m.lib,'zeropage_peddle_set_'+field)(self.m.handle,value)
  self.m.write(0x100+((sp+1)&255),0xFE);self.m.write(0x100+((sp+2)&255),0x02)
  before=self.m.regs();pages=[];tails=[];count=0
  while (regs:=self.m.regs()).pc!=0x02FF:
   assert count<1_000_000,(name,hex(regs.pc))
   if monitor and regs.pc in (self.page,self.tail):
    address=self.get('ovl_ptr',2)+regs.y
    (pages if regs.pc==self.page else tails).append(address)
   self.m.lib.zeropage_peddle_step_instruction(self.m.handle);count+=1
  assert regs.instructions-before.instructions==count
  if error is not None:assert regs.p&1 and regs.a==error,(name,regs.a,error)
  return regs,count,pages,tails
 def okay(self,name,*args,**kwargs):
  regs,count,pages,tails=self.call(name,*args,**kwargs);assert not regs.p&1,(name,hex(regs.a));return regs,count,pages,tails

def wrap(payload,identity=91,entry=16,slot=0,declared=None):
 size=len(payload) if declared is None else declared
 header=struct.pack('<4sBBBBHHHH',b'SEO2',2,slot,identity,0,size,entry,ccitt(payload),0)+struct.pack('<HH',symbols['se_overlay_call'],symbols['se_overlay_frame'])+digest
 checksum=ccitt(header[:14]+header[16:])
 return header[:14]+checksum.to_bytes(2,'little')+header[16:]+payload

def payload(size,tag=0x61,entry=16):
 data=bytearray(((i*73+29)^(i>>8))&255 for i in range(size));data[:min(16,size)]=digest[:min(16,size)]
 if size-entry>=4:data[entry:entry+4]=bytes([0xA9,tag,0x18,0x60])
 elif size-entry>=2:data[entry:entry+2]=bytes([0x18,0x60])
 elif size-entry==1:data[entry]=0x60
 return bytes(data)

crc=Editor();cache=None
try:
 # Actual PRG table admission: no dependency on calling cold initialization.
 low=symbols['se_crc_table_low'];high=symbols['se_crc_table_high'];value=symbols['se_crc_value'];entry=symbols['se_crc_byte']
 assert low%256==high%256==0 and high==low+256
 segment=next(p for p in report['segments'] if p['name']=='CRC_TABLE')
 assert segment['start']==low and segment['end']==high+255 and segment['size']==512
 assert 0x1000<=low<high+256<=0x4000
 for i in range(256):assert crc.m.read(low+i)|(crc.m.read(high+i)<<8)==ccitt(bytes([i]),0)
 # The emitted20-byte callable update uses the actual state and resident arrays.
 expected=bytes([0x4D])+struct.pack('<H',value+1)+bytes([0xAA,0xAD])+struct.pack('<H',value)+bytes([0x5D])+struct.pack('<H',high)+bytes([0x8D])+struct.pack('<H',value+1)+bytes([0xBD])+struct.pack('<H',low)+bytes([0x8D])+struct.pack('<H',value)+bytes([0x60])
 assert crc.read(entry,len(expected))==expected
 initregs,*_=crc.okay('se_crc_init');assert crc.get('se_crc_value',2)==0xFFFF
 crc.m.write(value-1,0xA5);crc.m.write(value+2,0x5A)
 shim=bytes((i*73+29)&255 for i in range(1024));crc.m.load(0xC600,shim)
 protected=[(a,crc.read(a,n)) for a,n in [(0,256),(0x0200,value-0x0200),(value+2,0xCA00-value-2)]]
 rng=random.Random(0xCC17);vectors=[(seed,byte) for seed in [0,1,0x8000,0xFFFF,0x29B1] for byte in range(256)]
 vectors += [(rng.randrange(65536),rng.randrange(256)) for _ in range(4096)]
 counts=set();y_stack_cases=0
 for index,(seed,byte) in enumerate(vectors):
  crc.put('se_crc_value',seed,2);y=(index*73+29)&255
  regs,count,_,_=crc.call('se_crc_byte',a=byte,y=y,carry=index&1)
  assert crc.get('se_crc_value',2)==ccitt(bytes([byte]),seed)
  assert regs.y==y and regs.sp==0xFF
  counts.add(count)
 for y in range(256):
  for carry in (0,1):
   for sp in [0,1,0x7F,0xFD,0xFE,0xFF]:
    stack=bytearray((i*11+y)&255 for i in range(256));crc.m.load(0x100,stack)
    seed=((y*257)^0xBEEF)&65535;byte=(y*37+carry)&255;crc.put('se_crc_value',seed,2)
    regs,count,_,_=crc.call('se_crc_byte',a=byte,y=y,carry=carry,sp=sp)
    assert crc.get('se_crc_value',2)==ccitt(bytes([byte]),seed) and regs.y==y and regs.sp==((sp+2)&255)
    stack[(sp+1)&255]=0xFE;stack[(sp+2)&255]=0x02;assert crc.read(0x100,256)==bytes(stack)
    counts.add(count);y_stack_cases+=1
 assert counts=={8}
 lengths=[0,1,2,15,16,255,256,257,4095,4096,4097,65535,65536,65537]
 source=bytes(((i*73+29)^(i>>8)^(i>>16))&255 for i in range(max(lengths)))
 stream_bytes=0
 for length in lengths:
  crc.okay('se_crc_init')
  for i,byte in enumerate(source[:length]):
   regs,count,_,_=crc.call('se_crc_byte',a=byte,y=i&255,carry=i&1)
   assert regs.y==(i&255) and count==8
  assert crc.get('se_crc_value',2)==ccitt(source[:length]);stream_bytes+=length
 crc.okay('se_crc_init')
 for byte in b'123456789':crc.call('se_crc_byte',a=byte)
 assert crc.get('se_crc_value',2)==0x29B1
 for a,expected_bytes in protected:assert crc.read(a,len(expected_bytes))==expected_bytes,hex(a)
 print('Actual editor callable fast CRC:5376 vectors,allY/carry/stack boundaries,large streams and protected RAM pass.',flush=True)

 # Exercise actual FAST_EDITOR_CRC page/tail loops through public import/call.
 cache=Editor();expected_reu=bytearray(8*65536);cache.m.load(0xC600,shim)
 sizes=[17,18,20,31,32,127,128,255,256,257,511,512,513,1023,1024,1025,2047,2048,2049,4095,4096]
 path_cases=[];corrupt_cases=[];rejects=[];prefix_reject=False
 def check_paths(pages,tails,n,label):
  count=(n//256)*256
  assert pages==list(range(0x5000,0x5000+count)),(label,'pages',len(pages),count)
  assert tails==list(range(0x5000+count,0x5000+n)),(label,'tails',len(tails),n-count)
 def image_import(image,error=None):
  cache.m.load(symbols['se_overlay_header'],image[:36]);cache.m.load(0x5000,image[36:36+4096])
  if error is None:return cache.okay('se_overlay_import',monitor=True)
  return cache.call('se_overlay_import',monitor=True,error=error)
 def patch(offset,byte):
  cache.put('se_reu_logical',cache.get('se_overlay_asset'));cache.put('se_reu_offset',offset,2);cache.put('se_reu_length',1,2);cache.put('se_reu_c64',0x7000,2);cache.m.write(0x7000,byte);cache.okay('se_reu_copy',a=0)
  expected_reu[2*65536+offset]=byte
 for n in sizes:
  cache.call('se_clear_state');cache.put('se_reu_banks',8,2);cache.okay('se_reu_provider_init');cache.okay('se_reu_bind',a=4,x=200,y=1);cache.okay('se_overlay_init')
  assert cache.get('se_overlay_asset')==1 and cache.m.read(symbols['se_reu_map']+1)==2
  guard=bytes((i*11+57)&255 for i in range(4096));cache.m.load(0xB000,guard)
  cache.m.write(0x4FFF,0xA5);cache.m.write(0x6000,0x5A)
  at=4092 if n==4096 else 16;data=payload(n,entry=at);image=wrap(data,entry=at)
  regs,used,pages,tails=image_import(image);check_paths(pages,tails,n,('import',n));expected_reu[2*65536:2*65536+n]=data
  regs,used,pages,tails=cache.okay('se_overlay_call',a=91,x=0,monitor=True);check_paths(pages,tails,n,('reload',n))
  assert cache.read(0xA000,n)==data
  if n-at>=4:assert regs.a==0x61
  before_dma=cache.get('se_reu_dma_calls',2);before_hits=cache.get('se_overlay_hits',2)
  regs,_,pages,tails=cache.okay('se_overlay_call',a=91,x=0,monitor=True)
  assert not pages and not tails and cache.get('se_reu_dma_calls',2)==before_dma and cache.get('se_overlay_hits',2)==before_hits+1
  replacement=payload(20,tag=0x62);image_import(wrap(replacement,identity=92));expected_reu[2*65536+4096:2*65536+4116]=replacement
  cache.okay('se_overlay_call',a=92,x=0)
  for offset in sorted(set([16,n-1]+([255] if n>255 else [])+([256] if n>256 else []))):
   patch(offset,data[offset]^1)
   active=cache.read(symbols['se_overlay_active'],2);resident=cache.read(0xA000,4096);loads=cache.get('se_overlay_loads',2);calls=cache.get('se_overlay_calls',2);dma=cache.get('se_reu_dma_calls',2);dma_bytes=cache.get('se_reu_dma_bytes',3)
   regs,_,pages,tails=cache.call('se_overlay_call',a=91,x=0,monitor=True,error=0x14);check_paths(pages,tails,n,('corrupt',n,offset))
   assert cache.read(symbols['se_overlay_active'],2)==active and cache.read(0xA000,4096)==resident
   assert cache.get('se_overlay_loads',2)==loads and cache.get('se_overlay_calls',2)==calls
   assert cache.get('se_reu_dma_calls',2)==dma+1 and cache.get('se_reu_dma_bytes',3)==dma_bytes+n
   assert cache.read(symbols['se_overlay_busy'],2)==bytes(2)
   patch(offset,data[offset]);cache.okay('se_overlay_call',a=91,x=0);cache.okay('se_overlay_call',a=92,x=0)
   corrupt_cases.append(dict(length=n,offset=offset))
  if n==4096:
   patch(0,data[0]^1);active=cache.read(symbols['se_overlay_active'],2);resident=cache.read(0xA000,4096)
   regs,_,pages,tails=cache.call('se_overlay_call',a=91,x=0,monitor=True,error=0x11)
   assert not pages and not tails and cache.read(symbols['se_overlay_active'],2)==active and cache.read(0xA000,4096)==resident
   patch(0,data[0]);prefix_reject=True
  assert cache.m.read(0x4FFF)==0xA5 and cache.m.read(0x6000)==0x5A and cache.read(0xB000,4096)==guard and cache.read(0xC600,1024)==shim
  path_cases.append(dict(length=n,page_bytes=n//256*256,tail_bytes=n%256,entry=at))
 # Public invalid-length/entry headers cannot reach either CRC loop or DMA.
 for declared,entry in [(0,16),(16,16),(4097,16),(20,15)]:
  image=wrap(payload(max(20,declared)),identity=93,entry=entry,declared=declared)
  before=cache.get('se_reu_dma_calls',2);active=cache.read(symbols['se_overlay_active'],2)
  regs,_,pages,tails=image_import(image,error=0x13)
  assert not pages and not tails and cache.get('se_reu_dma_calls',2)==before and cache.read(symbols['se_overlay_active'],2)==active
  rejects.append(dict(declared_length=declared,entry=entry,error=0x13))
 # Valid size but incorrect header CRC is rejected before the payload loop.
 bad=bytearray(wrap(payload(20),identity=93));bad[14]^=1;before=cache.get('se_reu_dma_calls',2)
 regs,_,pages,tails=image_import(bad,error=0x10);assert not pages and not tails and cache.get('se_reu_dma_calls',2)==before
 actual_reu=bytes(cache.m.lib.zeropage_peddle_read_reu(cache.m.handle,i) for i in range(8*65536));assert actual_reu==bytes(expected_reu),'whole private REU ownership/contents'
 assert cache.read(0xC600,1024)==shim
 print('Actual fast cache page/tail boundary imports/reloads,corruption rejection,active preservation and whole512KiB REU pass.',flush=True)
 result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=report['sha256'],resident_binding=report['resident_binding']['digest'],production_source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['src/overlay/crc_fast.s','src/overlay/crc_tables.inc','src/overlay/cache.s']},test_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),reference='Independent Python bitwise CCITT-FALSE poly1021/initFFFF,not production lookup tables',callable_code_bytes=20,table_bytes=512,table_addresses=dict(low=low,high=high),table_warm_in_prg=True,byte_instructions=8,old_vectors=len(vectors),all_y_carry_stack_cases=y_stack_cases,large_stream_lengths=lengths,large_stream_bytes=stream_bytes,published_vector='29b1',protected_callable_ram_bytes=sum(len(v) for _,v in protected),shim_bytes_verified=1024,fast_page_loop=symbols['se_overlay_crc_page_byte'],fast_tail_loop=symbols['se_overlay_crc_tail_byte'],exact_payload_address_cases=path_cases,cache_corruption_cases=corrupt_cases,cache_prefix_rejected_before_crc=prefix_reject,invalid_admissions_before_crc=rejects,header_crc_rejected_before_payload=True,cache_hit_avoids_crc_dma=True,failed_reload_only_staging_fetch=True,failed_reload_preserves_active_slot=True,private_reu_bytes_verified=8*65536,nonidentity_asset_mapping=True,limitations='Actual current editor CPU code/data/import/cache path verified; no VICE/video/IRQ/normal-clock latency or physical-key proof. Production fit/binding packaging and other editor suites remain root gates.')
 RESULT.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:
 crc.close()
 if cache:cache.close()
