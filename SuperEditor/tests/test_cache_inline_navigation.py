"""Private actual-root C23 typed CR/INLINE reuse, no result/state seeding."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,importlib.util,inspect,json,sys,types
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_observer as observer
import test_plain_geos as plain

def build(out,base,targeted=False):
 path=ROOT/'src/cache/inline/probes/navigation/build.py';spec=importlib.util.spec_from_file_location('nav_build',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module.build(out,base,targeted)

def run(out,base,faults_only=False,matrix_only=False,targeted=False):
 budget=build(out/'build',base,targeted);cases=[];broad_cases=[];fault_result=[]
 for variant in('control','candidate'):
  d=out/variant;d.mkdir();g=observer.Gate(d,base);f=g.f
  try:
   if variant=='candidate':
    f.assets['geosnav']=(out/'build/geosnav.seo').read_bytes();f.assets['geosinln']=(out/'build/geosinln.seo').read_bytes();f.m.load(f.s['se_geos_render'],(out/'build/dispatch-candidate/image.bin').read_bytes())
   c=inspect.getsource(observer.geos.grid.editor_fixture.EditorFixture.settle).replace('25000','200000');ns={};exec('\n'.join(x[1:]for x in c.splitlines()),ns);f.settle=types.MethodType(ns['settle'],f)
   fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in observer.geos.GEOS_FONTS+('native8.bin',)}
   targets=[('C23','geosnav'),('C20','geosline'),('C24','geossema'),('C26','geosinln'),('C35','inln'),('C37','page'),('C39','line')]
   g.dll.pb_config(f.s['se_overlay_active'],len(targets),(C.c_uint16*len(targets))(*([0xb010]*len(targets))),(C.c_uint8*len(targets))(*([2]*len(targets))),(C.c_uint8*len(targets))(*(g.identity['names'].index(v[1])+1 for v in targets)),(C.c_uint8*(16*len(targets)))())
   for preset in(()if faults_only or matrix_only else('plain','markdown')):
    for target in (3072,4102):
     data=observer.geos.native_text('**')+b'x'*4092+observer.geos.native_text('**\rNext.')
     f.source(data);f.typed(observer.geos.native_text('syntax '+preset));f.command(99);f.render();before=g.reu();stable=g.stable();start=f.total_instructions;loads=f.get('se_overlay_loads',2);dma=f.get('se_reu_dma_calls',2);buckets={};trace=[];original=f.call
     def tracked(name,a=0):
      job=f.get('se_e_job',1);req=tuple(f.read(0x9135,2))if job==12 else None;begin=f.total_instructions;reg=original(name,a)
      if name=='se_editor_service':
       key=f'job{job}:'+str(req);v=buckets.setdefault(key,[0,0]);v[0]+=1;v[1]+=f.total_instructions-begin
       if req is not None:trace.append(req)
      assert not f.get('se_e_error',1),(variant,preset,name,reg.a,trace[-12:],f.debug())
      return reg
     f.call=tracked;g.dll.pb_begin()
     try:
     
      if target==4102:f.command(35) #actualpublicBOTTOM includes target/reload/reveal
      else:f.position(target);reg=f.call('se_editor_reveal');assert not reg.p&1;f.settle()
     finally:g.dll.pb_end();f.call=original
     elapsed=f.total_instructions-start;nav_loads=(f.get('se_overlay_loads',2)-loads)&65535;nav_dma=(f.get('se_reu_dma_calls',2)-dma)&65535;counts={x[0]:int(g.dll.pb_get(i))for i,x in enumerate(targets)}
     assert f.get('se_hot_caret')==target and not any(f.get(n,1)for n in('se_e_job','se_e_error','se_f_owner','se_doc_read_locks'))
     assert g.stable()==stable and f.merged()==data and g.reu()==before and f.read(0xc600,1024)==f.shim
     if variant=='candidate'and preset=='markdown':
      assert(35,0)in trace and(26,7)in trace and(23,1)in trace,trace
      if target==3072:assert(39,0)in trace,trace
     if preset=='plain':assert counts['C24']==counts['C26']==counts['C35']==counts['C37']==counts['C39']==0
     f.render();bits,attrs,rows=plain.expected(f,data,fonts,0 if preset=='plain'else 1);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
     observer.geos.png(bits,attrs,d/(preset+'-'+str(target)+'.png'));item=dict(variant=variant,preset=preset,target=target,top=f.get('se_v_top'),instructions=elapsed,loads=nav_loads,dma=nav_dma,entry_counts=counts,service_attribution=buckets,trace=trace,bitmap=hashlib.sha256(bits).hexdigest(),attrs=hashlib.sha256(attrs).hexdigest());cases.append(item);(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n');print('PASS',{k:v for k,v in item.items()if k not in('trace','service_attribution')},flush=True)
   if not faults_only:broad_cases+=matrix(out/variant,g,fonts,variant)
   if variant=='candidate'and not matrix_only:fault_result=faults(out/'faults',g,fonts,out/'build',base)
  finally:f.close()
 for preset in(()if faults_only or matrix_only else('plain','markdown')):
  
  for target in(3072,4102):
   a,b=[x for x in cases if x['preset']==preset and x['target']==target];assert a['top']==b['top']and a['bitmap']==b['bitmap']and a['attrs']==b['attrs']
 
 for a in [x for x in broad_cases if x['variant']=='control']:
  b=next(x for x in broad_cases if x['variant']=='candidate'and x['tag']==a['tag']);assert a['state']==b['state']and a['bitmap']==b['bitmap']and a['attrs']==b['attrs'],('broad AB',a,b)
 result=dict(status='PASS',budget=budget,cases=cases,broad=broad_cases,faults=fault_result,scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


def matrix(out,g,fonts,variant):
 f=g.f;frames=[]
 mixed=observer.geos.native_text('# Heading **strong**\rPlain *italic* with **bold** and @@code@@.\r:::basic\r10 PRINT "Hi"\r20 REM comment\r:::\r:::asm\rstart: lda #$2A ; comment\r .byte 1,2\r:::\r:::region Group\rInside region.\r:::end\rFinal plain row.\r')
 for preset in('plain','markdown','full'):
  f.source(mixed);f.typed(observer.geos.native_text('syntax '+preset));f.command(99);f.render()
  for i,command in enumerate((37,37,36,39,38,75,74)):
   tag=f'mixed-{preset}-{i}-{command}';before=g.reu();stable=g.stable();start=f.total_instructions;loads=f.get('se_overlay_loads',2);dma=f.get('se_reu_dma_calls',2)
   trace=[];original=f.call
   def tracked(name,a=0):
    if name=='se_editor_service':trace.append((tuple(f.read(0x9135,2)),f.m.read(0x9134),f.read(0x912c,2).hex(),f.m.read(0x8b55),f.m.read(0x9173)))
    return original(name,a)
   f.call=tracked
   try:f.command(command)
   except BaseException:
    (out/(tag+'-failure-ram.bin')).write_bytes(f.read(0,65536));print('MATRIX FAILURE',variant,tag,trace[-12:],flush=True);raise
   finally:f.call=original
   elapsed=f.total_instructions-start
   assert g.stable()==stable and g.reu()==before and f.merged()==mixed,(tag,'navigation changed canonical/REU')
   nav_loads=(f.get('se_overlay_loads',2)-loads)&65535;nav_dma=(f.get('se_reu_dma_calls',2)-dma)&65535
   audit=g.audit_begin();f.render();g.audit_end(audit,tag);bits,attrs,_=plain.expected(f,mixed,fonts,dict(plain=0,markdown=1,full=3)[preset]);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'independent pixels')
   assert f.read(0xc600,1024)==f.shim and not any(f.get(n,1)for n in('se_e_job','se_e_error','se_f_owner','se_doc_read_locks'))
   state={n:f.get(n,w)for n,w in(('se_hot_caret',3),('se_v_top',3),('se_l_pan',3),('se_l_mode',1),('se_l_manual',1),('se_l_preferred',3))}
   item=dict(tag=tag,variant=variant,instructions=elapsed,loads=nav_loads,dma=nav_dma,state=state,bitmap=hashlib.sha256(bits).hexdigest(),attrs=hashlib.sha256(attrs).hexdigest());frames.append(item);print('MATRIX PASS',item,flush=True)
 # Actual collapsed source map remains the same; navigation must not reinterpret
 # phase records as parser state or make an outer query touch another owner's map.
 from dataclasses import replace
 from test_geos_fold_editor import tree
 from geos_fold_model import raster
 data=observer.geos.native_text('# First\rHidden **words**.\r# Second\rAfter.\r')
 f.source(data);f.command(99);f.typed(observer.geos.native_text('fold all'));f.render();assert f.get('se_ef_valid',1)==1
 folds=[replace(x,flags=1)for x in tree(data)]
 for i,command in enumerate((75,74,37,36)):
  tag=f'folded-{i}-{command}';before=g.reu();stable=g.stable();start=f.total_instructions;f.command(command);elapsed=f.total_instructions-start;assert g.stable()==stable and g.reu()==before and f.merged()==data
  audit=g.audit_begin();f.render();g.audit_end(audit,tag)
  bits,attrs,_,_=raster(data,fonts,folds,top=f.get('se_v_top'),caret=f.get('se_hot_caret'),nowrap=bool(f.get('se_l_mode',1)),pan=f.get('se_l_pan'))
  m,c,r=observer.geos.grid.logical_ui(f,data);bits,attrs=observer.geos.with_chrome(bits,attrs,m,c,fonts['native8.bin'],r);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'independent fold pixels')
  state={n:f.get(n,w)for n,w in(('se_hot_caret',3),('se_v_top',3),('se_l_pan',3),('se_l_mode',1),('se_l_manual',1),('se_l_preferred',3))}
  item=dict(tag=tag,variant=variant,instructions=elapsed,state=state,bitmap=hashlib.sha256(bits).hexdigest(),attrs=hashlib.sha256(attrs).hexdigest());frames.append(item);print('MATRIX PASS',item,flush=True)
 # Committed far source uses actual public BOTTOM; the target is after a
 # complete >64KiB logical body. The baseline and all target data are built by
 # actual producer/transport; no TOP/map/carry seeding.
 data=b'x'*65536+observer.geos.native_text('\rFar **bold** words.\rTail.')
 f.source(data);f.typed(observer.geos.native_text('syntax markdown'));f.command(99);f.render();assert f.get('se_bc_flags',1)&15==1
 before=g.reu();stable=g.stable();start=f.total_instructions;loads=f.get('se_overlay_loads',2);dma=f.get('se_reu_dma_calls',2);f.command(35);elapsed=f.total_instructions-start;navloads=(f.get('se_overlay_loads',2)-loads)&65535;navdma=(f.get('se_reu_dma_calls',2)-dma)&65535
 assert f.get('se_hot_caret')==len(data)>65535 and g.stable()==stable and g.reu()==before and f.merged()==data
 audit=g.audit_begin();f.render();g.audit_end(audit,'far24');bits,attrs,_=plain.expected(f,data,fonts,1);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
 state={n:f.get(n,w)for n,w in(('se_hot_caret',3),('se_v_top',3),('se_l_pan',3),('se_l_mode',1),('se_l_manual',1),('se_l_preferred',3))}
 item=dict(tag='far24-public-bottom',variant=variant,instructions=elapsed,loads=navloads,dma=navdma,state=state,bitmap=hashlib.sha256(bits).hexdigest(),attrs=hashlib.sha256(attrs).hexdigest());frames.append(item);print('MATRIX PASS',item,flush=True)
 return frames

def faults(out,g,fonts,build,base):
 out.mkdir();f=g.f;data=observer.geos.native_text('**')+b'x'*4092+observer.geos.native_text('**\rNext.');results=[]
 def prepare():
  f.assets['geosnav']=(build/'geosnav.seo').read_bytes();f.assets['geosinln']=(build/'geosinln.seo').read_bytes();f.source(data);f.typed(observer.geos.native_text('syntax markdown'));f.command(99);f.render();f.position(3072);r=f.call('se_editor_reveal');assert not r.p&1
 def pixelcheck():
  bits,attrs,_=plain.expected(f,data,fonts,1);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
 for action in('queued-STOP','missing35','source-change','missing26-capture','write-before-capture','missing39'):
  prepare();target=(26,7)if action in('missing26-capture','write-before-capture')else(39,1)if action=='missing39'else(35,1)
  for step in range(10000):
   if f.get('se_e_job',1)==12 and tuple(f.read(0x9135,2))==target and(target not in((35,1),(39,1))or(f.get('se_bc_flags',1)&8 and f.get('se_doc_read_locks',1)==1)):break
   assert f.get('se_e_job',1)==12;f.call('se_editor_service');assert not f.get('se_e_error',1)
  else:raise AssertionError(('fault boundary',action))
  cp=f.read(0x8880,140);had_cp=bool(f.m.read(0x9173)&64);cp_marker=f.m.read(0x890c)if had_cp else 0
  before=g.reu();stable=g.stable();canonical=f.canonical();bitmap=f.read(0x6000,8000)+f.read(0x4000,1000);rev=f.get('se_r_revision',4);idx=None;tail=f.get('se_input_tail',1)
  if action=='queued-STOP':f.queued(3)
  elif action=='source-change':f.put('se_r_revision',rev+1,4)
  elif action=='write-before-capture':
   # Checked typed53 self-write must revoke proof beforeDMA, even if bytes do
   # not change.8300 is inactive style staging, not DOC_LEAF8400 or merged cache8000.
   f.m.load(f.s['se_object_id'],f.read(f.s['se_bc_arena'],5));f.put('se_object_offset',0);f.put('se_object_length',1,2);f.put('se_object_c64',0x8300,2);assert not f.call('se_object_copy',1).p&1;assert not f.call('se_object_copy',0).p&1;assert not f.get('se_bc_flags',1)&32
  else:
   ident=26 if action=='missing26-capture'else 39 if action=='missing39'else 35;idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)&1==1);f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active']+1,0)
  f.call('se_editor_service')
  if action=='write-before-capture':
   assert tuple(f.read(0x9135,2))==(24,0) and f.m.read(0x8b40+28)==cp_marker and(not had_cp or f.read(0x8b40+29,140)==cp),'actual real CP restore'
   assert not f.get('se_doc_read_locks',1) and g.reu()==before
   f.settle()
  else:
   assert not any(f.get(n,1)for n in('se_e_job','se_e_draw_busy','se_f_owner','se_doc_read_locks')) and not f.get('se_bc_flags',1)&8
   assert f.get('se_e_error',1)==(0 if action=='queued-STOP'else 0xb1 if action=='source-change'else 0x17)
   assert f.read(0x6000,8000)+f.read(0x4000,1000)==bitmap and g.reu()==before
  assert f.canonical()==canonical and g.stable()==stable and f.merged()==data and f.read(0xc600,1024)==f.shim
  if idx is not None:f.m.write(f.s['se_overlay_ids']+idx,26 if action=='missing26-capture'else 39 if action=='missing39'else 35)
  if action=='source-change':f.put('se_r_revision',rev,4)
  if action=='queued-STOP':
   assert f.get('se_input_tail',1)==tail;f.put('se_status',1,1);f.tick();f.settle();assert f.get('se_input_tail',1)==f.get('se_input_head',1)
  elif action!='write-before-capture':f.key(0x8b);f.key(0x8b)
  # Navigation is completed again through the public safe-point; no target or
  # source state is synthesized after cancellation/missing-image recovery.
  r=f.call('se_editor_reveal');assert not r.p&1;f.settle();assert g.stable()==stable and f.canonical()==canonical
  f.render();pixelcheck();after=g.reu();want=bytearray(before);_,bank=f.raw_cache();spans=[(0,64),(0x600,0x680),(0xb200,0xd568),(0xe568,0xea88),(0xfc00,0xfda0)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]+[(0x700+i*0x800,0x740+i*0x800)for i in range(22)]
  for lo,hi in spans:want[bank*65536+lo:bank*65536+hi]=after[bank*65536+lo:bank*65536+hi]
  assert after==want,'recovery full16MiB outside exactFE'
  assert not any(f.get(n,1)for n in('se_e_job','se_e_error','se_f_owner','se_doc_read_locks'))
  item=dict(action=action,steps_to_boundary=step,real_CP_restored=action=='write-before-capture'and had_cp);results.append(item);print('FAULT PASS',item,flush=True)
 # Build a genuine baseline over a pending edit before moving its gap. The
 # content/revision stayfixed while FS59 geometry changes: a legitimateMISS.
 f.assets['geosnav']=(build/'geosnav.seo').read_bytes();f.assets['geosinln']=(build/'geosinln.seo').read_bytes();f.source(data);f.typed(observer.geos.native_text('syntax markdown'));f.key(observer.Q);assert f.get('se_hot_pending',1);f.command(99);f.render();assert f.get('se_bc_count',1)==0 and f.get('se_bc_flags',1)&15==1
 for _ in range(900):g.hot(observer.W_RIGHT)
 assert f.get('se_hot_pending',1)and f.get('se_hot_caret')==901
 pending_data=bytes([observer.Q])+data;before=g.reu();stable=g.stable();canonical=f.canonical();f.call('se_editor_reveal')
 for _ in range(10000):
  if f.get('se_e_job',1)==12 and tuple(f.read(0x9135,2))==(35,0):break
  f.call('se_editor_service');assert not f.get('se_e_error',1)
 else:raise AssertionError('pending baseline didnotrequest35')
 pending_marker=f.m.read(0x890c)if f.m.read(0x9173)&64 else 0;actual_cp=f.read(0x8880,140)
 for _ in range(10000):
  f.call('se_editor_service');assert not f.get('se_e_error',1)
  if tuple(f.read(0x9135,2))==(24,0):break
 else:raise AssertionError('pending geometryMISS didnotfallback24')
 assert f.m.read(0x8b40+28)==pending_marker and(not pending_marker or f.read(0x8b40+29,140)==actual_cp),'exact actual CP marker/bytes on pendingMISS'
 f.settle();assert f.get('se_hot_pending',1)and f.canonical()==canonical and g.stable()==stable and g.reu()==before and f.merged()==pending_data
 f.render();bits,attrs,_=plain.expected(f,pending_data,fonts,1);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
 results.append(dict(action='real-pending-geometry-MISS',actual_CP_marker=pending_marker,actual_CP_bytes=140 if pending_marker else 0));print('FAULT PASS pending geometry actualMISS',flush=True)
 # Force one real legacy classification before optional cache admission.
 # This creates a genuine post-event CP1. Re-enable the original advisory
 # flags only after C24 completes; no parser/carry/event bytes are synthesized.
 prepare();saved_flags=f.get('se_bc_flags',1)
 for _ in range(10000):
  if tuple(f.read(0x9135,2))==(26,6):break
  f.call('se_editor_service');assert not f.get('se_e_error',1)
 else:raise AssertionError('selector boundary absent')
 f.put('se_bc_flags',saved_flags&~1,1);f.call('se_editor_service');assert tuple(f.read(0x9135,2))==(24,0)
 for _ in range(10000):
  if tuple(f.read(0x9135,2))==(23,1)and f.m.read(0x9134)==5 and not f.m.read(0x8b40+21):break
  f.call('se_editor_service');assert not f.get('se_e_error',1)
 else:raise AssertionError('real legacy CP completion absent')
 assert f.m.read(0x8b40+28)==1,'actual C24 must publish post-event CP1'
 f.put('se_bc_flags',saved_flags,1)
 for _ in range(10000):
  if tuple(f.read(0x9135,2))==(35,0):break
  f.call('se_editor_service');assert not f.get('se_e_error',1)
 else:raise AssertionError('real CP query boundary absent')
 assert f.m.read(0x9173)&64 and f.m.read(0x890c)==1,'real CP1 not saved'
 actual_cp=f.read(0x8880,140)
 for _ in range(10000):
  if tuple(f.read(0x9135,2))==(26,7):break
  f.call('se_editor_service');assert not f.get('se_e_error',1)
 else:raise AssertionError('real CP capture boundary absent')
 before=g.reu();stable=g.stable();canonical=f.canonical()
 f.m.load(f.s['se_object_id'],f.read(f.s['se_bc_arena'],5));f.put('se_object_offset',0);f.put('se_object_length',1,2);f.put('se_object_c64',0x8300,2);assert not f.call('se_object_copy',1).p&1;assert not f.call('se_object_copy',0).p&1;assert not f.get('se_bc_flags',1)&32
 f.call('se_editor_service');assert tuple(f.read(0x9135,2))==(24,0)and f.m.read(0x8b40+28)==1 and f.read(0x8b40+29,140)==actual_cp,('real CP1 exact restoration',tuple(f.read(0x9135,2)),f.m.read(0x9173),f.m.read(0x890c),f.m.read(0x8b40+28),[(i,a,b)for i,(a,b)in enumerate(zip(f.read(0x8b40+29,140),actual_cp))if a!=b][:8],[(i,a,b)for i,(a,b)in enumerate(zip(f.read(0x8880,140),actual_cp))if a!=b][:8])

 for _ in range(200000):
  req=tuple(f.read(0x9135,2));f.call('se_editor_service')
  if f.get('se_e_error',1):
   (out/'CP1-error-ram.bin').write_bytes(f.read(0,65536));raise AssertionError(('CP1 replay',req,f.debug(),f.read(0x8ee0,86).hex(),f.read(0x9040,86).hex()))
  if not f.get('se_e_job',1):break
 else:raise AssertionError('CP1 replay bound')
 assert f.canonical()==canonical and g.stable()==stable and g.reu()==before and f.merged()==data;f.render();pixelcheck();results.append(dict(action='real-legacy-CP1-restore',actual_CP_bytes=140,actual_CP_marker=1,setup='Temporary optional-admission flag fault; real C24 completion then savedflag restore; no parser/event/map seeding'));print('FAULT PASS real legacy CP1',flush=True)
 # Same resident binding is not the new helper protocol. The mandatory
 # operation capability is checked before a new opcode/publication is used.
 for action in('newnav-oldinline','oldnav-newinline'):
  f.assets['geosnav']=(base/'build/overlays/geosnav.seo').read_bytes()if action=='oldnav-newinline'else(build/'geosnav.seo').read_bytes();f.assets['geosinln']=(base/'build/overlays/geosinln.seo').read_bytes()if action=='newnav-oldinline'else(build/'geosinln.seo').read_bytes();f.source(data);f.typed(observer.geos.native_text('syntax markdown'));f.command(99);f.render();f.position(3072);before=g.reu();stable=g.stable();bitmap=f.read(0x6000,8000)+f.read(0x4000,1000);f.call('se_editor_reveal');f.settle(error=0x90 if action=='newnav-oldinline'else 0)
  assert g.reu()==before and g.stable()==stable and f.merged()==data and not any(f.get(n,1)for n in('se_e_job','se_f_owner','se_doc_read_locks'))
  if action=='newnav-oldinline':assert f.read(0x6000,8000)+f.read(0x4000,1000)==bitmap
  else:f.render();pixelcheck()
  results.append(dict(action=action,safe_error=0x90 if action=='newnav-oldinline'else 0));print('MIXED PASS',action,flush=True)
 return results

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--faults-only',action='store_true');p.add_argument('--matrix-only',action='store_true');p.add_argument('--targeted',action='store_true');p.add_argument('--fixture',type=Path,default=ROOT/'build/cache-editor-product/20261026T033702424844Z/fixture');a=p.parse_args();out=ROOT/'build/cache-inline-navigation'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture,a.faults_only,a.matrix_only,a.targeted)
