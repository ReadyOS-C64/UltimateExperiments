"""GEOS canonical fold integration gate. Default is host preparation only.

--run requires a parent-released immutable fixture; never builds shared products.
Actual CPU fixtures use explicit SEO/font IEC seams, not native IRQ/VIC proof.
"""
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import replace, asdict
import argparse, hashlib, json, sys, zipfile, shutil
import test_geos_editor as geos
import test_fold_builder as builder
import test_fold_projection as projection
import test_fold_retention as retention
from test_folds import action_model
from geos_packet import rows as packet_rows
from geos_fold_model import rows, raster, normalize_top, selected_summary, classify, preview, navigation

ROOT=geos.ROOT
TINY=geos.native_text('plain\r:::region A\ralpha\r:::end\rmiddle\r:::basic\r10 PRINT "Hi"\r:::\rtail\r')
NESTED=geos.native_text('# Parent\rintro\r:::region A\rfirst\r:::end\rmiddle\r:::region B\rsecond\r:::end\r# Tail\rend\r')


class Fixture(geos.Fixture):
    reu=retention.Fixture.reu
    audit_begin=retention.Fixture.audit_begin
    audit_end=retention.Fixture.audit_end
    metadata=projection.Fixture.metadata
    def source(self,data):super().source(data,banks=2,physical=256)


def tree(data):
    result,_,_,error=builder.oracle(data)
    assert not error,("host fold parser",error)
    return result


def host_check():
    fonts={n:(ROOT/'assets/fonts/generated'/n).read_bytes() for n in geos.GEOS_FONTS+('native8.bin',)}
    import test_geos_semantic_editor as literal
    for raw in (TINY,NESTED,literal.INLINE_FIXTURE):
        expected=literal.body(raw,fonts,caret=0)
        actual=raster(raw,fonts,[],caret=0)
        assert actual[:2]==expected[:2],'fold-free oracle must preserve accepted literal semantics'
    folds=[replace(f,flags=1) for f in tree(TINY)]
    lines,_=rows(TINY,fonts,folds)
    assert len([r for r in lines if r.marker])==2
    for f in folds:
        r=next(r for r in lines if r.end==f.hidden-1)
        assert r.marker and r.next==f.end
        assert normalize_top(TINY,folds,f.hidden)==f.start
        assert selected_summary(f.hidden,f.end,r.end,r.next)
        assert selected_summary(f.end,f.hidden,r.end,r.next)
        assert not selected_summary(f.start,r.end,r.end,r.next)
        assert not selected_summary(f.end,f.end+1,r.end,r.next)
        assert not selected_summary(r.end,r.end,r.end,r.next)
    # Parsing projected bytes would lose the BASIC closing delimiter. The
    # full canonical model must leave the following tail in prose9 geometry.
    _,_,_,code=classify(TINY)
    assert code[TINY.index(geos.native_text('10 PRINT'))]
    assert not code[TINY.index(geos.native_text('tail'))]
    nested=[replace(f,flags=1) for f in tree(NESTED)]
    lines,_=rows(NESTED,fonts,nested)
    assert sum(r.marker for r in lines)==2,"ancestor suppresses both child summaries"
    assert normalize_top(NESTED,nested,nested[1].hidden)==nested[0].start
    # Exact320 ends FULL before CR: inverse plus gets the genuine next row.
    exact=geos.native_text(':::region ')+b'.'*150+geos.native_text('\rbody\r:::end\rtail')
    widths=fonts['bsw9-widths.bin'];prefix=sum(widths[geos.native(v)] for v in geos.native_text(':::region '))
    exact=geos.native_text(':::region ')+b'.'*((320-prefix)//widths[geos.native(46)])+geos.native_text('\rbody\r:::end\rtail')
    es=[replace(f,flags=1) for f in tree(exact)];er,_=rows(exact,fonts,es)
    assert sum(r.marker for r in er)==1
    # Signed left partial marker and marker/caret union remain bounded.
    f=folds[0];full=raster(TINY,fonts,folds,caret=f.hidden-1,anchor=f.end)
    for pan in (1,5,9,319,324):
        b,a,_,_=raster(TINY,fonts,folds,caret=f.hidden-1,anchor=f.end,nowrap=True,pan=pan)
        assert len(b)==8000 and len(a)==1000
    high=b'X'*65540+geos.native_text('\r:::region High\rhidden\r:::end\rafter\r')
    hs=[replace(f,flags=1) for f in tree(high)];hr,_=rows(high,fonts,hs,top=hs[0].start)
    assert hs[0].start>65535 and hr[0].next==hs[0].end
    from geos_preview_model import render,FontCatalog
    defaults=b'SEST'+bytes((1,64,8,7))+b''.join(bytes((0,int(i==7),0,8 if i==7 else 9,7 if 1<=i<=6 else 1,6,0)) for i in range(8))
    catalog=FontCatalog(native=fonts['native8.bin'])
    raw=render(TINY,defaults,catalog=catalog);plain=preview(TINY,defaults,[],catalog=catalog)
    assert (plain.bitmap,plain.attrs,plain.bottom,plain.anchors)==(raw.bitmap,raw.attrs,raw.bottom,raw.anchors)
    formatted=preview(TINY,defaults,folds,catalog=catalog)
    assert formatted.bottom==len(TINY)
    assert all(not any(f.hidden<=at<f.end for f in folds) for r in formatted.rows for at in r.glyph_sources)
    terminal=geos.native_text(':::region Last\rhidden\r:::end\r')
    terminal_tree=[replace(f,flags=1) for f in tree(terminal)]
    terminal_view=preview(terminal,defaults,terminal_tree,catalog=catalog)
    assert terminal_view.bottom==len(terminal) and len(terminal_view.rows)==1
    return dict(status='host-prepared',source_bytes=len(TINY),summaries=2,
        nested_outer_summaries=2,high_anchor=hs[0].start,
        bitmap_sha256=hashlib.sha256(full[0]).hexdigest(),
        scope='Canonical/full-source host oracle only; no integrated product run.')


def run(out,previous,smoke=False,preview_gate=False):
    frozen,identity=geos.freeze(out,previous)
    if preview_gate and not (frozen/'genuine').exists():
        shutil.copytree(ROOT/'build/geos-font-catalog',frozen/'genuine')
    verification=[Path(__file__),ROOT/'tools/geos_fold_model.py',ROOT/'tools/geos_preview_model.py',
        ROOT/'tools/supermark_model.py',ROOT/'tests/test_geos_editor.py',ROOT/'tests/geos_packet.py',
        ROOT/'tests/test_fold_builder.py',ROOT/'tests/test_folds.py',ROOT/'tests/test_fold_retention.py',
        ROOT/'tests/test_fold_transform.py',ROOT/'tests/test_fold_projection.py',ROOT/'tests/test_grid_modes.py',
        ROOT/'tools/editor_fixture.py',ROOT/'tools/cpu_editor.py',ROOT/'tools/font_fixture.py']
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in verification}
    with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in verification:archive.write(path,path.relative_to(ROOT))
    geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
    geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
    fonts={n:(frozen/'fonts'/n).read_bytes() for n in geos.GEOS_FONTS+('native8.bin',)}
    dll=retention.runner(out);f=Fixture(out,frozen,dll,True);frames=[]
    def check(data,folds,tag,rebuild=False):
        before,reu,catalog=f.canonical(),f.reu(),f.catalog()
        metadata=None if rebuild else f.metadata();f.audit_begin()
        try:f.render()
        finally:f.dll.fr_end()
        writes=f.audit_end(reu,tag)
        assert f.get('se_mode',1)==3 and not f.get('se_r_presentation',1),(tag,'literal GEOS mode')
        bits,attrs,expected,sem=raster(data,fonts,folds,top=f.get('se_v_top'),
            caret=f.get('se_hot_caret'),anchor=f.get('se_sel_anchor') if f.get('se_sel_mark',1) else None,
            nowrap=bool(f.get('se_l_mode',1)),pan=f.get('se_l_pan'))
        matrix,colors,popup=geos.grid.logical_ui(f,data)
        bits,attrs=geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],popup)
        actualbits,actualattrs=f.read(0x6000,8000),f.read(0x4000,1000)
        cache,_=f.raw_cache();actual=packet_rows(cache)
        assert cache[0]==1 and len(actual)==len(expected),(tag,'published row count',len(actual),len(expected))
        for i,(a,e) in enumerate(zip(actual,expected)):
            assert (a['start'],a['end'],a['next'])==(e.start,e.end,e.next),(tag,'canonical projection',i,a,e)
            assert (a['top'],a['height'],a['reason'])==(e.top,e.height,e.reason),(tag,'mixed geometry',i,a,e)
            assert bool(a['prefix'][22]&128)==e.marker,(tag,'summary flag',i,a,e)
        if actualbits!=bits or actualattrs!=attrs:
            (out/(tag+'-actual.bin')).write_bytes(actualbits+actualattrs)
            (out/(tag+'-expected.bin')).write_bytes(bits+attrs)
            geos.png(actualbits,actualattrs,out/(tag+'-actual.png'));geos.png(bits,attrs,out/(tag+'-expected.png'))
            raise AssertionError((tag,'pixels/attrs',[(i,a,b)for i,(a,b)in enumerate(zip(actualbits,bits))if a!=b][:12],[(i,a,b)for i,(a,b)in enumerate(zip(actualattrs,attrs))if a!=b][:12]))
        assert f.canonical()==before and f.catalog()==catalog and f.merged()==data,(tag,'source/caret/history/clipboard changed')
        actualmeta=f.metadata();wantedmeta=b''.join(x.bytes() for x in folds)
        assert actualmeta==wantedmeta and (rebuild or metadata==actualmeta),(tag,'fold records changed',actualmeta.hex(),wantedmeta.hex())
        assert f.read(0xC600,1024)==f.shim
        assert not any(f.get(n,1) for n in ('se_f_owner','se_doc_read_locks','se_fs_owned','se_e_job')),(tag,'lease/job cleanup')
        geos.png(actualbits,actualattrs,out/(tag+'.png'))
        frames.append(dict(tag=tag,source_bytes=len(data),rows=[asdict(r) for r in expected],derived_dma_writes=writes))
        (out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
    def load(data):
        f.source(data);f.command(99);f.command(115)
        folds,_=action_model(tree(data),3,0,0,f.get('se_ef_motion',4),0)
        return folds
    def move(data,at):
        line=data[:at].count(b'\r')+1;column=at-(data.rfind(b'\r',0,at)+1)
        f.typed(geos.native_text(f'goto {line}'))
        for _ in range(column):f.command(2)
        assert f.get('se_hot_caret')==at,('canonical public GOTO',at,f.get('se_hot_caret'))
    def object_bytes(token,length):
        output=bytearray()
        for at in range(0,length,1024):
            count=min(1024,length-at);f.m.load(f.s['se_object_id'],token)
            f.put('se_object_offset',at);f.put('se_object_length',count,2);f.put('se_object_c64',0x8000,2)
            assert not f.call('se_object_copy',1).p&1
            output+=f.read(0x8000,count)
        return bytes(output)
    try:
        folds=load(TINY);check(TINY,folds,'tiny-collapse-all')
        if not smoke:
            region=folds[0]
            for tag,anchor,caret,mark in [('hidden-only',region.hidden+1,region.end,1),('reverse-full',region.end,region.start,1),('end-exact-CR',region.start,region.hidden-1,1),('start-exact-END',region.end,region.end+1,1),('zero-mark',region.end,region.end,1),('unmarked',region.hidden+1,region.end,0),('caret-marker-selected',region.end,region.hidden-1,1)]:
                f.position(caret);f.put('se_sel_anchor',anchor);f.put('se_sel_mark',mark,1);check(TINY,folds,tag)
            f.put('se_sel_mark',0,1);f.command(116)
            expanded,_=action_model(folds,4,0,f.get('se_hot_caret'),f.get('se_ef_motion',4),0)
            check(TINY,expanded,'expand-all')
            folds=load(NESTED);check(NESTED,folds,'nested-ancestor-collapsed')
            f.command(114);folds,_=action_model(folds,2,0,0,f.get('se_ef_motion',4),0)
            check(NESTED,folds,'nested-parent-open-children-retained')
            # A real canonical GOTO into hidden text must reveal ancestors;
            # this is distinct from invalid direct W_LOAD of a hidden caret.
            folds=load(TINY);query=folds[0].hidden+1;move(TINY,query)
            folds,_=action_model(folds,5,0,query,f.get('se_ef_motion',4),query)
            check(TINY,folds,'public-GOTO-reveals-hidden-ancestor',True)
            # Actual canonical clipboard selection includes bytes omitted from
            # the visible page; copy/cut/undo must never copy a projection.
            folds=load(TINY);region=folds[0];move(TINY,region.start);f.command(68);move(TINY,region.end)
            f.command(69);expected_clip=TINY[region.start:region.end]
            assert f.get('se_clip_length')==len(expected_clip)
            assert object_bytes(f.read(f.s['se_clip_token'],5),len(expected_clip))==expected_clip
            check(TINY,folds,'canonical-copy-includes-hidden')
            f.command(70);changed,remaining=retention.retained(folds,TINY,region.start,len(expected_clip),b'')
            assert f.merged()==changed;check(changed,remaining,'cut-canonical-hidden-range',True)
            f.command(16);assert f.merged()==TINY
            # Undo reparses current canonical source; deleted opener's old
            # hint is gone, while untouched BASIC retains its collapse.
            changed,restored=retention.retained(remaining,changed,region.start,0,expected_clip)
            assert changed==TINY;check(TINY,restored,'undo-cut-exact-source',True)
            # Edits on visible source are pending RAM changes, not a forced
            # document publication. Both disjoint folds retain their flags.
            folds=load(TINY);move(TINY,0);raw=geos.native_text('Q');f.key(raw[0])
            changed,folds=retention.retained(folds,TINY,0,0,raw)
            assert f.get('se_hot_pending',1);check(changed,folds,'outside-pending-retains',True)
            f.command(1);assert not f.get('se_hot_pending',1)
            check(changed,folds,'known-flush-retains')
            p=changed.index(geos.native_text('region A'))+len(geos.native_text('region '));move(changed,p);f.key(geos.native_text('X')[0])
            changed,folds=retention.retained(folds,changed,p,0,geos.native_text('X'))
            check(changed,folds,'changed-opener-drops-only-own-hint',True)
            # Projected UP/DOWN must not land in the canonical hidden interval.
            folds=load(TINY);move(TINY,folds[0].start);preferred=None
            for command in (37,37,36,36,39,38):
                before=f.get('se_hot_caret');target,preferred,_,_=navigation(TINY,fonts,folds,before,command,preferred)
                f.command(command);assert f.get('se_hot_caret')==target,('projected navigation',command,before,target,f.get('se_hot_caret'))
                check(TINY,folds,f'projected-nav-{command}-{len(frames)}')
            for count in (38,150,170):
                long=geos.native_text(':::region ')+b'X'*count+geos.native_text('\rhidden\r:::end\rtail\r')
                folds=load(long);check(long,folds,f'wrapped-opener-{count}')
            high=b'X'*65540+geos.native_text('\r:::region High\rhidden\r:::end\rafter\r')
            folds=load(high);move(high,folds[0].start);check(high,folds,'summary-above64KiB')
        if preview_gate:
            from geos_preview_model import FontCatalog
            catalog=FontCatalog(frozen/'genuine/catalog.json',native=fonts['native8.bin'])
            folds=load(TINY);before=f.canonical();reu=f.reu();assets=f.catalog()
            f.command(102);f.render()
            assert f.get('se_r_presentation',1)==1 and f.get('se_e_ui',1)==4
            expected=preview(TINY,f.read(f.s['se_editor_settings'],64),folds,catalog=catalog,top=f.get('se_v_top'))
            matrix,colors,popup=geos.grid.logical_ui(f,TINY);assert popup is None
            bits,attrs=geos.with_chrome(expected.bitmap,expected.attrs,matrix,colors,fonts['native8.bin'])
            (out/'preview-actual.bin').write_bytes(f.read(0x6000,8000)+f.read(0x4000,1000))
            (out/'preview-expected.bin').write_bytes(bits+attrs)
            geos.png(f.read(0x6000,8000),f.read(0x4000,1000),out/'preview-actual.png');geos.png(bits,attrs,out/'preview-expected.png')
            (out/'preview-expected.json').write_text(json.dumps(dict(bottom=expected.bottom,rows=[asdict(r) for r in expected.rows]),indent=2)+'\n')
            assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,'preview-fold pixels/attrs'
            assert f.canonical()==before and f.reu()==reu and f.catalog()==assets,'preview changed canonical/REU'
            geos.png(bits,attrs,out/'preview-collapsed.png')
            frames.append(dict(tag='preview-collapsed',source_bytes=len(TINY),rows=[asdict(r) for r in expected.rows]))
        result=dict(status='passed',identity=identity,frames=frames,checked_reu_bytes=16*1024*1024,
            source_hashes=source_hashes,
            scope='Actual root literal GEOS fold rendering/cache/selection, canonical metadata/source/history, typed FE/46 DMA and full16MiB/shim guards. CPU transport seams; no native claim.',preview_fold_gate=preview_gate)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    except BaseException as error:
        (out/'failure-ram.bin').write_bytes(f.read(0,65536))
        (out/'failure-reu.bin').write_bytes(f.reu())
        fields={n:f.get(n,w) for n,w in [('se_e_error',1),('se_e_job',1),('se_f_owner',1),('se_ef_active',1),('se_ef_operation',1),('se_fs_owned',1),('se_doc_read_locks',1),('se_hot_caret',3),('se_v_top',3)]}
        (out/'failure-state.json').write_text(json.dumps(fields,indent=2)+'\n')
        (out/'failure.json').write_text(json.dumps(dict(error=repr(error),frames=frames),indent=2)+'\n');raise
    finally:f.close()


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--model-check',action='store_true');p.add_argument('--smoke',action='store_true');p.add_argument('--preview',action='store_true');p.add_argument('--fixture',type=Path);args=p.parse_args()
    if args.model_check:print(json.dumps(host_check(),indent=2));return
    if not args.run:print('Prepared GEOS fold gate. Await parent build-ready; --run --fixture IMMUTABLE --smoke.');return
    assert args.fixture,'Explicit parent-released immutable fixture required'
    out=ROOT/'build/geos-fold-editor'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    print('RUN '+str(out),flush=True);run(out,args.fixture,args.smoke,args.preview)


if __name__=='__main__':main()
