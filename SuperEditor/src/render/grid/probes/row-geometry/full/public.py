"""Actual public structural edit frames; no manufactured geometry authority."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[6];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_grid_raw_wrapped as wrapped
raw=wrapped.raw;profile=raw.caret.profile;observer=profile.observer

def run(out,base,smoke=False,control=False):
 out.mkdir(parents=True);g=observer.Gate(out,base);f=g.f;cases=[]
 try:
  for width in(60,80):
   prefix=b''if smoke else b'Prefix\r'*9400
   specs=[('native-new-row',observer.geos.native_text('Plain editable words.\r'+'Alpha words '*18+'\r'+'A'*(width-1)+'\rUntouched tail.\r'),None)]
   if not smoke:
    specs += [('first-row',b'A'*(width-1)+b'\rTail.\r',5),('two-full-rows',b'A'*(width*2-1)+b'\rTail.\r',width+5),('late-far',prefix+b'A'*(width-1)+b'\rTail.\r',len(prefix)+5),('viewport-drop',b'A'*(width-1)+b'\r'+b'Following words\r'*30,5)]
   for tag,data,at in specs:
    f.source(data,physical=256);f.typed(observer.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);profile.drain(f)
    if at is None:at=data.index(b'\r',data.index(b'\r')+1)+6
    if tag=='late-far':f.position(len(data));profile.drain(f)
    f.position(at);profile.drain(f);source=data;where=at
    old_source=f.canonical();old_header=f.raw_cache()[0][0x1500:0x1600]
    for key in(observer.Q,20):
     semantic=f.read(f.s['se_st_descriptor'],37);sp2=f.raw_cache()[0][0x1600:0x1680]
     audit=g.audit_begin();initial=f.total_instructions;loads=f.get('se_overlay_loads',2);f.key(key);first=f.total_instructions-initial;canonical=f.canonical();stable=g.stable();bc=f.read(f.s['se_bc_arena'],17)+f.read(f.s['se_bc_ring'],96);profile.drain(f);settled=f.total_instructions-initial;endloads=(f.get('se_overlay_loads',2)-loads)&65535;g.audit_end(audit,tag)
     assert f.read(f.s['se_bc_arena'],17)+f.read(f.s['se_bc_ring'],96)==bc,(tag,'renderchangedobserver')
     assert f.canonical()==canonical and g.stable()==stable,(tag,'renderchangedsource/history/clipboard')
     assert f.read(f.s['se_st_descriptor'],37)==semantic and f.raw_cache()[0][0x1600:0x1680]==sp2,(tag,'rawmustnotfabricatesemantic/SP2authority')
     source=source[:where]+bytes((key,))+source[where:]if key!=20 else source[:where-1]+source[where:];where+=1 if key!=20 else -1
     assert f.merged()==source and f.read(0xc600,1024)==f.shim
     (bits,attrs),_,_,_=observer.geos.grid.expected(f,source);actual=f.read(0x6000,8000);colors=f.read(0x4000,1000)
     item=dict(width=width,tag=tag,key=key,input_call=first,settled=settled,loads=endloads,route=f.m.read(0x89ff),pixels=hashlib.sha256(actual+colors).hexdigest());cases.append(item);print('FRAME',item,flush=True)
     if actual!=bits or colors!=attrs:
      observer.geos.png(actual,colors,out/'actual-failure.png');observer.geos.png(bits,attrs,out/'expected-failure.png');(out/'failureRAM.bin').write_bytes(f.read(0,65536));(out/'failureFE.bin').write_bytes(f.raw_cache()[0]);(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
      raise AssertionError((width,tag,key,'independent pixels',next((i,a,b)for i,(a,b)in enumerate(zip(actual+colors,bits+attrs))if a!=b)))
     wrapped.packet_check(f,source,(width,tag,key))
     expected_route=0 if control or(tag=='viewport-drop'and key==20)else 2
     assert item['route']==expected_route,(tag,key,'actualgeometryroute')
     if tag=='late-far':assert where>65535,(tag,'actual24bitposition')
     observer.geos.png(bits,attrs,out/(str(width)+'-'+tag+'-'+str(key)+'.png'))
     assert not any(f.get(n,1)for n in('se_f_owner','se_doc_read_locks','se_e_error')),(tag,'no lease/owner')
    assert source==data
  result=dict(status='PASS',cases=cases,scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve(),'--smoke'in sys.argv,'--control'in sys.argv)
