"""R2 nested-call, binding/state identity, eviction and loader-failure cleanup."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from cpu_editor import startup,NAMES
r=json.loads((ROOT/'build/editor-report.json').read_text());s=r['symbols'];assets={n:(ROOT/f'build/overlays/{n}.seo').read_bytes() for n in NAMES}
from overlays import HEADER
m=Machine();result_path=ROOT/'build/engine-admission-result.json';result_path.unlink(missing_ok=True)
def read(a,n):return bytes(m.read(a+i) for i in range(n))
def get(n,w=3):return int.from_bytes(read(s[n],w),'little')
def put(n,v,w=3):m.load(s[n],v.to_bytes(w,'little'))
def call(n,a=0,x=0,error=None):
 regs,_=m.call(s[n],a=a,x=x,limit=2_000_000)
 if n=='se_editor_service':
  assert get('se_e_error',1)==(error or 0),(n,get('se_e_error',1),error)
 else:assert bool(regs.p&1)==(error is not None),(n,hex(regs.a),error)
 if error is not None:assert regs.a==error,(hex(regs.a),error)
 return regs.a

def reset():
 startup(m,s,assets)
 while get('se_e_job',1):call('se_editor_service')
 call('se_editor_render')
 return read(s['se_doc_roots'],256)+read(s['se_doc_length'],3)+read(s['se_doc_generation'],2)
def published():return read(s['se_doc_roots'],256)+read(s['se_doc_length'],3)+read(s['se_doc_generation'],2)
def document():
 out=bytearray();length=get('se_doc_length')
 for i in range(0,length,1024):
  count=min(1024,length-i);put('se_doc_offset',i);put('se_doc_count',count,2);put('se_doc_c64',0x8000,2);call('se_doc_read');out.extend(read(0x8000,count))
 return bytes(out)
def catalog():
 return next(i for i in range(12) if m.read(s['se_overlay_ids']+i)==2 and m.read(s['image_slot']+i)==0)
def patch_engine(corrupt):
 index=catalog();put('se_reu_logical',get('se_overlay_asset',1),1);put('se_reu_offset',index*4096+20,2);put('se_reu_length',1,2);put('se_reu_c64',0x5000,2)
 m.write(0x5000,assets['engine'][HEADER+20]^(1 if corrupt else 0));call('se_reu_copy')
def type_pending(data):
 for value in data:put('se_hot_byte',value,1);call('se_hot_call',3)
def finish():
 steps=0
 while get('se_hot_phase',1):call('se_hot_call',2);steps+=1;assert steps<2000
try:
 shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim)
 before=reset();original=document();old_exec=read(0xA000,4096)
 frame=bytes((0xA5+i*17)&255 for i in range(16));m.load(s['se_overlay_frame'],frame)
 put('se_doc_edit_position',0);put('se_doc_edit_delete',0);put('se_doc_edit_insert',1)
 # Unknown engine command and disallowed renderer->renderer nesting preserve
 # shared parent frame, executable code and source publication.
 m.write(s['se_overlay_busy'],1);call('se_doc_splice_begin',error=0x19);m.write(s['se_overlay_busy'],0)
 assert read(s['se_overlay_frame'],16)==frame and published()==before
 patch_engine(True);call('se_doc_splice_begin',error=0x14)
 assert read(s['se_overlay_frame'],16)==frame and read(0xA000,4096)==old_exec and published()==before and get('se_doc_busy',1)==0
 patch_engine(False);assert call('se_doc_splice_begin')==1 and read(s['se_overlay_frame'],16)==frame
 # Cancel has no asset dependency and performs no DMA even when engine missing.
 index=catalog();m.write(s['se_overlay_ids']+index,0);dma=get('se_reu_dma_calls',2);call('se_doc_splice_cancel')
 assert get('se_doc_busy',1)==0 and get('se_reu_dma_calls',2)==dma and published()==before
 m.write(s['se_overlay_ids']+index,2)
 # R2 step must clean the outer C edit and hot job after a failed reload.
 # Render an actual pending view between preparation and apply to evict R2.
 reset();original=document();before=published();type_pending(b'pending text')
 call('se_hot_call',8)
 while get('se_h_phase',1)!=4:call('se_hot_call',2)
 call('se_hot_call',2) #feed insertion through real C->R path
 assert get('se_doc_busy',1)==1 and get('se_h_applied',1)==0
 call('se_editor_render');old_exec=read(0xA000,4096);patch_engine(True)
 call('se_hot_call',2,error=0x14)
 assert published()==before and document()==original and read(0xA000,4096)==old_exec
 assert get('se_hot_pending',1)==1 and get('se_hot_ready',1)==1 and get('se_hot_phase',1)==0
 assert get('se_doc_busy',1)==0 and get('se_doc_read_locks',1)==0 and get('se_h_phase',1)==0
 assert read(s['se_h_owned_lease'],3)==bytes(3) and get('se_h_current',4)==1
 patch_engine(False);call('se_hot_call',8);finish()
 assert document()==b'pending text'+original and get('se_h_current',4)==2 and get('se_h_end',2)==75
 assert get('se_overlay_busy',1)==get('se_overlay_busy',2)==0
 # Data/ZP addresses survive the split. The old immutable source editor report
 # records the complete prior layout, not an estimate or relocated frame.
 old=json.loads((ROOT/'agentsworking/evidence/M3/editor40-final/editor-report.json').read_text())
 for name in ['ZEROPAGE','DOCSTATE']:
  assert next(a for a in old['segments'] if a['name']==name)==next(a for a in r['segments'] if a['name']==name),name
 old_objects=next(a for a in old['segments'] if a['name']=='OBJECTS')
 new_objects=next(a for a in r['segments'] if a['name']=='OBJECTS')
 assert new_objects['start']==old_objects['start'] and s['se_clip_token']==old_objects['end']+1
 assert new_objects['end']<0xA000
 old_bss=next(a for a in old['segments'] if a['name']=='BSS')
 new_bss=next(a for a in r['segments'] if a['name']=='BSS')
 assert new_bss['start']==old_bss['start'] and s['se_s_active']==old_bss['end']+1
 assert new_bss['end']<0xC600
 checked=0
 for name,address in old['symbols'].items():
  if (old_bss['start']<=address<=old_bss['end']) or (0x9A00<=address<0xA000 and name.startswith(('se_doc_','se_h_','se_hot_','object_'))) or (0x8C00<=address<=0x8CAA and name.startswith(('se_e_','se_v_'))):
   assert s[name]==address,(name,address,s[name]);checked+=1
 binding=json.loads((ROOT/'build/engine-bindings.json').read_text());assert binding['resident_binding']==r['resident_binding']['digest']
 assert binding['imports']['pending']['resident_symbol']=='se_engine_emit_pending'
 for name in ['se_doc_splice_begin','se_doc_splice_local_begin','se_doc_splice_feed','se_doc_splice_step','se_doc_splice_refs_begin','se_doc_splice_local_refs_begin']:
  assert name not in binding['imports'] and name in binding['engine_exports'] and s[name]<0x4000
 assert s['se_doc_splice_cancel']<0x4000 and read(0xC600,1024)==shim
 result=dict(status='passed',prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],engine_payload_bytes=len(assets['engine'])-HEADER,engine_sha256=hashlib.sha256(assets['engine']).hexdigest(),resident_core_end=r['cold_end_exclusive'],free_core_bytes=0x4000-r['cold_end_exclusive'],persistent_fields_same_address=checked,protected_state_zp_prefix_unchanged=True,appended_bss_bytes=new_bss['size']-old_bss['size'],appended_objects_bytes=new_objects['size']-old_objects['size'],existing_view_fields_same_address=True,checked_link_imports=len(binding['imports']),internal_exports=len(binding['engine_exports']),parent_frame_and_carry_preserved=True,same_slot_nesting_refused=True,failed_reload_preserves_executable_and_source=True,resident_cancel_without_dma=True,outer_c_job_and_lease_cleanup=True,pending_text_retry_exact_once=True,shim_bytes_verified=1024)
 result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:m.close()
