from pathlib import Path
import sys
W=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(W/'.absent-freeze-stage-cache')
if Path(sys.pycache_prefix).exists():raise RuntimeError('Absent source-only cache')
import json,hashlib,http.client,socket
if Path.cwd()!=W:raise RuntimeError('Exact private work cwd')
B=W.parents[2];P=W.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
excluded={'LAUNCH_MANIFEST.json','LAUNCH_SHA.txt'}
files={str(p):sha(p)for p in W.iterdir()if p.is_file()and p.name not in excluded}
for folder in ['assets','close']:
 for p in(W/folder).rglob('*'):
  if p.is_file():files[str(p)]=sha(p)
authority={'root_fast_acceptance':B/'evidence/c64u-fast-put-physical-root-20261017.json','author_stager_manifest':B/'scratch/native-current9-put-stager-20261017/MANIFEST.json','author_fast_manifest':B/'scratch/native-fast-file-put-recovery-runnable-20261017/MANIFEST.json'}
# Full sealed native/component authority plus unchanged historical backup pins.
for p in authority.values():
 files[str(p)]=sha(p)
 if p.name=='MANIFEST.json':
  for name,row in json.loads(p.read_text())['files'].items():
   q=Path(name);q=q if q.is_absolute()else p.parent/q;files[str(q)]=row['sha256']if isinstance(row,dict)else row
for name,row in json.loads((W/'historical-PHYSICAL_MANIFEST.json').read_text())['files'].items():files[name]=row['sha256']
for p in [P/'HANDOFF.md',P/'FIRST_FAILURES.md',P/'SOURCE_DELTA.json',P/'attest_binding.py',B/'HARDWARE_BACKGROUND_EXECUTION.md',Path(sys.executable).resolve(),Path(http.client.__file__).resolve(),Path(socket.__file__).resolve()]:files[str(p)]=sha(p)
for p in files:
 if sha(p)!=files[p]:raise ValueError('Changed authority before freeze '+p)
m={'schema':'CURRENT9_STAGING_PUT_PHYSICAL_PURPOSE_1','scope':'CURRENT9_OWNED_STAGING_THREE_FULL4M_AND_ONE_RESTORE','host':'10.0.0.79','owner':'cia_probe_independent_review','identity':{'product':'C64 Ultimate','firmware_version':'3.14','fpga_version':'121','core_version':'1.47','unique_id':'DCAF71'},'session_id':'17280000000000000000000000000006','purpose_nonce':'17280000000000000000000000000004','run_id':'c64u-current9-stage-20261017-172800','run':str(B/'runs/c64u-current9-stage-20261017-172800'),'runs_root':str(B/'runs'),'active':str(B/'ACTIVE_HARDWARE_SESSION.json'),'predecessor':str(W/'ACTIVE-predecessor.json'),'streams':{r:{'source':str(W/(r+'-stream.prg')),'nonce':str(W/(r+'-NONCE.hex'))}for r in ['initial','changed','final']},'template':str(W/'stream-template.prg'),'stream_labels':str(W/'stream.labels'),'service':str(W/'service.prg'),'baseline':str(W/'BASELINE.reu'),'stager':str(W/'stager.prg'),'stager_labels':str(W/'stager.labels'),'home':'/usb1/DOS64_TEST/current9-live172800','candidate_result':str(W/'CANDIDATE_RESULT.json'),'asset_folder':str(W/'assets'),'assets':{n:str(W/'assets'/n)for n in ['SETUP.PRG','SETUP.FAT','SETUP.PUB','CONFIG.PRG','START.TPL','START.REL','START.INO','DOS64.PRG','DOS64.REL']},'detached':str(W/'detached'),'dispatch_claim':str(W/'dispatch-claim'),'supervisor_pidfile':str(W/'supervisor.pid'),'entry':str(W/'launch.py'),'shared_core_seconds':600,'cold_cleanup_seconds':90,'config_cleanup_seconds':45,'watchdog_seconds':900,'interrupt_grace_seconds':120,'source_chunk_bytes':128,'source_load_seconds':15,'full_snapshots':3,'healthy_full_GETs':387,'healthy_stream_ACKs':384,'nonstager_source_chunks':145,'stager_source_chunks':101,'native_jobs':119,'native_restore_attempts':1,'native_READ_count':8192,'native_STORE_count':2048,'stager_REU_start':2097152,'stager_REU_end_exclusive':2113536,'restore_start':0,'restore_end_exclusive':4194304,'configuration_PUT_max':2,'ROOT_review_required_before_dispatch':True,'historical_backup_adoption':True,'cold_entry':'FRESH_BASIC_ONLY_REFUSE_NATIVE_MAIN'}
for k in ['POST','FTP','upper12MiB_access','fullboard_reset','API_config_repair','original_CPU_restore','original_RAM_restore','original_application_resume','automatic_retry','live_MAIN_takeover','SETUP_CONFIG_UI_execution','START_DOS_execution','DOS_images_staged','fresh_remote_backup_before_write_read','second_native_attempt']:m[k]=False
m.update({k:str(p)for k,p in authority.items()});m['files']=dict(sorted(files.items()));(W/'LAUNCH_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n');(W/'LAUNCH_SHA.txt').write_text(sha(W/'LAUNCH_MANIFEST.json')+'\n');print(sha(W/'LAUNCH_MANIFEST.json'),len(files))
