#!/usr/bin/env python3
import sys
from pathlib import Path
_cache=Path(__file__).resolve().parent/'.source-import-cache-disabled'
if _cache.exists():raise RuntimeError('Source-only cache path must remain absent')
sys.dont_write_bytecode=True;sys.pycache_prefix=str(_cache)
import bootstrap,json,argparse
from ac_contract import sha,read_json
HERE=Path(__file__).resolve().parent
PURPOSE='genuineDOS33-A-plus-C20MiB-physical-development'
def freeze(arguments,output):
 from ac_runner import validate
 args=read_json(arguments);app,client,pal,pins,helper,labels,hpatch,stage,hstage=validate(args)
 if any(read_json(args[k]).get('offline_validation_fixture') is True for k in ['media_manifest','staging_manifest','helper_staging_manifest']):raise ValueError('Concrete real staging required for launch freeze')
 for f in list(HERE.glob('*.py'))+[HERE/'DEPENDENCIES.json']+[bootstrap.HELPER/'close_reopen.s',bootstrap.HELPER/'link.cfg',bootstrap.HELPER_BUILD/'close-reopen.prg',bootstrap.HELPER_BUILD/'close-reopen.labels',bootstrap.HELPER_BUILD/'source-manifest.json',Path(arguments),Path(sys.executable).resolve()]:pins[str(f.resolve())]=sha(f.read_bytes())
 for module in list(sys.modules.values()):
  f=getattr(module,'__file__',None)
  if f:
   q=Path(f).resolve()
   if q.suffix=='.py' and q.is_relative_to(bootstrap.PROJECT):pins[str(q)]=sha(q.read_bytes())
 result={'schema':1,'purpose':PURPOSE,'host':args['host'],'output':str(Path(args['output']).resolve()),'arguments':args,'configured_runtime_sha256':sha(app.prg),'configured_helper_sha256':sha(helper),'native_purpose_proof_sha256':app.registration.proof_sha,'original_recovery_orchestrator_sha256':'b017e4b0854a9e9cf073d7176ea5bc5370c0a9cbfb3d418739ba3644bed3877f','application_seconds':1800,'retention_and_each_REU_recovery_phase_seconds':600,'restore_fullscan_seconds':600,'restore_max_write_batches':4,'restore_batch_chunks_max':64,'restore_each_batch_seconds':600,'restore_total_seconds_max':3000,'compare_separate_full4MiB_seconds':600,'b017_restore_attempts':2,'load_restore_compare_two_attempts_seconds_max':8400,'required_ROOT_process_watchdog_seconds':21600,'batched_recovery_module_sha256':'27f5bd8f9caca58d2d42647ac9b885826eedbecacd8146e4bdcaa2627266b86a','FTP_seconds':180,'source_only_cache_must_remain_absent':str(bootstrap.CACHE_DISABLED),'hardware_executed':False,'files':{name:{'bytes':Path(name).stat().st_size,'sha256':digest} for name,digest in sorted(pins.items())}}
 if sha((HERE/'game_full_recovery.py').read_bytes())!=result['original_recovery_orchestrator_sha256']:raise ValueError('Reviewed b017 controlflow changed')
 if Path(output).exists():raise ValueError('Fresh concrete guard output required')
 Path(output).write_text(json.dumps(result,indent=2)+'\n');return result

def verify_guard(path,digest,args):
 body=Path(path).read_bytes()
 if sha(body)!=digest:raise ValueError('Explicit reviewed exact guard hash differs')
 r=json.loads(body)
 if r.get('purpose')!=PURPOSE or r.get('arguments')!=args or r['host']!=args['host'] or r['output']!=str(Path(args['output']).resolve()) or Path(args['output']).exists():raise ValueError('Exact guard arguments/host/fresh output differ')
 if Path(r['source_only_cache_must_remain_absent']).exists():raise ValueError('Source-only import cache path exists')
 for name,want in r['files'].items():
  f=Path(name)
  if not f.is_file() or f.stat().st_size!=want['bytes'] or sha(f.read_bytes())!=want['sha256']:raise ValueError('Frozen source/artifact changed: '+name)
 for module in list(sys.modules.values()):
  f=getattr(module,'__file__',None)
  if f:
   q=Path(f).resolve()
   if q.is_relative_to(bootstrap.PROJECT) and q.suffix in ('.py','.pyc'):
    if q.suffix=='.pyc' or str(q) not in r['files']:raise ValueError('Unpinned project import executed: '+str(q))
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--arguments',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=freeze(a.arguments,a.output);print(json.dumps({'guard_sha256':sha(Path(a.output).read_bytes()),'pins':len(r['files']),'hardware_executed':False}))
