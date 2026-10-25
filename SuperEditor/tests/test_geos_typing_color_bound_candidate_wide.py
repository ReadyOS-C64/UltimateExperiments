"""Private9px glyph shift for1..11px transformedglyphs, up to3 touched bytes."""
from pathlib import Path
from datetime import datetime,timezone
import json,random,importlib.util,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_fold_editor as fold
from test_geos_typing_candidate import bits,packed,at
BASE=ROOT/'build/geos-incremental-editor/20261025T161722424199Z/fixture';F=0x8a80;B=0x8400;TEMP=0x8580

def run(out,base=BASE):
 frozen=out/'fixture';shutil.copytree(base,frozen);spec=importlib.util.spec_from_file_location('style_wide',ROOT/'src/render/geos/typing-color-bound-candidate/build-wide.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);image,s=b.build(out/'component',frozen)
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen;names=json.loads((frozen/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names;dll=fold.geos.grid.runner(out);f=fold.Fixture(out,frozen,dll,True);rng=random.Random(0x5711E);cases=0;peak=0
 def check(op,x,advance,oldwidth,top,glyph,caret):
  nonlocal cases,peak
  base=b''.join(packed([rng.randrange(2)if p<oldwidth else 0 for p in range(320)])for _ in range(9));frame=bytes([op,0,top,advance])+x.to_bytes(2,'little')+oldwidth.to_bytes(2,'little')+bytes([caret,0x16])+glyph+b'\xa7'*(105-28);f.m.load(F,frame);f.m.load(B,base);f.m.load(TEMP,b'\xa7'*40);f.m.load(0x4000+(top//8)*40,bytes([0x16])*80)
  for row in range(9):
   for c in range(40):f.m.write(at(top+row,c),(row*31+c*13)&255)
  before=f.read(0,65536);r,n=f.fast_call(s['se_typing_patch']);after=f.read(0,65536);peak=max(peak,n);assert not r.p&1 and r.a==0 and after[F+28]==1,(op,x,advance,oldwidth,top,r.a,r.p)
  want=bytearray(before);want[F+28:F+105]=after[F+28:F+105];want[TEMP:TEMP+40]=after[TEMP:TEMP+40];want[0x100:0x200]=after[0x100:0x200]
  for name in ['text_ptr','screen_ptr']:a=f.s[name];want[a:a+2]=after[a:a+2]
  for row in range(9):
   old=bits(base[row*40:(row+1)*40]);ink=bits(glyph[row*2:row*2+2])[:advance];new=old[:x]+(ink+old[x:oldwidth]if op==0 else old[x+advance:oldwidth]);new=(new+[0]*320)[:320];want[B+row*40:B+(row+1)*40]=packed(new);cx=x+advance if op==0 else x
   for p in range(cx,min(320,cx+caret)):new[p]^=1
   for c,v in enumerate(packed(new)):want[at(top+row,c)]=v
  assert after==want,('wholeRAM/pixels/attrs/source/shim',op,x,advance,oldwidth,top,next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,want))if a!=b));cases+=1
 try:
  data=fold.geos.native_text('Plain **boldword** and *italicword*.\rTail.');f.source(data);f.command(99);f.position(data.index(fold.geos.native_text('boldword'))+3);f.render();f.key(ord('X'));assert f.m.read(0xcfe8)==1;f.put('se_f_owner',4,1);f.m.load(0xa000,image);canonical=f.canonical();reu=f.reu()
  for advance in range(1,12):
   glyph=b''.join((rng.randrange(1<<advance)<<(16-advance)).to_bytes(2,'big')for _ in range(9))
   for phase in range(8):
    for top in [16,17,23,25,183]:
     check(0,phase+8,advance,308,top,glyph,11);check(1,phase+8,advance,319,top,glyph,11)
   for x in [0,1,7,8,15,16,307-advance,308-advance]:check(0,x,advance,308,25,glyph,5)
   for x in [0,1,7,8,15,16,318-advance,319-advance]:check(1,x,advance,319,183,glyph,5)
  for _ in range(400):
   advance=rng.randrange(1,12);op=rng.randrange(2);oldwidth=rng.randrange(advance,320-advance if not op else 320);x=rng.randrange(oldwidth+1 if not op else oldwidth-advance+1);top=rng.randrange(16,184);glyph=b''.join((rng.randrange(1<<advance)<<(16-advance)).to_bytes(2,'big')for _ in range(9));check(op,x,advance,oldwidth,top,glyph,rng.randrange(1,12))
  from test_geos_typing_bounds import wide_faults
  faults=wide_faults(f,s)
  assert f.canonical()==canonical and f.reu()==reu and f.read(0xc600,1024)==f.shim
  result=dict(status='passed',payload_bytes=len(image),cases=cases,faults=faults,advance1to11=True,caret1to11=True,fullRAMguard=65536,wholeREU=16777216,peak_instructions=peak,newBSS=0,newZP=0,actual_pendingC6=True,scope='Explicit trustedcaret-freebase/pretransformedglyph primitive only. Exact9scanlines/attributeunchanged/source/font/shim/fullRAMandREU; callerMUST separately certify allintersectingglyphroles0. No parser/controller/rootfastpath/latency claim.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result);return result
 except BaseException:
  (out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 out=ROOT/'build/geos-typing-two-wide'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
