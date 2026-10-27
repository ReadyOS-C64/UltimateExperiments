"""Prepared native GEOS folds: real File/Open and IRQ events,8100/text8200.

Requires an explicit parent-released immutable CPU fixture and --run. No shared
build, monitor document/register/PC writes, substitute fold records, or physical
keyboard claim. Independent canonical fold/raster models drive every capture.
"""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import asdict
import argparse,hashlib,json,shutil,subprocess,zipfile
import test_geos_preview_vice as previous
import test_geos_fold_editor as folded
import test_fold_projection as grid_fold
from test_fold_locator import target_model
from test_folds import action_model
from test_fold_retention_vice import Captured,decoded_fold
from test_geos_navigation_vice import object_bytes
from d81_image import D81Image
from png_pixels import read_png
from geos_fold_model import raster,preview,navigation,normalize_top
import vice_plan
from cache_job_build import editor_pair_index

ROOT=previous.ROOT;live=previous.live


class Plan(previous.Plan):
    def plan(self):
        p=super().plan();p['global_defaults']['monitor_port_start']=8100
        p['global_defaults']['monitor_port_span']=1
        assert not p['global_defaults'].get('kill_stale',False)
        return p


def freeze(cpu,expected_prg=None,expected_disk=None):
    """Copy ONLY the explicit immutable product; never the changing shared build."""
    cpu=cpu.resolve();identity=json.loads((cpu/'freeze.json').read_text())
    e=ROOT/'agentsworking/evidence/M7'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ-geos-fold-native');e.mkdir(parents=True)
    for name in ('editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json','supereditor.d81'):
        shutil.copy2(cpu/'build'/name,e/name)
    disk=D81Image((e/'supereditor.d81').read_bytes());prg=(e/'editor.prg').read_bytes()
    prg_sha=hashlib.sha256(prg).hexdigest();disk_sha=hashlib.sha256((e/'supereditor.d81').read_bytes()).hexdigest()
    assert prg_sha==identity['prg_sha256'] and disk_sha==identity['disk_sha256']
    assert expected_prg is None or prg_sha==expected_prg
    assert expected_disk is None or disk_sha==expected_disk
    assert disk.read(b'SUPEREDITOR',kind=2).data==prg
    names=identity['names'];seal=json.loads((e/'editor-report.json').read_text())['resident_binding']['digest']
    assert {'geosfold','geostail'}<=set(names)
    for name in names:
        image=(cpu/'build/overlays'/(name+'.seo')).read_bytes()
        assert image[20:36]==image[36:52]==bytes.fromhex(seal)
        assert disk.read(name.upper().encode(),kind=1).data==image
        (e/(name+'.seo')).write_bytes(image)
    for name in live.geos.GEOS_FONTS+('native8.bin','chargen.bin'):
        shutil.copy2(cpu/'fonts'/name,e/name)
    pack=disk.read(b'GEOSFONTS',kind=1).data;(e/'font-pack.bin').write_bytes(pack)
    report=json.loads((e/'editor-report.json').read_text());start=int.from_bytes(prg[:2],'little');offset=report['symbols']['session_defaults']-start+2
    defaults=prg[offset:offset+64];assert defaults[:8]==b'SEST\1\x40\10\7'
    (e/'editor-defaults.bin').write_bytes(defaults)
    shutil.copy2(cpu/'product-sources.zip',e/'product-sources.zip')
    final=dict(prg_sha256=prg_sha,disk_sha256=disk_sha,resident_binding=seal,catalog=names,
        asset_sha256={n:hashlib.sha256((e/(n+'.seo')).read_bytes()).hexdigest() for n in names},
        cpu_fixture=str(cpu),font_pack_sha256=hashlib.sha256(pack).hexdigest())
    (e/'freeze.json').write_text(json.dumps(final,indent=2)+'\n')
    shutil.copy2(e/'supereditor.d81',e/'working.d81');data=live.grid.fixture();(e/'diverse.bin').write_bytes(data)
    p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'diverse.bin'),'diverse,s'],capture_output=True,text=True)
    (e/'package.log').write_text(p.stdout+p.stderr);assert not p.returncode
    assert D81Image((e/'working.d81').read_bytes()).read(b'DIVERSE',kind=1).data==data
    shutil.copy2(e/'working.d81',e/'initial-fixtures.d81');print('FROZEN',e,flush=True)
    return e


def scenario(e):
    n=Plan(e,json.loads((e/'editor-report.json').read_text()),'gallery');data=live.grid.fixture()
    folds=folded.tree(data);caret=0;clip=None;mark=False;anchor=None;preferred=None
    fonts={name:(e/name).read_bytes() for name in live.geos.GEOS_FONTS+('native8.bin',)}
    def capture(ident,mode=3,ui=0,kind='literal',require_summary=False):
        n.memory(ident+'_caret','se_hot_caret',caret,3)
        n.memory(ident+'_mark','se_sel_mark',int(mark),1)
        if mark:n.memory(ident+'_anchor','se_sel_anchor',anchor,3)
        n.capture(ident,data,mode,ui,kind=kind,caret=caret,mark=mark,anchor=anchor,
            folds=[f.bytes().hex() for f in folds],clipboard=clip.hex() if clip is not None else None,
            require_summary=require_summary)
    def goto(ident,at):
        nonlocal caret,preferred
        line=data[:at].count(b'\r')+1;column=at-(data.rfind(b'\r',0,at)+1)
        n.typed(ident,f'goto {line}')
        if column:n.send(ident+'_column',bytes([0x1D])*column)
        caret=at;preferred=None
    def collapse(ident,at):
        nonlocal caret,folds
        goto(ident+'_goto',at);target=target_model(folds,caret,0);assert target!=65535
        folds,caret=action_model(folds,0,target,caret,0,caret)
        n.typed(ident,'fold')
    n.boot();n.memory('cold_font_pack_ready',0xCBC0,0xA5)
    n.open('open_diverse',b'DIVERSE');n.mode_to(2);capture('expanded80',2)
    n.typed('mode_geos','mode hires');capture('expanded-geos')
    basic=data.index(live.grid.native_text(':::basic'));asm=data.index(live.grid.native_text(':::asm'));region=data.index(live.grid.native_text(':::region'))
    collapse('collapse_basic',basic);capture('basic-collapsed')
    collapse('collapse_asm',asm);collapse('collapse_region',region)
    goto('collapsed_top',0);capture('three-collapsed')
    goto('navigation_basic',basic)
    for label,command,key in [('down-skip-hidden',37,0x11),('up-summary',36,0x91)]:
        caret,preferred,_,_=navigation(data,fonts,folds,caret,command,preferred)
        n.send(label+'_key',bytes([key]));capture(label)
    # Public GOTO ends beyond the hidden interval; no debugger caret insertion
    # or projected-source copy. The selected bytes include opener/body/closer.
    goto('select_fold_start',basic);anchor=caret;mark=True;n.send('mark_native',b'\x89')
    codefold=next(f for f in folds if f.start==basic)
    goto('select_fold_end',codefold.end);capture('marked-hidden-region')
    n.send('copy_native0B',b'\x0B');clip=data[anchor:caret]
    n.memory('complete_hidden_clip_length','se_clip_length',len(clip),3);capture('copied-hidden-region')
    n.send('unmark',b'\3');mark=False;anchor=None;goto('preview_top',0)
    n.typed('preview_collapsed','preview',ui=4);capture('preview-collapsed',ui=4,kind='preview')
    n.send('preview_next_page',b'\x87',ui=4)
    capture('preview-summary-page2',ui=4,kind='preview',require_summary=True)
    n.send('preview_readonly',b'Q\x14',ui=4);capture('preview-readonly',ui=4,kind='preview')
    n.send('preview_first_page',b'\x86',ui=4)
    n.send('return_literal',b'\r');capture('literal-restored')
    n.mode_to(2);capture('collapsed80',2)
    n.typed('mode_geos_again','mode hires');capture('collapsed-geos-return')
    n.send('help',b'\x8B',ui=1);capture('fold-help',ui=1)
    n.send('help_close',b'\x8B');capture('fold-help-restored')
    # Canonical GOTO is deliberately different from projected arrows: asking
    # for a hidden body must expand its ancestor before publishing caret/pixels.
    goto('goto_hidden_basic_body',codefold.hidden)
    folds,caret=action_model(folds,5,0,caret,0,caret)
    capture('hidden-goto-reveals-basic')
    n.typed('expand_all','unfold all');folds,caret=action_model(folds,4,0,caret,0,caret)
    capture('expanded-again')
    return n


def evaluate(e):
    out=e/'gallery';s=json.loads((e/'editor-report.json').read_text())['symbols'];identity=json.loads((e/'freeze.json').read_text())
    cases=json.loads((out/'cases.json').read_text());images=live.grid.reu_images(out/'run')
    fonts={name:(e/name).read_bytes() for name in live.geos.GEOS_FONTS+('native8.bin',)}
    catalog=previous.pack_catalog((e/'font-pack.bin').read_bytes(),fonts['native8.bin'])
    palette={};observed=[];canonical=None;immutable={};intervals=0
    # Masks are only authenticated FE/type46 banks actually used by this run.
    derived=set()
    for c in cases:
        ram=(out/'captures'/(c['id']+'-ram.bin')).read_bytes()
        derived.update(i for i in range(256) if ram[s['se_reu_physical_owner']+i] in (0xFE,0x46))
    for c in cases:
        ident=c['id'];ram=(out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(out/'captures'/(ident+'-colors.bin')).read_bytes();reu=images[ident]
        f=Captured(s,ram,colors,e);f.colored=True;data=bytes.fromhex(c['source']);folds=[decoded_fold(bytes.fromhex(x)) for x in c['folds']]
        assert live.merged(f,reu)==data and f.get('se_hot_caret')==c['caret']
        assert f.get('se_mode',1)==c['mode'] and f.get('se_e_ui',1)==c['ui']
        assert bool(f.get('se_sel_mark',1))==c['mark']
        if c['mark']:assert f.get('se_sel_anchor')==c['anchor']
        assert not any(f.get(k,1) for k in ('se_e_job','se_e_error','se_e_redraw','se_e_draw_busy','se_f_owner','se_doc_read_locks','se_hot_pending','se_h_dirty'))
        assert f.read(0xC600,1024)==bytes((i*73+29)&255 for i in range(1024))
        assert f.read(0xCB80,64)==(e/'editor-defaults.bin').read_bytes()
        pack=(e/'font-pack.bin').read_bytes()
        assert f.read(0xCBC0,1)==b'\xA5' and f.read(0xCBC6,1)==f.read(0xCBC8,1)==b'\0'
        assert f.read(0xCBC3,2)==f.read(s['se_reu_epoch'],2)
        for i,handle in enumerate(f.read(0xCBC1,2)):
            bank=ram[s['se_reu_map']+handle]
            assert handle and bank and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+bank]==0xFD
            part=pack[i*65536:(i+1)*65536]
            assert reu[bank*65536:bank*65536+len(part)]==part,(ident,'complete actual cold fontpack')
        for order,name in enumerate(identity['catalog']):
            image=(e/(name+'.seo')).read_bytes();slot=editor_pair_index(image[5],image[6]) if 'catalog_index' in s else order
            handle=f.get(('se_overlay_asset','se_overlay_asset_second','se_overlay_asset_third','se_overlay_asset_fourth')[slot>>4],1)
            bank=ram[s['se_reu_map']+handle];assert handle and bank and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+bank]==2
            payload=image[36:];start=bank*65536+(slot&15)*4096
            assert reu[start:start+len(payload)]==payload,(ident,'catalog',name)
        if f.get('se_ef_valid',1):
            token=f.read(s['se_ef_token'],5)
            assert f.get('se_ef_count',2)==len(folds) and ram[s['object_owner']+token[0]]==0x46
            raw=object_bytes(f,reu,token,len(folds)*32)
            assert raw==b''.join(fold.bytes() for fold in folds),(ident,'canonical checked fold tree')
        else:assert not any(x.flags&1 for x in folds),(ident,'missing trusted collapsed map')
        if c['clipboard'] is not None:
            clip=bytes.fromhex(c['clipboard']);assert object_bytes(f,reu,f.read(s['se_clip_token'],5),len(clip))==clip
        state=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],w) for k,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)])
        if canonical is None:canonical=state
        assert canonical==state,(ident,'source/history publication')
        group='precopy' if c['clipboard'] is None else 'postcopy'
        masked=bytearray(reu)
        for bank in derived:masked[bank*65536:(bank+1)*65536]=bytes(65536)
        digest=hashlib.sha256(masked).hexdigest()
        if group in immutable:intervals+=1
        assert digest==immutable.setdefault(group,digest),(ident,'wholeREU outside declared derived banks')
        if c['kind']=='preview':
            result=preview(data,f.read(0xCB80,64),folds,catalog=catalog,top=f.get('se_v_top'))
            bits,attrs=result.bitmap,result.attrs
            assert f.get('se_v_bottom')==result.bottom
            assert f.read(s['se_v_rows'],len(result.anchors)*3)==b''.join(x.to_bytes(3,'little') for x in result.anchors)
            if c.get('require_summary'):
                summaries=[(fold,row) for fold in folds if fold.flags&1
                    for row in result.rows if row.end==fold.hidden-1 and row.next>=fold.end]
                assert len(summaries)==3,(ident,'page must actually contain all3 visible summaries',summaries)
                assert all(row.profile==7 for fold,row in summaries if fold.kind==2),'collapsed fences use CODEprofile'
        elif c['mode']==3:
            assert normalize_top(data,folds,f.get('se_v_top'))==f.get('se_v_top')
            bits,attrs,rows,_=raster(data,fonts,folds,top=f.get('se_v_top'),caret=c['caret'],anchor=c['anchor'] if c['mark'] else None,
                nowrap=bool(f.get('se_l_mode',1)),pan=f.get('se_l_pan'))
        else:(bits,attrs),_,_,_,_=grid_fold.expected(f,data,folds,f.get('se_v_top'))
        matrix,ink,popup=live.geos.grid.logical_ui(f,data)
        bits,attrs=live.geos.with_chrome(bits,attrs,matrix,ink,fonts['native8.bin'],popup)
        assert ram[0x6000:0x7F40]==bits,(ident,'bitmap',[(i,a,b) for i,(a,b) in enumerate(zip(ram[0x6000:0x7F40],bits)) if a!=b][:8])
        assert ram[0x4000:0x43E8]==attrs,(ident,'attrs')
        w,h,pixels=read_png(out/('native-'+ident+'.png'));assert (w,h)==(384,272)
        for y in range(200):
            for x in range(320):
                at=(y//8)*40+x//8;ink=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8));color=attrs[at]>>4 if ink else attrs[at]&15;pixel=pixels[(35+y)*w+32+x]
                assert pixel==palette.setdefault(color,pixel),(ident,'actualVIC',x,y)
        observed.append(dict(id=ident,kind=c['kind'],mode=c['mode'],caret=c['caret'],collapsed=sum(bool(f.flags&1) for f in folds),png_sha256=hashlib.sha256((out/('native-'+ident+'.png')).read_bytes()).hexdigest()))
    assert len(set(palette.values()))==len(palette),'native palette roles alias'
    assert (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes()
    result=dict(status='passed',identity=identity,frames=observed,pixels=len(cases)*64000,attributes=len(cases)*1000,
        whole16MiB_derived_only_intervals=intervals,
        scope='Actual ROM FileOpen/IRQ GEOS literal+formatted-preview folds, projectednavigation, canonical hidden-region copy,80roundtrip and help; independent native pixels/source/history/catalog/shim. No physical-key/timing claim.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result


def execute(e):
    n=scenario(e);p=n.plan();assert len({x['id'] for x in p['steps']})==len(p['steps'])
    (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(p,indent=2)+'\n')
    with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for folder in ('tests','tools'):
            for path in sorted((ROOT/folder).glob('*.py')):z.write(path,path.relative_to(ROOT))
    project=live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
    b=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120)
    (n.out/'dotnet-build.log').write_text(b.stdout+b.stderr);assert not b.returncode
    print('NATIVE',e,'ports8100/8200','steps',len(n.steps),'IRQbytes',n.keys,'frames',len(n.cases),flush=True)
    vice_plan.run_plan(p,n.out);return evaluate(e)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--freeze',action='store_true');p.add_argument('--source-fixture',type=Path);p.add_argument('--fixture',type=Path);p.add_argument('--verify',type=Path);p.add_argument('--expected-prg');p.add_argument('--expected-disk');a=p.parse_args()
    if a.verify:evaluate(a.verify.resolve())
    elif a.run or a.freeze:
        if not a.fixture and not a.source_fixture:p.error('explicit parent-released --source-fixture required')
        e=a.fixture.resolve() if a.fixture else freeze(a.source_fixture,a.expected_prg,a.expected_disk)
        if a.run:execute(e)
    else:print('Prepared only; wait parent CPU-pass/final-product grant before freeze/run. Own8100/text8200.')
