"""CurrentC32split8 NTSC12, originalnativeguards, owned8100/text8200."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,sys,threading,subprocess,time,hashlib,shutil
import test_geos_style_profile_vice as style
from png_pixels import read_png
ROOT=style.ROOT;LAST=None;STOP=threading.Event();WATCH=None
class Plan(style.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8100;p['global_defaults']['monitor_port_span']=1
  assert not p['global_defaults'].get('kill_stale',False)
  return p
original_freeze=style.freeze

def freeze(source):
 global LAST,WATCH
 e=original_freeze(source);target=e.with_name(e.name.replace('-style-typing-profile-native','-style-typing-ntsc-native'));shutil.move(e,target);LAST=target
 def observe():
  while not STOP.wait(.1):
   p=subprocess.run(['ps','-axo','pid=,ppid=,command='],capture_output=True,text=True)
   for line in p.stdout.splitlines():
    if '/x64sc 'in line and '-binarymonitoraddress 127.0.0.1:8100'in line and str(target/'working.d81')in line:
     fields=line.strip().split(None,2);(target/'owned-process.json').write_text(json.dumps(dict(PID=int(fields[0]),parent=int(fields[1]),command=fields[2],binary_port=8100,text_port=8200,source='Readonlypsmatch requires exactprivateworkingD81 AND binaryport',kill_stale=False),indent=2)+'\n');return
 WATCH=threading.Thread(target=observe,daemon=True);WATCH.start();return target

def compare(e,reference):
 actual=json.loads((e/'timing/result.json').read_text());old=json.loads((reference/'timing/result.json').read_text());assert actual['standard']==2 and actual['vicii_model']==3 and old['standard']==1;checks=[]
 for a,b in zip(actual['measurements'],old['measurements']):
  assert a['id']==b['id']and a['source']==b['source'];ident=a['id'];np=e/'timing'/('native-'+ident+'.png');pp=reference/'timing'/('native-'+ident+'.png');w,h,pixels=read_png(np);pw,ph,prior=read_png(pp);x,y=actual['native_viewport'];px,py=old['native_viewport'];now=[pixels[(y+yy)*w+x+xx]for yy in range(200)for xx in range(320)];before=[prior[(py+yy)*pw+px+xx]for yy in range(200)for xx in range(320)];assert now==before,(ident,'reviewedPALcrop');checks.append(dict(id=ident,exact_native_pixels=64000,ntsc_cycles=a['first_publish_cycles'],reference_pal_cycles=b['first_publish_cycles'],ntsc_sha256=hashlib.sha256(np.read_bytes()).hexdigest(),reference_sha256=hashlib.sha256(pp.read_bytes()).hexdigest()))
 assert len(checks)==12;r=dict(status='passed',reference=str(reference),checks=checks,pixels=768000,scope='EachcurrentNTSC320x200crop exactreviewedpreviousPALstylescounterpart; same12canonicaleditstates. Videostalls/firstprime differ; no PC/inputseamweakening.');(e/'reviewed-pal-comparison.json').write_text(json.dumps(r,indent=2)+'\n');return r

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path,required=True);p.add_argument('--standard',choices=['ntsc'],default='ntsc');p.add_argument('--reference',type=Path,default=ROOT/'agentsworking/evidence/M8/20261025T140416711643Z-style-typing-profile-native');a=p.parse_args();assert a.run
 style.Plan=Plan;style.freeze=freeze;sys.argv=['test_geos_style_profile_vice.py','--run','--fixture',str(a.fixture.resolve()),'--standard','ntsc']
 try:style.main();compare(LAST,a.reference.resolve());print('ALL12PALCROPSEQUAL',LAST,flush=True)
 finally:
  STOP.set()
  if WATCH:WATCH.join(timeout=2)
if __name__=='__main__':main()
