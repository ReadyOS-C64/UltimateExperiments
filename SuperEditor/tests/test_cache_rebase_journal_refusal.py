"""Actual producer journal under/exact/full48 applicability boundary, CPU only.

Twenty-four real public insertion+flush+COW transactions create the root;
no host root/journal metadata is seeded. The one-pending49 check explicitly
uses the released derived-cache invalidation benchmark seam to force render
without flushing. Production source/history/ref authority is never fabricated.
"""
from pathlib import Path
import argparse,inspect,json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_rebase_registered as registered


def boundary(locals_,out):
 f,g,arena,check=map(locals_.get,('f','g','arena','check'));data=locals_['data'];before_root=registered.suite.sp.roots(arena()[1]);assert before_root[2][30:32]==bytes([48,5])
 results=[];trace=[];original=f.call
 def call(name,a=0):
  before=(f.m.read(0x9135),f.m.read(0x9136))if name=='se_editor_service'and f.get('se_e_job',1)==11 else None
  r=original(name,a)
  if before:trace.append([*before,r.a,r.p&1,f.m.read(0x9135),f.m.read(0x9136)])
  return r
 f.call=call
 def force_pending_render():
  # Same declared benchmark seam as the original pure-REKEY protocol. Only
  # disposable derived validity is revoked; source/BC root/queue are untouched.
  for name in('se_gc_width','se_r_valid','se_l_valid'):f.put(name,0,1)
  f.m.write(0xcf90,0);f.m.write(0xcfe8,0);f.put('se_l_need_wrap',1,1)
 def readonly_fallback(tag,queued):
  before=g.reu();stable=f.canonical();queue=g.queue();root=registered.suite.sp.roots(arena()[1]);trace.clear();f.render();after=g.reu()
  assert f.canonical()==stable and g.queue()==queue and f.get('se_bc_count',1)==queued
  assert registered.suite.sp.roots(arena()[1])==root,'full journal refusal altered selected root/sequence'
  assert after==registered.fe_allowed(registered.suite.ob.geos,f,before,after),'full16MiB outside authenticatedFE changed'
  handoffs=[x for x in trace if x[0]==41 and x[4]==21];assert handoffs and all(x[2:]==[1,0,21,1]for x in handoffs),handoffs
  digest=check(tag,data);results.append(dict(tag=tag,journal_count=48,queued=queued,sum=48+queued,C41_to_C21=handoffs,whole53_exact=True,whole16MiB_precise_FE_only=True,pixels_sha256=digest))
 try:
  # Real pending SPLICE makes48+1=49, while all24priorCOWs already proved
  # under and exact48 admission using original source/pixel/COW oracles.
  q=bytes([registered.suite.ob.Q]);at=f.get('se_hot_caret');f.key(q[0]);data=data[:at]+q+data[at:];assert f.merged()==data and f.get('se_bc_count',1)==1
  force_pending_render();readonly_fallback('full48-plus-one-pending',1)
  # Real WRAP_OFF flush adds the genuine REKEY, making48+2=50.
  f.command(77);assert f.get('se_bc_count',1)==2;readonly_fallback('full48-plus-splice-rekey',2)
  # Genuine between-yield incarnation fault must still failC1 BEFORE capacity
  # applicability. Keep the old valid full48 graph and queue byte-exact.
  force_pending_render();f.call('se_editor_render')
  for _ in range(100):
   if f.m.read(0x9135)==41 and f.m.read(0x9136)==0:break
   f.call('se_editor_service')
  else:raise AssertionError('C41 BEGIN not reached for stale control')
  r=f.call('se_editor_service');assert not r.p&1 and f.m.read(0x9135)==41 and f.m.read(0x9136)==1
  before=g.reu();stable=f.canonical();queue=g.queue();inc=f.get('se_bc_incarnation',4);f.put('se_bc_incarnation',inc^1,4);r=f.call('se_editor_service');f.put('se_bc_incarnation',inc,4)
  assert f.get('se_e_error',1)==0xc1 and not any(f.get(n,1)for n in('se_f_owner','se_e_job','se_fs_owned','se_doc_read_locks'))
  expected=bytearray(queue[0]);expected[13]&=~(8|32);assert g.queue()==(bytes(expected),queue[1])and g.reu()==before and f.canonical()==stable and f.read(0xc600,1024)==f.shim
  results.append(dict(tag='full48-held-incarnation-fault',error=0xc1,whole16MiB_exact=True,canonical_and_queue_exact=True))
  (out/'journal-boundary.json').write_text(json.dumps(dict(status='PASS',cases=results,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
 finally:f.call=original


def run(out,fixture,project):
 original_adapt=registered.adaptation
 def adapt(dest):
  ns=original_adapt(dest);text=(dest/'registered-run.py').read_text();needle='  faults=[]\n  if protocols:';assert text.count(needle)==1;text=text.replace(needle,"  journal_boundary(locals(),out)\n  faults=[]\n  if protocols:")
  ns['journal_boundary']=boundary;exec(compile(text,str(dest/'journal-registered-run.py'),'exec'),ns);(dest/'journal-registered-run.py').write_text(text);return ns
 registered.adaptation=adapt
 text=inspect.getsource(registered.run);needle="'repeat': (8000, 4, True)";assert text.count(needle)==1;text=text.replace(needle,"'repeat': (8000, 24, False)")
 ns=dict(vars(registered));exec(compile(text,str(out)+'::actual24journal','exec'),ns)
 try:return ns['run'](out,fixture,project,('repeat',))
 finally:registered.adaptation=original_adapt
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--project',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.out.resolve(),a.fixture.resolve(),a.project.resolve())
