"""Actual32-asset GEOS bold/italic inline editor gallery and source oracle.

Own7900/text8000. Canonical SuperMark remains literal; no debugger source/PC
writes. Model uses whole-input host matched pairs and independent font metrics.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,zipfile
import test_geos_semantic_editor as semantic
import test_geos_semantic_io_vice as io
from test_fold_retention_vice import Captured
from d81_image import D81Image
from png_pixels import read_png
import vice_plan
live=io.live;ROOT=live.ROOT
DEFAULT=ROOT/'build/geos-semantic-editor/20261025T033255997029Z/fixture'


def freeze(source):
    source=Path(source).resolve();chargen=(source/'fonts/chargen.bin').read_bytes()
    flat=io.previous.freeze(source)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');e=ROOT/'agentsworking/evidence/M7'/(stamp+'-geos-inline-native');e.mkdir(parents=True)
    for p in flat.iterdir():
        if p.is_file():shutil.copy2(p,e/p.name)
    (e/'chargen.bin').write_bytes(chargen)
    assert len(json.loads((e/'freeze.json').read_text())['catalog'])==32
    (e/'inline.bin').write_bytes(semantic.INLINE_FIXTURE)
    p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'inline.bin'),'inline,s'],capture_output=True,text=True)
    (e/'inline-package.log').write_text(p.stdout+p.stderr);assert p.returncode==0
    assert D81Image((e/'working.d81').read_bytes()).read(b'INLINE',kind=1).data==semantic.INLINE_FIXTURE
    shutil.copy2(e/'working.d81',e/'initial-fixtures.d81');print('FROZEN '+str(e),flush=True);return e


def scenario(e):
    n=io.Plan(e,json.loads((e/'editor-report.json').read_text()),'gallery');data=semantic.INLINE_FIXTURE;caret=0;preferred=None
    def capture(ident,mode=3,ui=0,mark=False,anchor=0,pref=False,group=None):
        n.memory(ident+'_caret','se_hot_caret',caret,3);n.memory(ident+'_mark','se_sel_mark',int(mark))
        if mark:n.memory(ident+'_anchor','se_sel_anchor',anchor,3)
        if mode<3 and ui==0:n.memory(ident+'_styles','se_st_valid',1);n.memory(ident+'_styledone','se_st_request',0)
        if mode==3:n.memory(ident+'_visible','se_v_seen',1)
        if pref:n.memory(ident+'_preferred','se_l_preferred',preferred,3);n.memory(ident+'_preferred_kind','se_n_preferred_valid',2)
        n.snapshot(ident,data,mode,ui)
        n.cases[-1].update(caret=caret,mark=mark,anchor=anchor,preferred=preferred if pref else None,group=group)
    def position(ident,p):
        nonlocal caret,preferred
        line=data[:p].count(b'\r')+1;column=p-(data.rfind(b'\r',0,p)+1)
        n.typed(ident+'_goto','goto '+str(line))
        if column:n.send(ident+'_right',bytes([0x1D])*column)
        caret=p;preferred=None
    n.boot();n.open('open_inline',b'INLINE');n.memory('exact_source406','se_doc_length',len(data),3)
    for mode in (0,1,2):n.mode_to(mode);capture('source'+str((40,60,80)[mode]),mode,group='initial-modes')
    n.typed('enter_geos','mode hires');capture('geos-inline',group='initial-modes')
    position('bold',data.index(live.grid.native_text('Strong')));capture('bold-caret')
    n.send('typeQ',live.grid.native_text('Q'));data=data[:caret]+live.grid.native_text('Q')+data[caret:];caret+=1
    n.memory('real_pending','se_hot_pending',1);capture('pending-bold')
    n.send('undoQ',bytes([0x1A]));data=semantic.INLINE_FIXTURE;caret-=1;capture('undo-bold')
    closing=data.index(b'**',caret+2);position('closing',closing+1)
    n.send('backspace_close',bytes([0x14]));data=data[:closing]+data[closing+1:];caret=closing;capture('unmatched-close')
    n.send('undo_close',bytes([0x1A]));data=semantic.INLINE_FIXTURE;caret=closing+1;capture('undo-close',group='after-undo')
    start=data.index(live.grid.native_text('Plain'));stop=data.index(live.grid.native_text('italic'),start)+3
    position('mark_start',start);n.send('mark_key',bytes([0x89]));n.send('select_styles',bytes([0x1D])*(stop-start));caret=stop
    capture('selected-styles',mark=True,anchor=start,group='after-undo');n.send('unmark_key',bytes([3]))
    position('navigation',start+5)
    widths=(e/'bsw9-widths.bin').read_bytes()
    for i,command in enumerate((37,37,36,39,38)):
        caret,preferred,_,_=semantic.navigation(data,widths,caret,command,preferred)
        n.send('vertical_key_'+str(i),bytes([{37:0x11,36:0x91,39:0x87,38:0x86}[command]]));capture('styled-nav-'+str(i),pref=True,group='after-undo')
    n.send('help_key',bytes([0x8B]),ui=1);capture('help',ui=1,group='after-undo');n.send('helpclose_key',bytes([0x8B]))
    n.send('File_key',bytes([0x85,0x46]),ui=1);capture('File-menu',ui=1,group='after-undo');n.send('Fileclose_key',bytes([3]))
    n.send('command_key',bytes([0x88]),ui=2);capture('commandline',ui=2,group='after-undo');n.send('commandcancel_key',bytes([3]));capture('restored',group='after-undo')
    return n


def evaluate(e):
    out=e/'gallery';s=json.loads((e/'editor-report.json').read_text())['symbols'];cases=json.loads((out/'cases.json').read_text());images=live.grid.reu_images(out/'run');fonts={name:(e/name).read_bytes() for name in live.geos.GEOS_FONTS};fonts['native8.bin']=(e/'grid80.seo').read_bytes()[36+0xC00:36+0x1000]
    font40=(e/'chargen.bin').read_bytes()[0x800:0x1000];assert len(font40)==2048
    palette={};catalog=None;groups={};intervals=0;observed=[];cache_banks={}
    for c in cases:
        if not c['group']:continue
        ram=(out/'captures'/(c['id']+'-ram.bin')).read_bytes();handle=ram[s['se_gc_handle']]
        if handle:
            physical=ram[s['se_reu_map']+handle]
            assert physical and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+physical]==0xFE
            cache_banks.setdefault(c['group'],set()).add(physical)

    for c in cases:
        ident=c['id'];ram=(out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(out/'captures'/(ident+'-colors.bin')).read_bytes();reu=images[ident];f=Captured(s,ram,colors,e);f.colored=True;data=bytes.fromhex(c['source'])
        assert live.merged(f,reu)==data and f.get('se_hot_caret')==c['caret'] and bool(f.get('se_sel_mark',1))==c['mark'],(ident,'canonical source/caret/mark')
        if c['mark']:assert f.get('se_sel_anchor')==c['anchor']
        if c['preferred'] is not None:assert f.get('se_l_preferred')==c['preferred'] and f.get('se_n_preferred_valid',1)==2
        assert f.read(0xC600,1024)==bytes((i*73+29)&255 for i in range(1024))
        assert all(f.get(k,1)==0 for k in ('se_e_job','se_e_draw_busy','se_e_redraw','se_doc_read_locks','se_e_error','se_f_owner'))
        cat=f.read(s['se_overlay_ids'],192)
        if catalog is None:catalog=cat
        assert cat==catalog
        if c['mode']==3:
            assert f.get('se_v_seen',1)==1
            bits,attrs,_,_=semantic.expected(f,data,fonts)
        else:
            (a,b),_,_,_=live.geos.grid.expected(f,data)
            if c['mode']==0:
                assert f.read(0x4000,1000)==a and bytes(v&15 for v in colors)==b,(ident,'source40 matrix/colors')
                assert f.read(0x4800,2048)==font40,(ident,'full256glyphsource40fontvsfrozenROM')
                bits=bytearray(8000);attrs=bytearray(1000)
                for row in range(25):
                    for col in range(40):
                        at=row*40+col;code=a[at];bits[row*320+col*8:row*320+col*8+8]=bytes(v for v in font40[code*8:code*8+8]);attrs[at]=(b[at]<<4)|6
            else:bits,attrs=a,b
        if c['mode']:
            assert ram[0x6000:0x7F40]==bits,(ident,'bitmap',next((i,a,b) for i,(a,b) in enumerate(zip(ram[0x6000:0x7F40],bits)) if a!=b))
            assert ram[0x4000:0x43E8]==attrs,(ident,'attrs',next((i,a,b) for i,(a,b) in enumerate(zip(ram[0x4000:0x43E8],attrs)) if a!=b))
        w,h,pixels=read_png(out/('native-'+ident+'.png'));assert (w,h)==(384,272)
        for y in range(200):
            for x in range(320):
                attr=attrs[(y//8)*40+x//8];ink=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8));role=attr>>4 if ink else attr&15;actual=pixels[(35+y)*w+32+x]
                assert actual==palette.setdefault(role,actual),(ident,'actualVICpixel',x,y)
        if c['group']:
            handle=f.get('se_gc_handle',1);physical=f.ram[s['se_reu_map']+handle] if handle else 0
            if handle:assert physical and f.get('se_gc_epoch',2)==f.get('se_reu_epoch',2) and f.ram[s['se_reu_logical_owner']+handle]==f.ram[s['se_reu_physical_owner']+physical]==0xFE
            else:assert c['mode']==0,'only initial text40 precedes derived cache allocation'
            assert len(reu)==16*1024*1024
            masked=bytearray(reu)
            if c['group']=='initial-modes':
                for bank in cache_banks[c['group']]:masked[bank*65536:(bank+1)*65536]=bytes(65536)
            else:
                assert handle and len(cache_banks[c['group']])==1
                start=physical*65536;masked[start:start+64]=bytes(64)
                for i in range(22):a=start+0x200+i*0x800;masked[a:a+0x800]=bytes(0x800)
            state=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],n) for k,n in (('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)))
            value=state,hashlib.sha256(masked).hexdigest()
            if c['group'] in groups:intervals+=1
            assert groups.setdefault(c['group'],value)==value,(ident,'canonical/history/otherREU readonly group')
        observed.append(dict(id=ident,mode=c['mode'],source_bytes=len(data),caret=c['caret'],preferred=c['preferred']))
    assert len(set(palette.values()))==len(palette)
    assert (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes(),'read-only native run modifiedD81'
    result=dict(status='passed',identity=json.loads((e/'freeze.json').read_text()),frames=observed,screenshots=len(cases),native_pixels=len(cases)*64000,native_attributes=len(cases)*1000,whole16MiB_readonly_intervals=intervals,after_undo_FE_allowance='header64+22x2048slots only; all undeclared cache prefix/tail exact',initial_modes_FE_allowance='union of authenticated allocated FE banks; initial text40 may precede cache allocation',fullROM_font_sha256=hashlib.sha256((e/'chargen.bin').read_bytes()).hexdigest(),scope='ActualROMD81FileOpen+IRQnative inline bold/italic/nested/code/pending/undo/unmatched/stylemetricnavigation/selection/all4modes/UI; markersliteral; no physicalkey/timing claim.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result


def execute(e):
    n=scenario(e);plan=n.plan();assert len({x['id'] for x in plan['steps']})==len(plan['steps'])
    (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
    with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for module in (__file__,semantic.__file__,live.__file__,io.__file__,io.native.__file__,live.geos.__file__,ROOT/'tools/supermark_model.py'):
            p=Path(module);z.write(p,p.relative_to(ROOT))
    project=live.grid.synchronous_project(n.out);vice_plan.PROJECT=project;p=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120);(n.out/'dotnet-build.log').write_text(p.stdout+p.stderr);assert p.returncode==0
    print('NATIVE '+str(e)+' steps='+str(len(n.steps))+' IRQbytes='+str(n.keys)+' screenshots='+str(len(n.cases)),flush=True)
    vice_plan.run_plan(plan,n.out);return evaluate(e)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path);p.add_argument('--source-freeze',type=Path,default=DEFAULT);p.add_argument('--verify',type=Path);args=p.parse_args()
    if args.verify:return evaluate(args.verify.resolve())
    if args.run:return execute((args.fixture or freeze(args.source_freeze)).resolve())
    print('Prepared only; --run requires own7900/text8000 native window.')


if __name__=='__main__':main()
