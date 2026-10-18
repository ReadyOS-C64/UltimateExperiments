import sys,os,json,hashlib
from pathlib import Path
WORK=Path(__file__).resolve().parents[3]
HOST=WORK/'build_support/ac_development'
sys.dont_write_bytecode=True;sys.pycache_prefix=str(HOST/'.source-import-cache-disabled');sys.path.insert(0,str(HOST))
if Path(sys.pycache_prefix).exists():raise RuntimeError('Source-only cache path must remain absent')
context_path=Path(os.environ['DOS64_AC_TEST_CONTEXT']);context_raw=context_path.read_bytes()
if hashlib.sha256(context_raw).hexdigest()!=os.environ['DOS64_AC_TEST_CONTEXT_SHA']:raise ValueError('Explicit test context hash differs')
CONTEXT=json.loads(context_raw);P=Path(CONTEXT['fixture_root'])
if hashlib.sha256((P/'MANIFEST.json').read_bytes()).hexdigest()!=CONTEXT['source_host_manifest_sha256']:raise ValueError('Sealed test fixture authority differs')
import bootstrap,unittest,json,tempfile,copy,io,ftplib,hashlib,types
from unittest.mock import patch
from ac_contract import Registration,sha,verify_media,A_SHA,HD_SHA
from ac_staging import stage_media
from ac_helper_staging import stage_helper,validate_helper_stage
from ac_helper import configure_helper,HelperLoadThenSys,CompositeClient,HelperSession
from ac_load_then_sys import ACLoadThenSysClient
from ac_application import CollectionApplication
from ac_script import CollectionScript,COMMANDS,keys
from ac_runner import prepare,validate
from ac_freeze import verify_guard
from ac_retention import verify_overlay_sources

class FTP:
 def __init__(self,existing=False,corrupt=False,excess=False):self.files={};self.dirs=set(['/usb1/DOS64_TEST']);self.stores=[];self.existing=existing;self.corrupt=corrupt;self.excess=excess;self.sock=None
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def mkd(self,d):
  if d in self.dirs or self.existing:raise ftplib.error_perm('exists')
  self.dirs.add(d)
 def cwd(self,d):
  if d not in self.dirs:raise ftplib.error_perm('missing')
 def storbinary(self,cmd,stream,callback=None):
  body=stream.read();self.files[cmd[5:]]=body;self.stores.append(cmd)
  if callback:callback(body)
 def retrbinary(self,cmd,callback):
  b=self.files[cmd[5:]]
  if self.corrupt and cmd.endswith('DOSHD.IMG'):b=b[:-1]+bytes([b[-1]^1])
  if self.excess and cmd.endswith('DOS33A.IMG'):b+=b'x'
  for at in range(0,len(b),16384):callback(b[at:at+16384])
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.reg=Registration(P/'evidence/native-ac-success/NATIVE_AC_PROOF.json','2b2dae383d87fc08836ef9ba83608c49649846e32d505ab21b933c4bac07f336')
  cls.floppy=(P/'outputs/full-tp/BOOT-A.IMG').read_bytes();cls.hd=(P/'outputs/full-tp/HD.IMG').read_bytes();cls.media=json.loads((Path(CONTEXT['media_manifest'])).read_text());cls.configured,cls.patch=cls.reg.configure(cls.media,cls.floppy,cls.hd)
  cls.service=(P/'inputs/REU-RECOVERY.PRG').read_bytes();cls.helper_base=(bootstrap.HELPER_BUILD/'close-reopen.prg').read_bytes();cls.helper_blob=(bootstrap.HELPER_BUILD/'close-reopen.labels').read_bytes();cls.helper,cls.hlabels,cls.hpatch=configure_helper(cls.helper_base,cls.helper_blob,cls.media['files']['hd']['native_path'])
 def temp(self):return tempfile.TemporaryDirectory(prefix='host-test-',dir=Path(__file__).resolve().parent)
 def test_registration_actual_source_closure_and_old_allowlists_unchanged(self):
  import load_then_sys,c64u_native_application_support
  self.assertEqual(len(self.reg.proof['execution_source_closure']),323);self.assertEqual(load_then_sys.ARTIFACTS['original-split256'][0][:8],'d883c678');self.assertEqual(c64u_native_application_support.SOURCE_SHA[:8],'bca98992')
 def test_bad_proof_hash_rejected(self):
  with self.assertRaises(ValueError):Registration(P/'evidence/native-ac-success/NATIVE_AC_PROOF.json','0'*64)
 def test_exact_only_two_cold_blocks_patched(self):
  n=self.reg.labels['dos64_native_config']-0x801+2;h=self.reg.labels['hdc_config']-0x801+2;allowed={n+4,n+7}|set(range(n+10,n+142))|set(range(h+4,h+140))
  self.assertTrue(all(i in allowed for i,(x,y) in enumerate(zip(self.reg.blobs['dos64.prg'],self.configured)) if x!=y));self.assertEqual(self.configured[h:h+12],b'D64H'+bytes([0xa5,1,1,0,0,2,2,len(self.media['files']['hd']['native_path'])+1]))
 def test_media_each_readback_hash_size_path_owner_guard(self):
  for change in ['status','created_directory','original_sources_unchanged','marker_sha256','HDhash','Asize','HDpath']:
   r=copy.deepcopy(self.media)
   if change=='HDhash':r['files']['hd']['remote_readback_sha256']='0'*64
   elif change=='Asize':r['files']['floppy']['remote_readback_bytes']-=1
   elif change=='HDpath':r['files']['hd']['native_path']='/usb1/UNOWNED.IMG'
   elif change=='marker_sha256':r[change]='bad'
   elif change=='status':r[change]='failed'
   else:r[change]=False
   with self.assertRaises(ValueError):verify_media(r,self.floppy,self.hd)
 def test_bad_source_A_and_HD_rejected(self):
  for floppy,hd in [(self.floppy[:-1],self.hd),(self.floppy,self.hd[:-1])]:
   with self.assertRaises(ValueError):verify_media(self.media,floppy,hd)
 def test_full_fakeFTP_dualmedia_stage_readback(self):
  with self.temp() as d:
   f=FTP();r=stage_media(lambda seconds:f,P/'outputs/full-tp/BOOT-A.IMG',P/'outputs/full-tp/HD.IMG','unit-media',Path(d)/'stage');verify_media(r,self.floppy,self.hd);self.assertEqual(len(f.stores),3)
 def test_existing_remote_never_overwritten(self):
  with self.temp() as d:
   f=FTP(existing=True)
   with self.assertRaises(ftplib.error_perm):stage_media(lambda seconds:f,P/'outputs/full-tp/BOOT-A.IMG',P/'outputs/full-tp/HD.IMG','unit-existing',Path(d)/'stage')
   self.assertFalse(f.stores)
 def test_fullHD_corruption_and_A_excess_failclosed(self):
  for kw in [{'corrupt':True},{'excess':True}]:
   with self.temp() as d:
    f=FTP(**kw)
    with self.assertRaises(ValueError):stage_media(lambda seconds:f,P/'outputs/full-tp/BOOT-A.IMG',P/'outputs/full-tp/HD.IMG','unit-corrupt',Path(d)/'stage')
    self.assertEqual(json.loads((Path(d)/'stage/ac-media-staging.json').read_text())['status'],'failed')
 def test_ftp_deadline_before_connect(self):
  with self.temp() as d:
   times=iter([0,181]);calls=[]
   with self.assertRaises(TimeoutError):stage_media(lambda seconds:calls.append(seconds),P/'outputs/full-tp/BOOT-A.IMG',P/'outputs/full-tp/HD.IMG','unit-timeout',Path(d)/'stage',clock=lambda:next(times))
   self.assertFalse(calls)
 def test_helper_config_only_allowed_path_enable(self):
  at=self.hlabels['helper_config']-0x801+2;self.assertTrue(all(at+4<=i<at+134 for i,(x,y) in enumerate(zip(self.helper_base,self.helper)) if x!=y))
  with self.assertRaises(ValueError):configure_helper(self.helper_base,self.helper_blob,'/usb1/NOTOWNED.IMG')
 def test_helper_stage_fullread_and_negative_guards(self):
  with self.temp() as d:
   source=Path(d)/'HELPER.PRG';source.write_bytes(self.helper);f=FTP();r=stage_helper(lambda seconds:f,source,sha(self.helper),'unit-helper',Path(d)/'stage');self.assertTrue(validate_helper_stage(r,self.helper).endswith('/HD-CLOSE.PRG'))
   for key in ['created_directory','source_files_unchanged']:
    bad=copy.deepcopy(r);bad[key]=False
    with self.assertRaises(ValueError):validate_helper_stage(bad,self.helper)
 def test_application_constructor_rejects_unregistered_code(self):
  bad=bytearray(self.configured);bad[40]^=1
  with self.assertRaises(ValueError):CollectionApplication(self.reg,bytes(bad),self.patch,self.floppy,self.hd,self.media,self.service)
 def test_native_load_constructor_rejects_unregistered_code(self):
  delegate=types.SimpleNamespace(paths={sha(self.configured):'/usb1/DOS64_TEST/unit-prgs/NATIVE-DOS.PRG'})
  bad=bytearray(self.configured);bad[40]^=1;fakepatch={**self.patch,'configured_sha256':sha(bad)}
  with self.assertRaises(ValueError):ACLoadThenSysClient(delegate,self.reg,bytes(bad),fakepatch,self.media,self.floppy,self.hd)
 def test_helper_load_constructor_rejects_changed_source_or_config(self):
  delegate=types.SimpleNamespace();bad=bytearray(self.helper);bad[40]^=1
  with self.assertRaises(ValueError):HelperLoadThenSys(delegate,bytes(bad),'/usb1/DOS64_TEST/unit-helper/HD-CLOSE.PRG',{**self.hpatch,'configured_sha256':sha(bad)},base=self.helper_base,labels_blob=self.helper_blob)
 def test_helper_load_verifies_entire_visible_code(self):
  h=HelperLoadThenSys(types.SimpleNamespace(),self.helper,'/usb1/DOS64_TEST/unit-helper/HD-CLOSE.PRG',self.hpatch,base=self.helper_base,labels_blob=self.helper_blob);ram=bytearray(65536);ram[0x801:0x801+len(self.helper)-2]=self.helper[2:];h.verify_loaded(bytes(ram));ram[0x950]^=1
  with self.assertRaises(ValueError):h.verify_loaded(bytes(ram))
 def test_all7_overlay_sources_and_each_corruption(self):
  app=types.SimpleNamespace(prg=self.configured,shadow_build_metadata=self.reg.shadow_metadata);reu=bytearray(4*1024*1024);pkg=self.reg.shadow_metadata['package']
  for i,source in enumerate(pkg['startup_sources']):reu[0x340000+i*2048:0x340000+(i+1)*2048]=self.configured[source-0x801+2:source-0x801+2+2048]
  self.assertTrue(verify_overlay_sources(app,reu)['passed'])
  for i in range(7):
   reu[0x340000+i*2048+2031]^=1
   with self.assertRaises(ValueError):verify_overlay_sources(app,reu)
   reu[0x340000+i*2048+2031]^=1
 def test_script_queue_capacity_and_stale_prompt(self):
  script=CollectionScript();screen={'ring_used':14,'guest_instructions':0,'prompt':True,'mode':3,'columns':80,'text':'C>','cursor_row':0,'cursor_column':2};words=script.observe(screen);self.assertEqual(len(words),1);self.assertEqual(script.pending,'LS\r');screen['ring_used']=15;self.assertEqual(script.observe(screen),[]);screen.update(ring_used=0,guest_instructions=100);self.assertEqual(len(script.observe(screen)),3);self.assertEqual(script.observe(screen),[]);self.assertEqual(script.step,0)
 def test_all_command_characters_and_bounds(self):
  for command,expected in COMMANDS:self.assertTrue(keys(command));self.assertLess(len(command),128)
 def test_helper_descriptor_transport_never_widens_original_adapter(self):
  raw=types.SimpleNamespace(put=lambda route:route);native=types.SimpleNamespace(client=raw,request=lambda *a:'original',put=lambda route:'original',read=lambda *a:b'');helper=types.SimpleNamespace(configured=self.helper,awaiting_start_resume=False)
  client=CompositeClient(native,helper);client.helper_active=True
  with self.assertRaises(ValueError):client.request('POST','machine:writemem?address=6009',bytes(8),'application/octet-stream')
  client.request('POST','machine:writemem?address=6004',b'\0','application/octet-stream')
  descriptor=bytes([1,1])+bytes([0,2])+bytes(4);client.request('POST','machine:writemem?address=6009',descriptor,'application/octet-stream');client.request('POST','machine:writemem?address=6004',b'G','application/octet-stream')
  for address,body in [('6009',bytes([2,5])+bytes(6)),('8000',b'x'),('6004',b'X')]:
   with self.assertRaises(ValueError):client.request('POST','machine:writemem?address='+address,body,'application/octet-stream')
 def test_snapshot_rejects_all_active_UCI_states_and_resumes(self):
  for state in list(range(1,9))+[11,255]:
   events=[];labels={'hdb_active':1,'hd_state':2,'dos64_files_state':3,'dos64_uci_state':4};obj=CollectionApplication.__new__(CollectionApplication);obj.labels=labels;obj.client=types.SimpleNamespace(put=lambda route:events.append(route),read=lambda at,n:bytes([state if at==4 else 0]));self.assertFalse(obj.can_snapshot());self.assertEqual(events,['machine:pause','machine:resume'])
  for state in [0,9,10]:
   events=[];obj.client=types.SimpleNamespace(put=lambda route:events.append(route),read=lambda at,n:bytes([state if at==4 else 0]));self.assertTrue(obj.can_snapshot());self.assertEqual(events,['machine:pause'])
 def test_snapshot_HD_FILE_busy_guards_resume(self):
  labels={'hdb_active':1,'hd_state':2,'dos64_files_state':3,'dos64_uci_state':4}
  for active in [1,2,3]:
   events=[];obj=CollectionApplication.__new__(CollectionApplication);obj.labels=labels;obj.client=types.SimpleNamespace(put=lambda route:events.append(route),read=lambda at,n:bytes([1 if at==active else 0]));self.assertFalse(obj.can_snapshot());self.assertEqual(events,['machine:pause','machine:resume'])
 def test_actual_NTSC_rejected_before_any_native_launch(self):
  app=CollectionApplication(self.reg,self.configured,self.patch,self.floppy,self.hd,self.media,self.service);events=[];app.preflight=lambda:{'status':'passed'};app.capture_ram=lambda name:'mock';client=types.SimpleNamespace(client=types.SimpleNamespace(budget=None),configs=lambda v:events.append(('configs',v)),get=lambda route:{'U64 Specific Settings':{'CPU Speed':{'values':['64']}}} if route.endswith('/CPU%20Speed') else {'U64 Specific Settings':{'System Mode':'NTSC','Turbo Control':'Manual','CPU Speed':'64'}},request=lambda *a:events.append(('request',a)))
  with self.temp() as d:
   with self.assertRaisesRegex(ValueError,'actual PAL/Manual64'):app(client,d)
   self.assertFalse(any(e[0]=='request' for e in events));report=json.loads((Path(d)/'application-result.json').read_text());self.assertEqual(report['actual_active_turbo']['System Mode'],'NTSC')
 def test_actual_postrun_sector_ownership_and_free_sector_negative(self):
  from ac_filesystem import verify_owned_mutations
  from dos_disk_inspect import Volume
  import struct
  actual=(P/'successors/root4589/proof/HD-after.img').read_bytes();self.assertTrue(verify_owned_mutations(self.hd,actual)['passed']);start=struct.unpack_from('<I',actual,454)[0]*512;before=Volume(self.hd[start:]);after=Volume(actual[start:]);cluster=next(c for c in range(2,before.clusters+2) if before.entry(c)==0 and after.entry(c)==0);offset=start+(after.data_sector+(cluster-2)*after.spc)*512;bad=bytearray(actual);bad[offset]^=1
  self.assertEqual(Volume(bad[start:]).payloads,after.payloads)
  with self.assertRaisesRegex(ValueError,'outside exact'):verify_owned_mutations(self.hd,bytes(bad))
 def test_actual_postrun_original_attribute_and_time_negatives(self):
  from ac_filesystem import verify_owned_mutations
  from dos_disk_inspect import Volume
  import struct
  actual=(P/'successors/root4589/proof/HD-after.img').read_bytes();start=struct.unpack_from('<I',actual,454)[0]*512;v=Volume(actual[start:]);at=start+v.root_sector*512
  for index in [11,22,24]:
   bad=bytearray(actual);bad[at+index]^=0x20 if index==11 else 1;self.assertEqual(Volume(bad[start:]).payloads,v.payloads)
   with self.assertRaises(ValueError):verify_owned_mutations(self.hd,bytes(bad))
 def test_actual_postrun_original_file_tail_and_directory_padding_negatives(self):
  from ac_filesystem import verify_owned_mutations
  from dos_disk_inspect import Volume
  import struct
  actual=(P/'successors/root4589/proof/HD-after.img').read_bytes();start=struct.unpack_from('<I',actual,454)[0]*512;v=Volume(actual[start:]);row=next(r for r in v.files if r['name']=='IO.SYS');tail=start+(v.data_sector+(row['clusters'][-1]-2)*v.spc+v.spc)*512-1;bad=bytearray(actual);bad[tail]^=1;self.assertEqual(Volume(bad[start:]).payloads,v.payloads)
  with self.assertRaises(ValueError):verify_owned_mutations(self.hd,bytes(bad))
  root=start+v.root_sector*512;slot=next(at for at in range(root,root+v.bpb['root_entries']*32,32) if actual[at]==0);bad=bytearray(actual);bad[slot+12]^=1
  with self.assertRaisesRegex(ValueError,'padding changed'):verify_owned_mutations(self.hd,bytes(bad))
 def test_failed_native_stage_and_cancellation_restore_budget(self):
  for failure in [RuntimeError('placeholder'),KeyboardInterrupt('cancel')]:
   app=CollectionApplication(self.reg,self.configured,self.patch,self.floppy,self.hd,self.media,self.service);events=[];original=object();app.preflight=lambda:{'status':'passed'};app.capture_ram=lambda name:events.append(('capture',name));app.write=lambda *a:None
   client=types.SimpleNamespace(client=types.SimpleNamespace(budget=original),put=lambda route:events.append(('put',route)),configs=lambda v:None,get=lambda route:{'U64 Specific Settings':{'CPU Speed':{'values':['64']}}} if route.endswith('/CPU%20Speed') else {'U64 Specific Settings':{'System Mode':'PAL','Turbo Control':'Manual','CPU Speed':'64'}},request=lambda *a:events.append(('request',a)))
   if isinstance(failure,KeyboardInterrupt):
    def diag():raise failure
    app.diag=diag;expected=KeyboardInterrupt
   else:app.diag=lambda:bytes([0xe1])+bytes(18);expected=RuntimeError
   with self.temp() as d:
    with self.assertRaises(expected):app(client,d)
    self.assertIs(client.client.budget,original);report=json.loads((Path(d)/'application-result.json').read_text());self.assertEqual(report['status'],'failed');self.assertTrue(any(e[0]=='capture' for e in events))
 def application_cleanup_case(self,restore_failures=0,install_failure=False,report_failure=False):
  import ac_application
  app=CollectionApplication(self.reg,self.configured,self.patch,self.floppy,self.hd,self.media,self.service);first=KeyboardInterrupt('first application cancel');second=KeyboardInterrupt('second cleanup cancel');original=object()
  class BudgetClient:
   def __init__(self):self.value=original;self.calls=0
   @property
   def budget(self):return self.value
   @budget.setter
   def budget(self,value):
    if value is original:
     self.calls+=1
     if self.calls<=restore_failures:raise second
    elif install_failure:raise first
    self.value=value
  client=types.SimpleNamespace(client=BudgetClient());app.preflight=lambda:(_ for _ in ()).throw(first);app.capture_ram=lambda name:None
  real_dump=ac_application.dump;calls=[]
  def report_dump(path,value):
   if path.name=='application-result.json':
    calls.append(path)
    if report_failure and len(calls)==1:raise second
   return real_dump(path,value)
  with self.temp() as d,patch.object(ac_application,'dump',report_dump):
   with self.assertRaises(KeyboardInterrupt) as caught:app(client,d)
   self.assertIs(caught.exception,first);r=json.loads((Path(d)/'application-result.json').read_text());self.assertEqual(r['status'],'failed');self.assertEqual(r['previous_budget_restored'],restore_failures<3)
   if restore_failures<3:self.assertIs(client.client.budget,original)
   else:self.assertIsNot(client.client.budget,original)
   if report_failure:self.assertEqual(len(calls),2)
 def test_application_double_interrupt_keeps_first_and_restores_budget(self):self.application_cleanup_case(restore_failures=1)
 def test_application_exhausted_restore_preserves_first_truthful_report(self):self.application_cleanup_case(restore_failures=3)
 def test_application_budget_install_interruption_is_protected(self):self.application_cleanup_case(install_failure=True)
 def test_application_report_interruption_preserves_first_independent_report(self):self.application_cleanup_case(report_failure=True)
 def retention_case(self,ram_failure=False,reu_failure=False,helper_failure=False,budget_failures=0):
  import ac_retention,time
  from ac_retention import ACRetention
  events=[];raw=bytearray(65536);h=self.reg.labels['hdc_config']-0x801+2;at=self.reg.labels['hdc_state_start'];raw[at:at+136]=self.configured[h+4:h+140];reu=bytearray(4*1024*1024);reu[0x100000:0x100000+len(self.floppy)]=self.floppy;pkg=self.reg.shadow_metadata['package']
  for i,source in enumerate(pkg['startup_sources']):reu[0x340000+i*2048:0x340000+(i+1)*2048]=self.configured[source-0x801+2:source-0x801+2+2048]
  app=types.SimpleNamespace(clock=time.monotonic,sleep=lambda seconds:None,labels=self.reg.labels,prg=self.configured,shadow_build_metadata=self.reg.shadow_metadata,app_upload_started=True,verify_resident=lambda data:[{'matches':True}],data=self.floppy,hd_source=self.hd,media=self.media,script=types.SimpleNamespace(stage='done'));original=object()
  def read(address,count):
   events.append(('RAM',address,count))
   if ram_failure and address==0 and count==65536:raise OSError('first RAM failure')
   return bytes(raw[address:address+count])
  first_cancel=KeyboardInterrupt('first REU cancel');second_cancel=KeyboardInterrupt('second budget cancel')
  class BudgetClient:
   def __init__(self):self.value=original;self.restore_calls=0
   @property
   def budget(self):return self.value
   @budget.setter
   def budget(self,value):
    if value is original:
     self.restore_calls+=1
     if self.restore_calls<=budget_failures:raise second_cancel
    self.value=value
  client=types.SimpleNamespace(client=BudgetClient(),put=lambda route:events.append(('put',route)),read=read)
  class Service:
   def __init__(self,*a,**k):pass
   def load(self):events.append(('REU-helper-load',))
   def command(self,op,address,count):
    events.append(('REU-read',address))
    if reu_failure and address==0x8000:raise first_cancel
    return bytes(reu[address:address+count])
   def check_code(self):pass
  class Helper:
   def __init__(self,*a,**k):self.closed=False
   def load(self):
    self.assert_order=True;events.append(('HD-helper-load',))
    if helper_failure:raise OSError('first helper failure')
    return {'initial_close_A5':True,'reopened_readonly_A5':True}
   def command(self,op,offset=0,count=0):
    events.append(('HD-op',op,offset,count))
    if op==2:self.closed=True;return b''
    return self_hd[offset:offset+count]
   def mailbox(self):
    b=bytearray(32);b[:4]=b'DHC1';b[4]=0xa5 if self.closed else 0x11;b[8]=0 if self.closed else 1;b[31]=0xa5 if self.closed else 0;return bytes(b)
  self_hd=self.hd
  def snapshot(connect,media,floppy,output,budget):events.append(('FTP',Path(output).name));Path(output).write_bytes(self.hd);return self.hd
  with self.temp() as d,patch.object(ac_retention,'DeadlineDeltaService',Service),patch.object(ac_retention,'HelperSession',Helper),patch.object(ac_retention,'ftp_snapshot',snapshot),patch.object(ac_retention,'verify_collection',lambda *a,**k:{'passed':True,'changed_sectors':[]}):
   hook=ACRetention(app,lambda seconds:None,self.helper,self.hlabels)
   error=None
   try:result=hook.run(client,self.service,d,lambda *a,**k:None)
   except BaseException as e:error=e;result=json.loads((Path(d)/'AC-retention-result.json').read_text())
   if budget_failures>=3:self.assertIsNot(client.client.budget,original)
   else:self.assertIs(client.client.budget,original)
   if budget_failures:
    self.assertIs(error,first_cancel if reu_failure else second_cancel);self.assertEqual(client.client.restore_calls,min(budget_failures+1,3));self.assertEqual(result['status'],'failed');self.assertEqual(result['previous_budget_restored'],budget_failures<3);self.assertTrue(any(e['scope']=='previous_budget_restore' for e in result['errors']))
   if ram_failure:
    self.assertIsInstance(error,OSError);self.assertIn('first RAM failure',str(error));self.assertNotIn(('REU-helper-load',),events);self.assertNotIn(('HD-helper-load',),events);self.assertTrue(result['destructive_helpers_skipped_for_missing_original_RAM'])
   elif reu_failure:
    self.assertIsInstance(error,KeyboardInterrupt);self.assertEqual(str(error),'first REU cancel');self.assertNotIn(('HD-helper-load',),events);self.assertEqual((Path(d)/'reu-changed-before-restoration.partial.bin').stat().st_size,0x8000);self.assertEqual(len(json.loads((Path(d)/'reu-partial-valid-ranges.json').read_text())['ranges']),2);self.assertTrue(result['cancelled'])
   elif helper_failure:
    self.assertIsInstance(error,OSError);self.assertEqual(str(error),'first helper failure');self.assertTrue(result['full_changed_REU_retained']);self.assertTrue(result['native_target2_final_closed']);self.assertEqual(result['status'],'failed')
   elif not budget_failures:
    self.assertIsNone(error);self.assertEqual(result['status'],'passed');self.assertLess(events.index(('RAM',0,65536)),events.index(('REU-helper-load',)));self.assertLess(events.index(('REU-read',0x3fc000)),events.index(('HD-helper-load',)));self.assertTrue(result['all_seven_sources']['passed']);self.assertTrue(result['native_target2_final_closed'])
 def test_retention_order_full_authority_before_HDhelper(self):self.retention_case()
 def test_retention_RAM_failure_skips_destructive_helpers(self):self.retention_case(ram_failure=True)
 def test_retention_REU_interrupt_preserves_prefix_first_error(self):self.retention_case(reu_failure=True)
 def test_retention_helper_failure_keeps_first_error_and_closes(self):self.retention_case(helper_failure=True)
 def test_retention_two_interrupts_preserves_exact_first_and_restores_budget(self):self.retention_case(reu_failure=True,budget_failures=1)
 def test_retention_budget_restore_exhaustion_keeps_first_and_reports_failure(self):self.retention_case(reu_failure=True,budget_failures=3)
 def test_retention_second_cleanup_interrupt_alone_is_failed_with_restored_budget(self):self.retention_case(budget_failures=1)
 def test_helper_EOF_zero_count_does_not_issue_invalid_host_read(self):
  class Client:
   def __init__(self):self.box=bytearray(32);self.box[:4]=b'DHC1';self.box[4]=0x11;self.events=[]
   def put(self,route):pass
   def request(self,method,route,body,kind):
    at=int(route.split('=')[1],16);self.box[at-0x6000:at-0x6000+len(body)]=body
    if at==0x6004 and body==b'G':self.box[4]=0xa5;self.box[17:19]=b'\0\0'
   def read(self,at,count):
    self.events.append((at,count))
    if count==0:raise ValueError('bounded transport forbids zero count')
    return bytes(self.box[at-0x6000:at-0x6000+count])
  client=Client();session=HelperSession(client,self.helper,self.hlabels);session.verify_code=lambda:None;self.assertEqual(session.command(1,20*1024*1024,2),b'');self.assertNotIn((0x6200,0),client.events)
 def test_batched_outer_and_original_readonly_retention_are_separate(self):
  import ac_runner,ac_retention
  from batched_delta_recovery import BatchedDeadlineDeltaService
  from game_recovery import DeadlineDeltaService
  self.assertIs(ac_runner.BatchedDeadlineDeltaService,BatchedDeadlineDeltaService);self.assertIs(ac_retention.DeadlineDeltaService,DeadlineDeltaService);self.assertNotEqual(ac_retention.DeadlineDeltaService,BatchedDeadlineDeltaService)
 def test_synthetic_registries_refuse_concrete_freeze(self):
  from ac_freeze import freeze
  with self.temp() as d:
   with self.assertRaisesRegex(ValueError,'Concrete real staging'):freeze(Path(CONTEXT['offline_arguments']),Path(d)/'guard.json')
   self.assertFalse((Path(d)/'guard.json').exists())
 def test_script_requires_actual_clear_before_accepting_next_output(self):
  script=CollectionScript();s={'ring_used':0,'guest_instructions':0,'prompt':True,'mode':3,'columns':80,'text':'OLD Version 3.30\nC>','cursor_row':1,'cursor_column':2};script.observe(s);self.assertEqual(script.step,0);s['guest_instructions']=5000;self.assertEqual(script.observe(s),[]);self.assertEqual(script.step,0);s['text']='C>';s['cursor_row']=0;words=script.observe(s);self.assertEqual(script.step,1);self.assertEqual(words,keys('VER\r'));s['guest_instructions']=10000
  with self.assertRaisesRegex(ValueError,'output missing'):script.observe(s)
 def test_outer_final_report_second_interrupt_preserves_original(self):
  import ac_runner
  first=KeyboardInterrupt('first outer cancel');second=KeyboardInterrupt('second report cancel');calls=[]
  with self.temp() as d:
   out=Path(d)/'run';out.mkdir();args={'host':'10.0.0.79','output':str(out),'media_manifest':'unused','staging_manifest':'unused','helper_staging_manifest':'unused'};app=types.SimpleNamespace(clock=lambda:0,prg=b'native',data=b'A',hd_source=b'HD',service_prg=b'service');retention=types.SimpleNamespace(final_HD=b'HD',interruption=first)
   def dump(path,value):
    if path.name=='result.json':
     calls.append(path)
     if len(calls)==1:raise second
     path.write_text(json.dumps(value))
   with patch.object(ac_runner,'validate',lambda args:(app,None,None,{},None,None,None,None,None)),patch.object(__import__('ac_freeze'),'verify_guard',lambda *a:{'files':{}}),patch.object(ac_runner,'read_json',lambda *a:{}),patch.object(ac_runner,'connect_factory',lambda *a:None),patch.object(ac_runner,'verify_stage_FTP',lambda *a,**k:{'passed':True}),patch.object(ac_runner,'ACRetention',lambda *a:retention),patch.object(ac_runner,'recover_honestly',lambda *a,**k:({'status':'failed'},first)),patch.object(ac_runner,'dump',dump):
    with self.assertRaises(KeyboardInterrupt) as caught:ac_runner.run(args,'unused','unused')
    self.assertIs(caught.exception,first);self.assertEqual(len(calls),2);r=json.loads((out/'result.json').read_text());self.assertEqual(r['status'],'failed');self.assertEqual(r['outer_report_errors'][0]['error'],repr(second))
 def test_pure_guard_changedhash_and_arguments_rejected(self):
  with self.temp() as d:
   out=Path(d)/'future';args={'host':'10.0.0.79','output':str(out)};file=Path(d)/'input';file.write_bytes(b'original');pins={str(file):{'bytes':8,'sha256':sha(b'original')}}
   for module in list(sys.modules.values()):
    name=getattr(module,'__file__',None)
    if name:
     q=Path(name).resolve()
     if q.suffix=='.py' and q.is_relative_to(bootstrap.PROJECT):pins[str(q)]={'bytes':q.stat().st_size,'sha256':sha(q.read_bytes())}
   guard={'purpose':'genuineDOS33-A-plus-C20MiB-physical-development','host':args['host'],'output':str(out),'arguments':args,'source_only_cache_must_remain_absent':str(P/'.source-import-cache-disabled'),'files':pins};path=Path(d)/'guard.json';path.write_text(json.dumps(guard));digest=sha(path.read_bytes());verify_guard(path,digest,args)
   with self.assertRaises(ValueError):verify_guard(path,'0'*64,args)
   with self.assertRaises(ValueError):verify_guard(path,digest,{**args,'host':'10.0.0.80'})
   file.write_bytes(b'altered!')
   with self.assertRaises(ValueError):verify_guard(path,digest,args)
if __name__=='__main__':unittest.main(verbosity=2)
