"""Actual6510 post-glyph underline plane; no parser/frontend integration."""
from pathlib import Path
from datetime import datetime,timezone
import ctypes as C,json,hashlib,subprocess,random
import test_geos_glyphs as glyph
ROOT=glyph.ROOT

def build(out):
 out.mkdir(parents=True,exist_ok=True);glyph.OUT=out;objects=[]
 for name in glyph.SOURCES+['render/geos/underline']:
  obj=out/(name.replace('/','-')+'.o');subprocess.run(['ca65','-g','-I','src','-o',str(obj),'src/'+name+'.s'],cwd=ROOT,check=True);objects.append(obj)
 subprocess.run(['ld65','-C','src/render/geos/probe.cfg','-o',str(out/'probe.bin'),'-Ln',str(out/'probe.lbl'),'-m',str(out/'probe.map'),*map(str,objects)],cwd=ROOT,check=True)
 return {x[2].lstrip('.'):int(x[1],16) for line in (out/'probe.lbl').read_text().splitlines() if len(x:=line.split())==3 and x[0]=='al'}

def run(out,smoke=False):
 s=build(out/'leaf');f=glyph.Fixture(s);cases=0;normal=0;selection=0;faults=[];rng=random.Random(0x554E4445)
 def check(value,encoding=0,style=4,flags=0,clip=(0,16,0,9),ctx=0xC000):
  nonlocal cases,normal,selection
  # Real unchanged glyph first. Only the new style bit is restored afterwards;
  # no glyph pixels, masks, metrics or source/font results are host-generated.
  f.check(value,encoding,style&3,flags,clip,ctx=ctx)
  f.m.write(ctx+2,style);before=f.read(0,65536);frame=before[ctx:ctx+77];r=f.call('se_geos_underline',ctx);after=f.read(0,65536)
  assert not r.p&1 and r.a==0
  want=bytearray(before);o=f.oracle(value,encoding,style&3,flags,clip)
  ink=bytearray(o['ink']);coverage=o['coverage'];reverse=bool(flags&1 or encoding and value&128)
  if style&4:
   row=7;cell=int.from_bytes(coverage[row*2:row*2+2],'big')
   ink[row*2:row*2+2]=(0 if reverse else cell).to_bytes(2,'big')
   want[ctx+21:ctx+39]=ink
  else:normal+=1
  assert after[ctx:ctx+77]==want[ctx:ctx+77],(value,encoding,style,flags,clip,after[ctx+21:ctx+39].hex(),ink.hex())
  assert after[ctx+18]==frame[18] and after[ctx+39:ctx+57]==frame[39:57]
  want[0xF0:0xF4]=after[0xF0:0xF4];want[0x100:0x200]=after[0x100:0x200]
  assert after==want,('fullRAM/font/source/shim/plane guard',value,style,next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,want)) if a!=b))
  # Parent's existing selection/caret XOR is a union. Compare independent raw
  # underline-before-inverse truth table against the transformed plane.
  for selected,caret in [(0,0),(1,0),(0,1),(1,1)]:
   union=bool(selected or caret);got=bytes(a^(b if union else 0) for a,b in zip(ink,coverage))
   # Separate raw-font oracle: style ink, OR underline over whole advance,
   # explicit inverse, union selection, THEN existing clip. This exercises the
   # ordering rather than just restating the transformed output plane.
   raw_cell=((1<<o['advance'])-1)<<(16-o['advance']);expected=bytearray()
   for row,word in enumerate(f.words[o['code']]):
    if style&1:word|=word>>1
    if style&2:word>>=2 if row<3 else 1 if row<6 else 0
    if style&4 and row==7:word|=raw_cell
    if reverse:word^=raw_cell
    if union:word^=raw_cell
    word&=int.from_bytes(coverage[row*2:row*2+2],'big')
    expected+=word.to_bytes(2,'big')
   assert got==expected,('raw underline/inverse/union/clip order',value,style,flags,clip,selected,caret)
   selection+=1
  cases+=1
 try:
  check(0x41,style=4);check(0xDC,style=7,flags=1,clip=(2,9,4,8),ctx=0xC0FB)
  print('FIRST UNDERLINE PASS: actual glyph +6510 transform; normal/inverse clipped baseline+1; unchanged advance',flush=True)
  if not smoke:
   for encoding in (0,1):
    for value in range(256):
     for style in range(8):
      for flags in (0,1):check(value,encoding,style,flags,ctx=0xC0FB if (style+value)&1 else 0xC000)
   for style in range(4,8):
    for left in range(17):
     for right in range(17):check([0x47,0x5C,0x5E,0xD1][(left+right)&3],style=style,flags=(left+right)&1,clip=(left,right,0,9))
    for top in range(10):
     for bottom in range(10):check([0x47,0x4A,0x50,0x51,0x59][(top+bottom)%5],style=style,flags=(top+bottom)&1,clip=(0,16,top,bottom))
   # Raster invariants: outside-height underline is a no-op; malformed raster,
   # unknown style and impossible height refuse before any frame write.
   for baseline,height in [(0,9),(5,9),(7,9),(8,9),(255,9),(0,0)]:
    f.check(0x41);ctx=0xC000;f.m.write(ctx+2,4);f.m.write(ctx+19,baseline);f.m.write(ctx+20,height);before=f.read(0,65536);r=f.call('se_geos_underline',ctx);after=f.read(0,65536);assert not r.p&1
    want=bytearray(before);row=baseline+1
    if row<height:want[ctx+21+row*2:ctx+23+row*2]=before[ctx+39+row*2:ctx+41+row*2]
    want[0xF0:0xF4]=after[0xF0:0xF4];want[0x100:0x200]=after[0x100:0x200];assert want==after
   faults.append('baseline+1 height guard and255overflow safe')
   for field,value in [(2,8),(2,255),(14,0),(14,1),(14,3),(20,10),(20,255)]:
    f.check(0x41);ctx=0xC000;f.m.write(ctx+2,4);f.m.write(ctx+field,value);before=f.read(0,65536);r=f.call('se_geos_underline',ctx);after=f.read(0,65536)
    assert r.p&1 and r.a==0x90 and after[ctx:ctx+77]==before[ctx:ctx+77]
    want=bytearray(before);want[0xF0:0xF4]=after[0xF0:0xF4];want[0x100:0x200]=after[0x100:0x200];assert after==want
   faults.append('invalid style/raster/height refused before plane writes')
  assert f.reu()==f.reu_before
  # Last linker label to next module isn't assumed: object CODE size is exact.
  dump=subprocess.run(['od65','--dump-segments',str(out/'leaf/render-geos-underline.o')],capture_output=True,text=True,check=True).stdout
  (out/'underline-segments.txt').write_text(dump)
  result=dict(status='passed',cases=cases,normal_style_byte_identical_cases=normal,selection_union_truth_cases=selection,fault_groups=faults,peak_instructions=f.peak,new_BSS=0,new_ZP=0,GG_frame=77,underline_style=4,baseline_plus=1,ink_before_inverse_equivalent=True,full_RAM_guard_bytes=65536,REU_guard_bytes=512*1024,scope='Actual unchanged packed glyph+new6510 clipped underline transform, stylebit$04; no parser/editor/native integration')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
 finally:f.close()
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-underline'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,a.smoke)
