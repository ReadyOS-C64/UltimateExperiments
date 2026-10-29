"""Current immutable42-asset file protocol native regression; private8100/8200.

Legacy scenarios remain read-only imports. New freeze/full16MiB/token decoder/
current source+File/recovery UI oracle; no product/shared build changes.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,shutil,subprocess,zipfile,sys,socket
from types import SimpleNamespace
import test_grid_modes as modes
import test_file_faults_vice as old
import test_geos_fold_native as frozen_native
import test_geos_editor as geos
import test_grid_editor_vice as grid
import test_reu_capacity_vice as runner
from test_fold_retention_vice import Captured
from d81_image import D81Image,D81Error
from png_pixels import read_png
from vice_config import step
import vice_plan
from cache_job_build import editor_pair_index
ROOT=old.ROOT;BASE=old.BASE;OPENED=old.OPENED;CASES=old.CASES
DEFAULT=ROOT/'build/geos-incremental-editor/20261025T081538083121Z/fixture'
SELECTED=['missing-device','write-protected','disk-full','cancel-read','cancel-write','cancel-candidate-scan','candidate-seq','candidate-prg','candidate-splat','promotion-ack-injected','missing-c12-open','missing-c12-save','missing-both-read','missing-both-preflight','missing-c12-saved-ack9','missing-c12-savepoint-pending9']
digest=old.digest;raw_file=old.raw_file;free_blocks=old.free_blocks


def freeze(source):
 e=frozen_native.freeze(source)
 target=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-file-faults-native42')
 target.parent.mkdir(exist_ok=True);shutil.move(e,target)
 record=json.loads((target/'freeze.json').read_text());assert len(record['catalog'])==42
 for artifact in ('working.d81','initial-fixtures.d81','diverse.bin','package.log'):(target/artifact).unlink(missing_ok=True)
 # Each legacy case receives a fresh independent product disk and fixtures.
 with zipfile.ZipFile(target/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in ('tests','tools'):
   for p in sorted((ROOT/folder).glob('*.py')):z.write(p,p.relative_to(ROOT))
 return target


class Plan(old.FaultPlan):
 def boot(self):
  super().boot();p=self.out/'resources.mon';s=p.read_text();assert '"REUsize" "1024"'in s
  p.write_text(s.replace('"REUsize" "1024"','"REUsize" "16384"'))
  self.memory('real_font_pack_ready',0xcbc0,0xa5)
  self.memory('real_reu_256banks','se_reu_banks',256,2)
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8100;p['global_defaults']['monitor_port_span']=1
  p['global_defaults']['timeouts']['step_s']=120
  assert not p['global_defaults'].get('kill_stale',False)
  return p
 def lose(self,*names):
  captures=self.out/'captures';captures.mkdir(exist_ok=True)
  self.raw('pre_loss_display',[f'bsave "{captures}/pre-loss-ram.bin" 0 $0000 $cfff',f'bsave "{captures}/pre-loss-colors.bin" 0 $d800 $dbe7'])
  super().lose(*names)
 def snapshot(self,ident,**kw):
  # Preserve every actual old memory assertion, but replace its asynchronous
  # screenshot/RAM captures with one monitor-halted coherent frame.
  start=len(self.steps);super().snapshot(ident,**kw)
  added=self.steps[start:]
  # The api above emits a playback monitor.command, which has a different id;
  # preserve all its command/assertions and remove only the three finalcaptures.
  self.steps[start:]=[v for v in added if v['id'] not in (ident+'_native',ident+'_ram',ident+'_reu')]
  captures=self.out/'captures';captures.mkdir(exist_ok=True)
  commands=['delete']
  if not self.controlled:
   wanted=[('se_e_ui',kw.get('ui',3)),('se_f_owner',kw.get('owner',1)),('se_e_job',0),('se_e_redraw',0),('se_e_draw_busy',0)]
   condition=' && '.join(f'(@cpu:${self.s[k]:04x} == ${v:02x})'for k,v in wanted)
   condition+=f' && (@cpu:${self.s["se_input_head"]:04x} == @cpu:${self.s["se_input_tail"]:04x}) && (@cpu:$00c6 == $00)'
   if kw.get('ui',3)==0:condition+=f' && (@cpu:${self.s["se_st_request"]:04x} == $00)'
   commands +=[f'break exec ${self.s["se_idle"]:04x} if {condition}','x','delete']
  commands +=[f'screenshot "{self.out}/native-{ident}.png" 2',f'bsave "{captures}/{ident}-ram.bin" 0 $0000 $cfff',f'bsave "{captures}/{ident}-colors.bin" 0 $d800 $dbe7']
  self.raw(ident+'_coherent',commands)
  self.steps.append(step(ident+'_reu','dump.reu',mode='full',stage_tag=ident+'_reu'))
  # Retain old artifact filenames as additional exact mirror captures for its
  # unmodified logical assertions in protocol_evaluate.
  self.steps.append(step(ident+'_ram','dump.memory_ranges',ranges=[dict(label='ram',start=0,end=0xcfff),dict(label='colors',start=0xd800,end=0xdbe7)]))


def decode_source(ram,reu,s):
 def val(n,w=1):return int.from_bytes(ram[s[n]:s[n]+w],'little')
 epoch=ram[s['se_reu_epoch']:s['se_reu_epoch']+2]
 assert epoch==ram[s['se_doc_epoch']:s['se_doc_epoch']+2]==ram[s['se_object_epoch']:s['se_object_epoch']+2]
 def obj(identity,offset,length):
  assert identity<8 and ram[s['object_owner']+identity]
  owner=ram[s['object_owner']+identity];size=sum(ram[s[n]+identity]<<(8*i)for i,n in enumerate(('object_size_lo','object_size_mid','object_size_hi')))
  assert 0<=offset<=offset+length<=size
  out=bytearray()
  while length:
   n=min(length,65536-(offset&65535));handle=ram[s['object_extents']+identity*16+(offset>>16)];bank=ram[s['se_reu_map']+handle]
   assert handle and bank and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+bank]==owner
   start=bank*65536+(offset&65535);assert start+n<=len(reu)
   out+=reu[start:start+n];offset+=n;length-=n
  return bytes(out)
 def token(name):
  t=ram[s[name]:s[name]+5];i=t[0];assert i<8 and t[1:3]==bytes((ram[s['object_gen_lo']+i],ram[s['object_gen_hi']+i]))and t[3:5]==epoch
  return i
 meta=token('se_doc_meta');token('se_doc_original');token('se_doc_append');assert val('se_doc_root_count')*8<=512
 data=bytearray()
 for i in range(val('se_doc_root_count')):
  root=ram[s['se_doc_roots']+i*8:s['se_doc_roots']+(i+1)*8];leaf=obj(meta,root[0]*1024,root[1]*16)
  for j in range(root[1]):
   piece=leaf[j*16:(j+1)*16];identity=piece[0];assert identity<8 and piece[1:3]==bytes((ram[s['object_gen_lo']+identity],ram[s['object_gen_hi']+identity]))
   data+=obj(identity,int.from_bytes(piece[3:6],'little'),int.from_bytes(piece[6:9],'little'))
 assert len(data)==val('se_doc_length',3)and not val('se_hot_pending')
 return bytes(data),obj


def protocol_evaluate(n,artifacts,manifest):
 images={}
 for p in (artifacts/'dumps').glob('*.json'):
  for chunk in json.loads(p.read_text(encoding='utf-8-sig')).get('chunks',[]):
   if chunk.get('source')=='vice_native_reu_image':images[p.name.removeprefix('reu_').removesuffix('_reu_index.json')]=(p.parent/Path(chunk['file']).name).read_bytes()
 baseline=None;observed=[]
 for item in n.observations:
  ident=item['id'];ram=(n.out/'captures'/(ident+'-ram.bin')).read_bytes();reu=images[ident];assert len(ram)==0xD000 and len(reu)==16*1024*1024
  def val(name,width=1):return int.from_bytes(ram[n.s[name]:n.s[name]+width],'little')
  source,obj=decode_source(ram,reu,n.s);assert source==bytes.fromhex(item['expected']),(ident,'source mismatch')
  assert ram[0xC600:0xCA00]==n.canary and ram[0x98]==0
  # Cursor/selection and clipboard objects are independent from file staging.
  clip=ram[n.s['se_clip_token']:n.s['se_clip_token']+5];clipdata=obj(clip[0],0,val('se_clip_length',3)) if val('se_clip_active') else b''
  history={name:ram[n.s[name]:n.s[name]+width].hex() for name,width in [('se_h_token',5),('se_h_generation',2),('se_h_original',5),('se_h_append',5),('se_h_end',2),('se_h_cursor',2),('se_h_current',4),('se_h_saved',4),('se_h_counter',4),('se_h_dirty',1)]}
  canonical=ram[n.s['se_doc_roots']:n.s['se_doc_roots']+256]+ram[n.s['se_doc_ready']:n.s['se_doc_ready']+22]
  selection=(val('se_hot_caret',3),val('se_sel_mark'),val('se_sel_anchor',3));clipboard=(clip.hex(),clipdata.hex(),val('se_clip_length',3),val('se_clip_generation',2))
  if baseline is None:baseline=dict(history=history,canonical=canonical,selection=selection,clipboard=clipboard)
  else:
   assert clipboard==baseline['clipboard'],(ident,'clipboard changed')
   if item['unchanged']:
    expected_history=dict(baseline['history'])
    if item['saved_ack']:expected_history.update(se_h_saved=baseline['history']['se_h_current'],se_h_dirty='00')
    assert history==expected_history and canonical==baseline['canonical'] and selection==baseline['selection'],(ident,'source/history/savepoint/selection changed')
   else:assert val('se_hot_caret',3)==0 and val('se_sel_mark')==0 and val('se_h_current',4)==val('se_h_saved',4)
  if item['caret'] is not None:assert val('se_hot_caret',3)==item['caret']
  observed.append(dict(id=ident,source_bytes=len(source),source_sha256=hashlib.sha256(source).hexdigest(),root_error=val('se_e_error'),file_error=val('se_f_error') if val('se_f_owner') else None,dos=val('se_f_dos_error') if val('se_f_owner') else None,owner=val('se_f_owner'),lease=val('se_f_lease') if val('se_f_owner') else None,history=history,clipboard_bytes=len(clipdata)))
 before=D81Image((n.out/'initial.d81').read_bytes());after=D81Image((n.out/'working.d81').read_bytes());changed_target=n.case=='promotion-ack-injected'
 for entry in before.entries():
  if changed_target and entry.name==b'FBASE':assert after.read(b'FBASE',kind=1).data==n.source;continue
  first,last=raw_file(before,entry.name),raw_file(after,entry.name);assert first.entry.raw[2:]==last.entry.raw[2:] and first.data==last.data and first.sectors==last.sectors,(n.case,'unrelated original chain changed',entry.name)
 names={entry.name for entry in after.entries()};extra=names-{entry.name for entry in before.entries()}
 allowed={b'SE~T000000000000',b'SE~B000000000000'}|({b'FSAFE'} if n.case=='native-a0-retry' else set());assert extra<=allowed,(n.case,extra)
 extras=[]
 for name in sorted(extra):
  entry=next(x for x in after.entries() if x.name==name);record=dict(name=name.decode('ascii'),closed=entry.closed,blocks=entry.blocks)
  try:
   candidate=after.read(name);record.update(bytes=len(candidate.data),sha256=hashlib.sha256(candidate.data).hexdigest(),first32_hex=candidate.data[:32].hex(),sector_chain=[(t,sec) for t,sec,_ in candidate.sectors])
  except D81Error as error:record['unreadable_candidate']=str(error)
  extras.append(record)
 if n.case=='native-a0-retry':assert after.read(b'FSAFE',kind=1).data==n.source and extra=={b'FSAFE'}
 if n.case=='disk-full':assert free_blocks(before)==1 and free_blocks(after)==0 and extra=={b'SE~T000000000000'}
 if n.case=='promotion-ack-injected':assert after.read(b'SE~B000000000000',kind=1).data==BASE
 if n.case in ['missing-c12-saved-ack9','missing-c12-savepoint-pending9']:
  nine=D81Image((n.out/'working9.d81').read_bytes());assert nine.read(b'FSAVED9',kind=1).data==n.source and {x.name for x in nine.entries()}=={b'FSAVED9'}
 if n.case.startswith('candidate-') or n.case in ['missing-device','write-protected','native-at16','cancel-candidate-scan']:assert (n.out/'working.d81').read_bytes()==(n.out/'initial.d81').read_bytes()
 if n.case in ['cancel-read','cancel-write','cancel-candidate-scan','promotion-refused','backup-collision','close-status-injected']:assert not extra,(n.case,'uncollected owned temp',extra)
 result=dict(status='passed',executed_test_sha256=digest(Path(__file__)),case=n.case,coverage=CASES[n.case],evidence=str(n.out),manifest=str(manifest),resident_sha256=n.r['sha256'],injections=n.injections,observations=observed,extra_exact_native_names=[name.decode('ascii') for name in sorted(extra)],extra_artifacts=extras,raw_disk_sha256=digest(n.out/'working.d81'),shim_bytes=1024,channels_closed=True,limitations='Native ROM IEC/root pump with IRQ keyboard bytes; no physical keyboard or power-loss claim. Monitor stubs control bounded phase scheduling; catalog/status/epoch changes are explicitly debugger-injected, never physical disk failures. Screenshots need visual review.')
 (n.out/'protocol-result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def ui_expected(f,data):
 class Underlying:
  s=f.s;fonts=f.fonts;colored=True
  def read(self,*args):return f.read(*args)
  def get(self,name,w=3):return 0 if name=='se_e_ui' else f.get(name,w)
 (matrix,colors),_,_,_=modes.expected(Underlying(),data)
 u=grid.UI(SimpleNamespace(matrix=matrix,colors=colors))
 if f.get('se_e_ui',1)!=3:return bytes(u.matrix),bytes(u.colors)
 u.box(1,4,38,19)
 u.put(5,3,'Open a PETSCII document' if f.get('se_f_operation',1)==1 else 'Save a PETSCII document')
 u.colors[203:238]=bytes([7])*35
 u.put(6,3,'Device:');u.put(6,10,str(f.get('se_f_device',1)));u.put(7,3,'Name:')
 name=f.read(f.s['se_f_name'],f.get('se_f_name_len',1));u.put(7,10,bytes(map(grid.screen_code,name)),3,raw=True);u.put(7,10+len(name),b'\xa0',3,raw=True)
 if f.get('se_f_ui_help',1):
  for row,label in [(10,'Type up to 16 PETSCII characters.'),(12,'RETURN accepts the name.'),(14,'F3 drive F5 page DEL erase'),(16,'STOP cancels; F6 help.'),(18,'S Save   D Discard   C Cancel')]:u.put(row,3,label)
 elif f.get('se_fd_confirm',1):
  for row,label in [(10,'Save changes before opening?'),(12,'S Save   D Discard   C Cancel'),(14,'STOP cancels; F6 help.')]:u.put(row,3,label)
 elif f.get('se_f_error',1)==0x9b:
  u.put(10,3,'Recovery: files retained.');u.put(12,3,'K keeps files and closes')
  for row,owned,name in [(14,'se_io_owned_temp','se_io_temp_name'),(16,'se_io_owned_backup','se_io_backup_name')]:
   if f.get(owned,1):u.put(row,4,bytes(map(grid.screen_code,f.read(f.s[name],16))),raw=True)
 else:
  count=f.get('se_fd_list_count',1);assert count<=8
  for i in range(count):
   length=f.read(f.s['se_fd_list_lengths']+i,1)[0];assert length<=16
   name=f.read(f.s['se_fd_list_names']+16*i,length)
   u.put(9+i,4,bytes(map(grid.screen_code,name)),3 if i==f.get('se_fd_list_index',1) else 1,inverse=i==f.get('se_fd_list_index',1),raw=True)
  u.put(18,3,'UP/DOWN choose; RETURN accepts');u.put(19,3,'F3 drive 8/9  F5 page')
  error=f.get('se_f_error',1) or f.get('se_fd_list_error',1)
  if error:
   u.put(21,3,'Error $    DOS $');u.put(21,10,f'{error:02X}');u.put(21,19,f'{f.get("se_f_dos_error",1):02X}')
 u.put(24,0,' File dialog       F6 Help   STOP Back   ')
 return bytes(u.matrix),bytes(u.colors)


def evaluate(n):
 result=protocol_evaluate(n,n.out/'run',n.out/'run/manifest.json')
 images=grid.reu_images(n.out/'run');identity=json.loads((n.e/'freeze.json').read_text());stable_catalog=None;stable_journal=None;stable_objects=None;stable_graph=None;palette={};observations=[]
 font=(n.e/'chargen.bin').read_bytes()[2048:4096];assert len(font)==2048
 for item in n.observations:
  ident=item['id'];ram=(n.out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(n.out/'captures'/(ident+'-colors.bin')).read_bytes();reu=images[ident];f=Captured(n.s,ram,colors,n.e);f.colored=True
  data,obj=decode_source(ram,reu,n.s);assert len(reu)==16*1024*1024 and f.get('se_reu_banks',2)==256
  assert f.get('se_mode',1)==0 and f.read(0xcb80,64)==(n.e/'editor-defaults.bin').read_bytes()
  catalog=bytearray(f.read(n.s['se_overlay_ids'],384))
  if ident!='before':
   for injection in n.injections:
    for name in injection.get('assets',[]):
     image=(n.e/(name+'.seo')).read_bytes();index=editor_pair_index(image[5],image[6]) if 'catalog_index' in n.s else identity['catalog'].index(name)
     assert catalog[index]==0;catalog[index]=stable_catalog[index]
  if stable_catalog is None:stable_catalog=bytes(catalog)
  assert bytes(catalog)==stable_catalog,(ident,'42-image catalog changed outside declared injected IDs')
  for order,name in enumerate(identity['catalog']):
   image=(n.e/(name+'.seo')).read_bytes();slot=editor_pair_index(image[5],image[6]) if 'catalog_index' in n.s else order
   handle=f.get(('se_overlay_asset','se_overlay_asset_second','se_overlay_asset_third','se_overlay_asset_fourth')[slot>>4],1);bank=ram[n.s['se_reu_map']+handle]
   assert handle and bank and ram[n.s['se_reu_logical_owner']+handle]==ram[n.s['se_reu_physical_owner']+bank]==2
   payload=image[36:];at=bank*65536+(slot&15)*4096;assert reu[at:at+len(payload)]==payload,(ident,name,'asset bytes')
  pack=(n.e/'font-pack.bin').read_bytes()
  for i,handle in enumerate(f.read(0xcbc1,2)):
   bank=ram[n.s['se_reu_map']+handle];assert handle and bank and ram[n.s['se_reu_logical_owner']+handle]==ram[n.s['se_reu_physical_owner']+bank]==0xfd
   part=pack[i*65536:(i+1)*65536];assert reu[bank*65536:bank*65536+len(part)]==part,(ident,'real font pack')
  journal=obj(f.get('se_h_token',1),0,f.get('se_h_end',2))
  if stable_journal is None:stable_journal=journal
  elif item['unchanged']:assert journal==stable_journal,(ident,'history journal bytes')
  protected={}
  for name in ('se_doc_meta','se_doc_original','se_doc_append','se_h_token','se_clip_token'):
   token=f.read(n.s[name],5);index=token[0];assert index<8
   assert token[1:3]==bytes((ram[n.s['object_gen_lo']+index],ram[n.s['object_gen_hi']+index])) and token[3:5]==f.read(n.s['se_object_epoch'],2),(ident,name,'full capability')
   size=sum(ram[n.s[k]+index]<<(i*8)for i,k in enumerate(('object_size_lo','object_size_mid','object_size_hi')))
   protected[name]=dict(token=token.hex(),size=size,sha256=hashlib.sha256(obj(index,0,size)).hexdigest())
  graph=f.read(n.s['se_doc_roots'],512)+b''.join(f.read(n.s[k],w)for k,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_doc_root_count',1)])
  if stable_objects is None:stable_objects=protected;stable_graph=graph
  elif item['unchanged']:
   assert protected==stable_objects,(ident,'whole live canonical/append/history/clipboard objects changed')
   assert graph==stable_graph,(ident,'full512B canonical root graph')
  if n.case.startswith('missing-both') and ident!='before':
   # Both admission images are absent: this deliberately retained phase cannot
   # paint a new error panel. Prove the exact pre-fault display is held instead.
   prior=(n.out/'captures/pre-loss-ram.bin').read_bytes();expected=(prior[0x4000:0x43e8],bytes(v&15 for v in (n.out/'captures/pre-loss-colors.bin').read_bytes()))
  else:expected=ui_expected(f,data)
  actual=(f.read(0x4000,1000),bytes(v&15 for v in colors))
  for label,got,want in zip(('screen','colors'),actual,expected):
   assert len(got)==len(want)==1000
   if got!=want:
    differences=[(i//40,i%40,a,b)for i,(a,b)in enumerate(zip(got,want))if a!=b];(n.out/(ident+'-'+label+'-diff.json')).write_text(json.dumps(differences,indent=2));raise AssertionError((n.case,ident,label,differences[:12]))
  w,h,pixels=read_png(n.out/('native-'+ident+'.png'));assert(w,h)==(384,272)
  for y in range(200):
   for x in range(320):
    at=(y//8)*40+x//8;code=expected[0][at];ink=expected[1][at] if font[code*8+(y&7)]&(128>>(x&7)) else 6
    rgb=pixels[(y+35)*w+x+32]
    if ink in palette:assert rgb==palette[ink],(n.case,ident,'actual VIC pixel',x,y,ink,rgb,palette[ink])
    else:assert rgb not in palette.values(),('palette collapse',ink,rgb);palette[ink]=rgb
  observations.append(dict(id=ident,pixels=64000,attributes=1000,catalog_bytes=384,font_pack_bytes=len(pack),reu_bytes=len(reu),history_bytes=len(journal),protected_objects=protected,screen_sha256=hashlib.sha256(actual[0]).hexdigest(),png_sha256=digest(n.out/('native-'+ident+'.png'))))
 result.update(current_ui='passed independent full1000 screen/color cells and actual64000 VIC pixels per screenshot',screens=len(observations),pixels=len(observations)*64000,attributes=len(observations)*1000,guards=observations,vice_closed=True,
  limitations='Actual ROM IEC, IRQ keyboard bytes and full16MiB captures. Catalog/ack faults are explicitly debugger-injected. All live42 assets, actual fontpack, canonical source/clipboard/history and shim checked; file staging legitimately changes/free leaves REU bytes, so no claim that every unowned REU byte stays unchanged. Both-missing phase preserves its exact pre-fault UI and owned failure state; no completed cleanup claim. No physical keyboard, power-loss, lifecycle or final release claim.')
 (n.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',n.case,len(observations),'screens',flush=True);return result


def execute(e,case,prepare=False):
 if not(e/case/'initial.d81').exists():old.package(e,case)
 r=json.loads((e/'editor-report.json').read_text());old.FaultPlan=Plan;n=old.scenario(e,case,r);p=n.plan()
 assert len({s['id']for s in p['steps']})==len(p['steps'])
 (n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n');(n.out/'observations.json').write_text(json.dumps(n.observations,indent=2)+'\n')
 (n.out/'scenario.json').write_text(json.dumps(dict(source=n.source.hex(),injections=n.injections,keys=n.keys),indent=2)+'\n')
 print('PREPARED',case,n.out,len(n.steps),'steps',n.keys,'IRQbytes',flush=True)
 if prepare:return
 for port in (8100,8200):
  with socket.socket()as c:assert c.connect_ex(('127.0.0.1',port))!=0,('owned port already busy',port)
 project=grid.synchronous_project(n.out);vice_plan.PROJECT=project
 built=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(built.stdout+built.stderr);assert not built.returncode
 runner.run_owned_plan(p,n.out,timeout=900);return evaluate(n)


def reload_case(path):
 path=path.resolve();e=path.parent;r=json.loads((e/'editor-report.json').read_text());meta=json.loads((path/'scenario.json').read_text())
 return SimpleNamespace(e=e,out=path,case=path.name,r=r,s=r['symbols'],canary=bytes((i*73+29)&255 for i in range(1024)),observations=json.loads((path/'observations.json').read_text()),source=bytes.fromhex(meta['source']),injections=meta['injections'])


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--prepare',action='store_true');p.add_argument('--fixture',type=Path,default=DEFAULT);p.add_argument('--evidence',type=Path);p.add_argument('--case',choices=SELECTED,action='append');p.add_argument('--verify',type=Path);a=p.parse_args()
 if a.verify:evaluate(reload_case(a.verify))
 elif a.run or a.prepare:
  e=a.evidence.resolve()if a.evidence else freeze(a.fixture)
  for case in a.case or SELECTED:execute(e,case,prepare=not a.run)
 else:print(json.dumps(dict(cases={c:CASES[c]for c in SELECTED},fixture=str(DEFAULT),owned_ports=[8100,8200],note='Private immutable42 native regression, not a final release claim.'),indent=2))
