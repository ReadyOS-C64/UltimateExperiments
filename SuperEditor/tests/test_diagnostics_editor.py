"""Integrated Help/D/F7 diagnostics, pending CRC, ownership and popup integrity."""
import binascii
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_fixture import EditorFixture
from redraw_model import source40,verify_screen,native_text
from diagnostics_model import diagnostic_popup
from overlays import HEADER

f=EditorFixture();cases=[];max_step=0
def reu():return hashlib.sha256(bytes(f.m.lib.zeropage_peddle_read_reu(f.m.handle,i) for i in range(16*65536))).hexdigest()
def merged():
    data=f.document();base=f.get('se_hot_base')
    span=f.read(0x9200,f.get('se_hot_left',2))+f.read(0x9200+f.get('se_hot_right',2),2048-f.get('se_hot_right',2))
    return data[:base]+span+data[base+f.get('se_hot_old_length',2):]
def key(byte):
    f.put('se_e_key',byte,1);f.put('se_e_mods',0,1)
    return f.call('se_editor_input')
def typed(text):
    key(0x88)
    for value in text:key(value)
    return key(13)
def preserved():
    return (f.read(f.s['se_doc_roots'],512)+f.read(f.s['se_doc_generation'],5)
            +f.read(f.s['se_hot_state_start'],f.s['se_hot_state_end']-f.s['se_hot_state_start'])
            +f.read(0x9200,2048)+f.read(f.s['se_h_state_start'],f.s['se_h_state_end']-f.s['se_h_state_start'])
            +f.read(0x8D00,1152)+f.read(0x9180,123))
def start(route):
    if route=='typed':typed(b'DIAG')
    elif route=='menu':
        for value in [0x85,ord('H'),ord('D')]:key(value)
    else:f.call('se_editor_command',78)
    assert f.get('se_e_job',1)==8 and f.get('se_diag_active',1)==1 and f.get('se_diag_owned',1)==1
def drain(model,foreign=0,evict=False):
    global max_step
    old=preserved();steps=0
    while f.get('se_e_job',1):
        assert f.get('se_e_job',1)==8
        assert f.get('se_doc_read_locks',1)==foreign+1
        pos=f.get('se_diag_pos')
        if evict and steps%31==0:
            for _ in range(2):
                f.put('se_overlay_frame',1,1)
                regs,_=f.m.call(f.s['se_overlay_call'],a=7,x=1);assert not regs.p&1
        regs,used=f.m.call(f.s['se_editor_service']);max_step=max(max_step,used)
        assert f.get('se_e_error',1)==0,(regs.a,f.get('se_e_error',1))
        assert 0<=f.get('se_diag_pos')-pos<=128
        assert preserved()==old
        steps+=1;assert steps<12000
    d=f.read(0x8800,128)
    assert d[:8]==b'DGS1\x01\x80\x02\x01'
    assert int.from_bytes(d[8:11],'little')==len(model)
    assert int.from_bytes(d[22:24],'little')==binascii.crc_hqx(model,0xFFFF)
    assert f.get('se_doc_read_locks',1)==foreign and f.get('se_diag_owned',1)==0
    assert f.get('se_e_ui',1)==1 and f.get('se_e_menu',1)==7
    return d,steps
def stop():
    i=f.get('se_input_tail',1)
    f.m.write(f.s['se_input_chars']+i,3);f.m.write(f.s['se_input_mods']+i,0)
    f.put('se_input_head',(i+1)&63,1);f.call('se_editor_service')

try:
    # Actual pending edit remains uncommitted throughout typing,diagnostics and
    # C7 popup paint. Length exceeds64KiB and source covers every native byte.
    original=(bytes(range(256))*274)[:70000]
    f.source(original)
    pending=native_text('DiAg')+b'\r'+bytes(range(160,256))
    for value in pending:f.key(value)
    model=pending+original
    generation=f.get('se_doc_generation',2);node=f.get('se_h_current',4)
    before=reu();stable=preserved()
    start('typed');d,steps=drain(model,evict=True)
    assert d[16:19]==b'\x01\x01\x00'
    assert f.get('se_doc_generation',2)==generation and f.get('se_h_current',4)==node
    assert f.document()==original and merged()==model and preserved()==stable
    # R1 body rendering occurs before C7;the128-byte descriptor must survive it.
    f.render();assert f.read(0x8800,128)==d
    expected=diagnostic_popup(source40(model,f.get('se_v_top'),len(pending),pending=True),d)
    verify_screen(f.read(0x4000,1000),f.read(0xD800,1000),expected,tag='integrated diagnostics popup')
    assert reu()==before
    for value in [0x11,0x91,0x1D,0x9D,ord('A'),13,0x14]:
        key(value);assert f.get('se_e_ui',1)==1 and f.get('se_e_menu',1)==7
        assert f.read(0x8800,128)==d and preserved()==stable
    key(3);f.render();verify_screen(f.read(0x4000,1000),f.read(0xD800,1000),source40(model,f.get('se_v_top'),len(pending),pending=True),tag='diagnostics restores document')
    cases.append(dict(tag='pending-native-64k-popup',source_bytes=len(model),steps=steps,complete_cells=1000))
    start('menu');d2,steps=drain(model);assert d2[22:24]==d[22:24]
    f.render();key(0x8B);assert f.get('se_e_menu',1)==6
    key(0x8B);assert f.get('se_e_ui',1)==0
    cases.append(dict(tag='Help-D-and-global-F6',steps=steps))

    # Partial cancel,repeat BEGIN and foreign counted lease must be independent.
    assert not f.call('se_doc_read_acquire').p&1
    start('direct');f.call('se_editor_service');partial=f.get('se_diag_pos');assert 0<partial<=128
    owned=f.read(f.s['se_diag_frame_start'],f.s['se_diag_frame_end']-f.s['se_diag_frame_start'])
    result=f.call('se_diag_call',1);assert result.p&1 and result.a==0x78
    assert f.read(f.s['se_diag_frame_start'],len(owned))==owned
    stop();assert f.get('se_e_job',1)==0 and f.get('se_diag_owned',1)==0
    assert f.get('se_doc_read_locks',1)==1 and f.read(0x8800+6,1)==b'\x03'
    assert preserved()==stable
    assert not f.call('se_doc_read_release').p&1
    cases.append(dict(tag='partial-STOP-foreign-lease',scanned=partial))

    # C11 missing on continuation must release our lease through resident code,
    # keeping the foreign lease and the pending source untouched.
    assert not f.call('se_doc_read_acquire').p&1
    start('direct');f.call('se_editor_service')
    index=next(i for i in range(12) if f.m.read(f.s['se_overlay_ids']+i)==11 and f.m.read(f.s['image_slot']+i)==1)
    f.m.write(f.s['se_overlay_ids']+index,0)
    f.call('se_editor_service')
    assert f.get('se_e_error',1)==0x17 and f.get('se_e_job',1)==0
    assert f.get('se_doc_read_locks',1)==1 and f.get('se_diag_owned',1)==0 and f.get('se_diag_active',1)==0
    assert f.read(0x8800+6,1)==b'\x04' and f.read(0x8800+27,1)==b'\x17'
    assert preserved()==stable and merged()==model
    f.m.write(f.s['se_overlay_ids']+index,11)
    assert not f.call('se_doc_read_release').p&1
    f.put('se_e_error',0,1)
    cases.append(dict(tag='missing-C11-owned-cleanup',scanned=partial))

    # Context error plus a successful rerun demonstrate independent lifetime.
    start('direct');f.call('se_editor_service')
    revision=f.get('se_r_revision',4);f.put('se_r_revision',revision+1,4)
    f.call('se_editor_service');assert f.get('se_e_error',1)==0x79
    assert f.get('se_doc_read_locks',1)==0 and f.get('se_diag_owned',1)==0
    f.put('se_r_revision',revision,4);f.put('se_e_error',0,1)
    start('direct');d3,steps=drain(model);assert d3[22:24]==d[22:24]
    key(3);assert reu()==before and preserved()==stable
    assert f.read(0xC600,1024)==f.shim
    result=dict(status='passed',prg_sha256=f.report['sha256'],resident_binding=f.report['resident_binding']['digest'],
                asset_sha256={n:hashlib.sha256(v).hexdigest() for n,v in f.assets.items()},cases=cases,
                independent_crc='binascii.crc_hqx/CCITT-FALSE',pending_source_bytes=len(model),
                complete_popup_and_restored_screen_cells=2000,new_zp_bytes=0,
                source_history_hot_index_nav_immutable=True,read_only_reu_bytes=16*65536,
                partial_cancel_foreign_lease_preserved=True,failed_C11_continuation_cleanup=True,
                max_service_instructions=max_step,shim_bytes=1024,
                core_end=f.report['cold_end_exclusive'],state_bytes=f.report['state_bytes'],
                c7_bytes=len(f.assets['menu40'])-HEADER,c11_bytes=len(f.assets['layout'])-HEADER,
                limitations='Actual editor CPU/overlay pipeline; native VICE/pixels/keyboard proof separate')
    (ROOT/'build/diagnostics-editor-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
finally:f.close()
