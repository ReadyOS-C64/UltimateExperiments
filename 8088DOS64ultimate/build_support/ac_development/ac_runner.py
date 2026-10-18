#!/usr/bin/env python3
# Source-only before every private/project import.
import sys
from pathlib import Path
_cache=Path(__file__).resolve().parent/'.source-import-cache-disabled'
if _cache.exists():raise RuntimeError('Source-only cache path must remain absent')
sys.dont_write_bytecode=True;sys.pycache_prefix=str(_cache)
import bootstrap
import argparse,json,ipaddress,time
from types import SimpleNamespace
from ac_contract import Registration,read_json,sha,SERVICE_SHA
from ac_application import CollectionApplication
from ac_helper import configure_helper,parse_labels,HelperLoadThenSys,CompositeClient
from ac_load_then_sys import ACLoadThenSysClient
from ac_retention import ACRetention,ftp_snapshot,read_ftp
from c64u_native_file_runner import clock_evidence
from c64u_native_file_recovery import DeadlineClient,Budget
from c64u_ftp_put_transport import FtpPutClient
from c64u_bulk_reu_recovery import dump
from game_recovery import DeadlineDeltaService
from batched_delta_recovery import BatchedDeadlineDeltaService
from game_full_recovery import run_with_recovery
from game_cancellation import recover_honestly
from game_launch_application import application_with_launch_evidence
HERE=Path(__file__).resolve().parent;PROJECT=bootstrap.PROJECT

def connect_factory(host):
 def connect(seconds):
  import ftplib
  ftp=ftplib.FTP()
  try:ftp.connect(host,21,timeout=seconds);ftp.login('anonymous','anonymous@');return ftp
  except BaseException:
   try:ftp.close()
   except BaseException:pass
   raise
 return connect

def validate(args,unstaged=False):
 args=SimpleNamespace(**args) if isinstance(args,dict) else args
 ipaddress.IPv4Address(args.host)
 output=Path(args.output).resolve()
 if not output.is_relative_to(PROJECT/'agentworking/runs') or output.exists():raise ValueError('Fresh project-owned application output required')
 registration=Registration(args.proof,args.proof_sha,read_json(args.artifacts) if getattr(args,'artifacts',None) else None)
 media=read_json(args.media_manifest);floppy=Path(args.floppy).read_bytes();hd=Path(args.hd).read_bytes();configured,patch=registration.configure(media,floppy,hd)
 service=Path(args.service).read_bytes()
 if sha(service)!=SERVICE_SHA:raise ValueError('Original40fe recovery service required')
 helper_manifest=read_json(bootstrap.HELPER_BUILD/'source-manifest.json')
 for name,meta in helper_manifest['inputs'].items():
  b=Path(name).read_bytes()
  if len(b)!=meta['bytes'] or sha(b)!=meta['sha256']:raise ValueError('Reviewed helper source/build input differs: '+name)
 helper_base=Path(args.helper_prg).read_bytes();helper_blob=Path(args.helper_labels).read_bytes()
 if sha(helper_base)!=helper_manifest['prg_sha256'] or sha(helper_blob)!=helper_manifest['labels_sha256']:raise ValueError('Exact source-built disabled helper/labels required')
 helper_prg,helper_labels,helper_patch=configure_helper(helper_base,helper_blob,media['files']['hd']['native_path'])
 pal=clock_evidence(args.pal_clock_evidence);app=CollectionApplication(registration,configured,patch,floppy,hd,media,service)
 client=None;stage=None;helper_stage=None
 if not unstaged:
  stage=read_json(args.staging_manifest);helper_stage=read_json(args.helper_staging_manifest)
  delegate=FtpPutClient(DeadlineClient(args.host),stage,{'native':configured,'recovery':service},app.base)
  from ac_helper_staging import validate_helper_stage
  helper_path=validate_helper_stage(helper_stage,helper_prg)
  native=ACLoadThenSysClient(delegate,registration,configured,patch,media,floppy,hd,clock=app.clock,sleep=app.sleep)
  helper=HelperLoadThenSys(delegate,helper_prg,helper_path,helper_patch,base=helper_base,labels_blob=helper_blob,clock=app.clock,sleep=app.sleep);client=CompositeClient(native,helper)
 pins=dict(registration.pins)
 for item in media['files'].values():
  q=Path(item['source_path']);body=q.read_bytes()
  if len(body)!=item['source_bytes'] or sha(body)!=item['source_sha256']:raise ValueError('Original staged source identity changed')
  pins[str(q.resolve())]=sha(body)
 if media.get('adopted_prior_failed_staging'):
  prior=Path(media['adopted_prior_failed_staging']);adoption=Path(args.media_manifest).parent/media['adoption_report'];record=read_json(adoption)
  if media.get('independent_complete_readback') is not True or record.get('status')!='passed' or record.get('prior_failure_preserved') is not True or record.get('prior_failed_record_sha256')!=sha(prior.read_bytes()):raise ValueError('Explicit complete read-only adoption chain differs')
  for role,digest in [('OWNER',media['marker_sha256']),('floppy',sha(floppy)),('hd',sha(hd))]:
   if record['files'][role].get('passed') is not True or record['files'][role]['sha256']!=digest:raise ValueError('Adoption complete byte receipt differs')
  pins[str(prior.resolve())]=sha(prior.read_bytes());pins[str(adoption.resolve())]=sha(adoption.read_bytes())
 for name,meta in helper_manifest['inputs'].items():pins[str(Path(name).resolve())]=meta['sha256']
 for registry in [stage,helper_stage]:
  if registry:
   for item in registry['files'].values():
    q=Path(item['source_path']);body=q.read_bytes()
    if len(body)!=item['bytes'] or sha(body)!=item['sha256']:raise ValueError('Staged local source changed before freeze')
    pins[str(q.resolve())]=sha(body)
 for value in vars(args).values():
  if isinstance(value,str) and Path(value).is_file():pins[str(Path(value).resolve())]=sha(Path(value).read_bytes())
 pins[str((bootstrap.HELPER_BUILD/'source-manifest.json').resolve())]=sha((bootstrap.HELPER_BUILD/'source-manifest.json').read_bytes())
 return app,client,pal,pins,helper_prg,helper_labels,helper_patch,stage,helper_stage

def prepare(args,destination):
 app,client,pal,pins,helper,labels,patch,stage,hstage=validate(args,unstaged=True);out=Path(destination).resolve()
 if out.exists() or not out.is_relative_to(PROJECT/'agentworking'):raise ValueError('Fresh private preparation directory required')
 out.mkdir();(out/'NATIVE-DOS.PRG').write_bytes(app.prg);(out/'REU-RECOVERY.PRG').write_bytes(app.service_prg);(out/'HD-CLOSE.PRG').write_bytes(helper)
 dump(out/'prepared.json',{'purpose':'genuine-A-plus-C20MiB-development','hardware_executed':False,'native_sha256':sha(app.prg),'service_sha256':sha(app.service_prg),'helper_sha256':sha(helper),'patch':app.patch,'helper_patch':patch,'native_diag':app.base,'target_purpose_proof_sha256':app.registration.proof_sha});return app

def verify_stage_FTP(connect,app,stage,hstage,output,expected_HD=None):
 budget=Budget(app.clock,180);out=Path(output);raw=ftp_snapshot(connect,app.media,app.data,out,budget)
 if raw!=(app.hd_source if expected_HD is None else expected_HD):raise ValueError('Complete independent20MiB FTP identity differs')
 with connect(min(5,budget.remaining())) as ftp:
  for registry in [stage,hstage]:
   marker=read_ftp(ftp,registry['remote_directory']+'/OWNER.JSON',4096,budget)
   if sha(marker)!=registry['marker_sha256']:raise ValueError('Owned staged PRG marker changed')
   for item in registry['files'].values():
    body=read_ftp(ftp,item['remote_path'],item['bytes']+1,budget)
    if len(body)!=item['bytes'] or sha(body)!=item['sha256']:raise ValueError('Complete staged PRG readback changed')
 return {'passed':True,'full20MiB_HD_sha256':sha(raw),'all_PRGs_and_both_owner_markers_exact':True,'independent_new_FTP_connections':True}

def run(args,guard_path,guard_sha):
 from ac_freeze import verify_guard
 guard=verify_guard(guard_path,guard_sha,args)
 app,client,pal,pins,helper,labels,hpatch,stage,hstage=validate(args)
 if any(read_json(args[k]).get('offline_validation_fixture') is True for k in ['media_manifest','staging_manifest','helper_staging_manifest']):raise ValueError('Offline validation registry cannot execute hardware')
 connect=connect_factory(args['host']);output=Path(args['output']);pre=HERE/'launch-preflight'
 # Run-owned preflight output is a distinct new path; application directory must remain absent for b017.
 pre=output.with_name(output.name+'-FTP-before')
 if pre.exists():raise ValueError('Fresh independent FTP preflight directory required')
 pre.mkdir();verify_stage_FTP(connect,app,stage,hstage,pre/'HD-source.img')
 retention=ACRetention(app,connect,helper,labels)
 def factory(adapter,prg,journal):
  adapter.journal=journal;dump(output/'reviewed-AC-guard.json',guard);dump(output/'reviewed-inputs-before.json',pins);dump(output/'PAL-evidence.json',pal)
  return BatchedDeadlineDeltaService(adapter,prg,journal,clock=app.clock,sleep=app.sleep)
 result,interruption=recover_honestly(run_with_recovery,output,client,app.service_prg,application=application_with_launch_evidence(app),service_factory=factory,restore_attempts=2,pre_restore_evidence=retention)
 # The reviewed b017 orchestrator is unchanged; its generic no-media-write statement applies only to its REU backend.
 result['workflow']='owned A+C development; realDOS/TPC/BASIC/COPY, nativeHDclose/reopen, exhaustiveREU recovery'
 result['recovery_backend_scope']='Original40fe/b017 REU restoration performs no persistent media writes. Application writes only fresh owned DOSHD.IMG; that changed image is retained and not rolled back.'
 result['limitations']=[x for x in result.get('limitations',[]) if x!='No persistent media or UCI writes; REST is development control only']
 if interruption is None:interruption=retention.interruption
 try:
  if retention.final_HD is None:raise ValueError('No complete changed HD authority retained')
  result['post_recovery_FTP']=verify_stage_FTP(connect,app,stage,hstage,output/'HD-independent-after-outer-recovery.img',retention.final_HD)
 except BaseException as error:
  result['status']='failed';result['post_recovery_FTP_error']=repr(error)
  if interruption is None:interruption=error
 try:
  changed=[name for name,digest in guard['files'].items() if not Path(name).is_file() or sha(Path(name).read_bytes())!=digest['sha256']]
  result['source_closure_after']={'passed':not changed,'changed':changed}
  if changed:raise ValueError('Frozen source/artifact closure changed through recovery')
 except BaseException as error:
  result['status']='failed';result['source_closure_error']=repr(error)
  if interruption is None:interruption=error
 # Keep the original cancellation/error authoritative if evidence cleanup is
 # interrupted. These are bounded local writes, never remote-command retries.
 for attempt in range(1,4):
  try:dump(output/'result.json',result);break
  except BaseException as error:
   result['status']='failed';result.setdefault('outer_report_errors',[]).append({'error':repr(error),'type':type(error).__name__})
   if interruption is None:interruption=error
 if interruption is not None:raise interruption.with_traceback(interruption.__traceback__)
 return result

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--arguments',required=True);p.add_argument('--validate-only',action='store_true');p.add_argument('--prepare-only');p.add_argument('--guard');p.add_argument('--guard-sha')
 a=p.parse_args(argv);args=read_json(a.arguments)
 if a.prepare_only:prepare(args,a.prepare_only);print('prepared offline');return 0
 if a.validate_only:app,*rest=validate(args);print(json.dumps({'status':'validated-offline','configured_sha256':sha(app.prg),'hardware_executed':False}));return 0
 if not a.guard or not a.guard_sha:p.error('Concrete reviewed exact guard/hash required before hardware')
 result=run(args,a.guard,a.guard_sha);print(json.dumps({k:result.get(k) for k in ['status','reu_restored','configuration_restored','reset_resumed']}));return int(result['status']!='passed')
if __name__=='__main__':raise SystemExit(main())
