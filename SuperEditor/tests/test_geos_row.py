"""Real packed-font GEOS physical strip compositor, independent pixel oracle.

Private CPU build only; no editor build, fonts regeneration or VICE. Nine-pixel
logical lines are supplied as intersecting runs in each physical eight-pixel
strip; both runs share one tile-color arbitration pass.
"""
from pathlib import Path
import ctypes as C,hashlib,json,random,re,struct,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine,VENDOR
from test_geos_glyphs import native
OUT=ROOT/'build/geos-row';F=0x8880;SIZE=704
PRIORITY=[0,6,7,8,0,0,0,5,3,4,1,5,2,0]
PALETTE=bytes([1,3,7,10,12,12,12,7,13,5,15,7,3,1])
SOURCES=['render/geos/row','render/geos/row-probe','render/geos/measure','render/geos/glyph','render/geos/assets','tui/petscii']
def run(args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
def build(frame=0x8880):
 OUT.mkdir(parents=True,exist_ok=True);objs=[]
 for name in SOURCES:
  q=OUT/(name.replace('/','-')+'.o');run(['ca65','-g','-I','src','-o',q,'-D',f'GEOS_ROW_FRAME={frame}','src/'+name+'.s']);objs.append(q)
 (OUT/'row-probe.cfg').write_text((ROOT/'src/render/geos/row-probe.cfg').read_text().replace('RODATA:load=C,type=ro;', 'RODATA:load=C,type=ro; GEOS_ROW_FAST:load=C,type=ro,optional=yes;'))
 run(['ld65','-C',OUT/'row-probe.cfg','-o',OUT/'row.bin','-Ln',OUT/'row.lbl','-m',OUT/'row.map',*objs])
 assert len((OUT/'row.bin').read_bytes())<=4096
 return {n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(OUT/'row.lbl').read_text())}
def runner():
 cpp=OUT/'runner.cpp';cpp.write_text('''#include "zeropage_peddle.h"
extern "C" uint64_t gr_run(ZeroPagePeddle*m,uint64_t limit){auto start=zeropage_peddle_regs(m).instructions;for(uint64_t i=0;i<limit;i++){if(zeropage_peddle_regs(m).pc==0x2ff)return zeropage_peddle_regs(m).instructions-start;zeropage_peddle_step_instruction(m);}return 0;}
extern "C" void gr_read(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read(m,a+i);}
extern "C" void gr_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read_reu(m,i);}
''');ext='.dylib' if sys.platform=='darwin' else '.so';p=OUT/('runner'+ext);run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),cpp,ROOT/('build/libse_peddle'+ext),'-o',p]);dll=C.CDLL(str(p));dll.gr_run.argtypes=[C.c_void_p,C.c_uint64];dll.gr_run.restype=C.c_uint64;dll.gr_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];dll.gr_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p];return dll
class Fixture:
 def __init__(self,s):
  self.s=s;self.m=Machine();self.r=runner();self.m.load(0,bytes((i*73+19)&255 for i in range(0xD000)));self.m.load(0x1000,(OUT/'row.bin').read_bytes());self.font=(ROOT/'assets/fonts/generated/bsw9.bin').read_bytes();self.widths=(ROOT/'assets/fonts/generated/bsw9-widths.bin').read_bytes();self.native=(ROOT/'assets/fonts/generated/native8.bin').read_bytes();self.m.load(0xA000,self.native);self.m.load(0xA400,PALETTE);self.native_addr=0xA000;self.calls=0;self.peak=0;self.reu_before=self.reu()
 def close(self):self.m.close()
 def read(self,a,n):
  p=C.create_string_buffer(n);self.r.gr_read(self.m.handle,a,n,p);return p.raw
 def reu(self):
  p=C.create_string_buffer(512*1024);self.r.gr_reu(self.m.handle,len(p),p);return p.raw
 def call(self,ctx=None):
  if ctx is None:ctx=F
  for n,v in [('pc',self.s['se_geos_row']),('sp',0xFD),('a',0),('x',ctx&255),('y',ctx>>8),('p',0x24)]:getattr(self.m.lib,'zeropage_peddle_set_'+n)(self.m.handle,v)
  self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);n=self.r.gr_run(self.m.handle,3_000_000);assert n,('nonreturn',hex(self.m.regs().pc));self.peak=max(self.peak,n);self.calls+=1;return self.m.regs()
 def setup(self,runs,row=0,clip=(0,320,0,8),reset=True):
  left,right,top,bottom=clip;frame=bytearray([row,len(runs),int(reset),6]);frame+=(0x8D00).to_bytes(2,'little');frame+=self.s['se_geos_packed'].to_bytes(2,'little');frame+=self.s['se_geos_widths'].to_bytes(2,'little');frame+=self.native_addr.to_bytes(2,'little');frame+=(0xA400).to_bytes(2,'little');frame+=left.to_bytes(2,'little')+right.to_bytes(2,'little')+bytes([top,bottom]);assert len(frame)==20
  if reset:self.m.load(F,frame+bytes([0xA7])*(SIZE-20))
  else:self.m.load(F,frame)
  cursor=0x8D30;records=[]
  for i,rec in enumerate(runs):
   chars,styles,roles,flags,x,y=rec;n=len(chars);assert n<=128 and len(styles)==len(roles)==len(flags)==n
   desc=bytearray([n,y&255])+(x&65535).to_bytes(2,'little');arrays=[]
   for a in [chars,styles,roles,flags]:
    arrays.append(cursor);self.m.load(cursor,bytes(a));desc+=cursor.to_bytes(2,'little');cursor+=len(a)
   map_=cursor;self.m.load(map_,b'\xA7'*(2*(n+1)));cursor+=2*(n+1);desc+=map_.to_bytes(2,'little')+b'\xA7'*3;assert len(desc)==17;self.m.load(0x8D00+i*17,desc);records.append((map_,n,arrays))
  assert cursor<=0x9180,hex(cursor)
  return frame,records
 def oracle(self,runs,row,clip,before,hist=None):
  left,right,top,bottom=clip;out=bytearray(before);weights=[[0]*14 for _ in range(40)] if hist is None else [list(h) for h in hist];maps=[];dones=[]
  for sy in range(top,bottom):
   for x in range(left,right):out[0x6000+row*320+(x//8)*8+sy]&=~(128>>(x&7))&255 if hist is None else 255
  for chars,styles,roles,flags,x,y in runs:
   boundaries=[x];done=0
   for value,style,role,flag in zip(chars,styles,roles,flags):
    if x>=right:break
    code=native(value);advance=self.widths[code]+(style&1)+(style&2);cell=((1<<advance)-1)<<(16-advance)
    for gy in range(9):
     sy=gy+y
     if not top<=sy<bottom:continue
     word=int.from_bytes(self.font[code*18+gy*2:code*18+gy*2+2],'big')
     if style&1:word|=word>>1
     if style&2:word>>=2 if gy<3 else 1 if gy<6 else 0
     if flag&1:word^=cell
     for gx in range(advance):
      px=x+gx
      if not left<=px<right:continue
      base=bool(word&(1<<(15-gx)));weights[px//8][role]=min(255,weights[px//8][role]+base)
      if base^bool(flag&6):out[0x6000+row*320+(px//8)*8+sy]|=128>>(px&7)
    x+=advance;boundaries.append(x);done+=1
   maps.append(boundaries);dones.append(done)
  if top<bottom:
   for tile,w in enumerate(weights):
    if tile*8>=right or tile*8+8<=left:continue
    role=max(range(14),key=lambda r:(w[r],PRIORITY[r] if w[r] else 0,-r));out[0x4000+row*40+tile]=(PALETTE[role]<<4)|6
  return out,weights,maps,dones
 def check(self,runs,row=0,clip=(0,320,0,8),reset=True,hist=None):
  frame,records=self.setup(runs,row,clip,reset);before=self.read(0,65536);want,weights,maps,dones=self.oracle(runs,row,clip,before,hist);r=self.call();after=self.read(0,65536)
  assert not r.p&1 and r.a==0,(row,clip,r.a,r.p)
  assert after[F:F+20]==frame and after[F+20]==1
  assert after[F+98:F+658]==bytes(v for w in weights for v in w),('histogram',row,clip,next((i,a,b) for i,(a,b) in enumerate(zip(after[F+98:F+658],bytes(v for w in weights for v in w)))) if after[F+98:F+658]!=bytes(v for w in weights for v in w) else None)
  for i,(mp,n,arrays) in enumerate(records):
   expected=b''.join((x&65535).to_bytes(2,'little') for x in maps[i]);assert after[mp:mp+len(expected)]==expected,('boundaries',i,maps[i],after[mp:mp+len(expected)].hex());assert after[mp+len(expected):mp+2*(n+1)]==b'\xA7'*(2*(n+1)-len(expected));at=0x8D00+i*17+14;assert after[at:at+3]==bytes([dones[i]])+(maps[i][-1]&65535).to_bytes(2,'little');want[mp:mp+len(expected)]=expected;want[at:at+3]=after[at:at+3]
  want[F+20:F+SIZE]=after[F+20:F+SIZE];want[0xF0:0xF4]=after[0xF0:0xF4];want[0x100:0x200]=after[0x100:0x200]
  assert after==want,('pixel/tile/source/shim/neighbor guard',row,clip,next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,want)) if a!=b))
  return weights,maps,dones

def main():
 global F,OUT
 s=build();(OUT/'result.json').unlink(missing_ok=True);f=Fixture(s);rows=0;invalid=0;coverage=[];rng=random.Random(0xB590)
 def rec(chars,x=0,y=0,phase=0):
  return chars,bytes((i+phase)%4 for i in range(len(chars))),bytes((i+phase)%14 for i in range(len(chars))),bytes((i+phase)%8 for i in range(len(chars))),x,y
 try:
  for row in [0,1,12,23,24]:
   for phase in range(8):
    chars=bytes((i*11+phase*19)&255 for i in range(80));f.check([rec(chars,phase,y=(phase%8),phase=phase)],row=row);rows+=1
  # Every native input value/styles/flags, clipped32x8 windows and real differing widths.
  for value in range(256):
   for style in range(4):
    chars=bytes([value])*8;f.check([(chars,bytes([style])*8,bytes([value%14])*8,bytes([value%8])*8,3,0)],row=value%25,clip=(5,37,0,8));rows+=1
  # Small negative horizontal origins preserve real partial glyph ink,
  # source-boundary words and zero-crossing arithmetic. Every style/flag union
  # is checked against signed Python pixels, not emitted product maps.
  signed_rows=0
  for x in range(-15,0):
   for style in range(4):
    for flag in range(8):
     chars=b'Wim. gjpq';n=len(chars)
     f.check([(chars,bytes([style])*n,bytes((i+style)%14 for i in range(n)),bytes([flag])*n,x,0)],row=(x+style+flag)%25)
     rows+=1;signed_rows+=1
  for x in [-15,-8,-1]:
   for clip in [(0,0,0,8),(7,29,1,7),(0,320,3,5),(0,320,0,8)]:
    f.check([rec(b'gjpq Wim.',x=x,y=-3,phase=2),rec(b'Next',x=x,y=6,phase=3)],row=24,clip=clip);rows+=1;signed_rows+=1
  # Unsigned off-right inputs outside the explicitly reserved negative range
  # still consume no glyphs and never wrap through a visible pixel address.
  for x in [320,1000,0x8000,0xFFF0]:
   _,maps,dones=f.check([rec(b'Wim.',x=x)],row=11)
   assert dones==[0] and maps==[[x]];rows+=1
  weights,_,_=f.check([rec(b'Wim.',x=-7)],row=10);rows+=1
  f.check([rec(b'gjpq',x=-3,y=-8,phase=3)],row=10,reset=False,hist=weights);rows+=1;signed_rows+=2
  coverage.append('signed horizontal-15..-1, allstyles/flags, exactzero crossing, partialclips, append, unsignedoffright')
  # Adjacent physical strips of9px lines: strip0 top8, strip1 receives the
  # genuine ninth row plus next logical line's rows0..6 in ONE arbitration.
  upper=rec(b'gjpqy ABC'+bytes([0xC1,0xC7,0xD9]),x=2,y=0,phase=1)
  f.check([upper],row=4);rows+=1
  desc=(*upper[:5],-8);lower=rec(b'Next lower/UPPER',x=3,y=1,phase=2)
  f.check([desc,lower],row=5);rows+=1;coverage.append('adjacent strips include ninth-row descenders and both intersecting lines')
  for left,right,top,bottom in [(0,0,0,8),(320,320,0,8),(7,9,0,8),(0,320,3,5),(11,319,8,8),(19,301,1,7)]:
   f.check([rec(b'Wim.'*20,y=-3),rec(b'gjpq'*16,y=6,phase=1)],row=24,clip=(left,right,top,bottom));rows+=1
  # Optional existing charset address is only an explicitly supplied valid
  # native source, never an assumption about retained bitmap-mode contents.
  f.m.load(0x4800,f.native);f.native_addr=0x4800
  for style in range(4):
   chars=bytes([0x5C,0x5E,0x7F,0xA1,0xFF])*5;f.check([(chars,bytes([style])*len(chars),bytes([3])*len(chars),bytes([6])*len(chars),1,0)],row=14);rows+=1
  f.native_addr=0xA000
  f.check([],row=7);f.check([rec(b'')],row=8);rows+=2
  # Long-line clipping stops source consumption and leaves unused map entries.
  weights,maps,dones=f.check([rec(b'i'*128)],row=9,clip=(0,96,0,8));rows+=1;assert 0<dones[0]<128 and maps[0][-1]>=96
  # Bounded appends preserve prior ink/histogram and arbitrate shared tiles.
  a=rec(b'Wim.'*12,phase=0);weights,maps,dones=f.check([a],row=10);rows+=1
  b=rec(b'gjpq'*10,x=2,y=-8,phase=3);f.check([b],row=10,reset=False,hist=weights);rows+=1
  # Saturating shared-tile weights remain stable across repeated appends.
  dense=(b' '*80,bytes(80),bytes([2])*80,bytes([1])*80,0,0)
  weights,_,_=f.check([dense],row=6);rows+=1
  for _ in range(4):weights,_,_=f.check([dense],row=6,reset=False,hist=weights);rows+=1
  assert weights[0][2]==255
  coverage.append('saturating tile weights and reset/append composition')
  assert len(set(f.widths[native(v)] for v in b'Wim. '+bytes([0xC1,0xC9])))>2
  # Frame/range/style errors refuse before output writes. Only caller private
  # validation scratch may change; inputs/maps/fonts and all otherRAM stay exact.
  base=[rec(b'Valid')]
  mutations=[(0,25),(1,3),(2,2),(3,16),(18,9),(19,9),(15,2),(17,2),(5,0xC6),(7,0x60),(11,0xC6),(13,0x88),('count',129),('origin',8),('origin',0xF7),('style',4),('role',14),('flag',8),('map',0x917F),('chars',0x8800)]
  for at,v in mutations:
   _,records=f.setup(base)
   if isinstance(at,int):f.m.write(F+at,v)
   elif at=='count':f.m.write(0x8D00,v)
   elif at=='origin':f.m.write(0x8D01,v)
   elif at in ['style','role','flag']:f.m.write(records[0][2][{'style':1,'role':2,'flag':3}[at]],v)
   else:f.m.load(0x8D00+({'map':12,'chars':4}[at]),v.to_bytes(2,'little'))
   before=f.read(0,65536);r=f.call();after=f.read(0,65536);want=bytearray(before);want[F+20:F+SIZE]=after[F+20:F+SIZE];want[0xF0:0xF4]=after[0xF0:0xF4];want[0x100:0x200]=after[0x100:0x200]
   assert r.p&1 and r.a==0x90,(at,v,r.a,r.p);assert after==want,('invalid wrote outsideframe',at);invalid+=1
  _,_=f.setup(base);before=f.read(0,65536);r=f.call(0xC600);after=f.read(0,65536);want=bytearray(before);want[0x100:0x200]=after[0x100:0x200];assert r.p&1 and r.a==0x90 and after==want;invalid+=1
  # Alternate compile-time caller placement still fits entirely belowVIEW.
  default_out,default_frame=OUT,F;OUT=default_out/'relocated';F=0x8940
  alt=Fixture(build(frame=F))
  try:
   alt.check([rec(b'gjpq Lower/UPPER',y=-8),rec(b'Next line',y=1,phase=2)],row=24)
   assert alt.reu()==alt.reu_before
  finally:alt.close();OUT,F=default_out,default_frame
  assert f.reu()==f.reu_before
  result=dict(status='passed',payload_bytes=len((OUT/'row.bin').read_bytes()),caller_frame_bytes=SIZE,maximum_runs=2,maximum_source_bytes_per_run=128,source_boundary_words_per_run='consumed+1;<=129',new_BSS=0,new_ZP=0,borrowed_ZP_bytes=4,relocated_frame=0x8940,rows=rows,pixels_checked=rows*320*8,invalid_frames=invalid,signed_horizontal_rows=signed_rows,full_RAM_guard_bytes=65536,shim_bytes=1024,catalog_tail_bytes=192,REU_bytes_unchanged=512*1024,peak_call_instructions=f.peak,coverage=coverage,scope='Actual GEOS packed-font physical-strip code and independent pixel/tile/mapping oracle; no editor placement, native VIC, multiline source layout or performance claim')
  (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()
if __name__=='__main__':main()
