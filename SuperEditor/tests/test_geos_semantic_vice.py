"""Native PAL D81/IRQ acceptance for independently styled GEOS and all modes.

Own7700/text7800 only. Initial source enters through the real File/Open dialog;
no monitor source/register writes or synthetic screenshot pixels are used.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,zipfile
import test_geos_editor_vice as live
import test_geos_semantic_editor as semantic
import test_geos_navigation_vice as native
from test_fold_retention_vice import Captured
from d81_image import D81Image
from png_pixels import read_png
import vice_plan
ROOT=live.ROOT


def freeze(cpu_fixture=None):
    if cpu_fixture:
        cpu_fixture=Path(cpu_fixture).resolve();identity=json.loads((cpu_fixture/'freeze.json').read_text())
        live.grid.NAMES=identity['names']
        e=live.grid.freeze(cpu_fixture/'build',cpu_fixture/'product-sources.zip',wide_colors=True)
        target=ROOT/'agentsworking/evidence/M7'/e.name.replace('-grid-editor-native','-geos-semantic-native');shutil.move(e,target);e=target
        live.grid.package(e)
        for name in live.geos.GEOS_FONTS:shutil.copy2(cpu_fixture/'fonts'/name,e/name)
    else:
        e=live.freeze();target=e.with_name(e.name.replace('-geos-editor-native','-geos-semantic-native'));shutil.move(e,target);e=target
    (e/'styled.bin').write_bytes(semantic.FIXTURE)
    p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'styled.bin'),'styled,s'],capture_output=True,text=True)
    (e/'styled-package.log').write_text(p.stdout+p.stderr);assert p.returncode==0
    assert D81Image((e/'working.d81').read_bytes()).read(b'STYLED',kind=1).data==semantic.FIXTURE
    shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')
    return e


def scenario(e):
    n=native.Plan(e,json.loads((e/'editor-report.json').read_text()));data=semantic.FIXTURE
    def capture(ident,mode=3,ui=0):
        n.snapshot(ident,data,mode,ui)
        if mode<3 and ui==0:
            n.memory(ident+'_stylevalid','se_st_valid',1);n.memory(ident+'_styledone','se_st_request',0)
    n.boot();n.open('open_styled',b'STYLED')
    n.memory('opened328','se_doc_length',len(data),3)
    for mode in (0,1,2):
        n.mode_to(mode);n.memory('ready_style_'+str(mode),'se_st_valid',1)
        n.memory('done_style_'+str(mode),'se_st_request',0);capture('source'+str((40,60,80)[mode]),mode)
    n.typed('geos','mode hires');capture('geos-styled')
    n.send('typeQ',live.grid.native_text('Q'));data=live.grid.native_text('Q')+data;capture('geos-typed')
    n.typed('undoQ','undo');data=semantic.FIXTURE;capture('geos-undo')
    n.send('Filemenu',bytes([0x85,0x46]),ui=1);capture('File-menu',ui=1)
    n.send('Fileclose',bytes([3]));capture('File-restored')
    n.send('help_key',bytes([0x8B]),ui=1);capture('help',ui=1)
    n.send('helpclose',bytes([0x8B]));capture('help-restored')
    n.send('commandline_key',bytes([0x88]),ui=2);capture('commandline',ui=2)
    n.send('commandcancel',bytes([3]));capture('command-restored')
    n.modal('open-dialog','O');capture('dialog',ui=3)
    n.send('dialogcancel',bytes([3]),owner=0);capture('dialog-restored')
    return n


def evaluate(e):
    out=e/'editing';s=json.loads((e/'editor-report.json').read_text())['symbols'];cases=json.loads((out/'cases.json').read_text());images=live.grid.reu_images(out/'run')
    fonts={name:(e/name).read_bytes() for name in live.geos.GEOS_FONTS}
    fonts['native8.bin']=(e/'grid80.seo').read_bytes()[36+0xC00:36+0x1000]
    palette={};observed=[];catalog=None;stable=None;stable_reu=None;readonly_intervals=0
    for c in cases:
        ident=c['id'];ram=(out/'captures'/(ident+'-ram.bin')).read_bytes();colors=(out/'captures'/(ident+'-colors.bin')).read_bytes();reu=images[ident];data=bytes.fromhex(c['source'])
        f=Captured(s,ram,colors,e);f.colored=True
        assert live.merged(f,reu)==data,(ident,'canonical merged source')
        assert ram[0xC600:0xCA00]==bytes((i*73+29)&255 for i in range(1024)),(ident,'shim')
        assert all(f.get(k,1)==0 for k in ('se_e_job','se_e_draw_busy','se_e_redraw','se_doc_read_locks')),(ident,'quiescent')
        assert f.get('se_f_owner',1)==(1 if c['ui']==3 else 0)
        current_catalog=f.read(s['se_overlay_ids'],192)
        if catalog is None:catalog=current_catalog
        assert current_catalog==catalog,(ident,'catalog')
        if ident in ('geos-undo','File-menu','File-restored','help','help-restored','commandline','command-restored','dialog','dialog-restored'):
            state=f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],w) for k,w in (
                ('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),
                ('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)))
            if stable is None:stable=state
            assert state==stable,(ident,'read-only chrome/navigation changed canonical/history')
            handle=f.get('se_gc_handle',1);assert handle and f.get('se_gc_epoch',2)==f.get('se_reu_epoch',2)
            physical=f.ram[s['se_reu_map']+handle]
            assert physical and f.ram[s['se_reu_logical_owner']+handle]==f.ram[s['se_reu_physical_owner']+physical]==0xFE
            assert len(reu)==16*1024*1024
            masked=bytearray(reu);start=physical*65536;masked[start:start+64]=bytes(64)
            for i in range(22):a=start+0x200+i*0x800;masked[a:a+0x800]=bytes(0x800)
            digest=hashlib.sha256(masked).hexdigest()
            if stable_reu is None:stable_reu=digest
            else:readonly_intervals+=1
            assert digest==stable_reu,(ident,'whole16MiBREU outside authenticated64+22slots changed')
        if c['mode']==3:
            if c['ui']==3:
                bits,attrs,_,_=semantic.body(data,fonts,top=f.get('se_v_top'),caret=f.get('se_hot_caret'))
                ui=live.grid.UI(live.grid.source40(data,f.get('se_v_top'),f.get('se_hot_caret')))
                listing=[f.read(s['se_fd_list_names']+i*16,f.read(s['se_fd_list_lengths']+i,1)[0]) for i in range(f.get('se_fd_list_count',1))]
                wanted=[x.name for x in D81Image((e/'initial-fixtures.d81').read_bytes()).entries() if x.kind==1][:8]
                assert listing==wanted,(ident,'directory raw D81')
                ui.file_dialog(f.get('se_f_device',1),f.read(s['se_f_name'],f.get('se_f_name_len',1)),listing,f.get('se_fd_list_index',1))
                bits,attrs=live.geos.with_chrome(bits,attrs,ui.matrix,ui.colors,fonts['native8.bin'],(1,4,38,19))
            else:bits,attrs,_,_=semantic.expected(f,data,fonts)
        else:
            (first,second),_,_,_=live.geos.grid.expected(f,data)
            if c['mode']==0:
                assert f.read(0x4000,1000)==first,(ident,'40columnmatrix')
                assert bytes(v&15 for v in colors)==second,(ident,'40columncolors')
                bits=bytearray(8000);attrs=bytearray(1000)
                for row in range(25):
                    for col in range(40):
                        at=row*40+col;code=first[at]
                        bits[row*320+col*8:row*320+col*8+8]=bytes(v^(255 if code&128 else 0) for v in fonts['native8.bin'][(code&127)*8:(code&127)*8+8])
                        attrs[at]=(second[at]<<4)|6
            else:bits,attrs=first,second
        if c['mode']:
            assert ram[0x6000:0x7F40]==bits,(ident,'bitmap',next((i,a,b) for i,(a,b) in enumerate(zip(ram[0x6000:0x7F40],bits)) if a!=b))
            assert ram[0x4000:0x43E8]==attrs,(ident,'attributes',next((i,a,b) for i,(a,b) in enumerate(zip(ram[0x4000:0x43E8],attrs)) if a!=b))
        width,height,pixels=read_png(out/('native-'+ident+'.png'));assert (width,height)==(384,272)
        for y in range(200):
            for x in range(320):
                attr=attrs[(y//8)*40+x//8];ink=bits[(y//8)*320+(x//8)*8+y%8]&(128>>(x%8));role=attr>>4 if ink else attr&15;actual=pixels[(35+y)*width+32+x]
                assert actual==palette.setdefault(role,actual),(ident,'nativeVICpixel',x,y,role)
        observed.append(dict(id=ident,mode=c['mode'],source_bytes=len(data),source_sha256=hashlib.sha256(data).hexdigest()))
    assert len(set(palette.values()))==len(palette),'native palette aliases'
    assert (e/'working.d81').read_bytes()==(e/'initial-fixtures.d81').read_bytes(),'read-only run changed D81'
    result=dict(status='passed',evidence=str(e),identity=json.loads((e/'freeze.json').read_text()),frames=observed,screenshots=len(cases),pixels=len(cases)*64000,attributes=len(cases)*1000,whole_REU_readonly_intervals=readonly_intervals,REU_bytes=16*1024*1024,
        scope='Actual ROM D81 FileOpen +IRQnative input +all4modes +styledGEOS +typing/undo +File/help/command/dialog; independent canonical block/lexer/fullnativeVICpixel oracle. No inline markup hiding/physicalchord/timing claim.')
    (out/'semantic-verifier.py').write_text(Path(__file__).read_text())
    (out/'semantic-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result


def execute(e):
    e=Path(e).resolve();n=scenario(e);plan=n.plan();assert len({x['id'] for x in plan['steps']})==len(plan['steps'])
    (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
    with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for module in (__file__,semantic.__file__,live.__file__,native.__file__,live.geos.__file__,ROOT/'tools/supermark_model.py'):
            p=Path(module);z.write(p,p.relative_to(ROOT))
    project=live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
    p=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120)
    (n.out/'dotnet-build.log').write_text(p.stdout+p.stderr);assert p.returncode==0
    print('NATIVE '+str(e)+' steps='+str(len(n.steps))+' IRQbytes='+str(n.keys)+' screenshots='+str(len(n.cases)),flush=True)
    vice_plan.run_plan(plan,n.out);return evaluate(e)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path);p.add_argument('--cpu-fixture',type=Path);p.add_argument('--verify',type=Path);args=p.parse_args()
    if args.verify:return evaluate(args.verify.resolve())
    if args.run:return execute(args.fixture or freeze(args.cpu_fixture))
    print('Prepared; --run uses exclusive7700/text7800 with exact immutable product/D81.')


if __name__=='__main__':main()
