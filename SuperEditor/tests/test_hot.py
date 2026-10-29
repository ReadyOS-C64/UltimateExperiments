"""Gap working-set + real history overlays against independent whole-byte models."""
import hashlib,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from overlays import HEADER
from engine_test_profile import Profile
profile=Profile('hot-probe','hot')
r=profile.report;s=r['symbols']
assets=profile.assets(['hwin','wedit','wplay'])
result_path=profile.result_path;result_path.unlink(missing_ok=True)
m=Machine();maximum_key=0;maximum_key_reload=0;maximum_load_step=0;maximum_flush=0;random_operations=0

def read(a,n):return bytes(m.read(a+i) for i in range(n))
def put(n,v,w=3):m.load(s[n],v.to_bytes(w,'little'))
def get(n,w=3):return int.from_bytes(read(s[n],w),'little')
def call(n,a=0,x=0,error=None):
 regs,used=m.call(s[n],a=a,x=x,limit=2_000_000)
 assert bool(regs.p&1)==(error is not None),(n,a,hex(regs.a),get('se_hot_phase',1),get('se_h_phase',1))
 if error is not None:assert regs.a==error,(n,hex(regs.a),error)
 return regs.a,used
def hot(c,error=None):return call('se_hot_call',a=c,error=error)
def h(c,error=None):return call('se_history_call',a=c,error=error)
def token(n):return read(s[n],5)
def obj_write(t,at,data):
 m.load(s['se_object_id'],t);m.load(0x8000,data);put('se_object_offset',at);put('se_object_length',len(data),2);put('se_object_c64',0x8000,2);call('se_object_copy')
def doc_read(at,count):
 put('se_doc_offset',at);put('se_doc_count',count,2);put('se_doc_c64',0x8000,2);call('se_doc_read');return read(0x8000,count)
def document():
 n=get('se_doc_length');return b''.join(doc_read(i,min(1024,n-i)) for i in range(0,n,1024))
def span():
 left=get('se_hot_left',2);right=get('se_hot_right',2)
 assert 0<=left<=right<=2048 and left+2048-right==get('se_hot_length',2)
 return read(0x9200,left)+read(0x9200+right,2048-right)
def view(base):
 start=get('se_hot_base');old=get('se_hot_old_length',2)
 return base[:start]+span()+base[start+old:]
def published():return read(s['se_doc_roots'],256)+read(s['se_doc_length'],3)+read(s['se_doc_generation'],2)
def import_assets():
 call('se_overlay_init')
 for n,data in assets.items():m.load(s['se_overlay_header'],data[:HEADER]);m.load(0x5000,data[HEADER:]);call('se_overlay_import')
def setup(data,banks=2,physical=256):
 put('se_reu_banks',physical,2);call('se_reu_provider_init');call('se_object_init');call('se_doc_init',a=banks)
 t=token('se_doc_original')
 for at in range(0,len(data),1024):obj_write(t,at,data[at:at+1024])
 put('se_doc_source_length',len(data));call('se_doc_adopt_original');import_assets();call('se_history_cold');h(1);call('se_hot_cold')
def load(caret):
 global maximum_load_step
 put('se_hot_position',caret);hot(1);steps=0
 while get('se_hot_phase',1):
  _,used=hot(2);maximum_load_step=max(maximum_load_step,used);steps+=1;assert steps<130
 assert get('se_hot_ready',1)==1 and get('se_hot_caret')==caret and get('se_doc_read_locks',1)==0
 return steps
def finish():
 global maximum_flush
 steps=0
 while get('se_hot_phase',1):hot(2);steps+=1;assert steps<2000
 maximum_flush=max(maximum_flush,steps)
 return steps
def flush():hot(8);finish();assert get('se_hot_pending',1)==0 and get('se_hot_ready',1)==1 and get('se_doc_read_locks',1)==0
def playback(command):
 h(command);steps=0
 while get('se_h_phase',1):h(4);steps+=1;assert steps<1000
 return document()
def key(command,value=None,error=None):
 global maximum_key,maximum_key_reload
 cached=m.read(s['se_overlay_active']+1)==1 # HWIN imported first, catalog tag1.
 if value is not None:put('se_hot_byte',value,1)
 result,used=hot(command,error=error)
 if error is None:
  if cached:maximum_key=max(maximum_key,used)
  else:maximum_key_reload=max(maximum_key_reload,used)
 return result
try:
 m.load(0x801,profile.image[2:]);m.call(s['se_clear_state'])
 shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim)
 outside=bytes((i*17+3)&255 for i in range(512));m.load(0x9000,outside)
 # No whole-window replacement: ordinary typing flushes just the delta and
 # uses the same history grouping/caret machinery as direct byte transactions.
 original=b'alpha\rbeta';setup(original);load(3);assert span()==original
 before=published();dma=get('se_reu_dma_calls',2);loads=get('se_overlay_loads',2)
 for c in b'XYZ':key(3,c)
 assert published()==before and get('se_reu_dma_calls',2)==dma and get('se_overlay_loads',2)==loads
 assert view(original)==b'alpXYZha\rbeta' and get('se_hot_pending',1)==1
 assert get('se_h_dirty',1)==0 # UI dirty is history dirty OR hot pending.
 flush();expected=b'alpXYZha\rbeta';assert document()==expected and get('se_h_current',4)==2 and get('se_h_end',2)==75
 assert get('se_h_before_caret')==3 and get('se_h_after_caret')==6
 assert get('se_doc_edit_position')==3 and get('se_doc_edit_delete')==0 and get('se_doc_edit_insert')==3
 assert playback(6)==original and get('se_h_caret')==3
 assert playback(7)==expected and get('se_h_caret')==6
 print('Local typing/no DMA, minimal delta and grouped history boundary pass.',flush=True)
 # Both sides/page boundaries, exact full2KiB and refusal without overwriting.
 source=bytes(i&255 for i in range(4096));setup(source);load(768);model=source;caret=768
 assert get('se_hot_base')==256 and span()==source[256:1280]
 for _ in range(300):key(6);caret-=1
 for c in range(1024):key(3,c&255);model=model[:caret]+bytes([c&255])+model[caret:];caret+=1
 assert get('se_hot_length',2)==2048 and get('se_hot_left',2)==get('se_hot_right',2)
 old=span();key(3,33,error=0x73);assert span()==old and view(source)==model
 for _ in range(260):key(4);model=model[:caret-1]+model[caret:];caret-=1
 for _ in range(250):key(7);caret+=1
 for _ in range(260):key(5);model=model[:caret]+model[caret+1:]
 assert view(source)==model and get('se_hot_caret')==caret
 flush();assert document()==model
 assert playback(6)==source and playback(7)==model
 print('Gap/page movement, exact full capacity and cross-gap flush pass.',flush=True)
 # Multi-page source past64KiB; private pending view and conservative change
 # interval checked after every random mutation/movement. Foreign read/cache
 # activity is allowed; it cannot mutate the gap or committed root.
 rng=random.Random(0x474150);source=rng.randbytes(70000);setup(source);committed=source;versions=[source]
 for cycle in range(24):
  caret=rng.randrange(len(committed)+1);load(caret);model=committed;root=published();dma=get('se_reu_dma_calls',2)
  for event in range(60):
   lo=get('se_hot_base');n=get('se_hot_length',2);p=caret-lo;choice=rng.randrange(5)
   if choice==0 and n<2048:
    c=rng.randrange(256);key(3,c);model=model[:caret]+bytes([c])+model[caret:];caret+=1
   elif choice==1 and p:
    key(4);model=model[:caret-1]+model[caret:];caret-=1
   elif choice==2 and p<n:
    key(5);model=model[:caret]+model[caret+1:]
   elif choice==3 and p:key(6);caret-=1
   elif p<n:key(7);caret+=1
   assert view(committed)==model and get('se_hot_caret')==caret and published()==root
   random_operations+=1
  assert get('se_reu_dma_calls',2)==dma
  # Reject reload/close while local edits are pending, preserving input.
  if get('se_hot_pending',1):
   old=span();put('se_hot_position',0);hot(1,error=0x71);hot(10,error=0x71);assert span()==old
  # Corrupt the shared IO/leaf cache through a legal document read, not a gap.
  assert doc_read(65530,min(32,len(committed)-65530))==committed[65530:65562]
  flush();assert document()==model;committed=model;versions.append(model)
 for prior in reversed(versions[:-1]):assert playback(6)==prior
 for later in versions[1:]:assert playback(7)==later
 print('1440 random gap operations and24 flush/undo/redo roundtrips past64KiB pass.',flush=True)
 # Load cancellation releases only its own lease. Dirty flush cancellation
 # preserves pending source bytes, original document and active history.
 setup(b'0123456789'*200);put('se_hot_position',900);hot(1);hot(1,error=0x71);hot(3,error=0x71);assert get('se_hot_phase',1)==1;call('se_doc_read_acquire');hot(9)
 assert get('se_doc_read_locks',1)==1 and get('se_hot_phase',1)==0;call('se_doc_read_release');load(900)
 key(4);key(3,65);pending_view=view(document());old=published();old_node=get('se_h_current',4)
 hot(8);hot(1,error=0x71);hot(3,error=0x71);assert get('se_hot_phase',1)==2;hot(2);hot(9)
 assert published()==old and get('se_h_current',4)==old_node and get('se_hot_pending',1)==1 and get('se_doc_read_locks',1)==0
 assert view(document())==pending_view
 flush();assert document()==pending_view
 # Zero-byte dirty delta (insert then backspace) safely clears local pending
 # without generating a history node or consuming append space.
 setup(b'');load(0);key(6,error=0x72);key(7,error=0x72);key(4,error=0x72);key(5,error=0x72)
 key(3,65);key(4);flush();assert document()==b'' and get('se_h_current',4)==1 and get('se_h_end',2)==0
 # No-commit admission failures preserve pending input, so removing it can
 # recover an append/document-capacity error without typing it again.
 source=b'A'*65536;setup(source,banks=1);load(65000);key(3,66);pending_view=view(source)
 hot(8,error=0x32);assert document()==source and get('se_hot_pending',1)==1 and view(source)==pending_view
 key(4);flush();assert document()==source
 # Overlay eviction between asynchronous reads: frame remains resident.
 setup(b'fixture'*300);put('se_hot_position',900);hot(1);hot(2);h(10);finish();assert span()==(b'fixture'*300)[388:1412]
 # Contiguous flushes retain typing grouping, but SAVED closes the boundary.
 setup(b'base');load(0);put('se_hot_group',1,1)
 key(3,65);flush();key(3,66);flush();assert get('se_h_end',2)==75
 h(8);key(3,67);flush();assert get('se_h_end',2)==150 and document()==b'ABCbase'
 assert playback(6)==b'ABbase' and get('se_h_dirty',1)==0
 # A stale load's cancel cannot release a foreign new-epoch lease.
 load(2)

 put('se_hot_position',1);hot(1)
 put('se_reu_banks',8,2);call('se_reu_provider_init');call('se_object_init');call('se_doc_init',a=1);put('se_doc_source_length',0);call('se_doc_adopt_original');call('se_doc_read_acquire')
 hot(9);assert get('se_doc_read_locks',1)==1;call('se_doc_read_release')
 # Evicted HWIN reload failure aborts its load lease without touching any
 # current text, and explicitly repaired cache bytes permit a later retry.
 setup(b'load error'*200);put('se_hot_position',400);hot(1);hot(2);h(10)
 asset_bank=get('se_overlay_asset',1)
 def patch_cache(value):
  put('se_reu_logical',asset_bank,1);put('se_reu_offset',20,2);put('se_reu_length',1,2);put('se_reu_c64',0x8000,2)
  m.write(0x8000,value);call('se_reu_copy',a=0)
 patch_cache(assets['hwin'][HEADER+20]^1)
 hot(2,error=0x14);assert get('se_doc_read_locks',1)==0 and get('se_hot_phase',1)==0 and get('se_hot_ready',1)==0
 patch_cache(assets['hwin'][HEADER+20]);load(400)
 # If a caller violates the flush-before-mutation rule, refuse all further
 # local mutations by context while retaining the pending bytes for recovery.
 setup(b'base');load(0);key(3,65);flush();key(3,66);pending=span()
 playback(6);key(3,67,error=0x74)
 assert span()==pending and get('se_hot_pending',1)==1 and document()==b'base'
 # Postcommit failure invalidates stale RAM view, preserves applied state and
 # exact authoritative text; consumers must not retry the pending insertion.
 setup(b'old');load(0);key(3,90);hot(8)
 while not get('se_h_applied',1):hot(2)
 hot(9,error=0x61)
 ident=token('se_h_token')[0];logical=m.read(s['object_extents']+ident*16);owner=m.read(s['se_reu_logical_owner']+logical)
 m.write(s['se_reu_logical_owner']+logical,0);hot(2,error=0x34);m.write(s['se_reu_logical_owner']+logical,owner)
 assert document()==b'Zold' and get('se_hot_pending',1)==0 and get('se_hot_ready',1)==0
 assert get('se_h_applied',1)==1 and get('se_h_fault',1)==0x34 and get('se_hot_fault',1)==0x34 and get('se_doc_read_locks',1)==0
 assert read(0xC600,1024)==shim and read(0x9000,512)==outside
 print('Cancel,capacity,epoch and applied-fault recovery boundaries pass.',flush=True)
 result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],
  overlay_sha256={n:hashlib.sha256(data).hexdigest() for n,data in assets.items()},gap_bytes=2048,baseline_bytes=1024,
  bounded_load_packet_bytes=128,random_gap_operations=random_operations,random_flush_roundtrips=24,source_bytes=70000,
  typing_dma_calls=0,typing_overlay_swaps=0,minimal_delta=True,exact_full_gap=True,cancel_preserves_pending=True,
  capacity_failure_preserves_pending=True,stale_cancel_preserves_foreign_lease=True,applied_fault_invalidates_pending=True,
  max_cached_key_instructions=maximum_key,max_key_reload_instructions=maximum_key_reload,max_load_step_instructions=maximum_load_step,max_flush_steps=maximum_flush,
  shim_bytes_verified=1024,adjacent_sentinel_bytes=512,
  limitations='CPU working-set API; native D81/UI integration and PAL/NTSC timing remain open.')
 result.update(profile.identity);result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:m.close()
