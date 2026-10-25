"""Actual root cancellation/admission recovery during the derived edit transaction.

Only STOP and missing-catalog availability are injected. Source, row maps and
pixels come from the actual editor; no private overlay substitutions.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,zipfile
import test_geos_fold_editor as fold
import test_geos_semantic_editor as semantic
geos=fold.geos;ROOT=fold.ROOT
DEFAULT=ROOT/'build/geos-incremental-editor/20261025T081538083121Z/fixture'

def run(out,previous):
 frozen,identity=geos.freeze(out,previous)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=fold.retention.runner(out);fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
 data=geos.native_text('Ordinary text here.\rSecond source line.\rThird source line.\rLast.')
 cases=[]
 for target,action in [('source','STOP'),('rebase','STOP'),('partial-rebase','STOP'),('rebase','missing-R28'),('rebase','missing-C21'),('paint','missing-C22')]:
  f=fold.Fixture(out,frozen,dll,True);tag=target+'-'+action;idx=None
  try:
   f.source(data);f.command(99);f.position(5);f.render();f.key(geos.native_text('Q')[0]);source=f.merged();canonical=f.canonical();reu=f.reu();catalog=f.catalog();f.audit_begin()
   r=f.call('se_editor_render');assert not r.p&1
   for count in range(10000):
    assert f.get('se_e_job',1)==11,(tag,'job ended',f.debug())
    state=f.m.read(0x9134);request=f.m.read(0x9135)
    found=(state==1 and request==20 and f.m.read(0x912D))if target=='source' else(request==22)if target=='paint' else(state==12 and request==21)
    if found:break
    f.call('se_editor_service')
   else:raise AssertionError((tag,'target absent'))
   if target=='partial-rebase':f.call('se_editor_service');assert f.m.read(0x9134)==12
   if action=='STOP':f.queued(3)
   else:
    ident=28 if action=='missing-R28'else 21 if action=='missing-C21'else 22;slot=0 if ident==28 else 1
    idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)==slot)
    f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active']+slot,0)
   f.call('se_editor_service');f.settle(error=0 if action=='STOP'else 0x17)
   assert f.canonical()==canonical and f.merged()==source,(tag,'pending edit/history changed')
   assert not any(f.get(n,1)for n in('se_e_job','se_e_draw_busy','se_f_owner','se_doc_read_locks','se_fs_owned')),(tag,'cleanup',f.debug())
   assert f.read(0x8B40,2)==bytes(2) and f.m.read(0x912D)==0
   if idx is not None:f.m.write(f.s['se_overlay_ids']+idx,ident);f.key(0x8B);f.key(0x8B)
   assert f.catalog()==catalog
   f.render();assert f.canonical()==canonical and f.merged()==source
   eb,ea,_,_=semantic.expected(f,source,fonts)
   assert f.read(0x6000,8000)==eb and f.read(0x4000,1000)==ea,(tag,'recovery pixels')
   assert f.read(0xC600,1024)==f.shim
   writes=f.audit_end(reu,tag);actual=f.reu();_,bank=f.cache();cursor=0
   for a,b in[(bank*65536,bank*65536+64),(bank*65536+0x200,bank*65536+0xE568)]:
    assert actual[cursor:a]==reu[cursor:a],(tag,'undeclared REU');cursor=b
   assert actual[cursor:]==reu[cursor:],(tag,'REU tail')
   geos.png(eb,ea,out/(tag+'.png'));cases.append(dict(tag=tag,steps_to_phase=count,typed_derived_dma_stashes=writes));print('PASS',cases[-1],flush=True)
  except BaseException:(out/(tag+'-failure-ram.bin')).write_bytes(f.read(0,65536));raise
  finally:dll.fr_end();f.close()
 result=dict(status='passed',identity=identity,cases=cases,pixels_checked=len(cases)*64000,attributes_checked=len(cases)*1000,scope='Actual packaged root C6/C21/R28/C22 STOP/missing admission recovery including partial rebase, pending source/history and typed/exact16MiB guards. Independent canonicalfont pixels. CPU only, no native claim.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=DEFAULT);a=p.parse_args();out=ROOT/'build/geos-incremental-recovery'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 with zipfile.ZipFile(out/'verifier.zip','w',zipfile.ZIP_DEFLATED)as z:
  for folder in('tests','tools'):
   for path in sorted((ROOT/folder).glob('*.py')):z.write(path,path.relative_to(ROOT))
 run(out,a.fixture)
