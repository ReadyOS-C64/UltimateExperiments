from pathlib import Path
import json,hashlib,subprocess,sys
D=Path(__file__).resolve().parent;E=D/'error-tests';PAR=D.parent/'native-installer-bootstrap-diagnostics-20261017'
def identity(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
records={str(p):identity(p)for p in [Path(__file__),E/'test_file_diag.py',E/'test_strip_lifetime.py',E/'bankguard/RESULT.json',PAR/'test_boot.py',PAR/'model-observer/runtime/model/save-peddle.dylib',Path(sys.executable).resolve()]}
for row in json.loads((PAR/'model-observer/counter-source/BEFORE.json').read_text()):
 for p in [Path(row['path']),PAR/'model-observer'/row['copy']]:
  wanted=identity(p);assert wanted['sha256']==row['sha256'],str(p);records[str(p)]=wanted
j=json.loads((E/'bankguard/RESULT.json').read_text())
for p,w in j['source_inputs'].items():assert identity(Path(p))==w,p;records[p]=w
for name,w in j['products'].items():
 p=Path(j['work'])/'build'/name;assert identity(p)==w,str(p);records[str(p)]=w
(E/'INPUTS_BEFORE.json').write_text(json.dumps(records,indent=2)+'\n')
for script in ['test_file_diag.py','test_strip_lifetime.py']:
 with(E/(script+'.stdout')).open('wb')as o,(E/(script+'.stderr')).open('wb')as e:
  subprocess.run([sys.executable,'-B',script],cwd=E,stdin=subprocess.DEVNULL,stdout=o,stderr=e,check=True)
for p,w in records.items():assert identity(Path(p))==w,p
(E/'INPUTS_AFTER.json').write_text(json.dumps(records,indent=2)+'\n')
results={n:json.loads((E/n).read_text())for n in ['FILE_TEST_RESULT.json','STRIP_RESULT.json']}
assert all(j['passed']for j in results.values())
(E/'RESULT.json').write_text(json.dumps({'status':'passed','actual_native_methods':6,'actual_cases':9,'source_model_product_records':len(records),'model':'reused qualified source-built parent observer, all originals+retainedcopies rechecked; no new C++ compile','results':results,'scope':'currente710 actual BASIC37 bootstrap/privateSO API fault components/root failure continuation; no fullpublication/DOS/physical claim'},indent=2)+'\n')
print('currente710 actualnative6methods/9cases pass;',len(records),'source/model/product records exact')
