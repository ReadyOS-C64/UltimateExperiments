"""Current immutable32case PAL/NTSC native timings, owned8100/text8200.

Only wraps the original scenario/evaluator. No product/substituted image changes.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess,threading,time,zipfile
import test_display_timing_vice as timing
import test_reu_capacity_vice as capacity
from png_pixels import read_png
import vice_plan
ROOT=timing.ROOT
class Plan(timing.Plan):
 def measure(self,ident,data,mode,**kw):
  super().measure(ident,data,mode,**kw)
  if kw.get('full')and mode==3 and kw.get('ui',0)==0:
   # Original pre-cache seam cleared gc_valid, which is not consulted by
   # sourceGEOS page/caret reuse. Refuse all derived source-page reuse only.
   with zipfile.ZipFile(self.e/'product-sources.zip')as z:
    caret=z.read('src/render/geos/caret-cache.inc').decode()
    edit=z.read('src/render/geos/edit-certificate.inc').decode()
   assert 'GCC_STATE=$CF90' in caret and 'GCC_VALID=GCC_STATE' in caret
   assert 'GEC_RECORD=$CFE8' in edit and 'GEC_VALID=GEC_RECORD' in edit
   assert self.s['se_gc_width']+1==self.s['se_gc_valid']
   proof=dict(status='passed',source='immutable product-sources.zip',GCC_VALID=0xCF90,GEC_VALID=0xCFE8,se_gc_width=self.s['se_gc_width'],scope='Three derived validity bytes only; no cache payload/source/provider/REU mutation. Before-RAM snapshot retained by originalmeasure.')
   (self.e/'forced-full-contract.json').write_text(json.dumps(proof,indent=2)+'\n')
   path=self.out/(ident+'_timed_coherent.mon');text=path.read_text()
   needle='logname "'+str(self.out/('stopwatch-'+ident+'.log'))+'"'
   assert text.count(needle)==1
   reset=f'> {self.s["se_gc_width"]:04x} 00\n> cf90 00\n> cfe8 00\n'
   path.write_text(text.replace(needle,reset+needle))
   self.measurements[-1]['forced_full_invalidation']=['se_r_valid','se_gc_valid[3]','se_gc_width','GCC_VALID_CF90','GEC_VALID_CFE8']
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8100;p['global_defaults']['monitor_port_span']=1
  assert not p['global_defaults'].get('kill_stale',False)
  return p

def crop(e,item,result):
 w,h,pixels=read_png(e/'timing'/('native-'+item['id']+'.png'));x,y=result['native_viewport']
 return bytes(v for yy in range(200)for xx in range(320)for v in pixels[(y+yy)*w+x+xx])

def compare(e,reference,filename):
 a=json.loads((e/'timing/result.json').read_text());b=json.loads((reference/'timing/result.json').read_text());old={v['id']:v for v in b['measurements']};checks=[]
 for x in a['measurements']:
  y=old[x['id']];assert x['source']==y['source'],(x['id'],'sourcebound reference')
  actual=crop(e,x,a);prior=crop(reference,y,b)
  checks.append(dict(id=x['id'],same_source=True,exact_pixels=actual==prior,pixels=64000,actual_crop_sha256=hashlib.sha256(actual).hexdigest(),reference_crop_sha256=hashlib.sha256(prior).hexdigest()))
 r=dict(reference=str(reference),checks=checks,exact_count=sum(v['exact_pixels']for v in checks),count=len(checks),scope='Source-bound exact320x200nativepixel comparison; nonmatches require direct visual review, never waive original independent raster oracle.')
 (e/filename).write_text(json.dumps(r,indent=2)+'\n');return r

def execute(fixture,label):
 timing.Plan=Plan;e=timing.freeze(fixture,label);n=timing.scenario(e,1 if label=='pal'else 2,0 if label=='pal'else 3,focus='all',cost_profile=True);p=n.plan();assert len(n.measurements)==32
 (n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
 with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in('tests','tools'):
   for path in sorted((ROOT/folder).glob('*.py')):z.write(path,path.relative_to(ROOT))
 project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
 r=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(r.stdout+r.stderr);assert not r.returncode
 stopped=threading.Event();owned=[]
 def observe():
  while not stopped.wait(.1):
   ps=subprocess.run(['ps','-axo','pid=,ppid=,command='],capture_output=True,text=True)
   for line in ps.stdout.splitlines():
    if '/x64sc 'in line and '-binarymonitoraddress 127.0.0.1:8100'in line and str(e/'working.d81')in line:
     f=line.strip().split(None,2);v=dict(PID=int(f[0]),parent=int(f[1]),command=f[2],binary_port=8100,text_port=8200,kill_stale=False,match='ExactprivateworkingD81 AND binarymonitor8100');owned.append(v);(e/'owned-process.json').write_text(json.dumps(v,indent=2)+'\n');return
 watch=threading.Thread(target=observe,daemon=True);watch.start();print('NATIVE',label,e,'32captures',len(n.steps),'steps',flush=True)
 try:capacity.run_owned_plan(p,n.out,timeout=1800)
 finally:stopped.set();watch.join(timeout=2)
 assert owned,'actual ownedPID observed'
 ps=subprocess.run(['ps','-p',str(owned[0]['PID']),'-o','pid=,command='],capture_output=True,text=True);ports=subprocess.run(['lsof','-nP','-iTCP:8100','-iTCP:8200'],capture_output=True,text=True)
 closure=dict(status='passed'if not ps.stdout.strip()and not ports.stdout.strip()else'failed',PID=owned[0]['PID'],process=ps.stdout,ports=ports.stdout,method='normal.NET --close-vice; readonlyps/lsofafterterminal');(e/'process-closure.json').write_text(json.dumps(closure,indent=2)+'\n');assert closure['status']=='passed',closure
 r=timing.evaluate(n);assert (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes(),'readonlytimingdiskunchanged'
 summary=[]
 for item in r['measurements']:
  d=item['counter_deltas'];summary.append(dict(id=item['id'],category=item['category'],first_publish_cycles=item['first_publish_cycles'],quiescent_cycles=item['emulated_cycles'],peak_service_cycles=item['service_peak_cycles'],loads=d['se_overlay_loads'],calls=d['se_overlay_calls'],DMA_calls=d['se_reu_dma_calls'],DMA_bytes=d['se_reu_dma_bytes'],CRC_cycles=item['cost_profile']['crc_cycles']))
 (e/'timing-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('PASS',label,e,flush=True)
 return e

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--standard',choices=['pal','ntsc','both'],default='both');a=p.parse_args();results=[]
 for standard in('pal','ntsc'):
  if a.standard in(standard,'both'):results.append(execute(a.fixture.resolve(),standard))
 if len(results)==2:
  c=compare(results[1],results[0],'current-pal-ntsc-comparison.json');assert c['exact_count']==32,c
 print('ALLCURRENT32',*[str(e)for e in results],flush=True)
if __name__=='__main__':main()
