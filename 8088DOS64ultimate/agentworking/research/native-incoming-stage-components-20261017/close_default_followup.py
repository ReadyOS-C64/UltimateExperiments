from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;assert Path.cwd()==P;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-iw-default-follow');assert not Path(sys.pycache_prefix).exists()
import json,hashlib,subprocess,shutil
E=P/'closed-default-followup';E.mkdir();old=json.loads((P/'closed-incoming/INPUTS_BEFORE.json').read_text())
def info(q):return {'sha256':hashlib.sha256(q.read_bytes()).hexdigest(),'bytes':q.stat().st_size}
inputs={Path(q)for q in old}|{P/'close_default_followup.py'}|{q for q in(P/'default-expected').rglob('*')if q.is_file()}
before={str(q):info(q)for q in sorted(inputs)};assert all(before[q]==h for q,h in old.items());(E/'INPUTS_BEFORE.json').write_text(json.dumps(before,indent=2)+'\n')
for q in inputs:
 rel=q.relative_to(P)if q.is_relative_to(P)else Path('EXTERNAL')/str(q).lstrip('/');d=E/'inputs'/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,d)
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPYCACHEPREFIX=str(P/'.absent-iw-followup-cache'))
for n in ['PYTHONPATH','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']:env.pop(n,None)
r=subprocess.run([sys.executable,'-B','check_incoming_defaults.py'],cwd=P,env=env,capture_output=True);(E/'stdout').write_bytes(r.stdout);(E/'stderr').write_bytes(r.stderr);assert r.returncode==0,r.stderr.decode()
after={str(q):info(q)for q in inputs};assert after==before
for q in inputs:
 rel=q.relative_to(P)if q.is_relative_to(P)else Path('EXTERNAL')/str(q).lstrip('/');assert info(E/'inputs'/rel)==before[str(q)]
pb=json.loads((P/'closed-incoming/PRODUCTS_BEFORE.json').read_text());assert all(info(Path(q))==v for q,v in pb.items())
(E/'INPUTS_AFTER.json').write_text(json.dumps(after,indent=2)+'\n');(E/'RESULT.json').write_text(json.dumps({'passed':True,'input_source_tool_copies':len(before),'old_native_inputs_still_exact':len(old),'all47_native_products_still_exact':len(pb),'native_actual24_reused_from_closed_incoming':True,'default3_fresh_sourcebuilds':json.loads((P/'default-controls/RESULT.json').read_text())},indent=2)+'\n');print((E/'RESULT.json').read_text())
