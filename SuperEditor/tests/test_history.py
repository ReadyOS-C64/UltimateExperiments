"""History controller through the real checked command-overlay trampoline."""
import binascii
import hashlib
import json
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from overlays import HEADER
from engine_test_profile import Profile
profile=Profile('history-probe','history')
r=profile.report;s=r['symbols']
asset_images=profile.assets(['hedit','hplay'])
api_text=(ROOT/('build/editor-api.inc' if profile.engine else 'build/history-api.inc')).read_text();assert 'se_doc_probe =' not in api_text and 'se_doc_read =' in api_text
result_path=profile.result_path;result_path.unlink(missing_ok=True)
m=Machine();maximum_cached_step=0;maximum_load_step=0;maximum_edit_steps=0;maximum_prepare_steps=0
def read(a,n):return bytes(m.read(a+i) for i in range(n))
def put(n,v,w=3):m.load(s[n],v.to_bytes(w,'little'))
def get(n,w=3):return int.from_bytes(read(s[n],w),'little')
def call(n,a=0,x=0,y=0,error=None):
 regs,used=m.call(s[n],a=a,x=x,y=y)
 assert bool(regs.p&1)==(error is not None),(n,hex(regs.a),regs.p)
 if error is not None:assert regs.a==error,(n,hex(regs.a),error)
 return regs.a

def h_raw(command):
 global maximum_cached_step,maximum_load_step
 desired=5 if get('se_h_phase',1)>=8 else 4
 tags=[i+1 for i in range(12) if m.read(s['se_overlay_ids']+i)==desired and m.read(s['image_slot']+i)==1]
 cached=bool(tags) and m.read(s['se_overlay_active']+1)==tags[0]
 if profile.engine:
  engine_tags=[i+1 for i in range(12) if m.read(s['se_overlay_ids']+i)==2 and m.read(s['image_slot']+i)==0]
  cached=cached and bool(engine_tags) and m.read(s['se_overlay_active'])==engine_tags[0]
 regs,used=m.call(s['se_history_call'],a=command,limit=2_000_000)
 if command==4:
  if cached:maximum_cached_step=max(maximum_cached_step,used)
  else:maximum_load_step=max(maximum_load_step,used)
 return regs
def h(command,error=None):
 regs=h_raw(command)
 assert bool(regs.p&1)==(error is not None),(command,hex(regs.a),regs.p,get('se_h_phase',1))
 if error is not None:assert regs.a==error,(command,hex(regs.a),error)
 return regs.a
def token(n):return read(s[n],5)
def obj_write(t,offset,data,host=0x8000):
 m.load(s['se_object_id'],t);m.load(host,data);put('se_object_offset',offset);put('se_object_length',len(data),2);put('se_object_c64',host,2);call('se_object_copy',a=0)
def load_source(t,data):
 for at in range(0,len(data),4096):obj_write(t,at,data[at:at+4096])
def obj_read(t,offset,length):
 out=bytearray()
 for i in range(0,length,1024):
  count=min(1024,length-i);m.load(s['se_object_id'],t);put('se_object_offset',offset+i);put('se_object_length',count,2);put('se_object_c64',0x8000,2);call('se_object_copy',a=1);out.extend(read(0x8000,count))
 return bytes(out)
def doc_read(at,count):put('se_doc_offset',at);put('se_doc_count',count,2);put('se_doc_c64',0x8000,2);call('se_doc_read');return read(0x8000,count)
def document(length):return b''.join(doc_read(at,min(1024,length-at)) for at in range(0,length,1024))
def journal():return obj_read(token('se_h_token'),0,get('se_h_end',2))
def published():return read(s['se_doc_roots'],256)+read(s['se_doc_length'],3)+read(s['se_doc_generation'],2)
def history_public():return read(s['se_h_end'],16)+read(s['se_h_dirty'],1)
def import_assets():
 call('se_overlay_init')
 for name in asset_images:
  image=asset_images[name];m.load(s['se_overlay_header'],image[:HEADER]);m.load(0x5000,image[HEADER:]);call('se_overlay_import')
def setup(data,banks=1,physical=256,initialize=True):
 put('se_reu_banks',physical,2);call('se_reu_provider_init');call('se_object_init');call('se_doc_init',a=banks)
 load_source(token('se_doc_original'),data);put('se_doc_source_length',len(data));call('se_doc_adopt_original')
 import_assets();call('se_history_cold')
 if initialize:h(1)
def finish():
 steps=0
 while get('se_h_phase',1):h(4);steps+=1;assert steps<1000
 return steps
def playback(command,expected,node=None):
 old_append=token('se_doc_append');identity=old_append[0]
 before_size=bytes(m.read(s[n]+identity) for n in ['object_size_lo','object_size_mid','object_size_hi'])
 started=h(command);steps=finish() if started else 0
 assert document(len(expected))==expected
 assert bytes(m.read(s[n]+identity) for n in ['object_size_lo','object_size_mid','object_size_hi'])==before_size
 if node is not None:assert get('se_h_current',4)==node,(get('se_h_current',4),node)
 assert get('se_doc_read_locks',1)==0
 return steps
def record_check(log):
 at=0;last=None;count=0
 while at<len(log):
  head=log[at:at+64];assert len(head)==64 and head[:5]==b'SEH1\x01'
  length=int.from_bytes(head[6:8],'little');body=log[at+64:at+length]
  removed=int.from_bytes(head[35:37],'little');inserted=int.from_bytes(head[37:39],'little')
  assert 0<=removed<=2048 and 0<=inserted<=1 and length==66+9*(removed+inserted)
  assert binascii.crc_hqx(head[:58]+head[60:],0xFFFF)==int.from_bytes(head[58:60],'little')
  assert binascii.crc_hqx(body,0xFFFF)==int.from_bytes(head[56:58],'little') and int.from_bytes(body[-2:],'little')==length
  before=int.from_bytes(head[8:12],'little');after=int.from_bytes(head[12:16],'little')
  assert before and after and before!=after
  if last is not None:assert before==last,(before,last)
  last=after
  assert sum(int.from_bytes(body[i*9+6:i*9+9],'little') for i in range(removed))==int.from_bytes(head[29:32],'little')
  assert sum(int.from_bytes(body[(removed+i)*9+6:(removed+i)*9+9],'little') for i in range(inserted))==int.from_bytes(head[32:35],'little')
  assert head[16:21]==token('se_doc_original') and head[21:26]==token('se_doc_append')
  at+=length;count+=1
 assert at==len(log)
 return count
def failure(command,error):
 before=published();hist=history_public();started=h_raw(command);steps=0
 while not started.p&1 and get('se_h_phase',1):
  started=h_raw(4);steps+=1;assert steps<1000
 assert started.p&1 and started.a==error,(command,hex(started.a),error)
 assert published()==before and history_public()==hist and get('se_h_phase',1)==0 and get('se_doc_read_locks',1)==0
 return steps
def edit(old,at,delete,data):
 global maximum_edit_steps,maximum_prepare_steps
 before=published();before_history=history_public();put('se_doc_edit_position',at);put('se_doc_edit_delete',delete);put('se_doc_edit_insert',len(data));put('se_h_before_caret',at);put('se_h_after_caret',at+len(data))
 if not h(2):assert not delete and not data;return old
 steps=0
 while get('se_h_phase',1)!=4:
  h(4);steps+=1;assert steps<1500
  assert published()==before and history_public()==before_history
 maximum_prepare_steps=max(maximum_prepare_steps,steps)
 for i in range(0,len(data),1024):
  chunk=data[i:i+1024];m.load(0x8000,chunk);put('se_doc_count',len(chunk),2);put('se_doc_c64',0x8000,2);h(3)
 while get('se_h_phase',1):h(4);steps+=1;assert steps<2000
 maximum_edit_steps=max(maximum_edit_steps,steps)
 expected=old[:at]+data+old[at+delete:];assert document(len(expected))==expected
 assert get('se_doc_read_locks',1)==0 and get('se_h_applied',1)==1
 return expected
try:
 m.load(0x801,profile.image[2:]);m.call(s['se_clear_state'])
 shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim)
 if profile.engine:
  setup(b'original source\r'*64,banks=2,physical=8)
 else:
  put('se_reu_banks',8,2);m.call(s['se_doc_probe'])
  call('se_reu_free',x=190);call('se_reu_free',x=191);call('se_overlay_init');call('se_history_cold')
  for name in asset_images:
   image=asset_images[name];m.load(s['se_overlay_header'],image[:HEADER]);m.load(0x5000,image[HEADER:]);call('se_overlay_import')
 h(1);assert get('se_h_ready',1)==1 and get('se_h_current',4)==1
 original=document(get('se_doc_length'));model=edit(original,0,0,b'X')
 body=journal();assert len(body)==75 and body[:4]==b'SEH1'
 assert binascii.crc_hqx(body[:58]+body[60:64],0xFFFF)==int.from_bytes(body[58:60],'little')
 assert binascii.crc_hqx(body[64:],0xFFFF)==int.from_bytes(body[56:58],'little')
 assert int.from_bytes(body[-2:],'little')==75 and get('se_h_current',4)==2 and get('se_h_dirty',1)==1
 # Restore/reapply exact source through existing immutable references.
 assert h(6)==1
 while get('se_h_phase',1):h(4)
 assert document(len(original))==original and get('se_h_current',4)==1 and get('se_h_dirty',1)==0 and get('se_h_cursor',2)==0
 assert h(7)==1
 while get('se_h_phase',1):h(4)
 assert document(len(model))==model and get('se_h_current',4)==2 and get('se_h_dirty',1)==1
 print('First journalled edit and undo/redo pass.',flush=True)
 # Adjacent typing combines source references, preserving the first before
 # node/caret and the latest after node/caret across many committed edits.
 put('se_h_group',7,1)
 for i in range(30):model=edit(model,1+i,0,bytes([65+i%26]))
 assert get('se_h_end',2)==150 and get('se_h_counter',4)==32
 h(6)
 while get('se_h_phase',1):h(4)
 assert document(len(original)+1)==b'X'+original and get('se_h_current',4)==2
 h(7)
 while get('se_h_phase',1):h(4)
 assert document(len(model))==model and get('se_h_current',4)==32
 h(8);assert get('se_h_saved',4)==32 and get('se_h_dirty',1)==0
 model=edit(model,31,0,b'after save')
 assert get('se_h_end',2)==225
 h(6)
 while get('se_h_phase',1):h(4)
 assert get('se_h_current',4)==32 and get('se_h_dirty',1)==0
 model=model[:31]+model[41:]
 # Editing after undo drops redo only at commit, and never reuses node IDs.
 model=edit(model,31,0,b'new branch')
 assert get('se_h_counter',4)==34 and h(7)==0 and get('se_h_dirty',1)==1
 print('Typing grouping, saved node and redo-branch truncation pass.',flush=True)
 # Small independent byte/version model across edits, undo/redo and branches.
 rng=random.Random(0x48495354);model=rng.randbytes(2000);setup(model)
 states=[(model,1)];index=0;counter=1;saved_id=1;random_edits=0
 for case in range(100):
  choice=rng.randrange(10)
  if choice<6:
   at=rng.randrange(len(model)+1);delete=rng.randrange(min(30,len(model)-at)+1);data=rng.randbytes(rng.randrange(25))
   model=edit(model,at,delete,data)
   if delete or data:
    counter+=1;states=states[:index+1]+[(model,counter)];index+=1;random_edits+=1
  elif choice<8 and index:
   index-=1;model,node=states[index];playback(6,model,node)
  elif choice==8 and index+1<len(states):
   index+=1;model,node=states[index];playback(7,model,node)
  else:h(8);saved_id=states[index][1]
  assert get('se_h_current',4)==states[index][1] and get('se_h_counter',4)==counter
  assert get('se_h_dirty',1)==int(states[index][1]!=saved_id)
 record_check(journal())
 print('Random edit/undo/redo/version model passes.',flush=True)
 # Cancel preparation, plus retryable missing/invalid insertion feed.
 before=published();hist=history_public();active=journal();put('se_doc_edit_position',1);put('se_doc_edit_delete',20);put('se_doc_edit_insert',3);put('se_h_before_caret',1);put('se_h_after_caret',4)
 h(2);h(4);h(5);assert published()==before and history_public()==hist and journal()==active
 assert get('se_doc_read_locks',1)==0
 put('se_doc_edit_delete',0);h(2)
 while get('se_h_phase',1)!=4:h(4)
 h(4,error=0x45);assert published()==before and history_public()==hist
 m.load(0x8000,b'12');put('se_doc_count',2,2);put('se_doc_c64',0x8000,2);h(3)
 h(3,error=0x32)
 m.load(0x8000,b'3');put('se_doc_count',1,2);h(3);finish();model=model[:1]+b'123'+model[1:]
 assert document(len(model))==model
 # Idle cancel cannot touch an unrelated core splice.
 put('se_doc_edit_position',0);put('se_doc_edit_delete',0);put('se_doc_edit_insert',1);call('se_doc_splice_begin');h(5)
 assert get('se_doc_busy',1)==1;call('se_doc_splice_cancel')
 # Source caret bounds and node exhaustion fail without consuming history.
 before=published();hist=history_public();put('se_h_before_caret',len(model)+1);h(2,error=0x32)
 assert published()==before and history_public()==hist
 put('se_h_before_caret',0);put('se_h_after_caret',len(model)+2);h(2,error=0x32)
 put('se_h_after_caret',1);old_counter=get('se_h_counter',4);put('se_h_counter',0xFFFFFFFF,4);h(2,error=0x63)
 assert published()==before;put('se_h_counter',old_counter,4)
 # CRC/header/context/reference/trailer failures all precede text publication.
 setup(b'original source');model=edit(b'original source',0,0,b'X');valid=journal();playback(6,b'original source',1)
 for offset in [4,16,56,64,len(valid)-1]:
  bad=bytearray(valid);bad[offset]^=1;obj_write(token('se_h_token'),0,bad);failure(7,0x62)
  obj_write(token('se_h_token'),0,valid)
 bad=bytearray(valid);bad[-2]^=1;bad[56:58]=binascii.crc_hqx(bad[64:],0xFFFF).to_bytes(2,'little');bad[58:60]=binascii.crc_hqx(bad[:58]+bad[60:64],0xFFFF).to_bytes(2,'little')
 obj_write(token('se_h_token'),0,bad);failure(7,0x62);obj_write(token('se_h_token'),0,valid)
 bad=bytearray(valid);bad[65:67]=b'\xff\xff';bad[56:58]=binascii.crc_hqx(bad[64:],0xFFFF).to_bytes(2,'little');bad[58:60]=binascii.crc_hqx(bad[:58]+bad[60:64],0xFFFF).to_bytes(2,'little')
 obj_write(token('se_h_token'),0,bad);failure(7,0x31);obj_write(token('se_h_token'),0,valid);playback(7,model,2)
 print('Cancel, retry and corrupted-record publication guards pass.',flush=True)
 # Byte-bounded eviction with overlap-safe forward relocation. About600 tiny
 # ungrouped records fit; undo reaches the retained base, not the original file.
 setup(b'');model=b''
 for i in range(620):model=edit(model,len(model),0,bytes([65+i%26]))
 depth=record_check(journal());assert depth==600 and get('se_h_trimmed',2)==20
 h(8);top_node=get('se_h_current',4)
 for i in range(depth):playback(6,model[:619-i])
 assert get('se_h_current',4)==21 and get('se_h_cursor',2)==0 and document(20)==model[:20]
 assert h(6)==0
 for i in range(depth):playback(7,model[:21+i])
 assert get('se_h_current',4)==top_node and get('se_h_dirty',1)==0
 for i in range(depth):playback(6,model[:619-i])
 branch=model[:20]+b'Z';edit(model[:20],20,0,b'Z')
 assert get('se_h_counter',4)==622 and get('se_h_current',4)==622 and get('se_h_dirty',1)==1 and get('se_h_end',2)==75
 assert h(7)==0 and document(len(branch))==branch
 print('Eviction,600-level undo/redo and saved IDs after branching pass.',flush=True)
 # Full1MiB document/append,2048 checked source pieces and a maximum deletion
 # record. Undo must restore all refs without appending a single source byte.
 source=rng.randbytes(1048576);reverse_source=source[::-1];setup(source,banks=16,initialize=False)
 app=token('se_doc_append');load_source(app,reverse_source);m.load(s['se_object_id'],app);put('se_object_offset',1048576);call('se_object_resize')
 orig=token('se_doc_original');meta=token('se_doc_meta');pieces=[];roots=bytearray();full_model=bytearray()
 for page in range(32):
  leaf=bytearray(1024)
  for rec in range(64):
   index_piece=page*64+rec;t=orig if index_piece%2==0 else app;data=source if index_piece%2==0 else reverse_source
   offset=(index_piece*65537+65500)%(1048576-512+1);at=rec*16
   leaf[at:at+3]=t[:3];leaf[at+3:at+6]=offset.to_bytes(3,'little');leaf[at+6:at+9]=(512).to_bytes(3,'little');leaf[at+9:at+12]=b'\xff'*3
   full_model.extend(data[offset:offset+512])
  obj_write(meta,(63-page*2)*1024,leaf,host=0x8400);roots.extend(bytes([63-page*2,64])+(32768).to_bytes(3,'little')+b'\xff'*3)
 m.load(s['se_doc_roots'],roots);put('se_doc_root_count',32,1);put('se_doc_generation',3,2);m.call(s['se_doc_invalidate'])
 # Establish the canonical graph through the full real validator before local
 # capture/reuse is admitted. This initial fixture is host-built, not a splice.
 m.call(s['se_doc_walk_reset']);count=0
 while True:
  regs,_=m.call(s['se_doc_walk_next'])
  if regs.p&1:assert regs.a==0;break
  count+=1
 assert count==2048;h(1);full_model=bytes(full_model)
 assert edit(full_model,0,len(full_model),b'')==b''
 assert get('se_h_end',2)==18498 and record_check(journal())==1
 large_undo_steps=playback(6,full_model,1);playback(7,b'',2);playback(6,full_model,1)
 assert get('se_h_current',4)==1 and get('se_h_dirty',1)==0
 print('Full1MiB/2048-reference deletion and undo/redo pass at full append.',flush=True)
 # The maximum18507-byte replacement record needs an append byte available;
 # use a checked all-original graph with empty append, not an impossible
 # insertion into the full-append fixture above.
 setup(source,banks=16,initialize=False);orig=token('se_doc_original');meta=token('se_doc_meta');roots=bytearray();largest_model=bytearray()
 for page in range(32):
  leaf=bytearray(1024)
  for rec in range(64):
   index_piece=page*64+rec;offset=(index_piece*65537+65500)%(1048576-512+1);at=rec*16
   leaf[at:at+3]=orig[:3];leaf[at+3:at+6]=offset.to_bytes(3,'little');leaf[at+6:at+9]=(512).to_bytes(3,'little');leaf[at+9:at+12]=b'\xff'*3
   largest_model.extend(source[offset:offset+512])
  obj_write(meta,(63-page*2)*1024,leaf,host=0x8400);roots.extend(bytes([63-page*2,64])+(32768).to_bytes(3,'little')+b'\xff'*3)
 m.load(s['se_doc_roots'],roots);put('se_doc_root_count',32,1);put('se_doc_generation',3,2);m.call(s['se_doc_invalidate']);m.call(s['se_doc_walk_reset'])
 checked=0
 while True:
  regs,_=m.call(s['se_doc_walk_next'])
  if regs.p&1:assert regs.a==0;break
  checked+=1
 assert checked==2048;h(1);largest_model=bytes(largest_model)
 assert edit(largest_model,0,len(largest_model),b'X')==b'X'
 assert get('se_h_end',2)==18507 and record_check(journal())==1
 playback(6,largest_model,1);playback(7,b'X',2)
 print('Maximum18507-byte replacement record and both replay directions pass.',flush=True)

 # Active capture/frame survives an unrelated command swap and shared-CRC
 # clobber, then a corrupted reload aborts and releases owned leases.
 setup(b'frame survives overlay swaps'*20);original=document(get('se_doc_length'))
 put('se_doc_edit_position',0);put('se_doc_edit_delete',20);put('se_doc_edit_insert',1);put('se_h_after_caret',1)
 before=published();hist=history_public();h(2);h(4)
 m.write(s['se_overlay_frame'],0);call('se_overlay_call',a=5,x=1,error=0x60)
 h(4) # reload edit and finish its record sealing with restored CRC state
 h(5);assert published()==before and history_public()==hist and get('se_doc_read_locks',1)==0
 h(2);h(4);m.write(s['se_overlay_frame'],0);call('se_overlay_call',a=5,x=1,error=0x60)
 cached=asset_images['hedit'][HEADER:];m.load(0x5000,bytes([cached[16]^1]));put('se_reu_c64',0x5000,2);put('se_reu_offset',16,2);put('se_reu_length',1,2);put('se_reu_logical',get('se_overlay_asset',1),1);call('se_reu_copy',a=0)
 h(4,error=0x14);assert published()==before and history_public()==hist and get('se_doc_read_locks',1)==0
 m.load(0x5000,cached[16:17]);put('se_reu_c64',0x5000,2);put('se_reu_offset',16,2);put('se_reu_length',1,2);put('se_reu_logical',get('se_overlay_asset',1),1);call('se_reu_copy',a=0)
 assert edit(original,0,20,b'!')==b'!'+original[20:]
 # Post-commit failure reports applied=1 and a latched history fault; the
 # inserted byte stays present and clear-history preserves dirty/node identity.
 setup(b'old');before=published();put('se_doc_edit_position',0);put('se_doc_edit_delete',0);put('se_doc_edit_insert',1);put('se_h_after_caret',1);h(2)
 while get('se_h_phase',1)!=4:h(4)
 m.load(0x8000,b'Z');put('se_doc_count',1,2);put('se_doc_c64',0x8000,2);h(3)
 while not get('se_h_applied',1):h(4)
 assert get('se_h_phase',1)==7 and get('se_doc_read_locks',1)==1 and published()!=before
 h(5,error=0x61);h(3,error=0x61)
 put('se_doc_edit_insert',1);call('se_doc_splice_begin',error=0x41)
 logical=m.read(s['object_extents']+get('se_h_token',1)*16);owner=m.read(s['se_reu_logical_owner']+logical);m.write(s['se_reu_logical_owner']+logical,0)
 h(4,error=0x34);m.write(s['se_reu_logical_owner']+logical,owner)
 assert get('se_h_phase',1)==0 and get('se_doc_read_locks',1)==0 and get('se_h_applied',1)==1 and get('se_h_fault',1)==0x34
 assert document(4)==b'Zold' and get('se_h_current',4)==2 and get('se_h_dirty',1)==1
 h(1,error=0x65);h(9);assert get('se_h_end',2)==0 and get('se_h_current',4)==2 and get('se_h_dirty',1)==1
 #512KiB allocation refusal is atomic. A later init succeeds without leaking.
 setup(b'small profile',banks=2,physical=8,initialize=False);reserved=call('se_reu_alloc',a=7);owners=read(s['se_reu_logical_owner'],512)
 h(1,error=1);assert get('se_h_ready',1)==0 and read(s['se_reu_logical_owner'],512)==owners
 call('se_reu_free',x=reserved);h(1);assert edit(b'small profile',0,0,b'!')==b'!small profile'
 # Old pending cleanup cannot release a new provider epoch's read lease.
 put('se_doc_edit_position',0);put('se_doc_edit_delete',1);put('se_doc_edit_insert',0);put('se_h_after_caret',0);h(2)
 put('se_reu_banks',8,2);call('se_reu_provider_init');call('se_object_init');call('se_doc_init',a=1);put('se_doc_source_length',0);call('se_doc_adopt_original');call('se_doc_read_acquire')
 h(4,error=0x18);assert get('se_doc_read_locks',1)==1 and get('se_h_phase',1)==0;call('se_doc_read_release')
 import_assets();call('se_history_cold');h(1)
 assert read(0xC600,1024)==shim
 print('Overlay reload, applied-storage fault, allocation and epoch guards pass.',flush=True)
 result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=r['sha256'],
  overlay_sha256={name:hashlib.sha256(image).hexdigest() for name,image in asset_images.items()},
  resident_binding=r['resident_binding']['digest'],random_steps=100,random_edits=random_edits,
  typing_group_characters=30,stable_saved_nodes=True,redo_branch_truncation=True,
  journal_byte_capacity=45056,small_record_bytes=75,retained_undo_records=depth,evicted_records=20,
  maximum_document_bytes=1048576,maximum_deleted_references=2048,maximum_tested_record_bytes=18507,
  full_append_undo_steps=large_undo_steps,full_append_no_growth=True,
  cancellation_and_retry=True,corrupt_record_rejections=7,reference_lifetime_rejection=True,
  private_frame_survives_overlay_swap=True,failed_reload_cleans_lease=True,
  postcommit_fault_reports_applied=True,small_reu_allocation_atomic=True,stale_cleanup_preserves_new_lease=True,
  max_cached_step_instructions=maximum_cached_step,max_load_step_instructions=maximum_load_step,
  max_edit_steps=maximum_edit_steps,max_prepare_steps=maximum_prepare_steps,shim_bytes_verified=1024,
  limitations='Controller API verified; command UI integration,native evidence and actual PAL/NTSC timing remain separate gates.')
 result.update(profile.identity);result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:m.close()
