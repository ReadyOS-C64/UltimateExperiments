"""Private ASM-only lexer fix in actual C25, baseline root/C23 unchanged."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,inspect,zipfile
import test_geos_fold_editor as fold
import test_geos_semantic_lex as worker
import test_geos_semantic_editor as semantic
import test_grid_modes as grid
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/geos-incremental-editor/20261025T183509461736Z/fixture'
SOURCE=ROOT/'src/supermark/asm-word-candidate/lexer.s'
def run(out,base=BASE):
 out.mkdir(parents=True,exist_ok=True);frozen=out/'fixture';shutil.copytree(base,frozen);old,json_identity=worker.build(out/'baseline-leaf',base),json.load(open(base/'freeze.json'));assert old[0]==(base/'build/overlays/geoslex.seo').read_bytes(),'baseline currentC25 must byte-match immutablefixture'
 src=inspect.getsource(worker.build);needle="('lexer','src/supermark/lexer.s')";assert src.count(needle)==1;namespace=dict(worker.__dict__,SOURCE=SOURCE);exec(compile(src.replace(needle,"('lexer',str(SOURCE))"),str(Path(__file__))+':newlexer-only','exec'),namespace);image,labels=namespace['build'](out/'candidate-leaf',base);(frozen/'build/overlays/geoslex.seo').write_bytes(image);identity=json_identity.copy();identity['assets']=dict(identity['assets']);identity['assets']['geoslex']=hashlib.sha256(image).hexdigest();(frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n');assert len(image)-36<=4096
 dll=fold.retention.runner(out);grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=frozen;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=identity['names'];f=fold.Fixture(out,frozen,dll,True);grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=base;g=fold.Fixture(out,base,dll,True);fonts={n:(base/'fonts'/n).read_bytes()for n in fold.geos.GEOS_FONTS+('native8.bin',)};cases=[]
 def full(x):x.put('se_gc_valid',0,1);x.m.write(0xcf90,0);x.m.write(0xcfe8,0);x.render()
 def check(tag,raw,pending=False):
  before=f.canonical();reu=f.reu();full(f);full(g);want,attrs,_,_=semantic.expected(f,raw,fonts);actual=f.read(0x4000,1000);prior=g.read(0x4000,1000)
  assert f.merged()==g.merged()==raw and f.canonical()==before and f.read(0xc600,1024)==f.shim
  assert f.read(0x6000,8000)==want==g.read(0x6000,8000),(tag,'bitmap must notchange')
  assert actual==attrs,(tag,'actualC25 exactASM word pixels/attributes')
  differences=[i for i,(a,b)in enumerate(zip(prior,attrs))if a!=b];assert differences,(tag,'baseline must reproduce existing suffix defect')
  bank=f.m.read(f.s['se_reu_map']+f.get('se_gc_handle',1));now=f.reu();start=bank*65536;assert now[:start]==reu[:start]and now[start+65536:]==reu[start+65536:],(tag,'wholeforeign16MiB')
  assert bool(f.get('se_hot_pending',1))==pending
  fold.geos.png(want,attrs,out/(tag+'.png'));cases.append(dict(tag=tag,source=raw.hex(),baseline_differences=[dict(cell=i,actual=prior[i],expected=attrs[i])for i in differences],pending=pending));print('PASS',tag,cases[-1]['baseline_differences'],flush=True)
 try:
  for word in('ldaQ','ldxQ','sta0','adcQ'):
   raw=grid.native_text(':::asm\r'+word+' #1\r:::\rTail.')
   for x in(f,g):x.source(raw);x.command(99);x.position(7)
   check(word+'-full',raw)
  raw=grid.native_text(':::asm\rlda\r:::\rTail.')
  for x in(f,g):x.source(raw);x.command(99);x.position(10);x.render();x.key(81)
  check('pending-lda-to-ldaQ',raw[:10]+b'Q'+raw[10:],True)
  result=dict(status='passed',cases=cases,baseline_payload=len(old[0])-36,candidate_payload=len(image)-36,baseline_C23_sha256=hashlib.sha256((base/'build/overlays/geosnav.seo').read_bytes()).hexdigest()if(base/'build/overlays/geosnav.seo').exists()else'unchanged catalog',scope='OnlyC25 image replaced. Allroot/C23/C31/sourceunchanged; explicit derivedcache invalidation forcesactualfullC25. Actual pending edit proves baseline defect independentof anynewC23 checkpoint.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close();g.close()
if __name__=='__main__':
 out=ROOT/'build/asm-word-editor-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out)
