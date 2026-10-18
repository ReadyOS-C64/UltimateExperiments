from pathlib import Path
import sys
D=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(D/'.absent-final-preflight');assert not Path(sys.pycache_prefix).exists()
import unittest,json
import test_preflight as T
class MissingMain(T.Native):
 def seed(self):
  for k,(path,data)in enumerate(zip(T.ALLPATH,T.ALLDATA)):
   if k!=5:T.L.bulk_model_seed(self.f.m,path,data,len(data))
class Final(unittest.TestCase):
 make=T.Tests.make
 def test_01_true_SYS_CIA_eight_sources_before_FAT_or_CREATE(self):T.Tests.test_01_true_SYS_CIA_eight_sources_before_FAT_or_any_CREATE(self)
 def test_02_actual_missing_main_terminal_caption_zero_CREATE(self):
  u=MissingMain();self.addCleanup(u.close);u.select();self.assertEqual(u.finish(),5);self.assertEqual(u.call('_rc_error'),0x32);self.assertEqual(u.call('_bc_files_closed'),1);self.assertEqual(u.call('_rc_source_ready'),0);u.no_create()
  s='Checking DOS64.PRG';codes=bytes(ord(c)-96 if 'a'<=c<='z'else ord(c)for c in s)
  self.assertEqual(u.f.readat(0x400+20*40,len(codes)),codes)
  self.assertEqual(u.f.byte('_rc_output_mask')if '_rc_output_mask'in u.f.labels else u.f.read('_rc_retained',183)[180],0)
  (D/'MISSING_MAIN_SCREEN_CODES.bin').write_bytes(u.f.readat(0x400,1000));T.REPORT.append({'case':'actual-missing-main','error':50,'zero_creates':True,'native_caption':s,'known_closed':True})
if __name__=='__main__':
 r=unittest.main(exit=False,verbosity=2).result;(D/'FINAL_PREFLIGHT_RESULTS.json').write_text(json.dumps({'passed':r.wasSuccessful(),'tests':r.testsRun,'receipts':T.REPORT,'scope':'Actual native SYS→CIA folder/selection→sameengine8readonlysources→FATcheckpoint or terminalmissingmain; no output creation/physical/guest boot'},indent=2)+'\n');sys.exit(not r.wasSuccessful())
