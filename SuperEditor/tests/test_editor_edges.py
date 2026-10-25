"""Actual C8 edge planner and resident flush/reload/retry integration.

Arithmetic fixtures are independent planner inputs; actual editing cases use
real document/hot/history services. No VICE, screen or physical-key claim.
"""
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from editor_fixture import EditorFixture
from overlays import HEADER

f=EditorFixture()
planner_cases=0
max_planner=0
pipeline=[]

def reu_hash():
    return hashlib.sha256(bytes(f.m.lib.zeropage_peddle_read_reu(f.m.handle,i)
                               for i in range(16*65536))).hexdigest()

def merged():
    source=f.document();base=f.get('se_hot_base')
    span=f.read(0x9200,f.get('se_hot_left',2))+f.read(0x9200+f.get('se_hot_right',2),2048-f.get('se_hot_right',2))
    return source[:base]+span+source[base+f.get('se_hot_old_length',2):]

def hot(command,count):
    for _ in range(count):
        regs=f.call('se_hot_call',command)
        assert not regs.p&1,(command,regs.a)

def planner(command,caret,length,base,old,pending):
    global planner_cases,max_planner
    sentinel=0xABCDEF
    for name,value,width in [('se_e_command',command,1),('se_hot_caret',caret,3),
                             ('se_doc_length',length,3),('se_hot_base',base,3),
                             ('se_hot_old_length',old,2),('se_hot_pending',pending,1),
                             ('se_e_target',sentinel,3),('se_e_after_load',0xA5,1),
                             ('se_e_key',0xD8,1),('se_hot_byte',0xD8,1)]:
        f.put(name,value,width)
    hot_before=f.read(f.s['se_hot_state_start'],f.s['se_hot_state_end']-f.s['se_hot_state_start'])
    roots=f.read(f.s['se_doc_roots'],512)
    foreign=f.read(f.s['se_n_start'],f.s['se_n_end']-f.s['se_n_start'])
    f.put('se_overlay_frame',6,1)
    regs,used=f.m.call(f.s['se_overlay_call'],a=8,x=1)
    assert not regs.p&1,regs.a
    max_planner=max(max_planner,used)
    target=sentinel;retry=0xA5
    if command==1:
        action=0 if caret==0 else 1
        if caret:target=caret-1
    else:
        target=caret
        if command==2:
            action=0 if caret==length else 1
            if action:target=caret+1
        elif command==3 and caret==0:action=0
        elif command==4 and base+old==length:action=0
        else:
            retry=4 if command==3 else 5
            action=2 if pending else 1
    assert (regs.a,f.get('se_e_target'),f.get('se_e_after_load',1))==(action,target,retry),(command,caret,length,base,old,pending,regs.a,target,retry)
    assert f.read(f.s['se_hot_state_start'],len(hot_before))==hot_before
    assert f.read(f.s['se_doc_roots'],512)==roots
    assert f.read(f.s['se_n_start'],len(foreign))==foreign
    assert f.get('se_doc_read_locks',1)==3 and f.get('se_n_owned',1)==1
    assert f.get('se_e_key',1)==f.get('se_hot_byte',1)==0xD8
    assert f.read(0xC600,1024)==f.shim
    planner_cases+=1

def check(tag,expected,caret):
    assert merged()==expected,(tag,len(merged()),len(expected))
    assert f.get('se_hot_caret')==caret,(tag,f.get('se_hot_caret'),caret)
    assert f.get('se_e_after_load',1)==0 and f.get('se_e_job',1)==0
    assert f.read(0xC600,1024)==f.shim
    pipeline.append(dict(tag=tag,bytes=len(expected),caret=caret,pending=f.get('se_hot_pending',1)))

try:
    f.put('se_doc_read_locks',3,1)
    f.put('se_n_owned',1,1)
    initial_reu=reu_hash()
    for length in [0,1,255,256,1024,1500,65535,65536,70000,1048576,0xFFFFFF]:
        for command in [1,2,3,4]:
            for pending in ([0] if command<3 else [0,1]):
                old=min(1024,length);base=length-old
                caret=base if command in [1,3] else length
                planner(command,caret,length,base,old,pending)
    # Regression: pending caret numerically equals committed EOF, but the old
    # window ends at1024 and committed bytes still follow it through1500.
    planner(4,1500,1500,0,1024,1)
    rng=random.Random(0xED6E)
    for _ in range(160):
        length=rng.randrange(1,1048577);base=rng.randrange(length)
        old=min(rng.randrange(1,1025),length-base)
        command=rng.randrange(1,5);pending=rng.randrange(2) if command>=3 else 0
        caret=base if command in [1,3] else base+old
        planner(command,caret,length,base,old,pending)
    assert reu_hash()==initial_reu,'planner wrote REU'

    # Actual editor cache-boundary movement preserves the complete source.
    source=bytes((i*17+65)&255 for i in range(4096))
    f.source(source);f.position(1024);hot(6,512);f.key(0x9D)
    check('left-recenter',source,511)
    f.source(source);f.position(512);hot(7,512);f.key(0x1D)
    check('right-recenter',source,1025)
    f.source(source);f.position(1024);hot(6,512);f.key(0x14)
    check('back-recenter-once',source[:511]+source[512:],511)
    f.source(source);f.position(512);hot(7,512);f.command(4)
    check('delete-recenter-once',source[:1024]+source[1025:],1024)

    # A pending forward delete at the left boundary is committed before a
    # backspace retries. The new backspace must run once after the reload.
    f.source(source);f.position(1024);hot(6,512);hot(5,1);f.key(0x14)
    check('pending-back-flush-reload-once',source[:511]+source[513:],511)
    # A pending insertion makes caret==committed length without reaching true
    # visible EOF. Forward delete must remove the following original byte.
    source=b'R'*1500
    f.source(source);hot(7,1024)
    for _ in range(476):
        f.put('se_hot_byte',0xD8,1);hot(3,1)
    assert f.get('se_hot_caret')==f.get('se_doc_length')==1500
    f.command(4)
    check('pending-false-eof-delete',source[:1024]+bytes([0xD8])*476+source[1025:],1500)

    f.source(b'');f.key(0x9D);f.key(0x1D);f.key(0x14);f.command(4)
    check('empty-boundary-noops',b'',0)
    # Existing gap-full safe point remains resident and retains the native byte.
    f.source(b'')
    for _ in range(2048):
        f.put('se_hot_byte',65,1);hot(3,1)
    f.key(0xD8)
    check('full-gap-original-byte-once',b'A'*2048+bytes([0xD8]),2049)

    # Corrupt C8 admission after eviction must not cancel a foreign navigation
    # lease/frame. The resident error path preserves pending source/native byte.
    f.source(b'edge failure'*300)
    f.key(0x85);f.key(3) #C7 active,so next C8 request reloads
    index=next(i for i in range(12) if f.m.read(f.s['se_overlay_ids']+i)==8 and f.m.read(f.s['image_slot']+i)==1)
    original=f.assets['navigate'][HEADER+20]
    def patch(value):
        f.put('se_reu_logical',f.get('se_overlay_asset',1),1)
        f.put('se_reu_offset',index*4096+20,2);f.put('se_reu_length',1,2);f.put('se_reu_c64',0x5000,2)
        f.m.write(0x5000,value);assert not f.call('se_reu_copy',0).p&1
    patch(original^1)
    f.put('se_doc_read_locks',3,1);f.put('se_n_owned',1,1);f.put('se_v_nav_busy',1,1)
    f.put('se_e_command',3,1);f.put('se_e_key',0xD8,1);f.put('se_hot_byte',0xD8,1)
    old=f.document();hot_before=f.read(0x9200,2048)
    regs=f.call('edge')
    assert regs.p&1 and regs.a==f.get('se_e_error',1)==0x14
    assert f.get('se_doc_read_locks',1)==3 and f.get('se_n_owned',1)==1 and f.get('se_v_nav_busy',1)==1
    assert f.document()==old and f.read(0x9200,2048)==hot_before
    assert f.get('se_e_key',1)==f.get('se_hot_byte',1)==0xD8
    patch(original)
    assert f.read(0xC600,1024)==f.shim

    removed=251-(f.s['gap_full']-f.s['edge'])
    assert removed>=150,removed
    result=dict(status='passed',prg_sha256=f.report['sha256'],resident_binding=f.report['resident_binding']['digest'],
                planner_cases=planner_cases,pipeline_cases=pipeline,read_only_planner_reu_bytes=16*65536,
                foreign_lease_preserved_on_reload_failure=True,native_byte_retry_exact_once=True,
                reserved_shim_bytes=1024,new_bss_bytes=0,new_zp_bytes=0,
                former_edge_bytes=251,resident_edge_bytes=f.s['gap_full']-f.s['edge'],resident_code_bytes_freed=removed,
                core_end=f.report['cold_end_exclusive'],free_core_bytes=0x4000-f.report['cold_end_exclusive'],
                navigate_payload_bytes=len(f.assets['navigate'])-HEADER,max_planner_instructions_including_reload=max_planner,
                limitations='Actual emitted editor/services; arithmetic fixtures independent; no VICE/cycle/physical-key claim')
    (ROOT/'build/editor-edges-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
finally:f.close()
