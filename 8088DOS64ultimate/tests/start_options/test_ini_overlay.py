import sys,os
from pathlib import Path
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.pycache_prefix=str(P/('.absent-ini-overlay-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import ctypes as C,struct,unittest,json,zlib
from test_actual import F,L
from test_controller import Controller,HOME
class Integrated(Controller):
 def guard(self):
  smc=set()
  for n in ['uci_status_read','uci_control_write','uci_id_read','uci_command_write','uci_data_read','uci_stat_read','read','store']:smc.update([self.at(n)+1,self.at(n)+2])
  bs=self.at('__BSS_RUN__');be=self.at('__DEVICESTATE_RUN__')+self.at('__DEVICESTATE_SIZE__');zp_end=self.at('regbank')+6
  assert zp_end<=0x3e
  lo=self.at('__PRELAUNCH_RUN__');hi=self.at('__PRELAUNCH_RO_RUN__')+self.at('__PRELAUNCH_RO_SIZE__')
  allowed=lambda a:a in [0,1]or 0x20<=a<zp_end or 0x100<=a<0x200 or bs<=a<be or lo<=a<hi or self.at('_br_config')<=a<self.at('_br_config')+134 or 0xcd00<=a<0xd000 or 0xc000<=a<0xc800 or 0xc900<=a<0xcd00 or 0xdf00<=a<=0xdf0a or a in [0xdf1c,0xdf1d]or a in smc
  if not hasattr(self,'write_mask'):self.write_mask=bytes(int(allowed(a))for a in range(65536))
  bad=L.lc_check_writes(self.m,self.write_mask)
  assert bad==65536,('unexpected native write',hex(bad))
  assert (L.dos64_peek(self.m,0)&7)==7 and (L.dos64_peek(self.m,1)&7)==5
 def overlay_inputs(self,asset=None):
  self.asset=(P/'START.INO').read_bytes();self.seedfile(HOME+b'/START.INO',self.asset if asset is None else asset)
  self.seedfile(HOME+b'/DOS64.CFG',bytes(576));self.control();self.write('_lc_now',struct.pack('<H',500))
 def ram(self,a,n):return bytes(L.dos64_peek(self.m,a+i)for i in range(n))
class Actual(unittest.TestCase):
 def setUp(self):self.f=Integrated()
 def tearDown(self):self.f.guard();self.f.close()
 def test_disabled_profile_still_sends_no_commands(self):
  f=self.f;self.assertEqual(f.call('_lc_begin'),0);self.assertEqual(L.bulk_model_commands(f.m),0)
 def test_verified_overlay_calls_real_CFG_validator_and_parser(self):
  f=self.f;f.overlay_inputs();self.assertEqual(f.call('_lc_begin'),1);r=f.finish_lc();self.assertEqual(r[:3],b'\3\6\0');self.assertEqual(f.ram(0x6000,len(f.asset)),f.asset);self.assertEqual(L.bulk_model_commands(f.m),8);self.assertEqual(f.result()[3],0)
  self.assertEqual(f.call('_ni_begin'),1);text=b'[emulator]\ninitial_columns=40\n';f.write('_ni_input',text);f.write('_ni_count',bytes([len(text)]));self.assertEqual(f.call('_ni_feed'),1);self.assertEqual(f.call('_ni_finish'),1);self.assertEqual(f.call('_ni_columns'),40)
 def test_asset_CRC_mismatch_never_installs_or_opens_CFG(self):
  f=self.f;a=bytearray((P/'START.INO').read_bytes());a[200]^=1;f.overlay_inputs(bytes(a));self.assertEqual(f.call('_lc_begin'),1);self.assertEqual(f.finish_lc()[:3],b'\3\4\0');self.assertEqual(L.bulk_model_commands(f.m),4);self.assertEqual(f.ram(0x6000,len(a)),bytes(len(a)))
 def test_wrong_asset_size_closes_before_execution(self):
  f=self.f;f.overlay_inputs(b'x');self.assertEqual(f.call('_lc_begin'),1);self.assertEqual(f.finish_lc()[:3],b'\3\3\0');self.assertEqual(f.result()[3],0);self.assertEqual(L.bulk_model_commands(f.m),3)
 def test_public_spec_mutation_after_acceptance_cannot_change_bound_asset(self):
  f=self.f;f.overlay_inputs();self.assertEqual(f.call('_lc_begin'),1);f.write('_so_overlay_spec',bytes(16));self.assertEqual(f.finish_lc()[:3],b'\3\6\0');self.assertEqual(f.ram(0x6000,len(f.asset)),f.asset)
 def test_fetch_failure_stops_before_relocated_validator(self):
  f=self.f;f.overlay_inputs();self.assertEqual(f.call('_lc_begin'),1)
  for _ in range(5000):
   if f.lc()[3]==9 and f.lc()[4]==1 and f.result()[3]==0:break
   f.poll_lc()
  else:raise AssertionError('overlay closed CRC phase absent')
  L.dos64_reu_fail_after(f.m,0,17);f.poll_lc();self.assertEqual(f.lc()[:3],b'\3\7\0');self.assertEqual(L.bulk_model_commands(f.m),4);self.assertEqual(f.result()[3],0)
if __name__=='__main__':unittest.main(verbosity=2)
