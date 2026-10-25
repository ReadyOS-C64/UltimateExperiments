"""Exact old/new certificate compatibility, actual root fallback and sealed stages."""
from pathlib import Path
from datetime import datetime,timezone
import json,shutil,sys,importlib.util
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_fold_editor as fold
import test_geos_semantic_editor as semantic
BASE=ROOT/'build/geos-incremental-editor/20261025T161722424199Z/fixture';D=ROOT/'src/render/geos/typing-color-bound-candidate'
def build(name,out,base):
 p=D/name;s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m.build(out,base)
def run(out):
 frozen=out/'fixture';shutil.copytree(BASE,frozen);v2,budget=build('build-runtime-v2.py',out/'v2',frozen);v1,_=build('build-runtime.py',out/'v1',frozen);old={n:(frozen/'build/overlays'/(z+'.seo')).read_bytes()for n,z in [('window','window'),('worker','gtype'),('stage','type')]}
 identity=json.load(open(frozen/'freeze.json'));fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen;fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=identity['names'];dll=fold.geos.grid.runner(out);f=fold.Fixture(out,frozen,dll,True);fonts={n:(frozen/'fonts'/n).read_bytes()for n in fold.geos.GEOS_FONTS+('native8.bin',)};cases=[]
 def install(seo):
  slot,ident=seo[5:7]
  for i in range(f.s['se_overlay_capacity']):
   if f.m.read(f.s['se_overlay_ids']+i)==ident and(f.m.read(f.s['image_slot']+i)&1)==slot:f.m.write(f.s['se_overlay_ids']+i,0)
  f.m.write(f.s['se_overlay_active']+slot,0);f.m.load(f.s['se_overlay_header'],seo[:36]);f.m.load(0x5000,seo[36:]);assert not f.call('se_overlay_import').p&1
 def setup(text,needle,delta,key,images):
  data=fold.geos.native_text(text);at=data.index(fold.geos.native_text(needle))+delta;f.source(data);f.command(99);f.position(at);f.render()
  for n in ['stage','worker','window']:install(images[n])
  before=f.read(0x4000,1000);f.key(key);return data,before
 def direct(tag,expected_a,expected_c):
  can=f.canonical();reu=f.reu();bits=f.read(0x6000,8000);attrs=f.read(0x4000,1000);valid=f.m.read(0x9149);gcc=f.m.read(0xcf90);f.m.write(f.s['se_overlay_frame'],3);r,n=f.fast_call(f.s['se_overlay_call'],a=30,x=0);assert r.a==expected_a and bool(r.p&1)==expected_c,(tag,r.a,r.p)
  if expected_a or expected_c:assert f.canonical()==can and f.reu()==reu and f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs and f.m.read(0xcf90)==gcc,(tag,'read-only-decline')
  assert not f.get('se_f_owner',1)and not f.get('se_doc_read_locks',1)and f.read(0xc600,1024)==f.shim
  return dict(tag=tag,VALID=valid,result=r.a,carry=bool(r.p&1),instructions=n)
 def pixels(tag):
  eb,ea,_,_=semantic.expected(f,f.merged(),fonts);assert f.read(0x6000,8000)==eb and f.read(0x4000,1000)==ea,(tag,'independent-native-model')
 try:
  # Historical V1 mixed pair really admits the known minoritycolor mistake.
  setup('Intro.\rjjj\r- .\rTail.','jjj',2,0x14,dict(old,window=v1['window']));r=direct('historical-v1-producer-old-worker',0,False);_,ea,_,_=semantic.expected(f,f.merged(),fonts);assert f.read(0x4000,1000)[160]==0x16 and ea[160]==0x36;(out/'historical-v1-unsafe-ram.bin').write_bytes(f.read(0,65536));cases.append(dict(r,known_unsafe_demonstrated=True,actual_attr=0x16,expected_attr=0x36,attribute_cell=160))
  for tag,text,needle,delta,key,images,valid in [
   ('new-producer-old-worker','Intro.\rjjj\r- .\rTail.','jjj',2,0x14,dict(old,window=v2['window']),2),
   ('old-producer-new-worker','Alpha interiorwords omega.\rTail.','interiorwords',2,ord('X'),dict(v2,window=old['window']),1)]:
   setup(text,needle,delta,key,images);assert f.m.read(0x9149)==valid;r=direct(tag,2,False);can=f.canonical();f.render();pixels(tag);assert f.canonical()==can;cases.append(dict(r,root_fallback_exact=True))
  setup('# Heading\rPlain row having ample room\rTail.','having',2,ord('X'),v2);assert f.m.read(0x9149)==2;r=direct('matched-new-generation',0,False);pixels(r['tag']);cases.append(r)
  setup('Alpha interiorwords omega.\rTail.','interiorwords',2,ord('X'),dict(v2,stage=old['stage']));cases.append(direct('new-worker-old-stage',0x94,True))
  setup('Alpha interiorwords omega.\rTail.','interiorwords',2,ord('X'),dict(v2,stage=v1['stage']));cases.append(direct('new-worker-compatible-stage',0,False));pixels('stage-compatible')
  result=dict(status='passed',budget=budget,cases=cases,scope='HistoricalV1 counterexample retained. V2 VALID2 producer+strict2worker safely refuse both mixedgenerations beforepublication; actualrootexpandedfallback exact. Sealed incompatibleC32 refuses beforeexecution. No canonical/native changes.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 out=ROOT/'build/geos-typing-two-generation'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
