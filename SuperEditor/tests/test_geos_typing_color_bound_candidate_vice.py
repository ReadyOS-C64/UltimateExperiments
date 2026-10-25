"""Private released C6/R30/C32 actual native PAL qualification,7900/text8000.

Public File/Open and IRQ setup; measured public-input PC/SP seam remains
explicit. Atomic private image substitutions only, never canonical/sharedmake.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,zipfile,threading,time
import test_geos_style_profile_vice as style
import test_geos_edit_profile as profile
import test_reu_capacity_vice as capacity
from d81_image import D81Image
import vice_plan
ROOT=profile.ROOT;timing=profile.timing
RELEASE=ROOT/'agentsworking/evidence/M8/20261025T164809216737Z-typing-two-color-private'
FILES=[
 ('white','Alpha interiorwords omega.\rSecond source line.\rTail.','interiorwords',2,ord('X'),True),
 ('natural','# Heading\rPlain row having ample room\rTail.','having',2,ord('X'),True),
 ('pangram','# Heading\rA quick brown fox jumps over the lazy dog.\rTail.','brown',2,ord('X'),True),
 ('alpha','# Heading\rAlpha interiorwords omega.\rTail.','interiorwords',2,ord('X'),True),
 ('italic','# Heading\rAlpha *interiorwords* omega.\rTail.','interiorwords',2,ord('X'),True),
 ('winner','# .\rjjj\rTail.','jjj',1,ord('X'),False),
 ('LSN190','Intro.\rjjj\r- .\rTail.','jjj',2,0x14,False)]
STOP=threading.Event();WATCH=None
class Plan(style.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=7900;p['global_defaults']['monitor_port_span']=1
  assert not p['global_defaults'].get('kill_stale',False);return p

def freeze(source):
 # Verify exact released pair; the immutable baseline ZIP remains labelled as
 # baseline, with independent privatecandidate provenance copied alongside.
 for name,part in [('window','window'),('gtype','worker'),('type','stage')]:assert(source/'build/overlays'/(name+'.seo')).read_bytes()==(RELEASE/'release-build'/(part+'.seo')).read_bytes(),name
 e=timing.native.freeze(source);target=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-typing-two-color-native');shutil.move(e,target);shutil.copytree(ROOT/'build/geos-font-catalog',target/'genuine');shutil.copy2(source/'candidate-sources.zip',target/'candidate-sources.zip');shutil.copy2(source/'freeze.json',target/'private-fixture.json');logs=[]
 for tag,text,_,_,_,_ in FILES:
  p=target/(tag+'.bin');data=timing.native.live.grid.native_text(text);p.write_bytes(data);q=subprocess.run(['c1541','-attach',str(target/'working.d81'),'-write',str(p),tag.lower()+',s'],capture_output=True,text=True,errors="replace");logs.append(q.stdout+q.stderr);assert not q.returncode;assert D81Image((target/'working.d81').read_bytes()).read(tag.upper().encode(),kind=1).data==data
 (target/'fixtures-package.log').write_text('\n'.join(logs));shutil.copy2(target/'working.d81',target/'profile-initial.d81')
 global WATCH
 def observe():
  while not STOP.wait(.1):
   q=subprocess.run(['ps','-axo','pid=,ppid=,command='],capture_output=True,text=True)
   for line in q.stdout.splitlines():
    if '/x64sc 'in line and '-binarymonitoraddress 127.0.0.1:7900'in line and str(target/'working.d81')in line:
     p=line.strip().split(None,2);(target/'owned-process.json').write_text(json.dumps(dict(PID=int(p[0]),parent=int(p[1]),command=p[2],binary_port=7900,text_port=8000,kill_stale=False),indent=2)+'\n');return
 WATCH=threading.Thread(target=observe,daemon=True);WATCH.start();return target

def scenario(e):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.cost_profile=True;n.boot()
 for i,(tag,text,word,delta,key,want) in enumerate(FILES):
  if i:n.send(tag+'_make_dirty_before_open',b'X')
  n.open(tag+'_open',tag.upper().encode(),choice='D'if i else None)
  if not i:n.typed('enter_geos','mode hires')
  data=timing.native.live.grid.native_text(text);at=data.index(timing.native.live.grid.native_text(word))+delta
  line=data[:at].count(b'\r')+1;column=at-(data.rfind(b'\r',0,at)+1)
  n.typed(tag+'_goto',f'goto {line}')
  if column:n.send(tag+'_column',b'\x1d'*column)
  n.memory(tag+'_caret','se_hot_caret',at,3)
  for serial,k in enumerate([key,timing.native.live.grid.native_text('j')[0]if key==0x14 else 0x14]):
   data=data[:at-1]+data[at:]if k==0x14 else data[:at]+bytes([k])+data[at:]
   at+=-1 if k==0x14 else 1
   ident=tag+('-first'if not serial else'-second');n.measure(ident,data,3,key=k,category=ident);n.measurements[-1].update(expected_direct=want,guard_group=i,source_case=tag)
   if want:
    n.memory(ident+'_R30','se_overlay_active',style.catalog_slot(e,0,30));n.memory(ident+'_C6',n.s['se_overlay_active']+1,style.catalog_slot(e,1,6));n.memory(ident+'_stage',0xcbd5,0x42)
   n.memory(ident+'_pending','se_hot_pending',1)
  assert data==timing.native.live.grid.native_text(text)
 # Separate canonical undo/redo: no pending-pair invariant is claimed here.
 n.send('undo_prepare_dirty',b'X');n.open('undo_open',b'NATURAL',choice='D');data=timing.native.live.grid.native_text(FILES[1][1]);at=data.index(timing.native.live.grid.native_text('having'))+2
 n.typed('undo_goto','goto 2');n.send('undo_column',b'\x1d'*(at-data.index(b'\r')-1));n.memory('undo_caret','se_hot_caret',at,3)
 edited=data[:at]+b'X'+data[at:]
 for ident,source,key,want in [('undo-seed',edited,ord('X'),True),('undo',data,0x1a,None),('redo',edited,0x19,None)]:
  n.measure(ident,source,3,key=key,category=ident);n.measurements[-1].update(expected_direct=want,guard_group=None,source_case='undo-redo')
 return n

def guards(n):
 s=n.s;images=timing.native.live.grid.reu_images(n.out/'run');states={};hashes={};intervals=0;cases=[]
 for item in n.measurements:
  ident=item['id'];ram=(n.out/'captures'/(ident+'-ram.bin')).read_bytes();active=ram[s['se_overlay_active']];direct=bool(active)and(n.e/(json.loads((n.e/'freeze.json').read_text())['catalog'][active-1]+'.seo')).read_bytes()[6]==30;want=item['expected_direct']
  if want is not None:assert direct==want,(ident,'actualpath',direct,want)
  if direct:assert ram[0x8bcc]==int(item['source_case']!='white'),(ident,'CRC-certifiedconditionalmode',ram[0x8bcc])
  if direct:assert ram[s['se_overlay_active']+1]==style.catalog_slot(n.e,1,6)and ram[0xcbd5]==0x42 and ram[0xcbd4]==0xff and ram[0xcf90]==1 and not ram[0x9149]and not ram[0xcfe8],(ident,'actualstagedpublication')
  assert not ram[s['se_f_owner']]and not ram[s['se_doc_read_locks']]
  group=item['guard_group']
  if group is not None:
   state=ram[s['se_doc_roots']:s['se_doc_roots']+512]+b''.join(ram[s[k]:s[k]+w]for k,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)])
   assert state==states.setdefault(group,state),(ident,'canonical/historypending')
   reu=images[ident];assert len(reu)==16*1024*1024;h=ram[s['se_gc_handle']];bank=ram[s['se_reu_map']+h];assert h and bank and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+bank]==0xfe;masked=bytearray(reu)
   spans=[(0,64),(0x200,0xb200),(0xb200,0xd528)]
   if not direct:spans.append((0xd528,0xe568)) #existingR28fallback backup authority
   # Both members of a fallbackpair must mask the same declaredFE spans.
   if not item['expected_direct']:spans=[(0,64),(0x200,0xe568)]
   for a,b in spans:masked[bank*65536+a:bank*65536+b]=bytes(b-a)
   digest=hashlib.sha256(masked).hexdigest()
   if group in hashes:intervals+=1
   assert digest==hashes.setdefault(group,digest),(ident,'whole16MiBoutsideFE')
  cases.append(dict(id=ident,direct=direct,group=group,owner=ram[s['se_f_owner']]))
 result=dict(status='passed',cases=cases,whole16MiB_paired_intervals=intervals,canonical_history_pairs=len(states),scope='Private sealed trio; everypaired pending edit preserves canonical/history and all16MiB outside authenticatedFEpage/body spans; fallbackpairs additionally allow R28backup. Native evaluator separately verifies wholecatalog/payload/source/shim/lowerstack/allVICpixels.');(n.out/'guard-result.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--run',action='store_true');p.add_argument('--prepare',action='store_true');a=p.parse_args();e=freeze(a.fixture.resolve());n=scenario(e);plan=n.plan();(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
 with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for d in ['tests','tools']:
   for q in(ROOT/d).glob('*.py'):z.write(q,q.relative_to(ROOT))
 print('PREPARED',e,'steps',len(n.steps),'captures',len(n.measurements),flush=True)
 if not a.run:STOP.set();return
 try:
  project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;q=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(q.stdout+q.stderr);assert not q.returncode
  capacity.run_owned_plan(plan,n.out,timeout=1800);result=timing.evaluate(n);summary=profile.summary(n,result);summary['extra_guards']=guards(n)
  assert(e/'working.d81').read_bytes()==(e/'profile-initial.d81').read_bytes(),'read-onlydiskchanged';(n.out/'two-color-profile.json').write_text(json.dumps(summary,indent=2)+'\n');print('PASS',e,flush=True)
  for row in summary['cases']:print(json.dumps(row),flush=True)
 finally:
  STOP.set()
  if WATCH:WATCH.join(timeout=2)
if __name__=='__main__':main()
