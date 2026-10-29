"""Independent source40 viewport audit around pending edits and replay boundaries.

Baseline assumptions: raw PETSCII,40-byte soft wrap,22 body rows, separate bottom,
no pan/no-wrap/rendered markup. No shared oracle imports, build or VICE.
"""
import bisect
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_fixture import EditorFixture
OUT=ROOT/'build/viewport-edges-result.json'

def glyph(v):
 if v<32 or 128<=v<160:return 63
 if v<64:return v
 if v<96:return v-64
 if v<128:return v-32
 if v==255:return 94
 if v<192:return v%32+96
 if v<224:return v-128
 return v%32+96

def layout(data):
 """Every source row and caret cell, derived from bytes rather than view cache."""
 out=[];start=0;cells=[]
 for i,v in enumerate(data):
  if v==13:
   cells.append((i,32));out.append((start,i+1,cells));start=i+1;cells=[]
  else:
   cells.append((i,glyph(v)))
   if len(cells)==40:out.append((start,i+1,cells));start=i+1;cells=[]
 cells.append((len(data),32));out.append((start,len(data),cells))
 return out

def expected_body(data,top,caret):
 rows=layout(data);starts=[r[0] for r in rows]
 assert top in starts,('unaligned top',top,'nearest row',starts[max(0,bisect.bisect_right(starts,top)-1)])
 first=starts.index(top);matrix=bytearray([32]*880);colors=bytearray([1]*880);anchors=[];seen=None
 for y in range(22):
  if first+y>=len(rows):anchors.append(len(data));continue
  start,end,cells=rows[first+y];anchors.append(start)
  for x,(position,code) in enumerate(cells):
   if position==caret and seen is None:code^=128;colors[y*40+x]=3;seen=(y,x)
   matrix[y*40+x]=code
 anchors.append(rows[first+22][0] if first+22<len(rows) else len(data))
 return bytes(matrix),bytes(colors),anchors,seen

def native(text):
 return bytes(ord(c)+128 if 'A'<=c<='Z' else ord(c)-32 if 'a'<=c<='z' else 13 if c=='\n' else ord(c) for c in text)

f=globals().get('fixture') or EditorFixture()
source=b'';caret=0;traces=[];failures=[];operations=[];cases=0;async_jobs=0;async_steps=0;fault_checks=[]
snapshot=dict(prg_sha256=f.report['sha256'],resident_binding=f.report['resident_binding']['digest'],overlay_sha256={n:hashlib.sha256(v).hexdigest() for n,v in f.assets.items()})
WIDTHS={'se_hot_caret':3,'se_hot_base':3,'se_hot_left':2,'se_hot_right':2,'se_hot_old_length':2,'se_hot_pending':1,'se_hot_phase':1,'se_hot_length':2,'se_doc_length':3,'se_doc_generation':2,'se_v_top':3,'se_v_bottom':3,'se_v_length':3,'se_v_seen':1,'se_v_caret_row':1,'se_v_caret_col':1,'se_r_valid':1,'se_r_path':1,'se_r_rows':1,'se_r_cells':2,'se_r_damage_from':3,'se_r_damage_to':3,'se_r_damage_valid':1,'se_r_revision':4,'se_r_saved_revision':4,'se_h_current':4,'se_h_saved':4,'se_h_dirty':1,'se_e_job':1,'se_e_error':1,'se_e_redraw':1,'se_e_draw_sequence':2,'se_doc_read_locks':1,'se_n_owned':1,'se_v_nav_busy':1,'se_l_active':1,'se_l_valid':1,'se_l_scan':3}
def state():
 out={n:f.get(n,w) for n,w in WIDTHS.items() if n in f.s}
 out['rows']=[int.from_bytes(f.read(f.s['se_v_rows']+3*i,3),'little') for i in range(22)]
 return out

def merged():
 data=f.document();base=f.get('se_hot_base')
 span=f.read(0x9200,f.get('se_hot_left',2))+f.read(0x9200+f.get('se_hot_right',2),2048-f.get('se_hot_right',2))
 return data[:base]+span+data[base+f.get('se_hot_old_length',2):]

def check(tag,*,context=False,storage=False):
 global async_jobs,async_steps
 before=state();item=dict(tag=tag,before=before,host_caret=caret,host_source_length=len(source))
 try:
  assert merged()==source,('merged source',len(merged()),len(source))
  assert f.get('se_hot_caret')==caret,('caret source position',f.get('se_hot_caret'),caret)
  preserved={n:f.read(f.s[n],w) for n,w in [('se_hot_caret',3),('se_doc_generation',2),('se_h_current',4),('se_h_saved',4),('se_hot_pending',1)]}
  reu_before=hashlib.sha256(bytes(f.m.lib.zeropage_peddle_read_reu(f.m.handle,i) for i in range(8*65536))).hexdigest() if storage else None
  # Explicit asynchronous contract: A1/Cclear queues job7 without painting.
  # Complete bounded resident service steps, then ask for the actual paint.
  queued=steps=attempts=0
  while True:
   old_pixels=f.read(0x4000,1000)+f.read(0xD800,1000)
   old_sequence=f.get('se_e_draw_sequence',2)
   regs=f.call('se_editor_render');assert not regs.p&1,('render',regs.a)
   if not f.get('se_e_job',1):break
   assert regs.a==1 and f.get('se_e_job',1)==7,('unexpected render job',regs.a,f.get('se_e_job',1))
   assert f.read(0x4000,1000)+f.read(0xD800,1000)==old_pixels,'queued layout painted pixels'
   assert f.get('se_e_draw_sequence',2)==old_sequence,'queued layout published a draw'
   queued+=1;async_jobs+=1;attempts+=1;assert attempts<4,'layout preparation did not converge'
   while f.get('se_e_job',1):
    assert f.get('se_e_job',1)==7
    assert f.get('se_doc_read_locks',1)==1 and f.get('se_n_owned',1)==1 and f.get('se_v_nav_busy',1)==1
    if 'se_l_active' in f.s:assert f.get('se_l_active',1)==1
    scan=f.get('se_l_scan') if 'se_l_scan' in f.s else 0
    f.call('se_editor_service');steps+=1;async_steps+=1;assert steps<25000,'layout step bound'
    assert f.get('se_e_error',1)==0,('layout error',f.get('se_e_error',1))
    assert f.read(0x4000,1000)+f.read(0xD800,1000)==old_pixels,'layout step painted pixels'
    assert f.get('se_e_draw_sequence',2)==old_sequence,'layout step published a draw'
    if f.get('se_e_job',1):assert 0<=f.get('se_l_scan')-scan<=128,'layout exceeded128 source bytes'
   assert f.get('se_doc_read_locks',1)==0 and f.get('se_n_owned',1)==0 and f.get('se_v_nav_busy',1)==0
   if 'se_l_active' in f.s:assert f.get('se_l_active',1)==0
  item.update(queued_layout_jobs=queued,layout_service_steps=steps)
  assert f.read(0xC600,1024)==f.shim,'shim changed'
  for n,old in preserved.items():assert f.read(f.s[n],len(old))==old,('render mutated',n)
  if storage:assert hashlib.sha256(bytes(f.m.lib.zeropage_peddle_read_reu(f.m.handle,i) for i in range(8*65536))).hexdigest()==reu_before,'render changed REU'
  top=f.get('se_v_top');wanted,colors,anchors,visible=expected_body(source,top,caret)
  assert visible is not None,('caret invisible',top,caret)
  assert f.get('se_v_seen',1)==1 and (f.get('se_v_caret_row',1),f.get('se_v_caret_col',1))==visible,('caret cell',visible)
  actual=f.read(0x4000+80,880);actual_colors=bytes(v&15 for v in f.read(0xD800+80,880))
  assert actual==wanted,('body glyphs',[(i//40,i%40,a,b) for i,(a,b) in enumerate(zip(actual,wanted)) if a!=b][:12])
  assert actual_colors==colors,('body colors',[(i//40,i%40,a,b) for i,(a,b) in enumerate(zip(actual_colors,colors)) if a!=b][:12])
  row_anchors=[int.from_bytes(f.read(f.s['se_v_rows']+3*i,3),'little') for i in range(22)]+[f.get('se_v_bottom')]
  assert row_anchors==anchors,('row anchors',row_anchors,anchors)
  if context:
   rows=layout(source);starts=[r[0] for r in rows];index=bisect.bisect_right(starts,caret)-1
   expected_top=starts[max(0,index-21)]
   assert top==expected_top,('lost preceding context',top,expected_top,'caret row',visible)
  item['status']='passed'
 except AssertionError as error:
  item.update(status='failed',error=str(error),source_hex=source.hex(),operations=list(operations),actual_matrix_hex=f.read(0x4000+80,880).hex(),actual_colors_hex=f.read(0xD800+80,880).hex())
  # Canonical maximum-context frame is retained even if actual top is invalid.
  starts=[r[0] for r in layout(source)];index=bisect.bisect_right(starts,caret)-1;canonical=starts[max(0,index-21)]
  wanted,colors,anchors,visible=expected_body(source,canonical,caret)
  item.update(expected_context_top=canonical,expected_matrix_hex=wanted.hex(),expected_colors_hex=colors.hex(),expected_anchors=anchors,expected_caret=visible)
  failures.append(item)
 item['after']=state();traces.append(item)
 return item['status']=='passed'

def setup(name,data,position=None):
 global source,caret,operations,cases
 cases+=1;source=data;caret=0;operations=[dict(operation='source',name=name,source_hex=data.hex())]
 f.source(data,banks=1,physical=8)
 if position=='bottom':f.command(35);caret=len(source);operations.append(dict(operation='bottom'))
 elif position is not None:f.position(position);caret=position;operations.append(dict(operation='position',position=position))
 check(name+' / initial')
def type_bytes(data):
 global source,caret
 for byte in data:
  f.key(byte);source=source[:caret]+bytes([byte])+source[caret:];caret+=1
 operations.append(dict(operation='type pending',bytes_hex=data.hex()))
def back():
 global source,caret
 f.key(0x14)
 if caret:source=source[:caret-1]+source[caret:];caret-=1
 operations.append(dict(operation='backspace'))
def delete():
 global source
 f.command(4)
 source=source[:caret]+source[caret+1:]
 operations.append(dict(operation='forward delete'))
def command(c,new_source=None,new_caret=None):
 global source,caret
 f.command(c)
 if new_source is not None:source=new_source
 if new_caret is not None:caret=new_caret
 operations.append(dict(operation='command',command=c))

try:
 OUT.unlink(missing_ok=True)
 # Minimal crossing: EOF occupies body row21; Return/one byte creates row22.
 setup('minimal pending Return off bottom',b'\r'*21,'bottom');type_bytes(b'\r');check('minimal pending Return off bottom',context=True,storage=True)
 setup('minimal printable wrap off bottom',b'\r'*21+b'X'*39,'bottom');type_bytes(b'A');check('minimal printable wrap off bottom',context=True)
 setup('longline one byte off bottom',b'X'*879,'bottom');type_bytes(b'A');check('longline one byte off bottom',context=True)
 setup('longline pending batch off bottom',b'X'*879,'bottom');type_bytes(b'ABCD'*31);check('longline124 pending bytes off bottom',context=True,storage=True)
 setup('longline pending CR batch off bottom',b'X'*839,'bottom');type_bytes(b'\rQ'*25);check('25 pending CR/text rows off bottom',context=True)
 setup('middle of longline wraps with suffix',b'X'*2000,879);type_bytes(b'A');check('middle longline pending shift off bottom',context=True)
 # Before-top deletion: remove the CR preceding first visible short line.
 setup('minimal backspace before top',b'X\r'*22,'bottom');top=f.get('se_v_top');f.position(top);caret=top;operations.append(dict(operation='position',position=top));check('minimal backspace / at top');back();check('minimal backspace deletes preceding CR',storage=True)
 setup('longline backspace before top',b'X'*2000,'bottom');top=f.get('se_v_top');f.position(top);caret=top;operations.append(dict(operation='position',position=top));check('longline backspace / at top');back();check('longline backspace deletes previous source byte')
 setup('exact wrap CR backspace before top',b'X'*40+b'\r'*22,'bottom');top=f.get('se_v_top');f.position(top);caret=top;operations.append(dict(operation='position',position=top));back();check('exact wrap CR backspace')
 # Forward delete keeps source position; CR joins, empty rows and full wrap move.
 for name,data in [('short lines',b'ABCDE\r'*48),('exact40 CR',(b'X'*40+b'\r')*30),('mixed empties',b'\rQ\r'+(b'X'*41+b'\r\r')*24)]:
  setup('forward delete '+name,data,'bottom');top=f.get('se_v_top');f.position(top);caret=top;operations.append(dict(operation='position',position=top));delete();check('forward delete at top '+name)
  back();check('backspace after forward delete '+name)
 # Diverse native raw document, pending edits and widely separated undo carets.
 data=b'\r'.join(native('# Section '+str(i)+' Mixed CASE') if i%5==0 else native('10 PRINT "HELLO":GOTO10') if i%5==1 else native('loop: lda #$00 ; Mixed') if i%5==2 else bytes([0,0x93,0x41,0xC1,0x61])*9 if i%5==3 else b'Q'*81 for i in range(60))
 setup('substantial mixed pending bottom',data,'bottom')
 for i in range(6):type_bytes(native('abCD')+b'\r');check('mixed pending row '+str(i),context=True)
 # Force one history transaction at start, another at EOF, then replay both ways.
 setup('widely separated replay',data,0);original=source;type_bytes(b'A');command(35,new_caret=len(source));check('replay first committed bottom',context=True)
 first=source;before_second=caret;type_bytes(b'Z');command(1,new_caret=caret-1);second=source;check('replay second committed left')
 command(16,new_source=first,new_caret=before_second);check('undo EOF edit',context=True)
 command(16,new_source=original,new_caret=0);check('undo start edit')
 command(17,new_source=first,new_caret=1);check('redo start edit')
 command(17,new_source=second,new_caret=before_second+1);check('redo EOF edit',context=True,storage=True)
 # Job7 cancellation/error cleanup is resident and owns only its lease epoch.
 if 'se_layout_prepare' in f.s:
  def queue_layout(tag):
   setup(tag,b'\r'*21,'bottom');type_bytes(b'\r')
   pixels=f.read(0x4000,1000)+f.read(0xD800,1000)
   regs=f.call('se_editor_render')
   assert not regs.p&1 and regs.a==1 and f.get('se_e_job',1)==7
   assert f.get('se_doc_read_locks',1)==f.get('se_n_owned',1)==f.get('se_v_nav_busy',1)==1
   return pixels
  pixels=queue_layout('job7 STOP cancellation')
  f.m.write(f.s['se_input_chars'],3);f.m.write(f.s['se_input_mods'],0);f.put('se_input_head',1,1);f.put('se_input_tail',0,1)
  f.call('se_editor_service')
  for n in ['se_e_job','se_e_redraw','se_n_owned','se_v_nav_busy','se_doc_read_locks','se_l_active']:assert f.get(n,1)==0,n
  assert f.read(0x4000,1000)+f.read(0xD800,1000)==pixels and merged()==source and f.get('se_hot_pending',1)==1
  fault_checks.append(dict(case='STOP',released_owned_lease=True,old_pixels_retained=True,pending_preserved=True))
  check('job7 STOP explicit retry',context=True)

  pixels=queue_layout('job7 queued CTRL-C is not STOP')
  f.m.write(f.s['se_input_chars'],3);f.m.write(f.s['se_input_mods'],4);f.put('se_input_head',1,1);f.put('se_input_tail',0,1)
  while f.get('se_e_job',1):f.call('se_editor_service')
  assert f.get('se_input_tail',1)==0 and f.get('se_doc_read_locks',1)==0 and f.read(0x4000,1000)+f.read(0xD800,1000)==pixels
  fault_checks.append(dict(case='CTRL-C',not_consumed_as_stop=True,layout_completed=True))
  check('job7 CTRL-C remains queued',context=True);f.put('se_input_tail',1,1)

  pixels=queue_layout('job7 C11 cached checksum failure')
  assert not f.call('se_history_call',10).p&1 #legitimate command-slot eviction
  index=next(i for i in range(12) if f.m.read(f.s['se_overlay_ids']+i)==11 and f.m.read(f.s['image_slot']+i)==1)
  original=f.assets['layout'][36+20]
  def patch_layout(byte):
   f.put('se_reu_logical',f.get('se_overlay_asset',1),1);f.put('se_reu_offset',index*4096+20,2);f.put('se_reu_length',1,2);f.put('se_reu_c64',0x5000,2);f.m.write(0x5000,byte)
   assert not f.call('se_reu_copy').p&1
  patch_layout(original^1);f.call('se_editor_service')
  assert f.get('se_e_error',1)==0x14
  for n in ['se_e_job','se_n_owned','se_v_nav_busy','se_doc_read_locks','se_l_active']:assert f.get(n,1)==0,n
  assert f.read(0x4000,1000)+f.read(0xD800,1000)==pixels and merged()==source and f.get('se_hot_pending',1)==1
  fault_checks.append(dict(case='corrupt C11 reload',error=0x14,released_owned_lease=True,old_pixels_retained=True,pending_preserved=True))
  patch_layout(original);f.put('se_e_error',0,1);check('job7 C11 checksum retry',context=True)

  queue_layout('job7 foreign provider epoch lease')
  f.put('se_reu_banks',8,2)
  for n,a in [('se_reu_provider_init',0),('se_object_init',0),('se_doc_init',1)]:assert not f.call(n,a).p&1
  f.put('se_doc_source_length',0);assert not f.call('se_doc_adopt_original').p&1
  assert not f.call('se_doc_read_acquire').p&1 and f.get('se_doc_read_locks',1)==1
  assert not f.call('se_navigation_call',3).p&1
  assert f.get('se_doc_read_locks',1)==1 and f.get('se_n_owned',1)==0 and f.get('se_v_nav_busy',1)==0 and f.get('se_l_active',1)==0
  fault_checks.append(dict(case='foreign provider epoch',foreign_lease_preserved=True))
  assert not f.call('se_doc_read_release').p&1;f.put('se_e_job',0,1)
 assert f.read(0xC600,1024)==f.shim
 result=dict(status='failed' if failures else 'passed',**snapshot,test_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),assumptions=dict(source40_softwrap=40,body_rows=22,status_row=24,no_pan=True,no_markup_rendering=True),fixture_cases=cases,frames=len(traces),failed_frames=len(failures),async_layout_jobs=async_jobs,async_layout_service_steps=async_steps,async_fault_cases=fault_checks,failures=failures,traces=[{k:v for k,v in item.items() if k not in ['source_hex','actual_matrix_hex','actual_colors_hex','expected_matrix_hex','expected_colors_hex','operations']} for item in traces],shim_bytes_verified=1024,limitations='CPU current source40 viewport audit; no VICE/pixels/normal-clock/physical-key proof; pan/no-wrap baseline intentionally not exercised.')
 OUT.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ['status','prg_sha256','fixture_cases','frames','failed_frames']},indent=2))
 for item in failures:print(item['tag']+': '+item['error'])
 if failures:raise SystemExit(1)
finally:f.close()
