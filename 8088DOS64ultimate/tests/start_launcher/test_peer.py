import sys,os
from pathlib import Path
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.pycache_prefix=str(P/('.absent-peer-cache-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import json,unittest
import struct
from test_controller import Controller,L
from test_actual import bind,ptr,u8
bind('bulk_model_open',u8,[ptr,u8])
EVIDENCE={}
def snap(f):
 return {'controller':f.read('_lc_result',16).hex(),'leaf':list(f.result()),'files':f.byte('_files_handle'),'uci':f.byte('_uci_state'),'commands':L.bulk_model_commands(f.m),'target1_open':L.bulk_model_open(f.m,1),'abort':L.dos64_uci_model_count(f.m,2),'ready':f.reu(0x3ff005,1).hex()}
def load_pending(f):
 for _ in range(3000):
  if f.result()[0]==1 and f.result()[7]==0x21:return
  f.poll_lc()
 raise AssertionError('LOAD phase not reached')
class Peer(unittest.TestCase):
 def setUp(self):self.f=Controller()
 def tearDown(self):self.f.guard();self.f.close()
 def closed(self):
  f=self.f;self.assertEqual(f.lc()[0],3);self.assertEqual(f.lc()[2],0)
  self.assertEqual(f.byte('_files_handle'),0);self.assertEqual(L.bulk_model_open(f.m,1),0)
  self.assertIn(f.byte('_uci_state'),[0,9]);self.assertEqual(f.reu(0x3ff005,1),b'\0')
 def test_forged_done_closed_cannot_skip_active_leaf_cleanup(self):
  f=self.f;f.seed_inputs();self.assertEqual(f.call('_lc_begin'),1);load_pending(f)
  before=snap(f);self.assertEqual(before['target1_open'],1)
  f.write('_br_result',bytes([2,0,0,0])+bytes(14));f.poll_lc()
  pending=snap(f);self.assertEqual(f.lc()[0],1);self.assertEqual(f.byte('_files_handle'),1)
  f.write('_br_result',bytes([2,0,0,0])+bytes(14));f.call('_lc_cancel');f.call('_lc_cancel');f.finish_lc()
  self.closed();self.assertEqual(f.lc()[1],8);self.assertEqual(L.dos64_uci_model_count(f.m,2),1)
  EVIDENCE[self._testMethodName]={'before':before,'after_forgery':pending,'terminal':snap(f)}
 def test_status_before_cancel_preserves_first_leaf_cause(self):
  f=self.f;f.seed_inputs();f.faults(fail=3);self.assertEqual(f.call('_lc_begin'),1)
  for _ in range(3000):
   f.poll_lc()
   if f.result()[1]:break
  else:raise AssertionError('status failure not reached')
  before=snap(f);self.assertEqual(f.result()[:2],(1,3));self.assertEqual(f.lc()[1],2)
  self.assertEqual(f.read('_lc_result',16)[13:15],b'\x21\x03')
  f.call('_lc_cancel');f.call('_lc_cancel');f.faults();f.finish_lc();self.closed()
  self.assertEqual(f.lc()[1],2);self.assertEqual(f.read('_lc_result',16)[13:15],b'\x21\x03')
  self.assertEqual(L.dos64_uci_model_count(f.m,2),1)
  EVIDENCE[self._testMethodName]={'status_busy':before,'terminal':snap(f)}
 def test_cancel_before_status_preserves_cancel(self):
  f=self.f;f.seed_inputs();f.faults(fail=3);self.assertEqual(f.call('_lc_begin'),1);load_pending(f)
  for _ in range(3000):
   if L.bulk_model_commands(f.m)==3:break
   f.poll_lc()
  else:raise AssertionError('LOAD command not accepted')
  self.assertEqual(f.result()[1],0);f.call('_lc_cancel');before=snap(f)
  self.assertEqual(f.lc()[1],8);f.call('_lc_cancel');f.finish_lc();self.closed()
  self.assertEqual(f.lc()[1],8);self.assertEqual(f.read('_lc_result',16)[13:16],bytes(3))
  self.assertEqual(L.dos64_uci_model_count(f.m,2),1)
  EVIDENCE[self._testMethodName]={'cancel_first':before,'terminal':snap(f)}
 def test_protocol_before_cancel_preserves_first_and_quiet_cleanup(self):
  f=self.f;f.seed_inputs();f.faults(reply=3,kind=6);self.assertEqual(f.call('_lc_begin'),1)
  for _ in range(3000):
   f.poll_lc()
   if f.result()[1]:break
  else:raise AssertionError('protocol failure not reached')
  before=snap(f);self.assertEqual(f.result()[1],4);self.assertEqual(f.lc()[1],2)
  self.assertEqual(f.read('_lc_result',16)[13:15],b'\x21\x04')
  # BUSY recovery must not issue CLOSE before the leaf reaches terminal.
  if f.result()[0]==1:self.assertEqual(L.bulk_model_commands(f.m),3)
  f.call('_lc_cancel');f.faults();f.finish_lc();self.closed()
  self.assertEqual(f.lc()[1],2);self.assertEqual(f.read('_lc_result',16)[13:15],b'\x21\x04')
  self.assertEqual(L.dos64_uci_model_count(f.m,2),1)
  EVIDENCE[self._testMethodName]={'protocol_first':before,'terminal':snap(f)}
 def test_transport_before_cancel_preserves_first_transport(self):
  f=self.f;f.seed_inputs();f.write('_uci_timeout',struct.pack('<H',4));f.write('_uci_recovery_timeout',struct.pack('<H',20))
  self.assertEqual(f.call('_lc_begin'),1);load_pending(f)
  for _ in range(3000):
   if L.bulk_model_commands(f.m)==3:break
   f.poll_lc()
  else:raise AssertionError('actual LOAD not reached')
  L.dos64_uci_model_stuck(f.m,1);f.write('_lc_now',struct.pack('<H',509));f.tick=9*32;f.call('_lc_poll')
  before=snap(f);self.assertEqual(f.result()[1:3],(2,3));self.assertEqual(f.lc()[1],2)
  self.assertEqual(f.read('_lc_result',16)[13:16],b'\x21\x02\x03')
  f.call('_lc_cancel');L.dos64_uci_model_stuck(f.m,0);f.finish_lc();self.closed()
  self.assertEqual(f.read('_lc_result',16)[13:16],b'\x21\x02\x03');self.assertEqual(L.dos64_uci_model_count(f.m,2),1)
  EVIDENCE[self._testMethodName]={'transport_first':before,'terminal':snap(f)}
 def test_uninitialized_CRC_fails_closed_without_anchor(self):
  f=self.f;f.seed_inputs();self.assertEqual(f.call('_lc_begin'),1)
  for _ in range(5000):
   if f.lc()[3]==3 and f.lc()[4]==3:break
   f.poll_lc()
  else:raise AssertionError('main closed CRC phase not reached')
  self.assertEqual(f.result()[3],0);f.poke('c32_ready',0);f.poll_lc();self.closed()
  self.assertEqual(f.lc()[1],7);self.assertEqual(f.byte('_c32_error'),1)
  EVIDENCE[self._testMethodName]={'terminal':snap(f)}
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Peer))
 (P.parent/'PEER_RESULTS.json').write_text(json.dumps(EVIDENCE,indent=2)+'\n')
 sys.exit(not r.wasSuccessful())
