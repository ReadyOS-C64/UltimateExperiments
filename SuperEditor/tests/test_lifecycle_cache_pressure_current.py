"""Current54 CPU pressure audit: genuine semantic53+FC, modal refusal/recovery.

Actual packaged root/allocator/lifecycle calls; KERNAL file channels use the
released explicit filesystem model. No native IEC/IRQ/ReadyOS claim. Frozen
source and exact typed-owner banks are authoritative; no generic REU mask.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,zipfile
import test_capacity_lifecycle as parent
import test_lifecycle_cache_current as cache
ROOT=parent.ROOT;geos=parent.geos
BASE=ROOT/'build/cache-editor-product/20261026T033702424844Z/fixture'

def run(out,base,banks):
 out.mkdir(parents=True);frozen,identity=geos.freeze(out,base)
 assert len(identity['names'])==54 and identity['names'][-1]=='line'
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=parent.runner(out);f=parent.Fixture(out,frozen,dll,True);stages=[];catalog=None
 data=geos.native_text('# Capacity\rOrdinary text for copying.\r:::basic\r10 PRINT "Hi"\r:::\r:::region Work\rHidden text.\r:::end\rTail.\r')
 def state(tag):
  nonlocal catalog
  current=f.catalog()
  if catalog is None:catalog=current
  else:assert current==catalog,'catalog identity changed'
  v={n:f.get(n,w)for n,w in [('se_f_owner',1),('se_e_ui',1),('se_f_error',1),('se_e_error',1),('se_fd_confirm',1),('se_h_current',4),('se_h_saved',4),('se_hot_pending',1),('se_bc_flags',1),('se_bc_count',1)]}
  v.update(tag=tag,banks_peak=dll.ca_info(0),objects_peak=dll.ca_info(1),owner_stores=dll.ca_info(2),owners=f.read(f.s['se_reu_physical_owner'],banks).hex(),objects=f.read(f.s['object_owner'],8).hex());stages.append(v);print('STATE',v,flush=True);return v
 def snap(tag):
  ram=f.read(0,65536);reu=f.reu()[:banks*65536]
  (out/(tag+'-ram.bin')).write_bytes(ram);(out/(tag+'-reu.bin')).write_bytes(reu)
  return ram,reu
 def quiet():
  assert not any(f.get(n,1)for n in('se_e_job','se_f_owner','se_doc_read_locks','se_fs_owned'))
  assert f.read(0xc600,1024)==f.shim
 def stable():
  source=f.merged();canon=f.canonical();name=f.read(f.s['se_f_current_name'],18)
  return source,canon,name
 def unchanged(before):assert stable()==before,'source/history/selection/current filename changed on refused operation'
 try:
  geos.grid.Fixture.source(f,data,banks=1,physical=banks);assert not f.call('se_clip_init').p&1
  dll.ca_config(f.s['se_reu_physical_owner'],f.s['object_owner']);dll.ca_baseline(f.m.handle)
  f.typed(geos.native_text('syntax markdown'));f.command(99);f.render();quiet()
  state('semantic-baseline');arena,payload=cache.cache_frame(f.s,f.read(0,65536),f.reu(),frozen/'build/overlays')
  assert f.get('se_bc_flags',1)&15==1 and f.get('se_bc_count',1)==0 and arena['merged_length']==len(data)
  f.position(0);f.command(68)
  for _ in range(5):f.command(2)
  f.command(69);f.key(3);assert f.get('se_clip_length')==5
  f.command(115);f.render();quiet();state('clip-fold-arena-FE-fonts')
  digest=bytes.fromhex(json.loads((frozen/'build/editor-report.json').read_text())['resident_binding']['digest'])
  f.m.load(0x800,digest+bytes(0x40));image=(frozen/'build/overlays/lifectrl.seo').read_bytes();f.m.load(0xa00,image[36+0x800:36+0x900]);f.put('se_e_redraw',0,1)
  r,n=f.lc(0);assert not r.p&1 and r.a==1
  steps=0
  while r.a:
   r,n=f.lc(1);steps+=1;assert not r.p&1 and steps<400
  assert steps==381
  fc=f.m.read(0x810);phys=f.m.read(f.s['se_reu_map']+fc);assert f.m.read(f.s['se_reu_physical_owner']+phys)==0xfc
  fc_bytes=f.reu()[phys*65536:(phys+1)*65536]
  r,n=f.lc(2);assert not r.p&1;quiet();state('retained-FC')
  f.command(96);f.position(5);f.key(geos.native_text('Q')[0]);data=data[:5]+geos.native_text('Q')+data[5:]
  f.start(operation='A');f.enter_name(b'CAPOUT');f.key(13);assert f.fs[b'CAPOUT']==data;quiet();state('saved-with-FC')
  f.fs[b'REOPEN']=data;f.start(operation='O');f.enter_name(b'REOPEN');before=stable();ram,reu=snap('open-before');owners=ram[f.s['se_reu_physical_owner']:f.s['se_reu_physical_owner']+banks]
  f.key(13);s=state('open-first-return');snap('open-first-return');unchanged(before)
  # A confirmation is a public modal decision, not a failed allocation. Keep
  # its exact flags/state, then explicitly choose the saved-source discard path.
  if s['se_fd_confirm']:
   assert not s['se_f_error'];f.key(ord('D'));s=state('open-after-confirm');snap('open-after-confirm')
  admitted=not f.get('se_f_owner',1)
  if not admitted:
   assert f.get('se_f_owner',1)==1 and f.get('se_e_ui',1)==3
   assert f.get('se_f_error',1)==0x99,('unexpected modal cause',s)
   unchanged(before);now=f.reu()[:banks*65536]
   for b,owner in enumerate(owners):
    if 2<=owner<255:assert now[b*65536:(b+1)*65536]==reu[b*65536:(b+1)*65536],('rollback owned REU',b,owner)
   assert now==reu,'failed reservation changed actual REU bytes'
   assert f.read(f.s['se_reu_physical_owner'],banks)==owners,'reservation ownership did not roll back'
   f.key(3);quiet();unchanged(before);assert f.reu()[:banks*65536]==reu;state('refusal-cancelled')
   if banks==16:
    # Exact FC release is an explicit embedding capability operation. It
    # frees a bank but not a logical object slot; one free bank still cannot
    # satisfy OPEN's metadata+original pair. Prove the second rollback too.
    r,n=f.fast_call(f.s['se_reu_free'],x=fc);assert not r.p&1
    f.start(operation='O');f.enter_name(b'REOPEN');retry=stable();retry_reu=f.reu()[:banks*65536];retry_owners=f.read(f.s['se_reu_physical_owner'],banks)
    f.key(13);state('retry-one-free-bank');snap('retry-one-free-bank')
    assert f.get('se_f_owner',1)==1 and f.get('se_f_error',1)==0x99
    unchanged(retry);assert f.reu()[:banks*65536]==retry_reu and f.read(f.s['se_reu_physical_owner'],banks)==retry_owners
    f.key(3);quiet();unchanged(retry)
   # Use the real checked R33/TRIM API, not object-table injection. Caller
   # claims owner4 and initializes only that API's idle/proof fields. No live
   # source lease or FILE job coexists. This is not an automatic UI policy.
   authority=f.read(f.s['se_bc_ticket'],8)+f.read(f.s['se_bc_head'],3)
   before_trim=f.reu()[:banks*65536];canon=stable()
   f.put('se_f_owner',4,1);f.m.write(0x8d00+387+8,0);f.m.write(0x8d00+387+39,0);f.put('se_overlay_frame',3,1)
   r,n=f.fast_call(f.s['se_overlay_call'],a=33,x=0);assert not r.p&1 and r.a==0,('actual R33 trim',r.a,r.p)
   f.put('se_f_owner',0,1)
   assert f.read(f.s['se_bc_arena'],5)==bytes(5) and f.get('se_bc_flags',1)&3==2
   assert f.read(f.s['se_bc_ticket'],8)+f.read(f.s['se_bc_head'],3)==authority
   assert f.reu()[:banks*65536]==before_trim;unchanged(canon);quiet();state('checked-optional-arena-trim')
   f.start(operation='O');f.enter_name(b'REOPEN');f.key(13)
   if f.get('se_fd_confirm',1):f.key(ord('D'))
   state('retry-after-trim');assert not f.get('se_f_owner',1),'checked optional trim did not restore admission'
  assert f.merged()==data;quiet();state('open-complete')
  if admitted or banks==32:assert f.reu()[phys*65536:(phys+1)*65536]==fc_bytes,'successful OPEN changed retained FC'
  f.position(5);f.key(geos.native_text('R')[0]);assert f.merged()==data[:5]+geos.native_text('R')+data[5:]
  f.command(16);assert f.merged()==data;quiet();state('edit-undo-after-open')
  result=dict(status='passed',identity=identity,physical_banks=banks,actual_REU_bytes=banks*65536,typed53=arena,FC_capture_steps=steps,first_open_admitted=admitted,whole_actual_REU_refusal_rollback=True,catalog_identity_preserved=True,stages=stages,scope=__doc__,wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except Exception:
  state('failure');snap('failure');raise
 finally:
  (out/'stages.json').write_text(json.dumps(stages,indent=2)+'\n');f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--banks',type=int,choices=[16,32],required=True);a=p.parse_args()
 out=ROOT/'build/lifecycle-cache-pressure-current'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.banks)
