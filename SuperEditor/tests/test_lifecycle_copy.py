"""PRIVATE exact-extent 6510 copy/thunk proof; no editor suspend integration.

The fixture has TWO independently linked images of the actual copier. Capture
runs at E000 (outside warm RAM); fresh restore validation runs at A000 and is
overwritten by the snapshot's unrelated A000 bytes. Only the copied0900 thunk
then executes until its restored1100 fresh-entry transfer. Host DMA is used only
to seed/corrupt test inputs, never to emulate the routine under test.
"""
from pathlib import Path
import argparse,binascii,ctypes as C,hashlib,json,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine,VENDOR
FC,PHYSICAL=88,70
EXTENTS=((0x1000,0xB600,0),(0xCA00,0x600,0xB600),(2,24,0xBC00))
def crc(b):return binascii.crc_hqx(b,0xFFFF)
def command(*args):
 p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True)
 if p.returncode:raise AssertionError(p.stdout+p.stderr)
def build(out):
 out.mkdir(parents=True,exist_ok=True)
 (out/'stub.s').write_text('.export se_reu_banks\n.segment "BSS"\nse_reu_banks:.res 2\n')
 objs=[]
 for n,p in [('copy','src/lifecycle/probe-copy.s'),('provider','src/reu/provider.s'),('stub',out/'stub.s')]:
  o=out/(n+'.o');command('ca65','-g','-I','src','-o',o,p);objs.append(o)
 results={}
 for origin in (0xA000,0xE000):
  tag=f'{origin:04x}';cfg=out/(tag+'.cfg')
  cfg.write_text(f'MEMORY {{ C:file=%O,start=${origin:04X},size=$1000; B:file="",start=$C000,size=$600; }} SEGMENTS {{ CODE:load=C,type=ro; RODATA:load=C,type=ro; BSS:load=B,type=bss; }}')
  command('ld65','-C',cfg,'-o',out/(tag+'.bin'),'-Ln',out/(tag+'.lbl'),'-m',out/(tag+'.map'),*objs)
  s={x[2].lstrip('.'):int(x[1],16) for line in (out/(tag+'.lbl')).read_text().splitlines() if len(x:=line.split())==3 and x[0]=='al'}
  results[origin]=(s,(out/(tag+'.bin')).read_bytes())
 return results

class Fixture:
 def __init__(self,out,images):
  self.images=images;self.m=Machine();self.calls=[]
  (out/'runner.cpp').write_text(r'''#include "zeropage_peddle.h"
#include <cstdint>
static uint8_t low=255;static uint32_t cold=0;static bool first=false;static uint32_t entry=0,commands=0,bytes=0;
extern "C" uint64_t lc_run(ZeroPagePeddle*m){auto b=zeropage_peddle_regs(m).instructions;low=255;cold=0;first=false;entry=0;commands=0;bytes=0;for(uint32_t i=0;i<3000000;i++){auto r=zeropage_peddle_regs(m);if(r.sp<low)low=r.sp;if(r.pc==0x2ff)return r.instructions-b;if(r.pc>=0x900&&r.pc<0xa00)cold++;if(r.pc==0x900)first=true;if(r.pc==0x1100&&first)entry=(r.a==0&&r.sp==255&&!(r.p&1))?1:2;
if(zeropage_peddle_read(m,r.pc)==0x8d&&zeropage_peddle_read(m,r.pc+1)==1&&zeropage_peddle_read(m,r.pc+2)==0xdf){commands++;bytes+=zeropage_peddle_read(m,0xdf07)+(zeropage_peddle_read(m,0xdf08)<<8);}
zeropage_peddle_step_instruction(m);}return 0;}
extern "C" uint32_t lc_info(int n){return n==0?low:n==1?cold:n==2?first:n==3?entry:n==4?commands:bytes;}
extern "C" void lc_ram(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read(m,a+i);}
extern "C" void lc_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read_reu(m,i);}
extern "C" void lc_bank(ZeroPagePeddle*m,uint8_t bank,const uint8_t*p){for(uint32_t off=0;off<65536;off+=4096){zeropage_peddle_load(m,0xe000,p+off,4096);zeropage_peddle_write(m,0xdf02,0);zeropage_peddle_write(m,0xdf03,0xe0);zeropage_peddle_write(m,0xdf04,off&255);zeropage_peddle_write(m,0xdf05,off>>8);zeropage_peddle_write(m,0xdf06,bank);zeropage_peddle_write(m,0xdf07,0);zeropage_peddle_write(m,0xdf08,16);zeropage_peddle_write(m,0xdf09,0);zeropage_peddle_write(m,0xdf0a,0);zeropage_peddle_write(m,0xdf01,0x90);}}
''')
  ext='.dylib' if sys.platform=='darwin' else '.so';lib=out/('runner'+ext)
  command('clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),out/'runner.cpp',ROOT/('build/libse_peddle'+ext),'-o',lib)
  self.r=C.CDLL(str(lib));self.r.lc_run.argtypes=[C.c_void_p];self.r.lc_run.restype=C.c_uint64
  self.r.lc_info.argtypes=[C.c_int];self.r.lc_info.restype=C.c_uint32
  self.r.lc_ram.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];self.r.lc_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p];self.r.lc_bank.argtypes=[C.c_void_p,C.c_uint8,C.c_void_p]
  # Nonzero patterns in every physical bank, not just blank foreign memory.
  for bank in range(256):self.bankwrite(bank,bytes((i*13+(i>>8)*7+bank*11)&255 for i in range(65536)))
  self.m.load(0,bytes((i*73+(i>>8)*19+31)&255 for i in range(65536)))
  self.m.load(0xC000,bytes(0x600));self.m.write(0,0x2F);self.m.write(1,0x35)
  self.ports(0x2F,0x35)
  self.origin=0xE000;self.load_image(self.origin);s=self.s
  self.m.load(s['se_reu_banks'],b'\0\1');assert not self.call('se_reu_provider_init').p&1
  assert not self.call('se_reu_bind',a=0xFC,x=FC,y=PHYSICAL).p&1
  descriptor=bytes([FC,PHYSICAL])+self.read(s['se_reu_epoch'],2)+bytes(range(1,17))+(0x1100).to_bytes(2,'little')+bytes(10)
  self.m.load(0x800,descriptor);self.m.load(0x1100,b'\xa9\x7e\x8d\x60\x08\x4c\xff\x02')
 def load_image(self,origin):self.origin=origin;self.s,self.image=self.images[origin];self.m.load(origin,self.image)
 def read(self,a,n):
  b=C.create_string_buffer(n);self.r.lc_ram(self.m.handle,a,n,b);return b.raw
 def reu(self):
  b=C.create_string_buffer(16*1024*1024);self.r.lc_reu(self.m.handle,len(b),b);return b.raw
 def bankwrite(self,bank,data):
  saved=self.read(0xE000,4096) if hasattr(self,'r') else None
  b=C.create_string_buffer(bytes(data));self.r.lc_bank(self.m.handle,bank,b)
  if saved is not None:self.m.load(0xE000,saved)
 def ports(self,ddr,port):
  # Real6510 has internal ports, distinct from host RAM reads0/1 in Peddle.
  self.m.load(0x2D0,bytes([0xA9,ddr,0x85,0,0xA9,port,0x85,1,0x4C,0xFF,2]))
  self.m.lib.zeropage_peddle_set_pc(self.m.handle,0x2D0);assert self.r.lc_run(self.m.handle)
 def call(self,n,a=0,x=0,y=0,p=0x24):
  for k,v in [('a',a),('x',x),('y',y),('p',p),('sp',0xFD),('pc',self.s[n])]:getattr(self.m.lib,'zeropage_peddle_set_'+k)(self.m.handle,v)
  self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);before=self.m.regs();used=self.r.lc_run(self.m.handle);r=self.m.regs()
  assert used,('no completion',n,hex(r.pc));self.calls.append(dict(name=n,instructions=used,min_sp=self.r.lc_info(0),thunk_instructions=self.r.lc_info(1),thunk_entered=self.r.lc_info(2),fresh_entry_contract=self.r.lc_info(3),dma_commands=self.r.lc_info(4),dma_bytes=self.r.lc_info(5)))
  return r
 def close(self):self.m.close()

def expected_header(ram,desc):
 payload=b''.join(ram[c:c+n] for c,n,_ in EXTENTS);h=bytearray(b'LCP1'+bytes([1,0xA5,3,0xFC])+desc[:22])
 h+=bytes.fromhex('18bc00')
 for c,n,o in EXTENTS:h+=c.to_bytes(2,'little')+n.to_bytes(2,'little')+o.to_bytes(2,'little')
 h+=crc(payload).to_bytes(2,'little')+bytes(9);h+=crc(h).to_bytes(2,'little');assert len(h)==64
 return payload,bytes(h)

def guard_ram(before,after,restored=None,thunk=False):
 want=bytearray(before)
 for lo,hi in [(0x100,0x200),(0x700,0x800),(0x820,0x828),(0x880,0x8C0),(0xDF00,0xDF0B)]+([(0x900,0x900+158),(0x860,0x861)] if thunk else []):want[lo:hi]=after[lo:hi]
 if restored:
  for c,n,_ in EXTENTS:want[c:c+n]=restored[c:c+n]
 assert after==want,('wholeRAM',next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,want)) if a!=b))

def run(out,smoke=False):
 images=build(out/'leaf');f=Fixture(out/'leaf',images);faults=[]
 try:
  ram=f.read(0,65536);reu=f.reu();desc=f.read(0x800,32);payload,h=expected_header(ram,desc)
  r=f.call('se_lcp_capture');assert not r.p&1 and r.a==0,(r.a,r.p)
  guard_ram(ram,f.read(0,65536));captured=f.reu();want=bytearray(reu);base=PHYSICAL*65536
  want[base:base+len(payload)]=payload;want[base+0xBC20:base+0xBC60]=h
  assert captured==want,'whole16MiB capture/padding guard'
  bank=captured[base:base+65536]
  # Warm self-overwrite proof: validation livesA000; capturedA000 is unrelated.
  for c,n,_ in EXTENTS:f.m.load(c,bytes((i*23+17)&255 for i in range(n)))
  for field in ('se_reu_map','se_reu_logical_owner','se_reu_physical_owner'):
   at=f.s[field];f.m.load(at,ram[at:at+256])
  at=f.s['se_reu_epoch'];f.m.load(at,ram[at:at+3]);f.load_image(0xA000)
  before=f.read(0,65536);assert before[0xA000:0xA100]!=ram[0xA000:0xA100]
  r=f.call('se_lcp_restore');assert not r.p&1 and r.a==0x7E and r.sp==255 and f.m.read(0x860)==0x7E,(r.a,r.p,r.sp,hex(r.pc),f.calls[-1])
  guard_ram(before,f.read(0,65536),ram,True);assert f.reu()==captured
  assert f.calls[-1]['thunk_entered'] and f.calls[-1]['thunk_instructions']>60 and f.calls[-1]['fresh_entry_contract']==1
  print('FIRST LIFECYCLE COPY PASS: exact48152B capture +CRC/provider validation +fresh0900 self-overwrite thunk +restored1100 entry/SPFF; shim/wholeRAM/16MiBREU guards',flush=True)
  restored=f.read(0,65536)
  def error(expected):
   f.load_image(0xA000);a=f.read(0,65536);b=f.reu();r=f.call('se_lcp_restore')
   assert r.p&1 and r.a==expected,(expected,r.a,r.p)
   guard_ram(a,f.read(0,65536));assert f.reu()==b and not f.calls[-1]['thunk_entered']
  if not smoke:
   # Header corruptions MUST reject before any warm write, including bytes
   # outside recognized semantic fields; full header CRC covers every byte.
   for i in range(64):
    bad=bytearray(bank);bad[0xBC20+i]^=1;f.bankwrite(PHYSICAL,bad);error(0xD2)
   f.bankwrite(PHYSICAL,bank);faults.append('all64headerbyte corruptions reject beforewarmwrites')
   # RecomputedCRC cannot authorize geometry/schema/build/capability changes.
   for i in list(range(51))+list(range(53,62)):
    bad=bytearray(bank);bad[0xBC20+i]^=1;bad[0xBC5E:0xBC60]=crc(bad[0xBC20:0xBC5E]).to_bytes(2,'little');f.bankwrite(PHYSICAL,bad);error(0xD2)
   f.bankwrite(PHYSICAL,bank);faults.append('60semanticheader mutations withrecomputedCRC reject exactgeometry/identity/reserved')
   for i in (0,0x2FFF,0x4FFF,0x8FFF,0xB5FF,0xB600,0xBBFF,0xBC00,0xBC17):
    bad=bytearray(bank);bad[i]^=1;f.bankwrite(PHYSICAL,bad);error(0xD3)
   f.bankwrite(PHYSICAL,bank);faults.append('9payloadboundaries includingCAandZP rejectfullCRC beforewarmwrites')
   for i in (51,52):
    bad=bytearray(bank);bad[0xBC20+i]^=1;bad[0xBC5E:0xBC60]=crc(bad[0xBC20:0xBC5E]).to_bytes(2,'little');f.bankwrite(PHYSICAL,bad);error(0xD3)
   # A forged internally consistent CRC cannot grant ownership of unrelated
   # live allocations: the saved table bytes are also checked against live RAM.
   for field in ('se_reu_map','se_reu_logical_owner','se_reu_physical_owner'):
    bad=bytearray(bank);bad[f.s[field]-0x1000+33]^=0x80;bad[0xBC53:0xBC55]=crc(bad[:0xBC18]).to_bytes(2,'little');bad[0xBC5E:0xBC60]=crc(bad[0xBC20:0xBC5E]).to_bytes(2,'little');f.bankwrite(PHYSICAL,bad);error(0xD4)
   f.bankwrite(PHYSICAL,bank);faults.append('2forgedpayloadCRCfields +3internallyCRCconsistentbutforeignsavedprovidertables refuse')
   for field,n in [('se_reu_map',33),('se_reu_logical_owner',33),('se_reu_physical_owner',33)]:
    at=f.s[field]+n;old=f.m.read(at);f.m.write(at,old^0x80);error(0xD4);f.m.write(at,old)
   faults.append('all3liveprovider tables rejectchangedforeignallocation despitevalidFC')
   for address,value in [(0x800,0),(0x801,0),(0x801,71),(0x802,desc[2]^1),(f.s['se_reu_retired'],1),(f.s['se_reu_map']+FC,71),(f.s['se_reu_logical_owner']+FC,4),(f.s['se_reu_physical_owner']+PHYSICAL,4)]:
    old=f.m.read(address);f.m.write(address,value);error(0xD1);f.m.write(address,old)
   faults.append('8epoch/logical/physical/owner/retired capabilityfaults')
   for ddr,port in [(0,0x35),(0x2F,0x37)]:
    f.ports(ddr,port);error(0xD0);f.ports(0x2F,0x35)
   for address,value in [(0x815,0x0F),(0x815,0x40),(0x816,1),(0x81F,1)]:
    old=f.m.read(address);f.m.write(address,value);error(0xD0);f.m.write(address,old)
   old=f.read(0x804,16);f.m.load(0x804,bytes(16));error(0xD0);f.m.load(0x804,old)
   for p in (0x20,0x2C):
    f.load_image(0xA000);a=f.read(0,65536);b=f.reu();r=f.call('se_lcp_restore',p=p);assert r.p&1 and r.a==0xD0;guard_ram(a,f.read(0,65536));assert f.reu()==b
   faults.append('invalidCPUport/DDR/entry/reserved/build/I/D refusals')
   # CAPTURE admission must not invalidate a prior committed snapshot on error.
   old=f.m.read(0x800);f.m.write(0x800,0);a=f.read(0,65536);b=f.reu();r=f.call('se_lcp_capture');assert r.p&1 and r.a==0xD1;guard_ram(a,f.read(0,65536));assert f.reu()==b;f.m.write(0x800,old)
   faults.append('capturecapabilityrefusal leavespreviouscommit/wholeREU unchanged')
  sizes=re.search(r'copy.o:\s+CODE\s+Offs=\w+\s+Size=(\w+).*?RODATA\s+Offs=\w+\s+Size=(\w+)',(out/'leaf/a000.map').read_text(),re.S);code,rodata=(int(x,16) for x in sizes.groups())
  result=dict(status='passed',scope='PRIVATE assembled exact copier/provider/CRC/fresh thunk; no editor lifecycle/IRQ/NMI/display/ReadyOS integration',payload_bytes=len(payload),header_bytes=64,private_scratch='0700..07FF,0800..085F,0880..08BF,0900..09FF; stack; REU registers',code_bytes=code,rodata_bytes=rodata,bss_bytes=0,zp_bytes=0,linked_image_including_provider_bytes=len(images[0xA000][1]),thunk_bytes=images[0xA000][0]['se_lcp_thunk_size'],cpu_measurement='actual6510 instruction counts; Peddle wrapper cycles counter unavailable; no PAL/NTSC timing claim',fault_groups=faults,calls=f.calls[:4],total_calls=len(f.calls),source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('src/lifecycle/probe-copy.s','src/lifecycle/probe-copy.inc','tests/test_lifecycle_copy.py')})
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
 finally:f.close()

if __name__=='__main__':
 from datetime import datetime,timezone
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args();out=a.out or ROOT/'build/lifecycle-copy'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True,exist_ok=True);run(out,a.smoke)
