"""Private48 PAL C33 cycle check on owned8300/text8400.

Uses established explicitPC/SP/public-input stopwatch seam; no physical-input
latency claim. No product/sharedbuild changes. Full native oracle retained.
"""
from pathlib import Path
import argparse,json,shutil,subprocess,zipfile,hashlib
import test_display_timing_vice as timing
import test_grid_caret_candidate_vice as proof
import vice_plan
ROOT=proof.ROOT
class Plan(timing.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8300;return p

def scenario(e):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.cost_profile=True;data=timing.native.live.grid.fixture();n.boot();n.open('open_diverse',b'DIVERSE')
 for mode in (0,1,2):
  n.mode_to(mode);n.typed('top'+str(mode),'top');n.measure('m'+str(mode)+'-right',data,mode,key=0x1d,category='warm-right');n.measure('m'+str(mode)+'-left',data,mode,key=0x9d,category='warm-left')
  if mode:
   n.typed('cross_goto'+str(mode),'goto 2');n.measure('m'+str(mode)+'-cross-left',data,mode,key=0x9d,category='cross-CR-left');n.measure('m'+str(mode)+'-cross-right',data,mode,key=0x1d,category='cross-CR-right')
 return n

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--base',type=Path,default=proof.DEFAULT);a=p.parse_args()
 if not a.run:print('Prepared private PAL10 on8300/text8400; --run');return
 proof.ports_free();e=timing.freeze(a.base.resolve(),'pal');target=ROOT/'agentsworking/evidence/M8'/e.name.replace('-display-timing-pal','-grid-caret-timing-pal');shutil.move(e,target);e=target;n=scenario(e);plan=n.plan();(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
 with zipfile.ZipFile(e/'verifier-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in ('tests','tools'):
   for q in sorted((ROOT/folder).glob('*.py')):z.write(q,q.relative_to(ROOT))
 project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode;print('NATIVE',e,len(n.measurements),'PAL',flush=True)
 try:timing.native.live.grid.run_plan(plan,n.out)
 finally:proof.ports_free()
 result=timing.evaluate(n);rows=[]
 for m in result['measurements']:
  cap=n.out/'captures';before=(cap/(m['id']+'-before-ram.bin')).read_bytes();after=(cap/(m['id']+'-ram.bin')).read_bytes();s=n.s
  for name,w in [('se_doc_roots',512),('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),('se_clip_length',3)]:assert before[s[name]:s[name]+w]==after[s[name]:s[name]+w],(m['id'],'canonical/history/clip',name)
  if m['mode']:
   assert after[0x89c0]==1,(m['id'],'actualC33TRY-not-fullfallback')
  else:assert m['counter_deltas']['se_overlay_loads']==0
  rows.append(dict(id=m['id'],cycles=m['emulated_cycles'],first_publish=m['first_publish_cycles'],counters=m['counter_deltas'],payload_groups=m['cost_profile']['groups']))
 (n.out/'summary.json').write_text(json.dumps(dict(status='passed',cases=rows,scope=__doc__,native_pixels=result['native_pixels'],resident=result['identity']['prg_sha256']),indent=2)+'\n');print(json.dumps(rows,indent=2),flush=True)
if __name__=='__main__':main()
