import sys,os
from pathlib import Path
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.pycache_prefix=str(P/('.absent-ini-io-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import ctypes as C,struct,unittest
from test_actual import L,Regs,bind,ptr,u8,u32
from test_ini_overlay import Integrated
from test_controller import HOME
bind('ini_model_missing_status',None,[ptr,ptr,u32]);bind('bulk_model_open',u8,[ptr,u8])
PATH=HOME+b'/DOS64.INI';ABSENT=b"FILE DOESN'T EXIST";assert len(ABSENT)==18
class IO(Integrated):
 def __init__(self):
  super().__init__();self.overlay_inputs();assert self.call('_lc_begin')==1;assert self.finish_lc()[:3]==b'\3\6\0'
 def argcall(self,n,value):
  ret=self.at('fixture_return')-1;L.dos64_poke(self.m,0x1ff,ret>>8);L.dos64_poke(self.m,0x1fe,ret&255);L.dos64_set_regs(self.m,Regs(self.at(n),0xfd,value&255,value>>8,0x93,0x24,0,0));L.dos64_clear_writes(self.m);r=L.dos64_run(self.m,self.at('fixture_return'),12_000_000);assert not r.status,(n,r.status,hex(r.regs.pc));assert self.read('sp',2)==b'\xff\xcf';self.guard();return r.regs.a
 def begin(self,data=None):
  if data is not None:self.seedfile(PATH,data)
  self.write('_d64_path_output',PATH.ljust(128,b'\0'));self.write('_ii_now',struct.pack('<H',1000));return self.argcall('_ii_begin',self.at('_d64_path_output'))
 def poll_io(self):
  self.tick+=1;self.write('_ii_now',struct.pack('<H',1000+self.tick//32));self.call('_ii_poll')
 def finish_io(self):
  for _ in range(10000):
   if self.call('_ii_state')!=1:return self.call('_ii_state')
   self.poll_io()
  raise AssertionError('INI bounded poll')
 def closed(self):assert self.byte('_files_handle')==0 and L.bulk_model_open(self.m,1)==0 and self.call('_ii_cleanup')==0
class Actual(unittest.TestCase):
 def setUp(self):self.f=IO()
 def tearDown(self):self.f.guard();self.f.close()
 def test_default_missing_exact_firmware_status_has_owned_CLOSE(self):
  f=self.f;before=L.bulk_model_commands(f.m);self.assertEqual(f.begin(),1);self.assertEqual(f.finish_io(),2);self.assertEqual(f.call('_ii_columns'),80);f.closed();self.assertEqual(L.bulk_model_commands(f.m)-before,2)
 def test_present_empty40_and80_actual_parser(self):
  for data,columns in [(b'',80),(b'[emulator]\ninitial_columns=40\n',40),(b'[Emulator]\r\nschema=1\r\ninitial_columns=80',80)]:
   f=IO()
   try:self.assertEqual(f.begin(data),1);self.assertEqual(f.finish_io(),2);self.assertEqual(f.call('_ii_columns'),columns);f.closed();self.assertEqual(f.call('_ii_begin'),0)
   finally:f.close()
 def test_all_missing_status_truncations_extensions_and_other_errors_refused(self):
  for status in [ABSENT[:n]for n in range(18)]+[ABSENT+b'X',ABSENT+b'\0',b"PATH DOESN'T EXIST",b'ACCESS DENIED',b"82,FILE DOESN'T EXIST"]:
   f=IO()
   try:L.ini_model_missing_status(f.m,status,len(status));self.assertEqual(f.begin(),1);self.assertEqual(f.finish_io(),3,status);self.assertEqual(f.call('_ii_columns'),0);self.assertEqual(f.call('_ii_error'),1);f.closed()
   finally:f.close()
 def test_native_split_line_chunk_and_full1024_bound(self):
  for data,columns in [(b'#'+b'x'*61+b'\n[emulator]\ninitial_columns=40\n',40),(b'#'+b'x'*126+b'\n',80),((b'#'+b'x'*126+b'\n')*8,80)]:
   f=IO()
   try:self.assertEqual(f.begin(data),1);self.assertEqual(f.finish_io(),2);self.assertEqual(f.call('_ii_columns'),columns);f.closed()
   finally:f.close()
 def test_malformed_and_oversize_fail_without_defaults(self):
  for data in [b'[emulator]\ninitial_columns=41',b'[emulator]\nunknown=40',b'[emulator]\nschema=2',b'\xef\xbb\xbf[emulator]',b'#'+b'x'*128,b'x'*1025]:
   f=IO()
   try:self.assertEqual(f.begin(data),1);self.assertEqual(f.finish_io(),3);self.assertEqual(f.call('_ii_columns'),0);self.assertIn(f.call('_ii_error'),[1,2]);f.closed()
   finally:f.close()
 def test_short_CPU_read_fails_and_safety_CLOSE_preserves_cause(self):
  f=self.f;index=L.bulk_model_commands(f.m)+3;f.faults(short=index);self.assertEqual(f.begin(b'[emulator]\ninitial_columns=40\n'),1);self.assertEqual(f.finish_io(),3);self.assertEqual(f.call('_ii_error'),1);f.closed()
 def test_public_leaf_DONE_and_parser_output_forgery_cannot_skip_IO(self):
  f=self.f;self.assertEqual(f.begin(b'[emulator]\ninitial_columns=40\n'),1);f.write('_br_result',bytes([2,0,0,0])+bytes(14));f.write('_ni_output_columns',b'\x50');f.poll_io();self.assertEqual(f.call('_ii_state'),1);self.assertEqual(f.finish_io(),2);self.assertEqual(f.call('_ii_columns'),40);f.closed()
 def test_cancel_once_closes_and_cannot_publish(self):
  f=self.f;self.assertEqual(f.begin(b'[emulator]\ninitial_columns=40\n'),1);f.call('_ii_cancel');f.call('_ii_cancel');self.assertEqual(f.finish_io(),3);self.assertEqual(f.call('_ii_error'),3);self.assertEqual(f.call('_ii_columns'),0);f.closed();self.assertEqual(L.dos64_uci_model_count(f.m,2),1)
 def test_sticky_failed_clock_bounds_unknown_drain_after_recovery_input(self):
  f=self.f;self.assertEqual(f.begin(b'[emulator]\ninitial_columns=40\n'),1);L.dos64_uci_model_stuck(f.m,1);f.call('_ii_clock_fail')
  for _ in range(256):f.call('_ii_poll')
  self.assertEqual(f.call('_ii_state'),3);self.assertEqual(f.call('_ii_error'),4);self.assertEqual(f.call('_ii_cleanup'),1);self.assertEqual(f.call('_ii_columns'),0)
if __name__=='__main__':unittest.main(verbosity=2)
