"""Independent logical-line/pan oracle against the real async C11/editor path.

All renderer bytes and23 source anchors are derived from native source, never
from the product's row/cache tables. CPU proof only; no native video timing.
"""
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from editor_fixture import EditorFixture
from redraw_model import Screen,source40,screen_code,native_text,verify_screen

OUT=ROOT/'build/nowrap-result.json';OUT.unlink(missing_ok=True)
f=EditorFixture();frames=[];max_layout_steps=0;logical=b''

def line_starts(source):return [0]+[i+1 for i,b in enumerate(source) if b==13]
def line_at(source,caret):return bisect_right(line_starts(source),caret)-1
def line_end(source,start):
    end=source.find(b'\r',start)
    return len(source) if end<0 else end
def merged():
    data=f.document();base=f.get('se_hot_base')
    gap=f.read(0x9200,f.get('se_hot_left',2))+f.read(0x9200+f.get('se_hot_right',2),2048-f.get('se_hot_right',2))
    return data[:base]+gap+data[base+f.get('se_hot_old_length',2):]
def oracle(source,top,caret,pan):
    # Reuse independently specified shared chrome/PETSCII conversion, replacing
    # its entire body and row mapping with logical-line layout.
    base=source40(source,top,caret,marked=bool(f.get('se_sel_mark',1)),
                  anchor=f.get('se_sel_anchor'),pending=bool(f.get('se_hot_pending',1)),
                  dirty=bool(f.get('se_h_dirty',1)),error=f.get('se_e_error',1),
                  history_fault=bool(f.get('se_h_fault',1)),trimmed=bool(f.get('se_h_trimmed',2)))
    matrix=bytearray(base.matrix);colors=bytearray(base.colors)
    matrix[80:960]=bytes([32])*880;colors[80:960]=bytes([1])*880
    assert top==0 or source[top-1]==13,('top is not logical line start',top)
    lo,hi=sorted((f.get('se_sel_anchor'),caret)) if f.get('se_sel_mark',1) else (caret,caret)
    pos=top;anchors=[];visible_caret=None
    for row in range(22):
        anchors.append(pos);end=line_end(source,pos)
        for col in range(40):
            at=(row+2)*40+col;p=pos+pan+col
            if p>end:continue
            glyph=32 if p==end else screen_code(source[p]);color=1
            if lo<=p<hi:glyph^=128;color=3
            if p==caret and visible_caret is None:
                glyph=(32 if p==end else screen_code(source[p]))^128
                color=7 if f.get('se_sel_mark',1) else 3
                visible_caret=(row,col)
            matrix[at]=glyph;colors[at]=color
        pos=end+1 if end<len(source) else len(source)
    anchors.append(pos)
    return Screen(bytes(matrix),bytes(colors),tuple(anchors),visible_caret)
def paint(tag,*,allow_hidden=False):
    global max_layout_steps
    assert merged()==logical,(tag,'visible source')
    source_state={n:f.read(f.s[n],w) for n,w in [('se_doc_generation',2),('se_doc_length',3),
                  ('se_h_current',4),('se_h_saved',4),('se_hot_caret',3),('se_hot_pending',1)]}
    steps=0
    for attempt in range(5):
        r=f.call('se_editor_render');assert not r.p&1,(tag,'render',r.a)
        if r.a==0:break
        assert r.a==1 and f.get('se_e_job',1)==7,(tag,'async publication')
        while f.get('se_e_job',1):
            f.call('se_editor_service');steps+=1
            assert steps<30000,(tag,'layout bound')
        assert f.get('se_e_error',1)==0,(tag,hex(f.get('se_e_error',1)))
    else:raise AssertionError((tag,'render did not complete'))
    max_layout_steps=max(max_layout_steps,steps)
    top=f.get('se_v_top');caret=f.get('se_hot_caret');mode=f.get('se_l_mode',1)
    if mode:
        expected=oracle(logical,top,caret,f.get('se_l_pan'))
    else:
        expected=source40(logical,top,caret,marked=bool(f.get('se_sel_mark',1)),
                  anchor=f.get('se_sel_anchor'),pending=bool(f.get('se_hot_pending',1)),
                  dirty=bool(f.get('se_h_dirty',1)),error=f.get('se_e_error',1),
                  history_fault=bool(f.get('se_h_fault',1)),trimmed=bool(f.get('se_h_trimmed',2)))
    verify_screen(f.read(0x4000,1000),f.read(0xD800,1000),expected,tag=tag)
    actual=tuple(int.from_bytes(f.read(f.s['se_v_rows']+i*3,3),'little') for i in range(22))+(f.get('se_v_bottom'),)
    assert actual==expected.anchors,(tag,'23 row anchors',actual,expected.anchors)
    if expected.caret is None:
        assert allow_hidden and f.get('se_l_manual',1),(tag,'unexpected hidden caret')
        assert f.get('se_v_seen',1)==0
    else:
        assert f.get('se_v_seen',1)==1
        assert (f.get('se_v_caret_row',1),f.get('se_v_caret_col',1))==expected.caret
    assert f.get('se_doc_read_locks',1)==0 and f.get('se_n_owned',1)==0
    assert f.read(0xC600,1024)==f.shim
    for n,b in source_state.items():assert f.read(f.s[n],len(b))==b,(tag,'render mutated',n)
    frames.append(dict(tag=tag,mode=mode,pan=f.get('se_l_pan'),top=top,caret=caret,
                       caret_cell=expected.caret,layout_steps=steps))
def new_source(data,banks=1,physical=8):
    global logical
    logical=data;f.source(data,banks=banks,physical=physical)
    # Common fixture may have queued its initial asynchronous paint.
    f.settle();paint('source-wrap-default')
    assert f.get('se_l_mode',1)==0
def view(c,tag):
    before=merged();caret=f.get('se_hot_caret');saved=f.get('se_h_saved',4)
    pending=f.get('se_hot_pending',1)
    stable={n:f.read(f.s[n],w) for n,w in [('se_doc_generation',2),('se_h_current',4),
             ('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)]}
    f.command(c)
    assert merged()==before and f.get('se_hot_caret')==caret,(tag,'view changed source/caret')
    assert f.get('se_h_saved',4)==saved
    if not pending:
        for n,b in stable.items():assert f.read(f.s[n],len(b))==b,(tag,'view changed history',n)
def typed(text):f.typed(native_text(text))
def menu(letter):
    f.key(0x85);f.key(0x56);f.key(ord(letter))

try:
    lines=[b'START '+b'A'*130,b'tiny',b'',bytes(b for b in range(256) if b!=13),
           b'Z'*40,b'T'*41,b'line']+[bytes([65+i%26])*(5+(i*17)%180) for i in range(60)]
    initial=b'\r'.join(lines)+b'\r'
    new_source(initial)
    view(77,'nowrap-on');assert f.get('se_l_mode',1)==1;paint('logical-lines')
    # Manual pan keeps source/caret; it may intentionally hide the caret.
    view(75,'pan-right');assert f.get('se_l_pan')==20;paint('manual-right-hidden',allow_hidden=True)
    view(75,'pan-right-again');assert f.get('se_l_pan')==40;paint('manual-right40-hidden',allow_hidden=True)
    view(74,'pan-left');assert f.get('se_l_pan')==20;paint('manual-left20-hidden',allow_hidden=True)
    view(74,'pan-left-zero');view(74,'pan-left-clamped');assert f.get('se_l_pan')==0;paint('manual-left-clamp')
    view(75,'pan-before-cursor');f.command(2);paint('ordinary-right-reveals')
    assert f.get('se_hot_caret')==1 and not f.get('se_l_manual',1)
    f.position(100);paint('automatic-right-pan')
    assert f.get('se_l_pan')<=100<f.get('se_l_pan')+40
    # Independent vertical source-position model; retain preferred column100
    # across short/empty lines and21 logical-row pages.
    starts=line_starts(logical);row=0;preferred=100
    for tag,c,delta in [('down-short',37,1),('down-empty',37,1),('down-diverse',37,1),
                        ('up-empty',36,-1),('up-short',36,-1),('up-long',36,-1),
                        ('page-down21',39,21),('page-up21',38,-21)]:
        row+=delta;wanted=starts[row]+min(preferred,line_end(logical,starts[row])-starts[row])
        f.command(c);assert f.get('se_hot_caret')==wanted,(tag,f.get('se_hot_caret'),wanted)
        assert f.get('se_l_preferred')==preferred,(tag,'preferred24',f.get('se_l_preferred'))
        paint(tag)
    # Native routes to the same source-preserving command IDs.
    caret=f.get('se_hot_caret');f.key(0x8A);assert f.get('se_l_mode',1)==0;paint('F4-wrap')
    menu('W');assert f.get('se_l_mode',1)==1 and f.get('se_hot_caret')==caret;paint('View-W-nowrap')
    old=f.get('se_l_pan');menu('R');assert f.get('se_l_pan')==min(len(logical),old+20);paint('View-R',allow_hidden=True)
    menu('L');assert f.get('se_l_pan')==old;paint('View-L',allow_hidden=True)
    typed('wrap on');assert f.get('se_l_mode',1)==0;paint('F7-wrap-on')
    typed('wrap off');assert f.get('se_l_mode',1)==1;paint('F7-wrap-off')
    typed('pan right');paint('F7-pan-right',allow_hidden=True)
    typed('pan left');paint('F7-pan-left',allow_hidden=True)
    typed('wrap');assert f.get('se_l_mode',1)==0;paint('F7-toggle-wrap')
    view(77,'nowrap-before-selection')
    # Source selection includes hidden columns, controls and CR boundaries.
    a=20;b=starts[4]+3
    f.position(a);f.command(68);f.position(b);paint('selected-hidden-columns-and-CR')
    f.command(69);f.command(50);copied=logical[a:b]
    f.position(len(logical));f.command(71);logical+=copied;paint('EOF-native-paste')
    f.command(16);logical=initial;paint('undo-native-paste')
    f.command(17);logical=initial+copied;paint('redo-native-paste')
    # Pending input is rendered from the merged source; a pan may flush that
    # existing group but must add no extra edit, and one undo removes it.
    pending_base=b'long '+b'P'*150+b'\r\rshort\r'
    new_source(pending_base);view(77,'pending-nowrap');f.position(75)
    f.key(0xD8);logical=pending_base[:75]+bytes([0xD8])+pending_base[75:]
    assert f.get('se_hot_pending',1);paint('pending-merged-nowrap')
    view(75,'pan-flushes-existing-group');paint('pan-after-pending',allow_hidden=True)
    f.command(16);logical=pending_base;paint('one-undo-after-pending-pan')
    assert f.document()==pending_base
    # Empty document, trailing CR and all-empty row maps include exact EOF.
    for data in [b'',b'\r',b'\r\r',b'X'*40,b'X'*40+b'\r']:
        new_source(data);view(77,'edge-nowrap');paint('edge-'+data[:3].hex())
        f.command(35);paint('edge-EOF')
    # One >64KiB logical column, with short/blank following lines. Preferred
    # column must survive both individual moves and a21-row page roundtrip.
    long_lines=[b'L'*70010,b'short',b'']+[bytes([65+i%26])*(i%17) for i in range(35)]
    long_source=b'\r'.join(long_lines)+b'\r'
    new_source(long_source,banks=2,physical=8);f.position(70000);view(77,'large-nowrap');paint('column70000')
    lstarts=line_starts(long_source);r=0
    for tag,c,delta in [('large-down-short',37,1),('large-down-blank',37,1),
                        ('large-up-short',36,-1),('large-up-long',36,-1),
                        ('large-page-down',39,21),('large-page-up',38,-21)]:
        r+=delta;wanted=lstarts[r]+min(70000,len(long_lines[r]))
        f.command(c);assert f.get('se_hot_caret')==wanted,(tag,f.get('se_hot_caret'),wanted)
        assert f.get('se_l_preferred')==70000,(tag,f.get('se_l_preferred'))
    paint('preferred70000-roundtrip')
    assert f.get('se_l_pan')<=70000<f.get('se_l_pan')+40
    assert f.document()==long_source and f.read(0xC600,1024)==f.shim
    result=dict(status='passed',frames=frames,full_cells_checked=len(frames)*1000,
                anchors_checked=len(frames)*23,max_layout_steps=max_layout_steps,
                preferred_column70000=True,resident_sha256=f.report['sha256'],
                assets_sha256={n:hashlib.sha256(b).hexdigest() for n,b in f.assets.items()},
                shim_bytes_checked=1024,scope='Real emitted async editor/REU with independent source/logical-layout oracle; no native timing claim')
    OUT.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='frames'},indent=2))
except Exception as e:
    failure=dict(status='failed',error=repr(e),completed_frames=frames,
                 resident_sha256=f.report['sha256'],assets_sha256={n:hashlib.sha256(b).hexdigest() for n,b in f.assets.items()},
                 layout={n:f.get(n,w) for n,w in [('se_l_mode',1),('se_l_pan',3),('se_l_manual',1),
                          ('se_hot_caret',3),('se_v_top',3),('se_v_bottom',3),('se_e_error',1)]})
    OUT.write_text(json.dumps(failure,indent=2)+'\n');raise
finally:f.close()
