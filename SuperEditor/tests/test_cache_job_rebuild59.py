"""Private real59 Full/Plain/Full + ten-job and D81 coarse-clock proof."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,os,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'build/cache-lexical-registration/candidate-59b/project'
TAGS=('fold','sema','inln','page','line','edit','tail','lex','ical','ctrl')

def run(out,source):
 (out/'verifier.py').write_bytes(Path(__file__).read_bytes());project=out/'project';shutil.copytree(source,project,ignore=shutil.ignore_patterns('__pycache__'))
 helper=ROOT/'tools/probes/cache_job_rebuild59/ensure.py';spec=importlib.util.spec_from_file_location('guard59',helper);e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
 assert len(e.editor_names(project))==59
 initial_report=json.loads((project/'build/editor-report.json').read_text());assert initial_report['symbols']['se_presentation_default']==3
 baseline={n:(project/'build/overlays'/(n+'.seo')).read_bytes()for n in e.editor_names(project)}
 baseline_prg=(project/'build/editor.prg').read_bytes()
 initial_source={n:(project/n).read_bytes()for n in('src/cache/editor/build.py','src/cache/lexical/build.py')}
 epoch=int(time.time())-20;tools=out/'tool-bin';tools.mkdir();log=out/'tool-calls.jsonl'
 for name in('ca65','ld65','od65','c1541'):
  real=shutil.which(name);p=tools/name;p.write_text('#!'+sys.executable+'\nimport os,sys,json\nif sys.argv[1:] != ["-V"]:\n with open('+repr(str(log))+',"a")as f:f.write(json.dumps(dict(tool='+repr(name)+',argv=sys.argv[1:]))+"\\n")\nos.execv('+repr(real)+',['+repr(real)+',*sys.argv[1:]])\n');p.chmod(0o755)
 env=dict(os.environ,PATH=str(tools)+os.pathsep+os.environ['PATH'])
 def calls():return[json.loads(x)for x in log.read_text().splitlines()]if log.exists()else[]
 def toolcounts(before):
  r=calls()[before:];return{n:sum(x['tool']==n for x in r)for n in('ca65','ld65','od65','c1541')}
 def normalize():
  for p in(project/'build').rglob('*'):
   if p.is_file():os.utime(p,(epoch,epoch))
 def input_files():return{str(p.relative_to(project/'build')):p.read_bytes()for p in(project/'build').rglob('*')if p.is_file()and (str(p.relative_to(project/'build'))in('editor.prg','editor.lbl','editor-report.json')or p.suffix=='.seo'and p.parent.name=='overlays')}
 def disk_verify():
  modspec=importlib.util.spec_from_file_location('d81_guard59',project/'tools/d81_image.py');m=importlib.util.module_from_spec(modspec);sys.modules[modspec.name]=m;modspec.loader.exec_module(m);disk=m.D81Image((project/'build/supereditor.d81').read_bytes());inputs=e.package_inputs(project)
  for rel,name in inputs['members']:assert disk.read(name.split(',')[0].upper().encode(),kind=1 if name.endswith(',s')else 2).data==(project/rel).read_bytes(),name
  return len(inputs['members'])
 # Append a new private Make overlay. All original app prerequisites remain.
 mk=out/'guard.mk';base=project/'build/cache-editor';lex=project/'build/lexical';pub=project/'build/overlays';disk=project/'build/supereditor.d81'
 cli=f'{sys.executable} {helper} --project {project} --base {project} --out {base} --lexical-out {lex} --publish {pub}'
 mk.write_text(f'''\n.PHONY: cache-jobs-force cache-package-force
cache-jobs-force:
cache-package-force:
build/cache-editor/jobs.stamp: cache-jobs-force
\t{cli}
build/lexical/jobs.stamp: build/cache-editor/jobs.stamp
\t@test -f $@
$(addprefix build/overlays/,$(addsuffix .seo,fold sema inln page line)): build/cache-editor/jobs.stamp
\tcmp -s build/cache-editor/$(@F) $@ || cp build/cache-editor/$(@F) $@
$(addprefix build/overlays/,$(addsuffix .seo,edit tail lex ical ctrl)): build/cache-editor/jobs.stamp
\tcmp -s build/lexical/$(@F) $@ || cp build/lexical/$(@F) $@
build/supereditor.d81: cache-package-force
\t{cli} --package --c1541 {tools/'c1541'}
''')
 def cmd(args,label,guard=False):
  command=['make','-j1','-f','Makefile']+(['-f',str(mk)]if guard else[])+args
  r=subprocess.run(command,cwd=project,env=env,capture_output=True,text=True);(out/(label+'.log')).write_text(r.stdout+r.stderr);assert not r.returncode,(label,(r.stdout+r.stderr)[-3500:]);return r.stdout
 events=[]
 def check(label,build=False,package=False):
  count=len(calls());start=time.monotonic();text=cmd(['editor','build/supereditor.d81'],label,True);used=toolcounts(count);members=disk_verify();checks=[json.loads(x)for x in text.splitlines()if x.startswith('{')];record=dict(checks[-1]);record['observed_publish']=[n for c in checks for n in c['published']];record['job_checks']=checks;assert record['capsules']==10 and record['families']==['base','lexical']
  assert bool(used['ca65'])==build and bool(used['c1541'])==package,(label,used,build,package)
  events.append(dict(label=label,wall_seconds=time.monotonic()-start,tools=used,member_count=members,**record));return record
 check('initial-Full59',True,True)
 assert(project/'build/editor.prg').read_bytes()==baseline_prg
 assert all((pub/(n+'.seo')).read_bytes()==raw for n,raw in baseline.items()),'fresh real ten-job builds differ from registered59 source'
 normalize();mtimes={str(p):p.stat().st_mtime_ns for p in(project/'build').rglob('*')if p.is_file()};check('unchanged-Full59',False,False)
 assert mtimes=={str(p):p.stat().st_mtime_ns for p in(project/'build').rglob('*')if p.is_file()},'no-op touched product outputs'
 # Real private preset changes, with explicitly forced upstream compilation.
 preset=project/'build/editor-settings/presentation-defaults.inc';full_preset=preset.read_bytes();full_cache={str(p.relative_to(project/'build')):p.read_bytes()for root in(base,lex)for p in root.rglob('*')if p.is_file()}
 for name,value in(('Plain',0),('Full-restored',3)):
  preset.write_bytes(full_preset.replace(b'SE_PRESENTATION_DEFAULT=3',('SE_PRESENTATION_DEFAULT='+str(value)).encode()))
  cmd(['-W','build/editor-settings/presentation-defaults.inc','build/editor.prg'],name+'-resident')
  report=json.loads((project/'build/editor-report.json').read_text());assert report['symbols']['se_presentation_default']==value
  # Actual full rebind supplies all59 independent reference capsules. The
  # following equal-time replay models skipped cache stamp recipes explicitly.
  cmd(['-W','build/editor.prg','editor'],name+'-reference')
  expected={n:(pub/(n+'.seo')).read_bytes()for n in e.editor_names(project)}
  previous={str(p.relative_to(project/'build')):p.read_bytes()for root in(base,lex)for p in root.rglob('*')if p.is_file()}
  if name=='Plain':
   reference_plain=input_files();stale=full_cache
  else:stale=plain_cache
  for rel,data in stale.items():p=project/'build'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  for n in TAGS:
   folder=base if n in e.TAGS else lex;(pub/(n+'.seo')).write_bytes((folder/(n+'.seo')).read_bytes())
  normalize()
  legacy=out/(name+'-legacy.mk');legacy.write_text('all: '+str(base/'jobs.stamp')+' '+str(lex/'jobs.stamp')+'\n'+f'{base}/jobs.stamp: {project}/build/editor.prg {project}/build/editor.lbl {project}/build/editor-report.json\n\t{sys.executable} {project}/src/cache/editor/build.py {base} {project}\n'+f'{lex}/jobs.stamp: {project}/build/editor.prg {project}/build/editor.lbl {project}/build/editor-report.json\n\t{sys.executable} {project}/src/cache/lexical/build.py {lex} {project}\n')
  count=len(calls());r=subprocess.run(['make','-f',str(legacy)],cwd=project,env=env,capture_output=True,text=True);assert not r.returncode and len(calls())==count;(out/(name+'-legacy.log')).write_text(r.stdout+r.stderr)
  assert all((pub/(n+'.seo')).read_bytes()[20:36].hex()!=report['resident_binding']['digest']for n in TAGS),'equal-time replay must leave all ten foreign'
  check('same-second-'+name,True,True)
  assert all((pub/(n+'.seo')).read_bytes()==expected[n]for n in expected),'guarded fresh source capsules differ from actual reference rebind'
  if name=='Plain':plain_cache={str(p.relative_to(project/'build')):p.read_bytes()for root in(base,lex)for p in root.rglob('*')if p.is_file()}
 assert(project/'build/editor.prg').read_bytes()==baseline_prg,'restored Full resident differs'
 assert all((pub/(n+'.seo')).read_bytes()==raw for n,raw in baseline.items()),'restored all59 capsule bytes differ'
 normalize();mtimes={str(p):p.stat().st_mtime_ns for p in(project/'build').rglob('*')if p.is_file()};check('unchanged-restored-Full59',False,False);assert mtimes=={str(p):p.stat().st_mtime_ns for p in(project/'build').rglob('*')if p.is_file()}
 # Lexical source and artifacts are independently part of the combined proof.
 p=project/'src/cache/lexical/api.inc';old=p.read_bytes();p.write_bytes(old+b'\n; private closure regression\n');os.utime(p,(epoch,epoch));check('lexical-include-change',True,False);p.write_bytes(old);os.utime(p,(epoch,epoch));check('lexical-include-restore',True,False)
 (lex/'ical.seo').unlink();check('missing-lexical-output',True,False)
 p=lex/'lex.bin';raw=p.read_bytes();p.write_bytes(raw[:-1]+bytes([raw[-1]^1]));os.utime(p,(epoch,epoch));check('corrupt-lexical-raw',True,False)
 p=pub/'ctrl.seo';p.write_bytes(b'bad');record=check('published-lexical-repair',False,False);assert record['observed_publish']==['ctrl.seo']
 # A failing second builder must not publish the first newly built family.
 builder=project/'src/cache/lexical/build.py';old=builder.read_bytes();builder.write_bytes(old+b'\nraise RuntimeError("private second-family failure")\n');before={str(p):e.sha(p)for root in(base,lex,pub)for p in root.rglob('*')if p.is_file()};r=subprocess.run([sys.executable,helper,'--project',project,'--base',project,'--out',base,'--lexical-out',lex,'--publish',pub],capture_output=True,text=True,env=env);assert r.returncode;after={str(p):e.sha(p)for root in(base,lex,pub)for p in root.rglob('*')if p.is_file()};assert before==after,'second-family failure altered old proof/artifacts';(out/'second-family-failure.log').write_text(r.stdout+r.stderr);builder.write_bytes(old);check('second-family-recovered',False,False)
 # Forgetting the new family is an explicit refusal, never a five-only success.
 r=subprocess.run([sys.executable,helper,'--project',project,'--base',project,'--out',base,'--publish',pub],capture_output=True,text=True,env=env);assert r.returncode and '--lexical-out'in r.stderr;(out/'omitted-family-refusal.log').write_text(r.stdout+r.stderr)
 for n,data in initial_source.items():assert(project/n).read_bytes()==data,'immutable source builder changed'
 result=dict(status='PASS-private-content-aware59',source_project=str(source),resident_sha256=e.sha(project/'build/editor.prg'),binding=json.loads((project/'build/editor-report.json').read_text())['resident_binding']['digest'],events=events,registered_capsules=59,guarded_jobs=10,packaged_members=disk_verify(),real_Full_Plain_Full=True,unchanged_zero_compile_copy_c1541_and_all_mtimes=True,second_builder_failure_preserves_both_families=True,missing_family_refuses=True,source_closure=e.closure(project),all59_original_source_bytes_restored=True,scope='Copied immutable private promotion59 project only; actual Make/ca65/ld65/package.py/c1541; no application/native/hardware/sharedbuild/Git changes.')
 result['source_closure']=[str(p.relative_to(project))for p in result['source_closure']];(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',type=Path,default=SOURCE);a=p.parse_args();out=ROOT/'build/cache-job-rebuild59'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.project.resolve());print(r['status'],len(r['events']),r['registered_capsules'],r['packaged_members'])
