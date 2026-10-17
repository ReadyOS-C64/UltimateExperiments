from pathlib import Path
import json,hashlib,os,re,shutil,time
from cold_session import FrozenSources,durable,native_contract
from cold_entry import ColdEntry,ACTIVE_SHA
from copy_reader_host import Source as ReaderSource
from directory_host import DirectorySource
from copy_transport import CopyREST
from copy_session import CopySession
from process_context import ProcessContext,physical_context,local_context,Ledger,EvidenceWriter
from transport import FIELDS
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
SCHEMA='OWNED_COPY20M_PHYSICAL_PURPOSE_1';SCOPE='OWNED_COPY20M_READONLY_VERIFICATION'
READER='9ab9324f412194a66478a12ef6cba86f1247396eeed3aec7004ea21e9760a1c9';DIRECTORY='9901c211d0104ed8a233068e2c5e07d9b93e1285a92431b30a49d2123501e497';EXPECTED='78b941711081e5ee8b1e2855b1ca4d4876160f97a5dfdb1e475fa65a699d102c';BASELINE='ac43c06b5e23774b298011c1a97bfbc72eb8395020465c747b135a83e9cd3eb3'
def audit(m):
 for n,h in m['files'].items():
  if sha(n)!=h:raise ValueError('Frozen source/authority changed '+n)
 return len(m['files'])
def sources(m):
 streams={role:(Path(v['source']).read_bytes(),bytes.fromhex(Path(v['nonce']).read_text()))for role,v in m['streams'].items()};root=m['home'].encode('ascii');nonce=bytes.fromhex(m['purpose_nonce']);rp=Path(m['reader']).read_bytes();rl=Path(m['reader_labels']).read_text();dp=Path(m['directory']).read_bytes();dl=Path(m['directory_labels']).read_text()
 return streams,DirectorySource(dp,dl,DIRECTORY,sha(m['directory_labels']),root,nonce),ReaderSource(rp,rl,READER,sha(m['reader_labels']),root,nonce)
def preflight(m,local=False):
 if m.get('schema')!=('OWNED_COPY20M_LOCAL_TEST_1'if local else SCHEMA)or m.get('scope')!=SCOPE or m.get('owner')!='cia_probe_independent_review'or m.get('host')!='10.0.0.79'or m.get('identity')!=FIELDS:raise ValueError('Exact owned-copy device/scope')
 for k,v in {'core_seconds':600,'activation_seconds':90,'cold_cleanup_seconds':90,'config_cleanup_seconds':45,'watchdog_seconds':900,'interrupt_grace_seconds':120,'source_chunk_bytes':128,'source_load_seconds':15,'final_capture_reserve_seconds':120,'before_reader_reserve_seconds':180,'file_bytes':20971520,'file_frames':640,'file_READ04_count':40961,'COPY0B_count':1,'CREATE_DIR16_count':1,'OWNER_bytes':52,'directory_native_commands':14,'header_poll_max':8192,'request_max':30000,'configuration_PUT_max':2,'full_snapshots':2,'healthy_snapshot_full_GETs':258,'healthy_snapshot_ACKs':256}.items():
  if type(m.get(k))is not type(v)or m[k]!=v:raise ValueError('Exact finite bound '+k)
 for k in ['FTP','POST','REU_write','native3880_restore','fullboard_reset','upper12MiB_access','upper12MiB_byte_equality','API_config_repair','original_CPU_restore','original_RAM_restore','original_application_resume','automatic_retry','guest_execution','SETUP_CONFIG_execution','Turbo_execution','physical_Finish','full_V1_acceptance','fresh_remote_file_bytes_before_COPY_verified']:
  if m.get(k)is not False:raise ValueError('Forbidden capability/claim '+k)
 if m.get('ROOT_review_required_before_dispatch')is not True or m.get('historical_source_path')!='/usb1/DOS64_TEST/ac-media-20261016-081300/DOSHD.IMG'or m.get('destination_leaf')!='DOSHD.IMG'or m.get('cold_entry')!='EXACT_OWNED_FAILED_STREAM_OR_FRESH_BASIC':raise ValueError('Fixed readonly historical path and cold entry')
 audit(m)
 needed=['baseline','expected_file','reader','reader_labels','directory','directory_labels','template','stream_labels','predecessor','predecessor_terminal','predecessor_stream','reader_parent_manifest','reader_peer_manifest','directory_parent_manifest','root_component_receipt']
 for k in needed:
  if m[k]not in m['files']:raise ValueError('Unpinned consumed source/authority '+k)
 for role in m['streams'].values():
  for p in role.values():
   if p not in m['files']:raise ValueError('Unpinned streamsource/nonce')
 if sha(m['reader'])!=READER or sha(m['directory'])!=DIRECTORY or sha(m['expected_file'])!=EXPECTED or Path(m['expected_file']).stat().st_size!=20971520 or sha(m['baseline'])!=BASELINE:raise ValueError('Exact native/disk/baseline bytes')
 if set(m['streams'])!={'initial','final'}or len(m['purpose_nonce'])!=32 or not re.fullmatch('[0-9a-f]{32}',m['purpose_nonce']):raise ValueError('Exact distinct role nonces')
 streams,directory,reader=sources(m);contracts={role:native_contract(Path(m['template']).read_bytes(),v[0],Path(m['stream_labels']).read_text(),v[1])for role,v in streams.items()}
 if len({v[1]for v in streams.values()}|{bytes.fromhex(m['purpose_nonce'])})!=3:raise ValueError('Distinct purpose/snapshot nonces')
 ColdEntry(Path(m['predecessor']).read_bytes(),Path(m['predecessor_terminal']).read_bytes(),Path(m['predecessor_stream']).read_bytes())
 if Path(m['active']).read_bytes()!=Path(m['predecessor']).read_bytes()or sha(m['predecessor'])!=ACTIVE_SHA:raise ValueError('Current sole-owner predecessor changed')
 old=json.loads(Path(m['predecessor']).read_text())
 if not local:
  for key in ['owned_child_pid','owned_supervisor_pid']:
   pid=old.get(key)
   if isinstance(pid,int)and pid>0:
    try:os.kill(pid,0)
    except ProcessLookupError:pass
    else:raise ValueError('Prior owned process stilllive')
 w=Path(__file__).resolve().parent;run=Path(m['run']);runs=Path(m['runs_root'])
 if not local:
  b=w.parents[2]
  for k,path in {'entry':w/'launch.py','detached':w/'detached','dispatch_claim':w/'dispatch-claim','supervisor_pidfile':w/'supervisor.pid','active':b/'ACTIVE_HARDWARE_SESSION.json','runs_root':b/'runs'}.items():
   if Path(m[k])!=path:raise ValueError('Exact owned detached path '+k)
 if not run.is_absolute()or run.parent!=runs or run.name!=m['run_id']or not run.name.startswith('c64u-ownedcopy20m-')or run.exists():raise ValueError('Fresh owned output only')
 return {'pins':len(m['files']),'streams':contracts,'directory_source_sha256':hashlib.sha256(directory.configured).hexdigest(),'reader_source_sha256':hashlib.sha256(reader.configured).hexdigest(),'source_chunks':{'initial':36,'directory':91,'reader':103,'final':36},'no_device_calls':True,'scope':SCOPE,'remote_source_content_currently_unverified':True,'no_guest_authority_until_full20MiB_and_known_close':True}
class PurposeWire(CopyREST):
 def __init__(self,*a,ledger,**kw):super().__init__(*a,**kw);self.ledger=ledger
 def control(self,kind,key,end):
  if key=='start_resume'or key.endswith('_start_resume'):self.ledger.write(status='OWNED_COPY20M_NATIVE_ENTRY_PENDING',possible_native_execution=True,active_application=True,possible_native_FILES_writer=self.role in['directory','reader'])
  return super().control(kind,key,end)
def execute(m,ctx,wire_factory,clock=time.monotonic,sleep=time.sleep,session_class=CopySession):
 if not isinstance(ctx,ProcessContext):raise ValueError('Validated process context required')
 ctx.check(m);preflight(m,local=not ctx.physical);run=Path(m['run']);run.mkdir();ledger=Ledger(m,ctx);first=None;session=None;wire=None;result={'status':'failed','scope':SCOPE,'physical':ctx.physical,'hardware_reserved':True,'copy_content_authority':False,'guest_execution':False,'REU_write_operations':0,'upper12MiB_access':False,'upper12MiB_byte_equality':False,'original_CPU_RAM_application_restored':False}
 def latch(e):
  nonlocal first
  if first is None:first=e
 try:
  cp=run/'source-copies';cp.mkdir();records={}
  for i,(name,h)in enumerate(m['files'].items()):
   q=cp/(str(i)+'-'+Path(name).name);shutil.copyfile(name,q)
   if sha(q)!=h:raise ValueError('Retained source copy differs')
   records[name]={'copy':str(q),'sha256':h}
  durable(run/'SOURCE_BEFORE.json',(json.dumps(records,indent=2)+'\n').encode());audit(m);ledger.write(status='OWNED_COPY20M_PREFLIGHT',current_host_job_live=True,first_error=None)
  streams,directory,reader=sources(m);contracts={role:native_contract(Path(m['template']).read_bytes(),v[0],Path(m['stream_labels']).read_text(),v[1])for role,v in streams.items()};baseline=Path(m['baseline']).read_bytes();expected=Path(m['expected_file']).read_bytes();wire=wire_factory(streams,directory,reader,expected,ledger)
  entry=ColdEntry(Path(m['predecessor']).read_bytes(),Path(m['predecessor_terminal']).read_bytes(),Path(m['predecessor_stream']).read_bytes());session=session_class(wire,streams,baseline,run/'session',contracts=contracts,entry=entry,audit=FrozenSources(m['files']),clock=clock,sleep=sleep,writer=EvidenceWriter(ledger));core=session.run();result['library_report']=core
  if wire.stream_done!={'initial','final'}or wire.global_full!=258 or wire.global_acks!=256 or wire.directory_receipt is None or wire.reader_receipt is None or not wire.files_quiet or wire.reader_next!=641 or len(wire.reader_go)!=640:raise ValueError('Complete private file/snapshot/quiet ledger required')
  if(run/'session/DOSHD-independent20MiB.img').read_bytes()!=expected:raise ValueError('Durable whole20MiB mismatch')
  result.update(status='passed',copy_content_authority=True,whole_lower4MiB_equal_before_after=True,clone_path=m['home']+'/DOSHD.IMG',clone_sha256=EXPECTED,known_FILES_closed=True,first_error=None)
 except BaseException as e:latch(e)
 finally:
  if session is not None:result['library_report']=getattr(session,'report',None)
  try:
   audit(m)
   if(run/'SOURCE_BEFORE.json').exists():
    record=json.loads((run/'SOURCE_BEFORE.json').read_text())
    for row in record.values():
     if sha(row['copy'])!=row['sha256']:raise ValueError('Retained source drift')
    durable(run/'SOURCE_AFTER.json',(json.dumps(record,indent=2)+'\n').encode())
   result['source_closure_passed']=True
  except BaseException as e:latch(e);result['source_closure_passed']=False
  if first is not None:result.update(status='failed',first_error=repr(first),first_type=type(first).__name__,copy_content_authority=False)
  report=result.get('library_report')or{};cleanup=report.get('cleanup')or{};basic=all(cleanup.get(k)for k in ['cold_reset_ack','BASIC_ready_observed','resume_ack']);result['physical_acceptance']='PENDING_ROOT_RECEIPT_REVIEW'if result['status']=='passed'and ctx.physical else'NOT_ACCEPTED'
  if ledger.claimed:
   try:ledger.write(status='OWNED_COPY20M_COMPLETE_PENDING_ROOT_REVIEW'if result['status']=='passed'else'OWNED_COPY20M_FAILED_RESERVED',current_host_job_live=False,source_freeze_active=False,first_error=result.get('first_error'),physical_result=str(run/'final-result.json'),active_application=not basic,possible_native_execution=not basic,possible_native_FILES_writer=not(wire.files_quiet if wire else True),known_FILES_quiet=wire.files_quiet if wire else False,cold_BASIC_cleanup_acknowledged=basic,settings_media_equal=cleanup.get('settings_media_equal',False),copy_content_authority=result['copy_content_authority'],whole_lower4MiB_equal_before_after=result.get('whole_lower4MiB_equal_before_after',False),hardware_reserved=True)
   except BaseException as e:latch(e);result.update(status='failed',first_error=repr(first),copy_content_authority=False,physical_acceptance='NOT_ACCEPTED')
  try:durable(run/'final-result.json',(json.dumps(result,indent=2)+'\n').encode())
  except BaseException as e:
   latch(e);result.update(status='failed',first_error=repr(first),copy_content_authority=False,physical_acceptance='NOT_ACCEPTED')
   if ledger.claimed:
    try:ledger.write(status='OWNED_COPY20M_FAILED_RESERVED',first_error=repr(first),copy_content_authority=False,physical_result_durable=False,hardware_reserved=True)
    except BaseException:pass
  if first is not None:
   try:durable(run/'terminal-failure.json',(json.dumps(result,indent=2)+'\n').encode())
   except BaseException:pass
 if first is not None:raise first
 return result
def live(m,ctx):
 if not isinstance(ctx,ProcessContext)or not ctx.physical:raise ValueError('Validated detached physical context required')
 import http.client
 return execute(m,ctx,lambda streams,directory,reader,expected,ledger:PurposeWire(m['host'],streams,directory,reader,expected,ledger=ledger,factory=http.client.HTTPConnection))
