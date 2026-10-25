"""Read-only combined48 source60/80 typing attribution; owned8100/text8200."""
from pathlib import Path
from datetime import datetime,timezone
import json,argparse,shutil,zipfile,subprocess,re,threading
import test_display_timing_vice as timing
import test_reu_capacity_vice as runner
import vice_plan
ROOT=timing.ROOT
PLAIN=timing.native.live.grid.native_text('# Heading\rPlain paragraph having ample room.\rSecond untouched source row.\rTail.')
class Plan(timing.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8100;p['global_defaults']['monitor_port_span']=1;assert not p['global_defaults'].get('kill_stale',False);return p

def scenario(e):
 n=Plan(e,json.load(open(e/'editor-report.json')),1,0);n.cost_profile=True;n.boot();n.open('open_diverse',b'DIVERSE');data=timing.native.live.grid.fixture()
 for mode in [1,2]:
  n.mode_to(mode);n.typed('top'+str(mode),'top');n.measure('m'+str(mode)+'-front-heading',timing.native.live.grid.native_text('Q')+data,mode,key=timing.native.live.grid.native_text('Q')[0]);n.send('undo_front'+str(mode),b'\x1a')
 n.send('force_dirty_before_plain',b'X');n.open('open_plain',b'PLAIN',choice='D');data=PLAIN;at=data.index(timing.native.live.grid.native_text('having'))+2
 for mode in [1,2]:
  n.mode_to(mode);n.typed('plain_goto'+str(mode),'goto 2');n.send('plain_column'+str(mode),b'\x1d'*(at-data.index(b'\r')-1));n.memory('plain_caret'+str(mode),'se_hot_caret',at,3)
  inserted=data[:at]+b'X'+data[at:];n.measure('m'+str(mode)+'-plain-insert',inserted,mode,key=ord('X'));n.measure('m'+str(mode)+'-plain-delete',data,mode,key=0x14)
 return n

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();e=timing.freeze(a.fixture.resolve(),'source-grid-profile');q=e/'plain.bin';q.write_bytes(PLAIN);z=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(q),'plain,s'],capture_output=True,text=True);assert not z.returncode;n=scenario(e);plan=n.plan();(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
 with zipfile.ZipFile(e/'profile-verifier.zip','w',zipfile.ZIP_DEFLATED)as z:
  for d in ['tests','tools']:
   for p in(ROOT/d).glob('*.py'):z.write(p,p.relative_to(ROOT))
 print('RUN',e,len(n.steps),'steps',flush=True);stop=threading.Event()
 def watch():
  while not stop.wait(.05):
   p=subprocess.run(['ps','-axo','pid=,ppid=,command='],capture_output=True,text=True)
   for l in p.stdout.splitlines():
    if '/x64sc 'in l and str(e/'working.d81')in l:
     a=l.strip().split(None,2);(e/'owned-process.json').write_text(json.dumps(dict(PID=int(a[0]),command=a[2]),indent=2)+'\n');return
 t=threading.Thread(target=watch,daemon=True);t.start()
 try:
  project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode;runner.run_owned_plan(plan,n.out,timeout=900);r=timing.evaluate(n);summary=[]
  for item in r['measurements']:
   c=item['cost_profile'];cut=item['first_publish_cycles'];first=[q for q in c['overlay_intervals']if q['end']<=cut];later=[q for q in c['overlay_intervals']if q['entry']>cut]
   def groups(xs):
    ids=sorted(set((q['slot'],q['id'])for q in xs));return[dict(slot=s,id=i,calls=sum(1 for q in xs if(q['slot'],q['id'])==(s,i)),payload_self=sum(q['payload_self']for q in xs if(q['slot'],q['id'])==(s,i)),admission=sum(q['admission']for q in xs if(q['slot'],q['id'])==(s,i)))for s,i in ids]
   summary.append(dict(id=item['id'],first=cut,idle=item['emulated_cycles'],first_groups=groups(first),later_groups=groups(later),all_groups=c['groups'],counters=item['counter_deltas']))
  (n.out/'attribution.json').write_text(json.dumps(dict(status='passed',cases=summary),indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
 finally:
  stop.set();t.join(timeout=2)
  if(e/'owned-process.json').exists():
   p=json.load(open(e/'owned-process.json'));q=subprocess.run(['ps','-p',str(p['PID']),'-o','pid=,comm='],capture_output=True,text=True);assert not q.stdout.strip();p['closed']=True;(e/'closure.json').write_text(json.dumps(p,indent=2)+'\n')
if __name__=='__main__':main()
