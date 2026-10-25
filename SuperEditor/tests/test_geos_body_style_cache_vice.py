"""Private actual-C26 crossrow cache PAL comparison, owned8300/text8400."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,threading,time,zipfile
import test_geos_body_style_cache as candidate
import test_display_timing_vice as timing
from d81_image import D81Image
import vice_plan
ROOT=candidate.ROOT
class Plan(timing.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8300;p['global_defaults']['monitor_port_span']=1;assert not p['global_defaults'].get('kill_stale',False);return p

def prepare(base,control=False):
 out=ROOT/'build/geos-body-style-native-input'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+('-control'if control else'-candidate'));out.mkdir(parents=True)
 if control:
  fixture=out/'fixture';shutil.copytree(base,fixture)
 else:fixture=candidate.builder().install(out,base)
 disk=fixture/'build/supereditor.d81';args=['c1541','-attach',str(disk)]
 if not control:
  for n in('geosline','geosfold'):args+=['-delete',n,'-write',str(fixture/'build/overlays'/(n+'.seo')),n+',s']
  p=subprocess.run(args,capture_output=True,text=True);(out/'package.log').write_text(p.stdout+p.stderr);assert not p.returncode,p.stdout+p.stderr
 identity=json.loads((fixture/'freeze.json').read_text());image=D81Image(disk.read_bytes())
 for name in identity['names']:assert image.read(name.upper().encode(),kind=1).data==(fixture/'build/overlays'/(name+'.seo')).read_bytes(),name
 assert image.read(b'SUPEREDITOR',kind=2).data==(fixture/'build/editor.prg').read_bytes()
 identity['disk_sha256']=hashlib.sha256(disk.read_bytes()).hexdigest();identity['native_disk_packaged']=True
 (fixture/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n');manifest=json.loads((fixture/'build/disk-manifest.json').read_text());manifest.update(sha256=identity['disk_sha256'],disk=str(disk));(fixture/'build/disk-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 e=timing.freeze(fixture,'pal');target=e.with_name(e.name.replace('-display-timing-pal','-geos-body-style-native'+('-control'if control else'-candidate')));shutil.move(e,target);e=target
 for tag,data in [('long',timing.native.live.grid.native_text('**'+('Wim. '*170)+'end**\rTail.')),('wide',timing.native.live.grid.native_text('***'+('W'*200)+'***\rTail.')),('short',timing.native.live.grid.native_text('Plain **bold** tail.'))]:
  p=e/(tag+'.bin');p.write_bytes(data);r=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(p),'bc'+tag+',s'],capture_output=True,text=True);assert not r.returncode;assert D81Image((e/'working.d81').read_bytes()).read(('bc'+tag).upper().encode(),kind=1).data==data
 shutil.copy2(e/'working.d81',e/'initial-fixtures.d81');return e

def scenario(e):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.measurement_warp=False;n.boot();n.open('open_diverse',b'DIVERSE');n.typed('enter_geos','mode hires');n.typed('top_diverse','top')
 n.measure('diverse-full',timing.native.live.grid.fixture(),3,full=True,category='forcedfresh-TOP0')
 for tag in('long','wide','short'):
  n.open('open_'+tag,('bc'+tag).upper().encode());data=(e/(tag+'.bin')).read_bytes();n.typed('top_'+tag,'top');n.measure(tag+'-full',data,3,full=True,category='forcedfresh-retained-body-cache')
 return n

def run(base,control=False):
 e=prepare(base,control);n=scenario(e);plan=n.plan();(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n');print('PREPARED',n.out,flush=True)
 stop=threading.Event()
 def watch():
  while not stop.wait(.1):
   p=subprocess.run(['ps','-axo','pid=,ppid=,command='],capture_output=True,text=True)
   for row in p.stdout.splitlines():
    if '/x64sc 'in row and '-binarymonitoraddress 127.0.0.1:8300'in row and str(e/'working.d81')in row:
     pid,parent,cmd=row.strip().split(None,2);(e/'owned-process.json').write_text(json.dumps(dict(pid=int(pid),parent=int(parent),command=cmd,binary_port=8300,text_port=8400,kill_stale=False),indent=2)+'\n');return
 thread=threading.Thread(target=watch,daemon=True);thread.start()
 with zipfile.ZipFile(e/'candidate-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for p in(ROOT/'src/render/geos/body-style-cache-candidate').iterdir():
   if p.is_file():z.write(p,str(p.relative_to(ROOT)))
 with zipfile.ZipFile(e/'body-verifier.zip','w',zipfile.ZIP_DEFLATED)as z:
  for p in[Path(__file__),ROOT/'tests/test_display_timing_vice.py',ROOT/'tests/geos_packet.py',ROOT/'tools/geos_preview_model.py',ROOT/'tests/test_geos_semantic_editor.py']:z.write(p,str(p.relative_to(ROOT)))
 try:
  project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;p=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(p.stdout+p.stderr);assert not p.returncode
  vice_plan.run_plan(plan,n.out);result=timing.evaluate(n);assert (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes(),'readonly disk changed'
  owned=json.loads((e/'owned-process.json').read_text());gone=subprocess.run(['ps','-p',str(owned['pid']),'-o','command='],capture_output=True,text=True);assert gone.returncode!=0,('ownedVICEstillrunning',gone.stdout)
  (e/'closure.json').write_text(json.dumps(dict(status='passed',owned_process_closed=True,ports=[8300,8400],scope='NormalPAL measured intervals withIRQ/VIC. Public-entry PC/SP stopwatch seam is explicit; initialOpen and runtime render are real. Source/assets/shim/cold/stack/nativeVICpixels exact; not wholeREUimmutability or physicalkey proof.'),indent=2)+'\n');return e
 finally:stop.set();thread.join(timeout=2)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--base',type=Path,default=candidate.BASE);p.add_argument('--control',action='store_true');a=p.parse_args();assert a.run;print('DONE',run(a.base.resolve(),a.control),flush=True)
