"""Current combined59 source/settings/GEOS-preview native gallery, original oracles."""
from pathlib import Path
import argparse,json,shutil,subprocess,zipfile
import test_presentation_vice as gallery
import test_cache_presentation_vice as current
import test_normal_row80_vice as ports
from test_grid_geometry_current import authenticate
from closed_runtime_copy import run_with_closed_links
ROOT=gallery.ROOT

class Plan(gallery.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8500;p['global_defaults']['monitor_port_span']=1;return p

def run(source):
 ports.free_ports();seal=authenticate(source);e=gallery.timing.freeze(source,'pal');target=e.with_name(e.name.replace('display-timing-pal','presentation-registered-native'));e.rename(target);e=target
 # timing.freeze already packages DIVERSE through the native fold freezer.
 # Verify that exact member rather than attempting a duplicate IEC filename.
 assert gallery.D81Image((e/'working.d81').read_bytes()).read(b'DIVERSE',kind=1).data==gallery.timing.native.live.grid.fixture()
 assert(e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes()
 original=gallery.Plan;gallery.Plan=Plan
 try:n=gallery.scenario(e)
 finally:gallery.Plan=original
 plan=n.plan();assert len({x['id']for x in plan['steps']})==len(plan['steps'])
 (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
 (n.out/'plan-metadata.json').write_text(json.dumps(dict(cold_end=n.cold_end,service_return=n.service_return,publish_pc=n.publish_pc,cost_points=n.cost_points),indent=2)+'\n')
 with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in('tests','tools'):
   for p in sorted((ROOT/folder).glob('*.py')):z.write(p,p.relative_to(ROOT))
 project=gallery.timing.native.live.grid.synchronous_project(n.out);gallery.vice_plan.PROJECT=project
 build=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(build.stdout+build.stderr);assert not build.returncode
 print('NATIVE',e,'frames',len(n.measurements),'binary8500/text8600..8639',flush=True)
 manifest=run_with_closed_links(gallery.capacity.run_owned_plan,plan,n.out,900);(n.out/'owned-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 result=current.evaluate(n);ports.free_ports();result.update(registered_seal=seal,visual_review='pending',scope=__doc__)
 (n.out/'registered-result.json').write_text(json.dumps(result,indent=2)+'\n');print('PRESENTATION_REGISTERED_PASS',e,flush=True);return e,result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);p.add_argument('--verify',type=Path);a=p.parse_args()
 if a.verify:
  e=a.verify.resolve();n=gallery.scenario_loaded(e);result=current.evaluate(n);ports.free_ports();result.update(registered_seal=authenticate(Path(json.loads((e/'freeze.json').read_text())['cpu_fixture'])),visual_review='pending',scope=__doc__)
  (n.out/'registered-result.json').write_text(json.dumps(result,indent=2)+'\n');print('PRESENTATION_REGISTERED_PASS',e,flush=True)
 else:
  if a.fixture is None:p.error('--fixture is required unless --verify is used')
  run(a.fixture.resolve())
