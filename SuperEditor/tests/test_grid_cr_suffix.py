"""Private actual public Plain CR split/merge: one R29, genuine NC commit."""
from pathlib import Path
import argparse,hashlib,json
import test_grid_raw_wrapped as wrapped
ROOT=wrapped.ROOT;profile=wrapped.raw.caret.profile;observer=profile.observer
def make_gate(out,fixture,control=False):
 import cpu_editor
 old=cpu_editor.startup
 def startup(m,s,assets,banks=256):
  names=cpu_editor.NAMES
  if control:assert len(names)==59;return old(m,s,assets,banks)
  assert names[-1]=='geometry'and len(names)==60;cpu_editor.NAMES=names[:-1]
  try:r=old(m,s,assets,banks)
  finally:cpu_editor.NAMES=names
  image=assets['geometry'];m.load(s['se_overlay_header'],image[:36]);m.load(0x5000,image[36:]);a,n=m.call(s['se_overlay_import']);assert not a.p&1;return r
 cpu_editor.startup=startup
 try:g=observer.Gate(out,fixture)
 finally:cpu_editor.startup=old
 return g
def run(out,fixture,control=False):
 out.mkdir(parents=True);g=make_gate(out,fixture,control)
 f=g.f;cases=[]
 def check(data,tag):
  assert f.merged()==data and f.read(0xc600,1024)==f.shim
  (bits,attrs),_,_,_=observer.geos.grid.expected(f,data);actual=f.read(0x6000,8000)+f.read(0x4000,1000)
  if actual!=bits+attrs:
   observer.geos.png(actual[:8000],actual[8000:],out/'failure-actual.png');observer.geos.png(bits,attrs,out/'failure-expected.png');(out/'failureRAM.bin').write_bytes(f.read(0,65536));raise AssertionError((tag,'independent pixels',next((i,a,b)for i,(a,b)in enumerate(zip(actual,bits+attrs))if a!=b)))
  wrapped.packet_check(f,data,tag);assert not any(f.get(n,1)for n in('se_f_owner','se_doc_read_locks','se_e_error'))
  return hashlib.sha256(actual).hexdigest()
 try:
  for width in(60,80):
   data=observer.geos.native_text('Alpha words.\rBeta words.\rTail.\r');long=observer.geos.native_text('Alpha words '*12+'\rBeta words.\rTail.\r')
   specs=[('interior',data,5,13),('column0',data,0,13),('end',data,data.index(b'\r'),13),('EOF',data[:-1],len(data)-1,13),('merge',data,data.index(b'\r')+1,20),('merge-EOF',b'Alpha\r',6,20),('wrapped-insert',long,5,13),('wrapped-merge',long,long.index(b'\r')+1,20)]
   for tag,data,at,key in specs:
    f.source(data,physical=256);f.typed(observer.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);profile.drain(f);f.position(at);profile.drain(f);source=data;where=at
    for op in(key,20 if key==13 else 13):
     sem=f.read(f.s['se_st_descriptor'],37);sp2=f.raw_cache()[0][0x1600:0x1680];audit=g.audit_begin();start=f.total_instructions;loads=f.get('se_overlay_loads',2);f.key(op);first=f.total_instructions-start;canonical=f.canonical();stable=g.stable();profile.drain(f);g.audit_end(audit,tag)
     source=source[:where]+bytes((op,))+source[where:]if op!=20 else source[:where-1]+source[where:];where+=1 if op!=20 else -1
     assert canonical==f.canonical()and stable==g.stable(),(tag,'render source/history/clipboard mutation');assert sem==f.read(f.s['se_st_descriptor'],37)and sp2==f.raw_cache()[0][0x1600:0x1680],(tag,'fabricated semantic/SP2')
     pixel=check(source,(width,tag,op));item=dict(width=width,tag=tag,key=op,first=first,settled=f.total_instructions-start,loads=(f.get('se_overlay_loads',2)-loads)&65535,route=f.m.read(0x89ff),pixels=pixel);cases.append(item);print('FRAME',item,flush=True)
     assert item['route']==(0 if control else 2),(width,tag,op,'actual route')
    assert source==data
  result=dict(status='PASS',scope=__doc__,cases=cases);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--control',action='store_true');a=p.parse_args();run(a.out.resolve(),a.fixture.resolve(),a.control)
