from pathlib import Path
import sys,os,hashlib,json,subprocess,shutil,time
P=Path(__file__).resolve().parent;D=P/'closed-finish';assert not D.exists();D.mkdir();sys.dont_write_bytecode=True
h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
inputs=set()
for root in ['work/src','work/include','work/cfg','work/build_support','work/assets','work/third_party','broker','broker-runtime','ui','bridge','phase','binding','controller','finish','model/tests']:
 for f in(P/root).rglob('*'):
  if f.is_file()and f.suffix in ['.c','.h','.s','.inc','.cfg','.cpp','.hpp','.py','.mk','.bin']:inputs.add(f)
for f in P.glob('*.py'):inputs.add(f)
inputs.add(P/'work/Makefile')
for root in ['include','asminc']:
 inputs.update(f for f in(Path('/opt/homebrew/share/cc65')/root).rglob('*')if f.is_file())
inputs.add(Path('/opt/homebrew/share/cc65/lib/none.lib'))
tools={n:Path(shutil.which(n)).resolve()for n in ['python3','cc65','ca65','ld65','make','clang++']};inputs.update(tools.values())
rec={str(f):{'sha256':h(f),'bytes':f.stat().st_size}for f in sorted(inputs)}
for f in sorted(inputs):
 q=D/'inputs'/(f.relative_to(P)if f.is_relative_to(P)else Path('EXTERNAL')/str(f).lstrip('/'));q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,q)
(D/'INPUTS_BEFORE.json').write_text(json.dumps(rec,indent=2)+'\n');commands=[];env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
for n in ['PYTHONPATH','PYTHONPYCACHEPREFIX','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(n,None)
def run(name,a):
 t=time.monotonic()
 with(D/(name+'.stdout')).open('wb')as o,(D/(name+'.stderr')).open('wb')as e:r=subprocess.run(a,cwd=P,env=env,stdout=o,stderr=e)
 commands.append({'name':name,'argv':a,'exit':r.returncode,'seconds':time.monotonic()-t});(D/'COMMANDS.json').write_text(json.dumps(commands,indent=2)+'\n');assert not r.returncode,name
products=['MODAL.MNU','HEADER.bin','WORKERS.MNU']
for d,stem in [('work/build','dos64'),('broker','broker'),('broker-runtime','broker'),('ui','panel'),('bridge','bridge'),('controller','controller'),('finish','finish'),('phase','transaction-wire'),('phase','modal-save'),('phase','runtime-plan'),('binding','binding')]:
 for ext in ['.prg','.labels','.map']:products.append(d+'/'+stem+ext)
expected={f:h(P/f)for f in products};shutil.rmtree(P/'work/build');run('fresh-native',[str(tools['python3']),'-B','build_ui_bridge.py','--role','runtime']);assert all(h(P/f)==v for f,v in expected.items()),'fresh native product changed'
run('fresh-model',[str(tools['python3']),'-B','build_model.py']);products.append('model/save-peddle.dylib');frozen={f:{'sha256':h(P/f),'bytes':(P/f).stat().st_size}for f in products}
q=D/'excluded-UNIT';q.mkdir();excluded=[]
for f in(P/'work/build').glob('dos64-tests*'):excluded.append({'name':f.name,'sha256':h(f)});f.rename(q/f.name)
(D/'EXCLUDED_UNIT.json').write_text(json.dumps(excluded,indent=2)+'\n');run('actual-runtime',[str(tools['python3']),'-B','finish_role_replay.py'])
for f,v in rec.items():assert h(Path(f))==v['sha256'],f
for f,v in frozen.items():assert h(P/f)==v['sha256'];q=D/'products'/f;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(P/f,q)
for f in sorted(inputs):
 q=D/'inputs'/(f.relative_to(P)if f.is_relative_to(P)else Path('EXTERNAL')/str(f).lstrip('/'));assert h(q)==rec[str(f)]['sha256']
(D/'INPUTS_AFTER.json').write_text(json.dumps(rec,indent=2)+'\n');(D/'PRODUCTS.json').write_text(json.dumps(frozen,indent=2)+'\n');(D/'RESULT.json').write_text(json.dumps({'passed':True,'inputs':len(rec),'products':len(frozen),'excluded_UNIT':len(excluded),'commands':commands,'scope':'actual runtime/CIA Finish8 + SaveAs1; synthetic media; no cold/DOS/physical'},indent=2)+'\n')
