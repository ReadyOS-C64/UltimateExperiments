from pathlib import Path
import hashlib,json,shutil,subprocess,sys
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
parent=ROOT/'agentworking/scratch/v1-final-public-producer-consumer-20261017'
work=P/'work';work.mkdir()
def digest(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
records={}
def copy(p,q):
 q.parent.mkdir(parents=True,exist_ok=True);w=digest(p);shutil.copyfile(p,q);assert digest(p)==digest(q)==w
 records[str(p)]=w;records[str(q)]=w
for name in ['config.prg','config.labels','config.map','config_fixture.py','config-peddle.dylib']:
 copy(parent/'config-real/work'/name,work/name)
for p in (parent/'setup/full-output').iterdir():
 if p.is_file():copy(p,work/'generated'/p.name)
for name in ['tools/config/existing_cfg.c','tools/config/media_reinspect.c','tools/config/config_ui.c','tools/config/config_publish.c']:
 copy(ROOT/name,work/'source'/Path(name).name)
copy(P/'test_gap.py',work/'test_gap.py')
(P/'INPUTS_BEFORE.json').write_text(json.dumps(records,indent=2)+'\n')
with (P/'test.stdout').open('wb') as o,(P/'test.stderr').open('wb') as e:
 r=subprocess.run([sys.executable,'-B','test_gap.py'],cwd=work,stdin=subprocess.DEVNULL,stdout=o,stderr=e)
assert all(digest(Path(p))==w for p,w in records.items())
(P/'INPUTS_AFTER.json').write_text(json.dumps(records,indent=2)+'\n')
assert r.returncode==0,r.returncode
print((P/'RESULT.json').read_text())
