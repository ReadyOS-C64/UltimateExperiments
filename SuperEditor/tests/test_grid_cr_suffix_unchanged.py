"""Actual ordinary fast routes and Full CR fallback, with independent pixels."""
from pathlib import Path
import argparse,json
import test_grid_cr_suffix as p
def run(out,fixture):
 out.mkdir(parents=True);g=p.make_gate(out,fixture);f=g.f;cases=[]
 try:
  for width in(60,80):
   for caps in(0,3):
    for tag,data,at,key in [('ordinary-short',b'Alpha words.\rTail.',5,81),('ordinary-wrap',b'Alpha words '*18+b'\rTail.',width+5,81),('Full-CR',b'Alpha words.\rTail.',5,13)]:
     if caps==0 and tag=='Full-CR':continue
     f.source(data,physical=256);f.typed(p.observer.geos.native_text('syntax plain'if caps==0 else'syntax full'));f.command(97 if width==60 else 98);p.profile.drain(f);f.position(at);p.profile.drain(f)
     source=data;where=at
     for op in(key,20):
      audit=g.audit_begin();f.key(op);canonical=f.canonical();stable=g.stable();p.profile.drain(f);g.audit_end(audit,tag);source=source[:where]+bytes((op,))+source[where:]if op!=20 else source[:where-1]+source[where:];where+=1 if op!=20 else -1
      assert f.merged()==source and canonical==f.canonical()and stable==g.stable();(bits,attrs),_,_,_=p.observer.geos.grid.expected(f,source);assert f.read(0x6000,8000)+f.read(0x4000,1000)==bits+attrs,(width,caps,tag,op,'pixels')
      route=f.m.read(0x89ff);assert route==({'ordinary-short':1,'ordinary-wrap':2,'Full-CR':0}[tag]),(width,caps,tag,op,'ordinary fast/fallback route');assert not any(f.get(n,1)for n in('se_f_owner','se_doc_read_locks','se_e_error'));cases.append(dict(width=width,caps=caps,tag=tag,key=op,route=route));print('UNCHANGED',width,caps,tag,op,flush=True)
  result=dict(status='PASS',scope=__doc__,cases=cases);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('--fixture',type=Path,required=True);q.add_argument('--out',type=Path,required=True);a=q.parse_args();run(a.out.resolve(),a.fixture.resolve())
