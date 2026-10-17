from pathlib import Path
import hashlib,json,subprocess,sys,shutil,os,time
P=Path(__file__).resolve().parent;D=P/'final-attested';D.mkdir();h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rows={};cmds=[]
inputs=[P/n for n in ['build_controller.py','close_execution.py','test_controller.py','test_online_save.py','fixture_base.py','controller_fixture.py','fixture_config.py','dos_disk_inspect.py','refresh_inputs.py','CORRECTED_BINDING_INPUTS.json','INPUT_PRODUCTS.json']]
inputs += [P/'controller'/n for n in ['action_shell.c','action_shell.h','action_io.c','native_calls.s','entry.s','controller.cfg','media_plan.h']]
for directory in ['work/build','phase','binding','broker','model']:
 inputs += [p for p in (P/directory).rglob('*')if p.is_file()]
for n in ['cc65','ca65','ld65','python3']:inputs.append(Path(shutil.which(n)).resolve())
sdk=Path(shutil.which('cc65')).resolve().parents[1]/'share/cc65';inputs+=[sdk/'lib/none.lib']+list((sdk/'include').rglob('*.h'))
inputs=sorted(set(inputs));(D/'inputs').mkdir()
for i,p in enumerate(inputs):
 b=p.read_bytes();copy=D/'inputs'/('%04d-%s'%(i,p.name));copy.write_bytes(b);rows[str(p)]={'bytes':len(b),'sha256':h(p),'copy':str(copy)}
(D/'INPUTS.json').write_text(json.dumps(rows,indent=2)+'\n');first=None;started=time.monotonic()
try:
 for name,argv in [('build',[sys.executable,'-B','build_controller.py']),('test',[sys.executable,'-B','test_controller.py'])]:
  with(D/(name+'.stdout')).open('wb')as out,(D/(name+'.stderr')).open('wb')as err:r=subprocess.run(argv,cwd=P,stdout=out,stderr=err)
  cmds.append({'name':name,'argv':argv,'exit':r.returncode});assert r.returncode==0,(name,r.returncode)
except BaseException as e:first=repr(e)
after={str(p):h(p)for p in inputs};changed=[s for s,v in rows.items()if after[s]!=v['sha256']]
result={'pass':first is None and not changed,'first_failure':first,'changed_inputs':changed,'inputs':len(rows),'commands':cmds,'elapsed':time.monotonic()-started,'scope':'fresh controller rebuild and7 realnative groups using exact parent core/model/worker products; synthetic launch anchors, no CUI/coldcontainer/DOS/physical acceptance'}
for n in ['CONTROLLER_BUILD.json','CONTROLLER_TEST_RESULT.json','WORKERS.MNU','controller/controller.prg','controller/controller.map','controller/controller.labels']:
 p=P/n
 if p.exists():shutil.copyfile(p,D/p.name)
(D/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));raise SystemExit(not result['pass'])
