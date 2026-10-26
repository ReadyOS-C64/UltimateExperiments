"""Read-only public CR-at-terminal correctness probe on frozen released bytes."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[6];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_grid_raw_wrapped as wrapped
profile=wrapped.raw.caret.profile;observer=profile.observer
def run(out,fixture):
 out.mkdir(parents=True);g=observer.Gate(out,fixture);f=g.f;cases=[]
 try:
  for width in(60,80):
   data=observer.geos.native_text('Alpha words.\rBeta words.\rTail.\r');at=data.index(b'\r');f.source(data,physical=256);f.typed(observer.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);profile.drain(f);f.position(at);profile.drain(f);f.key(13);profile.drain(f);source=data[:at]+b'\r'+data[at:];assert f.merged()==source
   (bits,attrs),_,_,_=observer.geos.grid.expected(f,source);a=f.read(0x6000,8000);b=f.read(0x4000,1000);mismatch=a!=bits or b!=attrs
   tag=str(width);observer.geos.png(a,b,out/(tag+'-actual.png'));observer.geos.png(bits,attrs,out/(tag+'-expected.png'));cases.append(dict(width=width,route=f.m.read(0x89ff),mismatch=mismatch,first_difference=next(((i,x,y)for i,(x,y)in enumerate(zip(a+b,bits+attrs))if x!=y),None)))
  result=dict(status='REPRODUCED'if any(c['mismatch']for c in cases)else'PASS',cases=cases,scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result);return result
 finally:f.close()
if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
