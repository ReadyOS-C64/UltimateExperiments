from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;assert Path.cwd()==P
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-runtime-close');assert not Path(sys.pycache_prefix).exists()
import hashlib,json,subprocess,shutil,time,shlex
E=P/'closed-runtime';assert not E.exists();E.mkdir();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPYCACHEPREFIX=str(P/'.absent-final-model-cache'))
for n in ['PYTHONPATH','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(n,None)
def info(q):return {'sha256':hashlib.sha256(q.read_bytes()).hexdigest(),'bytes':q.stat().st_size}
inputs=set()
for d in ['work/src','work/include','work/cfg','work/build_support','work/assets','work/third_party','controller','phase','broker','broker-runtime','ui','bridge','binding','finish','model/tests','upstream-default']:
 for q in(P/d).rglob('*'):
  if q.is_file() and q.suffix in ['.s','.inc','.h','.c','.cpp','.hpp','.cfg','.py','.mk','.json','.bin','.prg']and not any(x in q.parts for x in ['.zig-cache','__pycache__','zig-out']):inputs.add(q)
# Assembled worker PRGs are products; their source/buildgraph is closed here.
inputs={q for q in inputs if q.suffix!='.prg'or q.is_relative_to(P/'upstream-default')}
for q in P.glob('*.py'):inputs.add(q)
for n in ['work/Makefile','PARENT_FINISH.json','VERSIONED_IMPORT.json','UPSTREAM_DEFAULT.json']:inputs.add(P/n)
for i,q in enumerate([P/'model/tests/floppy_export/bridge.cpp',*sorted((P/'work/third_party/peddle/Peddle').glob('*.cpp'))]):
 a=['/usr/bin/clang++','-std=c++20','-M','-I'+str(P/'model/tests/host'),'-I'+str(P/'model/tests/floppy_export'),'-I'+str(P/'work/third_party/peddle/Peddle'),str(q)];r=subprocess.run(a,cwd=P,env=env,capture_output=True);assert r.returncode==0,r.stderr.decode();(E/f'deps{i}.txt').write_bytes(r.stdout)
 for n in shlex.split(r.stdout.decode().replace('\\\n',' ').split(':',1)[1]):inputs.add(Path(n).resolve())
for n in ['ca65','ld65','cc65','make','clang++']:inputs.add(Path(shutil.which(n)).resolve())
inputs.add(Path(sys.executable).resolve());sdk=Path(shutil.which('cc65')).resolve().parents[1]/'share/cc65';inputs.add((sdk/'lib/none.lib').resolve())
for name in ['include','asminc']:
 for q in(sdk/name).rglob('*'):
  if q.is_file():inputs.add(q.resolve())
before={str(q):info(q)for q in sorted(inputs)};(E/'INPUTS_BEFORE.json').write_text(json.dumps(before,indent=2)+'\n')
for q in inputs:
 rel=q.relative_to(P)if q.is_relative_to(P)else Path('EXTERNAL')/str(q).lstrip('/');dst=E/'inputs'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,dst)
commands=[]
def run(a):
 t=time.monotonic();r=subprocess.run(a,cwd=P,env=env,capture_output=True);i=len(commands);(E/f'{i:02}.stdout').write_bytes(r.stdout);(E/f'{i:02}.stderr').write_bytes(r.stderr);commands.append({'argv':a,'exit':r.returncode,'seconds':time.monotonic()-t});(E/'COMMANDS.json').write_text(json.dumps(commands,indent=2)+'\n');assert r.returncode==0,(a,r.stderr.decode())
expected={str(q):info(q)for q in [P/'work/build/dos64.prg',P/'ui/panel.prg',P/'broker/broker.prg',P/'bridge/bridge.prg',P/'controller/controller.prg',P/'finish/finish.prg',P/'MODAL.MNU']}
shutil.rmtree(P/'work/build');run([sys.executable,'-B','build_ui_bridge.py','--role','runtime']);run([sys.executable,'-B','build_model.py'])
for n,h in expected.items():assert info(Path(n))==h,('fresh product changed',n)
products=[P/'MODAL.MNU',P/'HEADER.bin',P/'WORKERS.MNU',P/'model/save-peddle.dylib',P/'work/build/dos64-resident.prg.saver.bin']
for d,stem in [('work/build','dos64'),('controller','controller'),('broker','broker'),('broker-runtime','broker'),('bridge','bridge'),('ui','panel'),('phase','transaction-wire'),('phase','modal-save'),('phase','runtime-plan'),('phase','worker-calls'),('binding','binding'),('binding','binding-calls'),('finish','finish')]:
 products += [P/d/(stem+e)for e in ['.prg','.labels','.map']if(P/d/(stem+e)).exists()]
pbefore={str(q):info(q)for q in products};(E/'PRODUCTS_BEFORE.json').write_text(json.dumps(pbefore,indent=2)+'\n')
q=E/'excluded-UNIT';q.mkdir();excluded=[]
for f in(P/'work/build').glob('dos64-tests*'):excluded.append({'file':f.name,**info(f)});f.rename(q/f.name)
(E/'EXCLUDED_UNIT.json').write_text(json.dumps(excluded,indent=2)+'\n')
run([sys.executable,'-B','runtime_versioned_replay.py']);run([sys.executable,'-B','check_defaults.py'])
after={str(q):info(q)for q in inputs};assert after==before,'SUT/source/tool changed'
pa={str(q):info(q)for q in products};assert pa==pbefore,'executed product changed'
for q in inputs:
 rel=q.relative_to(P)if q.is_relative_to(P)else Path('EXTERNAL')/str(q).lstrip('/');assert info(E/'inputs'/rel)==before[str(q)]
for q in products:
 dst=E/'products'/q.relative_to(P);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,dst)
(E/'INPUTS_AFTER.json').write_text(json.dumps(after,indent=2)+'\n');(E/'PRODUCTS_AFTER.json').write_text(json.dumps(pa,indent=2)+'\n')
for n in ['RUNTIME_VERSIONED_RESULT.json','UI_BUILD_RESULT.json','CONTROLLER_BUILD.json']:shutil.copyfile(P/n,E/n)
R={'passed':True,'actual_native_groups':15,'source_tool_SDK_inputs':len(before),'products':len(products),'excluded_UNIT_products':len(excluded),'inputs_copies_products_unchanged':True,'default_controls':'undefined/zeroWIRE2bbf_same_runtime/native6660','scope':'actualruntime only; synthetic mountedfixture, no coldSTART/DOS/device','commands':commands};(E/'RESULT.json').write_text(json.dumps(R,indent=2)+'\n');print(json.dumps({k:v for k,v in R.items()if k!='commands'}))
