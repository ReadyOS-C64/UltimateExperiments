"""Actual 6510 font store proof and explicit CPU-only font-pack installer seam.

install_font_pack bypasses ROM IEC streaming only. It executes the real logical
provider and checked REU DMA, and stamps READY only after exact bytes transfer.
It is not native/cold IEC acceptance evidence.
"""
from pathlib import Path
import hashlib,binascii,json,argparse,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
PACK_SHA='5a980ffdeb34cec91469414768a273aa0f842fe16c8fd4ccc89215459c617975'

sys.path.insert(0,str(ROOT/'tools'))
from font_fixture import install_font_pack

def build(out):
 out.mkdir(parents=True,exist_ok=True)
 def run(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True,capture_output=True)
 run(sys.executable,'tools/geos_font_store_meta.py','--pack','build/geos-font-catalog/font-pack.bin','--output',out/'geos-font-pack.inc')
 (out/'stub.s').write_text('.export se_reu_banks,se_overlay_loads\n.exportzp text_ptr,screen_ptr\ntext_ptr=$F0\nscreen_ptr=$F2\n.segment "BSS"\nse_reu_banks:.res2\nse_overlay_loads:.res2\n'.replace('.res2','.res 2'))
 (out/'fixture.cfg').write_text('MEMORY { C:file=%O,start=$1000,size=$3000,fill=yes; B:file="",start=$C000,size=$600; D:file="",start=$CBC0,size=$40; } SEGMENTS { CODE:load=C,type=ro; RODATA:load=C,type=ro; CRC_TABLE:load=C,type=ro,align=$100; BSS:load=B,type=bss,define=yes; FONT_STORE_STATE:load=D,type=bss; }')
 objs=[]
 for n,p in [('runtime','src/render/geos/font-store.s'),('import','src/render/geos/font-import.s'),('state','src/render/geos/font-store-state.s'),('provider','src/reu/provider.s'),('dma','src/reu/dma.s'),('crc','src/overlay/crc_fast.s'),('stub',out/'stub.s')]:
  obj=out/(n+'.o');run('ca65','-g','-I',out,'-I','src','-o',obj,p);objs.append(obj)
 run('ld65','-C',out/'fixture.cfg','-o',out/'fixture.bin','-Ln',out/'fixture.lbl','-m',out/'fixture.map',*objs)
 return {x[2].lstrip('.'):int(x[1],16) for line in (out/'fixture.lbl').read_text().splitlines() if len(x:=line.split())==3 and x[0]=='al'}

class Fixture:
 def __init__(self,out,s):
  sys.path.insert(0,str(ROOT/'tools'));from peddle import Machine,VENDOR
  import ctypes as C
  self.C=C;self.s=s;self.m=Machine();self.calls=0;self.instructions=0;self.peak=0
  # Run real CPU loop in C for bounded cold chunk/CRC tests, not Python perinstruction.
  (out/'runner.cpp').write_text(r'''#include "zeropage_peddle.h"
#include <cstdint>
struct IO {const uint8_t*data=nullptr;uint32_t size=0,pos=0,at=0;int fault=0,opens=0,closes=0,owned=0,chkins=0,clear=0,bad=0,reads=0,status=0,device=0,name=0;};static IO io;
extern "C" void gf_io(const uint8_t*p,uint32_t n,int fault,uint32_t at){io=IO{};io.data=p;io.size=n;io.fault=fault;io.at=at;}
extern "C" uint32_t gf_info(int n){switch(n){case 0:return io.pos;case 1:return io.opens;case 2:return io.closes;case 3:return io.owned;case 4:return io.chkins;case 5:return io.clear;case 6:return io.bad;case 7:return io.reads;case 8:return io.status;case 9:return io.device;case 10:return io.name;}return 0;}
static bool rom(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);uint8_t a=r.a;bool carry=false;
switch(r.pc){
 case 0xffbd:{static const char want[]="0:GEOSFONTS,S,R";io.name=r.a==15;for(int i=0;i<r.a;i++)if(i>=15||zeropage_peddle_read(m,r.x+(r.y<<8)+i)!=want[i])io.name=0;break;}
 case 0xffba:io.device=r.x;if(r.a!=7||r.y!=2||(r.x!=8&&r.x!=9))io.bad++;break;
 case 0xffc0:io.opens++;io.owned=1;zeropage_peddle_write(m,0x98,1);io.status=io.fault==1?0x80:0;carry=io.fault==1;break;
 case 0xffc6:io.chkins++;if(r.x!=7||!io.owned)io.bad++;carry=io.fault==4;io.status=carry?0x80:0;break;
 case 0xffcf:io.reads++;if(!io.owned)io.bad++;if(io.fault==2&&io.pos>=io.at){a=0;io.status=2;}else if(io.pos<io.size){a=io.data[io.pos++];io.status=io.pos==io.size?0x40:0;}else{a=0;io.status=0x40;io.bad++;}break;
 case 0xffb7:a=io.status;break;
 case 0xffcc:io.clear++;break;
 case 0xffc3:io.closes++;if(r.a!=7||!io.owned)io.bad++;io.owned=0;zeropage_peddle_write(m,0x98,0);io.status=io.fault==3?0x80:0;break;
 default:return false;}
 auto lo=zeropage_peddle_read(m,0x100+((r.sp+1)&255)),hi=zeropage_peddle_read(m,0x100+((r.sp+2)&255));
 zeropage_peddle_set_a(m,a);zeropage_peddle_set_p(m,(r.p&~0x83)|(a==0?2:0)|(a&0x80)|(carry?1:0));zeropage_peddle_set_sp(m,(r.sp+2)&255);zeropage_peddle_set_pc(m,((hi<<8)|lo)+1);return true;}
extern "C" uint64_t gf_run(ZeroPagePeddle*m){auto b=zeropage_peddle_regs(m).instructions;for(int i=0;i<2000000;i++){if(zeropage_peddle_regs(m).pc==0x2ff)return zeropage_peddle_regs(m).instructions-b;if(io.data&&rom(m))continue;zeropage_peddle_step_instruction(m);}return 0;}
extern "C" void gf_ram(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read(m,a+i);}
extern "C" void gf_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read_reu(m,i);}
''')
  ext='.dylib' if sys.platform=='darwin' else '.so';path=out/('runner'+ext)
  subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),str(out/'runner.cpp'),str(ROOT/('build/libse_peddle'+ext)),'-o',str(path)],check=True,capture_output=True)
  self.r=C.CDLL(str(path));self.r.gf_run.argtypes=[C.c_void_p];self.r.gf_run.restype=C.c_uint64
  self.r.gf_io.argtypes=[C.c_void_p,C.c_uint32,C.c_int,C.c_uint32];self.r.gf_info.argtypes=[C.c_int];self.r.gf_info.restype=C.c_uint32
  self.r.gf_ram.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];self.r.gf_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p]
  self.m.load(0,bytes((i*73+(i>>8)*19+31)&255 for i in range(65536)));self.m.load(0x1000,(out/'fixture.bin').read_bytes())
  self.m.load(0xC000,bytes(0x600));self.m.load(0xCBC0,bytes(64));self.m.write(0x98,0)
  self.m.load(s['se_reu_banks'],(256).to_bytes(2,'little'));assert not self.call('se_reu_provider_init').p&1
 def read(self,a,n):
  b=self.C.create_string_buffer(n);self.r.gf_ram(self.m.handle,a,n,b);return b.raw
 def reu(self):
  b=self.C.create_string_buffer(16*1024*1024);self.r.gf_reu(self.m.handle,len(b),b);return b.raw
 def call(self,n,a=0,x=0,y=0):
  for k,v in [('a',a),('x',x),('y',y),('p',0x24),('sp',0xFD),('pc',self.s[n])]:getattr(self.m.lib,'zeropage_peddle_set_'+k)(self.m.handle,v)
  self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);used=self.r.gf_run(self.m.handle)
  assert used,('CPU nonreturn',n,hex(self.m.regs().pc));self.calls+=1;self.instructions+=used;self.peak=max(self.peak,used)
  return self.m.regs()
 def io(self,data,fault=0,at=0):
  self.io_bytes=self.C.create_string_buffer(data);self.r.gf_io(self.io_bytes,len(data),fault,at)
 def info(self):return [self.r.gf_info(i) for i in range(11)]
 def close(self):self.m.close()

def run(out,smoke=False):
 s=build(out/'leaf');f=Fixture(out/'leaf',s);pack=(ROOT/'build/geos-font-catalog/font-pack.bin').read_bytes();cases=[]
 try:
  initialram=f.read(0,65536);initialreu=f.reu()
  f.io(pack);r=f.call('se_gf_import_begin',8);assert not r.p&1 and r.a==1
  slices=0;used=f.instructions
  while r.a==1:
   r=f.call('se_gf_import_step');assert not r.p&1,('coldimport',slices,r.a,f.info(),f.read(0xCBC0,64).hex())
   slices+=1;assert slices<300
  assert r.a==0 and f.m.read(0xCBC0)==0xA5 and f.m.read(0xCBC0+8)==0
  assert f.info()[0]==len(pack) and f.info()[1:4]==[1,1,0] and not f.info()[6] and f.info()[9:]==[8,1]
  handles=tuple(f.read(0xCBC1,2));coldreu=f.reu()
  for bank,h in enumerate(handles):
   physical=f.m.read(s['se_reu_map']+h);part=pack[bank*65536:(bank+1)*65536]
   assert coldreu[physical*65536:physical*65536+len(part)]==part
  assert f.call('se_gf_import_cancel').a==0 and f.reu()==coldreu and tuple(f.read(0xCBC1,2))==handles
  assert install_font_pack(f)==handles #seam reuses only validated owned store
  want=bytearray(initialreu)
  for bank,h in enumerate(handles):
   physical=f.m.read(s['se_reu_map']+h);part=pack[bank*65536:(bank+1)*65536];want[physical*65536:physical*65536+len(part)]=part
  assert coldreu==want,'coldimport changed non-FD REU bytes or padding'
  after=f.read(0,65536);want=bytearray(initialram)
  for lo,hi in [(0x98,0x99),(0x100,0x200),(0x5000,0x5100),(0xCBC0,0xCC00),(s['__BSS_RUN__'],s['__BSS_RUN__']+s['__BSS_SIZE__']),(0xDF00,0xDF0B)]:want[lo:hi]=after[lo:hi]
  assert after==want,('cold fullRAM guard',next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,want)) if a!=b))
  cold=dict(slices=slices,bytes=len(pack),instructions=f.instructions-used,rom=f.info())
  print('FIRST COLD IMPORT PASS: actual BEGIN +291 bounded STEP +exact74432B CRC/EOI +CLOSE7',flush=True)
  before=f.reu();index=pack[32:32+43*16]
  for i in range(1 if smoke else 43):
   entry=index[i*16:i*16+16];f.m.load(0xCBC0+16,entry[:4]);ram=f.read(0,65536);used=f.instructions
   r=f.call('se_gf_fetch');assert not r.p&1,(i,r.a);offset=int.from_bytes(entry[8:11],'little');length=int.from_bytes(entry[11:13],'little')
   assert f.read(0x5000,length)==pack[offset:offset+length]
   assert f.read(0xCBC0+24,2)==entry[11:13] and f.read(0xCBC0+26,4)==entry[4:8]
   raw=pack[offset:offset+length];bits=int.from_bytes(raw[6:8],'little');xs=[int.from_bytes(raw[j:j+2],'little') for j in range(8,bits,2)];widths=[b-a for a,b in zip(xs,xs[1:])]
   assert f.read(0xCBC0+30,4)==bytes([entry[13],32,max(widths),128 if len(set(widths))==1 else 0])
   after=f.read(0,65536);want=bytearray(ram)
   for lo,hi in [(0x5000,0x6072),(0xCBC0,0xCC00),(0x100,0x200),(0xF0,0xF4),(s['se_reu_c64'],s['dma_physical']+1),(s['se_crc_value'],s['se_crc_value']+2),(0xDF00,0xDF0B)]:want[lo:hi]=after[lo:hi]
   assert after==want,('fullRAM guard',i,next((hex(j),a,b) for j,(a,b) in enumerate(zip(after,want)) if a!=b))
   assert f.reu()==before
   cases.append(dict(face=i,offset=offset,bytes=length,instructions=f.instructions-used))
   if i==0:print('FIRST FONT STORE PASS: actual FD allocation + checkedDMA +runtime fetchCRC; fullRAM/16MiBREU guards',flush=True)
  faults=[];hits=[]
  if not smoke:
   def query(i=0):f.m.load(0xCBC0+16,index[i*16:i*16+4]);f.m.write(0xCBC0+21,0)
   def fetch_error(code):
    a=f.read(0xA000,8192);shim=f.read(0xC600,1024);reu=f.reu();r=f.call('se_gf_fetch')
    assert r.p&1 and r.a==code and f.m.read(0xCBC0+21)==0,(code,r.a,r.p)
    assert f.reu()==reu and f.read(0xA000,8192)==a and f.read(0xC600,1024)==shim
   # Every native face gets a real no-DMA hit, still verified with trustedCRC.
   for i in range(43):
    query(i);assert not f.call('se_gf_fetch').p&1
    dma=f.read(s['se_reu_dma_calls'],2);used=f.instructions;assert not f.call('se_gf_fetch').p&1
    assert f.read(s['se_reu_dma_calls'],2)==dma;hits.append(dict(face=i,instructions=f.instructions-used))
   faults.append('43 cachehits CRC-verified without DMA')
   query();assert not f.call('se_gf_fetch').p&1
   f.m.write(0x500A,f.m.read(0x500A)^1);fetch_error(0x94)
   assert not f.call('se_gf_fetch').p&1 #invalid cache refetch repairs buffer
   for length in (0,1,9,4211,65535):
    query();assert not f.call('se_gf_fetch').p&1;f.m.load(0xCBC0+24,length.to_bytes(2,'little'));fetch_error(0x94)
   faults.append('cache stage corruption and malformed lengths refuse, VALID0/executable slots preserved')
   query();assert not f.call('se_gf_fetch').p&1
   f.m.write(0x500A,f.m.read(0x500A)^1);f.m.load(s['se_overlay_loads'],(f.m.read(s['se_overlay_loads'])+1).to_bytes(2,'little'))
   assert not f.call('se_gf_fetch').p&1 and f.read(0x5000,892)==pack[720:1612]
   faults.append('overlay-loadtag change refills staging before glyph use')
   for bank,h in enumerate(handles):
    for table,slot in [('se_reu_logical_owner',h),('se_reu_physical_owner',f.m.read(s['se_reu_map']+h))]:
     query();f.m.write(s[table]+slot,0x77);fetch_error(0x18);f.m.write(s[table]+slot,0xFD)
   for field,value,code in [(0,0,0x18),(3,255,0x18),(4,255,0x18),(5,1,0x91),(1,0,0x18),(2,0,0x18)]:
    query();old=f.m.read(0xCBC0+field);f.m.write(0xCBC0+field,value);fetch_error(code);f.m.write(0xCBC0+field,old)
   query();f.m.load(0xCBD0,b'\x01\x00\x00\xFF');fetch_error(0x17)
   faults.append('both logical+physical owners, full epoch, READY/busy/handles and absent font refuse')
   def change_pack(offset,value):
    h=handles[offset>>16];f.m.write(0x8000,value)
    for n,v,w in [('se_reu_logical',h,1),('se_reu_offset',offset&65535,2),('se_reu_c64',0x8000,2),('se_reu_length',1,2)]:f.m.load(s[n],v.to_bytes(w,'little'))
    assert not f.call('se_reu_copy',0).p&1
   for off,value in [(32,2),(32+11,0),(32+12,0xFF),(32+10,2),(32+8,0),(720+7,pack[727]^1),(1611,pack[1611]^1)]:
    query();change_pack(off,value);fetch_error(0x94);change_pack(off,pack[off])
   faults.append('index identity/length/bank bounds and raw payload corruption refuse CRC; REU read-only during FETCH')
   # Each fault runs the real cold service, with only KERNAL transport modeled.
   cold_faults=[]
   for tag,data,fault,at,cancel,expect in [
    ('open',pack,1,0,False,0x92),('chkin',pack,4,0,False,0x92),
    ('read-first',pack,2,0,False,0x92),('read-bank1',pack,2,66000,False,0x92),
    ('close',pack,3,0,False,0x92),('short',pack[:-1],0,0,False,0x94),
    ('extra',pack+b'X',0,0,False,0x94),('header',b'X'+pack[1:],0,0,False,0x94),
    ('payload',pack[:66000]+bytes([pack[66000]^1])+pack[66001:],0,0,False,0x94),
    ('cancel-first',pack,0,0,True,0),('cancel-bank1',pack,0,66000,True,0)]:
    assert not f.call('se_reu_provider_init').p&1;f.m.load(0xCBC0,bytes(64));f.m.write(0x98,0)
    foreign=f.call('se_reu_alloc',0x77).a;foreignphysical=f.m.read(s['se_reu_map']+foreign)
    f.io(data,fault,at);r=f.call('se_gf_import_begin',9);steps=0
    while not r.p&1 and r.a==1:
     if cancel and f.info()[0]>=at:r=f.call('se_gf_import_cancel');break
     r=f.call('se_gf_import_step');steps+=1;assert steps<300
    assert bool(r.p&1)==bool(expect) and r.a==expect,(tag,r.a,r.p,f.info())
    assert f.read(0xCBC0,3)==bytes(3) and not any(f.read(0xCBC0+5,1)+f.read(0xCBC0+8,1))
    assert not f.info()[3] and not f.info()[6] and f.info()[2]==f.info()[1]
    assert f.m.read(s['se_reu_logical_owner']+foreign)==f.m.read(s['se_reu_physical_owner']+foreignphysical)==0x77
    assert 0xFD not in f.read(s['se_reu_logical_owner'],256)
    cold_faults.append(dict(tag=tag,steps=steps,rom=f.info(),error=r.a))
   faults.append('11 cold OPEN/CHKIN/READ/CLOSE/length/header/CRC/cancel faults close only7 and releaseFD, preserve foreign77')
   # Actual provider exhaustion: allocation1 and allocation2 failures, no OPEN.
   for banks in (1,2):
    f.m.load(s['se_reu_banks'],banks.to_bytes(2,'little'));assert not f.call('se_reu_provider_init').p&1
    f.m.load(0xCBC0,bytes(64));f.io(pack);r=f.call('se_gf_import_begin',8)
    assert r.p&1 and r.a==1 and f.info()[1:4]==[0,0,0] and not any(f.read(0xCBC0,3))
    assert 0xFD not in f.read(s['se_reu_logical_owner'],256)
   faults.append('actual first/second FD allocation exhaustion has no OPEN or leaked handle')
   # Service admission must not seize another caller's existing ROM channel.
   f.m.load(s['se_reu_banks'],(256).to_bytes(2,'little'));assert not f.call('se_reu_provider_init').p&1
   f.m.load(0xCBC0,bytes(64));f.m.write(0x98,1);f.io(pack);snapshot=f.read(0xCBC0,64)
   r=f.call('se_gf_import_begin',8);assert r.p&1 and r.a==0x91 and f.read(0xCBC0,64)==snapshot and f.info()[1:4]==[0,0,0]
   f.m.write(0x98,0)
   for device in (0,7,10,255):
    r=f.call('se_gf_import_begin',device);assert r.p&1 and r.a==0x90 and f.info()[1:4]==[0,0,0]
   faults.append('invalid device/existing ROM channel refused before allocation or OPEN/CLOSE')
   # Epoch replacement: old descriptor cannot release replacement FD-free tables.
   f.io(pack);r=f.call('se_gf_import_begin',8);assert not r.p&1
   r=f.call('se_gf_import_step');assert not r.p&1
   assert not f.call('se_reu_provider_init').p&1;replacement=f.call('se_reu_alloc',0x77).a
   provider=f.read(s['se_reu_map'],771);reu=f.reu();r=f.call('se_gf_import_step')
   assert r.p&1 and r.a==0x18 and f.read(s['se_reu_map'],771)==provider and f.reu()==reu
   assert f.m.read(s['se_reu_logical_owner']+replacement)==0x77 and f.info()[1:4]==[1,1,0]
   faults.append('mid-import epoch replacement closes own channel without freeing replacement provider or writing REU')
   # Fixture seam after a source reset must replace stale descriptor, preserve
   # newly owned source tokens, and never accidentally reuse those handles.
   first=install_font_pack(f);assert first[0]!=replacement
   old_epoch=f.read(s['se_reu_epoch'],2);assert not f.call('se_reu_provider_init').p&1
   source=f.call('se_reu_alloc',4).a;second=install_font_pack(f)
   assert f.m.read(s['se_reu_logical_owner']+source)==4 and source not in second
   assert f.read(0xCBC3,2)!=old_epoch and install_font_pack(f)==second
   faults.append('reusable CPU transport seam safely reinstalls after provider/source reset without freeing new source')
   # Explicit logical/physical mismatch fault: FREE refuses; retain that FD
   # handle for diagnosis instead of silently forgetting its ownership record.
   assert not f.call('se_reu_provider_init').p&1;f.m.load(0xCBC0,bytes(64));f.io(pack)
   assert not f.call('se_gf_import_begin',8).p&1
   h=f.m.read(0xCBC1);ph=f.m.read(s['se_reu_map']+h);f.m.write(s['se_reu_physical_owner']+ph,0x77)
   reu=f.reu();r=f.call('se_gf_import_step');assert r.p&1 and r.a==4
   assert f.read(0xCBC0,3)==bytes([0,h,0]) and f.m.read(s['se_reu_logical_owner']+h)==0xFD
   assert f.m.read(s['se_reu_physical_owner']+ph)==0x77 and f.reu()==reu and f.info()[1:4]==[1,1,0]
   r=f.call('se_gf_import_begin',8);assert r.p&1 and r.a==0x91
   faults.append('refused sameepoch FD FREE retains precise descriptor handle and never touches foreign physical owner')
   # Cold/runtimereads use mappings, not guessed contiguous physical banks.
   assert not f.call('se_reu_provider_init').p&1;f.m.load(0xCBC0,bytes(64));f.io(pack)
   assert not f.call('se_reu_bind',0x77,x=1,y=2).p&1
   r=f.call('se_gf_import_begin',8);assert not r.p&1
   while r.a==1:r=f.call('se_gf_import_step');assert not r.p&1
   mapped=tuple(f.read(0xCBC1,2));physical=tuple(f.m.read(s['se_reu_map']+h) for h in mapped)
   assert mapped==(2,3) and physical==(1,3)
   f.m.load(0xCBC0+16,index[39*16:39*16+4]);assert not f.call('se_gf_fetch').p&1
   e=index[39*16:39*16+16];off=int.from_bytes(e[8:11],'little');size=int.from_bytes(e[11:13],'little')
   assert f.read(0x5000,size)==pack[off:off+size] and f.m.read(s['se_reu_physical_owner']+2)==0x77
   faults.append('actual coldimport and cross64KiB runtimefetch use logical2/3 -> noncontiguous physical1/3, preserve foreign2')
  else:cold_faults=[]
  result=dict(status='passed',cold=cold,faces=cases,hits=hits,fault_groups=faults,cold_faults=cold_faults,calls=f.calls,instructions=f.instructions,peak_instructions=f.peak,scope='Actual provider/DMA/runtime fontfetch and cold importer; only KERNAL IEC ROM modeled, no native transport claim')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
 finally:f.close()
if __name__=='__main__':
 from datetime import datetime,timezone
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args()
 out=a.out or ROOT/'build/geos-font-store'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True,exist_ok=True);run(out,a.smoke)
