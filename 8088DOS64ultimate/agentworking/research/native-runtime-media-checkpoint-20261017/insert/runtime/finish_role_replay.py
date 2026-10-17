from pathlib import Path
import os,sys,hashlib,json,ctypes as C,unittest
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-finish-replay');assert not Path(sys.pycache_prefix).exists()
assert not list((P/'work/build').glob('dos64-tests*')),'runtime proof excludes all UNIT products'
os.environ['DOS64_MEDIA_TEST_ROLE']='runtime'
from role_oracle import verify,constants,labels
oracle=verify('runtime');n=labels(P/'work/build/dos64.labels');b=labels(P/'broker/broker.labels');imports=constants(P/'finish/imports.inc')
for k,v in imports.items():assert v==(b[k[7:]]if k.startswith('broker_')else n[k]),k
from test_finish_ui import *
allowed={};loaded=[]
for name in ['work/build/dos64.prg','broker/broker.prg']:
 raw=(P/name).read_bytes();allowed[(int.from_bytes(raw[:2],'little'),len(raw)-2,hashlib.sha256(raw[2:]).hexdigest())]=name
original=L.dos64_load
def checked(machine,address,data,count):
 raw=data if isinstance(data,bytes)else C.string_at(data,count);key=(address,count,hashlib.sha256(raw).hexdigest());assert key in allowed,key;loaded.append(allowed[key]);return original(machine,address,data,count)
L.dos64_load=checked
suite=unittest.defaultTestLoader.loadTestsFromTestCase(FinishUI);suite.addTest(Tests('test_01_B38_Ctarget1'));r=unittest.TextTestRunner(verbosity=2).run(suite)
(P/'FINAL_FINISH_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'oracle':oracle,'Finish_imports':len(imports),'CPU_loads':loaded,'Finish_records':records,'scope':'actual runtime/CIA/Finish8+SaveAs1; all UNIT products absent; synthetic media, no coldSTART/DOS/physical'},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
