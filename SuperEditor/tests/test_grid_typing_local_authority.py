"""Actual managed font authority for C33-owned status, checked writes only."""
from pathlib import Path
from datetime import datetime,timezone
import json,shutil
import test_geos_fold_editor as fold
import test_grid_modes as grid
ROOT=Path(__file__).resolve().parents[1]
def run(out,base):
 identity=json.load(open(base/'freeze.json'));grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=base;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=identity['names'];dll=fold.retention.runner(out);f=fold.Fixture(out,base,dll,True);cases=[]
 def setup(width):
  f.source(grid.native_text('Alpha source row\rSecond row.'));f.command(97 if width==60 else 98);f.position(3);f.render();f.finish_style()
  ident=17 if width==60 else 16;index=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)&1==0);assert f.m.read(f.s['image_slot']+index)&128;f.command(2);return index
 def unchanged_try(tag):
  before=f.canonical();reu=f.reu();pixels=f.read(0x6000,8000)+f.read(0x4000,1000);phase=f.read(0x8d00,1152);f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=33,x=1)
  assert r.a==2 and not r.p&1 and f.canonical()==before and f.reu()==reu and f.read(0x6000,8000)+f.read(0x4000,1000)==pixels and f.read(0x8d00,1152)==phase and f.get('se_f_owner',1)==0,(tag,r.a,r.p)
  cases.append(dict(tag=tag,instructions=n,readonly=True))
 def asset(index,offset,value=None):
  h=f.m.read(f.s['se_overlay_asset']+(index>>4));f.put('se_reu_logical',h,1);f.put('se_reu_offset',(index&15)*4096+offset,2);f.put('se_reu_c64',0x8080,2);f.put('se_reu_length',1,2)
  if value is None:
   assert not f.call('se_reu_copy',1).p&1;return f.m.read(0x8080)
  f.m.write(0x8080,value);assert not f.call('se_reu_copy',0).p&1
 try:
  for width in (60,80):
   index=setup(width);f.m.write(f.s['image_slot']+index,0);unchanged_try(str(width)+'-unverified-even-unchanged-payload')
   index=setup(width);old=asset(index,0xc00+8);asset(index,0xc00+8,old^1);assert not f.m.read(f.s['image_slot']+index)&128;unchanged_try(str(width)+'-checked-owner2-nativefont-corruption-clears-verified')
   # Actual root must refuse corrupted renderer before producing any frame.
   pixels=f.read(0x6000,8000)+f.read(0x4000,1000);reu=f.reu();r=f.call('se_editor_render');assert r.p&1 and f.get('se_e_error',1)==0x14 and f.read(0x6000,8000)+f.read(0x4000,1000)==pixels and f.reu()==reu
   asset(index,0xc00+8,old);f.put('se_e_error',0,1);unchanged_try(str(width)+'-repair-not-yet-reverified')
   f.render();f.finish_style();(bits,attrs),_,_,_=grid.expected(f,f.merged());assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs and f.m.read(f.s['image_slot']+index)&128
   cases.append(dict(tag=str(width)+'-actual-full-root-reverification-repair',pixels=64000,attributes=1000))
  result=dict(status='passed',cases=cases,scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();out=ROOT/'build/grid-typing-local-authority'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);print(run(out,a.fixture))
