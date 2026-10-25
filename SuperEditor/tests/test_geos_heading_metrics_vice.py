"""Native heading transition and corrective Backspace on packaged public paths.

Owned7900/text8000, actual File/Open and IRQ-enabled stopwatch input seam.
No asset replacement or make. Canonical source/font pixels use the existing
native evaluator; both events must publish the real dirty-row FAST2 result.
"""
from pathlib import Path
import argparse,json,subprocess,zipfile
import test_geos_preview_metrics_vice as metrics
import test_reu_capacity_vice as capacity
import vice_plan

timing=metrics.timing
ROOT=metrics.ROOT

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--standard',choices=['pal','ntsc'],default='pal');a=p.parse_args()
 e=timing.freeze(a.fixture.resolve(),a.standard);standard,model=(1,0)if a.standard=='pal'else(2,3)
 n=metrics.Plan(e,json.loads((e/'editor-report.json').read_text()),standard,model);n.cost_profile=True
 n.boot();n.open('open_diverse',b'DIVERSE');n.typed('enter_geos','mode hires');n.typed('at_top','top')
 data=timing.native.live.grid.fixture();q=timing.native.live.grid.native_text('Q')[0]
 n.measure('heading-insert',bytes([q])+data,3,key=q,category='heading-to-prose')
 n.memory('insert_real_dirty_row',0x9148,2)
 n.measure('heading-backspace',data,3,key=0x14,category='prose-to-heading')
 n.memory('backspace_real_dirty_row',0x9148,2)
 plan=n.plan();(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
 with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in('tests','tools'):
   for path in sorted((ROOT/folder).glob('*.py')):z.write(path,path.relative_to(ROOT))
 project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
 build=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(build.stdout+build.stderr);assert not build.returncode
 print('NATIVE',e,'captures',len(n.measurements),flush=True);capacity.run_owned_plan(plan,n.out,timeout=900);r=timing.evaluate(n)
 assert len(r['measurements'])==2
 print('PASS',e,flush=True)
 for c in r['measurements']:print(json.dumps(dict(id=c['id'],cycles=c['first_publish_cycles'],loads=c['counter_deltas']['se_overlay_loads'])),flush=True)

if __name__=='__main__':main()
