"""Known editor publication must defeat16-bit renderer/index generation alias.

Numeric generation is forced toFFFF only in synthetic setup, with matching live
service contexts; the tested block/replay/hot publication is actual emitted code
and wraps it to0. Cached generation0 represents an ancient unpainted cache alias.
"""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from editor_fixture import EditorFixture
from redraw_model import source40,verify_screen,native_text

OUT=ROOT/'build/publication-wrap-result.json'
OUT.unlink(missing_ok=True)
f=EditorFixture();results=[];screens=0
original=b''.join(bytes([65+i%26])*39+b'\r' for i in range(500))
changed=original[:100]+b'\r'+original[101:]
def screen(data,tag):
    global screens
    r=f.call('se_editor_render');assert not r.p&1,(tag,hex(r.a))
    expected=source40(data,f.get('se_v_top'),f.get('se_hot_caret'),
                      marked=bool(f.get('se_sel_mark',1)),anchor=f.get('se_sel_anchor'),
                      pending=bool(f.get('se_hot_pending',1)),dirty=bool(f.get('se_h_dirty',1)))
    verify_screen(f.read(0x4000,1000),f.read(0xD800,1000),expected,tag=tag)
    assert f.read(0xC600,1024)==f.shim
    assert f.read(f.s['se_overlay_busy'],2)==b'\0\0'
    screens+=1
def starts(data):return [0]+[i+1 for i,c in enumerate(data) if c==13]
def index(data,tag):
    if not f.get('se_i_ready',1):
        assert f.get('se_n_cache_count',1)==0,(tag,'invalid index has live line cache')
        return
    assert f.get('se_i_generation',2)==f.get('se_doc_generation',2)
    count=f.get('se_i_count',1);assert 1<=count<=128
    records=[]
    for ordinal in range(count):
        b=f.read(f.s['se_index_table']+ordinal*9,9)
        records.append(tuple(int.from_bytes(b[i:i+3],'little') for i in [0,3,6]))
    records.append((f.get('se_i_scan'),f.get('se_i_line'),f.get('se_i_number')))
    for offset,line,number in records:
        assert 0<=offset<=len(data),(tag,offset)
        wanted_number=data[:offset].count(13)
        wanted_line=data.rfind(b'\r',0,offset)+1
        assert (line,number)==(wanted_line,wanted_number),(tag,'stale checkpoint/frontier',
                                                               (offset,line,number),(wanted_line,wanted_number))
    line_starts=starts(data);n=f.get('se_n_cache_count',1)
    assert n<=25
    for ordinal in range(n):
        slot=(f.get('se_n_cache_head',1)+ordinal)%25
        at=int.from_bytes(f.read(f.s['se_n_cache_starts']+slot*3,3),'little')
        line_number=f.get('se_n_cache_base')+ordinal
        assert at==line_starts[line_number],(tag,'stale line ring',line_number,at,line_starts[line_number])
def build_snapshot(data):
    f.command(35);index(data,'prepared-bottom')
    assert f.get('se_i_count',1)>=3 and f.get('se_i_scan')==len(data)
    f.position(0);f.put('se_v_top',0);f.put('se_r_valid',0,1)
    screen(data,'prepared-full')
def alias_at_wrap():
    # Synthetic context rebasing avoids65,536 expensive edits while retaining
    # actual published source/token ownership and actual wrap on the next edit.
    for name in ['se_doc_generation','se_hot_generation','se_h_generation']:
        f.put(name,0xFFFF,2)
    f.put('se_r_generation',0,2);f.put('se_i_generation',0,2)
    assert f.get('se_r_valid',1)==1 and f.get('se_i_ready',1)==1
def select_replace():
    f.position(100);f.command(68);f.position(101);f.key(13)
def publication(data,command,tag):
    alias_at_wrap()
    if command=='block':f.key(13)
    else:f.command(command)
    assert f.get('se_doc_generation',2)==0,(tag,'actual generation did not wrap')
    assert f.document()==data,(tag,'published bytes')
    assert f.get('se_r_valid',1)==0,(tag,'known publication retained ancient render cache')
    index(data,tag+'-after-publication')
    screen(data,tag)
    assert f.get('se_r_path',1)==0,(tag,'stale cache reused')
    assert f.get('se_r_rows',1)==22
    # Query beyond the8192/16384 checkpoints; a stale logical line number
    # returns a plausible but wrong source position with no transport error.
    f.typed(native_text('goto 450'))
    assert f.get('se_hot_caret')==starts(data)[449],(tag,'goto450',f.get('se_hot_caret'),starts(data)[449])
    index(data,tag+'-goto450')
    results.append(dict(tag=tag,wrapped_generation=0,render_rows=22,
                        goto450=f.get('se_hot_caret'),index_records=f.get('se_i_count',1)))
try:
    f.source(original,banks=1,physical=8)
    build_snapshot(original)
    f.position(100);f.command(68);f.position(101)
    publication(changed,'block','selected-block-replacement')

    # Real journal from the preceding replacement is replayed in both directions.
    build_snapshot(changed)
    publication(original,16,'undo-replay')
    build_snapshot(original)
    publication(changed,17,'redo-replay')

    # Same generation can mean a known aliased publication. Conservatively
    # resetting also remains safe if this hook is called without source change.
    build_snapshot(changed)
    before=f.document();generation=f.get('se_doc_generation',2)
    f.call('se_index_changed') # internal invalidation hook has no carry-result ABI
    assert f.get('se_i_ready',1)==0 and f.get('se_n_cache_count',1)==0
    assert f.document()==before and f.get('se_doc_generation',2)==generation
    screen(changed,'same-generation-conservative-reset')
    assert f.get('se_r_path',1)==1
    f.typed(native_text('goto 450'))
    assert f.get('se_hot_caret')==starts(changed)[449]
    index(changed,'same-generation-rebuilt')
    results.append(dict(tag='same-generation-no-op-index-hook',source_unchanged=True,
                        render_path=1,goto450=f.get('se_hot_caret')))

    # A known hot flush publishes bytes already painted. It must retain the
    # source revision fast path acrossFFFF→0 instead of forcing a full redraw.
    f.source(original,banks=1,physical=8);build_snapshot(original);f.position(100)
    for name in ['se_doc_generation','se_hot_generation','se_h_generation','se_i_generation']:
        f.put(name,0xFFFF,2)
    f.put('se_r_valid',0,1);screen(original,'hot-before-wrap')
    f.key(0xD8)
    pending=original[:100]+bytes([0xD8])+original[100:]
    screen(pending,'painted-hot-before-flush')
    assert f.get('se_r_valid',1)==1 and f.get('se_r_generation',2)==0xFFFF
    # An aliased index must still be reset; the separately painted renderer can
    # advance its generation because all visible bytes/revision were verified.
    f.put('se_i_generation',0,2)
    f.command(1)
    assert f.get('se_doc_generation',2)==0
    assert f.document()==pending and f.get('se_hot_pending',1)==0
    assert f.get('se_r_valid',1)==1 and f.get('se_r_generation',2)==0
    screen(pending,'known-painted-hot-flush')
    assert f.get('se_r_path',1)==1 and f.get('se_r_rows',1)==0
    index(pending,'known-painted-hot-flush-index')
    results.append(dict(tag='known-painted-hot-flush',wrapped_generation=0,
                        render_path=1,rows=0,source_bytes=len(pending)))
    assert f.read(0xC600,1024)==f.shim
    result=dict(status='passed',cases=results,full_screens_checked=screens,
                resident_sha256=f.report['sha256'],
                asset_sha256={n:hashlib.sha256(f.assets[n]).hexdigest() for n in ['text40','window','eedit','eplay','block','navigate']},
                shim_bytes_checked=1024,
                scope='Actual editor publications and screen/index oracle; synthetic generation rebase/cache alias, no claim of65,536-edit soak')
    OUT.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:f.close()
