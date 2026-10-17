from pathlib import Path
import subprocess,hashlib,json,shlex,shutil,os
P=Path.cwd();W=P/'runtime';D=P/'counter-source';D.mkdir();h=lambda q:hashlib.sha256(q.read_bytes()).hexdigest();deps=set();env=dict(os.environ)
for k in ['PYTHONPATH','PYTHONPYCACHEPREFIX','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(k,None)
cc=Path(shutil.which('clang++')).resolve();inc=['-Imodel/tests/floppy_export','-Imodel/tests/host','-Iwork/third_party/peddle/Peddle'];files=['model/tests/floppy_export/bridge.cpp',*['work/third_party/peddle/Peddle/'+n for n in ['Peddle.cpp','PeddleDebugger.cpp','PeddleDisassembler.cpp','StrWriter.cpp']]]
for i,n in enumerate(files):
 c=[str(cc),'-std=c++20','-M',*inc,n];r=subprocess.run(c,cwd=W,env=env,capture_output=True);assert not r.returncode,r.stderr.decode();(D/f'deps{i}.txt').write_bytes(r.stdout)
 for n in shlex.split(r.stdout.decode().replace('\\\n',' ').split(':',1)[1]):q=Path(n);deps.add((q if q.is_absolute()else W/q).resolve())
records=[]
for q in sorted(deps):
 d=D/'inputs'/str(q).lstrip('/');d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,d);records.append({'path':str(q),'copy':str(d.relative_to(P)),'sha256':h(q)})
(D/'BEFORE.json').write_text(json.dumps(records,indent=2)+'\n');shutil.copyfile(W/'model/save-peddle.dylib',D/'old-save-peddle.dylib');c=[str(cc),'-std=c++20','-O2','-fPIC','-shared',*inc,*files,'-o','model/save-peddle.dylib'];r=subprocess.run(c,cwd=W,env=env,capture_output=True);(D/'compile.stderr').write_bytes(r.stderr);assert not r.returncode,r.stderr.decode()
for x in records:assert h(Path(x['path']))==x['sha256'];assert h(P/x['copy'])==x['sha256']
(D/'MODEL.json').write_text(json.dumps({'compiler':{'path':str(cc),'sha256':h(cc)},'inputs':len(records),'source_unchanged':True,'source_built_model_sha256':h(W/'model/save-peddle.dylib'),'command':c},indent=2)+'\n')
