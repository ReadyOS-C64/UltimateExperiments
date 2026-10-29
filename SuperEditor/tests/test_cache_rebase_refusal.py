"""Private flags1 applicability regression, actual registered62 root routing.

Uses a source-matched private fixture built by edit-rebase-refusal-probe/build.py.
No host roots/refs/parser certificates or capsule substitution. Deliberate
incarnation fault is separately labeled; original source/pixel/fullREU oracles
remain. No native/physical hardware or canonical build.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import test_cache_rebase_registered as registered
import test_cache_splice as splice
plain=registered.suite.plain;ob=registered.suite.ob

def run(out,fixture,project):
 out.mkdir(parents=True);identity=registered.authenticate(fixture,project)
 g=ob.Gate(out/'gate',fixture);f=g.f;data=ob.geos.native_text('Ordinary words '*350+'\rTail.')
 fonts={n:(fixture/'fonts'/n).read_bytes()for n in ob.geos.GEOS_FONTS+('native8.bin',)}
 def arena(raw):
  token=f.read(f.s['se_bc_arena'],5);h=f.m.read(f.s['object_extents']+token[0]*16);bank=f.m.read(f.s['se_reu_map']+h)
  assert f.m.read(f.s['object_owner']+token[0])==0x53 and f.m.read(f.s['se_reu_physical_owner']+bank)==0x53
  return bank,splice.roots(raw[bank*65536:(bank+1)*65536])
 def prepare():
  f.source(data);f.command(99);f.command(77);f.render();bank,root=arena(g.reu());assert root[2][31]==1 and f.get('se_bc_count',1)==0
  f.command(35);f.render();assert f.get('se_hot_caret')==len(data)
  f.key(ob.Q);assert f.merged()==data+bytes([ob.Q]) and f.get('se_bc_count',1)==1
  f.call('se_editor_render')
  for _ in range(100):
   if f.m.read(0x9135)==41 and f.m.read(0x9136)==0:return
   f.call('se_editor_service')
  raise AssertionError('real C7 did not schedule C41 BEGIN')
 cases=[]
 try:
  prepare();before=g.reu();stable=f.canonical();queue=g.queue();bank,oldroot=arena(before);trace=[]
  for _ in range(120):
   request,op=f.m.read(0x9135),f.m.read(0x9136);r=f.call('se_editor_service');trace.append([request,op,r.a,r.p&1,f.m.read(0x9135),f.m.read(0x9136)])
   assert not f.get('se_e_error',1)
   if request==41 and f.m.read(0x9135)==21:break
  else:raise AssertionError('actual C41 never declined checked root1')
  assert trace[-1][0:4]==[41,1,1,0] and trace[-1][4:]==[21,1],trace
  assert f.get('se_f_owner',1)==4 and not f.get('se_fs_owned',1) and not f.get('se_doc_read_locks',1)
  assert f.read(0x8880+31,1)==b'\1'
  assert f.canonical()==stable and g.queue()==queue and g.reu()==before,'decline itself must publish/retire/write nothing'
  f.settle();f.render();after=g.reu();assert f.canonical()==stable and g.queue()==queue and after==registered.fe_allowed(ob.geos,f,before,after)
  assert after[bank*65536:(bank+1)*65536]==before[bank*65536:(bank+1)*65536]
  bits,attrs,rows=plain.expected(f,data+bytes([ob.Q]),fonts,3);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
  assert f.merged()==data+bytes([ob.Q]) and f.read(0xc600,1024)==f.shim
  ob.geos.png(bits,attrs,out/'baseline1-fallback.png');cases.append(dict(tag='real-baseline1-decline-and-render',trace=trace,queue_unchanged=True,whole53_exact=True,whole16MiB_outside_precise_FE=True,pixels=64000))
  # Explicit between-slice authority fault: actual public state is not forged
  # into applicability; the original stale C1 must precede optional refusal.
  prepare();r=f.call('se_editor_service');assert not r.p&1 and f.m.read(0x9135)==41 and f.m.read(0x9136)==1
  before=g.reu();stable=f.canonical();queue=g.queue();value=f.get('se_bc_incarnation',4);f.put('se_bc_incarnation',value^1,4)
  r=f.call('se_editor_service');f.put('se_bc_incarnation',value,4)
  assert f.get('se_e_error',1)==0xc1 and not any(f.get(n,1)for n in('se_e_job','se_f_owner','se_fs_owned','se_doc_read_locks'))
  want=bytearray(queue[0]);want[13]&=~(8|32);assert g.queue()==(bytes(want),queue[1]) and g.reu()==before and f.canonical()==stable and f.read(0xc600,1024)==f.shim
  cases.append(dict(tag='real-baseline1-yielded-incarnation-fault',error=0xc1,whole16MiB_exact=True,canonical_exact=True))
  result=dict(status='PASS',identity=identity,cases=cases,wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope=__doc__)
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('BASELINE1_REFUSAL_PASS',out,flush=True);return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--project',type=Path,required=True);p.add_argument('--out',type=Path);a=p.parse_args();out=a.out or ROOT/'build/cache-rebase-refusal'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');run(out.resolve(),a.fixture.resolve(),a.project.resolve())
