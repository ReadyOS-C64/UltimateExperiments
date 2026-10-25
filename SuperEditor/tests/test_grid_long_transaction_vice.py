"""Private SP2 long-paragraph actualnative PAL gate; owned8100/text8200."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib,shutil,subprocess,zipfile,threading,binascii
import test_grid_prose_authority_vice as previous
from test_fold_retention_vice import Captured
from supermark_model import blocks
import vice_plan
ROOT=previous.ROOT;profile=previous.profile;timing=previous.timing
CPU=ROOT/'build/grid-long-transaction-extended/20261025T200745478455Z/fixture'
DOC=timing.native.live.grid.native_text(':::basic\r10 PRINT 1\r:::\rAlpha '+('word '*100)+'ends.\rTail.')
def scenario(e):
 n=profile.Plan(e,json.load(open(e/'editor-report.json')),1,0);n.cost_profile=True;n.boot();n.open('open_long',b'LONG');data=DOC;at=data.index(timing.native.live.grid.native_text('Alpha'))+132
 for mode,width in((1,60),(2,80)):
  group='long-m'+str(mode);n.mode_to(mode);n.typed(group+'_goto','goto 4');n.send(group+'_column',b'\x1d'*132);n.memory(group+'_caret','se_hot_caret',at,3);caret=at
  for i,key in enumerate((81,82,20,20)):
   if key==20:caret-=1;data=data[:caret]+data[caret+1:]
   else:data=data[:caret]+bytes((key,))+data[caret:];caret+=1
   ident=group+'-edit'+str(i);n.measure(ident,data,mode,key=key);n.measurements[-1]['group']=group;n.memory(ident+'_long',0x89ff,2);n.memory(ident+'_pending','se_hot_pending',1)
  assert data==DOC
 return n

def extra(n):
 reus=timing.native.live.grid.reu_images(n.out/'run');prior={};rows=[];s=n.s
 for item in n.measurements:
  ident=item['id'];ram=(n.out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(n.out/'captures'/(ident+'-colors.bin')).read_bytes();f=Captured(s,ram,colors,n.e);reu=reus[ident];h=f.get('se_gc_handle',1);bank=ram[s['se_reu_map']+h];assert bank and ram[s['se_reu_logical_owner']+h]==254 and ram[s['se_reu_physical_owner']+bank]==254;start=bank*65536;cert=reu[start+0x1600:start+0x1680];assert cert[:4]==b'SP\2\xa5'and binascii.crc_hqx(cert[:126],65535)==int.from_bytes(cert[126:],'little');assert cert[4:37]==f.read(s['se_st_descriptor'],33)and cert[37:39]==f.read(s['se_doc_epoch'],2)and cert[39:41]==f.read(s['se_st_generation'],2);anchors=f.read(s['se_v_rows'],66)+f.read(s['se_v_bottom'],3);assert cert[42:111]==anchors
  data=bytes.fromhex(item['source']);events=blocks(data);expected=0
  for i in range(22):
   p=int.from_bytes(anchors[i*3:i*3+3],'little');q=next((q for q in events if q['start']<=p<q['end']),None)
   if q and q['kind']==0:
    line=data[q['start']:q['end']]
    if 65<=line[0]&127<=90 and not any(v in line for v in b'*@\\'):expected|=1<<i
  assert int.from_bytes(cert[111:114],'little')==expected,(ident,'wholelogicalprose authority')
  canonical=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],z)for k,z in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)])
  group=item['group']
  if group in prior:
   old,key=prior[group];assert key==canonical,(ident,'source/history exactpendinggroup');allowed=bytearray(old)
   for a,z in[(0,22*240),(0x1500,0x1680)]:allowed[start+a:start+z]=reu[start+a:start+z]
   assert bytes(allowed)==reu,(ident,'whole16MiB outsideownedinputs/NC/SP2')
  prior[group]=(reu,canonical);rows.append(dict(id=ident,FE=bank,SP2_crc=cert[126:].hex()))
 (n.out/'SP2-guards.json').write_text(json.dumps(dict(status='passed',cases=rows,whole16MiB_pairs=len(rows)-len(prior)),indent=2)+'\n')

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=CPU);p.add_argument('--run',action='store_true');a=p.parse_args();out=ROOT/'build/grid-long-native'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);frozen=previous.package(out,a.fixture);e=timing.freeze(frozen,'long-prose-pal');q=e/'long.bin';q.write_bytes(DOC);r=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(q),'long,s'],capture_output=True,text=True);assert not r.returncode;n=scenario(e);plan=n.plan();(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
 with zipfile.ZipFile(e/'SP2-verifier.zip','w',zipfile.ZIP_DEFLATED)as z:
  for directory in('tests','tools'):
   for q in(ROOT/directory).glob('*.py'):z.write(q,q.relative_to(ROOT))
 with zipfile.ZipFile(e/'SP2-private-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for q in(ROOT/'src/render/grid/long-prose-candidate').glob('*'):
   if q.is_file():z.write(q,q.relative_to(ROOT))
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
  project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode;previous.capacity.run_owned_plan(plan,n.out,timeout=1200);result=timing.evaluate(n);extra(n);print([(q['id'],q['first_publish_cycles'],q['emulated_cycles'],q['counter_deltas']['se_overlay_loads'])for q in result['measurements']],flush=True)
 finally:
  stop.set();t.join(timeout=2)
  if(e/'owned-process.json').exists():
   q=json.load(open(e/'owned-process.json'));ps=subprocess.run(['ps','-p',str(q['PID']),'-o','pid=,comm='],capture_output=True,text=True);assert not ps.stdout.strip();q['closed']=True;(e/'closure.json').write_text(json.dumps(q,indent=2)+'\n')
if __name__=='__main__':main()
