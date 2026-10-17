from pathlib import Path
import subprocess,json,hashlib,shutil,os
P=Path(__file__).parent;W=P/'profile-switch-v2';W.mkdir(exist_ok=False);S=W/'source';shutil.copytree(P/'project',S,ignore=shutil.ignore_patterns('build','.zig-cache','zig-out','__pycache__','*.pyc'))
def ident(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
inputs={str(p.relative_to(S)):ident(p)for p in sorted(S.rglob('*'))if p.is_file()};(W/'INPUTS_BEFORE.json').write_text(json.dumps(inputs,indent=2)+'\n')
products=['dos64.prg','dos64.labels','dos64.map','dos64-tests.prg','dos64-tests.labels','dos64-tests.map']
def run(n,flag):
 cmd=['make','-j4','build/dos64.prg','build/dos64-tests.prg','DOS64_TRAP1='+str(flag)]
 q=subprocess.run(cmd,cwd=S,capture_output=True);(W/(n+'.stdout')).write_bytes(q.stdout);(W/(n+'.stderr')).write_bytes(q.stderr);assert q.returncode==0,(n,q.stderr.decode());return {x:ident(S/'build'/x)for x in products}
zero=run('zero-first',0)
assert zero['dos64.prg']['sha256']=='666089b57e5611a67b5d87ae84880256ef5dafb121b152e1de81b9ec1cc29064'
assert zero['dos64-tests.prg']['sha256']=='b9e9cc9e7d87176848ccf8bae49dfe4f4ff0125b3aad5a1cb874341436b78df6'
one=run('one',1);assert one['dos64.prg']!=zero['dos64.prg']
for name in ['cfg/dos64-runtime-trap.cfg','cfg/dos64-unit-runtime-trap.cfg']:(S/name).touch()
one_after=run('one-cfg-touch',1);assert one_after==one
again=run('zero-after',0);assert again==zero
for n,v in inputs.items():assert ident(S/n)==v,n
q=subprocess.run(['make','-qp','DOS64_TRAP1=1'],cwd=S,capture_output=True);assert q.returncode in(0,1);(W/'make-database.stdout').write_bytes(q.stdout)
for target,cfg in [('build/dos64.prg','cfg/dos64-runtime-trap.cfg'),('build/dos64-tests.prg','cfg/dos64-unit-runtime-trap.cfg')]:
 row=next(s for s in q.stdout.decode().splitlines()if s.startswith(target+':'));assert cfg in row.split(),row
(W/'RESULT.json').write_text(json.dumps({'passed':True,'groups':['first0_matches_public_default_runtime_and_UNIT','same_tree0to1_changes_runtime','selected_cfg_dependencies_present','cfg_touch_relinks_exact_products','same_tree1to0_reproduces_all6products','all_source_inputs_unchanged'],'source_inputs':len(inputs),'zero':zero,'one':one,'last_zero':again},indent=2)+'\n');print('six profile controls PASS',len(inputs),'source inputs')
