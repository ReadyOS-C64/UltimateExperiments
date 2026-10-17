from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,shlex,time
P=Path(__file__).resolve().parent;R=P/'runtime';D=P/'closed-controller';assert not D.exists();D.mkdir();sys.dont_write_bytecode=True
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',DOS64_MEDIA_TEST_ROLE='runtime')
for n in ['PYTHONPATH','PYTHONPYCACHEPREFIX','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(n,None)
tools={n:Path(shutil.which(n)).resolve()for n in ['python3','cc65','ca65','ld65','make','clang++']};commands=[]
def run(name,argv,cwd):
 t=time.monotonic();argv=list(map(str,argv))
 with(D/(name+'.stdout')).open('wb')as o,(D/(name+'.stderr')).open('wb')as e:r=subprocess.run(argv,cwd=cwd,env=env,stdout=o,stderr=e)
 commands.append({'name':name,'argv':argv,'cwd':str(cwd),'exit':r.returncode,'seconds':time.monotonic()-t});(D/'COMMANDS.json').write_text(json.dumps(commands,indent=2)+'\n');assert not r.returncode,name
default=[]
for name in ['undefined','zero']:
 q=D/('default-'+name);shutil.copytree(R/'work',q,ignore=shutil.ignore_patterns('build','__pycache__','*.o','*.dylib','.absent*'));default.append(q)
# Seed each profile's generated includes before input closure; final builds
# below start again from absent products and must preserve those exact sources.
for name,q in zip(['undefined','zero'],default):
 flags=[]if name=='undefined'else[n+'=0'for n in ['DOS64_MODAL_MENU','DOS64_SAVE_HD_CONTEXT','DOS64_EXPORT_CRC','DOS64_SAVE_MODAL','DOS64_MEDIA_BINDING']]
 run('seed-default-'+name,[tools['make'],'-B','build/dos64.prg','build/dos64-tests.prg',*flags],q)
inputs={Path(__file__)}
for root in [R,*default]:
 for f in root.rglob('*'):
  if f.is_file()and(f.suffix in ['.c','.h','.s','.inc','.cfg','.cpp','.hpp','.py','.mk']or f.name=='Makefile'or'assets'in f.parts):inputs.add(f)
sdk=Path('/opt/homebrew/share/cc65')
for name in ['include','asminc']:inputs.update(f for f in(sdk/name).rglob('*')if f.is_file())
inputs.add(sdk/'lib/none.lib');inputs.update(tools.values())
tests=R/'model/tests';cpu=R/'work/third_party/peddle/Peddle'
run('cpp-dependencies',['/usr/bin/clang++','-std=c++20','-M','-MT','dos64dep','-I'+str(tests/'host'),'-I'+str(tests/'floppy_export'),'-I'+str(cpu),tests/'floppy_export/bridge.cpp',*sorted(cpu.glob('*.cpp'))],P)
dep=(D/'cpp-dependencies.stdout').read_text().replace('\\\n',' ')
for line in dep.splitlines():
 if line.strip():inputs.update(Path(n).resolve()for n in shlex.split(line.split(':',1)[1]))
rec={str(f):{'sha256':h(f),'bytes':f.stat().st_size}for f in sorted(inputs)}
for f in sorted(inputs):
 q=D/'inputs'/(f.relative_to(P)if f.is_relative_to(P)else Path('EXTERNAL')/str(f).lstrip('/'));q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,q)
(D/'INPUTS_BEFORE.json').write_text(json.dumps(rec,indent=2)+'\n')
products=['MODAL.MNU','HEADER.bin','WORKERS.MNU']
for d,stem in [('work/build','dos64'),('broker','broker'),('broker-runtime','broker'),('ui','panel'),('bridge','bridge'),('controller','controller'),('phase','transaction-wire'),('phase','modal-save'),('phase','runtime-plan'),('phase','worker-calls'),('binding','binding'),('binding','binding-calls'),('worker','incoming'),('insert-binding','binding'),('insert-binding','insert-calls'),('finish','finish')]:products.extend(d+'/'+stem+e for e in ['.prg','.labels','.map'])
products.append('insert-binding/insert-support.prg');expected={n:h(R/n)for n in products}
shutil.rmtree(R/'work/build');run('fresh-native',[tools['python3'],'-B','build_ui_bridge.py','--role','runtime'],R)
assert all(h(R/n)==v for n,v in expected.items()),'source-rebuilt products changed'
run('fresh-model',[tools['python3'],'-B','build_model.py'],R);products.append('model/save-peddle.dylib');frozen={n:{'sha256':h(R/n),'bytes':(R/n).stat().st_size}for n in products}
q=D/'excluded-UNIT';q.mkdir();excluded=[]
for f in(R/'work/build').glob('dos64-tests*'):excluded.append({'name':f.name,'sha256':h(f)});f.rename(q/f.name)
(D/'EXCLUDED_UNIT.json').write_text(json.dumps(excluded,indent=2)+'\n')
run('role-alias-inventory',[tools['python3'],'-B','-c','import json; from role_oracle import verify; print(json.dumps(verify("runtime"),indent=2))'],R)
run('controller-nine',[tools['python3'],'-B','test_insert_controller.py'],R)
run('CIA-Insert-five',[tools['python3'],'-B','test_insert_ui.py'],R)
run('composition-fault-five',[tools['python3'],'-B','test_insert_composition_faults.py'],R)
run('Save-Finish-regressions',[tools['python3'],'-B','-m','unittest','-v','test_ui_saveas.Tests.test_01_B38_Ctarget1','test_finish_ui.FinishUI.test01_Ctarget1_safe'],R)
defaults={}
for name,q in zip(['undefined','zero'],default):
 flags=[]if name=='undefined'else[n+'=0'for n in ['DOS64_MODAL_MENU','DOS64_SAVE_HD_CONTEXT','DOS64_EXPORT_CRC','DOS64_SAVE_MODAL','DOS64_MEDIA_BINDING']]
 shutil.rmtree(q/'build')
 run('default-'+name,[tools['make'],'-B','build/dos64.prg','build/dos64-tests.prg',*flags],q)
 defaults[name]={n:h(q/'build'/n)for n in ['dos64.prg','dos64.labels','dos64-tests.prg','dos64-tests.labels']}
 assert defaults[name]['dos64.prg']=='666089b57e5611a67b5d87ae84880256ef5dafb121b152e1de81b9ec1cc29064'
 assert defaults[name]['dos64-tests.prg']=='b9e9cc9e7d87176848ccf8bae49dfe4f4ff0125b3aad5a1cb874341436b78df6'
assert defaults['undefined']==defaults['zero'];(D/'DEFAULTS.json').write_text(json.dumps(defaults,indent=2)+'\n')
for f,v in rec.items():assert h(Path(f))==v['sha256'],f
for f,v in frozen.items():
 assert h(R/f)==v['sha256'],f
 q=D/'products'/f;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/f,q)
for f in sorted(inputs):
 q=D/'inputs'/(f.relative_to(P)if f.is_relative_to(P)else Path('EXTERNAL')/str(f).lstrip('/'));assert h(q)==rec[str(f)]['sha256']
(D/'INPUTS_AFTER.json').write_text(json.dumps(rec,indent=2)+'\n');(D/'PRODUCTS.json').write_text(json.dumps(frozen,indent=2)+'\n')
(D/'RESULT.json').write_text(json.dumps({'passed':True,'actual_groups':21,'inputs':len(rec),'products':len(frozen),'excluded_UNIT':len(excluded),'commands':commands,'defaults':defaults,'scope':'actualruntime controller9+nativeCIAInsert5+compositionfault5+SaveFinish2; synthetic media; no cold/DOS/physical acceptance'},indent=2)+'\n');print(json.dumps({'passed':True,'inputs':len(rec),'products':len(frozen),'groups':21},indent=2))
