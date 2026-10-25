"""Root recovery from missing GEOS fold/tail leaves and pending-query STOP.

Uses an explicitly frozen product; only derived cache validity and catalog
availability are fault-injected. Canonical source/maps/raster are never seeded.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,zipfile
import test_geos_fold_editor as fold
from geos_fold_model import raster,preview
from geos_preview_model import FontCatalog

ROOT=fold.ROOT


def run(out,previous):
    frozen,identity=fold.geos.freeze(out,previous)
    fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen
    fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=identity['names']
    dll=fold.retention.runner(out)
    fonts={n:(frozen/'fonts'/n).read_bytes() for n in fold.geos.GEOS_FONTS+('native8.bin',)}
    data=fold.TINY;cases=[]

    def remove(f,ident,slot):
        idx=next(i for i in range(f.s['se_overlay_capacity'])
            if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)==slot)
        f.m.write(f.s['se_overlay_ids']+idx,0)
        f.m.write(f.s['se_overlay_active']+slot,0)
        return idx

    def exact(f,tag):
        before,reu,catalog=f.canonical(),f.reu(),f.catalog()
        f.audit_begin()
        try:f.render()
        finally:dll.fr_end()
        f.audit_end(reu,tag)
        folds=fold.tree(data)
        from dataclasses import replace
        folds=[replace(r,flags=1) for r in folds]
        if f.get('se_r_presentation',1):
            e=preview(data,f.read(f.s['se_editor_settings'],64),folds,catalog=FontCatalog(native=fonts['native8.bin']),top=f.get('se_v_top'))
            b,a=e.bitmap,e.attrs
        else:
            b,a,_,_=raster(data,fonts,folds,top=f.get('se_v_top'),caret=f.get('se_hot_caret'))
        matrix,colors,popup=fold.geos.grid.logical_ui(f,data)
        b,a=fold.geos.with_chrome(b,a,matrix,colors,fonts['native8.bin'],popup)
        assert f.read(0x6000,8000)==b and f.read(0x4000,1000)==a,(tag,'recovered pixels')
        assert f.canonical()==before and f.catalog()==catalog and f.merged()==data
        assert f.read(0xC600,1024)==f.shim
        fold.geos.png(b,a,out/(tag+'.png'))

    for view,action in [('source','STOP'),('source','missing-R24'),('source','missing-C21'),
                        ('navigation','STOP'),('navigation','missing-R24'),
                        ('preview','STOP'),('preview','missing-R24'),('source','missing-R25'),('source','missing-R27')]:
        tag=view+'-'+action;f=fold.Fixture(out,frozen,dll,True)
        try:
            f.source(data);f.command(99);f.command(115);f.render()
            if view=='preview':f.command(102)
            f.put('se_gc_width',0,1)
            before,reu,catalog=f.canonical(),f.reu(),f.catalog();idx=None
            if action in ('missing-R25','missing-R27'):idx=remove(f,25 if action=='missing-R25' else 27,0)
            f.audit_begin()
            if view=='navigation':f.call('se_editor_command',37)
            else:
                admitted=f.call('se_editor_render')
                assert bool(admitted.p&1)==(action=='missing-R27'),(tag,'root admission')
            if action not in ('missing-R25','missing-R27'):
                for count in range(100000):
                    if f.m.read(0xCF12)==1 and f.get('se_f_owner',1)==4:break
                    assert f.get('se_e_job',1),(tag,'job ended before pending query')
                    f.call('se_editor_service')
                else:raise AssertionError((tag,'query did not pend'))
                if action=='STOP':f.queued(3)
                else:idx=remove(f,21,1) if action=='missing-C21' else remove(f,24,0)
            # R25 remains a public probe; C22 now links its pure policy locally.
            error=0 if action in ('STOP','missing-R25') else 0x17
            f.call('se_editor_service');f.settle(error=error)
            dll.fr_end();f.audit_end(reu,tag)
            assert f.canonical()==before and f.read(0xC600,1024)==f.shim,(tag,'canonical/shim')
            assert not any(f.get(n,1) for n in ('se_f_owner','se_doc_read_locks','se_fs_owned','se_e_job','se_e_draw_busy')),(tag,'cleanup')
            if idx is not None:
                ident=25 if action=='missing-R25' else 27 if action=='missing-R27' else 21 if action=='missing-C21' else 24
                f.m.write(f.s['se_overlay_ids']+idx,ident)
            assert f.catalog()==catalog
            if error:f.key(0x8B);f.key(0x8B)
            exact(f,tag)
            cases.append(dict(tag=tag,error=error,GFQ_abandoned=f.m.read(0xCF12)))
            (out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
        except BaseException:
            (out/(tag+'-failure-ram.bin')).write_bytes(f.read(0,65536));raise
        finally:dll.fr_end();f.close()
    result=dict(status='passed',identity=identity,cases=cases,pixels_checked=len(cases)*64000,
        scope='Actual public root STOP/missing R24/R27/C21 recovery and R25-independent repaint, full canonical/rawfont pixels and exact16MiB typed derived DMA guard; CPU transport seams, no native claim.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args()
    out=ROOT/'build/geos-fold-recovery'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for folder in ('tests','tools'):
            for path in sorted((ROOT/folder).glob('*.py')):z.write(path,path.relative_to(ROOT))
    print('RUN',out,flush=True);run(out,a.fixture)
