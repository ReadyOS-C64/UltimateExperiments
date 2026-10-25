"""Independent replay viewport-context contract on frozen actual editor code.

Source setup uses the existing provider fixture. Clipboard creation, selected
paste and replay use only public editor commands; no caret/map injections.
"""
from bisect import bisect_right
from datetime import datetime,timezone
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import editor_fixture
import cpu_editor
from redraw_model import source40,native_text,verify_screen
from navigation_model import visual_rows
spec=importlib.util.spec_from_file_location('native_logical_oracle',ROOT/'tests/test_layout_vice.py')
logical=importlib.util.module_from_spec(spec);spec.loader.exec_module(logical)


def layout(source,mode):
    return logical.line_starts(source) if mode else [start for start,end in visual_rows(source)]

def context(source,caret,mode):
    starts=layout(source,mode);index=bisect_right(starts,caret)-1
    return starts[max(0,index-21)]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--frozen',type=Path,required=True);parser.add_argument('--minimal',action='store_true');args=parser.parse_args()
    frozen=args.frozen.resolve();assert (frozen/'build/editor.prg').exists()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=frozen/'runs'/stamp;out.mkdir(parents=True)
    for name in ['tests/test_replay_viewport.py','tests/test_layout_vice.py','tools/redraw_model.py','tools/navigation_model.py','tools/editor_fixture.py','tools/cpu_editor.py']:
        dest=out/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    editor_fixture.ROOT=frozen;cpu_editor.ROOT=frozen
    f=editor_fixture.EditorFixture();frames=[];failures=[];current=b'';family='';max_steps=0
    report=f.report;assert hashlib.sha256((frozen/'build/editor.prg').read_bytes()).hexdigest()==report['sha256']
    def state():
        fields={'se_hot_caret':3,'se_v_top':3,'se_v_bottom':3,'se_v_length':3,'se_v_seen':1,'se_v_caret_row':1,'se_v_caret_col':1,'se_r_valid':1,'se_r_length':3,'se_r_generation':2,'se_doc_generation':2,'se_doc_length':3,'se_h_current':4,'se_h_saved':4,'se_l_mode':1,'se_l_pan':3,'se_e_job':1,'se_e_error':1,'se_sel_mark':1}
        return {name:f.get(name,width) for name,width in fields.items() if name in f.s}
    def cmd(command):
        nonlocal max_steps
        steps=f.command(command);max_steps=max(max_steps,steps);f.render()
    def key(value):
        nonlocal max_steps
        steps=f.key(value);max_steps=max(max_steps,steps);f.render()
    def check(tag,caret,*,want_context=False,top=None,marked=False,anchor=0,before=None):
        tag=family+'-'+tag;f.render();actual=state();starts=layout(current,f.get('se_l_mode',1))
        expected_top=context(current,caret,f.get('se_l_mode',1)) if want_context else top
        row=bisect_right(starts,caret)-1
        item=dict(id=tag,source_bytes=len(current),source_sha256=hashlib.sha256(current).hexdigest(),expected_caret=caret,expected_top=expected_top,expected_context_rows=min(21,row) if want_context else None,before=before,actual=actual)
        try:
            assert f.document()==current,(tag,'complete source changed')
            assert f.get('se_hot_caret')==caret,(tag,'caret',f.get('se_hot_caret'),caret)
            assert bool(f.get('se_sel_mark',1))==marked,(tag,'selection')
            assert actual['se_v_top'] in starts,(tag,'top not true global row')
            if actual['se_l_mode']:
                expected=logical.logical_screen(current,actual['se_v_top'],caret,actual['se_l_pan'],marked=marked,anchor=anchor,dirty=bool(f.get('se_h_dirty',1)))
            else:expected=source40(current,actual['se_v_top'],caret,marked=marked,anchor=anchor,dirty=bool(f.get('se_h_dirty',1)))
            verify_screen(f.read(0x4000,1000),f.read(0xD800,1000),expected,tag=tag)
            anchors=tuple(int.from_bytes(f.read(f.s['se_v_rows']+i*3,3),'little') for i in range(22))+(f.get('se_v_bottom'),)
            assert anchors==expected.anchors,(tag,'22starts+bottom')
            assert expected.caret is not None and actual['se_v_seen']==1,(tag,'caret hidden')
            assert (actual['se_v_caret_row'],actual['se_v_caret_col'])==expected.caret
            assert f.read(0xC600,1024)==f.shim,(tag,'ReadyOS shim')
            assert f.get('se_doc_read_locks',1)==f.get('se_n_owned',1)==f.get('se_e_job',1)==f.get('se_e_error',1)==0
            if expected_top is not None:assert actual['se_v_top']==expected_top,(tag,'viewport context',actual['se_v_top'],expected_top)
            item['status']='passed'
        except AssertionError as error:
            item['status']='failed';item['error']=str(error);failures.append(item)
            dest=out/tag;dest.mkdir();(dest/'ram.bin').write_bytes(f.read(0,65536));(dest/'source.petscii').write_bytes(current)
            (dest/'snapshot.json').write_text(json.dumps(item,indent=2)+'\n')
        frames.append(item);print(item['status'].upper(),tag,'top',actual['se_v_top'],'expected',expected_top,'caret',caret,flush=True)
    def source(data,mode,tag,banks=1,physical=8):
        nonlocal current,family
        current=data;family=('lines-' if mode else 'wrap-')+tag;f.source(data,banks=banks,physical=physical)
        if mode:cmd(77)
        check('initial',0,top=0)
    def copy_page():
        cmd(34);key(0x89);cmd(39);at=layout(current,f.get('se_l_mode',1))[21]
        assert f.get('se_hot_caret')==at;cmd(69);key(3)
        return current[:at]
    def eof_case(data,mode,tag):
        nonlocal current
        source(data,mode,tag);clip=copy_page();cmd(35);check('bottom',len(current),want_context=True)
        old=current;before=state();cmd(71);current+=clip;check('paste',len(current),want_context=True,before=before)
        # A valid in-range map must stay fixed while the caret moves up/down.
        kept=f.get('se_v_top');caret=len(current);index=bisect_right(layout(current,mode),caret)-1
        for suffix,delta,command in [('up1',-1,36),('up2',-1,36),('down1',1,37),('down2',1,37)]:
            index+=delta;caret=layout(current,mode)[index];cmd(command);check('preserve-'+suffix,caret,top=kept)
        before=state();cmd(16);current=old;check('undo',len(current),want_context=True,before=before)
        before=state();cmd(17);current=old+clip;check('redo',len(current),want_context=True,before=before)
        before=state();cmd(16);current=old;check('undo-again',len(current),want_context=True,before=before)
    def selected_case(data,mode,tag,line,shorter=False,reverse=False,large=False):
        nonlocal current
        source(data,mode,tag,banks=2 if large else 1,physical=16 if large else 8)
        if shorter:
            cmd(34);key(0x89);cmd(2);cmd(2);cmd(69);key(3);clip=current[:2]
        else:clip=copy_page()
        f.typed(('GOTO '+str(line)).encode('ascii'));f.render()
        start=logical.line_starts(current)[line-1];end=logical.line_end(current,start);assert f.get('se_hot_caret')==start
        if reverse:cmd(33);key(0x89);cmd(32);before_caret=start;anchor=end
        else:key(0x89);cmd(33);before_caret=end;anchor=start
        assert not large or before_caret>65535
        check('selection',before_caret,marked=True,anchor=anchor)
        old=current;before=state();cmd(71);current=old[:start]+clip+old[end:];after=start+len(clip)
        check('selected-paste',after,want_context=True,before=before)
        before=state();cmd(16);current=old;check('selected-undo',before_caret,want_context=True,before=before)
        before=state();cmd(17);current=old[:start]+clip+old[end:];check('selected-redo',after,want_context=True,before=before)
    try:
        minimal=native_text(''.join(('Ab\r' if i%2==0 else 'cD\r') for i in range(22)))
        for mode in [0,1]:eof_case(minimal,mode,'minimal66-EOF')
        if not args.minimal:
            lengths=[0,6,39,40,41,79,80,81]
            varied=b'\r'.join((native_text(f'Row{i:02d} ')[:lengths[i%8]]+bytes([0xC1+i%26])*max(0,lengths[i%8]-6)) for i in range(64))+b'\r'
            for mode in [0,1]:
                eof_case(varied,mode,'mixed-wrap-CR-EOF')
                selected_case(varied,mode,'selected-longer',30)
                selected_case(varied,mode,'selected-shorter-reverse',30,shorter=True,reverse=True)
            large=b'\r'.join(native_text(f'Line{i:04d} ')+bytes([0xC1+i%26])*54 for i in range(1200))+b'\r'
            assert len(large)>70000
            for mode in [0,1]:selected_case(large,mode,'selected24bit-reverse',1100,shorter=True,reverse=True,large=True)
        result=dict(status='failed' if failures else 'passed',frozen_build=str(frozen),run=str(out),prg_sha256=report['sha256'],resident_binding=report['resident_binding']['digest'],asset_sha256={n:hashlib.sha256(b).hexdigest() for n,b in f.assets.items()},frames=frames,failure_count=len(failures),failed_ids=[x['id'] for x in failures],max_service_steps=max_steps,max_service_instructions=f.max_service,shim_bytes_verified=1024,scope='Actual public CPU editor/REU source/clipboard/history pipeline, independent21-preceding-row context and complete source/screens/23anchors. Initial source setup uses provider fixture. No native/video/timing/physical-key proof.')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['frames','asset_sha256']},indent=2))
        if failures:raise SystemExit(1)
    finally:f.close()

if __name__=='__main__':main()
