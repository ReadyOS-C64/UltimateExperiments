from pathlib import Path
import hashlib,json,os,shlex,shutil,subprocess,sys,time
P=Path(__file__).resolve().parent;D=P/'closed-plan-journal';assert not D.exists();D.mkdir();sys.dont_write_bytecode=True
def digest(f):return hashlib.sha256(f.read_bytes()).hexdigest()
tools={n:Path(shutil.which(n)).resolve()for n in ['python3','cc65','ca65','ld65','make','clang++']}
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
for n in ['PYTHONPATH','PYTHONPYCACHEPREFIX','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(n,None)
commands=[]
def run(name,argv,cwd):
 start=time.monotonic()
 with(D/(name+'.stdout')).open('wb')as o,(D/(name+'.stderr')).open('wb')as e:r=subprocess.run(list(map(str,argv)),cwd=cwd,env=env,stdout=o,stderr=e)
 commands.append({'name':name,'argv':list(map(str,argv)),'cwd':str(cwd),'exit':r.returncode,'seconds':time.monotonic()-start});(D/'COMMANDS.json').write_text(json.dumps(commands,indent=2)+'\n');assert not r.returncode,name
inputs={Path(__file__)}
for role in ['runtime','cold']:
 for f in(P/role).rglob('*'):
  if f.is_file()and f.suffix in ['.c','.h','.s','.inc','.cfg','.cpp','.hpp','.py','.mk']and not any(x.startswith('.absent')for x in f.parts):inputs.add(f)
inputs.update(f for f in(P/'cold/inputs').rglob('*')if f.is_file())
inputs.update(f for f in(P/'runtime/work/assets').rglob('*')if f.is_file())
inputs.add(P/'runtime/work/Makefile')
sdk=Path('/opt/homebrew/share/cc65')
for root in ['include','asminc']:inputs.update(f for f in(sdk/root).rglob('*')if f.is_file())
inputs.add(sdk/'lib/none.lib');inputs.update(tools.values())
# Resolve the actual C++ translation units and their complete system headers.
models=[('runtime',P/'runtime/model/tests',P/'runtime/work/third_party/peddle/Peddle'),('cold',P/'cold/work/tests',P/'cold/work/third_party/peddle/Peddle')]
for name,tests,cpu in models:
 src=[tests/'floppy_export/bridge.cpp',*sorted(cpu.glob('*.cpp'))]
 argv=['/usr/bin/clang++','-std=c++20','-M','-MT','dos64dep','-I'+str(tests/'host'),'-I'+str(tests/'floppy_export'),'-I'+str(cpu),*map(str,src)]
 run(name+'-cpp-dependencies',argv,P)
 dep=(D/(name+'-cpp-dependencies.stdout')).read_text().replace('\\\n',' ')
 for line in dep.splitlines():
  if line.strip():inputs.update(Path(n).resolve()for n in shlex.split(line.split(':',1)[1]))
rec={str(f):{'sha256':digest(f),'bytes':f.stat().st_size}for f in sorted(inputs)}
for f in sorted(inputs):
 q=D/'inputs'/(f.relative_to(P)if f.is_relative_to(P)else Path('EXTERNAL')/str(f).lstrip('/'));q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,q)
(D/'INPUTS_BEFORE.json').write_text(json.dumps(rec,indent=2)+'\n')
products=['runtime/MODAL.MNU','runtime/HEADER.bin','runtime/WORKERS.MNU']
for base,stem in [('runtime/work/build','dos64'),('runtime/phase','runtime-plan'),('runtime/phase','worker-calls'),('cold/work','controller'),('cold/gate','START.RCV'),('cold/worker','ROLL.PRG')]:
 if stem in ['START.RCV','ROLL.PRG']:products.append(base+'/'+stem)
 else:products.extend(base+'/'+stem+ext for ext in ['.prg','.labels','.map'])
products.extend('cold/work/'+n for n in ['START.INO','START.RCV','START.RFW','START.REL','DOS64.REL','DOS64.MNU'])
products.extend(['cold/gate/gate.labels','cold/gate/gate.map','cold/worker/worker.labels','cold/worker/worker.map'])
expected={n:digest(P/n)for n in products}
shutil.rmtree(P/'runtime/work/build')
run('fresh-native-plan',[tools['python3'],'-B','build_ui_bridge.py','--role','runtime'],P/'runtime')
run('fresh-cold-coupling',[tools['python3'],'-B','couple.py'],P/'cold')
assert all(digest(P/n)==h for n,h in expected.items()),'fresh source products differ'
run('fresh-runtime-model',[tools['python3'],'-B','build_model.py'],P/'runtime')
tests=P/'cold/work/tests';cpu=P/'cold/work/third_party/peddle/Peddle'
run('fresh-cold-model',['/usr/bin/clang++','-std=c++20','-O2','-fPIC','-shared','-I'+str(tests/'floppy_export'),'-I'+str(tests/'host'),'-I'+str(cpu),tests/'floppy_export/bridge.cpp',*sorted(cpu.glob('*.cpp')),'-o',P/'cold/work/journal-peddle.dylib'],P)
products.extend(['runtime/model/save-peddle.dylib','cold/work/journal-peddle.dylib']);frozen={n:{'sha256':digest(P/n),'bytes':(P/n).stat().st_size}for n in products}
q=D/'excluded-UNIT';q.mkdir();excluded=[]
for f in(P/'runtime/work/build').glob('dos64-tests*'):excluded.append({'name':f.name,'sha256':digest(f)});f.rename(q/f.name)
(D/'EXCLUDED_UNIT.json').write_text(json.dumps(excluded,indent=2)+'\n')
run('actual-native-plan',[tools['python3'],'-B','test_insert_plan.py'],P/'runtime')
run('actual-cold-insert-recovery',[tools['python3'],'-B','test_insert_recovery.py'],P/'cold/work')
for f,v in rec.items():assert digest(Path(f))==v['sha256'],f
for f,v in frozen.items():
 assert digest(P/f)==v['sha256'],f
 q=D/'products'/f;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(P/f,q)
for f in sorted(inputs):
 q=D/'inputs'/(f.relative_to(P)if f.is_relative_to(P)else Path('EXTERNAL')/str(f).lstrip('/'));assert digest(q)==rec[str(f)]['sha256']
(D/'INPUTS_AFTER.json').write_text(json.dumps(rec,indent=2)+'\n');(D/'PRODUCTS.json').write_text(json.dumps(frozen,indent=2)+'\n')
(D/'RESULT.json').write_text(json.dumps({'passed':True,'inputs':len(rec),'products':len(frozen),'excluded_UNIT':len(excluded),'commands':commands,'scope':'actual runtime PLAN6 + native cold JG/RFW/CIA9; synthetic caller receipt/media, no whole Insert/DOS/hardware acceptance'},indent=2)+'\n')
print(json.dumps({'passed':True,'inputs':len(rec),'products':len(frozen),'commands':commands},indent=2))
