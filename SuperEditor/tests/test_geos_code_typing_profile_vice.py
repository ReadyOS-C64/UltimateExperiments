"""Actual PAL native C6/R31 code typing profile on an explicit frozen product.

Private8300/text8400, real D81 File/Open/setup, existing IRQ-enabled stopwatch
public-input seam and full independent source/native-pixel evaluator. No make.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,zipfile
import test_geos_edit_profile as profile
import test_reu_capacity_vice as capacity
from d81_image import D81Image
import vice_plan
ROOT=profile.ROOT;timing=profile.timing
DEFAULT=ROOT/'build/geos-incremental-editor/20261025T104351424394Z/fixture'
DOC=timing.native.live.grid.native_text(
 'Plain intro.\r:::basic\r10 PRINT "HELLO":REM KEEP\r20 GOTO 10\r:::\r'
 ':::asm\rstart: lda #$2A ; comment\rnext: sta $D020\r:::\r'
 'Plain **bold words** and *italic*.\rFollowing row.\rTail.')

class Plan(profile.Plan):
 def boot(self):
  super().boot()
  # Read actual BASIC SYS startup stack before the stopwatch's explicit SP seam.
  # Breakpoints/logging only: no register, code, stack or input writes here.
  self.raw('natural_startup_idle',[
   'delete',f'break exec ${self.idle_pc:04x} if {self.condition(0)}','x','delete',
   f'logname "{self.out / "natural-startup-idle.log"}"','log on','registers','log off'])
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8300
  p['global_defaults']['monitor_port_span']=1
  p['global_defaults']['timeouts']['step_s']=120
  assert not p['global_defaults'].get('kill_stale',False)
  return p

def catalog_slot(e,slot,ident):
 frozen=json.loads((e/'freeze.json').read_text());names=frozen.get('names')or frozen['catalog']
 return next(i+1 for i,name in enumerate(names)if(e/(name+'.seo')).read_bytes()[5:7]==bytes((slot,ident)))

def scenario(e, standard=1, model=0):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),standard,model);n.cost_profile=True
 n.boot();n.open('open_classdoc',b'CLASSDOC');n.typed('mode_geos','mode hires')
 data=DOC
 def position(tag,at):
  line=data[:at].count(b'\r')+1;column=at-(data.rfind(b'\r',0,at)+1)
  n.typed(tag+'_goto',f'goto {line}')
  if column:n.send(tag+'_column',b'\x1d'*column)
  n.memory(tag+'_caret','se_hot_caret',at,3)
 for tag,at,key in [
  ('basic-string',DOC.index(timing.native.live.grid.native_text('HELLO'))+2,timing.native.live.grid.native_text('X')[0]),
  ('asm-comment',DOC.index(timing.native.live.grid.native_text('comment'))+3,timing.native.live.grid.native_text('i')[0]),
  ('basic-number',DOC.index(timing.native.live.grid.native_text('GOTO 10'))+6,ord('2'))]:
  position(tag,at)
  data=data[:at]+bytes([key])+data[at:]
  n.measure(tag+'-insert',data,3,key=key,category=tag+'-insert')
  n.memory(tag+'_insert_actual_R31',n.s['se_overlay_active'],catalog_slot(n.e,0,31))
  n.memory(tag+'_insert_stage_ready',0xcbd5,0x41)
  n.memory(tag+'_insert_C6_retained',n.s['se_overlay_active']+1,catalog_slot(n.e,1,6))
  n.memory(tag+'_insert_pending_preserved','se_hot_pending',1)
  data=data[:at]+data[at+1:]
  n.measure(tag+'-backspace',data,3,key=0x14,category=tag+'-backspace')
  n.memory(tag+'_delete_actual_R31',n.s['se_overlay_active'],catalog_slot(n.e,0,31))
  n.memory(tag+'_delete_stage_ready',0xcbd5,0x41)
  n.memory(tag+'_delete_C6_retained',n.s['se_overlay_active']+1,catalog_slot(n.e,1,6))
  n.memory(tag+'_delete_pending_preserved','se_hot_pending',1)
  assert data==DOC
 return n


def freeze(source):
 e=timing.native.freeze(source)
 target=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-code-typing-profile-native')
 target.parent.mkdir(exist_ok=True);shutil.move(e,target)
 shutil.copytree(ROOT/'build/geos-font-catalog',target/'genuine')
 (target/'classdoc.bin').write_bytes(DOC)
 p=subprocess.run(['c1541','-attach',str(target/'working.d81'),'-write',str(target/'classdoc.bin'),'classdoc,s'],capture_output=True,text=True)
 (target/'classdoc-package.log').write_text(p.stdout+p.stderr);assert not p.returncode
 assert D81Image((target/'working.d81').read_bytes()).read(b'CLASSDOC',kind=1).data==DOC
 shutil.copy2(target/'working.d81',target/'profile-initial.d81')
 return target


def extra_guards(n):
 s=n.s;images=timing.native.live.grid.reu_images(n.out/'run');states={};hashes={};intervals=0
 for i,item in enumerate(n.measurements):
  ident=item['id'];ram=(n.out/'captures'/(ident+'-ram.bin')).read_bytes()
  assert ram[s['se_overlay_active']]==catalog_slot(n.e,0,31) and ram[s['se_overlay_active']+1]==catalog_slot(n.e,1,6) and ram[0xcbd5]==0x41 and ram[0xcbd4]==0xff,(ident,'actualC6/R31/stagedlex')
  assert ram[0xcf90]==1 and not ram[0xcfe8] and not ram[0x9149] and not ram[s['se_f_owner']],(ident,'publication/owner')
  group=i//2
  state=ram[s['se_doc_roots']:s['se_doc_roots']+512]+b''.join(ram[s[k]:s[k]+w]for k,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)])
  assert state==states.setdefault(group,state),(ident,'pending canonical/history changed')
  reu=images[ident];assert len(reu)==16*1024*1024
  handle=ram[s['se_gc_handle']];bank=ram[s['se_reu_map']+handle]
  assert handle and bank and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+bank]==0xfe
  masked=bytearray(reu)
  for a,b in [(0,64),(0x200,0xb200),(0xb200,0xd528)]:masked[bank*65536+a:bank*65536+b]=bytes(b-a)
  digest=hashlib.sha256(masked).hexdigest()
  if group in hashes:intervals+=1
  assert digest==hashes.setdefault(group,digest),(ident,'whole16MiB outside declaredFE')
 result=dict(status='passed',whole16MiB_intervals=intervals,canonical_history_groups=3,guard='Exact canonical/history and all16MiB except authenticatedFEheader64,22slots0200..B1FF and optionalbodyB200..D527 ; R28backup/fonttail/foreignbank bytes remain exact; pending edits alter onlyhotRAM plusdeclaredderivedcache.')
 (n.out/'guard-result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path,default=DEFAULT);p.add_argument('--verify',type=Path);p.add_argument('--standard',choices=['pal','ntsc'],default='pal');a=p.parse_args()
 if not(a.run or a.verify):print('Prepared frozen46 PAL code typing profile; own8300/text8400.');return
 if a.verify:
  e=a.verify.resolve();n=Plan.__new__(Plan);n.e=e;n.out=e/'timing'
  saved=json.loads((n.out/'result.json').read_text());n.s=json.loads((e/'editor-report.json').read_text())['symbols']
  n.standard=saved['standard'];n.model=saved['vicii_model'];n.cold_end=saved['cold_end_exclusive']
  n.cost_profile=True;n.cost_points=saved['cost_trace_points'];n.canary=bytes((i*73+29)&255 for i in range(1024))
  n.measurements=json.loads((n.out/'measurements.json').read_text())
  prg=(e/'editor.prg').read_bytes();load=int.from_bytes(prg[:2],'little');target=n.s['se_editor_service']
  needle=bytes((0x20,target&255,target>>8));sites=[load+i-2+3 for i in range(2,len(prg)-2)if prg[i:i+3]==needle];assert len(sites)==1;n.service_return=sites[0]
  target=n.s['se_e_draw_sequence'];needle=bytes((0xee,target&255,target>>8));sites=[load+i-2 for i in range(2,len(prg)-2)if prg[i:i+3]==needle];assert len(sites)==1;n.publish_pc=sites[0]
 else:
  e=freeze(a.fixture.resolve());standard,model=(1,0) if a.standard=='pal' else (2,3);n=scenario(e,standard,model);plan=n.plan()
  (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
  with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
   for folder in ('tests','tools'):
    for path in sorted((ROOT/folder).glob('*.py')):z.write(path,path.relative_to(ROOT))
  project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
  result=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120)
  (n.out/'dotnet-build.log').write_text(result.stdout+result.stderr);assert not result.returncode
  print('NATIVE',e,'steps',len(n.steps),'IRQ',n.keys,'captures',len(n.measurements),flush=True)
  capacity.run_owned_plan(plan,n.out,timeout=900)
 result=timing.evaluate(n);summary=profile.summary(n,result);summary['extra_guards']=extra_guards(n)
 for row in summary['cases']:
  cost=next(x for x in result['measurements']if x['id']==row['id'])['cost_profile']
  row['incremental']=sum(x['payload_self']for x in cost['groups']if(x['slot'],x['id'])==(0,28))
  row['direct_typing']=sum(x['payload_self']for x in cost['groups']if(x['slot'],x['id'])==(0,31))
 assert(e/'working.d81').read_bytes()==(e/'profile-initial.d81').read_bytes(),'read-onlyD81 changed'
 (n.out/'code-typing-profile.json').write_text(json.dumps(summary,indent=2)+'\n')
 print('PASS',e,flush=True)
 for item in summary['cases']:print(json.dumps(item),flush=True)
if __name__=='__main__':main()
