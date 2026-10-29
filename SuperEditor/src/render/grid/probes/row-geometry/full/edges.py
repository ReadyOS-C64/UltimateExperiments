"""Zero-copy suffix and last-viewport-row admission edges, actual public input."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[6];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_grid_raw_wrapped as wrapped
raw=wrapped.raw;profile=raw.caret.profile;observer=profile.observer
def run(out,fixture):
 out.mkdir(parents=True);g=observer.Gate(out,fixture);f=g.f;cases=[]
 try:
  for width in(60,80):
   for row in(20,21):
    data=b'P\r'*row+b'A'*(width-1)+b'\r';at=2*row+5
    f.source(data,physical=256);f.typed(observer.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);profile.drain(f);f.position(at);profile.drain(f);source=data;where=at
    for key in(observer.Q,20):
     audit=g.audit_begin();f.key(key);profile.drain(f);g.audit_end(audit,'edge')
     source=source[:where]+bytes([key])+source[where:]if key!=20 else source[:where-1]+source[where:];where+=1 if key!=20 else -1
     assert f.merged()==source and f.read(0xc600,1024)==f.shim
     (bits,attrs),_,_,_=observer.geos.grid.expected(f,source);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(width,row,key,'full raster')
     wrapped.packet_check(f,source,(width,row,key));route=f.m.read(0x89ff)
     # FIRST=22 is outside the released kernel's source-row contract even
     # for an empty deletion suffix. Preserve that safe fallback explicitly.
     assert route==(2 if row==20 and key!=20 else 0),(width,row,key,route)
     cases.append(dict(width=width,terminal=row,key=key,route=route,scope='row20 insert admitted; last-row/one-past empty suffix fallback'))
  result=dict(status='PASS',cases=cases,scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
