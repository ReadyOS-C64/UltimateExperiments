from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-config-profiles-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import unittest,argparse,json
p=argparse.ArgumentParser();p.add_argument('--relocation',action='store_true');p.add_argument('--all-file-diagnostics',action='store_true');a=p.parse_args();suite=unittest.TestSuite();expected=0
if a.relocation:
 from test_relocation import Relocation
 suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Relocation));expected+=5
if a.all_file_diagnostics:
 from test_combined_errors import Errors
 suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Errors));expected+=4
assert expected
r=unittest.TextTestRunner(verbosity=2).run(suite);passed=r.wasSuccessful()and r.testsRun==expected
(P.parent/'PROFILE_TEST_REPORT.json').write_text(json.dumps({'tests_run':r.testsRun,'expected':expected,'successful':passed,'actual_native_Peddle':True,'genuine_DOS':False,'physical':False},indent=2)+'\n');sys.exit(not passed)
