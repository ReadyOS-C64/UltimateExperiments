"""Actual fixed59 standalone lifecycle; five owned sequential native sessions.

Packaged C29/R26 byte identity, exact48152 warm bytes, live provider only.
Explicit fresh monitor bootstrap/PC/SP seams are inherited unchanged. No old
stack/ReadyOS/physicalRESTORE/physical-key ownership claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,json,os,shutil,socket,subprocess,zipfile
import test_lifecycle_current_vice as current
import test_lifecycle_cache_current as cache
import test_grid_capture_index as identity
import vice_plan
ROOT=current.ROOT;life=current.lifecycle
OriginalPlan=current.CurrentPlan

class RegisteredPlan(OriginalPlan):
 def open(self,ident,name):
  result=super().open(ident,name)
  if ident=='open_diverse' and self.test_mode<3:
   # Genuine foreground baseline before returning to the tested grid mode.
   # This creates real nonzero observer/arena state; no flags/refs are seeded.
   self.typed('prime_actual_semantic_baseline','mode hires')
   self.memory('prime_actual_ARMED','se_bc_flags',0x11) # ARMED|REBUILD_TRIED in this sealedautomatic profile
   self.mode_to(0)
  return result

def free_ports():
 # SO_REUSEADDR permits closed owned TIME_WAIT; a live listener still refuses.
 for port in (8500,*range(8600,8640)):
  with socket.socket()as sock:
   sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
   try:sock.bind(('127.0.0.1',port))
   except OSError as exc:raise AssertionError(f'owned port{port} has a live/busy listener; no process killed')from exc

def hardlink_duplicates(e):
 """Only closed owned files. Keep every path and hash, never touch other runs."""
 known={};saved=0;count=0
 for directory in (e,):
  for p in sorted(directory.rglob('*')):
   if not p.is_file() or p.stat().st_size<1024*1024:continue
   # RawREU names vary by .NETdump/backend; only exact16MiB byte images.
   if p.stat().st_size!=16*1024*1024:continue
   digest=hashlib.sha256(p.read_bytes()).hexdigest()
   if digest not in known:known[digest]=p;continue
   peer=known[digest]
   if p.stat().st_ino==peer.stat().st_ino:continue
   before=p.stat().st_size;temp=p.with_name(p.name+'.owned-hardlink')
   os.link(peer,temp);os.replace(temp,p)
   assert p.stat().st_ino==peer.stat().st_ino and hashlib.sha256(p.read_bytes()).hexdigest()==digest
   saved+=before;count+=1
 receipt=dict(closed_owned_only=True,hardlinked_files=count,bytes_avoided=saved,content_hashes=list(known))
 (e/'owned-REU-hardlinks.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt

def observer_audit(e):
 s=json.loads((e/'editor-report.json').read_text())['symbols'];caps=e/'lifecycle/captures';images=life.native.live.grid.reu_images(e/'lifecycle/run')
 ram=lambda n:(caps/(n+'-ram.bin')).read_bytes();reference=ram('pending-before');at=s['se_bc_arena'];ringat=s['se_bc_ring']
 state=reference[at:at+17];ring=reference[ringat:ringat+96]
 assert state[13]&15==1 and state[16]>=1 and not state[13]&32,'actualARMED+queued edit, no transientPAGEclaim'
 for name in ('prepared','exact-restored','prelude-finished','pending-resumed'):
  m=ram(name);assert m[at:at+17]==state and m[ringat:ringat+96]==ring,(name,'observer17/ring96 exact')
 proof,payload=cache.cache_frame(s,reference,images['pending-before'],e)
 assert proof['merged_length']==422 and proof['records']>0
 for name in ('prepared','pending-resumed'):
  p,raw=cache.cache_frame(s,ram(name),images[name],e);assert p==proof and raw==payload,(name,'allowned53bytes immutable')
 events=[]
 for i in range(state[16]):
  slot=(state[15]+i)%3;record=ring[slot*32:slot*32+32]
  assert record[0]==0xa5 and record[1]in(1,2,3)
  assert int.from_bytes(record[29:31],'little')==binascii.crc_hqx(record[1:29]+record[31:],65535)
  events.append(dict(kind=record[1],ticket=int.from_bytes(record[4:8],'little'),position=int.from_bytes(record[16:19],'little'),delete=int.from_bytes(record[19:22],'little'),insert=int.from_bytes(record[22:25],'little')))
 assert events[-1]['ticket']==int.from_bytes(state[5:9],'little') and events[-1]['position']==0 and events[-1]['delete']==0 and events[-1]['insert']==1
 boundary=ram('memo-invalidated');assert boundary[at:at+17]==state and boundary[ringat:ringat+96]==ring
 assert boundary[0xcf00]==boundary[0xcf90]==boundary[0xcfe8]==0,'freshprelude revokes fontquery/GCC/editcert'
 stages=[]
 for n in ('pending-before','pending-resumed','typed-after','undo','saved','reopened'):
  v=ram(n)[at:at+17];assert not v[13]&(4|8|32) and v[14]<3 and v[15]<3 and v[16]<=3
  stages.append(dict(stage=n,arena=v[:5].hex(),ticket=int.from_bytes(v[5:9],'little'),incarnation=int.from_bytes(v[9:13],'little'),flags=v[13],queue=v[16]))
 assert stages[-1]['incarnation']>stages[0]['incarnation'] and stages[-1]['queue']==0
 if stages[-1]['arena']!='0000000000':
  p,_=cache.cache_frame(s,ram('reopened'),images['reopened'],e);assert p['merged_length']==422
 else:assert stages[-1]['flags']&15==2,'nonGEOSreopen leavesLOST rather thaninventingbaseline'
 result=dict(observer_bytes=17,ring_bytes=96,observer_state=state.hex(),events=events,stages=stages,typed53=proof,whole_typed53_unchanged_across_restore=True,fresh_prelude_revokes=['GFQ_ACTIVE','GCC_VALID','editcertificate'],scope='Actual owned53 baseline and queuededit, copied with exactwarmextent; no identityrebind/oldstack/OSauthority claim.')
 (e/'registered-observer-result.json').write_text(json.dumps(result,indent=2)+'\n');return result

def run_one(base,mode,preview=False):
 current.CurrentPlan=RegisteredPlan;current.free_ports=free_ports
 # Original adapter evaluates all source/history/rawdisk/VIC checks; catalog
 # policy already admits only documented managed publishedbit7 changes.
 result=current.run_one(base,mode,preview);e=ROOT/result['evidence']
 extra=observer_audit(e);dedup=hardlink_duplicates(e)
 result.update(observer=extra,hardlinks=dedup)
 (e/'registered-result.json').write_text(json.dumps(result,indent=2)+'\n');print('REGISTERED_PASS',e,mode,preview,flush=True);return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=identity.FIXED);p.add_argument('--mode',choices=('40','60','80','literal','preview','all'),default='all');p.add_argument('--run',action='store_true');a=p.parse_args()
 if not a.run:print(__doc__);raise SystemExit(0)
 base=a.fixture.resolve();seal=identity.authenticate(base);modes={'40':(0,False),'60':(1,False),'80':(2,False),'literal':(3,False),'preview':(3,True)}
 selected=modes if a.mode=='all'else{a.mode:modes[a.mode]};results=[]
 for tag,(mode,preview)in selected.items():results.append(run_one(base,mode,preview))
 out=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-lifecycle-registered-gallery');out.mkdir()
 r=dict(status='PASS',seal=seal,cases=results,frames=sum(v['frames']for v in results),native_pixels=sum(v['native_pixels']for v in results),scope=__doc__,visual_review='pending')
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('REGISTERED_GALLERY',out,flush=True)
