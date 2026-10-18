import sys,os
from pathlib import Path
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.pycache_prefix=str(P/('.absent-sc-tests-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import ctypes as C,struct,json,unittest
from test_controller import Controller,L
from test_actual import bind,ptr,u8,u32
bind('dos64_uci_model_stale',None,[ptr,u8]);bind('dos64_uci_model_block',None,[ptr,ptr,C.c_size_t,ptr,C.c_size_t]);bind('bulk_model_open',u8,[ptr,u8]);bind('bulk_model_seed_open',None,[ptr,u8,C.c_char_p,u8,u32])
RESULT={}
class StartupClose(unittest.TestCase):
 def setUp(self):self.f=Controller();self.tick=500
 def tearDown(self):self.f.guard();self.f.close()
 def seed(self,targets):
  for t in targets:
   p=b'/usb1/Old Session/KEEP'+str(t).encode()+b'.BIN';d=b'unchanged prior bytes'*7;self.f.seedfile(p,d);L.bulk_model_seed_open(self.f.m,t,p,3,7)
 def poll(self):
  self.tick+=1;self.f.write('_sc_now',struct.pack('<H',(self.tick//32)&65535));return self.f.call('_sc_poll')
 def finish(self):
  for _ in range(3000):
   r=self.poll()
   if r!=1:return r
  raise AssertionError('bounded startup close polls')
 def obs(self):
  f=self.f;return {'observation':f.read('_sc_state',6).hex(),'firmwareopen':[L.bulk_model_open(f.m,t) for t in [1,2]],'files_handle':f.byte('_files_handle'),'uci':f.byte('_uci_state'),'wire':L.bulk_model_commands(f.m),'abort':L.dos64_uci_model_count(f.m,2)}
 def test_exact_no_file_both_known_closed_and_one_shot(self):
  f=self.f;self.assertEqual(f.call('_sc_begin',a=0),0);self.assertEqual(L.bulk_model_commands(f.m),0)
  self.assertEqual(f.call('_sc_begin',a=0xa5),1);self.assertEqual(self.finish(),2);self.assertEqual(f.call('_sc_ready'),1)
  self.assertEqual(self.obs()['firmwareopen'],[0,0]);self.assertEqual(f.read('_sc_state',6),bytes([2,0,0,2,3,0]))
  self.assertEqual([(L.bulk_model_command(f.m,i,0),L.bulk_model_command(f.m,i,1)) for i in range(2)],[(1,3),(2,3)])
  self.assertEqual(f.call('_sc_begin',a=0xa5),0);self.assertEqual(L.bulk_model_commands(f.m),2)
  RESULT[self._testMethodName]=self.obs()
 def test_seeded_each_and_both_channels_close_without_file_mutation(self):
  for ts in [(1,),(2,),(1,2)]:
   self.f.close();self.f=Controller();self.seed(ts);f=self.f
   self.assertEqual(f.call('_sc_begin',a=0xa5),1);self.assertEqual(self.finish(),2);self.assertEqual(f.call('_sc_ready'),1)
   self.assertEqual(self.obs()['firmwareopen'],[0,0]);self.assertEqual(L.bulk_model_commands(f.m),2)
   for t in ts:
    p=b'/usb1/Old Session/KEEP'+str(t).encode()+b'.BIN';d=b'unchanged prior bytes'*7;out=C.create_string_buffer(len(d));self.assertTrue(L.bulk_model_read(f.m,p,out,len(d)));self.assertEqual(out.raw,d)
  RESULT[self._testMethodName]=self.obs()
 def test_public_done_closed_forgery_has_no_authority(self):
  f=self.f;self.seed((1,2));self.assertEqual(f.call('_sc_begin',a=0xa5),1)
  f.write('_sc_state',bytes([2,0,0,2,3,0]));self.assertEqual(f.call('_sc_ready'),0)
  self.assertEqual(self.poll(),1);self.assertEqual(f.byte('_sc_state'),1)
  self.assertEqual(self.finish(),2);self.assertEqual(f.call('_sc_ready'),1)
  RESULT[self._testMethodName]=self.obs()
 def test_cancel_defers_safety_closes_and_revokes_readiness(self):
  f=self.f;self.seed((1,2));f.call('_sc_begin',a=0xa5);f.call('_sc_cancel');f.call('_sc_cancel')
  self.assertEqual(self.finish(),3);self.assertEqual(f.call('_sc_ready'),0);self.assertEqual(self.obs()['firmwareopen'],[0,0]);self.assertEqual(L.bulk_model_commands(f.m),2);self.assertEqual(f.byte('_sc_error'),1);self.assertEqual(f.byte('_sc_closed'),3);self.assertEqual(L.dos64_uci_model_count(f.m,2),0)
  RESULT[self._testMethodName]=self.obs()
 def test_status_failure_before_cancel_preserves_first_and_unknown(self):
  f=self.f;self.seed((1,2));f.faults(fail=1);f.call('_sc_begin',a=0xa5)
  for _ in range(1000):
   self.poll()
   if f.byte('_sc_error'):break
  self.assertEqual(f.byte('_sc_error'),3);f.call('_sc_cancel');self.assertEqual(self.finish(),3)
  self.assertEqual(f.byte('_sc_error'),3);self.assertEqual(f.byte('_sc_cleanup'),0);self.assertEqual(f.call('_sc_ready'),0);self.assertEqual(L.bulk_model_commands(f.m),1);self.assertEqual(self.obs()['firmwareopen'],[1,1])
  RESULT[self._testMethodName]=self.obs()
 def test_cancel_before_status_records_cleanup_without_replacing_cancel(self):
  f=self.f;self.seed((1,2));f.faults(fail=1);f.call('_sc_begin',a=0xa5);f.call('_sc_cancel');self.assertEqual(self.finish(),3)
  self.assertEqual(f.byte('_sc_error'),1);self.assertEqual(f.byte('_sc_cleanup'),3);self.assertEqual(f.call('_sc_ready'),0);self.assertEqual(L.bulk_model_commands(f.m),1)
  RESULT[self._testMethodName]=self.obs()
 def test_no_file_with_extra_data_is_protocol_failure(self):
  f=self.f;f.faults(reply=1,kind=5);f.call('_sc_begin',a=0xa5);self.assertEqual(self.finish(),3)
  self.assertEqual(f.byte('_sc_error'),4);self.assertEqual(f.byte('_sc_closed'),0);self.assertEqual(f.call('_sc_ready'),0);self.assertEqual(L.bulk_model_commands(f.m),1);self.assertEqual(L.dos64_uci_model_count(f.m,2),1)
  RESULT[self._testMethodName]=self.obs()
 def test_timeout_wrap_then_cancel_retains_transport_unknown(self):
  f=self.f;self.seed((1,2));f.write('_uci_timeout',struct.pack('<H',4));f.write('_uci_recovery_timeout',struct.pack('<H',3));f.write('_sc_now',struct.pack('<H',65534));f.call('_sc_begin',a=0xa5);L.dos64_uci_model_stuck(f.m,1)
  f.write('_sc_now',struct.pack('<H',3));f.call('_sc_poll');self.assertEqual(f.byte('_sc_error'),2);f.call('_sc_cancel');L.dos64_uci_model_stuck(f.m,0)
  for n in range(4,20):f.write('_sc_now',struct.pack('<H',n));r=f.call('_sc_poll')
  self.assertEqual(r,3);self.assertEqual(f.byte('_sc_error'),2);self.assertEqual(f.byte('_sc_transport'),3);self.assertEqual(f.call('_sc_ready'),0);self.assertEqual(f.byte('_sc_closed'),0);self.assertEqual(L.dos64_uci_model_count(f.m,2),1)
  RESULT[self._testMethodName]=self.obs()
 def test_wrong_ID_refuses_unknown_no_retry(self):
  f=self.f;L.dos64_uci_model_enable(f.m,0xdf1c,3,0x77);self.assertEqual(f.call('_sc_begin',a=0xa5),1);self.assertEqual(f.call('_sc_poll'),3);self.assertEqual(f.call('_sc_ready'),0);self.assertEqual(f.call('_sc_begin',a=0xa5),0);self.assertEqual(L.bulk_model_commands(f.m),0)
  RESULT[self._testMethodName]=self.obs()
 def test_stale_reset_queue_refuses_without_OPEN_or_retry(self):
  for state in [0x10,0x20]:
   self.f.close();self.f=Controller();f=self.f;self.seed((1,2))
   if state==0x20:L.dos64_uci_model_block(f.m,None,0,b'00,OK',5)
   L.dos64_uci_model_stale(f.m,state);f.call('_sc_begin',a=0xa5);self.assertEqual(self.finish(),3)
   self.assertEqual(f.byte('_sc_error'),2);self.assertEqual(f.byte('_sc_transport'),6);self.assertEqual(f.byte('_sc_closed'),0);self.assertEqual(f.call('_sc_ready'),0)
   self.assertEqual(self.obs()['firmwareopen'],[1,1]);self.assertEqual(L.bulk_model_commands(f.m),0);self.assertEqual(L.dos64_uci_model_count(f.m,2),1);self.assertEqual(f.call('_sc_begin',a=0xa5),0)
  RESULT[self._testMethodName]=self.obs()
 def test_actual_cc65_callers_balance_stack_and_return_private_state(self):
  self.f.close();self.f=Controller('sc-abi');f=self.f;self.seed((1,2))
  self.assertEqual(f.call('_sc_abi_begin'),1)
  for _ in range(3000):
   self.tick+=1;f.write('_sc_now',struct.pack('<H',self.tick//32));r=f.call('_sc_abi_poll')
   if r!=1:break
  self.assertEqual(r,2);self.assertEqual(f.call('_sc_abi_ready'),1);self.assertEqual(self.obs()['firmwareopen'],[0,0]);self.assertEqual(f.read('sp',2),b'\xff\xcf')
  RESULT[self._testMethodName]=self.obs()
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(StartupClose));(P.parent/'STARTUP_CLOSE_RESULTS.json').write_text(json.dumps(RESULT,indent=2)+'\n');sys.exit(not r.wasSuccessful())
