"""Private mocked orchestration tests. No network, firmware or physical device."""
import ftplib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import io
from urllib.parse import unquote
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build_support'))
import c64u_native_file_recovery as h
import c64u_native_file_runner as runner
from c64u_bulk_reu_recovery import run_with_recovery,sha,SIZE
from c64u_ftp_put_transport import LEAVES,BASE
ROOT=Path(__file__).resolve().parents[2]
BASE_PRG=h.base_prg(ROOT/'build/dos64-native-file-restore.prg')
RECOVERY=(ROOT/'build/dos64-bulk-reu-service.prg').read_bytes()
NATIVE=b'\x01\x08'+b'mocked-application'*20
DATA=bytes(range(256))*(SIZE//256)
BLOBS={'recovery':RECOVERY,'native':NATIVE}


def two_manifest():
 directory=BASE+'/initial-owned'
 return {'schema':1,'project':'8088DOS64ultimate','purpose':'owned-native-development-prgs','status':'verified',
         'run_id':'initial-owned','remote_directory':directory,'created_directory':True,'source_files_unchanged':True,
         'marker_sha256':'a'*64,'marker_readback_sha256':'a'*64,'marker_bytes':128,
         'files':{role:{'sha256':sha(body),'bytes':len(body),'remote_path':directory+'/'+LEAVES[role],
                        'remote_readback_sha256':sha(body),'remote_readback_bytes':len(body)} for role,body in BLOBS.items()}}

class Clock:
 def __init__(self):self.now=0
 def __call__(self):return self.now
 def sleep(self,value):self.now+=value

class FTP:
 def __init__(self,files,events):self.files=files;self.events=events;self.fault=None;self.close_error=False;self.sock=None;self.timeout=20
 def cwd(self,path):self.events.append(('cwd',path))
 def mkd(self,path):
  self.events.append(('mkd',path))
  if path in self.files:raise ftplib.error_perm('Exists')
  self.files[path]=None
 def storbinary(self,command,file,callback):
  self.events.append(('store',command[5:]))
  body=file.read();self.files[command[5:]]=body;callback(body)
  if self.fault=='upload':raise RuntimeError('First upload failure')
 def retrbinary(self,command,callback):
  path=command[5:];self.events.append(('retrieve',path));body=self.files[path]
  if self.fault=='short' and path.endswith('BACKUP.REU'):body=body[:-1]
  if self.fault=='extra' and path.endswith('BACKUP.REU'):body+=b'!'
  if self.fault=='marker' and path.endswith('OWNER.JSON'):body=b'bad-owner'
  callback(body)
 def close(self):
  self.events.append(('ftp-close',))
  if self.close_error:raise RuntimeError('Late close failure')

class REST:
 def __init__(self,files,clock):
  self.files=files;self.clock=clock;self.ram=bytearray(65536);self.reu=bytearray(b'\xff'*SIZE);self.events=[];self.mode='';self.native_reads=0;self.native_fault=None;self.fail_once=False;self.native_runs=0;self.truncate=False;self.compare_corrupt=False;self.disabled=False;self.reset_failure=False;self.config_failure=False;self.latency=0;self.on_native_error=None;self.stale_done=False;self.capture_fail_once=False;self.turbo={'Turbo Control':'Manual','CPU Speed':'64','System Mode':'PAL'}
 def get(self,route):
  self.events.append(('get',route))
  if route=='info':return {'product':'Mock'}
  if route=='configs/C64%20and%20Cartridge%20Settings':return {'C64 and Cartridge Settings':{'RAM Expansion Unit':'Enabled','REU Size':'16 MB','Command Interface':'Disabled' if self.disabled else 'Enabled'}}
  if route=='configs/U64%20Specific%20Settings':return {'U64 Specific Settings':dict(self.turbo)}
  if route=='configs/U64%20Specific%20Settings/CPU%20Speed':return {'U64 Specific Settings':{'CPU Speed':{'values':[' 1','16','64']}}}
  if route=='drives':return {'drives':[]}
  raise AssertionError(route)
 def put(self,route):
  self.events.append(('put',route));self.clock.now+=self.latency
  if route.startswith('runners:run_prg?file='):
   path=unquote(route.split('=',1)[1]);body=self.files[path];self.ram[0x801:0x801+len(body)-2]=body[2:]
   if body==RECOVERY:self.mode='service';self.ram[0x6000:0x6020]=b'DRS1'+bytes([0x11])+bytes(27)
   else:
    self.mode='native';self.native_reads=0;self.native_runs+=1;self.ram[0x6000:0x6020]=b'DRF1'+bytes([2])+bytes(27)
    if self.native_fault=='code':self.ram[0x850]^=1
   return {}
  if route.startswith('machine:writemem?'):
   address,body=route.split('?',1)[1].split('&data=');address=int(address.split('=')[1],16);body=bytes.fromhex(body);self.ram[address:address+len(body)]=body;return {}
  if route=='machine:resume' and self.mode=='service' and self.ram[0x6004]==0x47:
   r=self.ram;address=int.from_bytes(r[0x600b:0x600e],'little');count=int.from_bytes(r[0x600e:0x6010],'little')
   assert r[0x6006]==1 # Native-file recovery never uploads REST bulk payload.
   r[0x8000:0x8000+count]=self.reu[address:address+count]
   if self.compare_corrupt:r[0x8000]^=1
   r[0x6009:0x600b]=r[0x6007:0x6009];r[0x6004]=0xa5
  if route=='machine:reset' and self.reset_failure:raise RuntimeError('Reset failed')
  if route.startswith('configs/'):
   if self.config_failure:raise RuntimeError('Config cleanup failed')
   name,value=route.split('?',1);key=unquote(name.split('/')[-1]);self.turbo[key]=unquote(value.split('=',1)[1])
  return {}
 def read(self,address,length):
  self.events.append(('read',address,length));self.clock.now+=self.latency
  if address==0x6000 and length==32 and self.mode=='native':
   self.native_reads+=1
   if self.native_reads>1 or self.stale_done:
    fault=self.native_fault
    if self.fail_once and self.native_runs>1:fault=None
    if fault=='timeout':pass
    elif fault in ('error','hash-read'):
     self.ram[0x6004]=0xe1;self.ram[0x6005]=7;self.ram[0x6008]=2
     if self.on_native_error:self.on_native_error();self.on_native_error=None
    else:
     cfg=self.ram[h.CONFIG:h.CONFIG+138];path=bytes(cfg[10:10+cfg[5]-1]).decode();data=self.files[path];self.reu[:]=data
     raw=bytearray(b'DRF1'+bytes(28));raw[4]=0xa5;raw[7]=6;crc=zlib.crc32(data).to_bytes(4,'little');raw[16:20]=crc;raw[20:24]=crc;raw[28:30]=b'\0\x20';self.ram[0x6000:0x6020]=raw
     for target,value in zip(h.DYNAMIC,(0xc101,0xc67f)):self.ram[target:target+2]=value.to_bytes(2,'little')
     if fault=='crc':self.ram[0x6014]^=1
     if fault=='handle':self.ram[0x6008]=2
     if fault=='counter':self.ram[0x601d]=0x1f
     if fault=='operand':self.ram[h.DYNAMIC[0]:h.DYNAMIC[0]+2]=b'\0\x90'
  if self.capture_fail_once and address==0 and length==65536 and self.ram[0x6004]==0xe1:
   self.capture_fail_once=False;raise RuntimeError('First native RAM capture failed')
  result=bytes(self.ram[address:address+length])
  if self.truncate and address==0x8000:result=result[:-1]
  return result

class Tests(unittest.TestCase):
 def setup_run(self,d):
  root=Path(d);backup=root/'backup.bin';backup.write_bytes(DATA);backup.chmod(0o444)
  manifest={'schema':1,'complete':True,'reu_start':0,'length':SIZE,'sha256':sha(DATA)}
  files={BASE+'/initial-owned/'+LEAVES[role]:body for role,body in BLOBS.items()};events=[];clock=Clock();rest=REST(files,clock)
  adapter=h.NativeFileClient(rest,two_manifest(),BLOBS,0xeaf4,clock=clock)
  ftps=[]
  def ftp_factory(timeout):
   ftp=FTP(files,events);ftps.append(ftp);return ftp
  def factory(client,prg,journal):return h.NativeFileService(client,prg,journal,base=BASE_PRG,ftp_factory=ftp_factory,backup_path=backup,backup_manifest=manifest,output=root/'run',clock=clock,sleep=clock.sleep,run_id_factory=lambda i:'owned-pass-'+str(i))
  return root,backup,manifest,files,events,clock,rest,adapter,ftps,factory
 def execute(self,d,configure=None,application=None):
  items=self.setup_run(d)
  if configure:configure(items)
  root,backup,manifest,_,_,_,_,adapter,_,factory=items
  report=run_with_recovery(adapter,RECOVERY,root/'run',application=application,backup_path=backup,backup_manifest=manifest,service_factory=factory,restore_attempts=2)
  return items,report
 def test_complete_workflow_uses_one_owned_backup_prg_marker_and_all4MiB_compare(self):
  with tempfile.TemporaryDirectory() as d:
   items,report=self.execute(d);root,backup,_,files,events,_,rest,_,_,_=items
   self.assertEqual(report['status'],'passed');self.assertTrue(report['reu_restored']);self.assertTrue(report['configuration_restored']);self.assertTrue(report['reset_resumed'])
   self.assertEqual(bytes(rest.reu),DATA);self.assertEqual((root/'run/reu-after-1.bin').read_bytes(),DATA)
   self.assertEqual(len([e for e in events if e[0]=='store']),3);self.assertEqual(len([e for e in rest.events if e[:2]==('read',0x8000)]),256)
   self.assertTrue((root/'run/native-done-ram-1.bin').exists());self.assertFalse(backup.stat().st_mode&0o222)
   self.assertFalse(any('address=8000&data=' in e[1] for e in rest.events if e[0]=='put'))
 def test_two_fresh_attempts_recover_after_native_failure_and_capture_precedes_service_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   def configure(x):x[6].native_fault='error';x[6].fail_once=True
   items,report=self.execute(d,configure);root,_,_,files,events,_,rest,_,_,_=items
   self.assertTrue(report['reu_restored']);self.assertEqual(report['restore_attempts'],2)
   failure=(root/'run/native-restore-failure-1-before-service.bin').read_bytes();self.assertEqual(failure[0x6000:0x6006],b'DRF1\xe1\x07');self.assertEqual(failure[0x6008],2)
   self.assertEqual(len([e for e in events if e[0]=='mkd']),2);self.assertIn(BASE+'/owned-pass-1/BACKUP.REU',files);self.assertIn(BASE+'/owned-pass-2/BACKUP.REU',files)
 def test_terminal_faults_never_pass_and_retain_native_failure_evidence(self):
  for fault in ('crc','handle','counter','code','operand'):
   with self.subTest(fault=fault),tempfile.TemporaryDirectory() as d:
    items,report=self.execute(d,lambda x:setattr(x[6],'native_fault',fault));root=items[0]
    self.assertEqual(report['status'],'failed');self.assertFalse(report['reu_restored']);self.assertTrue(report['reset_resumed'])
    self.assertTrue((root/'run/native-restore-failure-1-before-service.bin').exists());self.assertEqual(items[6].native_runs,2)
 def test_timeout_bounded_and_failure_ram_before_retry(self):
  with tempfile.TemporaryDirectory() as d:
   items,report=self.execute(d,lambda x:setattr(x[6],'native_fault','timeout'))
   self.assertFalse(report['reu_restored']);self.assertLess(items[5].now,1201);self.assertTrue((items[0]/'run/native-restore-failure-1-before-service.bin').exists())
 def test_truncated_final_staging_read_is_explicit_failure(self):
  with tempfile.TemporaryDirectory() as d:
   items,report=self.execute(d,lambda x:setattr(x[6],'truncate',True))
   self.assertFalse(report['reu_restored']);self.assertTrue(any('length mismatch' in e for e in report['restore_errors']));self.assertTrue(report['reset_resumed'])
 def test_full_compare_mismatch_cannot_accept_native_crc_done(self):
  with tempfile.TemporaryDirectory() as d:
   _,report=self.execute(d,lambda x:setattr(x[6],'compare_corrupt',True))
   self.assertFalse(report['reu_restored']);self.assertTrue(any('first differs' in e for e in report['restore_errors']))
 def test_disabled_interface_prevents_ftp_or_native_launch(self):
  with tempfile.TemporaryDirectory() as d:
   items,report=self.execute(d,lambda x:setattr(x[6],'disabled',True))
   self.assertFalse(report['reu_restored']);self.assertEqual(items[6].native_runs,0);self.assertEqual(items[4],[])
 def test_mutated_or_writable_backup_is_rejected_before_file_stage(self):
  for writable in (False,True):
   with self.subTest(writable=writable),tempfile.TemporaryDirectory() as d:
    def configure(x):
     x[1].chmod(0o644)
     if not writable:x[1].write_bytes(b'bad');x[1].chmod(0o444)
    if not writable:
     items=self.setup_run(d);configure(items)
     with self.assertRaisesRegex(ValueError,'Backup size/hash mismatch'):run_with_recovery(items[7],RECOVERY,items[0]/'run',backup_path=items[1],backup_manifest=items[2],service_factory=items[9])
     self.assertEqual(items[6].events,[])
    else:
     items,report=self.execute(d,configure)
     self.assertFalse(report['reu_restored']);self.assertEqual(items[6].native_runs,0);self.assertEqual(items[4],[])
 def test_ftp_truncation_extra_owner_and_existing_directory_rejected_before_launch(self):
  for fault in ('short','extra','marker','existing'):
   with self.subTest(fault=fault),tempfile.TemporaryDirectory() as d:
    items=self.setup_run(d);root,backup,manifest,files,events,clock,rest,adapter,_,_=items
    def ftp_factory(timeout):
     ftp=FTP(files,events);ftp.fault=fault
     if fault=='existing':files[BASE+'/owned-pass-1']=None;files[BASE+'/owned-pass-2']=None
     return ftp
    def factory(c,p,j):return h.NativeFileService(c,p,j,base=BASE_PRG,ftp_factory=ftp_factory,backup_path=backup,backup_manifest=manifest,output=root/'run',clock=clock,sleep=clock.sleep,run_id_factory=lambda i:'owned-pass-'+str(i))
    report=run_with_recovery(adapter,RECOVERY,root/'run',backup_path=backup,backup_manifest=manifest,service_factory=factory)
    self.assertFalse(report['reu_restored']);self.assertEqual(rest.native_runs,0)
 def test_first_ftp_error_survives_close_error(self):
  with tempfile.TemporaryDirectory() as d:
   root,backup,manifest,files,events,clock,*_=self.setup_run(d);ftp=FTP(files,events);ftp.fault='upload';ftp.close_error=True
   with self.assertRaisesRegex(RuntimeError,'First upload failure'):h.stage_backup(lambda timeout:ftp,backup,manifest,DATA,BASE_PRG,'owned-stage',root/'stage',h.Budget(clock,600))
   record=json.loads((root/'stage/native-file-staging.json').read_text());self.assertIn('First upload failure',record['error']);self.assertIn('Late close failure',record['cleanup_errors'][0])
 def test_registered_third_prg_requires_fresh_clear_and_rejects_outside_patch(self):
  with tempfile.TemporaryDirectory() as d:
   root,backup,manifest,files,events,clock,rest,adapter,*_=self.setup_run(d)
   record,configured=h.stage_backup(lambda timeout:FTP(files,events),backup,manifest,DATA,BASE_PRG,'owned-stage',root/'stage',h.Budget(clock,600));adapter.register(record,BASE_PRG,configured,DATA)
   with self.assertRaises(ValueError):adapter.request('POST','runners:run_prg',configured,'application/octet-stream')
   adapter.put('machine:pause');adapter.clear_mailbox();adapter.request('POST','runners:run_prg',configured,'application/octet-stream')
   with self.assertRaises(ValueError):adapter.request('POST','runners:run_prg',configured,'application/octet-stream')
   adapter.put('machine:pause')
   with self.assertRaises(ValueError):adapter.clear_mailbox()
   with self.assertRaises(ValueError):adapter.register(record,BASE_PRG,configured,DATA)
   changed=bytearray(configured);changed[20]^=1
   with self.assertRaises(ValueError):adapter.register(record,BASE_PRG,bytes(changed),DATA)
   with self.assertRaises(ValueError):adapter.register(record,BASE_PRG,bytearray(configured),DATA)
   with self.assertRaises(ValueError):adapter.request('POST','runners:run_prg',bytes(changed),'application/octet-stream')
 def test_unknown_tiny_memory_write_and_unowned_registry_are_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root,backup,manifest,files,events,clock,rest,adapter,*_=self.setup_run(d)
   for address,body in ((0x6000,bytes(32)),(0x7000,b'bad')):
    with self.assertRaises(ValueError):adapter.request('POST',f'machine:writemem?address={address:X}',body,'application/octet-stream')
   record,configured=h.stage_backup(lambda timeout:FTP(files,events),backup,manifest,DATA,BASE_PRG,'owned-stage',root/'stage',h.Budget(clock,600));record['files']['restore']['remote_path']='/Temp/unowned.prg'
   with self.assertRaises(ValueError):adapter.register(record,BASE_PRG,configured,DATA)
 def test_expired_phase_clamps_ftp_and_disallows_launch(self):
  with tempfile.TemporaryDirectory() as d:
   root,backup,manifest,files,events,clock,rest,adapter,*_=self.setup_run(d)
   def factory(timeout):self.assertLessEqual(timeout,1);clock.now+=2;return FTP(files,events)
   with self.assertRaises(TimeoutError):h.stage_backup(factory,backup,manifest,DATA,BASE_PRG,'owned-stage',root/'stage',h.Budget(clock,1))
   self.assertEqual(rest.native_runs,0);self.assertFalse(any(e[0]=='store' for e in events))
 def test_restore_budget_includes_reload_and_all_compare_requests(self):
  with tempfile.TemporaryDirectory() as d:
   items=self.setup_run(d);root,backup,manifest,files,events,clock,rest,adapter,_,factory=items;root.joinpath('run').mkdir();service=factory(adapter,RECOVERY,lambda *a,**k:None)
   service.restore(DATA,phase_seconds=1);rest.latency=.01
   with self.assertRaises(TimeoutError):service.compare(DATA,root/'run/readback.bin')
   self.assertTrue((root/'run/native-compare-failure-1-before-reset.bin').exists());self.assertIsNone(adapter.budget)
 def test_application_and_cleanup_failures_remain_failed_while_recovery_runs(self):
  with tempfile.TemporaryDirectory() as d:
   def application(*args):raise RuntimeError('Earlier application failure')
   items,report=self.execute(d,lambda x:setattr(x[6],'config_failure',True),application)
   self.assertEqual(report['status'],'failed');self.assertIn('Earlier application failure',report['error']);self.assertTrue(report['reu_restored']);self.assertTrue(report['reset_resumed'])
 def test_reset_failure_does_not_skip_resume(self):
  with tempfile.TemporaryDirectory() as d:
   items,report=self.execute(d,lambda x:setattr(x[6],'reset_failure',True));self.assertEqual(report['status'],'failed');self.assertFalse(report['reset_resumed'])
   self.assertEqual(items[6].events[-1],('put','machine:resume'))

 def test_failed_application_result_is_raised_so_outer_recovery_cannot_pass(self):
  with tempfile.TemporaryDirectory() as d:
   _,report=self.execute(d,application=runner.checked_application(lambda *args:{'status':'failed'}))
   self.assertEqual(report['status'],'failed');self.assertTrue(report['reu_restored']);self.assertIn('failed/missing status',report['error'])
 def test_base_prg_and_pal_evidence_are_explicit_local_pins(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'bad.prg';path.write_bytes(BASE_PRG+b'bad')
   with self.assertRaises(ValueError):h.base_prg(path)
   path=Path(d)/'clock.json';path.write_text(json.dumps({'status':'passed','configuration_restored':True,'reset_resumed':True,'speeds':[{'mhz_setting':64,'profile':'NTSC','expected_ticks':1,'error_ticks':0,'tolerance_ticks':1}]}))
   with self.assertRaises(ValueError):runner.clock_evidence(path)

 def test_unobserved_done_is_never_accepted_even_with_fresh_valid_counters(self):
  with tempfile.TemporaryDirectory() as d:
   _,report=self.execute(d,lambda x:setattr(x[6],'stale_done',True));self.assertFalse(report['reu_restored'])
   self.assertTrue(any('without observed fresh' in error for error in report['restore_errors']))
 def test_source_read_failure_after_native_error_cannot_mask_first_error(self):
  with tempfile.TemporaryDirectory() as d:
   def configure(x):x[6].native_fault='error';x[6].on_native_error=lambda:x[1].unlink()
   items,report=self.execute(d,configure)
   self.assertIn('Native restore failure',report['restore_errors'][0]);self.assertIn('FileNotFoundError',report['restore_errors'][1]);self.assertEqual(report['status'],'failed')
   self.assertEqual((items[0]/'run/reu-before.bin').read_bytes(),DATA);self.assertTrue(report['reset_resumed'])
 def test_cli_validation_is_local_and_late_source_failure_preserves_primary_report(self):
  with tempfile.TemporaryDirectory() as d:
   root,backup,manifest,_,_,_,_,_,_,_=self.setup_run(d)
   for name,body in [('service.prg',RECOVERY),('native.prg',NATIVE)]:root.joinpath(name).write_bytes(body)
   root.joinpath('backup.json').write_text(json.dumps(manifest));root.joinpath('stage.json').write_text(json.dumps(two_manifest()))
   root.joinpath('clock.json').write_text(json.dumps({'status':'passed','configuration_restored':True,'reset_resumed':True,'speeds':[{'mhz_setting':64,'profile':'PAL-312x63','expected_ticks':1965600,'error_ticks':0,'tolerance_ticks':1008}]}))
   out=root/'agentworking/runs/cli'
   argv=['--recovery','native-file','--recovery-only','--host','must-not-contact','--output',str(out),'--service',str(root/'service.prg'),'--staging-manifest',str(root/'stage.json'),'--pal-clock-evidence',str(root/'clock.json'),'--backup',str(backup),'--backup-manifest',str(root/'backup.json'),'--registered-native-prg',str(root/'native.prg'),'--native-diag-address','0xeaf4','--restore-prg',str(ROOT/'build/dos64-native-file-restore.prg')]
   with mock.patch.object(h,'PROJECT',root),mock.patch.object(runner,'identities',return_value={'frozen':{}}),mock.patch('urllib.request.urlopen',side_effect=AssertionError('No network')),mock.patch('ftplib.FTP',side_effect=AssertionError('No FTP')),mock.patch('sys.stdout',new_callable=io.StringIO):
    self.assertEqual(runner.main(argv+['--validate-only']),0);self.assertFalse(out.exists())
   def outer(*args,**kw):
    self.assertEqual(kw['restore_attempts'],2);out.mkdir(parents=True)
    return {'status':'failed','error':'Earlier application error','reu_restored':True,'configuration_restored':True,'reset_resumed':True}
   with mock.patch.object(h,'PROJECT',root),mock.patch.object(runner,'identities',side_effect=[{'frozen':{}},FileNotFoundError('Late source hash failed')]),mock.patch.object(runner,'run_with_recovery',side_effect=outer),mock.patch('sys.stdout',new_callable=io.StringIO):
    self.assertEqual(runner.main(argv),1)
   report=json.loads((out/'result.json').read_text());self.assertEqual(report['error'],'Earlier application error');self.assertIn('Late source hash failed',report['late_evidence_errors'][0])

 def test_first_failure_capture_error_does_not_mask_native_error_or_skip_outer_capture(self):
  with tempfile.TemporaryDirectory() as d:
   def configure(x):x[6].native_fault='error';x[6].fail_once=True;x[6].capture_fail_once=True
   items,report=self.execute(d,configure)
   self.assertTrue(report['reu_restored']);self.assertIn('Native restore failure',report['restore_errors'][0])
   outer=(items[0]/'run/ram-restore-failure-1-before-reset.bin').read_bytes();self.assertEqual(outer[0x6000:0x6006],b'DRF1\xe1\x07')
   journal=(items[0]/'run/journal.jsonl').read_text();self.assertIn('native_failure_ram_capture_failed',journal)

 def test_private_rest_socket_timeout_is_clamped_and_late_completion_fails(self):
  clock=Clock();client=h.DeadlineClient('must-not-contact');client.budget=h.Budget(clock,600);clock.now=599.8;timeouts=[]
  class Response:
   headers={'Content-Type':'application/json'}
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self):clock.now+=.1;return b'{}'
  def open_mock(request,timeout):timeouts.append(timeout);return Response()
  with mock.patch('urllib.request.urlopen',side_effect=open_mock):
   self.assertEqual(client.get('info'),{});clock.now=599.99
   with self.assertRaises(TimeoutError):client.get('info')
   with self.assertRaises(TimeoutError):client.get('info')
  self.assertEqual(len(timeouts),2);self.assertLess(timeouts[0],.21);self.assertLess(timeouts[1],.011)
 def test_service_rejects_any_replacement_original_drs1_binary(self):
  with tempfile.TemporaryDirectory() as d:
   root,backup,manifest,files,events,clock,rest,adapter,*_=self.setup_run(d)
   with self.assertRaisesRegex(ValueError,'original DRS1'):h.NativeFileService(adapter,RECOVERY+b'bad',lambda *a,**k:None,base=BASE_PRG,ftp_factory=lambda timeout:FTP(files,events),backup_path=backup,backup_manifest=manifest,output=root,clock=clock,sleep=clock.sleep)

 def test_current_nonpal_rejected_before_ftp_or_native_execution(self):
  with tempfile.TemporaryDirectory() as d:
   items,report=self.execute(d,lambda x:x[6].turbo.update({'System Mode':'NTSC'}));self.assertFalse(report['reu_restored']);self.assertEqual(items[6].native_runs,0);self.assertEqual(items[4],[])
 def test_manual64_selection_uses_allowed_keys_and_original_turbo_is_restored(self):
  with tempfile.TemporaryDirectory() as d:
   items,report=self.execute(d,lambda x:x[6].turbo.update({'Turbo Control':'C64U Turbo Registers','CPU Speed':' 1'}))
   self.assertEqual(report['status'],'passed');self.assertEqual(items[6].turbo,{'Turbo Control':'C64U Turbo Registers','CPU Speed':' 1','System Mode':'PAL'})
   puts=[e[1] for e in items[6].events if e[0]=='put' and e[1].startswith('configs/')];self.assertEqual(len(puts),4);self.assertTrue(any('value=Manual' in p for p in puts));self.assertTrue(any('value=%201' in p for p in puts))

 def test_startup_identity_allows_only_known_partial_smc_publications(self):
  configured=h.configure(BASE_PRG,DATA,BASE+'/owned-stage/BACKUP.REU');ram=bytearray(65536);ram[0x801:0x801+len(configured)-2]=configured[2:]
  ram[h.DYNAMIC[0]:h.DYNAMIC[0]+2]=(0xff20).to_bytes(2,'little');ram[h.DYNAMIC[1]:h.DYNAMIC[1]+2]=(0xc400).to_bytes(2,'little')
  h.resident_identity(bytes(ram),configured)
  with self.assertRaises(ValueError):h.resident_identity(bytes(ram),configured,terminal=True)
  ram[h.DYNAMIC[0]:h.DYNAMIC[0]+2]=(0xc102).to_bytes(2,'little');ram[h.DYNAMIC[1]:h.DYNAMIC[1]+2]=(0xc67f).to_bytes(2,'little')
  with self.assertRaises(ValueError):h.resident_identity(bytes(ram),configured,terminal=True)
  ram[h.DYNAMIC[0]:h.DYNAMIC[0]+2]=(0x9000).to_bytes(2,'little')
  with self.assertRaises(ValueError):h.resident_identity(bytes(ram),configured)

if __name__=='__main__':unittest.main()
