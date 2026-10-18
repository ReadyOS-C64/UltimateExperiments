from pathlib import Path
import os,sys
sys.dont_write_bytecode=True
sys.pycache_prefix=str(Path(__file__).resolve().parent/('.absent-session-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import ctypes as C,struct,unittest,json,zlib
from test_source_load import DATA,PATHS,ADDR
from test_capsule import UI,L,reu
REPORT={}
class Session(UI):
 def begin(self,timeout=1000):
  self.f.write('_su_timeout',struct.pack('<H',timeout));return self.call('_su_begin')
 def poll(self):
  L.dos64_cia_clock_advance(self.f.m,1024);self.call('_su_poll');self.state=self.call('_su_state');return self.state
 def ready(self):
  if self.call('_db_state')!=1:return self.state
  for _ in range(3000):
   self.poll()
   if self.call('_db_state')!=1:return self.state
  raise AssertionError('bounded native directory')
 def finish(self):
  for _ in range(100000):
   if self.call('_su_state')!=1:return self.call('_su_state')
   self.poll()
  raise AssertionError('bounded session/cleanup')
 def select(self):
  self.directory(b'/',[(16,b'Home')]);self.directory(b'/Home',[(32,b'DOS 1.img'),(32,b'DOS 2.img'),(32,b'DOS 3.img')])
  assert self.begin()==1;self.ready();self.key(0,1);self.key(0,4)
  self.key(0,1);self.key(0,7);self.key(0,1);self.key(0,7);self.key(0,7);self.key(0,1)
  self.key(0,4);self.key(0,7);self.key(0,1);self.key(0,1)
  assert self.call('_ss_state')==2 and self.call('_su_state')==1
 def seed(self):
  for path,data in zip(PATHS,DATA):L.bulk_model_seed(self.f.m,path,data,len(data))
 def source_phase(self,phase):
  for _ in range(100000):
   if self.f.read('_sl_result',6)[2]==phase:return
   assert self.poll()==1
  raise AssertionError('bounded source phase')
class Actual(unittest.TestCase):
 def setUp(self):self.u=Session();self.u.seed()
 def tearDown(self):self.u.close()
 def test_real_CIA_selection_all_five_PRIVATE_receipts_and_bound_home(self):
  u=self.u;u.select();u.f.write('_su_timeout',b'\0\0');self.assertEqual(u.finish(),2);self.assertEqual(u.call('_su_error'),0);self.assertEqual(u.call('_su_closed_quiet'),1)
  raw=reu(u);facts=[]
  for k,data in enumerate(DATA):
   u.f.write('_sl_kind',bytes([k]));u.f.write('_sl_generation',raw[8:10]);u.f.write('_sl_identity',raw[700:704]);self.assertEqual(u.call('_sl_fact'),1);f=struct.unpack('<HIII',u.f.read('_sl_receipt',14));self.assertEqual(f,(1,int.from_bytes(raw[700:704],'little'),len(data),zlib.crc32(data)));facts.append(f)
   b=C.create_string_buffer(len(data));self.assertEqual(L.dos64_reu_read(u.f.m,ADDR[k],b,len(data)),1);self.assertEqual(b.raw,data)
  self.assertEqual(u.f.read('_so_request',135)[7:].split(b'\0')[0],b'/Home');self.assertEqual(u.begin(),0)
  commands=[[L.bulk_model_command(u.f.m,i,j)for j in range(2)]for i in range(L.bulk_model_commands(u.f.m))];self.assertTrue(all(c[1]not in [5,0x22]for c in commands));self.assertTrue(all(L.bulk_model_command(u.f.m,i,2)==1 for i,c in enumerate(commands)if c[1]==2));REPORT['complete']={'facts':facts,'commands':len(commands),'soft_stack_min':hex(u.f.soft_min)}
 def test_selection_public_ERROR_forgery_cannot_grant_or_fail(self):
  u=self.u;u.directory(b'/',[]);self.assertEqual(u.begin(),1);u.f.write('_ss_error',b'\xff');u.f.write('_ss_stage',b'\6');u.poll();self.assertEqual(u.call('_su_state'),1);self.assertEqual(u.call('_su_error'),0)
 def test_source_public_DONE_and_request_forgery_does_not_skip_PRIVATE_work(self):
  u=self.u;u.select();u.source_phase(3);u.f.write('_sl_result',b'\2'+bytes(5));u.f.write('_sl_kind',b'\4');u.f.write('_sl_timeout',b'\0\0');self.assertEqual(u.finish(),2);self.assertEqual(u.call('_su_error'),0);self.assertEqual(u.call('_bc_files_closed'),1)
 def test_corrupt_LOAD_preserves_first_SOURCE_cause_and_closes_source(self):
  u=self.u;L.bulk_model_faults(u.f.m,-1,-1,-1,0,0);u.select();self.assertEqual(u.finish(),3);self.assertEqual(u.call('_su_error'),0x34);self.assertEqual(u.call('_su_closed_quiet'),1);self.assertEqual(L.bulk_model_open(u.f.m,1),0);self.assertEqual(u.begin(),0)
 def test_RunStop_during_selection_drains_directory_before_terminal(self):
  u=self.u;u.directory(b'/',[(16,b'Home')]);self.assertEqual(u.begin(),1);L.dos64_host_input_model_keys(u.f.m,bytes(7)+b'\x80');self.assertEqual(u.finish(),3);self.assertEqual(u.call('_su_error'),0x13);self.assertEqual(u.call('_su_closed_quiet'),1)
 def test_RunStop_source_drain_never_DONE_and_cleanup_authority_PRIVATE(self):
  u=self.u;u.select();u.source_phase(4);L.dos64_host_input_model_keys(u.f.m,bytes(7)+b'\x80');self.assertEqual(u.finish(),3);self.assertEqual(u.call('_su_error'),0x35);self.assertEqual(u.call('_su_closed_quiet'),1)
 def test_corrupt_capsule_after_publish_refuses_any_SOURCE_OPEN(self):
  u=self.u;u.select();self.assertEqual(u.call('_sq_state'),2);L.dos64_reu_poke(u.f.m,0x2c0020,ord('X'));before=L.bulk_model_commands(u.f.m);self.assertEqual(u.finish(),3);self.assertEqual(u.call('_su_error'),0x26);self.assertEqual(L.bulk_model_commands(u.f.m),before);self.assertEqual(u.call('_su_closed_quiet'),1)
 def test_clock_incoherence_is_CAPSULE_firstcause_without_file_OPEN(self):
  u=self.u;u.select();before=L.bulk_model_commands(u.f.m)
  L.dos64_cia_clock_step.argtypes=[C.c_void_p,C.c_uint32];L.dos64_cia_clock_step.restype=None;L.dos64_cia_clock_step(u.f.m,0x40000)
  self.assertEqual(u.finish(),3);self.assertEqual(u.call('_su_error'),0x24);self.assertEqual(u.call('_su_closed_quiet'),1);self.assertEqual(L.bulk_model_commands(u.f.m),before)
 def test_cleanup_is_bounded_and_retains_first_INFO_error_when_transport_stuck(self):
  u=self.u;L.bulk_model_seed(u.f.m,PATHS[0],DATA[0][:64],64);u.select()
  for _ in range(1000):
   u.poll()
   if u.call('_su_error'):break
  self.assertEqual(u.call('_su_error'),0x32);self.assertEqual(u.call('_su_state'),1)
  L.dos64_uci_model_stuck(u.f.m,1);polls=0
  while u.call('_su_state')==1 and polls<300:u.poll();polls+=1
  self.assertEqual(u.call('_su_state'),3);self.assertEqual(u.call('_su_error'),0x32);self.assertEqual(u.call('_su_closed_quiet'),0);self.assertLessEqual(polls,258);REPORT['bounded_cleanup_polls']=polls
 def test_timeout_input_boundaries_refuse_without_consuming_selection(self):
  u=self.u
  for n in [0,32768,65535]:self.assertEqual(u.begin(n),0);self.assertEqual(u.call('_su_state'),0)
  self.assertEqual(u.begin(1),1)
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Actual));Path('../UI_SESSION_RESULTS.json').write_text(json.dumps(REPORT,indent=2)+'\n');sys.exit(not r.wasSuccessful())
