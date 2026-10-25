"""Owned NTSC counterpart of actual seven-case PAL preview metrics, no substitutions."""
from pathlib import Path
import argparse,json,subprocess,zipfile,hashlib
import test_geos_preview_metrics_vice as metrics
from png_pixels import read_png
import vice_plan
ROOT=metrics.ROOT;timing=metrics.timing
class Plan(metrics.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8300;p['global_defaults']['monitor_port_span']=1
  assert not p['global_defaults'].get('kill_stale',False)
  return p

def compare_pal(e,pal):
 actual=json.loads((e/'timing/result.json').read_text());reference=json.loads((pal/'timing/result.json').read_text());assert actual['identity']['prg_sha256']==reference['identity']['prg_sha256']and actual['identity']['disk_sha256']==reference['identity']['disk_sha256'];checks=[]
 for a,b in zip(actual['measurements'],reference['measurements']):
  assert a['id']==b['id'];ident=a['id'];ntsc=e/'timing'/('native-'+ident+'.png');pp=pal/'timing'/('native-'+ident+'.png');w,h,np=read_png(ntsc);pw,ph,pixels=read_png(pp);nx,ny=actual['native_viewport'];px,py=reference['native_viewport'];nc=[np[(ny+y)*w+nx+x]for y in range(200)for x in range(320)];pc=[pixels[(py+y)*pw+px+x]for y in range(200)for x in range(320)];assert nc==pc,(ident,'PAL/NTSC exactVICcrop');checks.append(dict(id=ident,exact_VIC_crop_pixels=64000,ntsc_cycles=a['first_publish_cycles'],pal_cycles=b['first_publish_cycles'],ntsc_png_sha256=hashlib.sha256(ntsc.read_bytes()).hexdigest(),pal_png_sha256=hashlib.sha256(pp.read_bytes()).hexdigest()))
 assert len(checks)==7;result=dict(status='passed',PAL=str(pal),NTSC=str(e),checks=checks,scope='AllsevenNTSCnative320x200crops exactPALindependentlyverifiedcrops; screenshotreviewbyexactmatch. TimingseamPC/SP/inputfieldintervention retained, notphysicalkeylatency.');(e/'pal-ntsc-comparison.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--pal',type=Path,required=True);a=p.parse_args();timing.Plan=Plan;e=timing.freeze(a.fixture.resolve(),'ntsc');n=timing.scenario(e,2,3,focus='geos',cost_profile=True);plan=n.plan();assert len(n.measurements)==7
 (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
 with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in('tests','tools'):
   for path in sorted((ROOT/folder).glob('*.py')):z.write(path,path.relative_to(ROOT))
 project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;r=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(r.stdout+r.stderr);assert not r.returncode
 print('NATIVE',e,'binary8300/text8400','captures',len(n.measurements),flush=True);metrics.capacity.run_owned_plan(plan,n.out,timeout=900);r=timing.evaluate(n);compare_pal(e,a.pal.resolve());print('PASS',e,flush=True)
 for c in r['measurements']:print(json.dumps(dict(id=c['id'],cycles=c['first_publish_cycles'],loads=c['counter_deltas']['se_overlay_loads'],CRC=c['cost_profile']['crc_cycles'])),flush=True)
if __name__=='__main__':main()
