from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;assert Path.cwd()==P;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-combined-close-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import json,hashlib,shutil,subprocess,shlex
D=P/'final-closed';D.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();deps=set();tools={n:{'path':str(Path(shutil.which(n)).resolve()),'sha256':sha(Path(shutil.which(n)).resolve())}for n in ['python3','cc65','ca65','ld65','make','clang++']};env=dict(os.environ)
for n in ['PYTHONPATH','PYTHONPYCACHEPREFIX','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG','COLD_NO_DOS_DIAG']:env.pop(n,None)
env['PYTHONDONTWRITEBYTECODE']='1';cpp=[]
for base,model in [(P/'work',P/'work/tests'),(P/'runtime/work',P/'runtime/model/tests')]:
 tus=[model/'floppy_export/bridge.cpp',*[base/'third_party/peddle/Peddle'/n for n in ['Peddle.cpp','PeddleDebugger.cpp','PeddleDisassembler.cpp','StrWriter.cpp']]]
 inc=['-I'+str(model/'floppy_export'),'-I'+str(model/'host'),'-I'+str(base/'third_party/peddle/Peddle')]
 for f in tus:
  cmd=[tools['clang++']['path'],'-std=c++20','-M',*inc,str(f)];r=subprocess.run(cmd,cwd=P,env=env,capture_output=True);(D/('CPP_DEPS%d.txt'%len(cpp))).write_bytes(r.stdout);assert not r.returncode,r.stderr.decode();cpp.append(cmd)
  deps.update(Path(n).resolve()for n in shlex.split(r.stdout.decode().replace('\\\n',' ').split(':',1)[1]))
for root in ['runtime','work','gate','worker','dependencies','inputs']:
 for f in(P/root).rglob('*'):
  if not f.is_file()or'__pycache__'in f.parts or f.name.startswith('dos64-tests'):continue
  if f.suffix in ['.s','.inc','.cfg','.h','.c','.cpp','.py','.mk','.bin','.img','.prg','.labels','.map']or f.name=='Makefile':deps.add(f.resolve())
deps.update(f.resolve()for f in P.glob('*.py'))
deps.update(f.resolve()for f in Path('/opt/homebrew/share/cc65/include').rglob('*')if f.is_file());deps.add(Path('/opt/homebrew/share/cc65/lib/none.lib').resolve())
items=[]
for f in sorted(deps):
 c=D/'inputs'/str(f).lstrip('/');c.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,c);items.append({'path':str(f),'copy':str(c.relative_to(P)),'sha256':sha(f)})
(D/'BEFORE.json').write_text(json.dumps(items,indent=2)+'\n');(D/'TOOLS.json').write_text(json.dumps(tools,indent=2)+'\n');(D/'CPP_DEP_COMMANDS.json').write_text(json.dumps(cpp,indent=2)+'\n');commands=[]
def run(name,cmd,cwd=P):
 with(D/(name+'.stdout')).open('wb')as out,(D/(name+'.stderr')).open('wb')as err:r=subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,stdout=out,stderr=err)
 commands.append({'name':name,'argv':list(map(str,cmd)),'cwd':str(cwd),'exit':r.returncode});(D/'COMMANDS.json').write_text(json.dumps(commands,indent=2)+'\n');assert r.returncode==0,name
py=tools['python3']['path'];run('runtime-build',[py,'-B','build_ui_bridge.py','--role','runtime'],P/'runtime');run('cold-couple',[py,'-B','couple.py'])
for base,model,out in [('work','work/tests','work/journal-peddle.dylib'),('runtime/work','runtime/model/tests','runtime/model/save-peddle.dylib')]:
 run('model-'+base.replace('/','-'),[tools['clang++']['path'],'-std=c++20','-O2','-fPIC','-shared','-I'+model+'/floppy_export','-I'+model+'/host','-I'+base+'/third_party/peddle/Peddle',model+'/floppy_export/bridge.cpp',*[base+'/third_party/peddle/Peddle/'+n for n in ['Peddle.cpp','PeddleDebugger.cpp','PeddleDisassembler.cpp','StrWriter.cpp']],'-o',out])
quarantine=D/'excluded-UNIT';quarantine.mkdir()
for f in(P/'runtime/work/build').glob('dos64-tests*'):shutil.move(f,quarantine/f.name)
run('warm-refusals',[py,'-B','warm_controls.py'],P/'runtime');run('initial-binding',[py,'-B','work/test_initial_binding.py']);run('cold-faults',[py,'-B','work/test_coupled_faults.py']);run('cold-S-controls-Resume-Cread-Finish',[py,'-B','work/test_cold_media.py'])
for r in items:assert sha(Path(r['path']))==r['sha256'],r['path'];assert sha(P/r['copy'])==r['sha256']
for t in tools.values():assert sha(Path(t['path']))==t['sha256']
(D/'AFTER.json').write_text(json.dumps(items,indent=2)+'\n');(D/'RESULT.json').write_text(json.dumps({'passed':True,'groups':8,'source_and_SDK_inputs_with_copies':len(items),'tools':6,'commands':commands,'scope':'actualcold SYS/DOS→ordinaryS→EjectProtect→Resume/Cread→Finish plus scopednative refusals; no device'},indent=2)+'\n')
