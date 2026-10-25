"""Private coherent48asset convergence experiments. Never writes sharedoutputs."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
BASE=ROOT/'build/geos-incremental-editor/20261025T203233990688Z/fixture'
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
 # Firstplacement proof: move the exact existingCP publisher and checkedwarm
 # transport toR19, leaving allnormalR19range/journalops0..6 intact.
 target=project/'src/render/geos/convergent-line-candidate';target.mkdir(exist_ok=True)
 shutil.copy2(HERE/'publisher.s',target/'publisher.s')
 for name in ['edit-cache.s','edit-cache.inc']:shutil.copy2(HERE/name,project/'src/render/geos'/name)
 page=project/'src/render/geos/page.s';s=page.read_text();s=s.replace('.include "render/geos/checkpoint/publish.inc"','''gsc_publish:
 lda #7
 sta se_overlay_frame
 lda #19
 ldx #0
 jmp se_overlay_call
''');page.write_text(s)
 entry=project/'src/engine/range-entry.s';s=entry.read_text();needle='    cmp #RANGE_BEGIN';assert s.count(needle)==1;s=s.replace(needle,'    cmp #7\n    jeq se_gcl_publish\n'+needle,1);s+='\n.import se_gcl_publish\n';entry.write_text(s)
 m=project/'Makefile';s=m.read_text();a=s.index('RANGE_CODE_OBJ = ');b=s.index('\n',a);s=s[:b]+' build/convergence/publisher.o build/geos-prod/cache-warm.o'+s[b:];s+='''
build/convergence/publisher.o: src/render/geos/convergent-line-candidate/publisher.s build/geos-prod/editor-api.inc build/geos-prod/checkpoint-witness.stamp
	mkdir -p $(dir $@)
	$(CA65) -g -I build/geos-prod -I src -o $@ $<
''';m.write_text(s)
 cfg=project/'cfg/range-journal.cfg';s=cfg.read_text().replace('RODATA: load=IMAGE, type=ro;','RODATA: load=IMAGE, type=ro; GEOS_PAGE: load=IMAGE, type=ro, optional=yes;');cfg.write_text(s)
 # Filesystems may report1second mtimes; remove only the affected private
 # products so same-second edits cannot silently reuse their controlobjects.
 for relative in ['build/geos-prod/page.o','build/geos-prod/edit-cache.o','build/engine/range-entry.o','build/range-bindings.s','build/engine/range-bindings.o','build/supereditor.d81']+['build/overlays/'+n+suffix for n in ['geospage','geosdelta','rangeio']for suffix in ['.bin','.seo']]:
  (project/relative).unlink(missing_ok=True)
 make('placement','editor','build/supereditor.d81')
 assets={n:dict(bytes=len((project/'build/overlays'/(n+'.seo')).read_bytes())-36,sha256=SHA(project/'build/overlays'/(n+'.seo')))for n in names}
 assert {n:assets[n]['bytes']for n in ['geospage','geosdelta','rangeio']}==dict(geospage=3741,geosdelta=3749,rangeio=4028)
 result=dict(status='placement-built',project=str(project),base=str(base),control_sha256=control,assets=assets,resident_sha256=SHA(project/'build/editor.prg'),d81_sha256=SHA(project/'build/supereditor.d81'),scope='Private outgoingcarry64B certificates +sameheightcomplete-logical-row convergence; original fullfallback for unsupported layouts. Existing48assets/no newstate.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);p.add_argument('--out',type=Path);a=p.parse_args();out=a.out or ROOT/'build/geos-convergent-line'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);r=build(out.resolve(),a.base.resolve());print('PASS',r['project'],{k:r['assets'][k]['bytes']for k in['geospage','rangeio']})
