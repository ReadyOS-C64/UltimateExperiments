"""Current sealed standalone lifecycle gallery, four sequential private VICE runs.

Reuses the actual C29/R26 native experiment without modifying its implementation.
Own binary8500/text8600..8639, private disk/PID per run. Requires an explicitly
released immutable fixture. Controlled monitor bootstrap/PC/SP/IRQ seams remain
those documented by test_lifecycle_native; no physical RESTORE or OS handoff.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,socket,zipfile
import test_lifecycle_native as lifecycle
import vice_plan
from overlay_catalog_policy import catalog_identity,catalog_state
ROOT=lifecycle.ROOT

class CurrentPlan(lifecycle.Plan):
 def raw(self,ident,commands):
  commands=list(commands)
  if ident=='fresh_restore_coherent' and self.s.get('se_overlay_managed_verification')==1:
   idle=f'until ${self.s["se_idle"]:04x}'
   assert commands.count(idle)==1
   at=commands.index(idle);caps=self.out/'captures'
   commands[at:at]=[f'until ${self.s["se_doc_invalidate"]:04x}',f'bsave "{caps}/memo-invalidated-ram.bin" 0 $0000 $cfff']
  return super().raw(ident,commands)
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8500
  p['global_defaults']['monitor_port_span']=1
  assert not p['global_defaults'].get('kill_stale',False)
  return p

def free_ports():
 # Fail before starting a process; never clean up another lane's emulator.
 for port in [8500,*range(8600,8640)]:
  with socket.socket()as s:
   try:s.bind(('127.0.0.1',port))
   except OSError as error:raise AssertionError(f'owned port{port} already busy')from error

def verifier_zip(e):
 # Freeze the executed wrapper and imported Python verification/model sources.
 with zipfile.ZipFile(e/'current-verifier.zip','w',zipfile.ZIP_DEFLATED)as z:
  for directory in ('tests','tools'):
   for p in sorted((ROOT/directory).glob('*.py')):z.write(p,p.relative_to(ROOT))

def run_one(fixture,mode,preview=False):
 free_ports()
 # Rebuild only private C29/R26 using exact frozen lifecycle source and current
 # feature flags, then require byte identity with every packaged actual asset.
 report=json.loads((fixture/'build/editor-report.json').read_text());managed=report['symbols'].get('se_overlay_managed_verification',0)
 assert managed in(0,1)
 with zipfile.ZipFile(fixture/'product-sources.zip')as source:
  for name in ('adapter.s','adapter.inc','resume.s','resume.inc','copy-entry.s','copy-entry.inc','preflight.s','preflight.inc'):
   assert source.read('src/lifecycle/'+name)==(ROOT/'src/lifecycle'/name).read_bytes(),('current lifecycle source differs from released fixture',name)
 oldcommand=lifecycle.component.command
 def compile_flags(*args):
  args=list(args)
  if managed and args[0]=='ca65' and str(args[-1]).endswith(('/resume.s','/copy-entry.s')):args[1:1]=['-D','EDITOR_MANAGED_CODE=1']
  return oldcommand(*args)
 lifecycle.component.command=compile_flags
 try:e=lifecycle.prepare(fixture)
 finally:lifecycle.component.command=oldcommand
 (e/'lifecycle-build-policy.json').write_text(json.dumps(dict(managed_verification=managed,resume_flags=['EDITOR_MANAGED_CODE=1']if managed else[],copy_flags=['EDITOR_MANAGED_CODE=1']if managed else[],packaged_C29_R26_byte_identity=True),indent=2)+'\n')
 lifecycle.Plan=CurrentPlan
 n=lifecycle.scenario(e,mode,preview);plan=n.plan()
 assert plan['global_defaults']['monitor_port_start']==8500
 assert len({v['id']for v in plan['steps']})==len(plan['steps'])
 (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n')
 (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
 verifier_zip(e)
 project=lifecycle.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
 lifecycle.component.command('dotnet','build',project,'--nologo')
 print('CURRENT_NATIVE',e,'mode',mode,'preview',preview,'steps',len(n.steps),flush=True)
 vice_plan.run_plan(plan,n.out)
 result=lifecycle.evaluate(e)
 # Preserve exact raw restore assertions in the original evaluator. Identity
 # normalization here permits only bit7 of explicitly published slot bytes.
 sym=json.loads((e/'editor-report.json').read_text())['symbols'];caps=n.out/'captures';at=sym['se_overlay_ids'];catalogs={}
 for name in ('pending-before','prepared','exact-restored','prelude-finished','pending-resumed','typed-after','undo','saved','reopened'):
  memory=(caps/(name+'-ram.bin')).read_bytes();raw=memory[at:at+384]
  catalogs[name]=catalog_identity(raw,sym);catalog_state(raw,sym)
 assert len(set(catalogs.values()))==1,'lifecycle changed actual catalog identity'
 if managed:
  boundary=(caps/'memo-invalidated-ram.bin').read_bytes();raw=boundary[at:at+384];state=catalog_state(raw,sym)
  assert not any(value for value in state.verified if value is not None)
  assert not any(raw[64+i]&128 for i in range(64))
  assert boundary[sym['se_overlay_active']:sym['se_overlay_active']+2]==b'\0\0' and boundary[0xCBD5]==0
  assert catalog_identity(raw,sym)==next(iter(catalogs.values()))
  result['fresh_prelude_managed_invalidation']=dict(observed_before='se_doc_invalidate/first overlay call',verified_bits=0,active_tags=0,window_tag=0)
 result['catalog_identity_policy']='tools/overlay_catalog_policy.py; only published slot bit7 when declared feature1'

 free_ports() # Owned .NET/VICE process must release both monitor surfaces.
 identity=json.loads((e/'freeze.json').read_text())
 result['executed_wrapper_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 result['ports_released']=True;result['ports']=[8500,'8600..8639']
 (e/'current-result.json').write_text(json.dumps(result,indent=2)+'\n')
 print('CURRENT_PASS',e,identity['prg_sha256'],result['native_pixels'],flush=True)
 return dict(evidence=str(e.relative_to(ROOT)),mode=mode,preview=preview,
  prg_sha256=identity['prg_sha256'],disk_sha256=identity['disk_sha256'],frames=len(result['frames']),native_pixels=result['native_pixels'],saved_bytes=result['saved_bytes'])

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);p.add_argument('--run',action='store_true')
 p.add_argument('--mode',choices=('40','80','literal','preview','all'),default='all');a=p.parse_args()
 if not a.run:
  print('Prepared only. Explicit final fixture required; sequential40/80/literal/preview,24 captures, owned8500/text8600..8639.');return
 assert a.fixture and (a.fixture/'freeze.json').exists(),'explicit immutable parent-released fixture required'
 fixture=a.fixture.resolve();before=(fixture/'freeze.json').read_bytes()
 scenarios={'40':(0,False),'80':(2,False),'literal':(3,False),'preview':(3,True)}
 selected=scenarios if a.mode=='all'else{a.mode:scenarios[a.mode]}
 results=[]
 for name,(mode,preview)in selected.items():
  assert (fixture/'freeze.json').read_bytes()==before
  results.append(run_one(fixture,mode,preview))
 out=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-lifecycle-current-gallery');out.mkdir()
 result=dict(status='passed',fixture=str(fixture),cases=results,frames=sum(x['frames']for x in results),native_pixels=sum(x['native_pixels']for x in results),scope=__doc__,visual_review='pending')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print('CURRENT_GALLERY',out,flush=True)
if __name__=='__main__':main()
