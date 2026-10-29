"""Owned native PAL GEOS/preview profile on an explicit immutable product."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,subprocess,zipfile
import test_display_timing_vice as timing
import test_reu_capacity_vice as capacity
import vice_plan
ROOT=timing.ROOT
class Plan(timing.Plan):
 def boot(self):
  super().boot()
  # Read-only natural BASIC SYS idle stack before the timing PC/SP seam.
  self.raw('natural_startup_idle',[
   'delete',f'break exec ${self.idle_pc:04x} if {self.condition(0)}','x','delete',
   f'logname "{self.out / "natural-startup-idle.log"}"','log on','registers','log off'])
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=7900;p['global_defaults']['monitor_port_span']=1
  p['global_defaults']['timeouts']['step_s']=120
  assert not p['global_defaults'].get('kill_stale',False)
  return p

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args()
 timing.Plan=Plan;e=timing.freeze(a.fixture.resolve(),'pal');n=timing.scenario(e,1,0,focus='geos',cost_profile=True);plan=n.plan()
 (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
 with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in('tests','tools'):
   for path in sorted((ROOT/folder).glob('*.py')):z.write(path,path.relative_to(ROOT))
 project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
 r=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(r.stdout+r.stderr);assert not r.returncode
 print('NATIVE',e,'captures',len(n.measurements),flush=True);capacity.run_owned_plan(plan,n.out,timeout=900);r=timing.evaluate(n)
 print('PASS',e,flush=True)
 for c in r['measurements']:print(json.dumps(dict(id=c['id'],cycles=c['first_publish_cycles'],loads=c['counter_deltas']['se_overlay_loads'],CRC=c['cost_profile']['crc_cycles'],groups=c['cost_profile']['groups'])),flush=True)
if __name__=='__main__':main()
