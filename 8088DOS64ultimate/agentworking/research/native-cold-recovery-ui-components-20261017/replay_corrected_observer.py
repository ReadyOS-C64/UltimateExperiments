from pathlib import Path
import sys,os,json,unittest
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-corrected-observer');assert not Path(sys.pycache_prefix).exists();sys.path.insert(0,str(P/'work'))
import test_recovery_ui_observer as t
names=['test_01_pending_OLD_actual_SYS_CIA_recovery_fresh_NONE_handoff','test_04_pending_MISSING_actual_confirmation_and_fresh_NONE','test_05_pending_NEW_actual_confirmation_and_fresh_NONE','test_09_human_confirmation_delay_uses_fresh_OPEN_deadline']
r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(t.Tests(n)for n in names))
(P/'CORRECTED_OBSERVER_RESULT.json').write_text(json.dumps({'pass':r.wasSuccessful(),'tests':r.testsRun,'records':t.records,'scope':'Additive corrected port oracle; same frozen160 native/source/products; only4priorbadliteral-observer cases repeated, other6 passed UI_FIXED10'},indent=2)+'\n');sys.exit(not r.wasSuccessful())
