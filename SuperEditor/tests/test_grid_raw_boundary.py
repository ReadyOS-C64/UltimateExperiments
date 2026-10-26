"""Actual public native-sequence reproduction; independent complete raster/map checks."""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util,json,hashlib
import test_grid_raw_wrapped as wrapped
raw=wrapped.raw;ROOT=wrapped.ROOT
def native_sequence(out,base,expect_failure=False):
 out.mkdir();g=raw.caret.profile.observer.Gate(out,base);f=g.f;cases=[]
 try:
  for width in(60,80):
   data=raw.caret.profile.observer.geos.native_text('Plain editable words.\r'+'Alpha words '*18+'\r'+'A'*(width-1)+'\rUntouched tail.\r')
   for caps in(0,3):
    f.source(data,physical=256);f.typed(raw.caret.profile.observer.geos.native_text('syntax '+('plain'if caps==0 else'full')));f.command(97 if width==60 else 98);raw.caret.profile.drain(f)
    first=data.index(b'\r')+1;edge=data.index(b'\r',first)+1
    sequence=[('short-space',5,32),('wrapped-quote',first+width+5,34),('wrapped-column0',first+width,81),('new-wrap',edge+5,81),('insert-CR',5,13)]
    for tag,at,key in sequence:
     line=data[:at].count(b'\r')+1;column=at-(data.rfind(b'\r',0,at)+1)
     f.typed(raw.caret.profile.observer.geos.native_text('goto '+str(line)))
     for _ in range(column):f.key(0x1d)
     raw.caret.profile.drain(f);assert f.get('se_hot_caret')==at
     source=data;where=at
     for operation in(key,20):
      audit=g.audit_begin();initial=f.total_instructions;loads=f.get('se_overlay_loads',2);f.key(operation);first=f.total_instructions-initial;raw.caret.profile.drain(f);g.audit_end(audit,tag)
      source=source[:where]+bytes((operation,))+source[where:]if operation!=20 else source[:where-1]+source[where:];where+=1 if operation!=20 else -1
      assert f.merged()==source and f.read(0xc600,1024)==f.shim
      (bits,attrs),_,_,_=raw.caret.profile.observer.geos.grid.expected(f,source)
      actual=f.read(0x6000,8000);colors=f.read(0x4000,1000);mismatch=actual!=bits or colors!=attrs
      item=dict(width=width,caps=caps,tag=tag,key=operation,route=f.m.read(0x89ff),first=first,instructions=f.total_instructions-initial,loads=(f.get('se_overlay_loads',2)-loads)&65535,mismatch=mismatch,pixels=hashlib.sha256(actual+colors).hexdigest());cases.append(item);print('FRAME',item,flush=True)
      if mismatch:
       raw.caret.profile.observer.geos.png(actual,colors,out/'actual-failure.png');raw.caret.profile.observer.geos.png(bits,attrs,out/'expected-failure.png')
       assert expect_failure and caps==0 and tag=='new-wrap'and operation==20,(width,caps,tag,operation,'independent pixels')
       (out/'result.json').write_text(json.dumps(dict(status='REPRODUCED',cases=cases),indent=2)+'\n');return cases
      if caps==0:wrapped.packet_check(f,source,(width,tag,operation))
      raw.caret.profile.observer.geos.png(bits,attrs,out/(str(width)+'-'+str(caps)+'-'+tag+'-'+str(operation)+'.png'))
     assert source==data
  assert not expect_failure,'expected native regression was not reproduced'
  (out/'result.json').write_text(json.dumps(dict(status='PASS',cases=cases),indent=2)+'\n');return cases
 finally:f.close()
def run(out):
 out.mkdir(parents=True);spec=importlib.util.spec_from_file_location('raw_boundary_build',ROOT/'src/render/grid/probes/raw-boundary/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);fixture,budget=b.build(out/'pair')
 old=native_sequence(out/'released-reproduction',b.RELEASE/'fixture',True);new=native_sequence(out/'candidate',fixture)
 result=dict(status='PASS',budget=budget,reproduced=old,candidate=new);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 out=ROOT/'build/grid-raw-boundary'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out)
