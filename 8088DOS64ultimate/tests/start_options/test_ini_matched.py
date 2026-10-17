import sys,os
from pathlib import Path
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-ini-matched-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import unittest,ctypes as C,struct,zlib,json
from fixture_synthetic import Generated,SYMS,L,MAIN
from test_start import Start
from test_actual import bind,ptr,u8,u32
bind('ini_model_missing_status',None,[ptr,ptr,u32]);bind('dos64_host_input_model_keys',None,[ptr,ptr]);bind('dos64_cia_clock_step',None,[ptr,u32])
class Actual(unittest.TestCase):
 def tearDown(self):
  if hasattr(self,'f'):self.f.close()
 def stop(self,f):
  r=f.run(SYMS['sf_entry_idle']);assert r.status==0,(r.status,hex(r.regs.pc));f.startup_guard();self.assertEqual(f.byte('_sf_status'),3);self.assertEqual(f.reu(0x3ff005,1),b'\0');self.assertEqual(f.reu(0x3ff505,1),b'\0');self.assertEqual(L.bulk_model_open(f.m,1),0);return f.read('_lc_result',16)
 def handoff(self,f):
  r=f.run(SYMS['trampoline_start']);assert r.regs.pc==0x200 and r.status in [0,2],(r.status,hex(r.regs.pc),f.read('_lc_result',16).hex());f.startup_guard();self.assertEqual(f.read('_lc_result',2),b'\5\0');self.assertEqual(L.bulk_model_open(f.m,1),0);self.assertEqual(f.reu(0x3ff005,1),b'\xa5');o=f.reu(0x3ff500,32);self.assertEqual(o[:8],b'D64O\1\xa5\x20\0');self.assertEqual(o[8:16],f.reu(0x3ff008,8));self.assertEqual(zlib.crc32(o[:28]),int.from_bytes(o[28:],'little'));return o
 def test_disabled_template_true_SYS_keeps_zero_wire(self):
  f=self.f=Start();r=f.run(SYMS['sf_entry_idle']);self.assertEqual(r.status,0);self.assertEqual(L.bulk_model_commands(f.m),0);self.assertEqual(f.byte('_sf_status'),3)
 def test_exact_missing18_normalized84_reaches_real_handoff_default80(self):
  f=self.f=Generated(80,None);o=self.handoff(f);self.assertEqual(o[16],80);self.assertEqual(f.byte('_files_handle'),0)
 def test_malformed_present_INI_never_falls_back_and_zeros_both_ready(self):
  f=self.f=Generated(80,b'[emulator]\ninitial_columns=41\n');r=self.stop(f);self.assertEqual(r[:3],b'\3\6\0')
 def test_path_not_found_is_not_optional_file_absence(self):
  f=self.f=Generated(80,None);status=b"PATH DOESN'T EXIST";L.ini_model_missing_status(f.m,status,len(status));r=self.stop(f);self.assertEqual(r[1],2)
 def test_legacy_v1_release_cannot_authorize_options_aware_START(self):
  f=self.f=Generated();r=bytearray(f.rel);r[4]=1;r[56:60]=bytes(4);struct.pack_into('<I',r,60,zlib.crc32(r[:60]));L.bulk_model_seed(f.m,f.home+b'/DOS64.REL',bytes(r),64);result=self.stop(f);self.assertEqual(result[1],5)
 def test_resigned_required_flag_alias_or_out_of_range_is_rejected(self):
  for value in [int.from_bytes((P/'DOS64.REL').read_bytes()[36:40],'little'),0,0xffffffff]:
   f=Generated();self.f=f
   try:r=bytearray(f.rel);struct.pack_into('<I',r,56,value);struct.pack_into('<I',r,60,zlib.crc32(r[:60]));L.bulk_model_seed(f.m,f.home+b'/DOS64.REL',bytes(r),64);result=self.stop(f);self.assertEqual(result[1],5)
   finally:f.close();del self.f
 def test_latest_STOP_at_native_options_commit_prevents_publication(self):
  f=self.f=Generated(40);r=f.run(SYMS['_ii_commit']);assert r.regs.pc==SYMS['_ii_commit'];L.dos64_host_input_model_keys(f.m,bytes(7)+b'\x80');result=self.stop(f);self.assertEqual(result[1],8)
 def test_latest_failed_clock_at_native_options_commit_prevents_publication(self):
  f=self.f=Generated(40);r=f.run(SYMS['_ii_commit']);assert r.regs.pc==SYMS['_ii_commit'];L.dos64_cia_clock_step(f.m,262144);result=self.stop(f);self.assertEqual(result[1],10)
if __name__=='__main__':unittest.main(verbosity=2)
