"""Independent source/visual-row model for actual indexed navigation commands."""
import bisect,hashlib,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from cpu_editor import startup,NAMES
from overlays import HEADER
r=json.loads((ROOT/'build/editor-report.json').read_text());s=r['symbols'];assets={n:(ROOT/f'build/overlays/{n}.seo').read_bytes() for n in NAMES}
result_path=ROOT/'build'/('navigation-cache-test-result.json' if '--cache-check' in sys.argv else 'navigation-test-result.json');result_path.unlink(missing_ok=True)
m=Machine();max_service=0;max_steps=0;random_actions=0;geometry_checks=0;cache_checks=0;cache_source=None;cache_lines=[]

def read(a,n):return bytes(m.read(a+i) for i in range(n))
def get(n,w=3):return int.from_bytes(read(s[n],w),'little')
def put(n,v,w=3):m.load(s[n],v.to_bytes(w,'little'))
def call(n,a=0,error=None):
 global max_service
 regs,used=m.call(s[n],a=a,limit=2_000_000)
 if n=='se_editor_service':max_service=max(max_service,used)
 if error is not None:assert regs.p&1 and regs.a==error,(n,regs.a,error)
 return regs

def check_cache():
 global cache_checks
 # Derived cache assertions use an independently built list of all CR starts.
 # Restrict to the exact unedited fixture generation; edits are separately
 # checked by complete document/index models below.
 if cache_source is None or get('se_doc_generation',2)!=2 or not get('se_i_ready',1):return
 count=get('se_n_cache_count',1)
 if not count:return
 head=get('se_n_cache_head',1);base=get('se_n_cache_base');end=get('se_n_cache_end')
 assert 1<=count<=25 and head<25 and end<=len(cache_source),(count,head,base,end)
 assert base+count<=len(cache_lines),(base,count,len(cache_lines))
 starts=[int.from_bytes(read(s['se_n_cache_starts']+3*((head+i)%25),3),'little') for i in range(count)]
 assert starts==cache_lines[base:base+count],(base,starts,cache_lines[base:base+count])
 assert starts[-1]<=end and bisect.bisect_right(cache_lines,end)-1==base+count-1,(starts,end,base)
 cache_checks+=1

def settle(render=False,error=0):
 global max_steps
 steps=0
 while get('se_e_job',1):
  call('se_editor_service');steps+=1;assert steps<20000,(get('se_n_phase',1),get('se_i_scan'),get('se_n_scan'),get('se_n_query'))
 assert get('se_e_error',1)==error,(hex(get('se_e_error',1)),error)
 assert get('se_doc_read_locks',1)==0 and get('se_n_owned',1)==0 and get('se_v_nav_busy',1)==0
 if render:
  call('se_editor_render')
  assert get('se_v_seen',1)==1,'successful navigation must reveal the caret'
 check_cache()
 max_steps=max(max_steps,steps);return steps

def command(c,render=True,error=0):call('se_editor_command',c);return settle(render,error)
def key(c,render=False):put('se_e_key',c,1);call('se_editor_input');return settle(render)
def document():
 out=bytearray();length=get('se_doc_length')
 for i in range(0,length,1024):
  count=min(1024,length-i);put('se_doc_offset',i);put('se_doc_count',count,2);put('se_doc_c64',0x8000,2)
  regs=call('se_doc_read');assert not regs.p&1;out.extend(read(0x8000,count))
 return bytes(out)
def setup(data,banks=2):
 global cache_source,cache_lines
 cache_source=None
 call('se_clear_state');put('se_reu_banks',256,2)
 for name,a in [('se_reu_provider_init',0),('se_object_init',0),('se_overlay_init',0),('se_doc_init',banks)]:assert not call(name,a).p&1
 t=read(s['se_doc_original'],5)
 for i in range(0,len(data),1024):
  chunk=data[i:i+1024];m.load(s['se_object_id'],t);m.load(0x8000,chunk);put('se_object_offset',i);put('se_object_length',len(chunk),2);put('se_object_c64',0x8000,2);assert not call('se_object_copy').p&1
 put('se_doc_source_length',len(data));assert not call('se_doc_adopt_original').p&1
 for image in assets.values():m.load(s['se_overlay_header'],image[:HEADER]);m.load(0x5000,image[HEADER:]);assert not call('se_overlay_import').p&1
 for name in ['se_history_cold','se_hot_cold']:assert not call(name).p&1
 assert not call('se_history_call',1).p&1
 put('se_hot_group',1,1);position(0);call('se_editor_render')
 cache_source=data;cache_lines=[0]+[i+1 for i,v in enumerate(data) if v==13]
def position(p):
 # Public clean-cache reposition, used only for fixtures/goto-equivalent anchors.
 put('se_hot_position',p);assert not call('se_hot_call',1).p&1
 put('se_e_job',1,1);settle()
def rows(data,width=40):
 result=[];start=pos=col=0
 for value in data:
  if value==13:result.append((start,pos));pos+=1;start=pos;col=0
  else:
   pos+=1;col+=1
   if col==width:result.append((start,pos-1));start=pos;col=0
 result.append((start,len(data)))
 return result

def model(c,data,caret,preferred,layout):
 if c in (36,37,38,39):
  starts=[a for a,b in layout];index=bisect.bisect_right(starts,caret)-1
  if preferred is None:preferred=caret-layout[index][0]
  delta={36:-1,37:1,38:-21,39:21}[c];target=index+delta
  if target<0:return 0,preferred
  if target>=len(layout):return len(data),preferred
  start,end=layout[target];return start+min(preferred,end-start),preferred
 start=data.rfind(b'\r',0,caret)+1;end=data.find(b'\r',caret);end=len(data) if end<0 else end
 return {32:start,33:end,34:0,35:len(data),40:max(start,caret-40),41:min(end,caret+40)}[c],None
def check_viewport(data,expected_top=None,expected_row=None):
 global geometry_checks
 # VIEW stores22 source STARTS, with the end anchor in separately appended BSS.
 # Build the complete source row layout independently; padding after EOF repeats
 # EOF, and a full40-byte row followed byCR has its own empty CR row.
 layout=rows(data);starts=[a for a,b in layout];top=get('se_v_top')
 assert top in starts,('unaligned viewport',top,starts[:30])
 index=starts.index(top)
 expected=(starts[index:index+22]+[len(data)]*22)[:22]
 actual=[int.from_bytes(read(s['se_v_rows']+3*i,3),'little') for i in range(22)]
 bottom=starts[index+22] if index+22<len(starts) else len(data)
 assert actual==expected,('22 body starts',actual,expected)
 assert get('se_v_bottom')==bottom,('separate bottom anchor',get('se_v_bottom'),bottom)
 caret=get('se_hot_caret');row=bisect.bisect_right(starts,caret)-1-index
 assert 0<=row<22 and get('se_v_seen',1)==1,('caret outside22 rows',caret,row,top)
 assert get('se_v_caret_row',1)==row,('caret row',get('se_v_caret_row',1),row)
 if expected_top is not None:assert top==expected_top,('top anchor',top,expected_top)
 if expected_row is not None:assert row==expected_row,('body row',row,expected_row)
 geometry_checks+=1

try:
 shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim);startup(m,s,assets);settle()
 sample=document();setup(b'ABCDEFGHIJ\rx\r123456789012345\r\rTAIL')
 for _ in range(8):command(2)
 expected=[12,21,12,8]
 for c,p in zip([37,37,36,36],expected):command(c);assert get('se_hot_caret')==p,(c,get('se_hot_caret'),p)
 assert get('se_n_preferred',1)==8
 # The reclaimed screen row23 is body index21; a page is21 row transitions.
 # First page lands there without scrolling, second page reveals21 predecessors.
 data=b'\r'.join(bytes([65+i%26])*5 for i in range(50));setup(data)
 check_viewport(data,0,0)
 command(39);assert get('se_hot_caret')==21*6;check_viewport(data,0,21)
 command(39);assert get('se_hot_caret')==42*6;check_viewport(data,21*6,21)
 command(38);assert get('se_hot_caret')==21*6;check_viewport(data,21*6,0)
 command(38);assert get('se_hot_caret')==0;check_viewport(data,0,0)
 command(35);check_viewport(data,28*6,21)
 # Exact-width EOF and trailingCR each create a caret row. With22 visible
 # starts, EOF at row21 fits; row22 requires exactly one row of reveal.
 for data,top,row in [(b'',0,0),(b'X'*840,0,21),(b'X'*879,0,21),
                      (b'X'*880,40,21),(b'X'*881,40,21),
                      (b'X'*919,40,21),(b'X'*929,80,21),
                      (b'X\r'*21,0,21),(b'X\r'*22,2,21),
                      (b'X'*40+b'\r'*22,41,21)]:
  setup(data);command(35);check_viewport(data,top,row)
 print('22 body anchors, separate bottom,21-row pages/reveal and reclaimed last row/EOF pass.',flush=True)
 # Randomized full command pipeline against a separate row builder, including
 # empty, short, exact-width and wrapped source lines, all clamp directions.
 rng=random.Random(0x4E4156);data=b'\r'.join(bytes([65+i%26])*rng.choice([0,1,7,39,40,41,79,80,81,150]) for i in range(100))+b'\r'
 setup(data);layout=rows(data);caret=0;preferred=None
 for case in range(600):
  c=rng.choice([36,37,38,39,32,33,34,35,40,41]);caret,preferred=model(c,data,caret,preferred,layout)
  command(c);assert get('se_hot_caret')==caret,(case,c,get('se_hot_caret'),caret,preferred)
  if preferred is not None:assert get('se_n_preferred',1)==preferred
  random_actions+=1
 assert document()==data
 print('Preferred-column fixture and600 randomized row/page/line/jump commands pass.',flush=True)
 # Checkpoints on either side of aCR exactly at an8KiB boundary have different
 # line-start metadata. Independently validate every populated packed record.
 for cr in [8191,8192]:
  data=b'A'*cr+b'\r'+b'B'*200;setup(data);command(35)
  for i in range(get('se_i_count',1)):
   raw=read(0x8D00+i*9,9);offset=int.from_bytes(raw[:3],'little');line=int.from_bytes(raw[3:6],'little');number=int.from_bytes(raw[6:9],'little')
   assert offset==i*8192 and line==data.rfind(b'\r',0,offset)+1 and number==data[:offset].count(13),(cr,i,raw.hex())
 data=b'\r'*65553;setup(data);command(35);assert get('se_i_number')==65553
 command(36);assert get('se_hot_caret')==65552
 print('Exact8KiB/CR checkpoints and24-bit line numbers beyond65535 pass.',flush=True)
 # One large index pass is retained. Near-EOF typing invalidates only the tail,
 # so the following vertical move needs at most one checkpoint stride to rescan.
 data=b'A'*(1048576-32);setup(data,banks=16);large_steps=command(35)
 assert get('se_i_count',1)==128 and get('se_i_scan')==len(data)
 key(ord('X'));near_end_steps=command(36)
 assert near_end_steps<150,(near_end_steps,get('se_i_count',1),get('se_i_scan'))
 assert get('se_i_count',1)==128 and document()==data+b'X'
 command(16);assert document()==data
 command(35);assert get('se_i_scan')==len(data)
 print('1MiB-profile sparse index and near-EOF edit/replay preserve indexed prefix.',flush=True)
 # Middle edit keeps earlier checkpoints; beginning edit invalidates every
 # derived source/line number after it, including across history replay.
 data=b'R'*100000;setup(data);command(35);assert get('se_i_count',1)==13
 position(50000);key(ord('X'));command(32)
 assert get('se_i_count',1)==7 and get('se_i_scan')==50001 and get('se_hot_caret')==0
 command(16);assert document()==data and get('se_i_count',1)==7
 command(35);command(34);key(13);command(37)
 assert get('se_i_count',1)==1 and document()==b'\r'+data
 command(16);assert document()==data
 # A source scan is cancelable through the real event-loop route. Only a
 # queued RUN/STOP at the head (or RESTORE pending) is consumed out of a job.
 setup(b'Q'*70000);call('se_editor_command',35);assert get('se_n_owned',1)==1
 m.write(s['se_input_chars'],3);put('se_input_head',1,1);put('se_input_tail',0,1)
 call('se_editor_service');assert get('se_e_job',1)==0 and get('se_doc_read_locks',1)==0 and get('se_key_sequence',2)==1 and get('se_hot_caret')==0
 # Evicted C navigation checksum failure must release the source lease through
 # resident cleanup, preserving document and current caret.
 call('se_editor_command',35);call('se_editor_service')
 assert get('se_doc_read_locks',1)==1
 call('se_history_call',10) #legitimate C eviction
 index=next(i for i in range(12) if m.read(s['se_overlay_ids']+i)==8 and m.read(s['image_slot']+i)==1)
 def patch(value):
  put('se_reu_logical',get('se_overlay_asset',1),1);put('se_reu_offset',index*4096+20,2);put('se_reu_length',1,2);put('se_reu_c64',0x5000,2);m.write(0x5000,value);assert not call('se_reu_copy').p&1
 patch(assets['navigate'][HEADER+20]^1);call('se_editor_service');assert get('se_e_error',1)==0x14
 assert get('se_e_job',1)==0 and get('se_doc_read_locks',1)==0 and get('se_i_ready',1)==0 and get('se_hot_caret')==0
 patch(assets['navigate'][HEADER+20]);put('se_e_error',0,1);command(35)
 # Bad derived offsets fail boundedly rather than walking past target/EOF.
 command(34);put('se_e_error',0,1);m.load(0x8D00,(100).to_bytes(3,'little'));put('se_n_cache_count',0,1);command(32,error=0x7B)
 assert get('se_i_ready',1)==0 and get('se_doc_read_locks',1)==0
 put('se_e_error',0,1);command(32)
 # Old cancellation must not release a new provider epoch's foreign lease.
 call('se_editor_command',35);assert get('se_n_owned',1)==1
 put('se_reu_banks',8,2)
 for name,a in [('se_reu_provider_init',0),('se_object_init',0),('se_doc_init',1)]:assert not call(name,a).p&1
 put('se_doc_source_length',0);assert not call('se_doc_adopt_original').p&1;assert not call('se_doc_read_acquire').p&1
 call('se_navigation_call',3);assert get('se_doc_read_locks',1)==1
 call('se_doc_read_release');call('se_view_init',error=0x74)
 assert read(0xC600,1024)==shim
 print('Prefix invalidation, cancel/reload/index corruption and epoch guards pass.',flush=True)
 result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],overlay_sha256={n:hashlib.sha256(v).hexdigest() for n,v in assets.items()},random_commands=random_actions,preferred_column=True,page_rows=21,body_rows=22,status_screen_row=24,separate_bottom_anchor=True,viewport_geometry_checks=geometry_checks,contiguous_line_cache=25,independent_cache_invariant_checks=cache_checks,checkpoint_records=128,checkpoint_bytes=9,stride_bytes=8192,maximum_source_bytes=1048576-32,line_number_test=65553,large_index_job_steps=large_steps,near_eof_edit_navigation_steps=near_end_steps,prefix_invalidation=True,cancel_and_reload_cleanup=True,corrupt_derived_index_rejected=True,stale_epoch_lease_preserved=True,max_service_instructions=max_service,max_job_steps=max_steps,shim_bytes_verified=1024,limitations='CPU command/index model; native navigation screenshots and normal PAL/NTSC timing separate.')
 result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:m.close()
