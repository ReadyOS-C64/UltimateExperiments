"""C33 true-CR capture across all22 rows; only TAX and short branch differ."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,importlib.util
import test_geos_fold_editor as fold
import test_grid_modes as grid
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/geos-incremental-editor/20261025T183509461736Z/fixture'
def run(out,base=BASE):
 frozen=out/'fixture';shutil.copytree(base,frozen);spec=importlib.util.spec_from_file_location('capturebuild',ROOT/'src/render/grid/capture-fix-candidate/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);seos,budget=b.build(out/'leaf',frozen);identity=json.load(open(frozen/'freeze.json'))
 assert seos['geostail']==(base/'build/overlays/geostail.seo').read_bytes(),'R25 EXACT unchanged'
 for n,seo in seos.items():(frozen/'build/overlays'/(n+'.seo')).write_bytes(seo);identity['assets'][n]=hashlib.sha256(seo).hexdigest()
 (frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n');dll=fold.retention.runner(out);grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=frozen;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=identity['names'];f=fold.Fixture(out,frozen,dll,True)
 old=json.load(open(base/'freeze.json'));grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=base;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=old['names'];g=fold.Fixture(out,base,dll,True);cases=[];defects=[]
 def ready(x):x.render();x.finish_style()
 def check(tag,typing=False):
  r=f.render();g.put('se_gc_valid',0,1);ready(g);want,attrs=grid.expected(f,f.merged())[0]
  assert not r.p&1 and f.read(0x6000,8000)==want==g.read(0x6000,8000),(tag,'bitmap')
  assert f.read(0x4000,1000)==attrs==g.read(0x4000,1000),(tag,'attributes')
  assert f.merged()==g.merged() and f.canonical()==g.canonical() and f.read(0xc600,1024)==f.shim,(tag,'source/history/shim')
  bank=f.m.read(f.s['se_reu_map']+f.get('se_gc_handle',1));h=f.reu()[bank*65536+0x1500:bank*65536+0x1600];raw=f.merged();starts=[int.from_bytes(f.read(f.s['se_v_rows']+i*3,3),'little')for i in range(22)]+[f.get('se_v_bottom')]
  expected=sum(1<<i for i in range(22)if starts[i+1]>starts[i] and raw[starts[i+1]-1]==13)
  assert int.from_bytes(h[193:196],'little')==expected,(tag,'all22 trueCR bits',hex(expected),h[193:196].hex())
  if typing:assert f.m.read(0x89ff)==1,(tag,'ordinary typing admitted')
  cases.append(dict(tag=tag,true_cr=expected,typing=typing));print('PASS',tag,flush=True)
 try:
  for width in(60,80):
   raw=grid.native_text('Alpha '+('x'*(width+4))+'\r'+('Short.\r'*5)+'Alpha '+('x'*(width+4))+'\r'+('Short.\r'*6)+'Alpha '+('x'*(width+4))+'\r'+('Short.\r'*4)+'Final EOF.')
   for x in(f,g):x.source(raw);x.command(97 if width==60 else 98);ready(x)
   # Actual old packagedcapture is retained as a witnessed defect, not a
   # golden bitmap reference for reuse: reference is forced-full below.
   bank=g.m.read(g.s['se_reu_map']+g.get('se_gc_handle',1));oldcr=g.reu()[bank*65536+0x1500+193:bank*65536+0x1500+196];defects.append(dict(width=width,old_cr=oldcr.hex()))
   check(str(width)+'-mixedcapture')
   anchors=[int.from_bytes(f.read(f.s['se_v_rows']+i*3,3),'little')for i in range(22)]
   for row in range(22):
    for x in(f,g):x.position(anchors[row]+1)
    check(str(width)+'-caret-'+str(row))
   for row in(0,7,8,15,16,21):
    for x in(f,g):x.position(anchors[row]+1);x.command(68);x.position(min(len(raw),anchors[row]+4))
    check(str(width)+'-selection-'+str(row))
    for x in(f,g):x.command(68)
   # Short rows through21 all remain below old strict BOF128 restriction.
   raw=grid.native_text(('Aaa\r'*21)+'Final EOF.')
   for row in(7,8,15,16,21):
    for x in(f,g):x.source(raw);x.command(97 if width==60 else 98);x.position(row*4+2);ready(x)
    for key in(81,20):
     for x in(f,g):x.key(key)
     check(str(width)+'-row'+str(row)+'-key'+str(key),True)
  result=dict(status='passed',budget=budget,cases=cases,old_capture_defects=defects);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close();g.close()
if __name__=='__main__':
 out=ROOT/'build/grid-capture-fix'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
