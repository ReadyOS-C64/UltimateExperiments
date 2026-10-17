from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;W=P/'work';R=P.parents[2];E=P.parent/'live-media-runtime-assets-root-20261017'
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-final-run');assert not Path(sys.pycache_prefix).exists()
import hashlib,json,subprocess,shutil,importlib.util
D=lambda p:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
record={}
for q in W.rglob('*'):
 if not q.is_file():continue
 if q.suffix in ['.c','.h','.cfg','.py','.inc']or(q.suffix=='.s'and not q.with_suffix('.c').exists()and q.name!='platform_c.s')or q.name in ['DOS64.MNU','modal-header.bin','bulk-peddle.dylib']:record[str(q)]=D(q)
for n in ['build.py','pack.py','defaults.py','final_exec.py']:record[str(P/n)]=D(P/n)
for n in ['build_support/start_launcher.py','build_support/start_template_descriptor.py','build_support/setup_release_descriptor.py']:record[str(R/n)]=D(R/n)
for n in ['MANIFEST.json','BINDING.json','HEADER.bin','work/build/dos64.prg','work/build/dos64.labels','broker-runtime/broker.prg','broker-runtime/broker.labels','ui/panel.prg']:record[str(E/n)]=D(E/n)
for n in ['cc65','ca65','ld65','make']:
 q=Path(shutil.which(n)).resolve();record[str(q)]=D(q)
record[str(Path(sys.executable).resolve())]=D(Path(sys.executable).resolve())
cc=Path(shutil.which('cc65')).resolve().parent.parent/'share/cc65';record[str(cc/'lib/none.lib')]=D(cc/'lib/none.lib')
for q in (cc/'include').rglob('*.h'):record[str(q)]=D(q)
(P/'EXEC_INPUTS_BEFORE.json').write_text(json.dumps(record,indent=2)+'\n')
commands=[]
for name,script,cwd in [('pack',P/'pack.py',P),('build',P/'build.py',P),('modal',W/'test_modal.py',W),('DOS',W/'test_handoff_entry.py',W)]:
 argv=[sys.executable,'-B',str(script)];commands.append({'cwd':str(cwd),'argv':argv})
 with (P/('FINAL_RUN_'+name+'.stdout')).open('wb')as out,(P/('FINAL_RUN_'+name+'.stderr')).open('wb')as err:subprocess.run(argv,cwd=cwd,stdout=out,stderr=err,check=True)
for n,v in record.items():assert D(Path(n))==v,('Source/input changed',n)
(P/'EXEC_INPUTS_AFTER.json').write_text(json.dumps(record,indent=2)+'\n')
products={str(W/n):D(W/n)for n in ['controller.prg','START.INO','controller.labels','controller.map','START.REL','DOS64.REL','DOS64.MNU','MODAL_RESULT.json','HANDOFF_ENTRY_RESULT.json','DOS_BEFORE_MENU.json']}
(P/'EXEC_RESULT.json').write_text(json.dumps({'status':'passed','source_inputs':len(record),'input_ledger_before_after_exact':True,'actual_groups':9,'products':products,'commands':commands,'physical':False,'scope':'cold START runtime-role MNU load8; genuineDOS VER/DIR+2MiBC then CIA/CUI Resume1; no SAVE/Swap/Turbo'},indent=2)+'\n')
print('PASS source-closed9 groups; inputs',len(record))
