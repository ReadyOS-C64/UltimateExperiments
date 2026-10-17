from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;W=P/'work';R=P.parents[2]
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-source-closed-run');assert not Path(sys.pycache_prefix).exists()
import hashlib,json,subprocess,shutil
D=lambda p:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
inputs={}
for directory in [W,P/'gate',P/'inputs']:
 for q in directory.rglob('*'):
  if not q.is_file()or '__pycache__'in q.parts:continue
  if directory==P/'inputs'or q.suffix in ['.c','.h','.hpp','.inc','.cfg','.py','.cpp']or(q.suffix=='.s'and not q.with_suffix('.c').exists()and q.name!='platform_c.s')or q.name in ['DOS64.MNU','modal-header.bin']:inputs[str(q)]=D(q)
for n in ['build.py','pack.py','defaults.py','couple.py','build_gate.py','final_exec.py','DEFAULTS.json','NATIVE_FIXTURE_ORIGIN.json']:inputs[str(P/n)]=D(P/n)
for n in ['start_launcher.py','start_template_descriptor.py','setup_release_descriptor.py']:inputs[str(R/'build_support'/n)]=D(R/'build_support'/n)
for n in ['cc65','ca65','ld65','clang++']:
 q=Path(shutil.which(n)).resolve();inputs[str(q)]=D(q)
q=Path(sys.executable).resolve();inputs[str(q)]=D(q)
cc=Path(shutil.which('cc65')).resolve().parent.parent/'share/cc65'
for q in (cc/'include').rglob('*.h'):inputs[str(q)]=D(q)
inputs[str(cc/'lib/none.lib')]=D(cc/'lib/none.lib')
(P/'FINAL_INPUTS_BEFORE.json').write_text(json.dumps(inputs,indent=2)+'\n');commands=[]
def run(name,argv,cwd):
 commands.append({'name':name,'cwd':str(cwd),'argv':list(map(str,argv))})
 with(P/(name+'.stdout')).open('wb')as out,(P/(name+'.stderr')).open('wb')as err:subprocess.run(argv,cwd=cwd,stdout=out,stderr=err,check=True)
run('FINAL_MODEL',['/usr/bin/clang++','-std=c++20','-O2','-dynamiclib','-Itests/floppy_export','-Itests/host','-Ithird_party/peddle/Peddle','tests/floppy_export/bridge.cpp',*[f'third_party/peddle/Peddle/{n}'for n in ['Peddle.cpp','PeddleDebugger.cpp','PeddleDisassembler.cpp','StrWriter.cpp']],'-o','journal-peddle.dylib'],W)
run('FINAL_COUPLE',[sys.executable,'-B',str(P/'couple.py')],P)
run('FINAL_TEST',[sys.executable,'-B','test_journal_start.py'],W)
for n,v in inputs.items():assert D(Path(n))==v,('Source/input changed',n)
(P/'FINAL_INPUTS_AFTER.json').write_text(json.dumps(inputs,indent=2)+'\n')
products={str(W/n):D(W/n)for n in ['controller.prg','START.INO','controller.labels','controller.map','START.RCV','START.REL','DOS64.REL','JOURNAL_START_RESULT.json','journal-peddle.dylib']}
for n in ['gate/START.RCV','gate/gate.labels','gate/gate.map','gate/MATCHED_BINDING.json','COUPLED_RESULT.json']:products[str(P/n)]=D(P/n)
(P/'FINAL_RESULT.json').write_text(json.dumps({'status':'passed','actual_native_groups':9,'inputs_before_after_exact':len(inputs),'fresh_model_compiled_from_captured_sources':True,'raw_RCV_disk_payload_has_no_loadword':True,'default_public_START_INO_exact_profiles':2,'commands':commands,'products':products,'physical':False,'scope':'actual START checks/loads RCV before normal CFG; nojournal then restores INO and hands off; pending/error blocks; no recovery mutation/archive'},indent=2)+'\n');print('PASS sourceclosed actual9; source/tool/media inputs',len(inputs))
