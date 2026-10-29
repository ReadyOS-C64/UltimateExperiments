"""Final body-memo resident compact media regression; private8700/text8800..8839.

Legacy scenarios and all protocol/pixel/chain/object oracles are unchanged.
Only immutable freeze cardinality and the owned ports differ. Actual media
failures remain distinct from named debugger ACK/catalog injections.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib,shutil,subprocess,zipfile,inspect
import test_final_file_faults_vice as prior
from overlay_catalog_policy import catalog_identity
import socket

def free_ports():
 for port in [8700,*range(8800,8840)]:
  with socket.socket()as s:
   try:s.bind(("127.0.0.1",port))
   except OSError as error:raise AssertionError(f"owned port{port} already busy")from error
import vice_plan
ROOT=prior.ROOT
CASES=['missing-device','write-protected','disk-full','cancel-write','cancel-candidate-scan','candidate-seq','candidate-prg','candidate-splat','promotion-ack-injected','missing-c12-save','missing-both-read']

class Plan(prior.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8700
  p['global_defaults']['monitor_port_span']=1
  assert not p['global_defaults'].get('kill_stale',False)
  return p

def freeze(source):
 names=json.loads((source/'freeze.json').read_text())['names']
 e=prior.frozen_native.freeze(source)
 target=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-current-file-faults-native'+str(len(names)))
 shutil.move(e,target);record=json.loads((target/'freeze.json').read_text());assert record['catalog']==names,'exact ordered approved catalog required'
 for artifact in ('working.d81','initial-fixtures.d81','diverse.bin','package.log'):(target/artifact).unlink(missing_ok=True)
 with zipfile.ZipFile(target/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in ('tests','tools'):
   for p in sorted((ROOT/folder).glob('*.py')):z.write(p,p.relative_to(ROOT))
 return target

def execute(e,case):
 free_ports();prior.old.package(e,case)
 r=json.loads((e/'editor-report.json').read_text());prior.old.FaultPlan=Plan
 n=prior.old.scenario(e,case,r);p=n.plan();assert p['global_defaults']['monitor_port_start']==8700
 assert len({s['id']for s in p['steps']})==len(p['steps'])
 (n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n')
 (n.out/'observations.json').write_text(json.dumps(n.observations,indent=2)+'\n')
 (n.out/'scenario.json').write_text(json.dumps(dict(source=n.source.hex(),injections=n.injections,keys=n.keys),indent=2)+'\n')
 project=prior.grid.synchronous_project(n.out);vice_plan.PROJECT=project
 built=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120)
 (n.out/'dotnet-build.log').write_text(built.stdout+built.stderr);assert not built.returncode
 print('CURRENT_NATIVE',case,n.out,len(n.steps),'steps',n.keys,'IRQbytes',flush=True)
 prior.runner.run_owned_plan(p,n.out,timeout=900)
 # Keep the actual protocol, source, UI, disk-chain and REU oracles. The only
 # evaluator delta permits the declared published verification bit after the
 # existing exact debugger-deleted-ID seam has been restored for comparison.
 managed=n.s.get('se_overlay_managed_verification',0)
 assert managed in(0,1)
 if managed:
  source=inspect.getsource(prior.evaluate)
  needle="  if stable_catalog is None:stable_catalog=bytes(catalog)"
  assert source.count(needle)==1
  source=source.replace(needle,"  catalog=bytearray(catalog_identity(catalog,n.s))\n"+needle)
  namespace=dict(vars(prior),catalog_identity=catalog_identity)
  exec(compile(source,str(n.out/'managed-evaluate.py'),'exec'),namespace)
  (n.out/'managed-evaluate.py').write_text(source)
  result=namespace['evaluate'](n)
 else:result=prior.evaluate(n)
 result['catalog_policy']='tools/overlay_catalog_policy.py; only published bit7 for declared feature1, after exact authorized debugger-ID restoration'

 free_ports()
 # Original evaluator's prose42 label is historical; its executable loop uses
 # the full current catalog. Preserve result and add exact wrapper provenance.
 result['actual_catalog_assets']=len(json.loads((e/'freeze.json').read_text())['catalog'])
 result['wrapper_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 result['ports_released']=True
 (n.out/'current-result.json').write_text(json.dumps(result,indent=2)+'\n')
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path);p.add_argument('--case',choices=CASES,action='append');a=p.parse_args()
 if not a.run:
  print(json.dumps(dict(status='prepared',ports=[8700,'8800..8839'],cases={c:prior.CASES[c]for c in CASES}),indent=2));return
 assert a.fixture and (a.fixture/'freeze.json').exists(),'explicit immutable fixture required'
 e=freeze(a.fixture.resolve());results=[]
 for case in a.case or CASES:
  r=execute(e,case);results.append(dict(case=case,status=r['status'],screens=r['screens'],pixels=r['pixels']))
 result=dict(status='passed',fixture=str(a.fixture.resolve()),catalog_assets=len(json.loads((e/'freeze.json').read_text())['catalog']),results=results,screens=sum(x['screens']for x in results),pixels=sum(x['pixels']for x in results),ports_released=True,visual_review='pending',scope=__doc__)
 (e/'current-summary.json').write_text(json.dumps(result,indent=2)+'\n');print('CURRENT_COMPLETE',e,flush=True)
if __name__=='__main__':main()
