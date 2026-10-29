"""Bounded actual6510 proportional line layout/maps and nearest-source hits.

Independent Python line-break/advance oracle; actual native path links the
existing packed-font measure module. Private build only, no editor/native claim.
"""
from pathlib import Path
import ctypes as C,hashlib,json,random,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine,VENDOR
from test_geos_glyphs import native
OUT=ROOT/'build/geos-line';F=0x8D00;SIZE=832
FIELDS={'state':32,'reason':33,'used':34,'x':35,'scan':38,'end':41,'next':44,'first':47,'count':50,'caretx':52,'caretvalid':55,'hitsource':56,'hitindex':59,'rewind':78}
def run(a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True)
def build():
 OUT.mkdir(parents=True,exist_ok=True);objs=[]
 for n in ['render/geos/line','render/geos/line-probe','render/geos/measure','render/geos/assets','tui/petscii']:
  q=OUT/(n.replace('/','-')+'.o');run(['ca65','-g','-I','src','-o',q,'src/'+n+'.s']);objs.append(q)
 run(['ld65','-C','src/render/geos/line-probe.cfg','-o',OUT/'line.bin','-Ln',OUT/'line.lbl','-m',OUT/'line.map',*objs]);assert len((OUT/'line.bin').read_bytes())<=4096
 return {n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(OUT/'line.lbl').read_text())}
def runner():
 cpp=OUT/'runner.cpp';cpp.write_text('''#include "zeropage_peddle.h"
extern "C" uint64_t gl_run(ZeroPagePeddle*m,uint64_t limit){auto start=zeropage_peddle_regs(m).instructions;for(uint64_t i=0;i<limit;i++){if(zeropage_peddle_regs(m).pc==0x2ff)return zeropage_peddle_regs(m).instructions-start;zeropage_peddle_step_instruction(m);}return 0;}
extern "C" void gl_read(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read(m,a+i);}
extern "C" void gl_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read_reu(m,i);}
''');ext='.dylib' if sys.platform=='darwin' else '.so';p=OUT/('runner'+ext);run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),cpp,ROOT/('build/libse_peddle'+ext),'-o',p]);r=C.CDLL(str(p));r.gl_run.argtypes=[C.c_void_p,C.c_uint64];r.gl_run.restype=C.c_uint64;r.gl_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];r.gl_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p];return r
class Fixture:
 def __init__(self,s):
  self.s=s;self.r=runner();self.m=Machine();self.m.load(0,bytes((i*43+7)&255 for i in range(0xD000)));self.m.load(0x1000,(OUT/'line.bin').read_bytes());self.peak={};self.calls=0;self.widths=(ROOT/'assets/fonts/generated/bsw9-widths.bin').read_bytes();self.reu_before=self.reu()
 def close(self):self.m.close()
 def read(self,a,n):
  p=C.create_string_buffer(n);self.r.gl_read(self.m.handle,a,n,p);return p.raw
 def reu(self):
  p=C.create_string_buffer(512*1024);self.r.gl_reu(self.m.handle,len(p),p);return p.raw
 def put(self,k,v,n):self.m.load(F+k,v.to_bytes(n,'little'))
 def get(self,k,n=3):return int.from_bytes(self.read(F+(FIELDS[k] if isinstance(k,str) else k),n),'little')
 def call(self,n,error=None,ctx=F,guard=True):
  before=self.read(0,65536) if guard else None
  for k,v in [('pc',self.s['se_geos_line_'+n]),('sp',0xFD),('a',0),('x',ctx&255),('y',ctx>>8),('p',0x24)]:getattr(self.m.lib,'zeropage_peddle_set_'+k)(self.m.handle,v)
  self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);used=self.r.gl_run(self.m.handle,200000);assert used,('nonreturn',n,hex(self.m.regs().pc));self.peak[n]=max(self.peak.get(n,0),used);self.calls+=1;r=self.m.regs();assert bool(r.p&1)==(error is not None) and r.a==(error or 0),(n,r.a,error)
  if guard:
   after=self.read(0,65536);want=bytearray(before);want[F:F+SIZE]=after[F:F+SIZE];want[0xF0:0xF4]=after[0xF0:0xF4];want[0x100:0x200]=after[0x100:0x200];assert after==want,('source/font/shim/catalog/RAM guard',n,next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,want)) if a!=b))
  return used
 def begin(self,start,width=320,pan=0,mode=0,encoding=0,caret=0):
  self.m.load(F,bytes(SIZE));self.put(0,mode,1);self.put(1,encoding,1);self.put(2,width,2);self.put(4,start,3);self.put(7,pan,3);self.put(10,caret,3);self.put(13,self.s['se_geos_packed'],2);self.put(15,self.s['se_geos_widths'],2);self.put(17,0xA000,2);self.put(20,0x9040,2);self.put(22,0x9060,2);self.put(24,0x9080,2);self.call('begin')
 def packet(self,data,styles,advances,anchor):
  assert len(data)<=32;self.m.load(0x9040,data);self.m.load(0x9060,bytes(styles));self.m.load(0x9080,bytes(advances));self.put(26,anchor,3);self.put(29,len(data),1);self.call('step');assert self.get('used',1)<=len(data)
 def advance(self,data,styles):return [self.widths[native(v)]+(s&1)+(s&2) for v,s in zip(data,styles)]

def oracle(data,adv,start,width,mode,pan,caret,base):
 i=start;x=0;last=None;reason=2
 while i<len(data):
  if data[i]==13:reason=1;end=i;next_=i+1;break
  a=adv[i]
  if not mode and x+a>width:
   if i==start:i+=1;x+=a;reason=6;end=next_=i
   elif last:end,next_,x=last[0],last[0],last[1];reason=4
   else:end=next_=i;reason=5
   break
  x+=a;i+=1
  if data[i-1]==32:last=(i,x)
  if not mode and x==width:reason=3;end=next_=i;break
 else:end=next_=i
 prefix=adv[start:end];maps=[0];first=start
 if mode:
  maps=[];xx=0;closed=False
  for at,a in enumerate(prefix,start):
   if xx+a>pan and not closed:
    if not maps:first=at;maps.append(max(0,min(width,xx-pan)))
    maps.append(max(0,min(width,xx+a-pan)));closed=xx+a>=pan+width
   xx+=a
  if not maps:first=end;maps=[max(0,min(width,x-pan))]
 else:
  for a in prefix:maps.append(min(width,maps[-1]+a))
 valid=(start<=caret<end) or (caret==end and reason in [1,2]);cx=sum(adv[start:caret]) if valid else None
 return dict(reason=reason,end=base+end,next=base+next_,x=x,first=base+first,maps=maps,caretx=cx)

def main():
 s=build();(OUT/'result.json').unlink(missing_ok=True);f=Fixture(s);rng=random.Random(0x9E05);lines=packets=hits=0;coverage=[]
 def check(data,styles,*,base=0,width=320,mode=0,pan=0,encoding=0,adv=None,packet_sizes=(1,7,32),caret=None):
  nonlocal lines,packets,hits
  adv=f.advance(data,styles) if adv is None else adv;start=0;caret=len(data)//2 if caret is None else caret
  for line in range(2000):
   want=oracle(data,adv,start,width,mode,pan,caret,base);f.begin(base+start,width,pan,mode,encoding,base+caret);at=start;k=0
   while f.get('state',1)==1:
    if at==len(data):f.call('finish');break
    n=min(packet_sizes[k%len(packet_sizes)],len(data)-at);k+=1;f.packet(data[at:at+n],styles[at:at+n],adv[at:at+n],base+at);used=f.get('used',1);assert f.get('scan')==base+at+used;at+=used;packets+=1
   got={n:f.get(n,1 if n=='reason' else 3) for n in ['reason','end','next','x','first']};assert got=={n:want[n] for n in got},(data,start,width,mode,pan,got,want)
   assert f.get('rewind',1)==int(f.get('next')<f.get('scan')),('rewind flag',got,f.get('scan'))
   count=f.get('count',2);maps=[int.from_bytes(f.read(F+176+i*2,2),'little') for i in range(count+1)];assert maps==want['maps'],('map',start,width,mode,pan,maps,want)
   assert f.get('caretvalid',1)==int(want['caretx'] is not None),('caretvalid',start,caret,want,f.get('caretvalid',1))
   if want['caretx'] is not None:assert f.get('caretx')==want['caretx']
   # Every exact boundary/midpoint plus clamps, with tie toward higher source.
   tests={0,width,width+1,65535,*maps};tests.update((a+b)//2 for a,b in zip(maps,maps[1:]));before=f.read(0,65536)
   for x in tests:
    f.put(30,x,2);f.call('hit',guard=False);target=min(width,x);index=min(range(len(maps)),key=lambda i:(abs(maps[i]-target),-i));assert f.get('hitindex',2)==index and f.get('hitsource')==want['first']+index,('hit',x,maps,f.get('hitindex',2),index);hits+=1
   after=f.read(0,65536);expected=bytearray(before);expected[F:F+SIZE]=after[F:F+SIZE];expected[0xF0:0xF4]=after[0xF0:0xF4];expected[0x100:0x200]=after[0x100:0x200];assert after==expected
   lines+=1;next_=want['next']-base
   if want['reason']==2:break
   assert next_>start;start=next_
  else:raise AssertionError('too many lines')
 try:
  for width in [1,7,31,127,320]:
   for phase in range(4):
    data=bytes([0x41,0xC1,0x49,0xC9,0x57,0xD7,32,0x2E,0xA1])*17+b'\r'+b'longWORD'*11+b'\r\rEND';styles=bytes((i+phase)%4 for i in range(len(data)));check(data,styles,width=width,base=65520,packet_sizes=(1,2,3,32))
  coverage.append('actual native lower/upper/fallback widths and all bold/italic advances')
  for n in [0,1,319,320,321,640]:
   for cr in [False,True]:
    data=b'A'*n+(b'\r' if cr else b'');check(data,bytes(len(data)),encoding=1,adv=[1]*len(data),base=0x1FF80)
  coverage.append('empty/CR/EOF/exact320 and supplied advances1 reach321-entry map')
  # Whitespace opportunity straddles packet boundaries; scanned suffix rewinds.
  for sizes in [(1,),(3,),(7,32),(32,)]:
   data=b'abc defghijklmnop qrst uvw';check(data,bytes(len(data)),width=30,packet_sizes=sizes)
  for pan in [0,1,17,319,320,65540,0x100000]:
   data=b'Wim. '*70+b'\rEND';check(data,bytes(i%4 for i in range(len(data))),mode=1,pan=pan,base=0x12345,packet_sizes=(32,1,17))
  coverage.append('nowrap24-bit clips, invisible lines and canonical anchors above64KiB')
  for _ in range(50):
   n=rng.randrange(1,150);data=bytes(rng.choice([32,13,65,0xC1,0x49,0xD7,0xFF]) for _ in range(n));check(data,bytes(rng.randrange(4) for _ in data),width=rng.randrange(1,321),base=0xFF00,packet_sizes=(rng.randrange(1,33),))
  # A >64KiB no-wrap logical line uses bounded packets and no giant map.
  data=b'i'*66000+b'\r';check(data,bytes(len(data)),mode=1,pan=130900,base=0x10010,packet_sizes=(32,),caret=65540);coverage.append('66000-byte logical line in bounded32-byte steps')
  check(b'A B',bytes(3),width=7,encoding=1,adv=[255,1,2],base=0xFFFF)
  # Admission/state/source-context scalar failures, no source/output mutation.
  errors=0
  f.begin(0)
  for offset,value,n in [(0,2,1),(1,2,1),(2,0,2),(2,321,2),(7,0xFFFFFF,3)]:
   f.put(offset,value,n);f.call('begin',error=0x90);errors+=1;f.begin(0)
  f.put(29,33,1);f.call('step',error=0x90);errors+=1
  f.put(29,1,1);f.put(26,1,3);f.call('step',error=0x74);errors+=1
  f.begin(0,encoding=1);f.m.load(0x9040,b'A');f.m.load(0x9080,b'\0');f.put(29,1,1);f.put(26,0,3);f.call('step',error=0x90);errors+=1
  f.begin(0,encoding=0);f.m.load(0x9060,b'\4');f.put(29,1,1);f.call('step',error=0x90);errors+=1
  f.begin(0);f.call('hit',error=0x70);f.call('begin',ctx=0xC600,error=0x90);errors+=2
  f.begin(0xFFFFFF,encoding=1);f.m.load(0x9040,b'A');f.m.load(0x9080,b'\1');f.put(29,1,1);f.put(26,0xFFFFFF,3);f.call('step',error=0x7B);errors+=1
  f.begin(0,mode=1,encoding=1);f.put(35,0xFFFFFF,3);f.m.load(0x9040,b'A');f.m.load(0x9080,b'\1');f.put(29,1,1);f.call('step',error=0x7B);errors+=1
  assert f.reu()==f.reu_before
  result=dict(status='passed',payload_bytes=len((OUT/'line.bin').read_bytes()),caller_frame_bytes=SIZE,map_boundary_words=321,new_BSS=0,new_ZP=0,borrowed_ZP_bytes=4,lines=lines,packets=packets,hit_tests=hits,invalid_cases=errors,maximum_packet_bytes=32,peak_instructions=f.peak,full_RAM_guards=65536,shim_bytes=1024,catalog_tail_bytes=192,REU_bytes_unchanged=512*1024,coverage=coverage,scope='Actual bounded proportional line/maps/hit code and existing native measure; independent CPU oracle only, no source adapter/editor/native GEOS completion claim')
  (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()
if __name__=='__main__':main()
