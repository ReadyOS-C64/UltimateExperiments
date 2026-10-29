"""Private bounded SP2 long-paragraph source-grid transaction actualroot gate."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,importlib.util
import test_geos_fold_editor as fold
import test_grid_modes as grid
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'build/geos-preflush-product/20261025T193429355750Z/fixture'
def run(out):
 frozen=out/'fixture';shutil.copytree(BASE,frozen);spec=importlib.util.spec_from_file_location('longbuild',ROOT/'src/render/grid/long-prose-candidate/build-long.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);seos,budget=b.build(out/'leaf',frozen);identity=json.load(open(frozen/'freeze.json'))
 for n,image in seos.items():(frozen/'build/overlays'/(n+'.seo')).write_bytes(image);identity['assets'][n]=hashlib.sha256(image).hexdigest()
 (frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n');dll=fold.retention.runner(out);grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=frozen;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=identity['names'];f=fold.Fixture(out,frozen,dll,True);cases=[]
 try:
  for width in(60,80):
   raw=grid.native_text(':::basic\r10 PRINT 1\r:::\rAlpha '+('word '*100)+'ends.\rTail.')
   at=raw.index(grid.native_text('word'))+width*2+2;f.source(raw);f.command(97 if width==60 else 98);f.position(at);f.render();f.finish_style();assert f.merged()==raw
   for key in(81,20):
    f.key(key);after=f.merged();before=f.total_instructions;loads=f.get('se_overlay_loads',2);f.render();first=f.total_instructions-before;f.finish_style();r=dict(width=width,key=key,first=first,settled=f.total_instructions-before,loads=(f.get('se_overlay_loads',2)-loads)&65535)
    (bits,attrs),_,_,_=grid.expected(f,after);actual=f.read(0x6000,8000);gotattrs=f.read(0x4000,1000);diff=[(i,a,z)for i,(a,z)in enumerate(zip(actual,bits))if a!=z];ad=[(i,a,z)for i,(a,z)in enumerate(zip(gotattrs,attrs))if a!=z];print('FRAME',r,'diff',diff[:12],'attrs',ad[:8],flush=True)
    assert not diff and not ad,(r,diff[:20],ad[:20]);assert f.merged()==after and f.read(0xc600,1024)==f.shim;cases.append(r)
  result=dict(status='passed',budget=budget,cases=cases);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure-reu.bin').write_bytes(f.reu());raise
 finally:f.close()
if __name__=='__main__':
 out=ROOT/'build/grid-long-transaction'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
