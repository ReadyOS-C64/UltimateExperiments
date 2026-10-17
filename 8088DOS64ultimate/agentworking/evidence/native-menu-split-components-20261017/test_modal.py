from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-modal-test');assert not Path(sys.pycache_prefix).exists()
import unittest,ctypes as C,json,zlib
from fixture_synthetic import Generated,SYMS,L
from test_actual import ptr,u8,u32
L.dos64_reu_fail_after.argtypes=[ptr,C.c_uint64,u32]
L.dos64_step.argtypes=[ptr]
L.dos64_host_input_model_keys.argtypes=[ptr,ptr]
class Menu(Generated):
 def __init__(self,columns=80,asset=True):
  super().__init__(columns)
  self.menu=(P/'DOS64.MNU').read_bytes()if asset is True else asset
  if self.menu is not None:L.bulk_model_seed(self.m,self.home+b'/DOS64.MNU',self.menu,len(self.menu))
class Tests(unittest.TestCase):
 def tearDown(self):
  if hasattr(self,'f'):self.f.close()
 def handoff(self,f):
  r=f.run(SYMS['trampoline_start']);self.assertEqual(r.regs.pc,0x200);self.assertIn(r.status,[0,2]);f.startup_guard();self.assertEqual(f.read('_lc_result',2),b'\5\0');self.assertEqual(L.bulk_model_open(f.m,1),0)
  self.assertEqual(f.reu(0x3da000,min(len(f.menu),24576)),f.menu[:24576]);self.assertEqual(f.reu(0x3f0000,max(0,len(f.menu)-24576)),f.menu[24576:]);self.assertEqual(f.reu(0x3ff005,1),b'\xa5');self.assertEqual(f.reu(0x3ff505,1),b'\xa5')
 def failed(self,f,error):
  r=f.run(SYMS['sf_entry_idle']);self.assertEqual(r.status,0);self.assertEqual(f.byte('_sf_status'),3);self.assertEqual(f.read('_lc_result',2),bytes([3,error]));self.assertEqual(f.reu(0x3da005,1),b'\0');self.assertEqual(f.reu(0x3ff005,1),b'\0');self.assertEqual(f.reu(0x3ff505,1),b'\0');self.assertEqual(L.bulk_model_open(f.m,1),0)
 def test_01_actual_START_40_80_loads_exact_all_menu_bytes_before_main_handoff(self):
  for col in [40,80]:
   self.f=Menu(col);self.handoff(self.f);self.f.close();del self.f
 def test_02_missing_menu_refuses_main_and_ready(self):
  self.f=Menu(asset=None);self.failed(self.f,2)
 def test_03_exact_length_required(self):
  self.f=Menu(asset=(P/'DOS64.MNU').read_bytes()[:-1]);self.failed(self.f,3)
 def test_04_body_and_padding_crc_required(self):
  for at in [512,2560,24575,24576,32767]:
   b=bytearray((P/'DOS64.MNU').read_bytes());b[at]^=1;self.f=Menu(asset=bytes(b));self.failed(self.f,4);self.f.close();del self.f
 def test_05_resigned_header_mismatch_refuses_before_copy(self):
  b=bytearray((P/'DOS64.MNU').read_bytes());b[8]^=1;self.f=Menu(asset=bytes(b));value=zlib.crc32(b)
  for i in range(4):L.dos64_poke(self.f.m,SYMS['_sm_modal_spec']+8+i,(value>>(8*i))&255)
  self.failed(self.f,5)
 def test_06_STOP_during_copy_clears_all_ready(self):
  self.f=Menu();r=self.f.run(SYMS['_modal_copy']);self.assertEqual(r.regs.pc,SYMS['_modal_copy']);L.dos64_host_input_model_keys(self.f.m,bytes(7)+b'\x80');self.failed(self.f,8)
 def test_07_failed_copy_DMA_clears_all_ready(self):
  self.f=Menu();r=self.f.run(SYMS['_modal_copy']);self.assertEqual(r.regs.pc,SYMS['_modal_copy']);L.dos64_reu_fail_after(self.f.m,1,1);self.failed(self.f,7)
 def test_08_failed_ready_DMA_never_enters_main(self):
  self.f=Menu();r=self.f.run(SYMS['_modal_ready']);self.assertEqual(r.regs.pc,SYMS['_modal_ready']);self.assertEqual(self.f.reu(0x3da005,1),b'\0');L.dos64_reu_fail_after(self.f.m,0,1);self.failed(self.f,7)
 def test_09_all_third_floppy_bytes_and_reserve_after_controller_remain_intact(self):
  self.f=Menu();spare=bytes((i*13+(i>>7))&255 for i in range(368640));guard=bytes((i*17)&255 for i in range(24576))
  self.f.seed(spare,0x380000);self.f.seed(guard,0x3f2000);self.handoff(self.f)
  self.assertEqual(self.f.reu(0x380000,len(spare)),spare);self.assertEqual(self.f.reu(0x3f2000,len(guard)),guard)
 def at_copy_offset(self,f,blocks):
  r=f.run(SYMS['_modal_copy']);self.assertEqual(r.regs.pc,SYMS['_modal_copy'])
  for _ in range(blocks):
   L.dos64_step(f.m);r=f.run(SYMS['_modal_copy']);self.assertEqual(r.regs.pc,SYMS['_modal_copy'])
 def test_10_failed_first_split_slot_STORE_never_publishes_ready(self):
  self.f=Menu();self.at_copy_offset(self.f,96);L.dos64_reu_fail_after(self.f.m,1,1);self.failed(self.f,7)
 def test_11_final_split_slot_target_corruption_is_caught_by_whole_crc(self):
  self.f=Menu();self.at_copy_offset(self.f,128);last=bytes([self.f.menu[-1]^1]);self.f.seed(last,0x3f1fff);self.failed(self.f,4)
if __name__=='__main__':
 r=unittest.main(exit=False,verbosity=2).result;(P/'MODAL_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'scope':'actual START synthetic-file load/verify/copy/handoff, no DOS boot or menu interaction'},indent=2)+'\n');sys.exit(not r.wasSuccessful())
