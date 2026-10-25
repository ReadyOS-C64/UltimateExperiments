"""Identical actual cold C24 query cost: released firstCP vs dualCP candidate."""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
from test_geos_semantic_checkpoint_codec import Fixture
import test_geos_heading_body_candidate as heading
geos=heading.geos;BASE=ROOT/'build/geos-incremental-editor/20261025T171440790321Z/fixture';F=0x8b40

def run(out):
 images={'original':(BASE/'build/overlays/geossema.seo').read_bytes()};budgets={}
 for name,folder in [('first','semantic-checkpoint-candidate'),('dual','semantic-previous-candidate')]:
  spec=importlib.util.spec_from_file_location('build_'+name,ROOT/'src/render/geos'/folder/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);budgets[name]=b.build(out/name,BASE);images[name]=(out/name/'seed/geossema.seo').read_bytes()
 frozen,identity=geos.freeze(out,BASE);geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out);cases=[];data=geos.native_text('prefix\r')*9400+geos.native_text('# Heading words.\rFollowing row.\rTail.');query=65817
 for name,image in images.items():
  f=Fixture(out,frozen,dll,True);f.assets['geossema']=image
  try:
   f.source(data);f.put('se_f_owner',4,1)
   for n in ['se_i_ready','se_i_count','se_n_cache_count']:f.put(n,0,1)
   f.m.load(F,bytes(192));f.m.load(F,query.to_bytes(3,'little'));reu=f.reu();canonical=f.canonical();used=steps=0;op=0
   while True:
    f.m.write(f.s['se_overlay_frame'],op);r,n=f.fast_call(f.s['se_overlay_call'],a=24,x=1);assert not r.p&1;used+=n;steps+=1
    if not f.m.read(F+21):break
    op=1;assert steps<5000
   result=dict(variant=name,instructions=used,services=steps,READS=int.from_bytes(f.read(F+164,3),'little'),event=f.read(F+5,16).hex());assert f.reu()==reu and f.canonical()==canonical and f.read(0xc600,1024)==f.shim and not f.get('se_doc_read_locks',1);cases.append(result);print('PASS',result,flush=True)
  finally:f.close()
 assert len({case['event']for case in cases})==1;r=dict(status='passed',cases=cases,dual_vs_original=cases[2]['instructions']-cases[0]['instructions'],dual_vs_first=cases[2]['instructions']-cases[1]['instructions'],budgets=budgets,scope='Same65837byte canonicalsource,query65817,actual sealed C24/R14. Includes coldadmission of different-sizeC24 and realper-slice servicecost; CPUinstructions notnativecycles. No BOF throughput improvement claim.');(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 out=ROOT/'build/geos-semantic-previous-cost'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);print(run(out))
