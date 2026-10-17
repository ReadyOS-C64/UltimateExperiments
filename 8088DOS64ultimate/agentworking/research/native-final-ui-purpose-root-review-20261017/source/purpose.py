"""Bounded native SETUP startup/human UI/cancel component, not full installation."""
from pathlib import Path
import json,hashlib,os,re,shutil,time
from cold_session import FrozenSources,durable,native_contract
from bound_release import BoundRelease,NAMES
from cold_entry import ColdEntry,ACTIVE_SHA
from setup_observer import SetupObserver
from close_contract import Contract as CloseContract
from protocol import Source
from history import verify as verify_history
from product_transport import ProductREST
from ui_backend import UIBackend as Backend
from process_context import ProcessContext,physical_context,local_context,Ledger,EvidenceWriter
from transport import FIELDS
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
SCOPE='V1_NATIVE_SETUP_UI_STAGING_AND_ONE_RESTORE'
SCHEMA='V1_NATIVE_SETUP_UI_PHYSICAL_PURPOSE_1'
def audit(m):
 for n,h in m['files'].items():
  if sha(n)!=h:raise ValueError('Frozen source/authority changed '+n)
 return len(m['files'])
def configured(m):
 streams={k:(Path(v['source']).read_bytes(),bytes.fromhex(Path(v['nonce']).read_text()))for k,v in m['streams'].items()}
 contracts={k:native_contract(Path(m['template']).read_bytes(),v[0],Path(m['stream_labels']).read_text(),v[1])for k,v in streams.items()}
 return streams,contracts
def preflight(m,local=False):
 if m.get('schema')!=('V1_NATIVE_SETUP_UI_LOCAL_TEST_1'if local else SCHEMA)or m.get('scope')!=SCOPE or m.get('owner')!='cia_probe_independent_review'or m.get('host')!='10.0.0.79'or m.get('identity')!=FIELDS:raise ValueError('Exact final public nativeSETUP UI purpose')
 for k,v in {'shared_core_seconds':600,'cold_cleanup_seconds':90,'config_cleanup_seconds':45,'watchdog_seconds':900,'interrupt_grace_seconds':120,'source_chunk_bytes':128,'source_load_seconds':15,'full_snapshots':3,'healthy_full_GETs':387,'healthy_stream_ACKs':384,'nonstager_source_chunks':145,'stager_source_chunks':102,'native_jobs':380,'native_restore_attempts':1,'native_READ_count':8192,'native_STORE_count':2048,'stager_REU_start':2097152,'stager_REU_end_exclusive':2113536,'restore_start':0,'restore_end_exclusive':4194304,'configuration_PUT_max':2,'human_window_seconds':120,'restore_reserve_seconds':180,'product_start_reserve_seconds':300,'product_SYS_count':1,'product_registered_LOAD_count':1,'product_header_poll_max':256}.items():
  if type(m.get(k))is not type(v)or m[k]!=v:raise ValueError('Exact finite bound '+k)
 for k in ['POST','FTP','upper12MiB_access','fullboard_reset','API_config_repair','original_CPU_restore','original_RAM_restore','original_application_resume','automatic_retry','live_MAIN_takeover','START_DOS_execution','fresh_remote_backup_before_write_read','second_native_attempt','native_CIA_input_injected','final_V1_acceptance','hidden_preSYS_RAM_verified']:
  if m.get(k)is not False:raise ValueError('Forbidden claim/capability '+k)
 for k in ['ROOT_review_required_before_dispatch','historical_backup_adoption','SETUP_CONFIG_UI_execution','DOS_images_staged']:
  if m.get(k)is not True:raise ValueError('Required explicit capability '+k)
 if m.get('product_leaf')!='SETUP.PRG'or m.get('cold_entry')!='EXACT_OWNED_FAILED_STREAM_OR_FRESH_BASIC'or re.fullmatch('[0-9a-f]{32}',str(m.get('purpose_nonce','')))is None or not int(m['purpose_nonce'],16):raise ValueError('Bound product/predecessor/nonce')
 audit(m)
 for k in ['baseline','service','template','stream_labels','predecessor','predecessor_terminal','predecessor_stream','inventory','observer_binding','intake','stager','stager_labels','main_labels','main_map','parent_observer_manifest','parent_knownC_manifest','root_fast_acceptance']:
  if m[k]not in m['files']:raise ValueError('Unpinned authority '+k)
 for p in list(m['observer_files'].values())+[p for role in m['streams'].values()for p in role.values()]:
  if p not in m['files']:raise ValueError('Unpinned consumed source/nonce '+p)
 if sha(m['inventory'])!=m['inventory_sha256']or sha(m['observer_binding'])!=m['observer_binding_sha256']:raise ValueError('Exact purpose record binding')
 if set(m['streams'])!={'initial','changed','final'}or len({Path(v['nonce']).read_bytes()for v in m['streams'].values()})!=3:raise ValueError('Three distinct source nonces')
 streams,contracts=configured(m)
 stager=Source(Path(m['stager']).read_bytes(),Path(m['stager_labels']).read_text(),m['home'].encode('ascii'))
 if set(m['assets'])!=set(NAMES)or any(p not in m['files']for p in m['assets'].values()):raise ValueError('Exactly15 pinned successor source files')
 release=BoundRelease(Path(m['inventory']).read_bytes(),m['inventory_sha256'],{n:Path(p).read_bytes()for n,p in m['assets'].items()});assets=release.assets(stager.home,bytes.fromhex(m['purpose_nonce']))
 expected=json.loads(Path(m['intake']).read_text())['assets']
 for n,row in expected.items():
  if n not in assets or {'sha256':hashlib.sha256(assets[n]).hexdigest(),'bytes':len(assets[n])}!={k:row[k]for k in ['sha256','bytes']}:raise ValueError('Final public matched asset differs '+n)
 record=Path(m['observer_binding']).read_bytes();observer=SetupObserver(record,m['observer_binding_sha256'],{n:Path(p).read_bytes()for n,p in m['observer_files'].items()})
 if observer.prg!=assets['SETUP.PRG']:raise ValueError('Actual large SETUPsource must match postentry observer')
 CloseContract(assets['DOS64.PRG'],Path(m['main_labels']).read_text(),Path(m['main_map']).read_text(),stager.home+b'/C.IMG') # identity only; no activation/RAM permission
 entry=ColdEntry(Path(m['predecessor']).read_bytes(),Path(m['predecessor_terminal']).read_bytes(),Path(m['predecessor_stream']).read_bytes())
 if Path(m['active']).read_bytes()!=Path(m['predecessor']).read_bytes()or sha(m['predecessor'])!=ACTIVE_SHA:raise ValueError('Current exact sole-owner predecessor changed')
 old=json.loads(Path(m['predecessor']).read_text())
 for key in ['owned_child_pid','owned_supervisor_pid']:
  pid=old.get(key)
  if isinstance(pid,int)and pid>0:
   try:os.kill(pid,0)
   except ProcessLookupError:pass
   else:raise ValueError('Prior owned process stilllive')
 history=verify_history(Path(m['service']).parent,Path(m['baseline']).read_bytes(),Path(m['service']).read_bytes())
 w=Path(__file__).resolve().parent;run=Path(m['run']);runs=Path(m['runs_root'])
 if not local:
  b=w.parents[2]
  for k,path in {'entry':w/'launch.py','detached':w/'detached','dispatch_claim':w/'dispatch-claim','supervisor_pidfile':w/'supervisor.pid','active':b/'ACTIVE_HARDWARE_SESSION.json','runs_root':b/'runs'}.items():
   if Path(m[k])!=path:raise ValueError('Exact detached physical path '+k)
 if not run.is_absolute()or run.parent!=runs or run.name!=m['run_id']or not run.name.startswith('c64u-final-setup-ui-')or run.exists():raise ValueError('Fresh owned output')
 return {'streams':contracts,'historical_backup':history,'stager_configured_sha':hashlib.sha256(stager.configured).hexdigest(),'files':16,'native_jobs':380,'large_load_contract':'trusted registeredfile loadfalse / visible preSYS / nativebankguard / readonlypostentry','hidden_preSYS_RAM_verified':False,'human_CIA_only':True,'final_V1_acceptance':False}

class PurposeWire(ProductREST):
 def __init__(self,*a,ledger,**kw):super().__init__(*a,**kw);self.ledger=ledger
 def stage_exchange(self,io,m,r,end,count=None):
  if m=='PUT'and r=='machine:resume'and io.loaded:self.ledger.write(possible_native_execution=True,active_application=True,status='V1_SETUP_UI_NATIVE_STAGER_POSSIBLY_RUNNING')
  if m=='PUT'and r=='machine:writemem?address=200&data=22':self.ledger.write(possible_stager_REU_write=True,status='V1_SETUP_UI_NATIVE_JOB_PENDING')
  return super().stage_exchange(io,m,r,end,count)
 def control(self,kind,key,deadline):
  if key=='restore_start_resume':self.ledger.write(REU_restoration_attempts=1,possible_lower4M_original_write=True,possible_native_execution=True,active_application=True,status='V1_SETUP_UI_ORIGINAL_RESTORE_PENDING')
  return super().control(kind,key,deadline)

def execute(m,ctx,wire_factory,clock=time.monotonic,sleep=time.sleep):
 if not isinstance(ctx,ProcessContext):raise ValueError('Validated context required')
 ctx.check(m);admission=preflight(m,local=not ctx.physical);run=Path(m['run']);run.mkdir();ledger=Ledger(m,ctx);first=None;session=None;wire=None
 result={'status':'failed','physical':ctx.physical,'scope':SCOPE,'hardware_reserved':True,'SETUP_CONFIG_UI_executed':False,'START_DOS_executed':False,'final_V1_installation_accepted':False,'original_CPU_RAM_application_restored':False,'upper12MiB_access':False,'historical_backup':admission['historical_backup']}
 def latch(e):
  nonlocal first
  if first is None:first=e
 try:
  copies=run/'source-copies';copies.mkdir();record={}
  for i,(n,h)in enumerate(m['files'].items()):
   q=copies/(str(i)+'-'+Path(n).name);shutil.copyfile(n,q)
   if sha(q)!=h:raise ValueError('Copied input differs '+n)
   record[n]={'copy':str(q),'sha256':h}
  durable(run/'SOURCE_BEFORE.json',(json.dumps(record,indent=2)+'\n').encode());audit(m);ledger.write(status='V1_SETUP_UI_STAGING_PREFLIGHT',first_error=None,current_host_job_live=True)
  streams,contracts=configured(m);stager=Source(Path(m['stager']).read_bytes(),Path(m['stager_labels']).read_text(),m['home'].encode());release=BoundRelease(Path(m['inventory']).read_bytes(),m['inventory_sha256'],{n:Path(p).read_bytes()for n,p in m['assets'].items()});assets=release.assets(stager.home,bytes.fromhex(m['purpose_nonce']));observer=SetupObserver(Path(m['observer_binding']).read_bytes(),m['observer_binding_sha256'],{n:Path(p).read_bytes()for n,p in m['observer_files'].items()});entry=ColdEntry(Path(m['predecessor']).read_bytes(),Path(m['predecessor_terminal']).read_bytes(),Path(m['predecessor_stream']).read_bytes());baseline=Path(m['baseline']).read_bytes();wire=wire_factory(streams,Path(m['service']).read_bytes(),baseline,stager,ledger)
  session=Backend(wire,streams,baseline,run/'session',stager=stager,assets=assets,contracts=contracts,release=release,observer=observer,entry=entry,audit=FrozenSources(m['files']),clock=clock,sleep=sleep,writer=EvidenceWriter(ledger));core=session.run();result['library_report']=core
  for n,b in assets.items():
   if(run/'session/actual-files'/n).read_bytes()!=b:raise ValueError('Actual independently retained file differs '+n)
  if wire.stream_done!={'initial','changed','final'}or wire.global_full!=387 or wire.global_acks!=384 or not wire.restore_done or not wire.restore_start_attempted or not wire.stage_closed or wire.product_terminal is None:raise ValueError('Exact snapshot/restore/quiet ledgers')
  if core['stage']['files'].keys()!=assets.keys()or len(session.protocol.records)!=380:raise ValueError('Exact16-file/380-job completion')
  for role,count in [('initial',36),('changed',36),('restore',37),('final',36)]:
   row=wire.source_loads[role]
   if row['ACKs']!=count or row['attempts']!=list(range(count)):raise ValueError('Exact source role PUT ledger')
  source=[v for v in session.stage_io.ledger if v['role']=='configured_source']
  if len(source)!=1 or source[0]['ACKs']!=102 or any(v['ACKs']!=len(v['attempts'])for v in session.stage_io.ledger):raise ValueError('Exact stager source/all-chunk ACK ledger')
  facts=core['callback_report']['facts']
  if not all(facts.get(k)for k in ['original4MiB_verified','native_restore_known_closed','BASIC_cleanup_verified','original_settings_verified']):raise ValueError('Complete RAM/source/settings/BASIC cleanup')
  result.update(status='passed',product_outcome=session.product_result['terminal']['outcome'],native_UI_admission_observed=True,native_human_keys_synthesized=False,final_V1_acceptance=False,native_readback_files=16,whole4MiB_retained_before_changed_after=True,original4MiB_restored_verified=True,known_handles_closed=True,first_error=None)
 except BaseException as e:latch(e)
 finally:
  if session is not None:result['library_report']=getattr(session,'report',None)
  try:
   audit(m)
   if(run/'SOURCE_BEFORE.json').exists():
    record=json.loads((run/'SOURCE_BEFORE.json').read_text())
    for row in record.values():
     if sha(row['copy'])!=row['sha256']:raise ValueError('Retained source copy differs')
    durable(run/'SOURCE_AFTER.json',(json.dumps(record,indent=2)+'\n').encode())
   result['source_closure_passed']=True
  except BaseException as e:latch(e);result['source_closure_passed']=False
  if first is not None:result.update(status='failed',first_error=repr(first),first_type=type(first).__name__)
  core=result.get('library_report')or{};result['SETUP_SYS_resume_attempted']=bool((core.get('product')or{}).get('SYS_resume_attempted'));result['SETUP_CONFIG_UI_executed']=bool((core.get('product')or{}).get('postentry'));facts=(core.get('callback_report')or{}).get('facts',{});cold=facts.get('BASIC_cleanup_verified',False)
  result['physical_acceptance']='PENDING_ROOT_RECEIPT_REVIEW'if result['status']=='passed'and ctx.physical else'NOT_ACCEPTED'
  if ledger.claimed:
   try:ledger.write(status='V1_SETUP_UI_STAGING_COMPLETE_PENDING_ROOT_REVIEW'if result['status']=='passed'else'V1_SETUP_UI_STAGING_FAILED_RESERVED',current_host_job_live=False,source_freeze_active=False,first_error=result.get('first_error'),physical_result=str(run/'final-result.json'),possible_native_execution=not cold,active_application=not cold,original_ac43_verified_restored=facts.get('original4MiB_verified',False),settings_media_equal=facts.get('original_settings_verified',False),cold_BASIC_cleanup_acknowledged=cold,known_stager_handles_closed=wire.stage_closed if wire else False,native_restore_known_closed=core.get('native_known_closed',False),REU_restoration_attempts=int(wire.restore_start_attempted)if wire else 0,hardware_reserved=True)
   except BaseException as e:latch(e);result.update(status='failed',first_error=repr(first),physical_acceptance='NOT_ACCEPTED')
  try:durable(run/'final-result.json',(json.dumps(result,indent=2)+'\n').encode())
  except BaseException as e:
   latch(e);result.update(status='failed',first_error=repr(first),physical_acceptance='NOT_ACCEPTED')
   if ledger.claimed:
    try:ledger.write(status='V1_SETUP_UI_STAGING_FAILED_RESERVED',first_error=repr(first),source_freeze_active=False,hardware_reserved=True)
    except BaseException:pass
  if first is not None:
   try:durable(run/'terminal-failure.json',(json.dumps(result,indent=2)+'\n').encode())
   except BaseException:pass
 if first is not None:raise first
 return result

def live(m,ctx):
 if not isinstance(ctx,ProcessContext)or not ctx.physical:raise ValueError('Validated truly detached physical context required')
 import http.client
 return execute(m,ctx,lambda streams,service,baseline,stager,ledger:PurposeWire(m['host'],streams,service,baseline,stager,ledger=ledger,factory=http.client.HTTPConnection))
