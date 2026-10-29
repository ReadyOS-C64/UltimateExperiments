"""Private SP1 actual C14/R14 + C33/R25 native qualification,8100/8200."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib,shutil,subprocess,zipfile,threading,binascii
import test_source_grid_typing_profile_vice as profile
import test_reu_capacity_vice as capacity
from test_fold_retention_vice import Captured
from supermark_model import blocks
import vice_plan
ROOT=profile.ROOT;timing=profile.timing
CPU=ROOT/'build/grid-prose-authority/20261025T185219156260Z/fixture'
NORMAL=timing.native.live.grid.native_text('# Heading\r:::basic\r10 PRINT "x"\r:::\r:::asm\rlda #1\r:::\r:::region Closed\rregion body\r:::end\rAlpha paragraph having ample room.\rTail.')
FAR=timing.native.live.grid.native_text(':::basic\r')+b'X'*65540+timing.native.live.grid.native_text('\r:::\r:::region Closed\rbody\r:::end\rAlpha paragraph having ample room.\rTail.')
def package(out,base):
 frozen=out/'fixture';shutil.copytree(base,frozen);identity=json.load(open(frozen/'freeze.json'))
 for name in ('styler','viewsource','geostail','grid'):
  p=frozen/'build/overlays'/(name+'.seo');r=subprocess.run(['c1541','-attach',str(frozen/'build/supereditor.d81'),'-delete',name,'-write',str(p),name+',s'],capture_output=True,text=True);(out/(name+'-disk.log')).write_text(r.stdout+r.stderr);assert not r.returncode
 identity['disk_sha256']=hashlib.sha256((frozen/'build/supereditor.d81').read_bytes()).hexdigest();(frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n');return frozen
def scenario(e):
 n=profile.Plan(e,json.load(open(e/'editor-report.json')),1,0);n.cost_profile=True;n.boot()
 for name,original in [('NORMAL',NORMAL),('FAR',FAR)]:
  n.open('open_'+name,name.encode());data=original;at=data.index(timing.native.live.grid.native_text('having'))+2
  for mode in(1,2):
   group=name+'-m'+str(mode);n.mode_to(mode);line=data[:at].count(b'\r')+1;col=at-data.rfind(b'\r',0,at)-1;n.typed(group+'_goto','goto '+str(line));n.send(group+'_column',b'\x1d'*col);n.memory(group+'_caret','se_hot_caret',at,3)
   caret=at
   for index,key in enumerate((81,82,20,20)):
    if key==20:caret-=1;data=data[:caret]+data[caret+1:]
    else:data=data[:caret]+bytes((key,))+data[caret:];caret+=1
    ident=group+'-edit'+str(index);n.measure(ident,data,mode,key=key);n.measurements[-1]['group']=group;n.measurements[-1]['typing']=True;n.memory(ident+'_typing',0x89ff,1);n.memory(ident+'_pending','se_hot_pending',1)
   assert data==original
   for ident,key in [('right',0x1d),('left',0x9d)]:
    tag=group+'-'+ident;n.measure(tag,data,mode,key=key);n.measurements[-1]['group']=group;n.measurements[-1]['typing']=False
 return n
def extra(n):
 images=timing.native.live.grid.reu_images(n.out/'run');previous={};rows=[];s=n.s
 for item in n.measurements:
  ident=item['id'];ram=(n.out/'captures'/(ident+'-ram.bin')).read_bytes();reu=images[ident];colors=(n.out/'captures'/(ident+'-colors.bin')).read_bytes();f=Captured(s,ram,colors,n.e);bank=ram[s['se_reu_map']+f.get('se_gc_handle',1)];assert bank and ram[s['se_reu_physical_owner']+bank]==0xfe;start=bank*65536;raw=reu[start+0x1600:start+0x1680]
  assert raw[:4]==b'SP\1\xa5'and binascii.crc_hqx(raw[:126],65535)==int.from_bytes(raw[126:],'little')
  assert raw[4:37]==f.read(s['se_st_descriptor'],33)and raw[37:39]==f.read(s['se_doc_epoch'],2)and raw[39:41]==f.read(s['se_st_generation'],2)
  anchors=f.read(s['se_v_rows'],66)+f.read(s['se_v_bottom'],3);assert raw[42:111]==anchors
  source=bytes.fromhex(item['source']);prose={b['start']for b in blocks(source)if b['kind']==0};expected=sum(1<<i for i in range(22)if int.from_bytes(anchors[i*3:i*3+3],'little')in prose);assert int.from_bytes(raw[111:114],'little')==expected
  canonical=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],z)for k,z in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)])
  group=item['group']
  if group in previous:
   old,oldcanonical=previous[group];assert canonical==oldcanonical,(ident,'canonical/history exactpendinggroup');target=bytearray(old);row=f.get('se_v_caret_row',1)
   for a,z in[(row*240,(row+1)*240),(0x1500,0x1600),(0x1600,0x1680)]:target[start+a:start+z]=reu[start+a:start+z]
   assert bytes(target)==reu,(ident,'whole16MiB onlydeclared row/NC/SP1 derivedwrites')
  previous[group]=(reu,canonical);rows.append(dict(id=ident,physical_FE=bank,SP1_crc=raw[126:].hex(),above64KiB=f.get('se_hot_caret')>65535))
 (n.out/'SP1-guards.json').write_text(json.dumps(dict(status='passed',cases=rows,paired16MiB_intervals=len(rows)-len(previous)),indent=2)+'\n');return rows
def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=CPU);p.add_argument('--run',action='store_true');a=p.parse_args();build=ROOT/'build/grid-prose-authority-native'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');build.mkdir(parents=True);frozen=package(build,a.fixture);e=timing.freeze(frozen,'prose-authority-pal')
 for name,data in [('normal',NORMAL),('far',FAR)]:
  q=e/(name+'.bin');q.write_bytes(data);r=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(q),name+',s'],capture_output=True,text=True);assert not r.returncode
 n=scenario(e);plan=n.plan();(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
 with zipfile.ZipFile(e/'SP1-verifier.zip','w',zipfile.ZIP_DEFLATED)as z:
  for directory in('tests','tools'):
   for q in(ROOT/directory).glob('*.py'):z.write(q,q.relative_to(ROOT))
 print('RUN',e,len(n.steps),'steps',flush=True)
 if not a.run:return
 stop=threading.Event()
 def watch():
  while not stop.wait(.05):
   q=subprocess.run(['ps','-axo','pid=,ppid=,command='],capture_output=True,text=True)
   for line in q.stdout.splitlines():
    if '/x64sc 'in line and str(e/'working.d81')in line:
     z=line.strip().split(None,2);(e/'owned-process.json').write_text(json.dumps(dict(PID=int(z[0]),command=z[2]),indent=2)+'\n');return
 t=threading.Thread(target=watch,daemon=True);t.start()
 try:
  project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode;capacity.run_owned_plan(plan,n.out,timeout=1200);result=timing.evaluate(n);extra(n);print([(q['id'],q['first_publish_cycles'],q['emulated_cycles'],q['counter_deltas']['se_overlay_loads'])for q in result['measurements']],flush=True)
 finally:
  stop.set();t.join(timeout=2)
  if(e/'owned-process.json').exists():
   q=json.load(open(e/'owned-process.json'));ps=subprocess.run(['ps','-p',str(q['PID']),'-o','pid=,comm='],capture_output=True,text=True);assert not ps.stdout.strip();q['closed']=True;(e/'closure.json').write_text(json.dumps(q,indent=2)+'\n')
if __name__=='__main__':main()
