"""Current48 genuine TOP0 GEOS full-page attribution, private8300/text8400.

The unchanged established stopwatch seam setsPC/SP/public-render only after
normalIRQ File/Open/mode setup. Explicitly invalidates all derived fast caches;
never changes source/style/geometry/font/provider or weakens native pixel guards.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,shutil,subprocess,zipfile
import test_display_timing_vice as timing
import test_grid_caret_candidate_vice as ports
import vice_plan
ROOT=timing.ROOT
DEFAULT=ROOT/'build/geos-incremental-editor/20261025T171440790321Z/fixture'
class Plan(timing.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8300;return p

def run(base):
 ports.ports_free();e=timing.freeze(base,'pal');target=ROOT/'agentsworking/evidence/M8'/e.name.replace('-display-timing-pal','-geos-rebuild-profile');shutil.move(e,target);e=target
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.cost_profile=True;n.boot();n.open('open_diverse',b'DIVERSE');n.typed('GEOS','mode hires');n.typed('canonical_top0','top');n.memory('top0_actual','se_v_top',0,3)
 data=timing.native.live.grid.fixture();n.measure('m3-full',data,3,full=True,category='forced-full-TOP0-rebuild')
 script=n.out/'m3-full_timed_coherent.mon';text=script.read_text();needle='logname ';at=text.index(needle);text=text[:at]+f'> cf90 00\n> cfe8 00\n> {n.s["se_gc_width"]:04x} 00\n'+text[at:];script.write_text(text)
 p=n.plan();(n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
 with zipfile.ZipFile(e/'verifier-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in ('tests','tools'):
   for q in sorted((ROOT/folder).glob('*.py')):z.write(q,q.relative_to(ROOT))
 project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode;print('NATIVE',e,flush=True)
 try:timing.native.live.grid.run_plan(p,n.out)
 finally:ports.ports_free()
 result=timing.evaluate(n);assert result['measurements'][0]['top']==0;return e,result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path,default=DEFAULT);a=p.parse_args()
 if a.run:
  e,r=run(a.fixture.resolve());print(e,flush=True);m=r['measurements'][0];print('CYCLES',m['emulated_cycles'],m['counter_deltas'],flush=True)
  for g in m['cost_profile']['groups']:print(g,flush=True)
 else:print('Prepared current48 TOP0 full-rebuild attribution; no product/native until --run')
