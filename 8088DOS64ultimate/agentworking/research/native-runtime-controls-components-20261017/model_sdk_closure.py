from pathlib import Path
import os,sys,hashlib,json,subprocess,shlex,shutil
P=Path(__file__).resolve().parent;D=P/'model-sdk-closure';assert not D.exists();D.mkdir();h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();deps=set();commands=[]
for f in [P/'model/tests/floppy_export/bridge.cpp',*sorted((P/'work/third_party/peddle/Peddle').glob('*.cpp'))]:
 a=['/usr/bin/clang++','-std=c++20','-M','-I'+str(P/'model/tests/host'),'-I'+str(P/'model/tests/floppy_export'),'-I'+str(P/'work/third_party/peddle/Peddle'),str(f)];r=subprocess.run(a,cwd=P,capture_output=True);assert not r.returncode,r.stderr.decode();(D/('deps'+str(len(commands))+'.txt')).write_bytes(r.stdout);commands.append(a)
 for n in shlex.split(r.stdout.decode().replace('\\\n',' ').split(':',1)[1]):deps.add(Path(n).resolve())
deps.update([Path('/usr/bin/clang++').resolve(),Path(sys.executable).resolve(),P/'build_model.py',P/'model_sdk_closure.py'])
rec={str(f):{'sha256':h(f),'bytes':f.stat().st_size}for f in sorted(deps)}
for f in sorted(deps):
 q=D/'inputs'/str(f).lstrip('/');q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,q)
(D/'INPUTS_BEFORE.json').write_text(json.dumps(rec,indent=2)+'\n');model=P/'model/save-peddle.dylib';expected=h(model)
r=subprocess.run([sys.executable,'-B','build_model.py'],cwd=P,capture_output=True);(D/'build.stdout').write_bytes(r.stdout);(D/'build.stderr').write_bytes(r.stderr);assert not r.returncode,r.stderr.decode();assert h(model)==expected,'source-rebuilt model differs from actually executed model'
for n,v in rec.items():assert h(Path(n))==v['sha256'];assert h(D/'inputs'/n.lstrip('/'))==v['sha256']
for n,v in json.loads((P/'closed-controls/INPUTS_BEFORE.json').read_text()).items():assert h(Path(n))==v['sha256']
for n,v in json.loads((P/'closed-controls/PRODUCTS.json').read_text()).items():assert h(P/n)==v['sha256']
(D/'INPUTS_AFTER.json').write_text(json.dumps(rec,indent=2)+'\n');(D/'RESULT.json').write_text(json.dumps({'passed':True,'model_sdk_inputs':len(rec),'commands':commands,'tested_model_sha256':expected,'same_tested_model_reproduced':True,'prior433_scoped_inputs_37_products_still_exact':True,'scope':'additive model SDK dependency capture then source rebuild of exact already-executed model; unchanged14 tests not repeated; original scoped native graph unchanged'},indent=2)+'\n')
