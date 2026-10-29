"""Private minimal authentic terminal-insert validation fix, no CR fast claim."""
from pathlib import Path
import difflib,hashlib,importlib.util,json,re,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[6]
def build(out,base=None):
 out.mkdir(parents=True);tree=out/'tree';short=[];product_mode=base is not None
 if base is None:
  shutil.copytree(ROOT/'build/grid-row-geometry-CR-budget1/tree',tree);base=ROOT/'build/grid-row-geometry-extend-empty/fixture'
 else:
  tree.mkdir()
  with zipfile.ZipFile(base/'product-sources.zip')as z:
   for n in z.namelist():
    if n.startswith(('src/','cfg/','tools/')):z.extract(n,tree)
 p=tree/'src/render/grid/caret/build.py';spec=importlib.util.spec_from_file_location('terminal_source_fix',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 if product_mode:
  # The optional current product mode must reconstruct both actual images
  # before changing source or using any generated linked witness.
  m.build(out/'control',base)
  for name in('grid','geostail'):
   assert(out/'control'/(name+'.seo')).read_bytes()==(base/'build/overlays'/(name+'.seo')).read_bytes(),('exact source control',name)
  original=(tree/'src/render/grid/paragraph/controller.inc').read_text()
  # Compacted old private tree is already12B smaller. For a fresh canonical
  # tree, use real assembler range refusal on each same-condition replacement.
  def trial():
   return subprocess.run(['ca65','-g','--bin-include-dir',str(out/'control'),'-I',str(out/'control'),'-I',str(tree/'src/render/grid/caret'),'-I',str(tree/'src/render/grid/paragraph'),'-I',str(tree/'src'),'-o',str(out/'trial.o'),str(tree/'src/render/grid/caret/caret.s')],capture_output=True).returncode
  for source in(tree/'src/render/grid/caret/caret.s',tree/'src/render/grid/paragraph/controller.inc'):
   lines=source.read_text().splitlines(True)
   for index,line in enumerate(lines):
    match=re.fullmatch(r'(\s*)j(eq|ne|cc|cs|mi|pl|vc|vs)(\s+@[A-Za-z0-9_]+.*\n)',line)
    if not match:continue
    replacement=match.group(1)+'b'+match.group(2)+match.group(3);lines[index]=replacement;source.write_text(''.join(lines))
    if trial():lines[index]=line;source.write_text(''.join(lines))
    else:short.append(dict(path=str(source.relative_to(tree)),line=index+1,before=line.strip(),after=replacement.strip()))
 else:original=(tree/'src/render/grid/paragraph/controller.inc').read_text()
 p=tree/'src/render/grid/paragraph/controller.inc';s=p.read_text()
 changes=[('@compare:\n ldx LS_COL\n cpx LS_COUNT\n bcs @row_done\n','@compare:\n ldx LS_COL\n'),('@skip:\n lda P,x\n','@skip:\n cpx LS_COUNT\n bcs @row_done\n lda P,x\n'),('@same:\n jsr se_view_peek\n','@same:\n ldx LS_COL\n cpx LS_COUNT\n bcs @row_done\n jsr se_view_peek\n')]
 for old,new in changes:assert s.count(old)==1;s=s.replace(old,new)
 p.write_text(s);(out/'controller.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='control/controller.inc',tofile='candidate/controller.inc')));m.build(out/'c33',base)
 fixture=out/'fixture';shutil.copytree(base,fixture);image=(out/'c33/grid.seo').read_bytes();(fixture/'build/overlays/grid.seo').write_bytes(image);identity=json.loads((fixture/'freeze.json').read_text());identity['assets']['grid']=hashlib.sha256(image).hexdigest();identity['private_change']='Guard-preserving local shortbranches +authenticate actual inserted terminalbyte before row_done; C33-only correctnessfix';(fixture/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 assert(out/'c33/geostail.seo').read_bytes()==(base/'build/overlays/geostail.seo').read_bytes()
 text=(out/'c33/grid.map').read_text();match=re.search(r'RODATA\s+[0-9A-F]+\s+([0-9A-F]+)',text.split('Segment list:')[1]);end=int(match.group(1),16)
 result=dict(status='BUILT',size=4096,prefont_end=hex(end),prefont_free=0xbf00-end-1,R25_unchanged=True,sha256=identity['assets']['grid'],shortbranches=short,baseline=str(base));(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return fixture,result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()if len(sys.argv)>2 else None)[1])
