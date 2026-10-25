"""Actual edited-fold retention stress at24-bit offsets and journal capacity.

Default prepares only. --run uses an immutable product fixture and private CPU
runner; no sharedmake/VICE. Fullsource/pixels/anchors and derived-only REU DMA.
"""
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace
import argparse,json,shutil
import test_fold_retention as r
import test_fold_projection as projection
import test_fold_builder as builder
from test_folds import action_model
from redraw_model import native_text,Screen,verify_screen
ROOT=r.ROOT

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');ap.add_argument('--fixture',type=Path);a=ap.parse_args()
 if not a.run:print('Prepared24bit/capacity/hidden-selection/object-pressure retention gate; --run after frozenproduction signal.');return
 out=ROOT/'build/fold-retention-faults'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);frozen,identity=r.freeze(out,a.fixture)
 r.grid.editor_fixture.ROOT=r.grid.cpu_editor.ROOT=frozen;r.grid.editor_fixture.NAMES=r.grid.cpu_editor.NAMES=identity['names'];dll=r.runner(out);frames=[];f=None
 def check(data,folds,tag,valid=True):
  canonical,reu,catalog=f.canonical(),f.reu(),f.catalog();top=f.get('se_v_top');f.audit_begin()
  try:f.render()
  finally:f.dll.fr_end()
  writes=f.audit_end(reu,tag);assert f.canonical()==canonical and f.merged()==data and f.catalog()==catalog,(tag,'canonical')
  assert bool(f.get('se_ef_valid',1))==valid,(tag,'mapvalid',f.get('se_ef_valid',1))
  if valid:assert f.metadata()==b''.join(x.bytes() for x in folds),(tag,'freshrecords',f.metadata().hex(),b''.join(x.bytes() for x in folds).hex())
  wanted,anchors,ends,bits,seen=projection.expected(f,data,folds,top)
  actual=tuple(int.from_bytes(f.read(f.s['se_v_rows']+i*3,3),'little') for i in range(22))+(f.get('se_v_bottom'),)
  assert actual==anchors,(tag,'anchors',actual,anchors)
  if valid:assert tuple(int.from_bytes(f.read(f.s['se_ef_paint_ends']+i*3,3),'little') for i in range(22))==ends
  assert f.get('se_ef_fold_rows')==sum(v<<i for i,v in enumerate(bits)),(tag,'bits')
  verify_screen(f.read(0x4000,1000),f.read(0xD800,1000),Screen(*wanted,anchors,seen),tag=tag)
  assert not any(f.get(n,1) for n in ['se_f_owner','se_doc_read_locks','se_fs_owned','se_ef_active']) and f.read(0xC600,1024)==f.shim
  frames.append(dict(tag=tag,source_bytes=len(data),caret=f.get('se_hot_caret'),collapsed=[i for i,x in enumerate(folds) if x.flags&1],pending=f.get('se_hot_pending',1),writes=writes));(out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
 def move(data,p):
  line=data[:p].count(b'\r')+1;column=p-(data.rfind(b'\r',0,p)+1);f.typed(native_text(f'goto {line}'))
  for _ in range(column):f.command(2)
  assert f.get('se_hot_caret')==p
 def fixture(data):
  nonlocal f
  if f is not None:f.close()
  f=r.Fixture(out,frozen,dll,True);f.source(data);tree,_,_,error=builder.oracle(data);assert not error;return tree
 try:
  # Source positions on both sides of the16-bit boundary; unrelated closed
  # siblings surround an open body that receives the real keyboard edits.
  data=b'P'*65530+native_text('\r:::region A\ralpha\r:::end\rvisible middle\r:::region B\rbeta\r:::end\rend\r')
  folds=fixture(data)
  for index in range(2):
   move(data,folds[index].start);f.command(113);folds,_=action_model(folds,1,index,f.get('se_hot_caret'),f.get('se_ef_motion',4),f.get('se_hot_caret'))
  p=data.index(native_text('visible middle'));assert p>65535;move(data,p);check(data,folds,'24bit-before-edit')
  f.key(ord('X'));data,folds=r.retained(folds,data,p,0,b'X');check(data,folds,'24bit-pending-retains-two')
  f.command(4);data,folds=r.retained(folds,data,p+1,1,b'');check(data,folds,'24bit-delete-retains-two')
  print('FIRST24BIT3SCREENS-PASS',flush=True)
  # Exactly112 witnessed edits retain both folds;113 deliberately disables the
  # optional chain and freshly parses all folds expanded. No source edit fails.
  base=native_text('prefix\r:::region A\ralpha\r:::end\rvisible middle\r:::region B\rbeta\r:::end\rend\r')
  for count in [112,113]:
   data=base;tree=fixture(data);f.command(115);folds,_=action_model(tree,3,0,0,f.get('se_ef_motion',4),0);p=data.index(native_text('visible middle'));move(data,p)
   for _ in range(count):f.key(ord('Q'))
   assert f.get('se_ej_count',1)==112 and f.get('se_ej_status',1)==(2 if count==112 else 0x80)
   data,retained=r.retained(folds,data,p,0,b'Q'*count)
   if count==113:
    retained,_,_,error=builder.oracle(data);assert not error
   check(data,retained if count==112 else [],f'journal-{count}-events',valid=count==112)
   assert [x.flags&1 for x in retained]==([1,1] if count==112 else [0,0])
   assert not f.get('se_e_error',1)
   if count==112:assert f.get('se_ej_status',1)==1 and not f.get('se_ej_count',1)
   else:
    assert f.get('se_ej_status',1)==0x80 and f.get('se_ej_count',1)==112
    at=f.get('se_hot_caret');f.key(ord('Y'));data=data[:at]+b'Y'+data[at:];check(data,[],f'journal-{count}-next-key-still-editable',valid=False)
  # A selected canonical range includes an entire collapsed region. Cut
  # removes that fold; undo restores its source expanded while keeping the
  # unrelated sibling's certified closed state.
  data=base;tree=fixture(data);f.command(115);folds,_=action_model(tree,3,0,0,f.get('se_ef_motion',4),0)
  start=folds[0].start;end=folds[0].end;move(data,start);f.command(68);move(data,end);check(data,folds,'selected-hidden-range')
  f.command(69);assert f.get('se_clip_length')==end-start
  f.command(70);old=data;data,folds=r.retained(folds,data,start,end-start,b'');check(data,folds,'cut-hidden-keeps-sibling');assert len(folds)==1 and folds[0].flags&1
  f.command(16);data,folds=r.retained(folds,data,start,0,old[start:end]);assert data==old;check(data,folds,'undo-hidden-keeps-sibling');assert [x.flags&1 for x in folds]==[0,1]
  # Fill all8 actual object slots with clipboard/history live. Retention's
  # optional hint allocation must fail safely, preserve foreign objects, and
  # allow subsequent ordinary expanded source painting with its error report.
  data=base;tree=fixture(data);f.command(115);folds,_=action_model(tree,3,0,0,f.get('se_ef_motion',4),0)
  move(data,0);f.command(68);f.command(2);f.command(69);f.command(50);assert f.get('se_clip_length')==1 and f.get('se_h_ready',1)
  p=data.index(native_text('visible middle'));move(data,p);check(data,folds,'objectpressure-before-fill')
  foreign=[]
  while sum(3<=f.m.read(f.s['object_owner']+i)<255 for i in range(8))<8:
   regs,_=f.fast_call(f.s['se_object_create'],a=0x47,x=1);assert not regs.p&1
   token=f.read(f.s['se_object_id'],5);foreign.append(token);f.put('se_object_offset',64);assert not f.call('se_object_resize').p&1
   f.m.load(0x8000,bytes((i*37+token[0])&255 for i in range(64)));f.put('se_object_offset',0);f.put('se_object_length',64,2);f.put('se_object_c64',0x8000,2);assert not f.call('se_object_copy',0).p&1
  assert foreign and sum(3<=f.m.read(f.s['object_owner']+i)<255 for i in range(8))==8
  f.key(ord('Z'));data=data[:p]+b'Z'+data[p:];assert f.merged()==data
  canonical,reu,catalog=f.canonical(),f.reu(),f.catalog();f.audit_begin();errors=[]
  try:
   for _ in range(16):
    rr=f.call('se_editor_render')
    if f.get('se_e_error',1):errors.append(f.get('se_e_error',1))
    for _ in range(25000):
     if not f.get('se_e_job',1):break
     f.call('se_editor_service')
    assert not f.get('se_e_job',1)
    if not rr.p&1 and not f.get('se_e_redraw',1):break
   else:raise AssertionError('full-object fallback did not settle')
  finally:f.dll.fr_end()
  f.audit_end(reu,'full-object-fallback');assert f.canonical()==canonical and f.merged()==data and f.catalog()==catalog
  assert f.get('se_e_error',1)==0x35 and errors and set(errors)=={0x35}
  for token in foreign:
   f.m.load(f.s['se_object_id'],token);assert not f.call('se_object_validate').p&1 and f.m.read(f.s['object_owner']+token[0])==0x47
  check(data,[],'full-object-expanded-fallback',valid=False)
  result=dict(status='passed',identity=identity,frames=frames,checked_reu_bytes=16*1024*1024,limits=['Actualrootjournal/R20/C19retention/pixels; existingROMreadseam, no native/cycleclaim.','Full-object optionalretention failure preserves error35 and expandededitablecanonicalsource.'])
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 except BaseException as e:(out/'failure.json').write_text(json.dumps(dict(error=repr(e),frames=frames),indent=2)+'\n');raise
 finally:
  if f is not None:f.close()
if __name__=='__main__':main()
