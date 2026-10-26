"""Real IRQ Return at a short line end and Undo, in registered60/80 modes.

Uses the unchanged standalone source/history/settings/font/catalog/shim and
independent full native VIC evaluator. Owns8500/text8600..8639, private D81/PIDs.
"""
from pathlib import Path
import argparse,hashlib,inspect,json,shutil,subprocess,zipfile
import test_standalone_acceptance_vice as engine
import test_retention_grammar_registered_vice as ports
from closed_runtime_copy import run_with_closed_links
from d81_image import D81Image
import vice_plan

ROOT=engine.ROOT
SOURCE=engine.live.grid.native_text('Alpha words.\rBeta words.\rTail.\r')
NAME=b'TERM'

class Plan(engine.Plan):
 def plan(self):
  result=super().plan()
  result['global_defaults']['monitor_port_start']=8500
  return result
 def capture(self,ident,data,mode=3,ui=0,kind='source',**extra):
  # The inherited formatted-gallery capture requires stylevalid1. Plain
  # correctly publishes no semantic style map: require that exact policy.
  assert mode in (1,2) and ui==0
  self.memory(ident+'_plain','se_render_caps',0)
  self.memory(ident+'_stylevalid','se_st_valid',0)
  self.memory(ident+'_styledone','se_st_request',0)
  self.snapshot(ident,data,mode,ui)
  self.cases[-1].update(kind=kind,**extra)

def freeze(fixture):
 identity=json.loads((fixture/'freeze.json').read_text())
 assert len(identity['names'])==59
 assert identity['assets']['grid']=='5dac796bd1d81907be37ddd51d9acc7a984ab7c4304427502cb77a720a9c919c'
 assert identity['assets']['foldctl']=='53884af91475602c11020180c519e10f36fc59df83d0489286f6c21fa92a318b'
 e=engine.folds.freeze(fixture,identity['prg_sha256'],identity['disk_sha256'])
 target=ROOT/'agentsworking/evidence/M8'/e.name.replace('geos-fold-native','grid-terminal-registered-native')
 shutil.move(e,target);e=target
 shutil.copy2(e/'supereditor.d81',e/'working.d81')
 (e/'term.bin').write_bytes(SOURCE)
 result=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'term.bin'),'term,s'],capture_output=True)
 (e/'package.log').write_bytes(result.stdout+result.stderr)
 assert not result.returncode
 assert D81Image((e/'working.d81').read_bytes()).read(NAME,kind=1).data==SOURCE
 shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')
 return e

def scenario(e):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),'gallery')
 n.boot();n.typed('public_plain','syntax plain');n.memory('actual_plain','se_render_caps',0)
 at=SOURCE.index(b'\r');changed=SOURCE[:at]+b'\r'+SOURCE[at:]
 for mode in (1,2):
  tag=str(mode)
  n.open('open_'+tag,NAME);n.switch('mode_'+tag,mode)
  n.typed('goto_'+tag,'goto 1');n.typed('end_'+tag,'end')
  n.memory('terminal_position_'+tag,'se_hot_caret',at,3)
  n.send('actual_return_'+tag,b'\r');n.send('flush_left_'+tag,b'\x9d')
  n.shot('split-'+tag,changed,mode,caret=at,node=2,current=NAME)
  n.send('actual_undo_'+tag,b'\x1a')
  n.shot('undo-'+tag,SOURCE,mode,caret=at,current=NAME)
 return n

def evaluate(e):
 # Keep the standalone evaluator's complete per-frame source/history/fonts/
 # settings/catalog/shim/independent VIC checks byte-for-byte. Its final disk
 # policy belongs to a different scenario that creates four Save As files.
 # This scenario performs no saves: require the ENTIRE disk to stay identical.
 original=inspect.getsource(engine.evaluate)
 marker=" baseline=D81Image((e/'initial-fixtures.d81').read_bytes());disk="
 assert original.count(marker)==1
 prefix=original[:original.index(marker)]
 tail=""" assert (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes(),'Return/Undo changed read-only D81'
 result=dict(status='PASS',identity=identity,frames=observed,pixels=len(cases)*64000,attributes=len(cases)*1000,whole16MiB_readonly_intervals=intervals,read_only_disk=True)
 return result
"""
 source=prefix+tail
 (e/'gallery/registered-frame-evaluator.py').write_text(source)
 context=dict(vars(engine));exec(compile(source,str(e/'gallery/registered-frame-evaluator.py'),'exec'),context)
 result=context['evaluate'](e,'gallery')
 result.update(scope=__doc__,visual_review='pending')
 (e/'gallery/registered-result.json').write_text(json.dumps(result,indent=2)+'\n')
 return result

def run(fixture):
 ports.free_ports();e=freeze(fixture);n=scenario(e);plan=n.plan()
 assert len({x['id']for x in plan['steps']})==len(plan['steps'])
 (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
 (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n')
 with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in ('tests','tools'):
   for p in sorted((ROOT/folder).glob('*.py')):z.write(p,p.relative_to(ROOT))
 project=engine.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
 built=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120)
 (n.out/'dotnet-build.log').write_text(built.stdout+built.stderr);assert not built.returncode
 print('NATIVE',e,'steps',len(n.steps),'IRQbytes',n.keys,'frames',len(n.cases),flush=True)
 run_with_closed_links(engine.capacity.run_owned_plan,plan,n.out,timeout=900)
 ports.free_ports();return evaluate(e)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);p.add_argument('--verify',type=Path);a=p.parse_args()
 if a.verify:evaluate(a.verify.resolve())
 else:
  assert a.fixture;run(a.fixture.resolve())
