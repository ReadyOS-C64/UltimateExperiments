"""Private coherent48asset convergence experiments. Never writes sharedoutputs."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
BASE=ROOT/'build/geos-convergent-line-editor/20261025T211148922415Z/fixture'
BOOT=ROOT/'build/checkpoint-refresh-hook/20261025T201118482734Z/project'
sys.path.insert(0,str(ROOT/'tools'))
from d81_image import D81Image
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def build(out,base=BASE):
 out.mkdir(parents=True);project=out/'project';project.mkdir()
 reference=out.parent/'GEOS20'
 if not reference.exists():reference.symlink_to(ROOT.parent.parent/'GEOS20',target_is_directory=True)
 for directory in ['assets','config','build']:shutil.copytree(BOOT/directory,project/directory)
 shutil.copytree(ROOT/'tools',project/'tools',ignore=shutil.ignore_patterns('__pycache__'))
 (project/'tests').mkdir();shutil.copy2(ROOT/'tests/test_geos_editor.py',project/'tests/test_geos_editor.py')
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(project)
 for p in(ROOT/'src').rglob('*.py'):
  q=project/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 def make(tag,*targets):
  with(out/(tag+'.log')).open('w')as log:r=subprocess.run(['make','-j4',*targets],cwd=project,stdout=log,stderr=subprocess.STDOUT)
  assert not r.returncode,(tag,str(out/(tag+'.log')))
 make('control','editor','build/supereditor.d81')
 names=json.loads((base/'freeze.json').read_text())['names'];control={}
 for relative in ['build/editor.prg']+['build/overlays/'+n+'.seo'for n in names]+['build/geos-font-catalog/font-pack.bin']:
  expected=(base/relative).read_bytes()if(base/relative).exists()else D81Image((base/'build/supereditor.d81').read_bytes()).read(b'GEOSFONTS',kind=1).data
  assert(project/relative).read_bytes()==expected,('control-not-byte-identical',relative);control[relative]=SHA(project/relative)
 assert SHA(project/'build/supereditor.d81')==SHA(base/'build/supereditor.d81')
 # Only private C21/R28 differ; current exactR19 outgoing publisher retained.
 for name in ['edit-cache.s','edit-cache.inc']:shutil.copy2(HERE/name,project/'src/render/geos'/name)
 page=project/'src/render/geos/page.s';s=page.read_text();needle='    cmp #2\n    jeq full_page\n    lda #12';assert s.count(needle)==1;s=s.replace(needle,'    cmp #2\n    jeq full_page\n    cmp #3\n    beq edit_continue\n    lda #12',1)
 needle='edit_rebase:';s=s.replace(needle,'edit_continue:\n    inc LINE\n    clc\n    lda TOP\n    adc GP_RECORD+GPR_HEIGHT\n    sta TOP\n    COPY24 GP_RECORD+GPR_NEXT,ANCHOR\n    jmp next_line\nedit_rebase:',1);page.write_text(s)
 # Filesystems may report1second mtimes; remove only the affected private
 # products so same-second edits cannot silently reuse their controlobjects.
 for relative in ['build/geos-prod/page.o','build/geos-prod/edit-cache.o','build/engine/range-entry.o','build/range-bindings.s','build/engine/range-bindings.o','build/supereditor.d81']+['build/overlays/'+n+suffix for n in ['geospage','geosdelta','rangeio']for suffix in ['.bin','.seo']]:
  (project/relative).unlink(missing_ok=True)
 make('placement','editor','build/supereditor.d81')
 assets={n:dict(bytes=len((project/'build/overlays'/(n+'.seo')).read_bytes())-36,sha256=SHA(project/'build/overlays'/(n+'.seo')))for n in names}
 assert {n:assets[n]['bytes']for n in ['geospage','geosdelta','rangeio']}==dict(geospage=3779,geosdelta=4091,rangeio=4028)
 result=dict(status='placement-built',project=str(project),base=str(base),control_sha256=control,assets=assets,resident_sha256=SHA(project/'build/editor.prg'),d81_sha256=SHA(project/'build/supereditor.d81'),scope='Private wrapped logical-paragraph same-height/rowcount convergence; actual fullcarry6 at CR/EOF, original fullfallback for unsupported geometry. Current R19 unchanged. Existing48assets/no newstate.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);p.add_argument('--out',type=Path);a=p.parse_args();out=a.out or ROOT/'build/geos-wrapped-convergence'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);r=build(out.resolve(),a.base.resolve());print('PASS',r['project'],{k:r['assets'][k]['bytes']for k in['geospage','rangeio']})
