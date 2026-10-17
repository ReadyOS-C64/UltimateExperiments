from pathlib import Path
import sys
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-40k-test');assert not Path(sys.pycache_prefix).exists()
import unittest,json
from test_journal_start import Journal,SYMS,L
class Tests(unittest.TestCase):
 def tearDown(self):
  if hasattr(self,'f'):self.f.close()
 def handoff(self,f):
  r=f.run(SYMS['trampoline_start']);self.assertEqual(r.regs.pc,0x200,(r.status,hex(r.regs.pc)))
  f.startup_guard();self.assertEqual(f.read('_lc_result',2),b'\5\0')
  self.assertEqual(f.reu(0x3da000,24576),f.menu[:24576]);self.assertEqual(f.reu(0x3f0000,16384),f.menu[24576:]);self.assertEqual(L.bulk_model_open(f.m,1),0)
 def failed(self,f,error):
  r=f.run(SYMS['sf_entry_idle']);self.assertEqual(r.status,0);self.assertEqual(f.read('_lc_result',2),bytes([3,error]))
  for at in [0x3da005,0x3ff005,0x3ff505]:self.assertEqual(f.reu(at,1),b'\0')
  self.assertEqual(L.bulk_model_open(f.m,1),0)
 def test_01_actual_SYS_40_80_nojournal_then_complete40KiB_assets(self):
  for columns in [40,80]:
   f=self.f=Journal(columns);self.assertEqual(len(f.menu),40960);self.handoff(f);f.close();del self.f
 def test_02_RCVcache_retired_before_40KiB_menu_staging_overwrites_it(self):
  f=self.f=Journal();self.actual_copy(f)
  self.assertEqual(f.reu(0x3e0000,len(f.menu)),f.menu);self.assertEqual(f.reu(0x3e8000,8192),f.menu[32768:])
  self.assertNotEqual(f.reu(0x3e8000,len(f.gate)),f.gate)
  self.assertEqual(bytes(L.dos64_peek(f.m,0x6000+i)for i in range(len(f.asset))),f.asset)
  L.dos64_step(f.m);self.handoff(f)
 def test_03_third_floppy_and_remaining_reserved16KiB_intact(self):
  f=self.f=Journal();disk=bytes((i*13+(i>>7))&255 for i in range(368640));guard=bytes((i*19)&255 for i in range(16384));f.seed(disk,0x380000);f.seed(guard,0x3f4000)
  self.handoff(f);self.assertEqual(f.reu(0x380000,len(disk)),disk);self.assertEqual(f.reu(0x3f4000,len(guard)),guard)
 def actual_copy(self,f):
  for _ in range(4096):
   r=f.run(SYMS['_modal_copy']);self.assertEqual(r.regs.pc,SYMS['_modal_copy'])
   if f.read('_lc_result',4)[3]==12:
    self.assertEqual(bytes(L.dos64_peek(f.m,0x6000+i)for i in range(len(f.asset))),f.asset);return
   L.dos64_step(f.m)
  self.fail('no phase12 modal copy; overlay address alone is ambiguous')
 def copy_offset(self,f,blocks):
  self.actual_copy(f)
  for _ in range(blocks):L.dos64_step(f.m);r=f.run(SYMS['_modal_copy']);self.assertEqual(r.regs.pc,SYMS['_modal_copy'])
 def test_04_first_BINDslot_STORE_failure_never_publishes_ready(self):
  f=self.f=Journal();self.copy_offset(f,128);L.dos64_reu_fail_after(f.m,1,1);self.failed(f,7)
 def test_05_last_BINDslot_target_byte_requires_wholeCRC(self):
  f=self.f=Journal();self.copy_offset(f,160);f.seed(bytes([f.menu[-1]^1]),0x3f3fff);self.failed(f,4)
if __name__=='__main__':
 r=unittest.main(exit=False,verbosity=2).result;(P/'FORTY_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'data_fixture_only':True},indent=2)+'\n');sys.exit(not r.wasSuccessful())
