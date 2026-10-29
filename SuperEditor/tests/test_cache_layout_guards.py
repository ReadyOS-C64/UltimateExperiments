"""Private R34 memo refusals/cancel and actualW_LOAD identity qualification."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,json,sys,hashlib
import test_cache_layout as lane
ROOT=lane.ROOT;geos=lane.geos;semantic=lane.semantic
S=lane.STATE

def run(out,base):
 out.mkdir(parents=True);print('RUN',out,flush=True)
 image=lane.build(out/'component',base);identity=json.loads((base/'freeze.json').read_text());geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=base;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);f=geos.Fixture(out,base,dll,True);cases=[];timings=[]
 def whole():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(f.m.handle,len(b),b);return b.raw
 def invoke(op):
  f.put('se_overlay_frame',op,1);r,n=f.fast_call(f.s['se_overlay_call'],a=34,x=0);timings.append(n);return r,n
 def drain(op):
  r,n=invoke(op);count=1;total=n
  while not r.p&1 and r.a==1:r,n=invoke(18);count+=1;total+=n;assert count<10000
  return r,count,total
 def import_component():
  f.m.load(f.s['se_overlay_header'],image[:36]);f.m.load(0x5000,image[36:]);assert not f.call('se_overlay_import').p&1
 def current():return f.canonical(),f.read(0xC600,1024),f.read(0x6000,8000)+f.read(0x4000,1000),f.get('se_doc_read_locks',1)
 def store(logical,offset,data):
  # Explicit checked input-fault transport / fixture rollback, not product IO.
  for i in range(0,len(data),1024):
   piece=data[i:i+1024];f.m.load(0x8000,piece);f.put('se_reu_logical',logical,1);f.put('se_reu_offset',offset+i,2);f.put('se_reu_c64',0x8000,2);f.put('se_reu_length',len(piece),2);assert not f.call('se_reu_copy',0).p&1
  f.call('se_doc_invalidate')
 def fs_snapshot():
  f.put('se_f_owner',4,1);f.put('se_overlay_frame',0,1);r,n=f.fast_call(f.s['se_overlay_call'],a=14,x=0);assert not r.p&1
  result=f.read(f.s['se_fs_identity'],59);assert not f.call('se_fs_end').p&1;f.put('se_f_owner',0,1);return result
 def capture(data,tag,top=None,pan=None):
  f.source(data);f.command(99)
  if top is not None:f.position(top);f.put('se_v_top',top)
  if pan is not None:f.command(77);f.put('se_l_pan',pan);f.put('se_l_manual',1,1)
  f.render();import_component();raw,p=f.raw_cache();before=whole();before_state=current();f.put('se_f_owner',4,1);f.m.load(S,bytes(64));r,count,total=drain(16);assert not r.p&1 and r.a==0,(tag,r.a,r.p)
  raw2,_=f.raw_cache();payload=lane.packet_payload(raw);packed=lane.stream(raw2);assert packed[320:320+len(payload)]==payload,(tag,'fullpacketidentity')
  assert current()==before_state and f.merged()==data
  physical=p*65536;cursor=0;after=whole()
  for a,b in lane.SPANS:assert before[cursor:physical+a]==after[cursor:physical+a];cursor=physical+b
  assert before[cursor:]==after[cursor:]
  cases.append(dict(tag=tag,kind='capture',rows=raw[1],max_count=max(int.from_bytes(raw[0x20c+i*0x800:0x20e+i*0x800],'little')for i in range(raw[1])),payload=len(payload),steps=count,instructions=total))
  (out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
  print('PASS',tag,'rows',raw[1],'payload',len(payload),'steps',count,'instructions',total,flush=True)
  return raw,raw2,p
 try:
  source=geos.native_text('# Heading\rA **bold** paragraph.\r:::basic\r10 PRINT "Hi"\r:::\rTail.\r')
  raw,stored,p=capture(source,'mixed')
  handle=f.get('se_gc_handle',1);ram=f.read(0,65536)
  def reset():
   f.m.load(2,ram[2:0xD000]);store(handle,0,stored);f.m.load(S,bytes(64));f.m.load(S+26,raw[32:35]);f.put('se_f_owner',4,1)
  def reject(tag,cpu=(),fe=None,owner=False):
   reset()
   if fe is not None:
    offset=fe;store(handle,offset,bytes([stored[offset]^1]))
   for a,v in cpu:f.m.write(a,v)
   before=whole();stable=current();opaque=f.read(0x8880,320)+f.read(0x8D00,1076)
   r,count,total=drain(17)
   assert (r.p&1)or r.a==2,(tag,r.a,r.p,count)
   assert whole()==before and current()==stable,(tag,'refusal writes canonical/REU/VIC/shim/lease')
   if owner:assert f.read(0x8880,320)+f.read(0x8D00,1076)==opaque,(tag,'foreignphase')
   cases.append(dict(tag=tag,kind='refusal',A=r.a,C=r.p&1,steps=count,instructions=total))
  # MetadataCRC covers every field including rawpixelgeometry/unusedreserved.
  for index in (0,1,2,3,6,7,8,9,12,16,44,48,76,139,140,141,144,156,159,166,168,169,170,171,174,176,180,271,272,319):
   cursor=index
   for lo,hi in lane.SPANS:
    if cursor<hi-lo:reject('metadata-byte-'+str(index),fe=lo+cursor);break
    cursor-=hi-lo
  # Actual payloadCRC failure must precede the first primary VALID0 write.
  payloadlen=len(lane.packet_payload(raw))
  for index in (0,63,64,127,841,842,payloadlen-1):
   cursor=320+index
   for lo,hi in lane.SPANS:
    if cursor<hi-lo:reject('payload-byte-'+str(index),fe=lo+cursor);break
    cursor-=hi-lo
  for owner in (0,1,2,3,5,255):reject('foreign-owner-'+str(owner),[(f.s['se_f_owner'],owner)],owner=True)
  for name,delta in [('se_reu_epoch',1),('se_gc_epoch',1),('se_reu_retired',1),('se_r_revision',1),('se_doc_generation',1),('se_render_caps',1),('se_l_mode',1),('se_r_presentation',1),('se_bc_count',1)]:reject(name,[(f.s[name],ram[f.s[name]]^delta)])
  for off in (0,4,5,8,12):reject('AUTH-'+str(off),[(f.s['se_bc_arena']+off,ram[f.s['se_bc_arena']+off]^1)])
  for off in (0,3,7,8,15,31,63):reject('settings-'+str(off),[(f.s['se_editor_settings']+off,ram[f.s['se_editor_settings']+off]^1)])
  reject('foreign-logicalFE',[(f.s['se_reu_logical_owner']+handle,7)]);reject('foreign-physicalFE',[(f.s['se_reu_physical_owner']+p,7)])
  reject('font4800',[(0x4800,ram[0x4800]^1)])
  raster=next(i for i in range(f.s['se_overlay_capacity'])if ram[f.s['se_overlay_ids']+i]==21 and ram[f.s['image_slot']+i]&1==0)
  reject('missing-raster-capability',[(f.s['se_overlay_ids']+raster,0)])
  for bit in (4,8):reject('competing-cache-'+str(bit),[(f.s['se_bc_flags'],ram[f.s['se_bc_flags']]|bit)])
  # Mid-flight cache work is also competing: no derived write after revocation.
  for op in (16,17):
   reset();r,n=invoke(op);assert not r.p&1 and r.a==1
   f.put('se_bc_flags',f.get('se_bc_flags',1)|8,1);before=whole();stable=current()
   r,count,total=drain(18);assert (r.p&1)or r.a==2;assert whole()==before and current()==stable
   cases.append(dict(tag='mid-flight-ACTIVE-'+str(op),kind='refusal',A=r.a,C=r.p&1))
  # A real active R14 lease is competing, even with GP sourcecontextflags0.
  reset();f.put('se_overlay_frame',0,1);r,n=f.fast_call(f.s['se_overlay_call'],a=14,x=0);assert not r.p&1;before=whole();phase=f.read(S,64);locks=f.get('se_doc_read_locks',1);r,n=invoke(16);assert r.p&1 and r.a==0x91 and whole()==before and f.read(S,64)==phase and f.get('se_doc_read_locks',1)==locks;f.call('se_fs_end');cases.append(dict(tag='competing-actual-R14',kind='refusal'))
  # Foreign read lease survives actual capture cancellation and restore cancel.
  reset();assert not f.call('se_doc_read_acquire').p&1;locks=f.get('se_doc_read_locks',1);stable=current();r,n=invoke(16);assert not r.p&1 and r.a==1
  for _ in range(3):r,n=invoke(18);assert not r.p&1 and r.a==1
  r,n=invoke(19);assert not r.p&1 and r.a==0 and current()==stable and f.get('se_doc_read_locks',1)==locks
  assert f.m.lib.zeropage_peddle_read_reu(f.m.handle,p*65536+0x680)==0,'canceledcapturemuststayunpublished';f.call('se_doc_read_release');cases.append(dict(tag='cancel-capture-preserves-foreignlease',kind='cancel'))
  reset();assert not f.call('se_doc_read_acquire').p&1;locks=f.get('se_doc_read_locks',1);r,n=invoke(17)
  for _ in range(1000):
   if f.m.read(S)==5:break
   r,n=invoke(18);assert not r.p&1 and r.a==1
  else:raise AssertionError('verified restore not reached')
  before=whole();pixels=f.read(0x6000,8000)+f.read(0x4000,1000);r,n=invoke(19);assert not r.p&1 and r.a==0 and whole()==before and f.get('se_doc_read_locks',1)==locks and f.read(0x6000,8000)+f.read(0x4000,1000)==pixels;assert f.m.lib.zeropage_peddle_read_reu(f.m.handle,p*65536)==0;f.call('se_doc_read_release');cases.append(dict(tag='cancel-restore-keeps-primary-unpublished',kind='cancel'))
  reset();before=whole();stable=current();r,n=invoke(20);assert not r.p&1 and r.a==0;after=whole();location=p*65536+0x680
  assert before[:location]==after[:location] and before[location+1:]==after[location+1:] and after[location]==0 and current()==stable
  r,count,total=drain(17);assert not r.p&1 and r.a==2 and whole()==after
  cases.append(dict(tag='explicit-cold-resume-freshFE-revoke',kind='revocation',only_modified_byte=hex(0x680)))
  # Full fixed-count capacity:22 actual native8 rows, no host-produced packets.
  raw22=geos.native_text(':::basic\r'+''.join(str(10+i)+' PRINT 1\r'for i in range(40))+':::\r')
  first=raw22.index(b'\r')+1;page,bank,p2=capture(raw22,'maximum22-native',top=first);assert page[1]==22 and len(lane.packet_payload(page))==20124
  dot=geos.native_text('.'*200+'\rTail.');page,bank,p3=capture(dot,'161-clipped-literal',pan=1);assert int.from_bytes(page[0x20c:0x20e],'little')==161
  folded=geos.native_text('# First\rHidden one.\r# Second\rHidden two.\r')
  f.source(folded);f.command(99);f.typed(geos.native_text('fold all'));f.render();assert f.get('se_ef_valid',1)==1;import_component();foldpage,_=f.raw_cache();before=whole();stable=current();f.put('se_f_owner',4,1);f.m.load(S,bytes(64));r,count,total=drain(16);assert not r.p&1 and r.a==0;foldmemo,_=f.raw_cache();assert lane.stream(foldmemo)[320:320+len(lane.packet_payload(foldpage))]==lane.packet_payload(foldpage) and current()==stable
  cases.append(dict(tag='actual-published-folded-page',kind='capture',rows=foldpage[1],instructions=total,steps=count))
  f.m.load(S,bytes(64));f.m.load(S+26,foldpage[32:35]);token=f.read(f.s['se_ef_token'],5);old=f.m.read(f.s['object_owner']+token[0]);f.m.write(f.s['object_owner']+token[0],0x45);before=whole();stable=current();r,count,total=drain(17);assert r.p&1 or r.a==2;assert whole()==before and current()==stable;f.m.write(f.s['object_owner']+token[0],old);cases.append(dict(tag='folded-map-foreign-type',kind='refusal',A=r.a,C=r.p&1))
  # Real shiftedW_LOAD: canonical28/ticket invariant, FS59representation differs.
  text=geos.native_text(''.join('row%03d Wim body.\r'%i for i in range(240)));page,bank,p4=capture(text,'shifted-W_LOAD-base');f.put('se_f_owner',0,1);a=fs_snapshot();key_a=f.read(f.s['se_doc_meta'],15)+f.read(f.s['se_doc_generation'],2)+f.read(f.s['se_r_revision'],4)+f.read(f.s['se_bc_arena'],13);f.position(3000);b=fs_snapshot();key_b=f.read(f.s['se_doc_meta'],15)+f.read(f.s['se_doc_generation'],2)+f.read(f.s['se_r_revision'],4)+f.read(f.s['se_bc_arena'],13)
  assert a!=b and key_a==key_b and f.merged()==text
  cases.append(dict(tag='publicW_LOAD-shifted',kind='identity-map',FS59_changed=[i for i,(x,y)in enumerate(zip(a,b))if x!=y],canonical_and_ticket_equal=True,before_FS59=a.hex(),after_FS59=b.hex()))
  # Pending visibleedit + publicBOTTOM commits representation; oldmemo misses.
  f.position(0);f.key(geos.native_text('Q')[0]);text=geos.native_text('Q')+text;f.render();f.put('se_f_owner',4,1);f.m.load(S,bytes(64));r,count,total=drain(16);assert not r.p&1 and r.a==0;oldgen=f.get('se_doc_generation',2);f.put('se_f_owner',0,1);f.command(35);f.render();assert not f.get('se_hot_pending',1) and f.get('se_doc_generation',2)!=oldgen and f.merged()==text
  f.put('se_f_owner',4,1);f.m.load(S,bytes(64));f.m.load(S+26,bytes(3));before=whole();stable=current();r,count,total=drain(17);assert (r.p&1)or r.a==2;assert whole()==before and current()==stable
  cases.append(dict(tag='pending-publicBOTTOM-flush',kind='strict-miss',old_generation=oldgen,new_generation=f.get('se_doc_generation',2),A=r.a,C=r.p&1))
  result=dict(status='passed',cases=cases,component_bytes=len(image)-36,max_service_instructions=max(timings),CPU_clock_unavailable=True,scope='actual private R34selector/checkedFE transport; no C21automatic hook or native timing',full_REU_guard_bytes=16777216,precise_scatter_bytes=20864,profilefits=True)
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status='passed',cases=len(cases),bytes=len(image)-36,max_instructions=max(timings),out=str(out)),indent=2))
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=lane.BASE);a=p.parse_args();run(ROOT/'build/cache-layout-guards'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),a.fixture.resolve())
