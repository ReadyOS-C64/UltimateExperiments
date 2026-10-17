from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;assert Path.cwd()==P
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-close-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import json,hashlib,shutil,subprocess,shlex
W=P/'project';D=P/'final-closed';D.mkdir();sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest();env=dict(os.environ)
for k in ['CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG','PYTHONPATH','PYTHONPYCACHEPREFIX']:env.pop(k,None)
env['PYTHONDONTWRITEBYTECODE']='1';tools={n:{'path':str(Path(shutil.which(n)).resolve()),'sha256':sha(Path(shutil.which(n)).resolve())}for n in ['python3','cc65','ca65','ld65','make','clang++']};deps=set();cpp=[]
tus=[W/'model/tests/floppy_export/bridge.cpp',*[W/'work/third_party/peddle/Peddle'/n for n in ['Peddle.cpp','PeddleDebugger.cpp','PeddleDisassembler.cpp','StrWriter.cpp']]];inc=['-I'+str(W/'model/tests/floppy_export'),'-I'+str(W/'model/tests/host'),'-I'+str(W/'work/third_party/peddle/Peddle')]
for i,q in enumerate(tus):
 cmd=[tools['clang++']['path'],'-std=c++20','-M',*inc,str(q)];r=subprocess.run(cmd,cwd=P,env=env,capture_output=True);assert not r.returncode,r.stderr.decode();(D/f'CPP_DEPS{i}.txt').write_bytes(r.stdout);cpp.append(cmd);deps.update(Path(n).resolve()for n in shlex.split(r.stdout.decode().replace('\\\n',' ').split(':',1)[1]))
for root in ['work/src','work/include','work/cfg','model','phase','binding','broker']:
 for q in(W/root).rglob('*'):
  if q.is_file() and'__pycache__'not in q.parts and q.suffix in ['.s','.inc','.cfg','.c','.h','.cpp','.py','.bin','.prg','.labels','.map']:deps.add(q.resolve())
for q in(W/'work/build').glob('*'):
 if q.is_file()and not q.name.startswith('dos64-tests')and q.suffix in ['.prg','.bin','.labels','.map','.json']:deps.add(q.resolve())
deps.update(q.resolve()for q in W.glob('*.py'));deps.update(q.resolve()for q in P.glob('*.py'));deps.update(q.resolve()for q in Path('/opt/homebrew/share/cc65/include').rglob('*')if q.is_file());deps.add(Path('/opt/homebrew/share/cc65/lib/none.lib').resolve())
items=[]
for q in sorted(deps):
 c=D/'inputs'/str(q).lstrip('/');c.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,c);items.append({'path':str(q),'copy':str(c.relative_to(P)),'sha256':sha(q)})
(D/'BEFORE.json').write_text(json.dumps(items,indent=2)+'\n');(D/'TOOLS.json').write_text(json.dumps(tools,indent=2)+'\n');(D/'CPP_COMMANDS.json').write_text(json.dumps(cpp,indent=2)+'\n');commands=[]
def run(name,cmd,cwd=P):
 with(D/(name+'.stdout')).open('wb')as o,(D/(name+'.stderr')).open('wb')as e:r=subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,stdout=o,stderr=e)
 commands.append({'name':name,'cwd':str(cwd),'argv':list(map(str,cmd)),'exit':r.returncode});(D/'COMMANDS.json').write_text(json.dumps(commands,indent=2)+'\n');assert not r.returncode,name
py=tools['python3']['path'];run('build',[py,'-B','build_insert.py','policy-final-products-build']);run('model',[tools['clang++']['path'],'-std=c++20','-O2','-fPIC','-shared',*inc,*tus,'-o',W/'model/save-peddle.dylib']);run('native-nine',[py,'-B','test_insert_commit.py'],W);run('default-undefined-zero',[py,'-B','check_default.py','policy-final-defaults']);run('exhausted',[py,'-B','test_insert_exhausted.py'],W);run('zero',[py,'-B','test_insert_zero_crc.py'],W)
for x in items:assert sha(Path(x['path']))==x['sha256'],x['path'];assert sha(P/x['copy'])==x['sha256']
for x in tools.values():assert sha(Path(x['path']))==x['sha256']
(D/'AFTER.json').write_text(json.dumps(items,indent=2)+'\n');(D/'RESULT.json').write_text(json.dumps({'passed':True,'groups':12,'inputs_and_copies':len(items),'tools':6,'borrowed_native_main_parent':'c866d8f6 source/products unchanged; no native main source change','source_rebuilt':'WIRE, Insert BIND/support/wrapper, undefined/0 Save WIRE/BIND, full CABI/Peddle model','scope':'actual WIRE/BIND/nativeCOMMIT, synthetic Incoming/PLAN fixture, no controller/CUI/device'},indent=2)+'\n')
