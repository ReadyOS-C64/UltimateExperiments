"""Current53 cache/observer lifecycle qualification, private8300/text8400.

Actual packaged C29/R26 + real File/Open, pending input, controlled fresh trusted
bootstrap, resumed edit/Undo/SaveAs/reopen. Same live provider/backing REU;
no saved-stack continuation, ReadyOS, physical RESTORE or IRQ-ownership claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,json,shutil,socket,zipfile
import test_lifecycle_current_vice as current
from test_geos_navigation_vice import object_bytes
from test_fold_retention_vice import Captured
from overlay_catalog_policy import catalog_identity,catalog_state
import vice_plan
ROOT=current.ROOT;life=current.lifecycle
BASE=ROOT/'build/cache-editor-product/20261026T031201729970Z/fixture'

class CachePlan(current.CurrentPlan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8300;p['global_defaults']['monitor_port_span']=1
  assert not p['global_defaults'].get('kill_stale',False);return p

def free_ports():
 for port in(8300,*range(8400,8440)):
  with socket.socket()as s:
   try:s.bind(('127.0.0.1',port))
   except OSError as exc:raise AssertionError(f'owned port{port} busy; no process killed')from exc

def prepare(base):
 free_ports();report=json.loads((base/'build/editor-report.json').read_text());assert report['symbols']['se_overlay_managed_verification']==1
 with zipfile.ZipFile(base/'product-sources.zip')as source:
  for name in('adapter.s','adapter.inc','resume.s','resume.inc','copy-entry.s','copy-entry.inc','preflight.s','preflight.inc'):
   assert source.read('src/lifecycle/'+name)==(ROOT/'src/lifecycle'/name).read_bytes(),name
 old=life.component.command
 def flags(*args):
  args=list(args)
  if args[0]=='ca65' and str(args[-1]).endswith(('/resume.s','/copy-entry.s')):args[1:1]=['-D','EDITOR_MANAGED_CODE=1']
  return old(*args)
 life.component.command=flags
 try:e=life.prepare(base)
 finally:life.component.command=old
 target=e.with_name(e.name.replace('-lifecycle-native','-lifecycle-cache-current-native'));shutil.move(e,target);e=target
 with zipfile.ZipFile(e/'qualification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for directory in('tests','tools'):
   for p in sorted((ROOT/directory).glob('*.py')):z.write(p,p.relative_to(ROOT))
 life.Plan=CachePlan;n=life.scenario(e,3,False);plan=n.plan();assert plan['global_defaults']['monitor_port_start']==8300
 (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
 (e/'qualification.json').write_text(json.dumps(dict(status='prepared',base=str(base),PRG=report['sha256'],catalog=53,ports=[8300,'8400..8439'],packaged_C29_R26_byte_identical=True,trusted_fresh_bootstrap='Explicit R26/0A00 from exact sealed lifecycle images; unchanged live provider/REU only',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
 return e,n,plan

def cache_frame(s,ram,reu,e):
 f=Captured(s,ram,b'',e);token=ram[s['se_bc_arena']:s['se_bc_arena']+5];ident=token[0];assert ident<8 and any(token[1:]) and ram[s['object_owner']+ident]==0x53
 count=ram[s['object_banks']+ident];assert 1<=count<=16
 size=sum(ram[s[n]+ident]<<(8*i)for i,n in enumerate(('object_size_lo','object_size_mid','object_size_hi')));assert size==count*65536
 for i in range(count):
  logical=ram[s['object_extents']+ident*16+i];physical=ram[s['se_reu_map']+logical];assert logical and physical and ram[s['se_reu_logical_owner']+logical]==ram[s['se_reu_physical_owner']+physical]==0x53
 payload=object_bytes(f,reu,token,size);roots=[]
 for at in(0,128):
  h=payload[at:at+128]
  if h[:4]!=b'BCA1' or h[4:8]!=b'\1\1\x80\0':continue
  crc=binascii.crc_hqx(h[:5]+h[6:119]+h[121:],65535)
  if int.from_bytes(h[119:121],'little')!=crc:continue
  assert h[8:13]==token and h[13]==0x53 and h[14:18]==ram[s['se_bc_incarnation']:s['se_bc_incarnation']+4]
  roots.append((int.from_bytes(h[18:22],'little'),at,h))
 assert roots,'no authenticated baseline root';seq,at,root=max(roots)
 return dict(token=token.hex(),banks=count,bytes=size,sha256=hashlib.sha256(payload).hexdigest(),root_offset=at,root_sequence=seq,root_ticket=int.from_bytes(root[22:26],'little'),source59=root[32:91].hex(),merged_length=int.from_bytes(root[91:94],'little'),records=int.from_bytes(root[112:115],'little')),payload

def evaluate(e):
 # Preserve all original source/history/rawD81/VIC/provider/exactextent checks.
 result=life.evaluate(e);s=json.loads((e/'editor-report.json').read_text())['symbols'];caps=e/'lifecycle/captures';images=life.native.live.grid.reu_images(e/'lifecycle/run')
 ram=lambda n:(caps/(n+'-ram.bin')).read_bytes();colors=lambda n:(caps/(n+'-colors.bin')).read_bytes()
 assert (s['se_bc_arena'],s['se_bc_ring'])==(0x9FB5,0x9D85)
 names=('pending-before','prepared','exact-restored','prelude-finished','pending-resumed');reference=ram('pending-before');state=reference[s['se_bc_arena']:s['se_bc_arena']+17];ring=reference[s['se_bc_ring']:s['se_bc_ring']+96]
 assert state[13]&15==1 and state[16]>=1,'must exercise actually ARMED baseline plus queued visible edit'
 assert not state[13]&32,'published painter must not claim live query-page proof'
 for n in names:
  memory=ram(n);assert memory[s['se_bc_arena']:s['se_bc_arena']+17]==state,(n,'observer17 restore');assert memory[s['se_bc_ring']:s['se_bc_ring']+96]==ring,(n,'ring96 restore')
 # Validate every live queued record against the real observer wire format.
 events=[]
 for index in range(state[16]):
  slot=(state[15]+index)%3;event=ring[slot*32:(slot+1)*32];assert event[0]==0xA5 and event[1]in(1,2,3)
  assert int.from_bytes(event[29:31],'little')==binascii.crc_hqx(event[1:29]+event[31:],65535)
  events.append(dict(kind=event[1],ticket=int.from_bytes(event[4:8],'little'),position=int.from_bytes(event[16:19],'little'),delete=int.from_bytes(event[19:22],'little'),insert=int.from_bytes(event[22:25],'little')))
 assert events[-1]['ticket']==int.from_bytes(state[5:9],'little') and events[-1]['position']==0 and events[-1]['delete']==0 and events[-1]['insert']==1
 before_cache,before_bytes=cache_frame(s,reference,images['pending-before'],e);assert before_cache['merged_length']==422 and before_cache['records']>0 and before_cache['root_ticket']<events[-1]['ticket']
 for n in('prepared','pending-resumed'):
  proof,payload=cache_frame(s,ram(n),images[n],e);assert proof==before_cache and payload==before_bytes,(n,'typed53arena changed across capture/restore')
 catalog=[]
 for n in('pending-before','prepared','exact-restored','prelude-finished','pending-resumed','typed-after','undo','saved','reopened'):
  memory=ram(n);raw=memory[s['se_overlay_ids']:s['se_overlay_ids']+384];catalog.append(catalog_identity(raw,s));catalog_state(raw,s)
 assert len(set(catalog))==1
 boundary=ram('memo-invalidated');raw=boundary[s['se_overlay_ids']:s['se_overlay_ids']+384];assert not any(v for v in catalog_state(raw,s).verified if v is not None)
 assert boundary[s['se_overlay_active']:s['se_overlay_active']+2]==b'\0\0' and boundary[0xCBD5]==0
 assert boundary[s['se_bc_arena']:s['se_bc_arena']+17]==state and boundary[s['se_bc_ring']:s['se_bc_ring']+96]==ring
 assert catalog_identity(raw,s)==catalog[0]
 # This actual same-source literal redraw changed only the documented GCC
 # bitmap/attribute snapshot, so strengthen the old wholeFE allowance here.
 prepared=images['prepared'];resumed=images['pending-resumed'];memory=ram('pending-resumed');h=memory[s['se_gc_handle']];bank=memory[s['se_reu_map']+h]
 assert h and bank and memory[s['se_reu_logical_owner']+h]==memory[s['se_reu_physical_owner']+bank]==0xFE
 lo=bank*65536+0xB200;hi=bank*65536+0xD528
 assert prepared[:lo]==resumed[:lo] and prepared[hi:]==resumed[hi:],'resume changed bytes outside exact GCC snapshot'
 stages=[]
 for n in('pending-before','pending-resumed','typed-after','undo','saved','reopened'):
  v=ram(n)[s['se_bc_arena']:s['se_bc_arena']+17];assert not v[13]&(4|8|32) and v[14]<3 and v[15]<3 and v[16]<=3
  stages.append(dict(stage=n,token=v[:5].hex(),ticket=int.from_bytes(v[5:9],'little'),incarnation=int.from_bytes(v[9:13],'little'),flags=v[13],count=v[16]))
 reopened,reopened_bytes=cache_frame(s,ram('reopened'),images['reopened'],e)
 assert stages[-1]['count']==0 and stages[-1]['flags']&15==1 and stages[-1]['incarnation']>stages[0]['incarnation'] and reopened['token']!=before_cache['token'] and reopened['merged_length']==422
 assert reopened['root_ticket']==stages[-1]['ticket']
 result.update(status='passed',observer17_bytes=17,observer_ring_bytes=96,observer_stage_summary=stages,reopened_fresh_baseline=reopened,resume_precise_REU_allowance=dict(owner=254,logical=h,physical=bank,start=0xB200,end=0xD528,changed_bytes=sum(a!=b for a,b in zip(prepared,resumed))),observer_state=state.hex(),queued_events=events,typed53arena=before_cache,typed53_whole_bytes_preserved=['pending-before→prepared','prepared→pending-resumed'],captured_PAGE_PROOF=0,managed_prelude_revokes='allpublished verificationbits+activeC/R+GFwindowtag before first overlay',catalog_identity_policy='published slot bit7 only underdeclared managedfeature',ports=[8300,'8400..8439'],scope=__doc__,wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),visual_review='pending')
 (e/'cache-current-result.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--run',action='store_true');p.add_argument('--prepare',action='store_true');p.add_argument('--verify',type=Path);a=p.parse_args()
 if a.verify:print(json.dumps(evaluate(a.verify.resolve()),indent=2));return
 if not(a.run or a.prepare):print(__doc__);return
 e,n,plan=prepare(a.fixture.resolve());print('CACHE_LIFECYCLE_PREPARED',e,'steps',len(n.steps),flush=True)
 if not a.run:return
 project=life.native.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;life.component.command('dotnet','build',project,'--nologo');print('CACHE_LIFECYCLE_NATIVE',e,'8300/8400',flush=True);vice_plan.run_plan(plan,n.out);result=evaluate(e);free_ports();result['owned_ports_released']=True;(e/'cache-current-result.json').write_text(json.dumps(result,indent=2)+'\n');print('CACHE_LIFECYCLE_PASS',e,result['native_pixels'],flush=True)
if __name__=='__main__':main()
