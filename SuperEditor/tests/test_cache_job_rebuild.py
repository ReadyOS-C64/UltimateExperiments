"""Actual make3.81/equal-timestamp stale-seal reproduction and guarded rebuild."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,os,shutil,subprocess,sys,time,zipfile
ROOT=Path(__file__).resolve().parents[1]
A=ROOT/'build/cache-editor-product/20261026T051042908519Z/fixture'
B=ROOT/'build/cache-editor-product/20261026T035310363807Z/fixture'
TAGS=('fold','sema','inln','page','line')

def packaging(out,project,a,b,e,env,epoch):
 # Reconstruct the exact real packager inputs from immutable media. No generic
 # probe report is guessed: only the four fields consumed by package.py are
 # decoded from the authentic RONE sidecar; regenerated fixtures are compared.
 sys.path.insert(0,str(project/'tools'));from d81_image import D81Image
 manifest=json.loads((a/'build/disk-manifest.json').read_text());command=manifest['command'];media=D81Image((a/'build/supereditor.d81').read_bytes());members=[]
 for i,item in enumerate(command):
  if item!='-write':continue
  rel='build/'+command[i+1].split('/build/',1)[1];name=command[i+2];p=project/rel;p.parent.mkdir(parents=True,exist_ok=True)
  raw=media.read(name.split(',')[0].upper().encode(),kind=1 if name.endswith(',s')else 2).data;p.write_bytes(raw);members.append((rel,name))
 rone=(project/'build/overlays/rone.seo').read_bytes();probe=dict(symbols=dict(se_overlay_call=int.from_bytes(rone[16:18],'little'),se_overlay_frame=int.from_bytes(rone[18:20],'little')),resident_binding=dict(digest=rone[20:36].hex()))
 (project/'build/overlay-probe-report.json').write_text(json.dumps(probe))
 def select(fixture):
  for n in('editor.prg','editor.lbl','editor-report.json'):shutil.copyfile(fixture/'build'/n,project/'build'/n)
  for n in e.editor_names(project):shutil.copyfile(fixture/'build/overlays'/(n+'.seo'),project/'build/overlays'/(n+'.seo'))
 def normalize():
  for p in (project/'build').rglob('*'):
   if p.is_file():os.utime(p,(epoch,epoch))
 select(a);jobs=project/'build/cache-editor';published=project/'build/overlays'
 e.ensure(project,project,jobs,published)
 c_log=out/'c1541-invocations.jsonl';tool=out/'c1541-wrapper';actual=shutil.which('c1541')
 tool.write_text('#!'+sys.executable+'\nimport os,sys,json\nwith open('+repr(str(c_log))+',"a")as f:f.write(json.dumps(sys.argv[1:])+"\\n")\nif os.environ.get("CACHE_PROBE_C1541_FAIL"):sys.exit(2)\nos.execv('+repr(actual)+',['+repr(actual)+',*sys.argv[1:]])\n');tool.chmod(0o755)
 helper=ROOT/'tools/probes/cache_job_rebuild/ensure.py';mk=out/'packaging.mk';disk=project/'build/supereditor.d81'
 mk.write_text(f'.PHONY: FORCE\n{disk}: FORCE\n\t{sys.executable} {helper} --project {project} --base {project} --out {jobs} --publish {published} --package --c1541 {tool}\n')
 events=[]
 def calls():return len(c_log.read_text().splitlines())if c_log.exists()else 0
 def verify():
  disk_image=D81Image(disk.read_bytes());current=e.package_inputs(project)
  for rel,name in current['members']:
   assert disk_image.read(name.split(',')[0].upper().encode(),kind=1 if name.endswith(',s')else 2).data==(project/rel).read_bytes(),rel
  return len(current['members'])
 def invoke(label,want_rebuild,want_package):
  start=calls();log=subprocess.check_output(['make','-f',str(mk)],text=True,stderr=subprocess.STDOUT,env=env);(out/(label+'.log')).write_text(log);r=json.loads(log.splitlines()[-1]);assert r['rebuilt']==want_rebuild and r['disk']['packaged']==want_package,(label,r)
  assert calls()-start==int(want_package),(label,'actual c1541 invocation count')
  count=verify();assert count==len(members);events.append(dict(label=label,**r));return r
 invoke('package-initial-A',False,True)
 # Every real disk member, not just the five jobs, matches the original medium.
 initial=D81Image(disk.read_bytes())
 for _,name in members:
  native=name.split(',')[0].upper().encode();kind=1 if name.endswith(',s')else 2
  assert initial.read(native,kind=kind).data==media.read(native,kind=kind).data,name
 normalize();times={str(p):p.stat().st_mtime_ns for p in (project/'build').rglob('*')if p.is_file()};invoke('package-unchanged-A',False,False)
 assert times=={str(p):p.stat().st_mtime_ns for p in (project/'build').rglob('*')if p.is_file()},'no-op rewrote a product output'
 # Demonstrate the packaging half of the timestamp defect independently.
 select(b);e.ensure(project,project,jobs,published);normalize();legacy=out/'packaging-legacy.mk'
 deps=' '.join(str(project/rel)for rel,_ in members)
 legacy.write_text(f'{disk}: {deps}\n\t{sys.executable} {project}/tools/package.py --c1541 {tool}\n')
 count=calls();log=subprocess.check_output(['make','-f',str(legacy)],text=True,stderr=subprocess.STDOUT,env=env);(out/'packaging-legacy-stale.log').write_text(log);assert calls()==count
 assert D81Image(disk.read_bytes()).read(b'SUPEREDITOR',kind=2).data!=(project/'build/editor.prg').read_bytes(),'legacy D81 unexpectedly fresh'
 invoke('package-same-second-B',False,True)
 assert all((published/(n+'.seo')).read_bytes()==(b/'build/overlays'/(n+'.seo')).read_bytes()for n in TAGS),'B five cache source bytes differ'
 select(a);normalize();invoke('package-same-second-A',True,True)
 normalize();times={str(p):p.stat().st_mtime_ns for p in (project/'build').rglob('*')if p.is_file()};invoke('package-unchanged-restored-A',False,False)
 assert times=={str(p):p.stat().st_mtime_ns for p in (project/'build').rglob('*')if p.is_file()},'restored no-op rewrote output'
 # Disk corruption at the identical mtime must repack; unrelated editor binding
 # corruption must instead refuse before c1541 and preserve the old disk.
 data=disk.read_bytes();disk.write_bytes(bytes([data[0]^1])+data[1:]);normalize();invoke('package-disk-corruption',False,True)
 bad=published/'geosrow.seo';saved=bad.read_bytes();bad.write_bytes(saved[:20]+bytes([saved[20]^1])+saved[21:]);normalize();old_disk=disk.read_bytes();count=calls()
 r=subprocess.run(['make','-f',str(mk)],capture_output=True,text=True,env=env);assert r.returncode and calls()==count and disk.read_bytes()==old_disk;(out/'package-foreign54-refusal.log').write_text(r.stdout+r.stderr);bad.write_bytes(saved);normalize();invoke('package-foreign54-recovered',False,False)
 # Real package.py deletes disk before c1541; the guard restores the prior disk
 # and manifest on failure, while leaving the old proof (which cannot authorize
 # changed inputs) untouched.
 script=project/'tools/package.py';saved=script.read_bytes();script.write_bytes(saved+b'\n# private forced packager failure\n');old_disk=disk.read_bytes();old_manifest=(project/'build/disk-manifest.json').read_bytes();old_proof=(project/'build/disk-content.json').read_bytes()
 r=subprocess.run(['make','-f',str(mk)],capture_output=True,text=True,env=dict(env,CACHE_PROBE_C1541_FAIL='1'));assert r.returncode and disk.read_bytes()==old_disk and(project/'build/disk-manifest.json').read_bytes()==old_manifest and(project/'build/disk-content.json').read_bytes()==old_proof
 (out/'package-c1541-failure-rollback.log').write_text(r.stdout+r.stderr);script.write_bytes(saved);normalize();invoke('package-failure-recovered',False,False)
 return dict(events=events,members=len(members),all_editor_capsules=54,actual_legacy_stale_D81=True,unchanged_all_product_mtimes_exact=True,c1541_failure_preserves_disk_manifest_proof=True,reconstructed_probe_metadata='Four package.py-consumed fields decoded from authentic RONE SEO header; actual regenerated malformed bytes compared against original medium.')

def run(out,a,b):
 (out/'verifier.py').write_bytes(Path(__file__).read_bytes());project=out/'project';project.mkdir()
 with zipfile.ZipFile(a/'product-sources.zip')as z:z.extractall(project)
 base=out/'input';(base/'build').mkdir(parents=True)
 helper=ROOT/'tools/probes/cache_job_rebuild/ensure.py';spec=importlib.util.spec_from_file_location('ensure',helper);e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
 epoch=int(time.time())-10
 # External tool invocation witnesses distinguish hashing/version checks from
 # real ca65/ld65 assembly. Wrappers exec the actual installed tools unchanged.
 tools=out/'tool-bin';tools.mkdir();tool_log=out/'tool-invocations.jsonl'
 for name in ('ca65','ld65','od65'):
  real=shutil.which(name);p=tools/name
  p.write_text('#!'+sys.executable+'\nimport os,sys,json\n'+
   'if sys.argv[1:] != ["-V"]:\n with open('+repr(str(tool_log))+',"a")as f:f.write(json.dumps(dict(tool='+repr(name)+',argv=sys.argv[1:]))+"\\n")\n'+
   'os.execv('+repr(real)+',['+repr(real)+',*sys.argv[1:]])\n')
  p.chmod(0o755)
 env=dict(os.environ,PATH=str(tools)+os.pathsep+os.environ['PATH'])
 def calls():return len(tool_log.read_text().splitlines())if tool_log.exists()else 0
 def select(fixture):
  for n in('editor.prg','editor.lbl','editor-report.json'):
   p=base/'build'/n;shutil.copyfile(fixture/'build'/n,p);os.utime(p,(epoch,epoch))
 def normalize(folder):
  for p in folder.rglob('*'):
   if p.is_file():os.utime(p,(epoch,epoch))
 def digest():return json.loads((base/'build/editor-report.json').read_text())['resident_binding']['digest']
 def mismatches(folder):return[n for n in TAGS if(folder/(n+'.seo')).read_bytes()[20:36].hex()!=digest()]
 # Legacy rule with the same real builder and all original prerequisite inputs.
 legacy=out/'legacy';legacy.mkdir();select(a)
 deps=' '.join(str(p)for p in [base/'build/editor.prg',base/'build/editor.lbl',base/'build/editor-report.json',*e.closure(project)])
 mk=out/'legacy.mk';mk.write_text(f'{legacy}/jobs.stamp: {deps}\n\t{sys.executable} {project}/src/cache/editor/build.py {legacy} {base}\n\ttouch $@\n')
 def make(path,override=None):return subprocess.check_output(['make','-f',str(path)],stderr=subprocess.STDOUT,text=True,env=env if override is None else override)
 make(mk);assert all((legacy/(n+'.seo')).read_bytes()==(a/'build/overlays'/(n+'.seo')).read_bytes()for n in TAGS),'first actual5 source builds differ from A fixture'
 normalize(legacy);normalize(project)
 select(b);first=make(mk);wrong_b=mismatches(legacy);assert len(wrong_b)==5
 # Actual manual repair to B, then immediate restore to A in the same second.
 subprocess.run([sys.executable,project/'src/cache/editor/build.py',legacy,base],check=True,stdout=subprocess.DEVNULL);normalize(legacy);select(a);second=make(mk);wrong_a=mismatches(legacy);assert len(wrong_a)==5
 (out/'legacy.log').write_text(first+'\n'+second)
 # The content-aware recipe is checked every make; true unchanged checks leave
 # ALL output/published mtimes unchanged and do no assembler/linker invocation.
 guarded=out/'guarded';publish=out/'published';events=[]
 gmk=out/'guarded.mk';gmk.write_text(f'.PHONY: FORCE\n{guarded}/jobs.stamp: FORCE {deps}\n\t{sys.executable} {helper} --project {project} --base {base} --out {guarded} --publish {publish}\n')
 def check(label,want):
  count=calls();start=time.monotonic();log=make(gmk);elapsed=time.monotonic()-start;(out/(label+'.log')).write_text(log);record=json.loads(log.splitlines()[-1]);assert record['rebuilt']==want,(label,record);assert not mismatches(guarded)and not mismatches(publish);invocations=calls()-count;assert(invocations>0)==want,(label,'actual tool invocation count',invocations,want);events.append(dict(label=label,tool_invocations=invocations,wall_seconds=elapsed,**record));return record
 check('initial-A',True);normalize(guarded);normalize(publish)
 times={str(p):p.stat().st_mtime_ns for d in(guarded,publish)for p in d.iterdir()if p.is_file()}
 check('unchanged-A',False);assert times=={str(p):p.stat().st_mtime_ns for d in(guarded,publish)for p in d.iterdir()if p.is_file()},'unchanged check touched outputs'
 select(b);check('same-second-B',True);normalize(guarded);normalize(publish);select(a);check('same-second-A',True)
 # Content changes survive timestamp equality, including transitive cache/api.
 p=project/'src/cache/api.inc';old=p.read_bytes();p.write_bytes(old+b'\n; private content guard regression\n');os.utime(p,(epoch,epoch));check('same-time-include-change',True);p.write_bytes(old);os.utime(p,(epoch,epoch));check('same-time-include-restore',True)
 # Missing/corrupt job outputs force repair even when the input binding agrees.
 (guarded/'inln.seo').unlink();check('missing-output',True)
 p=guarded/'page.seo';raw=p.read_bytes();p.write_bytes(raw[:-1]+bytes([raw[-1]^1]));os.utime(p,(epoch,epoch));check('corrupt-output',True)
 # Published-copy damage repairs cheaply without recompiling sealed jobs.
 p=publish/'line.seo';p.write_bytes(b'bad');record=check('published-repair',False);assert record['published']==['line.seo']
 (guarded/'jobs.stamp').unlink();assert check('missing-stamp-repair',False)['stamp_changed']
 # Interrupted/failed input verification never blesses an artifact manifest.
 old_manifest=(guarded/'content.json').read_bytes();p=base/'build/editor-report.json';old=p.read_bytes();obj=json.loads(old);obj['resident_binding']['digest']='00'*16;p.write_text(json.dumps(obj));os.utime(p,(epoch,epoch))
 bad=subprocess.run(['make','-f',str(gmk)],capture_output=True,text=True);assert bad.returncode and(guarded/'content.json').read_bytes()==old_manifest;(out/'invalid-report.log').write_text(bad.stdout+bad.stderr);p.write_bytes(old);os.utime(p,(epoch,epoch));check('recovered-unchanged-A',False)
 # Mid-build input change: candidate files may exist in a temporary output,
 # but old published family and proof remain exact, and no new proof is blessed.
 builder=project/'src/cache/editor/build.py';saved=builder.read_bytes();api=project/'src/cache/api.inc';saved_api=api.read_bytes()
 builder.write_bytes(saved+b'\nimport os\nif os.environ.get("CACHE_PROBE_MUTATE"):\n p=ROOT/"src/cache/api.inc";p.write_bytes(p.read_bytes()+b"\\n; raced input\\n")\n')
 old_family={n:e.sha(guarded/n)for n in e.ARTIFACTS};old_manifest=(guarded/'content.json').read_bytes();bad_env=dict(env,CACHE_PROBE_MUTATE='1')
 bad=subprocess.run(['make','-f',str(gmk)],capture_output=True,text=True,env=bad_env)
 assert bad.returncode and 'inputs changed while building'in bad.stderr
 assert (guarded/'content.json').read_bytes()==old_manifest and {n:e.sha(guarded/n)for n in e.ARTIFACTS}==old_family
 (out/'mid-build-input-change.log').write_text(bad.stdout+bad.stderr);builder.write_bytes(saved);api.write_bytes(saved_api)
 check('mid-build-failure-recovered-unchanged',False)
 assert all((publish/(n+'.seo')).read_bytes()==(a/'build/overlays'/(n+'.seo')).read_bytes()for n in TAGS),'final actual5 SEO source bytes differ from A fixture'
 disk_gate=packaging(out,project,a,b,e,env,epoch)
 result=dict(packaging=disk_gate,final_five_sha256={n:e.sha(publish/(n+'.seo'))for n in TAGS},status='PASS-private-content-aware-cache-jobs',make_version=subprocess.check_output(['make','--version'],text=True).splitlines()[0],source_a=str(a),source_b=str(b),same_second=epoch,legacy_stale_five_A_to_B=wrong_b,legacy_stale_five_B_to_A=wrong_a,events=events,input_closure_includes_cache_api='src/cache/api.inc'in e.identity(project,base)['source'],scope='Two actual sealed54 resident ABIs; real five-image cache builder. B is not claimed to be a Plain runtime. No app execution, shared outputs, canonical source or Git changes.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--a',type=Path,default=A);p.add_argument('--b',type=Path,default=B);x=p.parse_args();out=ROOT/'build/cache-job-rebuild'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,x.a.resolve(),x.b.resolve());print(r['status'],len(r['events']))
