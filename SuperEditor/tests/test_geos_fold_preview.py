"""Formatted fold boundary/font gates on an explicitly frozen product.

Appearance bytes are validated fixture inputs; real settings UI has a separate
gate. SEO/font IEC transport is substituted, never parser/maps/raster output.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, shutil, zipfile
import test_geos_fold_editor as fold
from geos_fold_model import preview
from geos_preview_model import FontCatalog
import editor_settings as settings

ROOT=fold.ROOT


def run(out, previous):
    frozen,identity=fold.geos.freeze(out,previous)
    shutil.copytree(ROOT/'build/geos-font-catalog',frozen/'genuine')
    fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen
    fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=identity['names']
    dll=fold.retention.runner(out);f=fold.Fixture(out,frozen,dll,True)
    native=(frozen/'fonts/native8.bin').read_bytes()
    fonts=FontCatalog(frozen/'genuine/catalog.json',native=native)
    defaults=f.read(f.s['session_defaults'],64)
    frames=[]

    def appearance(**profiles):
        s=settings.SessionSettings(defaults)
        for name,values in profiles.items():s.update(name,**values)
        return s.active

    mono=dict(origin=0,family=1,size=8,styles=0,foreground=1,background=6)
    uniform=appearance(**{name:mono for name in settings.PROFILES})

    def check(tag,data,tree,active,before,reu,catalog):
        f.render()
        expected=preview(data,active,tree,catalog=fonts,top=f.get('se_v_top'))
        ui,colors,popup=fold.geos.grid.logical_ui(f,data)
        assert popup is None
        bits,attrs=fold.geos.with_chrome(expected.bitmap,expected.attrs,ui,colors,native)
        actual=f.read(0x6000,8000),f.read(0x4000,1000)
        if actual!=(bits,attrs):
            (out/(tag+'-actual.bin')).write_bytes(actual[0]+actual[1])
            (out/(tag+'-expected.bin')).write_bytes(bits+attrs)
            fold.geos.png(*actual,out/(tag+'-actual.png'))
            fold.geos.png(bits,attrs,out/(tag+'-expected.png'))
            raise AssertionError((tag,'pixels/attributes'))
        assert f.get('se_v_bottom')==expected.bottom,(tag,'bottom',f.get('se_v_bottom'),expected.bottom)
        assert [int.from_bytes(f.read(f.s['se_v_rows']+3*i,3),'little') for i in range(len(expected.anchors))]==list(expected.anchors),(tag,'anchors')
        assert f.canonical()==before and f.reu()==reu and f.catalog()==catalog,(tag,'canonical/REU/catalog')
        assert f.metadata()==b''.join(r.bytes() for r in tree),(tag,'fold publication')
        assert f.merged()==data and f.read(0xC600,1024)==f.shim
        assert f.read(f.s['se_editor_settings'],64)==active
        fold.geos.png(bits,attrs,out/(tag+'.png'))
        frames.append(dict(tag=tag,top=f.get('se_v_top'),bottom=expected.bottom,anchors=list(expected.anchors),
            bitmap_sha256=hashlib.sha256(bits).hexdigest(),settings=active.hex()))
        (out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
        return expected

    def load(raw,active=defaults):
        data=fold.geos.native_text(raw)
        f.source(data);f.command(99);f.command(115);f.render()
        tree,_=fold.action_model(fold.tree(data),3,0,0,f.get('se_ef_motion',4),0)
        f.m.load(f.s['se_editor_settings'],active)
        before,reu,catalog=f.canonical(),f.reu(),f.catalog()
        f.command(102)
        return data,tree,active,before,reu,catalog

    try:
        # Exactly320px body: the virtual plus alone wraps, at its real CR.
        for count in (39,40,41,170):
            context=load(':::region '+'X'*count+'\rhidden\r:::end\rafter\r',uniform)
            result=check('marker-width-'+str(count),*context)
            assert len(result.rows)==(3 if count<40 else 4 if count<80 else 7)
        # Last visible row fits the title but not its plus. Bottom must remain
        # openerCR, then F5 shows the marker, skips the hidden body, and F3 returns.
        context=load(''.join('line\r' for _ in range(21))+':::region '+'X'*40+'\rhidden\r:::end\rafter\r',uniform)
        first=check('marker-at-page-edge',*context)
        cr=context[1][0].hidden-1
        assert first.bottom==cr,('marker should be deferred at its canonical CR',first.bottom,cr)
        f.key(0x87);assert f.get('se_v_top')==cr
        second=check('marker-on-next-page',*context)
        assert second.bottom==len(context[0])
        f.key(0x86);assert f.get('se_v_top')==0
        check('marker-page-back',*context)
        # Real GEOS font metrics and inherited band paper; marker itself is
        # style0 even when the enclosing heading/body profiles are B/I/U.
        custom=appearance(body=dict(origin=1,family=1,size=10,styles=7,foreground=3,background=6),
            heading1=dict(origin=1,family=3,size=24,styles=7,foreground=6,background=7),
            code=dict(origin=1,family=26,size=10,styles=7,foreground=14,background=6))
        for label,raw in [('heading','# **Large**\rhidden text\r## Child\rmore\r# Next\rtail\r'),
            ('region',':::region **Styled**\rhidden\r:::end\rAfter.\r'),
            ('code',':::basic\r10 PRINT "Hi"\r:::\r:::asm\rstart: rts\r:::\rtail\r')]:
            context=load(raw,custom);check('genuine-'+label,*context)
        result=dict(status='passed',identity=identity,frames=frames,pixels_checked=len(frames)*64000,
            attributes_checked=len(frames)*1000,scope='Actual public folded preview, canonical/rawfont pixels, page-edge marker continuation, genuine role fonts, full16MiB read-only guard; CPU transport seams, no native claim.')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    except BaseException:
        (out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
    finally:f.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args()
    out=ROOT/'build/geos-fold-preview'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
    with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for folder in ('tests','tools'):
            for path in sorted((ROOT/folder).glob('*.py')):archive.write(path,path.relative_to(ROOT))
    print('RUN',out,flush=True);run(out,a.fixture)
