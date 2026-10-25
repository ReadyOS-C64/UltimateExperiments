"""Private R28 heading-body PAL A/B qualification, own8500/text8600.

Real D81/Open and IRQ setup; explicit public-input PC/SP stopwatch seam.
No product/shared build edits, alternate renderer, or physical-key claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,shutil,socket,subprocess,zipfile
import test_geos_edit_profile as profile
import test_reu_capacity_vice as capacity
import test_file_throughput_vice as io
from test_fold_retention_vice import Captured
from d81_image import D81Image
import vice_plan
ROOT=profile.ROOT;timing=profile.timing
BASE=ROOT/'build/geos-incremental-editor/20261025T161722424199Z/fixture'
CANDIDATE=ROOT/'build/geos-heading-body/20261025T163902774632Z/fixture'
SOURCE_SHA='22f4543d4ad5ff04f1bc842bf1baf315cdd2b2c35aa827983dc09d598183f13b'
EOF_DOC=timing.native.live.grid.native_text('## Last heading words.')

class Plan(profile.Plan):
 calibrate=io.Plan.calibrate
 def boot(self):
  super().boot()
  self.raw('natural_startup_idle',['delete',f'break exec ${self.idle_pc:04x} if {self.condition(0)}','x','delete',f'logname "{self.out / "natural-startup-idle.log"}"','log on','registers','log off'])
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8500;p['global_defaults']['monitor_port_span']=1
  p['global_defaults']['timeouts']['step_s']=120;assert not p['global_defaults'].get('kill_stale',False);return p


def ports():
 for port in [8500,*range(8600,8640)]:
  with socket.socket()as s:s.bind(('127.0.0.1',port))


def freeze(base,tag):
 e=timing.native.freeze(base);target=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-heading-body-'+tag+'-native');shutil.move(e,target);e=target;io.unpack_catalog(e)
 ident=json.loads((e/'freeze.json').read_text());assert len(ident['catalog'])==47 and len((e/'styler.seo').read_bytes())-36==4047
 if tag=='candidate':
  with zipfile.ZipFile(e/'product-sources.zip')as z:assert hashlib.sha256(z.read('src/render/geos/edit-cache.s')).hexdigest()==SOURCE_SHA
  assert len((e/'geosdelta.seo').read_bytes())-36==4096
 else:assert len((e/'geosdelta.seo').read_bytes())-36==4051
 widths=(e/'bsw9-widths.bin').read_bytes();line=timing.native.live.grid.native_text('# ')
 while sum(widths[timing.native.live.geos.native(v)]for v in line)+widths[timing.native.live.geos.native(46)]<=320:line+=b'.'
 while sum(widths[timing.native.live.geos.native(v)]for v in line)>=320:line=line[:-1]
 assert sum(widths[timing.native.live.geos.native(v)]for v in line)+widths[timing.native.live.geos.native(timing.native.live.grid.native_text('Q')[0])]>320
 wrap=line+timing.native.live.grid.native_text('\rFollowing row.\rTail.')
 for name,data in [('EOFDOC',EOF_DOC),('WRAPDOC',wrap)]:
  p=e/(name.lower()+'.bin');p.write_bytes(data);r=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(p),name.lower()+',s'],capture_output=True,text=True);(e/(name.lower()+'-package.log')).write_text(r.stdout+r.stderr);assert not r.returncode
  assert D81Image((e/'working.d81').read_bytes()).read(name.encode(),kind=1).data==data
 shutil.copy2(e/'working.d81',e/'profile-initial.d81');return e,wrap


def scenario(e,variant,wrap):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),1,0);n.cost_profile=True;n.boot();n.calibrate();n.open('open_diverse',b'DIVERSE');n.typed('enter_geos','mode hires');data=timing.native.live.grid.fixture()
 def position(tag,at):
  line=data[:at].count(b'\r')+1;column=at-(data.rfind(b'\r',0,at)+1)
  n.typed(tag+'_top','top');n.typed(tag+'_goto',f'goto {line}')
  if column:n.send(tag+'_column',b'\x1d'*column)
  n.memory(tag+'_caret','se_hot_caret',at,3)
 def measure(tag,key,group,fast):
  nonlocal data
  at=n.expected_caret
  if key==0x14:data=data[:at-1]+data[at:];n.expected_caret-=1
  else:data=data[:at]+bytes([key])+data[at:];n.expected_caret+=1
  n.literal_return=key==13;n.measure(tag,data,3,key=key,category=group);n.literal_return=False
  expected=2 if variant=='candidate'and fast else 0
  n.measurements[-1].update(group=group,expected_fast=expected,expected_caret=n.expected_caret,expected_pending=1)
  n.memory(tag+'_actual_fast',0x9148,expected);n.memory(tag+'_actual_caret','se_hot_caret',n.expected_caret,3);n.memory(tag+'_pending','se_hot_pending',1)
  if expected:n.memory(tag+'_actual_class',0x9177,4)
 def pair(tag,at,key,fast=True):
  original=data;position(tag,at);n.expected_caret=at;measure(tag+'-insert',key,tag,fast);measure(tag+'-back',0x14,tag,fast);assert data==original
 q=timing.native.live.grid.native_text('Q')[0]
 pair('diverse422-heading-body',2+len(timing.native.live.grid.native_text('Super')),q)
 pair('heading-append-CR',data.index(b'\r'),q)
 pair('negative-split-CR',7,13,False)
 # Guarantee a real dirty confirmation before the next File/Open; the marker
 # is normal IRQ input and discarded by the actual D branch, outside timings.
 n.send('dirty_before_EOF_open',bytes([q]));n.open('open_EOF',b'EOFDOC',choice='D');data=EOF_DOC
 pair('heading-append-EOF',len(data),q)
 n.send('dirty_before_wrap_open',bytes([q]));n.open('open_wrap',b'WRAPDOC',choice='D');data=wrap
 pair('negative-new-wrap',3,q,False)
 return n


def extra(n,result):
 images=timing.native.live.grid.reu_images(n.out/'run');s=n.s;pack=(n.e/'font-pack.bin').read_bytes();states={};hashes={};intervals=0;groups=[]
 with zipfile.ZipFile(n.e/'product-sources.zip')as z:contract=z.read('src/render/geos/edit-cache.inc').decode()
 for expected in ['GEX_OLD_HEADER=$D528','GEX_OLD_ROW=$D568','GEX_NEW_ROW=$DD68','GEX_TAIL_END=$E568']:assert expected in contract
 fonts={name:(n.e/name).read_bytes()for name in timing.native.live.geos.GEOS_FONTS+('native8.bin',)}
 for item,measured in zip(n.measurements,result['measurements']):
  ident=item['id'];ram=(n.out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(n.out/'captures'/(ident+'-colors.bin')).read_bytes();f=Captured(s,ram,colors,n.e);f.colored=True;reu=images[ident]
  assert len(reu)==16777216 and f.get('se_reu_banks',2)==256
  assert ram[0x9148]==item['expected_fast'] and f.get('se_hot_caret')==item['expected_caret'] and f.get('se_hot_pending',1)==1,(ident,'actual path/caret/pending')
  if item['expected_fast']:assert ram[0x9177]==4
  assert not ram[0x9149]and not any(f.get(k,1)for k in ['se_e_error','se_f_owner','se_doc_read_locks','se_fs_owned','se_n_owned','se_doc_busy'])and ram[0x98]==0
  assert f.read(0xcb80,64)==(n.e/'editor-defaults.bin').read_bytes()
  for i,h in enumerate(f.read(0xcbc1,2)):
   bank=ram[s['se_reu_map']+h];assert h and bank and ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+bank]==0xfd
   part=pack[i*65536:(i+1)*65536];assert reu[bank*65536:bank*65536+len(part)]==part
  state=ram[s['se_doc_roots']:s['se_doc_roots']+512]+b''.join(ram[s[k]:s[k]+w]for k,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),('se_sel_mark',1),('se_clip_token',5),('se_clip_length',3)])
  group=item['group'];assert state==states.setdefault(group,state),(ident,'paired canonical/history changed')
  handle=ram[s['se_gc_handle']];bank=ram[s['se_reu_map']+handle];assert handle and bank and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+bank]==0xfe
  masked=bytearray(reu)
  for a,b in [(0,64),(0x200,0xe568)]:masked[bank*65536+a:bank*65536+b]=bytes(b-a)
  digest=hashlib.sha256(masked).hexdigest()
  if group in hashes:intervals+=1
  assert digest==hashes.setdefault(group,digest),(ident,'entire16MiB outside exactFE spans changed')
  data=bytes.fromhex(item['source']);_,_,rows,_=profile.timing.semantic.expected(f,data,fonts);cache=reu[bank*65536:(bank+1)*65536]
  assert cache[0]==1 and cache[1]==len(rows)
  for i,row in enumerate(rows):
   p=cache[0x200+i*0x800:0x220+i*0x800];assert (int.from_bytes(p[:3],'little'),int.from_bytes(p[3:6],'little'),int.from_bytes(p[6:9],'little'),int.from_bytes(p[9:12],'little'),int.from_bytes(p[12:14],'little'),p[14],p[15])==(row.start,row.end,row.next,row.start,row.end-row.start,row.height,row.top),(ident,'allcanonicalrows',i,p.hex(),row)
  assert f.get('se_v_bottom')==rows[-1].next
  text=(n.out/('stopwatch-'+ident+'.log')).read_text(encoding='utf-8-sig');regs=re.findall(r'(?m)^\.;([0-9a-f]{4})\s+[0-9a-f]{2}\s+[0-9a-f]{2}\s+[0-9a-f]{2}\s+([0-9a-f]{2})\s+[0-9a-f]{2}\s+[0-9a-f]{2}\s+([01]{8})',text,re.I)
  assert len(regs)==2 and int(regs[0][0],16)==timing.PROBE and regs[0][1].lower()=='ff'and int(regs[0][2],2)==0x20
  assert int(regs[-1][0],16)==n.idle_pc and regs[-1][1].lower()=='ff'and not(int(regs[-1][2],2)&4)
  groups.append(dict(id=ident,actual_fast=item['expected_fast'],caret=f.get('se_hot_caret'),rows=len(rows),source_bytes=len(data)))
 clocks=[int(v)for v in re.findall(r'Stopwatch:\s*(\d+)',(n.out/'calibration.log').read_text(encoding='utf-8-sig'),re.I)];assert clocks==[16],clocks
 assert (n.e/'working.d81').read_bytes()==(n.e/'profile-initial.d81').read_bytes(),'read-onlyD81 changed'
 resources=(n.out/'resources.log').read_text(encoding='utf-8-sig');launch=(n.out/'run/vice_stdout.log').read_text(encoding='utf-8-sig');assert'Warp mode is on.'in resources and' -trapdevice8 'in launch and' +drive8truedrive 'in launch
 result=dict(status='passed',whole16MiB_paired_intervals=intervals,canonical_history_groups=len(states),cases=groups,calibration_cycles=16,guard='Only authenticatedFEheader64/slots+body+transaction0200..E567 may change. Fonttail/allother16MiB, canonical/history/clip/settings exact within each realpending INSERT/BACK pair. Actual source/font/cache-allanchors also checked.',scope='Actual PAL publicinput seam to settledidle, not physicalkeyboard latency or worstcase.')
 (n.out/'extra-guards.json').write_text(json.dumps(result,indent=2)+'\n');return result


def execute(source,tag):
 ports();e,wrap=freeze(source,tag);n=scenario(e,tag,wrap);plan=n.plan();(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'measurements.json').write_text(json.dumps(n.measurements,indent=2)+'\n')
 with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in ['tests','tools']:
   for p in sorted((ROOT/folder).glob('*.py')):z.write(p,p.relative_to(ROOT))
 project=timing.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;p=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(p.stdout+p.stderr);assert not p.returncode
 print('NATIVE',tag,e,'steps',len(n.steps),'IRQbytes',n.keys,'captures',len(n.measurements),flush=True);capacity.run_owned_plan(plan,n.out,timeout=1800);ports();r=timing.evaluate(n);r['extra']=extra(n,r);(e/'result.json').write_text(json.dumps(r,indent=2)+'\n');return e,r


def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--baseline',type=Path,default=BASE);p.add_argument('--candidate',type=Path,default=CANDIDATE);a=p.parse_args()
 if not a.run:print('Prepared private R28 nativeA/B; --run owns8500/text8600, no sharedbuilds.');return
 out=ROOT/'build/geos-heading-body-native'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
 b,br=execute(a.baseline.resolve(),'baseline');c,cr=execute(a.candidate.resolve(),'candidate');cases=[]
 for x,y in zip(br['measurements'],cr['measurements']):
  assert x['id']==y['id'];bp=b/'timing'/('native-'+x['id']+'.png');cp=c/'timing'/('native-'+y['id']+'.png');assert bp.read_bytes()==cp.read_bytes(),(x['id'],'A/B PNGbytes differ')
  cases.append(dict(id=x['id'],baseline_cycles=x['emulated_cycles'],candidate_cycles=y['emulated_cycles'],baseline_first=x['first_publish_cycles'],candidate_first=y['first_publish_cycles'],baseline_loads=x['counter_deltas']['se_overlay_loads'],candidate_loads=y['counter_deltas']['se_overlay_loads'],PNG_byte_identical=True))
 result=dict(status='passed',baseline=str(b),candidate=str(c),cases=cases,whole16MiB_paired_intervals=br['extra']['whole16MiB_paired_intervals']+cr['extra']['whole16MiB_paired_intervals'],native_pixels=(len(br['measurements'])+len(cr['measurements']))*64000,VICE_closed=True,ports=[8500,8600],scope='PrivateR28-only PALactualsettledcost A/B. IRQenabledpublicinputPC/SPseam, realD81/Open/setup, source/pixel/font/payload/catalog/history/shim/stack/probe/REU guards; no productionpromotion/physicalkey/worstcase claim.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('DONE',out,json.dumps(result),flush=True)
if __name__=='__main__':main()
