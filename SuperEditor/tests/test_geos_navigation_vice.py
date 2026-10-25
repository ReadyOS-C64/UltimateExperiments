"""Actual D81/IRQ GEOS navigation acceptance; owned7700/text7800 only.

No shared product build, source replacement, PC substitution or physical key
claim. Navigation targets/preferred pixelX come from canonical reference metrics.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,sys,zipfile
import test_geos_editor_vice as live
import test_geos_navigation_editor as nav
from test_fold_retention_vice import Captured

ROOT=live.ROOT
sys.path.insert(0,str(ROOT/'tools'))
import vice_plan
from d81_image import D81Image


class Plan(live.Plan):
    def memory(self,*args,**kwargs):
        super().memory(*args,**kwargs)
        self.steps[-1]['retry']['max_attempts']=100


def scenario(e):
    report=json.loads((e/'editor-report.json').read_text());n=Plan(e,report)
    data=live.grid.fixture();widths=(e/'bsw9-widths.bin').read_bytes()
    rows=nav.lines(data,widths);caret=0;top=0;preferred=None;clip=None
    def capture(ident,mode=3,ui=0,mark=False,anchor=None,pref_valid=0):
        n.memory(ident+'_expected_caret','se_hot_caret',caret,3)
        n.memory(ident+'_expected_top','se_v_top',top,3)
        n.memory(ident+'_expected_mark','se_sel_mark',int(mark))
        if anchor is not None:n.memory(ident+'_expected_anchor','se_sel_anchor',anchor,3)
        if pref_valid:
            n.memory(ident+'_preferred_valid','se_n_preferred_valid',2)
            n.memory(ident+'_preferred_pixel_x','se_l_preferred',preferred,3)
        n.snapshot(ident,data,mode,ui)
        n.cases[-1].update(caret=caret,top=top,mark=mark,anchor=anchor,
            preferred=preferred if pref_valid else None,pref_valid=pref_valid,
            clipboard=clip.hex() if clip is not None else None)
    def vertical(ident,command,key):
        nonlocal caret,top,preferred
        caret,preferred,index=nav.move(rows,caret,command,preferred)
        top=nav.viewport(rows,top,index)
        n.send(ident+'_key',bytes([key]));capture(ident, pref_valid=2)
    n.boot();n.open('open_diverse',b'DIVERSE');n.mode_to(2)
    n.memory('source80_styles','se_st_valid',1);n.memory('source80_style_done','se_st_request',0)
    capture('source80',2)
    n.typed('enter_geos','mode hires');n.send('right5',bytes([0x1D])*5);caret=5
    capture('geos-caret5')
    for i in range(3):vertical('down'+str(i+1),37,0x11)
    # A marked canonical range within one source row. Copy is the native0B
    # binding, rather than pretending that a physical CTRL chord was pressed.
    anchor=caret;n.send('mark',bytes([0x89]));n.send('select3',bytes([0x1D])*3);caret+=3
    assert 13 not in data[anchor:caret]
    preferred=None;capture('marked',mark=True,anchor=anchor)
    n.send('copy_native_0b',bytes([0x0B]));clip=data[anchor:caret]
    n.memory('clipboard_length','se_clip_length',len(clip),3)
    capture('copied',mark=True,anchor=anchor)
    n.send('unmark',bytes([3]));n.typed('mode40','mode 40')
    n.memory('actual40','se_mode',0);n.memory('forty_source_length','se_doc_length',422,3)
    n.memory('forty_caret','se_hot_caret',caret,3)
    n.typed('return_geos','mode hires');top=0;capture('mode-roundtrip')
    vertical('page-down',39,0x87);vertical('page-up',38,0x86)
    preferred=None
    n.send('help_key',bytes([0x8B]),ui=1);capture('help',ui=1)
    n.send('helpclose',bytes([0x8B]));n.send('Filemenu',bytes([0x85,0x46]),ui=1)
    capture('File-menu',ui=1);n.send('Filemenuclose',bytes([3]))
    n.modal('open-dialog','O');capture('dialog',ui=3)
    n.send('dialogcancel',bytes([3]),owner=0);capture('restored')
    return n


def object_bytes(f,reu,token,length):
    identity=token[0]
    assert token[3:5]==f.read(f.s['se_object_epoch'],2)
    assert int.from_bytes(token[1:3],'little')==f.ram[f.s['object_gen_lo']+identity]+256*f.ram[f.s['object_gen_hi']+identity]
    out=bytearray()
    for at in range(0,length,65536):
        logical=f.ram[f.s['object_extents']+identity*16+(at>>16)]
        physical=f.ram[f.s['se_reu_map']+logical]
        assert logical and physical and f.ram[f.s['se_reu_logical_owner']+logical]==f.ram[f.s['se_reu_physical_owner']+physical]
        out+=reu[physical*65536:physical*65536+min(65536,length-at)]
    return bytes(out)


def evaluate(e):
    # Existing fullnative bitmap/palette/UI/rawD81 evaluator remains unchanged.
    base=live.evaluate(e)
    out=e/'editing';s=json.loads((e/'editor-report.json').read_text())['symbols']
    cases=json.loads((out/'cases.json').read_text());images=live.grid.reu_images(out/'run')
    before=D81Image((e/'initial-fixtures.d81').read_bytes())
    directory=[x.name for x in before.entries() if x.kind==1][:8]
    stable=None;catalog=None;before_copy=None;after_copy=None;observed=[]
    def source_state(f):
        fields=(('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_h_current',4),
                ('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4))
        return f.read(s['se_doc_roots'],512)+b''.join(f.read(s[k],w) for k,w in fields)
    def without_cache(f,reu):
        handle=f.get('se_gc_handle',1);assert handle
        physical=f.ram[s['se_reu_map']+handle]
        assert physical and f.ram[s['se_reu_logical_owner']+handle]==f.ram[s['se_reu_physical_owner']+physical]==0xFE
        assert f.get('se_gc_epoch',2)==f.get('se_reu_epoch',2)
        data=bytearray(reu);start=physical*65536
        data[start:start+64]=bytes(64)
        for i in range(22):a=start+0x200+i*0x800;data[a:a+0x800]=bytes(0x800)
        return hashlib.sha256(data).hexdigest()
    for case in cases:
        ident=case['id'];ram=(out/'captures'/(ident+'-ram.bin')).read_bytes()
        colors=(out/'captures'/(ident+'-colors.bin')).read_bytes();reu=images[ident]
        f=Captured(s,ram,colors,e)
        assert len(reu)==16*1024*1024
        assert f.get('se_hot_caret')==case['caret'] and f.get('se_v_top')==case['top'],(ident,'canonical target/viewport')
        assert bool(f.get('se_sel_mark',1))==case['mark']
        if case['anchor'] is not None:assert f.get('se_sel_anchor')==case['anchor']
        if case['pref_valid']:
            assert f.get('se_n_preferred_valid',1)==2 and f.get('se_l_preferred')==case['preferred'],(ident,'preferredpixelX')
        assert not f.get('se_h_dirty',1) and f.get('se_h_current',4)==f.get('se_h_saved',4)
        state=source_state(f)
        if stable is None:stable=state
        assert stable==state,(ident,'navigation edited canonical/history state')
        current_catalog=ram[s['se_overlay_ids']:s['se_overlay_ids']+192]
        if catalog is None:catalog=current_catalog
        assert current_catalog==catalog,(ident,'overlaycatalog')
        if case['clipboard'] is not None:
            wanted=bytes.fromhex(case['clipboard'])
            assert f.get('se_clip_length')==len(wanted)
            assert object_bytes(f,reu,f.read(s['se_clip_token'],5),len(wanted))==wanted,(ident,'actualclipboardbytes')
        if case['ui']==3:
            listing=[f.read(s['se_fd_list_names']+i*16,f.read(s['se_fd_list_lengths']+i,1)[0]) for i in range(f.get('se_fd_list_count',1))]
            assert listing==directory,(ident,'actualdirectoryvsrawD81',listing,directory)
        # Source80 initially uses a different derived cache layout. Compare
        # strict whole16MiB across GEOS navigation groups, only masking the
        # authenticated declared GEOS page extents; copy is an explicit break.
        if case['mode']==3:
            digest=without_cache(f,reu)
            if case['clipboard'] is None:
                if before_copy is None:before_copy=digest
                assert before_copy==digest,(ident,'otherREUbeforecopy')
            else:
                if after_copy is None:after_copy=digest
                assert after_copy==digest,(ident,'otherREUaftercopy')
        observed.append(dict(id=ident,mode=case['mode'],caret=case['caret'],top=case['top'],
                             preferred=case['preferred'],clipboard=case['clipboard']))
    result=dict(status='passed',evidence=str(e),identity=json.loads((e/'freeze.json').read_text()),
        screenshots=len(cases),native_pixels=len(cases)*64000,attributes=len(cases)*1000,
        cases=observed,source_bytes=422,REU_bytes=16*1024*1024,shim_bytes=1024,catalog_bytes=192,
        scope='ActualD81FileOpen/IRQ-nativebytes/publicGEOSnavigation/clipboard/UI/nativeVICpixels; no physicalkeyboard orlatencyclaim.')
    (out/'navigation-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result


def execute(e):
    e=Path(e).resolve();n=scenario(e);plan=n.plan()
    assert len({x['id'] for x in plan['steps']})==len(plan['steps'])
    (n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n')
    (n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
    sources=[Path(__file__),Path(nav.__file__),Path(live.__file__),ROOT/'tests/test_geos_editor.py',ROOT/'tests/test_grid_editor_vice.py']
    with zipfile.ZipFile(e/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in sources:z.write(path,path.relative_to(ROOT))
    project=live.grid.synchronous_project(n.out);vice_plan.PROJECT=project
    build=subprocess.run(['dotnet','build',str(project),'--nologo'],capture_output=True,text=True,timeout=120)
    (n.out/'dotnet-build.log').write_text(build.stdout+build.stderr);assert build.returncode==0
    print('NATIVE '+str(e)+' steps='+str(len(n.steps))+' IRQbytes='+str(n.keys)+' screenshots='+str(len(n.cases)),flush=True)
    vice_plan.run_plan(plan,n.out);return evaluate(e)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path);ap.add_argument('--verify',type=Path);args=ap.parse_args()
    if args.verify:return evaluate(args.verify.resolve())
    if args.run:return execute(args.run)
    print('Prepared only. Requires frozenproduct/privateD81 +exclusive7700/text7800 grant; use --run PATH.')


if __name__=='__main__':main()
