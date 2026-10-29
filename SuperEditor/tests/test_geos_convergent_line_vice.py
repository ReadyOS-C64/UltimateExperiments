"""Private actual complete-line convergence PAL A/B; own8500/text8600 only."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,shutil,socket,subprocess,zipfile
import test_geos_heading_body_candidate_vice as previous
from test_fold_retention_vice import Captured
from d81_image import D81Image
import vice_plan
ROOT=previous.ROOT;timing=previous.timing
BASE=ROOT/'build/geos-incremental-editor/20261025T203233990688Z/fixture'
CANDIDATE=ROOT/'build/geos-convergent-line-regression/20261025T205221679603Z/fixture'
Plan=previous.Plan
native_text=timing.native.live.grid.native_text
DOCS={'INLINE':native_text('Alpha *bold* words.\rSecond line.\rThird row.\rTail.'),'REGION':native_text(':::region A\rAlpha *bold* words.\r:::end\rTail.'),'CARRY':native_text(':::basic\r10 PRINT 1\r:::\rTail.'),'WRAP':native_text('m'*39+'i\rNext.\rTail.')}

def freeze(source,variant):
 e=timing.native.freeze(source);target=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-convergent-line-'+variant+'-native');shutil.move(e,target);e=target;previous.io.unpack_catalog(e)
 ident=json.loads((e/'freeze.json').read_text());assert len(ident['catalog'])==48
 expected={'rangeio':4028,'geospage':3741,'geosdelta':3749}if variant=='candidate'else{'rangeio':2817,'geospage':4073,'geosdelta':4095}
 assert all(len((e/(n+'.seo')).read_bytes())-36==size for n,size in expected.items())
 for name,data in DOCS.items():
  p=e/(name.lower()+'.bin');p.write_bytes(data);r=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(p),name.lower()+',s'],capture_output=True,text=True);(e/(name.lower()+'-package.log')).write_text(r.stdout+r.stderr);assert not r.returncode;assert D81Image((e/'working.d81').read_bytes()).read(name.encode(),kind=1).data==data
 shutil.copy2(e/'working.d81',e/'profile-initial.d81');return e

def scenario(e,variant):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.cost_profile=True;n.measurement_warp=False;n.boot();n.calibrate();n.open('open_diverse',b'DIVERSE');n.typed('enter_geos','mode hires');data=timing.native.live.grid.fixture()
 def position(tag,at):
  n.typed(tag+'_top','top');line=data[:at].count(b'\r')+1;column=at-(data.rfind(b'\r',0,at)+1);n.typed(tag+'_goto',f'goto {line}')
  if column:n.send(tag+'_column',b'\x1d'*column)
  n.memory(tag+'_caret','se_hot_caret',at,3);n.expected_caret=at
 def measure(tag,key,group,eligible):
  nonlocal data
  at=n.expected_caret
  if key==0x14:data=data[:at-1]+data[at:];n.expected_caret-=1
  else:data=data[:at]+bytes([key])+data[at:];n.expected_caret+=1
  n.measure(tag,data,3,key=key,category=group);want=2 if variant=='candidate'and eligible else 0;n.measurements[-1].update(group=group,expected_fast=want,expected_caret=n.expected_caret)
  n.memory(tag+'_actual_fast',0x9148,want);n.memory(tag+'_actual_caret','se_hot_caret',n.expected_caret,3);n.memory(tag+'_pending','se_hot_pending',1)
  if want:n.memory(tag+'_class',0x9177,5)
 def pair(tag,at,key,eligible=True,delete_first=False):
  original=data;position(tag,at);measure(tag+'-edit',0x14 if delete_first else key,tag,eligible);measure(tag+'-restore',key if delete_first else 0x14,tag,eligible);assert data==original
 pair('diverse-heading-inline',2+len(native_text('Super')),ord('*'))
 for name,tag,at,key,eligible,delete_first in [('INLINE','inline-activation',6,ord('*'),True,False),('REGION','region-carry',len(native_text(':::region A\r'))+6,ord('*'),True,False),('CARRY','negative-carry',1,ord(':'),False,True),('WRAP','negative-wrap',20,native_text('m')[0],False,False)]:
  n.send(tag+'_dirty_for_open',native_text('Q'));n.open(tag+'_open',name.encode(),choice='D');data=DOCS[name];pair(tag,at,key,eligible,delete_first)
 return n

def extra(n,result):
 images=timing.native.live.grid.reu_images(n.out/'run');s=n.s;pack=(n.e/'font-pack.bin').read_bytes();states={};hashes={};intervals=0;groups=[];fonts={name:(n.e/name).read_bytes()for name in timing.native.live.geos.GEOS_FONTS+('native8.bin',)}
 for item,measured in zip(n.measurements,result['measurements']):
  ident=item['id'];ram=(n.out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(n.out/'captures'/(ident+'-colors.bin')).read_bytes();f=Captured(s,ram,colors,n.e);f.colored=True;reu=images[ident];assert len(reu)==16777216 and f.get('se_reu_banks',2)==256
  assert ram[0x9148]==item['expected_fast']and f.get('se_hot_caret')==item['expected_caret']and f.get('se_hot_pending',1)==1,(ident,'path/caret/pending')
  if item['expected_fast']:assert ram[0x9177]==5
  assert not ram[0x9149]and not any(f.get(k,1)for k in ['se_e_error','se_f_owner','se_doc_read_locks','se_fs_owned','se_n_owned','se_doc_busy'])and ram[0x98]==0
  assert f.read(0xcb80,64)==(n.e/'editor-defaults.bin').read_bytes()
  for i,h in enumerate(f.read(0xcbc1,2)):
   bank=ram[s['se_reu_map']+h];assert h and bank and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+bank]==0xfd;part=pack[i*65536:(i+1)*65536];assert reu[bank*65536:bank*65536+len(part)]==part
  state=ram[s['se_doc_roots']:s['se_doc_roots']+512]+b''.join(ram[s[k]:s[k]+w]for k,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),('se_sel_mark',1),('se_clip_token',5),('se_clip_length',3)])
  group=item['group'];assert state==states.setdefault(group,state),(ident,'pairedcanonical/history')
  handle=ram[s['se_gc_handle']];bank=ram[s['se_reu_map']+handle];assert handle and bank and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+bank]==0xfe
  masked=bytearray(reu);spans=[(0,64),(0x600,0x680),(0xb200,0xd568),(0xe568,0xea88)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]
  if len((n.e/'rangeio.seo').read_bytes())-36==4028:spans += [(0x700+i*0x800,0x740+i*0x800)for i in range(22)]
  for a,b in spans:masked[bank*65536+a:bank*65536+b]=bytes(b-a)
  digest=hashlib.sha256(masked).hexdigest();intervals+=int(group in hashes);assert digest==hashes.setdefault(group,digest),(ident,'full16MiBoutsideexactspans')
  data=bytes.fromhex(item['source']);_,_,rows,_=timing.semantic.expected(f,data,fonts);cache=reu[bank*65536:(bank+1)*65536];assert cache[0]==1 and cache[1]==len(rows)
  for i,row in enumerate(rows):
   p=cache[0x200+i*0x800:0x220+i*0x800];assert (int.from_bytes(p[:3],'little'),int.from_bytes(p[3:6],'little'),int.from_bytes(p[6:9],'little'),p[14],p[15])==(row.start,row.end,row.next,row.height,row.top),(ident,'allanchors',i)
  assert f.get('se_v_bottom')==rows[-1].next
  text=(n.out/('stopwatch-'+ident+'.log')).read_text(encoding='utf-8-sig');regs=re.findall(r'(?m)^\.;([0-9a-f]{4})\s+[0-9a-f]{2}\s+[0-9a-f]{2}\s+[0-9a-f]{2}\s+([0-9a-f]{2})\s+[0-9a-f]{2}\s+[0-9a-f]{2}\s+([01]{8})',text,re.I);assert len(regs)==2 and int(regs[0][0],16)==timing.PROBE and regs[0][1].lower()=='ff'and int(regs[0][2],2)==0x20;assert int(regs[-1][0],16)==n.idle_pc and regs[-1][1].lower()=='ff'and not int(regs[-1][2],2)&4
  groups.append(dict(id=ident,actual_fast=item['expected_fast'],caret=f.get('se_hot_caret'),rows=len(rows)))
 assert [int(v)for v in re.findall(r'Stopwatch:\s*(\d+)',(n.out/'calibration.log').read_text(encoding='utf-8-sig'),re.I)]==[16]
 assert(n.e/'working.d81').read_bytes()==(n.e/'profile-initial.d81').read_bytes()
 result=dict(status='passed',whole16MiB_paired_intervals=intervals,cases=groups,guard='OnlyFEheader64,liveABI3prefix/glyph/style/role/X842B perrow,CP0600..067F,GCCB200..D567,expandedfontE568..EA87 andcandidate22x64B outgoingcarry0700+i0800 maychange. Deadbackups/allother16MiB exact; actualsource/history/catalog/payload/font/shim/nativepixels independentlychecked.')
 (n.out/'extra-guards.json').write_text(json.dumps(result,indent=2)+'\n');return result

def execute(source,variant):
 previous.ports();e=freeze(source,variant);n=scenario(e,variant);plan=n.plan();(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
 with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in ['tests','tools']:
   for p in sorted((ROOT/folder).glob('*.py')):z.write(p,p.relative_to(ROOT))
 project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;r=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(r.stdout+r.stderr);assert not r.returncode
 print('NATIVE',variant,e,'steps',len(n.steps),'IRQbytes',n.keys,'captures',len(n.measurements),flush=True);previous.capacity.run_owned_plan(plan,n.out,timeout=2400);previous.ports();r=timing.evaluate(n);r['extra']=extra(n,r);(e/'result.json').write_text(json.dumps(r,indent=2)+'\n');return e,r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--baseline',type=Path,default=BASE);p.add_argument('--candidate',type=Path,default=CANDIDATE);a=p.parse_args()
 if not a.run:print('PreparednativePAL A/B8500/8600; no productionbuilds.');raise SystemExit
 out=ROOT/'build/geos-convergent-line-native'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);b,br=execute(a.baseline.resolve(),'baseline');e,er=execute(a.candidate.resolve(),'candidate');cases=[]
 for x,y in zip(br['measurements'],er['measurements']):
  assert x['id']==y['id'];assert(b/'timing'/('native-'+x['id']+'.png')).read_bytes()==(e/'timing'/('native-'+y['id']+'.png')).read_bytes();cases.append(dict(id=x['id'],baseline_cycles=x['emulated_cycles'],candidate_cycles=y['emulated_cycles'],baseline_loads=x['counter_deltas']['se_overlay_loads'],candidate_loads=y['counter_deltas']['se_overlay_loads'],PNG_byte_identical=True))
 r=dict(status='passed',baseline=str(b),candidate=str(e),cases=cases,VICE_closed=True,ports=[8500,8600],scope='ActualPAL normalspeed measuredpublicinputPC/SPseam toforegroundquiescence; realROMcoldboot/FileOpen/IRQsetup, trap+warpboot; exactsource/pixels/history/catalog/font/whole16MiB/shim/stack/probeguards. Notphysicalkeyboard/worstcase/generalreflowclaim.');(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('DONE',out,json.dumps(r),flush=True)
