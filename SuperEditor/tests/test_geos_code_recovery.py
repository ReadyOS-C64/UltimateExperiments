"""Actual public R31-root failures, recovery pixels and subsequent Undo.

Only asset availability/content is faulted. The packaged editor performs the
edit and render; no worker substitution, row-map injection or native claim.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ctypes as C, json
import test_geos_semantic_editor as semantic
geos=semantic.geos
ROOT=geos.ROOT

class Fixture(geos.Fixture):
 def reu(self):
  data=C.create_string_buffer(16*1024*1024)
  self.dll.gm_reu(self.m.handle,len(data),data)
  return data.raw

def run(out,previous,styles=False):
 frozen,identity=geos.freeze(out,previous)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out)
 fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
 data=geos.native_text('Intro\rAlpha **interiorwords** tail.\rSecond plain row\rTail.' if styles else 'Intro\r:::basic\r10 PRINT "HELLO"\rSecond code row\r:::\rTail.')
 worker_id,capsule_id=(30,32) if styles else (31,31)
 word='interiorwords' if styles else 'HELLO'
 results=[]
 for tag,error in [(f'missing-R{worker_id}',0x17),(f'missing-C{capsule_id}',0x17),(f'binding-C{capsule_id}',0x11),(f'payload-C{capsule_id}',0x94)]:
  f=Fixture(out,frozen,dll,True)
  try:
   f.source(data);f.command(99);f.position(data.index(geos.native_text(word))+2);f.render()
   f.key(geos.native_text('Q')[0]);edited=f.merged();canonical=f.canonical()
   slot=0 if tag==f'missing-R{worker_id}'else 1
   ident=worker_id if slot==0 else capsule_id
   idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)&1==slot)
   original_id=f.m.read(f.s['se_overlay_ids']+idx)
   handle=f.m.read(f.s['se_overlay_asset']+(idx>>4))
   physical=f.m.read(f.s['se_reu_map']+handle)
   offset=((idx&15)*4096)+(32 if tag==f'payload-C{capsule_id}'else 0)
   saved=f.reu()[physical*65536+offset]
   def patch(value):
    f.m.write(0x8000,value)
    for name,value,width in [('se_reu_logical',handle,1),('se_reu_offset',offset,2),('se_reu_length',1,2),('se_reu_c64',0x8000,2)]:f.put(name,value,width)
    r=f.call('se_reu_copy',0);assert not r.p&1
   if tag.startswith('missing'):f.m.write(f.s['se_overlay_ids']+idx,0)
   else:patch(saved^1)
   f.m.write(f.s['se_overlay_active'],0)
   before=f.reu();f.call('se_editor_render')
   assert f.get('se_e_error',1)==error,(tag,f.debug())
   assert f.canonical()==canonical and f.merged()==edited,(tag,'source/history')
   assert f.reu()==before,(tag,'failed admission wrote REU')
   assert all(f.get(n,1)==0 for n in ('se_f_owner','se_doc_read_locks','se_fs_owned','se_e_job','se_e_draw_busy')),(tag,'cleanup')
   if tag.startswith('missing'):f.m.write(f.s['se_overlay_ids']+idx,original_id)
   else:patch(saved)
   f.put('se_e_error',0,1);f.render()
   eb,ea,_,_=semantic.expected(f,edited,fonts)
   assert f.read(0x6000,8000)==eb and f.read(0x4000,1000)==ea,(tag,'recovery pixels')
   assert f.canonical()==canonical and f.merged()==edited and f.read(0xC600,1024)==f.shim
   f.command(16);assert f.merged()==data,(tag,'continued Undo')
   f.render();eb,ea,_,_=semantic.expected(f,data,fonts)
   assert f.read(0x6000,8000)==eb and f.read(0x4000,1000)==ea,(tag,'Undo pixels')
   geos.png(eb,ea,out/(tag+'.png'))
   results.append(dict(case=tag,error=error,admission_REU_unchanged=True,recovered_pixels=True,continued_Undo=True))
   print('PASS',results[-1],flush=True)
  except BaseException:
   (out/(tag+'-failure-ram.bin')).write_bytes(f.read(0,65536));raise
  finally:f.close()
 result=dict(status='passed',identity=identity,cases=results,pixels_checked=len(results)*2*64000,scope=f'Actual packaged root/C6/R{worker_id}/C{capsule_id} missing/stale executable admission and continued editor/Undo. Full16MiB unchanged on failure; modeled ROM seams, CPU only.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--styles',action='store_true');a=p.parse_args()
 out=ROOT/'build/geos-code-recovery'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
 print('RUN',out,flush=True);run(out,a.fixture,a.styles)
