"""Paired public TOP commands on explicit frozen editors; owned PAL VICE10100.
Established stopwatch public-input PC/SP seam; not physical input latency.
"""
from pathlib import Path
import argparse,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_queued_repaint_vice as queue
from d81_image import D81Image
T=queue.timing;owned=queue.owned

def run(base,out):
 assert not out.exists();out.mkdir(parents=True)
 e=T.freeze(base,'pal');(out/'fixture.txt').write_text(str(e)+'\n')
 sentence=T.native.live.grid.native_text('Ordinary prose words across a long complete logical source line remain unchanged. ')
 long=(sentence*20)[:862]+b'\r'
 wrapped=T.native.live.grid.native_text('Plain **strong words** and *italic words* across one continuing paragraph. '*11+'\r')
 docs=[('LONG','full',long),('WRAPPED','markdown',wrapped)]
 for name,_,data in docs:
  p=e/(name+'.bin');p.write_bytes(data)
  r=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(p),name.lower()+',s'],capture_output=True,text=True,errors='replace');assert not r.returncode,r.stdout+r.stderr
  assert D81Image((e/'working.d81').read_bytes()).read(name.encode(),kind=1).data==data
 n=queue.Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.boot()
 for name,preset,data in docs:
  n.open(name+'_open',name.encode());n.typed(name+'_preset','syntax '+preset)
  n.typed(name+'_hires','mode hires');n.typed(name+'_bottom','bottom')
  n.send(name+'_TOP_prompt',b'\x88'+T.native.live.grid.native_text('top'),ui=2)
  n.measure(name+'_TOP',data,3,key=13,category='public TOP Return to completed source page')
 plan=n.plan();assert len(plan['steps'])==len({x['id']for x in plan['steps']})
 (n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
 (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n')
 p=n.out/'plan.yaml';p.write_text(json.dumps(plan,indent=2)+'\n')
 shutil.copy2(__file__,out/'executed.py')
 project=owned.private_project(n)
 b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'build.log').write_text(b.stdout+b.stderr);assert not b.returncode
 owned.free_ports();env=dict(os.environ,**{owned.ENV:str(n.out/'owned-process.json')})
 cmd=['dotnet','run','--no-build','--project',str(project),'--','run-plan','--plan',str(p),'--close-vice','--no-tui']
 print('NATIVE',e,flush=True)
 try:
  with(n.out/'stdout.txt').open('w')as so,(n.out/'stderr.txt').open('w')as se:
   proc=subprocess.Popen(cmd,cwd=ROOT,stdout=so,stderr=se,env=env)
   try:assert proc.wait(timeout=600)==0
   finally:
    if proc.poll()is None:proc.terminate();proc.wait(timeout=10)
 finally:owned.close_owned(n.out,e)
 r=json.loads((n.out/'stdout.txt').read_text());assert r['Status']=='success',r
 shutil.copytree(r['RunDir'],n.out/'run',copy_function=os.link)
 result=T.evaluate(n)
 compact=dict(status='PASS',fixture=str(base),native=str(e),cases=[dict(id=x['id'],cycles=x['emulated_cycles'],first_publish=x['first_publish_cycles'],service_peak=x['service_peak_cycles'],counters=x['counter_deltas'])for x in result['measurements']],scope=__doc__)
 (out/'result.json').write_text(json.dumps(compact,indent=2)+'\n');print(json.dumps(compact),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.fixture.resolve(),a.out.resolve())
