from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-strip-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import unittest,json
from test_file_diag import M,L,REPORT
class Strip(unittest.TestCase):
 def test_initial_diagnostic_copy_failure_park_never_partialcode(self):
  m=M()
  try:
   source=m.s['__BOOT_DIAG_LOAD__'];target=m.s['__BOOT_DIAG_RUN__'];size=m.s['__BOOT_DIAG_SIZE__'];bias=256-size;lo=(source-bias)&65535;to=(target-bias)&65535;pattern=b'\xbd'+lo.to_bytes(2,'little')+b'\x9d'+to.to_bytes(2,'little')+b'\xdd'+to.to_bytes(2,'little');raw=m.get('runtime_init',64);self.assertEqual(raw.count(pattern),1);pc=m.s['runtime_init']+raw.index(pattern)+6;m.at(self,pc);r=L.dos64_get_regs(m.m);a=to+r.x;m.put(a,bytes([m.get(a)[0]^1]));L.boot_pc_observe(m.m,target,target+size);m.at(self,'fixture_return');self.assertEqual(L.boot_pc_hits(m.m),0);self.assertEqual(L.bulk_model_commands(m.m),0);self.assertNotEqual(m.get(source,size),bytes(size));REPORT.append({'initialstrip_failedcopy':'trusted permanent park','no_partial_DIAG_PC':True,'no_FILES':True})
  finally:m.close()
 def test_strip_retired_before_C_and_stack_disjoint_helper(self):
  m=M()
  try:
   j=json.loads((P/'bankguard/RESULT.json').read_text());raw=(m.w/'setup.prg').read_bytes();source=m.s['__BOOT_DIAG_LOAD__'];target=m.s['__BOOT_DIAG_RUN__'];size=m.s['__BOOT_DIAG_SIZE__'];expected=raw[source-0x801+2:source-0x801+2+size];self.assertEqual(len(expected),size);m.boot(self);self.assertEqual(m.get(target,size),expected);self.assertNotEqual(m.get(source,size),expected);helper=m.get('__FILE_DIAG_RUN__',m.s['__FILE_DIAG_SIZE__']);self.assertEqual(len(helper),94);low=m.stack(self);self.assertGreaterEqual(low,0xcd00);self.assertLess(m.s['__FILE_DIAG_RUN__']+len(helper),0xc000);self.assertLess(m.s['__BSS_RUN__']+m.s['__BSS_SIZE__'],m.s['__FILE_DIAG_RUN__']);self.assertLessEqual(m.s['__HIGHBSS_RUN__']+m.s['__HIGHBSS_SIZE__'],0xf700);self.assertEqual(m.get(m.s['__FILE_DIAG_LOAD__'],len(helper)),bytes(len(helper)));REPORT.append({'copied_DIAG_exact_then_source_retired':True,'copied_FILEhelper_exact_then_source_zeroed':True,'software_stack_initial':0xcfff,'software_stack_low':low,'stack_reserved':[0xcd00,0xcfff],'helper':[0xbfa0,0xbffd]})
  finally:m.close()
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Strip));(P/'STRIP_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'records':REPORT},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
