"""C30 production wrapper: real checked font builder and parent continuation."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,subprocess
import test_geos_fold_editor as fold
ROOT=fold.ROOT

def run(out,base):
 out.mkdir(parents=True,exist_ok=True)
 # Use the same generated resident ABI as production without mutating a shared build.
 digest=(base/'build/overlays/window.seo').read_bytes()[36:52]
 api='.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$%02x'%v for v in digest)+'\n.endmacro\n';(out/'editor-api.inc').write_text(api)
 objects=[]
 sources=[('font','src/render/geos/typing-font-cache.s',[]),('loans','src/render/geos/typing-font-loans.s',[]),('measure','src/render/geos/measure.s',[]),('glyph','src/render/geos/glyph.s',[]),('assets','src/render/geos/assets.s',[]),('cache','src/render/geos/cache.s',['-D','SE_GP_CACHE_WARM_ONLY=1'])]
 def command(args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
 for name,source,flags in sources:
  obj=out/(name+'.o');command(['ca65','-g','-I',out,'-I','src','-o',obj,*flags,source]);objects.append(obj)
 command(['python3','tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'bindings.s',*objects])
 command(['ca65','-g','-o',out/'bindings.o',out/'bindings.s'])
 command(['ld65','-C','cfg/overlay-c.cfg','-o',out/'font.bin','-Ln',out/'font.lbl',*objects,out/'bindings.o'])
 command(['python3','tools/overlays.py',out/'font.bin',out/'font.seo','--slot','1','--id','30','--resident-report',base/'build/editor-report.json'])
 payload=(out/'font.bin').read_bytes();image=(out/'font.seo').read_bytes()
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=base
 names=json.loads((base/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names
 dll=fold.geos.grid.runner(out);f=fold.Fixture(out,base,dll,True)
 try:
  data=fold.geos.native_text('Plain row for font cache\rSecond plain row.')
  f.source(data);f.command(99);f.render();canonical=f.canonical();_,bank=f.raw_cache()
  f.m.load(f.s['se_overlay_header'],image[:36]);f.m.load(0x5000,image[36:]);assert not f.call('se_overlay_import').p&1
  before=f.reu()
  f.put('se_f_owner',4,1)
  def call(op):
   f.m.write(f.s['se_overlay_frame'],op);r,_=f.fast_call(f.s['se_overlay_call'],a=30,x=1);assert not r.p&1,(r.a,r.p);return r
  r=call(3);assert r.a==1 and f.read(0x9135,2)==bytes([30,1])
  steps=0
  while f.m.read(0x9135)==30:
   r=call(1);steps+=1;assert r.a==1 and steps<140
  assert steps==133 and f.read(0x9135,2)==bytes([21,4]) and f.m.read(0x8ba5)==0
  after=f.reu();a=bank*65536+0xe568;b=bank*65536+0xea88
  assert after[:a]==before[:a] and after[b:]==before[b:]
  expected=bytes((ROOT/'assets/fonts/generated/bsw9.bin').read_bytes()[c*18+y*2]for c in range(128)for y in range(9))+(ROOT/'assets/fonts/generated/bsw9-widths.bin').read_bytes()
  assert after[a:a+1280]==expected
  r=call(3);warm=0
  while f.m.read(0x9135)==30:
   r=call(1);warm+=1;assert warm<140
  assert r.a==1 and warm==5 and f.read(0x9135,2)==bytes([21,4]) and f.reu()==after
  # A corrupted reused derived glyph cache must rebuild, rather than causing
  # a permanent R30 miss on that glyph while retaining a stale READY tag.
  f.m.write(0x8080,after[a]^1);f.put('se_reu_logical',f.get('se_gc_handle',1),1)
  f.put('se_reu_offset',0xe568,2);f.put('se_reu_c64',0x8080,2);f.put('se_reu_length',1,2)
  assert not f.call('se_reu_copy',0).p&1
  r=call(3);repair=0
  while f.m.read(0x9135)==30:
   r=call(1);repair+=1;assert repair<140
  assert r.a==1 and repair==138 and f.reu()==after

  assert f.canonical()==canonical and f.merged()==data and f.read(0xc600,1024)==f.shim
  result=dict(status='passed',payload_bytes=len(payload),root_steps=steps,wholeREU=16777216,root_ready_reuse=True,warm_verify_steps=warm,corruption_repair_steps=repair,scope='Actual production C30 wrapper/private checked import on actual public page; parent requests verified, C21 op4 integration pending.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args()
 out=ROOT/'build/geos-typing-font-root'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve())
