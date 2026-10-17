from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-warm-controls-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists();assert not list((P/'work/build').glob('dos64-tests*'))
os.environ['DOS64_MEDIA_TEST_ROLE']='runtime'
import json,unittest
from role_oracle import verify,constants,labels
report=verify('runtime');N=labels(P/'work/build/dos64.labels');B=labels(P/'broker/broker.labels')
for k,v in constants(P/'finish/imports.inc').items():assert v==(B[k[7:]]if k.startswith('broker_')else N[k]),k
from test_controls_ui import Controls
from test_finish_ui import FinishUI
suite=unittest.TestSuite([Controls('test08_C_context_or_busy_UCI_blocks_before_control'),FinishUI('test05_unknown_CLOSE_never_safe_or_retry')]);r=unittest.TextTestRunner(verbosity=2).run(suite);(P/'WARM_CONTROLS_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'oracle':report,'scope':'actualruntime syntheticfixture negatives; UNIT products absent; no extra cold/physical claim'},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
