"""Actual6510 genuine-font metrics/raster/32bit masks; isolated, no editor build."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,shutil,struct,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine,VENDOR
import geos_font_catalog as catalog
from test_geos_glyphs import native,MAP
SIZE=240
OUT=ROOT/'build/geos-catalog-glyph'
sha=lambda b:hashlib.sha256(b).hexdigest()


def build(out):
 out.mkdir(parents=True,exist_ok=True)
 (out/'probe.s').write_text('.setcpu "6502"\n.exportzp se_gg_context,se_gg_pointer\n.segment "ZEROPAGE"\nse_gg_context:.res 2\nse_gg_pointer:.res 2\n')
 (out/'probe.cfg').write_text('MEMORY{Z:file="",start=$F0,size=4,type=rw;C:file=%O,start=$1000,size=$3000,type=rw;}\nSEGMENTS{ZEROPAGE:load=Z,type=zp;CODE:load=C,type=ro;RODATA:load=C,type=ro;}\n')
 objs=[]
 for name,p in [('glyph',ROOT/'src/render/geos/catalog-glyph.s'),('probe',out/'probe.s'),('petscii',ROOT/'src/tui/petscii.s')]:
  o=out/(name+'.o');subprocess.run(['ca65','-I',str(ROOT/'src'),'-g','-o',str(o),str(p)],check=True);objs.append(str(o))
 subprocess.run(['ld65','-C',str(out/'probe.cfg'),'-o',str(out/'probe.bin'),'-m',str(out/'probe.map'),'-Ln',str(out/'probe.lbl'),*objs],check=True)
 s={x[2].lstrip('.'):int(x[1],16) for line in (out/'probe.lbl').read_text().splitlines() if len(x:=line.split())==3 and x[0]=='al'}
 (out/'runner.cpp').write_text('''#include "zeropage_peddle.h"
extern "C" uint64_t cg_run(ZeroPagePeddle*m,uint64_t limit){auto start=zeropage_peddle_regs(m).instructions;for(uint64_t i=0;i<limit;i++){if(zeropage_peddle_regs(m).pc==0x2ff)return zeropage_peddle_regs(m).instructions-start;zeropage_peddle_step_instruction(m);}return 0;}
extern "C" void cg_read(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read(m,a+i);}
extern "C" void cg_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read_reu(m,i);}
''')
 ext='.dylib' if sys.platform=='darwin' else '.so'
 subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),str(out/'runner.cpp'),str(ROOT/('build/libse_peddle'+ext)),'-o',str(out/('runner'+ext))],check=True)
 return s,out/('runner'+ext)


def oracle(raw,fallback,value,encoding,style,flags,clip,native_only=False):
 code=value if encoding==2 else value&127 if encoding else native(value);reverse=bool(flags or encoding==1 and value&128)
 baseline,stride,height,index,bits=struct.unpack('<BHBHH',raw[:8]) if not native_only else (6,0,8,0,0)
 packed=not native_only and (encoding==2 or code in MAP)
 if packed:
  offsets=struct.unpack('<'+str((bits-index)//2)+'H',raw[index:bits]);start,end=offsets[(code if encoding==2 else MAP[code])-32:(code if encoding==2 else MAP[code])-30];width=end-start
 else:start=0;width=8
 advance=8 if native_only else width+(style&1)+(style&2)
 left,right,top,bottom=clip;ink=[];coverage=[];cell=(1<<advance)-1
 for y in range(24):
  row=0
  if y<height:
   if packed:
    for x in range(width):row=(row<<1)|bool(raw[bits+y*stride+(start+x)//8]&(128>>((start+x)%8)))
   else:row=fallback[code*8+y] if y<8 else 0
   # Convert the nativewidth bit string into a leftaligned32bit row before
   # procedural styles; this intentionally shares no assembly scratch/maps.
   row<<=32-width
   if style&1:row|=row>>1
   if style&2:row>>=2 if 3*y<height else 1 if 3*y<2*height else 0
   full=cell<<(32-advance)
   if style&4 and y==baseline+1:row=full
   if reverse:row^=full
   mask=sum(1<<(31-x) for x in range(advance) if left<=x<right)
   if top<=y<bottom:ink.append(row&mask);coverage.append(mask);continue
  ink.append(0);coverage.append(0)
 return bytes([2,code,width,advance,height,baseline]),b''.join(x.to_bytes(4,'big') for x in ink),b''.join(x.to_bytes(4,'big') for x in coverage)


class Fixture:
 def __init__(self,s,lib,out):
  self.s=s;self.m=Machine();self.r=C.CDLL(str(lib));self.r.cg_run.argtypes=[C.c_void_p,C.c_uint64];self.r.cg_run.restype=C.c_uint64;self.r.cg_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];self.r.cg_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p]
  self.m.load(0,bytes((i*37+11)&255 for i in range(0xD000)));self.m.load(0x1000,(out/'probe.bin').read_bytes())
  self.fallback=(ROOT/'assets/fonts/generated/native8.bin').read_bytes();self.m.load(0x7000,self.fallback);self.calls=0;self.peak=0;self.bytes_checked=0;self.reu_before=self.reu()
 def close(self):self.m.close()
 def read(self,a,n):
  b=C.create_string_buffer(n);self.r.cg_read(self.m.handle,a,n,b);return b.raw
 def reu(self):
  b=C.create_string_buffer(16*1024*1024);self.r.cg_reu(self.m.handle,len(b),b);return b.raw
 def call(self,ctx,measure=False):
  for k,v in [('pc',self.s['se_geos_catalog_measure' if measure else 'se_geos_catalog_glyph']),('sp',0xFD),('a',0),('x',ctx&255),('y',ctx>>8),('p',0x24)]:getattr(self.m.lib,'zeropage_peddle_set_'+k)(self.m.handle,v)
  self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);n=self.r.cg_run(self.m.handle,100000);assert n,('no return',hex(self.m.regs().pc));self.calls+=1;self.peak=max(n,self.peak);return self.m.regs()
 def check(self,raw,value=0x41,encoding=0,style=0,flags=0,clip=(0,32,0,24),native_only=False,measure=False,error=None,ctx=0x8800,fontptr=0x5000,length=None,nativeptr=0x7000,guard=True):
  if native_only:fontptr=0;length=0
  elif length is None:length=len(raw)
  if fontptr and 0x1000<=fontptr and fontptr+len(raw)<=0xC600:self.m.load(fontptr,raw)
  inputs=fontptr.to_bytes(2,'little')+length.to_bytes(2,'little')+nativeptr.to_bytes(2,'little')+bytes([value,encoding,style,flags,*clip]);assert len(inputs)==14
  self.m.load(ctx,inputs+bytes([0xA7])*(SIZE-14));before=self.read(0,0xD000) if guard else None;r=self.call(ctx,measure);frame=self.read(ctx,SIZE)
  assert frame[:14]==inputs,'inputmutation'
  if error is not None:assert r.p&1 and r.a==error and frame[14]==0,('refusal',hex(r.a),hex(r.p),error)
  else:
   assert not r.p&1 and r.a==0,('CPUerror',hex(r.a),hex(r.p),value,encoding,style)
   metrics,ink,coverage=oracle(raw,self.fallback,value,encoding,style,flags,clip,native_only)
   if measure:metrics=bytes([1])+metrics[1:]
   assert frame[14:20]==metrics,('metrics',value,style,frame[14:20].hex(),metrics.hex())
   if measure:assert frame[20:212]==bytes([0xA7])*192,'measurepainted'
   else:
    assert frame[20:116]==ink,('ink',value,encoding,style,flags,clip,frame[20:116].hex(),ink.hex())
    assert frame[116:212]==coverage,('coverage',value,style,clip,frame[116:212].hex(),coverage.hex())
    self.bytes_checked+=192
  if guard:
   after=self.read(0,0xD000);expected=bytearray(before);expected[ctx+14:ctx+SIZE]=after[ctx+14:ctx+SIZE];expected[0xF0:0xF4]=after[0xF0:0xF4];expected[0x100:0x200]=after[0x100:0x200]
   assert after==expected,('RAM/source/shim',next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,expected)) if a!=b))
  return frame


def main():
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');a=p.parse_args();out=OUT;syms,lib=build(out)
 source=ROOT/'build/geos-font-catalog';catalog.build([catalog.DEFAULT_MEDIA/'geos20-original.d81',catalog.DEFAULT_MEDIA/'geos-system.d81'],source,catalog.DEFAULT_BSW)
 cat=json.loads((source/'catalog.json').read_text());f=Fixture(syms,lib,out);cases=clips=faults=0
 try:
  bsw=next(x for x in cat['faces'] if x['family']=='BSW');raw=(source/bsw['files']['font.bin']).read_bytes()
  f.check(raw);f.check(raw,style=3);f.check(raw,style=7,flags=1);f.check(raw,value=0x5c,native_only=True);print('SMOKE PASS',flush=True)
  if a.smoke:return
  for face in cat['faces']:
   raw=(source/face['files']['font.bin']).read_bytes()
   for code in range(128):
    for style in range(8):
     for inverse in range(2):f.check(raw,code,1,style,inverse);cases+=1
   for style in range(8):
    for clip in [(0,0,0,0),(1,32,0,24),(0,31,0,24),(3,17,1,7),(32,0,24,0),(0,32,1,23),(7,19,8,18)]:f.check(raw,0x47,style=style,flags=style&1,clip=clip);clips+=1
   for value in range(32,32+face['metrics']['glyphs']):
    for style in range(8):
     for inverse in range(2):f.check(raw,value,2,style,inverse);cases+=1
   f.check(raw,0x61,measure=True,ctx=0xC0FB)
   print('FACE PASS',face['family'],face['point_size'],flush=True)
  for value in range(256):
   for style in range(8):
    f.check(raw,value,0,style,value&1,native_only=True);cases+=1
  for value in range(256):
   f.check(raw,value,0,value&7,value&1);cases+=1
   f.check(raw,value,1,value&7,value&1);cases+=1
  f.check(raw,ctx=0xC510)
  for context in (0x0FFF,0xC511,0xC600,0xFF80):
   before=f.read(0,0xD000);regs=f.call(context);assert regs.p&1 and regs.a==0x90
   after=f.read(0,0xD000);expected=bytearray(before);expected[0xF0:0xF4]=after[0xF0:0xF4];expected[0x100:0x200]=after[0x100:0x200];assert after==expected
   faults+=1
  for kw in [dict(encoding=3),dict(encoding=2,value=31),dict(encoding=2,value=129),dict(encoding=2,native_only=True),dict(style=8),dict(flags=2),dict(clip=(33,32,0,24)),dict(clip=(0,33,0,24)),dict(clip=(0,32,25,24)),dict(clip=(0,32,0,25)),dict(fontptr=0),dict(length=0),dict(fontptr=0xC500),dict(fontptr=0xFFF0),dict(nativeptr=0xFFF0),dict(nativeptr=0xC300),dict(nativeptr=0x8800),dict(fontptr=0x8800)]:
   f.check(raw,error=0x90,**kw);faults+=1
  for at in range(8):
   bad=bytearray(raw);bad[at]^=0xFF;f.check(bytes(bad),error=0x94);faults+=1
  for start,end in [(0xFFFF,0),(21,20),(0,512),(3,4)]:
   bad=bytearray(raw);bad[8:12]=struct.pack('<HH',start,end);f.check(bytes(bad),error=0x94);faults+=1
  assert f.reu()==f.reu_before
  image=(out/'probe.bin').read_bytes();result=dict(status='passed',faces=43,raster_cases=cases,clip_cases=clips,fault_cases=faults,CPU_calls=f.calls,pixel_and_coverage_bits=f.bytes_checked*8,frame_bytes=SIZE,borrowed_ZP=4,new_BSS=0,new_ZP=0,payload_bytes=len(image),module_bytes=syms['se_petscii_screen']-0x1000+8,peak_instructions=f.peak,REU_bytes_unchanged=len(f.reu_before),RAM_guard_bytes_per_call=0xD000,source_sha256={n:sha((ROOT/n).read_bytes()) for n in ('src/render/geos/catalog-glyph.s','src/render/geos/catalog-glyph.inc','tests/test_geos_catalog_glyph.py')},scope='Actual6510 metrics/raster primitive for genuine variablefonts/nativefallback; no preview/editor/nativeVIC claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()
if __name__=='__main__':main()
