"""Isolated full-build lexical registration; never uses shared build outputs.

Static resource inputs are copied and checked against the immutable54 fixture.
Product sources/Make/tools come from its ZIP. Private project builds are real
Make builds; no editor/capsule binary is copied into the output as a candidate.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time,zipfile
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'build/cache-editor-product/20261026T075912448811Z/fixture'
SEALED=ROOT/'agentsworking/evidence/M8/20261026T080308897581Z-cache-lexical-automatic'
NAMES=['edit','tail','lex','ical','ctrl']
IDENTITIES=[(1,45),(0,36),(0,37),(1,47),(1,49)]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def command(args,project,log):
 with open(log,'w')as out:p=subprocess.run(list(map(str,args)),cwd=project,stdout=out,stderr=subprocess.STDOUT)
 assert not p.returncode,Path(log).read_text()[-5000:]

def prepare(out,base=BASE):
 out.mkdir(parents=True);project=out/'project';project.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for n in z.namelist():
   if n.endswith('/'):continue
   p=project/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
 # Fonts are immutable data inputs, not copied code. Pin every available
 # frozen generated font and the actual pack read back from the original D81.
 shutil.copytree(ROOT/'assets',project/'assets');shutil.copytree(ROOT/'config',project/'config')
 for p in(base/'fonts').iterdir():
  q=project/'assets/fonts/generated'/p.name
  if q.exists()and p.suffix=='.bin':assert sha(p)==sha(q),p.name
 sys.path.insert(0,str(ROOT/'tools'));from d81_image import D81Image
 pack=D81Image((base/'build/supereditor.d81').read_bytes()).read(b'GEOSFONTS',kind=1).data
 assert hashlib.sha256(pack).hexdigest()==sha(ROOT/'build/geos-font-catalog/font-pack.bin')
 shutil.copytree(ROOT/'build/geos-font-catalog',project/'build/geos-font-catalog')
 # Host-compiled defaults remain the exact frozen64-byte source data; preserve
 # the matching complete host output set instead of regenerating a new preset.
 shutil.copytree(ROOT/'build/editor-settings',project/'build/editor-settings')
 (project/'build/overlays').mkdir(parents=True,exist_ok=True)
 report=json.load(open(base/'build/editor-report.json'));raw=(base/'build/editor.prg').read_bytes();load=int.from_bytes(raw[:2],'little');at=report['symbols']['session_defaults']-load+2
 assert (project/'build/editor-settings/editor-defaults.bin').read_bytes()==raw[at:at+64],'host settings differ from frozen data'
 assert report['symbols']['se_presentation_default']==3
 generated=project/'build/editor-settings/presentation-defaults.inc'
 assert 'SE_PRESENTATION_DEFAULT=3'in generated.read_text()
 # Prevent source extraction timestamps from unnecessarily regenerating the
 # already-pinned resource data through unrelated external-source discovery.
 for d in ('assets','build/editor-settings','build/geos-font-catalog'):
  for p in(project/d).rglob('*'):
   if p.is_file():os.utime(p,None)
 provenance=dict(baseline=str(base),resident=sha(base/'build/editor.prg'),binding=report['resident_binding']['digest'],source_zip=sha(base/'product-sources.zip'),pack=hashlib.sha256(pack).hexdigest(),settings=sha(project/'build/editor-settings/editor-defaults.bin'))
 (out/'inputs.json').write_text(json.dumps(provenance,indent=2)+'\n');return project

def build_control(out,base=BASE):
 project=prepare(out,base)
 command(['make','-j1','editor'],project,out/'control-make.log')
 assert (project/'build/editor.prg').read_bytes()==(base/'build/editor.prg').read_bytes(),'full54 resident reassembly differs'
 names=json.load(open(base/'freeze.json'))['names'];assert len(names)==54
 differences=[]
 for n in names:
  a=project/f'build/overlays/{n}.seo';b=base/f'build/overlays/{n}.seo'
  if a.read_bytes()!=b.read_bytes():differences.append(dict(name=n,rebuilt=sha(a),frozen=sha(b),bytes=len(a.read_bytes())))
 assert not differences,differences
 result=dict(status='PASS-full54-control',resident=sha(project/'build/editor.prg'),assets={n:sha(project/f'build/overlays/{n}.seo')for n in names},all54_byte_identical=True)
 (out/'control.json').write_text(json.dumps(result,indent=2)+'\n');return project

def rebase(out,base=BASE):
 project=prepare(out,base);source=SEALED/'run/automatic';changes={}
 def write(name,data):
  p=project/name;old=sha(p)if p.exists()else None;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data if isinstance(data,bytes)else data.encode());changes[name]=dict(before=old,after=sha(p))
 def exact(name,old,new):
  text=(project/name).read_text();assert text.count(old)==1,(name,old);write(name,text.replace(old,new,1))
 # Every relevant source is checked against the actual old sealed input before
 # rebasing, rather than copying any foreign bound capsule into the project.
 with zipfile.ZipFile(SEALED/'run/fixture/product-sources.zip')as old:
  cohort=[
   'src/render/geos/semantic-lex.s','src/cache/query/query.s','src/cache/query/source.s','src/cache/query/records.s','src/cache/query/classify-entry.s','src/cache/query/fast-entry.s','src/cache/query/proof.inc','src/cache/inline/source-seed.s','src/render/geos/page.s','src/render/geos/checkpoint/cache-outgoing.inc','src/cache/arena/writer.s']
  for n in cohort:assert (project/n).read_bytes()==old.read(n),('source rebase requires review',n)
 write('src/render/geos/semantic-lex.s',(source/'strict/strict.s').read_bytes())
 for n in ('classify-entry','query','source','records'):write('src/cache/query/'+n+'.s',(source/'query'/(n+'.s')).read_bytes())
 write('src/cache/query/fast-entry.s',(source/'forward/fast-entry.s').read_bytes())
 for n in ('api.inc','proof-api.inc','proof.inc'):write('src/cache/query/'+n,(source/'query/cache/query'/n).read_bytes())
 # C35 alone uses its proven local root-error trampoline compaction. Do not
 # broadcast that size optimization to the baseline writer/other arena users.
 write('src/cache/query/open-compact.s',(source/'query/arena-open.s').read_bytes())
 write('src/cache/inline/source-seed.s',(source/'inline/source-seed.s').read_bytes())
 exact('src/cache/api.inc','BC_REBUILD_TRIED=16','BC_REBUILD_TRIED=16\nBC_LEX_ATTEMPT=128 ;PRIVATE registration profile; bit64 remains reserved')
 exact('src/render/geos/checkpoint/cache-outgoing.inc','and #($FF-BC_REBUILD_TRIED)','and #($FF-BC_REBUILD_TRIED-BC_LEX_ATTEMPT)')
 exact('src/cache/arena/writer.s','and #($FF-BC_LOST-BC_ACTIVE)','and #($FF-BC_LOST-BC_ACTIVE-BC_LEX_ATTEMPT)')
 # Rehome private API includes into the actual new project runtime namespace.
 def paths(t):
  return t.replace('cache/lexical-link-probe/api.inc','cache/lexical/link.inc').replace('cache/lexical-probe/page.inc','cache/lexical/page.inc').replace('cache/lexical-probe/api.inc','cache/lexical/api.inc')
 with zipfile.ZipFile(SEALED/'sources.zip')as z:
  for target,original in [('api.inc','src/cache/lexical-probe/api.inc'),('page.inc','src/cache/lexical-probe/page.inc'),('link.inc','src/cache/lexical-link-probe/api.inc')]:write('src/cache/lexical/'+target,paths(z.read(original).decode()))
 for tag,target in [('gateway','gateway'),('resolver','resolver'),('roles','roles'),('producer','worker'),('writer','linker')]:
  name='gateway.s'if tag=='gateway'else'worker.s'if tag=='producer'else'entry.s';text=paths((source/tag/name).read_text())
  if tag=='gateway':text=text.replace('render/geos/preview-handoff.inc','cache/lexical/handoff.inc')
  write('src/cache/lexical/'+target+'.s',text)
 write('src/cache/lexical/handoff.inc',(source/'gateway/render/geos/preview-handoff.inc').read_bytes())
 write('src/cache/lexical/build.py',Path(__file__).with_name('jobs-template.py').read_bytes())
 # Existing cache build still compiles real sources against the new resident.
 exact('src/cache/editor/build.py',"path=out/'state.s'if name=='STATE'else ROOT/'src'/name", "path=out/'state.s'if name=='STATE'else ROOT/'src'/('cache/query/open-compact.s'if tag=='inln'and name=='cache/arena/open.s'else name)")
 exact('src/editor/catalog.inc','file_catalog_end:', ''.join(f' COLD_FILE file{i},{n}\n'for i,n in zip(range(54,59),(4,4,3,4,4)))+'file_catalog_end:')
 exact('src/editor/startup.s','file53=file24+4 ;LINE: C39 retained inline SOURCE consumer','''file53=file24+4 ;LINE: C39 retained inline SOURCE consumer
file54=file15+4 ;EDIT: C45 lexical admission
file55=file37+4 ;TAIL: R36 checked lexical resolver
file56=file14   ;LEX: R37 page/roles
file57=file14+3 ;ICAL: C47 producer
file58=file39+4 ;CTRL: C49 COW linker
; Future mapped aliases XFORM/PARSE/FINISH/ROW/PAINT remain unregistered.''')
 make=(project/'Makefile').read_text()+'''
# PRIVATE lexical registration; actual new capsule builds, no substitutions.
LEXICAL_ASSETS=$(addprefix build/overlays/,$(addsuffix .seo,edit tail lex ical ctrl))
build/lexical/jobs.stamp: build/editor.prg build/editor.lbl build/editor-report.json $(wildcard src/cache/lexical/*) $(wildcard src/cache/arena/*) src/supermark/lexer.s tools/module_bindings.py tools/bindings.py tools/overlays.py
	$(PYTHON) src/cache/lexical/build.py build/lexical $(CURDIR)
	touch $@
$(LEXICAL_ASSETS): build/lexical/jobs.stamp
	cp build/lexical/$(@F) $@
EDITOR_ASSETS += $(LEXICAL_ASSETS)
editor build/supereditor.d81: $(LEXICAL_ASSETS)
build/cache-editor/jobs.stamp: src/cache/query/open-compact.s
'''
 write('Makefile',make)
 # Actual package names exactly match raw cold aliases. Generic probe assets
 # keep their independent identities and bindings in the ordinary D81 build.
 exact('tools/package.py',"'fold','sema','inln','page','line']:","'fold','sema','inln','page','line','edit','tail','lex','ical','ctrl']:")
 exact('tools/cpu_editor.py',"NAMES += ['fold','sema','inln','page','line']","NAMES += ['fold','sema','inln','page','line','edit','tail','lex','ical','ctrl']")
 (out/'source-changes.json').write_text(json.dumps(changes,indent=2)+'\n');return project

def build_candidate(out,base=BASE):
 project=rebase(out,base);command(['make','-j1','editor','build/supereditor.d81'],project,out/'candidate-make.log')
 budget=json.load(open(SEALED/'manifest.json'))['budget']
 for name,key in zip(NAMES,('gateway','resolver','roles','producer','writer')):
  raw=(project/f'build/overlays/{name}.seo').read_bytes()[36:]
  assert len(raw)==budget[key]['bytes'],('new profile fit drift',name,len(raw),budget[key]['bytes'])
  original=(SEALED/f'private-overlays/{dict(edit="lexgate45",tail="lexresolve36",lex="lexpage37",ical="lexproducer47",ctrl="lexlink49")[name]}.bin').read_bytes()
  assert raw[16:]==original[16:],('new worker changed beyond actual binding',name)
 return project

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--control',action='store_true');p.add_argument('--candidate',action='store_true');a=p.parse_args()
 project=build_control(a.out.resolve(),a.fixture.resolve())if a.control else build_candidate(a.out.resolve(),a.fixture.resolve())if a.candidate else prepare(a.out.resolve(),a.fixture.resolve());print(project)


def freeze_project(project,target,base=BASE):
 """Freeze only genuinely rebuilt product files; verify disk before CPU use."""
 project=Path(project);target=Path(target);target.mkdir(parents=True)
 names=json.load(open(base/'freeze.json'))['names']+NAMES
 (target/'build/overlays').mkdir(parents=True)
 for name in ('editor.prg','editor.lbl','editor.map','editor-report.json','editor-bindings.json','disk-manifest.json','supereditor.d81'):
  shutil.copy2(project/'build'/name,target/'build'/name)
 for name in names:shutil.copy2(project/f'build/overlays/{name}.seo',target/f'build/overlays/{name}.seo')
 shutil.copytree(base/'fonts',target/'fonts')
 (target/'build/geos-font-catalog').mkdir()
 shutil.copy2(project/'build/geos-font-catalog/font-pack.bin',target/'build/geos-font-catalog/font-pack.bin')
 files=[project/'Makefile']+[p for d in ('src','cfg','tools')for p in(project/d).rglob('*')if p.is_file()and p.suffix in('.py','.s','.inc','.cfg')]
 with zipfile.ZipFile(target/'product-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for p in sorted(files):z.write(p,p.relative_to(project))
 # Import and validate the actual shipped image, not a binary replacement seam.
 sys.path.insert(0,str(ROOT/'tools'));from d81_image import D81Image
 disk=D81Image((target/'build/supereditor.d81').read_bytes())
 assert disk.read(b'SUPEREDITOR',kind=2).data==(target/'build/editor.prg').read_bytes()
 for name in names:assert disk.read(name.upper().encode(),kind=1).data==(target/f'build/overlays/{name}.seo').read_bytes(),name
 report=json.load(open(target/'build/editor-report.json'))
 identity=dict(names=names,prg_sha256=sha(target/'build/editor.prg'),assets={n:sha(target/f'build/overlays/{n}.seo')for n in names},fonts={p.name:sha(p)for p in(target/'fonts').iterdir()},disk_sha256=sha(target/'build/supereditor.d81'),binding=report['resident_binding']['digest'],private_registration=True,base=str(base))
 (target/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n');return target,identity
