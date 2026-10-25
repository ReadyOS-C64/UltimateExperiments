"""Cancellation,allocation,reload and applied-fault contracts in the real block UI."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_fixture import EditorFixture
from overlays import HEADER
from run_vice import native_screen_text
f=EditorFixture();path=ROOT/'build/selection-faults-result.json';path.unlink(missing_ok=True)
def select(a,b):
 f.command(50);f.position(a);f.command(68);f.position(b)
def stop():
 i=f.get('se_input_tail',1);f.m.write(f.s['se_input_chars']+i,3);f.m.write(f.s['se_input_mods']+i,0);f.put('se_input_head',(i+1)&63,1);f.call('se_editor_service')
def snapshot():return f.read(f.s['se_doc_roots'],256)+f.read(f.s['se_doc_length'],3)+f.read(f.s['se_doc_generation'],2)
def owner():return f.read(f.s['se_reu_logical_owner'],512)
def clip():return f.read(f.s['se_clip_token'],5)+f.read(f.s['se_clip_length'],3)+f.read(f.s['se_clip_generation'],2)
def prepare():
 f.source(b'Z'*70000);select(0,4);f.command(69);select(100,69000)
def until_phase(p):
 for _ in range(2000):
  if f.get('se_h_phase',1)==p:return
  f.call('se_editor_service');assert f.get('se_e_error',1)==0
 raise AssertionError(p)
def patch_block(corrupt):
 index=next(i for i in range(12) if f.m.read(f.s['se_overlay_ids']+i)==10 and f.m.read(f.s['image_slot']+i)==1)
 f.put('se_reu_logical',f.get('se_overlay_asset',1),1);f.put('se_reu_offset',index*4096+20,2);f.put('se_reu_length',1,2);f.put('se_reu_c64',0x5000,2);f.m.write(0x5000,f.assets['block'][HEADER+20]^(1 if corrupt else 0));assert not f.call('se_reu_copy').p&1
try:
 prepare();old=clip();before=snapshot();owners=owner();f.call('se_editor_command',69)
 assert f.get('se_clip_busy',1)==1 and f.get('se_doc_read_locks',1)==1
 f.call('se_editor_service');assert clip()==old and snapshot()==before
 # CTRL-C waits in the queue while copying; only unmodified STOP cancels.
 i=f.get('se_input_tail',1);f.m.write(f.s['se_input_chars']+i,3);f.m.write(f.s['se_input_mods']+i,4);f.put('se_input_head',(i+1)&63,1)
 f.call('se_editor_service');assert f.get('se_input_tail',1)==i and f.get('se_b_phase',1)==1
 # Another begin/cross-operation clipboard cancel cannot steal this operation.
 regs=f.call('se_block_begin');assert regs.p&1 and regs.a==0x51 and f.get('se_b_phase',1)==1
 stop();f.settle();assert snapshot()==before and clip()==old and owner()==owners and f.get('se_sel_mark',1)==1
 # Paste before publication, after real insertion bytes have been fed, is cancelable.
 f.command(50);f.position(3);f.call('se_editor_command',71);until_phase(4)
 f.call('se_editor_service');assert f.get('se_b_left')==0
 stop();f.settle();assert snapshot()==before and clip()==old and owner()==owners
 # Corrupt an evicted block feeder. Resident abort releases history and clipboard.
 select(10,20);f.call('se_editor_command',71);until_phase(4)
 f.call('se_search_call',2) #C9 inactive state refusal evicts C10 without mutation
 patch_block(True);f.call('se_editor_service');f.settle(0x14)
 assert snapshot()==before and clip()==old and f.get('se_sel_mark',1)==1 and owner()==owners
 patch_block(False);f.command(71);assert f.get('se_sel_mark',1)==0 and f.get('se_hot_caret')==14
 assert f.document()==b'Z'*(70000-6)
 print('Pending copy/paste cancel,competing begin and corrupt feeder retry pass.',flush=True)
 # Small provider: retain a clipboard, exhaust remaining banks, then fail copy.
 f.source(b'A'*100,banks=1,physical=8);assert f.get('se_reu_banks',2)==8;select(0,5);f.command(69);select(10,90)
 allocated=[]
 while True:
  regs=f.call('se_reu_alloc',7)
  if regs.p&1:break
  allocated.append(regs.a)
 old=clip();before=snapshot();owners=owner();f.command(69,error=1)
 assert clip()==old and snapshot()==before and owner()==owners and f.get('se_sel_mark',1)==1
 for n in allocated:
  regs,_=f.m.call(f.s['se_reu_free'],x=n);assert not regs.p&1
 # Applied journal failure keeps edited source; never repeats it on retry.
 f.source(b'old text');select(0,3);f.put('se_hot_byte',0xD8,1);f.call('se_editor_command',5)
 while not f.get('se_h_applied',1):f.call('se_editor_service');assert not f.get('se_e_error',1)
 assert f.get('se_b_phase',1)==3 and f.get('se_h_phase',1)==7
 regs=f.call('se_block_cancel');assert regs.p&1 and regs.a==0x61
 logical=f.m.read(f.s['object_extents']+f.get('se_h_token',1)*16);saved=f.m.read(f.s['se_reu_logical_owner']+logical);f.m.write(f.s['se_reu_logical_owner']+logical,0)
 f.call('se_editor_service');f.m.write(f.s['se_reu_logical_owner']+logical,saved);f.settle(0x34)
 expected=bytes([0xD8])+b' text';assert f.document()==expected and f.get('se_sel_mark',1)==0 and f.get('se_hot_ready',1)==1
 f.render();assert 'Undo fault' in native_screen_text(f.read(0x4000,1000))
 f.key(65,error=0x65);assert not f.get('se_hot_pending',1) and f.document()==expected
 current=f.get('se_h_current',4);f.typed(b'CLEAR UNDO');assert f.get('se_h_current',4)==current and f.get('se_h_dirty',1)==1
 f.key(66);f.command(33);assert f.document()==bytes([0xD8,66])+b' text'
 print('Applied journal error displays committed text and explicit recovery preserves dirty state.',flush=True)
 # An old context's cancellation cannot release new provider-owned leases.
 prepare();f.command(50);f.position(10);f.call('se_editor_command',71);until_phase(4)
 f.put('se_reu_banks',8,2)
 for n,a in [('se_reu_provider_init',0),('se_object_init',0),('se_doc_init',1)]:assert not f.call(n,a).p&1
 f.put('se_doc_source_length',0);assert not f.call('se_doc_adopt_original').p&1
 assert not f.call('se_clip_init').p&1;f.put('se_clip_busy',2,1)
 assert not f.call('se_doc_read_acquire').p&1
 f.call('se_block_cancel');assert f.get('se_doc_read_locks',1)==1 and f.get('se_clip_busy',1)==2
 f.call('se_doc_read_release');assert f.read(0xC600,1024)==f.shim
 result=dict(status='passed',prg_sha256=f.report['sha256'],resident_binding=f.report['resident_binding']['digest'],overlay_sha256={n:hashlib.sha256(v).hexdigest() for n,v in f.assets.items()},pending_copy_and_paste_cancel=True,queued_ctrl_c_does_not_cancel=True,small_reu_banks=8,competing_begin_refused_without_cancel=True,corrupt_feeder_cleans_owned_state=True,allocation_failure_preserves_clipboard_and_selection=True,applied_fault_never_retries_edit=True,committed_source_displayed_after_fault=True,explicit_clear_undo_recovers_preserving_dirty=True,foreign_epoch_lease_and_clipboard_lock_preserved=True,shim_bytes_verified=1024)
 path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:f.close()
