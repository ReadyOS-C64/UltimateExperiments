"""Independent source/clipboard/selection model through the integrated editor."""
import hashlib,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_fixture import EditorFixture
from run_vice import native_screen_text
f=EditorFixture();result_path=ROOT/'build/selection-test-result.json';result_path.unlink(missing_ok=True)
def select(a,b):
 f.command(50);f.position(a);f.key(0x89);f.position(b)
 assert f.get('se_sel_mark',1)==1 and f.get('se_sel_anchor')==a
 f.call('se_selection_range');assert f.get('se_sel_start')==min(a,b) and f.get('se_sel_length')==abs(a-b)
def clipboard():
 if not f.get('se_clip_active',1):return b''
 out=bytearray();length=f.get('se_clip_length');token=f.read(f.s['se_clip_token'],5)
 for p in range(0,length,1024):
  n=min(1024,length-p);f.m.load(f.s['se_object_id'],token);f.put('se_object_offset',p);f.put('se_object_length',n,2);f.put('se_object_c64',0x8000,2)
  assert not f.call('se_object_copy',1).p&1;out.extend(f.read(0x8000,n))
 return bytes(out)
try:
 source=b'ABCDEFGHIJ\rshort\r\r'+bytes([0xC1,0x42,0xC3])+b'\rTAIL';f.source(source)
 # Real cursor/page/menu paths extend mark without moving its source anchor.
 f.key(0x89);f.command(37);f.command(37);f.command(36);assert f.get('se_sel_anchor')==0
 f.key(0x85);f.key(0x42);f.key(0x43);assert clipboard()==source[:f.get('se_hot_caret')]
 f.key(3);assert f.get('se_sel_mark',1)==0
 # CTRL-C and RUN/STOP share byte03: modifier4 means copy, plain03 unmarks.
 select(0,10);f.key(3,mods=4);assert clipboard()==source[:10] and f.get('se_sel_mark',1)==1
 f.key(3);assert f.get('se_sel_mark',1)==0
 select(0,0);f.command(69);f.command(70);assert clipboard()==source[:10] and f.document()==source
 # Empty clipboard is never a selected deletion.
 f.source(source);select(10,0);f.command(71);assert f.document()==source and f.get('se_sel_mark',1)==1
 # Inspect actual inverse character/color cells, including selected CR/blank row.
 select(18,8);f.render();matrix=f.read(0x4000,1000);colors=f.read(0xD800,1000)
 assert 'Mark' in native_screen_text(matrix)
 for row in range(22):
  start=int.from_bytes(f.read(f.s['se_v_rows']+row*3,3),'little')
  end=source.find(b'\r',start);end=len(source) if end<0 else end
  for col in range(min(40,end-start+1)):
   p=start+col
   if p>len(source):continue
   at=(row+2)*40+col
   if p==8:assert colors[at]&15==7 and matrix[at]&128
   elif 8<=p<18:assert colors[at]&15==3 and matrix[at]&128,(row,col,p)
 print('Mark,cursor/menu,CTRL-C vs STOP,empty operations and selected CR pixels pass.',flush=True)
 rng=random.Random(0x53454C45);source=bytes(rng.choice([13,32,65,66,67,0xC1,0xC2,0xFF]) for _ in range(1200));f.source(source);clip=b'';edits=0
 for case in range(80):
  a=rng.randrange(len(source)+1);b=rng.randrange(len(source)+1);lo,hi=sorted((a,b));old=source;before=b;action=rng.choice(['copy','cut','paste','type','delete','back'])
  select(a,b);current=f.get('se_h_current',4)
  if action=='copy':
   f.command(69)
   if lo!=hi:clip=source[lo:hi]
  elif action=='cut':
   f.command(70)
   if lo!=hi:clip=source[lo:hi];source=source[:lo]+source[hi:]
  elif action=='paste':
   f.command(71)
   if clip:source=source[:lo]+clip+source[hi:]
  elif action=='type':
   value=rng.choice([13,65,0xC1,0xFF]);f.key(value);source=source[:lo]+bytes([value])+source[hi:]
   # Zero-length normal typing is pending until navigation; flush it explicitly.
   if lo==hi:f.command(33)
  else:
   f.command(4 if action=='delete' else 3)
   if lo!=hi:source=source[:lo]+source[hi:]
   else:
    p=b
    if action=='delete' and p<len(source):source=source[:p]+source[p+1:]
    if action=='back' and p:source=source[:p-1]+source[p:]
    f.command(33)
  assert f.document()==source,(case,action,lo,hi,len(source),len(f.document()))
  assert clipboard()==clip,(case,action,'clipboard')
  if source!=old:
   edits+=1;assert f.get('se_h_current',4)==current+1
   f.command(16);assert f.document()==old and f.get('se_hot_caret')==before,(case,action,'undo caret')
   f.command(17);assert f.document()==source and f.get('se_sel_mark',1)==0
 print('80 independent copy/cut/paste/replacement/replay cases pass.',flush=True)
 # Real edits while dirty before marking must copy the merged, then flushed source.
 f.source(b'abc\rdef');f.key(0xD8);f.key(0x89);f.command(2);f.key(0x0B);assert clipboard()==b'a' and f.document()==bytes([0xD8])+b'abc\rdef'
 # 24-bit selected source positions and long cross-page clipboard replacement.
 source=bytes((65+i%26 for i in range(70000)));f.source(source)
 select(69003,500);f.typed(b'COPY');clip=source[500:69003];assert clipboard()==clip
 select(3,68000);f.typed(b'PASTE');expected=source[:3]+clip+source[68000:];assert f.document()==expected
 assert f.get('se_hot_caret')==3+len(clip);f.typed(b'UNDO');assert f.document()==source and f.get('se_hot_caret')==68000
 f.typed(b'REDO');assert f.document()==expected
 f.typed(b'CLEAR UNDO');assert f.get('se_h_end',2)==0 and f.get('se_h_dirty',1)==1 and f.document()==expected
 assert f.read(0xC600,1024)==f.shim
 result=dict(status='passed',prg_sha256=f.report['sha256'],resident_binding=f.report['resident_binding']['digest'],overlay_sha256={n:hashlib.sha256(v).hexdigest() for n,v in f.assets.items()},random_transactions=80,edits=edits,reversed_multiline_selection=True,native_ctrl_c_and_stop_distinct=True,empty_copy_cut_and_clipboard_preserve_source=True,selection_glyph_and_color_cells_checked=True,pending_source_copy=True,clipboard_bytes_over_65535=len(clip),selected_replacement_undo_redo=True,clear_undo_preserves_dirty_source=True,max_service_instructions=f.max_service,shim_bytes_verified=1024,limitations='Source40 CPU/UI model;native VIC screenshots,fault matrix and normal timing separate.')
 result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:f.close()
