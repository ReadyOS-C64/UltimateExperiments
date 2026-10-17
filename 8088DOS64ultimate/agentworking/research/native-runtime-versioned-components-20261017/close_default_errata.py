from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;assert Path.cwd()==P
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-default-errata');assert not Path(sys.pycache_prefix).exists()
import hashlib,json,shutil,subprocess,time
E=P/'final-host-closure';assert not E.exists();E.mkdir()
def info(q):return{'sha256':hashlib.sha256(q.read_bytes()).hexdigest(),'bytes':q.stat().st_size}
prior=P/'first-runtime-default-oracle';old=json.loads((prior/'INPUTS_BEFORE.json').read_text());products=json.loads((prior/'PRODUCTS_BEFORE.json').read_text())
# Only the role-aware host oracle and its summary differ; all SUT/model/builders/native tests remain exact.
changed=[]
for n,v in old.items():
 if info(Path(n))!=v:changed.append(n)
assert set(changed)=={str(P/'check_defaults.py'),str(P/'close_runtime.py')},changed
before={n:info(Path(n))for n in old}
for q in [P/'upstream-default/phase/old_transaction_wire.s',P/'close_default_errata.py']:before[str(q)]=info(q)
(E/'INPUTS_BEFORE.json').write_text(json.dumps(before,indent=2)+'\n')
for n in before:
 q=Path(n);rel=q.relative_to(P)if q.is_relative_to(P)else Path('EXTERNAL')/str(q).lstrip('/');d=E/'inputs'/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,d)
for n,v in products.items():assert info(Path(n))==v,n
commands=[];env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPYCACHEPREFIX=str(P/'.absent-final-host-model'))
for n in ['PYTHONPATH','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(n,None)
def run(a):
 t=time.monotonic();r=subprocess.run(a,cwd=P,env=env,capture_output=True);i=len(commands);(E/f'{i:02}.stdout').write_bytes(r.stdout);(E/f'{i:02}.stderr').write_bytes(r.stderr);commands.append({'argv':a,'exit':r.returncode,'seconds':time.monotonic()-t});(E/'COMMANDS.json').write_text(json.dumps(commands,indent=2)+'\n');assert r.returncode==0,(a,r.stderr.decode())
shutil.rmtree(P/'work/build');run([sys.executable,'-B','build_ui_bridge.py','--role','runtime']);run([sys.executable,'-B','build_model.py'])
for n,v in products.items():assert info(Path(n))==v,('productrebuild',n)
q=E/'excluded-UNIT';q.mkdir();excluded=[]
for f in(P/'work/build').glob('dos64-tests*'):excluded.append({'name':f.name,**info(f)});f.rename(q/f.name)
(E/'EXCLUDED_UNIT.json').write_text(json.dumps(excluded,indent=2)+'\n');assert not list((P/'work/build').glob('dos64-tests*'))
if(P/'default-controls').exists():shutil.move(P/'default-controls',P/'preliminary-correct-default')
run([sys.executable,'-B','check_defaults.py'])
for n,v in before.items():assert info(Path(n))==v,('sourcechanged',n)
for n,v in products.items():assert info(Path(n))==v,('productchanged',n)
for n in before:
 q=Path(n);rel=q.relative_to(P)if q.is_relative_to(P)else Path('EXTERNAL')/str(q).lstrip('/');assert info(E/'inputs'/rel)==before[n]
(E/'INPUTS_AFTER.json').write_text(json.dumps(before,indent=2)+'\n');(E/'PRODUCTS_AFTER.json').write_text(json.dumps(products,indent=2)+'\n')
(E/'RESULT.json').write_text(json.dumps({'passed':True,'current_source_tool_SDK_inputs':len(before),'products_reproduced_exact':len(products),'retained_actual_native_groups':15,'native_reexecution':False,'native_group_authority':'first-runtime-default-oracle: actual15 successful with exact before/after sources,copies/products. Onlylaterhostdefaultoracle failed dueUNIT-vs-runtimebaseline. Currenthostdefault correctiondoesnot affectSUT/testsource/products.','old_new_same_runtime_WIRE':json.loads((P/'default-controls/RESULT.json').read_text()),'commands':commands},indent=2)+'\n');print((E/'RESULT.json').read_text())
