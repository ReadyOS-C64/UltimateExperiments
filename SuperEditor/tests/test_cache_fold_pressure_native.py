"""Native optional-analysis retirement under real Copy/Cut/fold rebuild pressure.

Actual sealed D81, ROM File/Open and IRQ bytes. Independent canonical source,
clipboard, fold flags/intervals and VIC pixel models. CPU tests separately prove
precise DMA, foreign ownership and refusal cases. No physical keyboard claim.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, shutil, socket, subprocess, zipfile
import test_geos_fold_native as base
from test_fold_retention_vice import Captured, decoded_fold
from test_geos_navigation_vice import object_bytes
from png_pixels import read_png
from d81_image import D81Image
import vice_plan
ROOT=base.ROOT


def free_ports():
    for port in (8100,*range(8200,8240)):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',port))


def freeze(fixture):
    e=base.freeze(fixture)
    target=ROOT/'agentsworking/evidence/M8'/(e.name.replace('geos-fold-native','cache-fold-pressure-native'))
    shutil.move(e,target);e=target
    data=base.folded.TINY;(e/'pressure.bin').write_bytes(data)
    p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'pressure.bin'),'pressure,s'],capture_output=True,text=True)
    (e/'pressure-package.log').write_text(p.stdout+p.stderr);assert p.returncode==0
    assert D81Image((e/'working.d81').read_bytes()).read(b'PRESSURE',kind=1).data==data
    shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')
    return e


def scenario(e):
    n=base.Plan(e,json.loads((e/'editor-report.json').read_text()),'pressure')
    data=base.folded.TINY;folds,_=base.action_model(base.folded.tree(data),3,0,0,0,0)
    region=folds[0];clip=data[region.start:region.end]
    def capture(ident,source,tree,caret,marked=False):
        n.memory(ident+'_caret','se_hot_caret',caret,3)
        n.capture(ident,source,3,0,kind='literal',caret=caret,mark=marked,
                  anchor=region.start,folds=[f.bytes().hex()for f in tree],clipboard=clip.hex())
    n.boot();n.open('open_pressure',b'PRESSURE');n.typed('enter_geos','mode hires')
    n.typed('collapse_all','fold all');n.typed('select_start','goto 2')
    n.send('mark',b'\x89');n.typed('select_end','goto 5')
    n.send('copy',b'\x0b');capture('copied',data,folds,region.end,True)
    n.send('cut',b'\x18')
    changed,remaining=base.folded.retention.retained(folds,data,region.start,len(clip),b'')
    capture('cut-rebuilt',changed,remaining,region.start)
    n.send('undo',b'\x1a')
    restored,tree=base.folded.retention.retained(remaining,changed,region.start,0,clip)
    assert restored==data
    capture('undo-restored',data,tree,region.end)
    return n


def evaluate(e):
    out=e/'pressure';s=json.loads((e/'editor-report.json').read_text())['symbols']
    identity=json.loads((e/'freeze.json').read_text());cases=json.loads((out/'cases.json').read_text())
    images=base.live.grid.reu_images(out/'run')
    fonts={n:(e/n).read_bytes()for n in base.live.geos.GEOS_FONTS+('native8.bin',)}
    palette={};frames=[];before=None
    for c in cases:
        ident=c['id'];ram=(out/'captures'/(ident+'-ram.bin')).read_bytes()
        colors=(out/'captures'/(ident+'-colors.bin')).read_bytes();reu=images[ident]
        f=Captured(s,ram,colors,e);f.colored=True;data=bytes.fromhex(c['source'])
        assert base.live.merged(f,reu)==data and f.get('se_hot_caret')==c['caret'],(ident,'source/caret')
        assert f.get('se_mode',1)==3 and f.get('se_e_ui',1)==0
        assert bool(f.get('se_sel_mark',1))==c['mark']
        if c['mark']:assert f.get('se_sel_anchor')==c['anchor']
        assert not any(f.get(n,1)for n in ('se_e_job','se_e_error','se_e_redraw','se_e_draw_busy','se_f_owner','se_doc_read_locks','se_hot_pending'))
        assert f.read(0xc600,1024)==bytes((i*73+29)&255 for i in range(1024))
        clip=bytes.fromhex(c['clipboard']);assert f.get('se_clip_length')==len(clip)
        assert object_bytes(f,reu,f.read(s['se_clip_token'],5),len(clip))==clip
        folds=[decoded_fold(bytes.fromhex(x))for x in c['folds']]
        assert f.get('se_ef_valid',1) and f.get('se_ef_count',2)==len(folds)
        raw=object_bytes(f,reu,f.read(s['se_ef_token'],5),len(folds)*32)
        for i,fold in enumerate(folds):
            record=raw[i*32:(i+1)*32];expected=fold.bytes()
            assert record[:21]==expected[:21] and record[25:]==expected[25:],(ident,'fold intervals/flags')
        bits,attrs,rows,_=base.raster(data,fonts,folds,top=f.get('se_v_top'),caret=c['caret'],anchor=c['anchor']if c['mark']else None)
        matrix,ink,popup=base.live.geos.grid.logical_ui(f,data)
        bits,attrs=base.live.geos.with_chrome(bits,attrs,matrix,ink,fonts['native8.bin'],popup)
        assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(ident,'independent raster')
        w,h,pixels=read_png(out/('native-'+ident+'.png'));assert(w,h)==(384,272)
        for y in range(200):
            for x in range(320):
                at=y//8*40+x//8;ink=bits[y//8*320+x//8*8+y%8]&(128>>(x%8))
                color=attrs[at]>>4 if ink else attrs[at]&15;pixel=pixels[(35+y)*w+32+x]
                assert pixel==palette.setdefault(color,pixel),(ident,'VIC pixel',x,y)
        for slot,name in enumerate(identity['catalog']):
            handle=f.get(('se_overlay_asset','se_overlay_asset_second','se_overlay_asset_third','se_overlay_asset_fourth')[slot>>4],1)
            bank=ram[s['se_reu_map']+handle]
            assert handle and bank and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+bank]==2
            payload=(e/(name+'.seo')).read_bytes()[36:];at=bank*65536+(slot&15)*4096
            assert reu[at:at+len(payload)]==payload,(ident,'sealed asset',name)
        token=f.read(s['se_bc_arena'],5);flags=f.get('se_bc_flags',1)
        if ident=='copied':
            assert token!=bytes(5) and flags&17==17
            assert ram[s['object_owner']+token[0]]==0x53
            assert sorted(v for v in ram[s['object_owner']:s['object_owner']+8]if v)==[3,4,4,5,6,0x46,0x53]
            before=token
        else:
            assert before and token==bytes(5) and flags&51==18
            assert 0x53 not in ram[s['object_owner']:s['object_owner']+8]
            assert f.get('se_h_dirty',1)==int(ident=='cut-rebuilt')
        frames.append(dict(id=ident,source_bytes=len(data),cache_flags=flags,arena_token=token.hex(),png_sha256=hashlib.sha256((out/('native-'+ident+'.png')).read_bytes()).hexdigest()))
    assert len(set(palette.values()))==len(palette)
    assert (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes()
    free_ports()
    result=dict(status='PASS',identity=identity,frames=frames,native_pixels=len(cases)*64000,attributes=len(cases)*1000,scope=__doc__,ports_released=True,visual_review='pending')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def execute(e):
    free_ports();n=scenario(e);p=n.plan()
    assert len({x['id']for x in p['steps']})==len(p['steps'])
    (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n')
    with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
        for folder in ('tests','tools'):
            for path in sorted((ROOT/folder).glob('*.py')):z.write(path,path.relative_to(ROOT))
    project=base.live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
    b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120)
    (n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode
    print('NATIVE',e,'steps',len(n.steps),'IRQbytes',n.keys,flush=True)
    vice_plan.run_plan(p,n.out);print(json.dumps(evaluate(e),indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);p.add_argument('--run',action='store_true');p.add_argument('--verify',type=Path);a=p.parse_args()
    if a.verify:print(json.dumps(evaluate(a.verify.resolve()),indent=2))
    elif a.run:
        assert a.fixture,'immutable product fixture required';execute(freeze(a.fixture.resolve()))
