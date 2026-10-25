"""Real C30 root STOP/admission failures, followed by exact public repaint."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json
import test_geos_fold_editor as fold
import test_geos_semantic_editor as semantic
geos=fold.geos;ROOT=fold.ROOT

def run(out,previous):
 frozen,identity=geos.freeze(out,previous)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=fold.retention.runner(out);fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
 data=geos.native_text('Ordinary text here.\rSecond source line.\rThird source line.\rLast.');cases=[]
 for tag in ['begin-STOP','glyph64-STOP','verify4-STOP','begin-missing-C30','done-missing-R27']:
  f=fold.Fixture(out,frozen,dll,True);idx=None
  try:
   f.source(data);f.command(99);canonical=f.canonical();before=f.reu();f.audit_begin()
   assert not f.call('se_editor_render').p&1
   for count in range(5000):
    assert f.get('se_e_job',1)==11,(tag,f.debug())
    request=f.m.read(0x9135);op=f.m.read(0x9136)
    found=(request==30 and op==3)if tag.startswith('begin')else(request==30 and op==1 and f.m.read(0x8ba0)==1 and f.m.read(0x8ba1)==64)if tag.startswith('glyph')else(request==30 and op==1 and f.m.read(0x8ba0)==2 and f.m.read(0x8ba2)==4)if tag.startswith('verify')else(request==21 and op==4)
    if found:break
    assert not f.call('se_editor_service').p&1
   else:raise AssertionError((tag,'target absent'))
   if tag.endswith('STOP'):f.queued(3)
   else:
    ident,slot=(30,1)if tag.startswith('begin')else(27,0)
    idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)==slot)
    f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active']+slot,0)
   f.call('se_editor_service');f.settle(error=0 if tag.endswith('STOP')else 0x17)
   assert f.canonical()==canonical and f.merged()==data
   assert not any(f.get(n,1)for n in('se_e_job','se_e_draw_busy','se_f_owner','se_doc_read_locks','se_fs_owned'))
   if idx is not None:
    f.m.write(f.s['se_overlay_ids']+idx,ident);f.key(0x8B);f.key(0x8B)
   f.render();assert f.canonical()==canonical and f.merged()==data
   eb,ea,_,_=semantic.expected(f,data,fonts)
   assert f.read(0x6000,8000)==eb and f.read(0x4000,1000)==ea,(tag,'recovery pixels')
   assert f.read(0xc600,1024)==f.shim
   dma=f.audit_end(before,tag);after=f.reu();_,bank=f.cache();a=bank*65536
   assert before[:a]==after[:a] and before[a+64:a+0x200]==after[a+64:a+0x200] and before[a+0xea88:]==after[a+0xea88:]
   geos.png(eb,ea,out/(tag+'.png'));cases.append(dict(tag=tag,steps_to_phase=count,typed_dma_stashes=dma));print('PASS',cases[-1],flush=True)
  finally:dll.fr_end();f.close()
 result=dict(status='passed',identity=identity,cases=cases,pixels_checked=len(cases)*64000,scope='Packaged C30 real root interruption/admission recovery, canonical/history/shim, typed DMA and independent source/font pixels. CPU only.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();out=ROOT/'build/geos-typing-font-recovery'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)
