"""Faults drive the actual resident job11; no host producer/link operations."""
import json
F=0x8d00
def qualify(f,g,dll,b,l,fonts,out,geos,plain,arena):
 groups=[]
 data=geos.native_text('Intro\r:::basic\r10 PRINT "Hi":REM ')+geos.native_text('x')*980+geos.native_text('\r:::\rTail.')
 def baseline(source=data):
  f.source(source);f.typed(geos.native_text('syntax markdown'));f.command(99);f.render()
  assert f.get('se_bc_flags',1)&143==1
  f.trace=[];f.observed_pages=set();f.candidate_roots=set()
  return f.canonical(),f.catalog(),f.reu()
 def observe(q):
  cs=f.m.read(0x9096)
  if cs in (4,6,7,8,9) and f.m.read(F+79)in(2,3):
   page=f.m.read(F+80)
   if 1<=page<16:f.observed_pages.add(page)
  if q==49:
   state=f.m.read(F)
   if 5<=state<=13:
    page=f.m.read(F+9)
    if 1<=page<16:f.observed_pages.add(page)
   if state==13:f.candidate_roots.add(f.m.read(F+13)^128)
 def service():
  q=f.m.read(0x9135);r=f.call('se_editor_service');observe(q);return r
 def advance(predicate,limit=50000):
  for n in range(limit):
   if predicate():return n
   assert f.get('se_e_job',1)==11,('job prematurely closed',f.get('se_e_error',1),getattr(f,'trace',[])[-8:])
   service()
  raise AssertionError('bounded actual foreground progress')
 def begin():
  f.typed(geos.native_text('syntax full'));r=f.call('se_editor_render');assert not r.p&1 and f.get('se_e_job',1)==11
 def interval(before,after):
  lo,selected,root=arena(f,before);wanted=bytearray(before)
  for page in f.observed_pages:
   at=lo+256+page*8;assert before[at:at+8]==bytes(8),('would overwrite old reachable page',page)
   wanted[at:at+8]=after[at:at+8];at=lo+4096*page;wanted[at:at+4096]=after[at:at+4096]
  for offset in f.candidate_roots:
   assert offset!=selected;wanted[lo+offset:lo+offset+128]=after[lo+offset:lo+offset+128]
  _,bank=f.raw_cache();fe=bank*65536
  for a,z in [(0,64),(0x200,0xEA88)]:wanted[fe+a:fe+z]=after[fe+a:fe+z]
  assert before[lo+selected:lo+selected+128]==after[lo+selected:lo+selected+128]
  assert after==wanted,'full16MiB outside actual unreferenced candidate pages/dir/alternate VALID0 root/sourceFE'
 def pixels(source=data):
  bits,attrs,rows=plain.expected(f,source,fonts,3)
  assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,'independent fallback pixels'
  return bits,attrs
 def clean(canon,catalog):
  assert f.canonical()==canon and f.catalog()==catalog and f.merged()==f.logical and f.read(0xc600,1024)==f.shim
  assert not any(f.get(n,1)for n in ('se_e_error','se_f_owner','se_e_job','se_fs_owned','se_doc_read_locks','se_e_draw_busy'))
  assert not f.get('se_bc_flags',1)&8
 def retry(canon,catalog,source=data):
  old=f.reu();f.trace=[];f.observed_pages=set();f.candidate_roots=set();f.key(0x8a);f.key(0x8a);f.render();pixels(source);clean(canon,catalog)
  assert not any(t[0]in(45,47,49)for t in f.trace),'attempt latch must prevent repeated construction after failure/STOP'
  lo,_,_=arena(f,old);assert f.reu()[lo:lo+65536]==old[lo:lo+65536],'retry modified arena'
  interval(old,f.reu())
 # Real IRQ STOP at distinct owned producer/page/linker phases, including a
 # provisional alternate root whose VALID byte has deliberately not published.
 points={
  'producer':lambda:f.m.read(0x9135)==47 and f.m.read(0x9136)==1 and int.from_bytes(f.read(F+41,3),'little')>0,
  'held-span':lambda:f.m.read(0x9135)==45 and f.m.read(0x9096)==6 and f.m.read(F+4)==1,
  'lexical-seal':lambda:f.m.read(0x9135)==45 and f.m.read(0x9096)==7 and f.m.read(F+92)==3,
  'COW-root-before-VALID':lambda:f.m.read(0x9135)==49 and f.m.read(0x9136)==1 and f.m.read(F)==13,
 }
 for tag,predicate in points.items():
  canon,catalog,before=baseline();begin();advance(predicate)
  assert f.get('se_bc_flags',1)&136==136 and f.get('se_doc_read_locks',1)==1 and f.m.read(F+3)==1
  f.queued(3);service();clean(canon,catalog);interval(before,f.reu());retry(canon,catalog)
  groups.append('actual-STOP-'+tag);print('AUTO_FAULT_PASS',groups[-1],flush=True)
 # Missing child admission is an actual loader failure; resident STOP/error
 # cleanup must work without executing that missing leaf's CANCEL operation.
 for id_,slot in ((47,1),(49,1),(36,0),(37,0),(14,0)):
  canon,catalog,before=baseline();begin()
  if id_==49:advance(lambda:f.m.read(0x9135)==49 and f.m.read(0x9136)==0)
  elif id_==47:advance(lambda:f.m.read(0x9135)==47 and f.m.read(0x9136)==0)
  else:advance(lambda:f.m.read(0x9135)==45 and f.m.read(0x9096)==(4 if id_==37 else 1))
  index=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==id_ and f.m.read(f.s['image_slot']+i)&127==slot)
  f.m.write(f.s['se_overlay_ids']+index,255);f.m.write(f.s['se_overlay_active']+slot,0)
  for _ in range(50000):
   if not f.get('se_e_job',1):break
   service()
  else:raise AssertionError('missing child did not settle')
  error=f.get('se_e_error',1)
  f.m.write(f.s['se_overlay_ids']+index,id_);f.m.write(f.s['se_overlay_active']+slot,0)
  assert not any(f.get(n,1)for n in ('se_f_owner','se_e_job','se_fs_owned','se_doc_read_locks','se_e_draw_busy'))
  assert not f.get('se_bc_flags',1)&8 and f.get('se_bc_flags',1)&128
  assert f.canonical()==canon and f.catalog()==catalog;interval(before,f.reu())
  if error:f.key(0x8b);f.key(0x8b)
  retry(canon,catalog);groups.append('missing-'+str(id_)+'-'+str(slot)+'-error'+str(error));print('AUTO_FAULT_PASS',groups[-1],flush=True)
 # A changed live source/typed authority refuses before the next payload DMA.
 for name in ('se_bc_ticket','se_bc_incarnation','se_r_revision','se_doc_generation'):
  canon,catalog,before=baseline();begin();advance(points['producer'])
  at=f.s[name];old=f.m.read(at);f.m.write(at,old^1);last=f.reu();service()
  assert f.reu()==last,'fault must refuse before additional DMA'
  assert f.m.read(0x9135)==45 and f.m.read(0x9096+26) and not f.get('se_doc_read_locks',1) and not f.get('se_bc_flags',1)&8
  f.m.write(at,old);f.settle();pixels();clean(canon,catalog);interval(before,f.reu());retry(canon,catalog)
  groups.append('actual-live-'+name);print('AUTO_FAULT_PASS',groups[-1],flush=True)
 canon,catalog,before=baseline();begin();advance(points['producer'])
 token=f.read(f.s['se_bc_arena'],5);logical=f.m.read(f.s['object_extents']+token[0]*16);physical=f.m.read(f.s['se_reu_map']+logical)
 at=f.s['se_reu_physical_owner']+physical;old=f.m.read(at);f.m.write(at,0x77);last=f.reu();service()
 assert f.reu()==last and f.m.read(0x9096+26) and not f.get('se_doc_read_locks',1) and not f.get('se_bc_flags',1)&8
 f.m.write(at,old);f.settle();pixels();clean(canon,catalog);interval(before,f.reu());retry(canon,catalog)
 groups.append('typed-arena-physical-owner-refuses-before-DMA');print('AUTO_FAULT_PASS',groups[-1],flush=True)
 # A real checked CR page's payload CRC must fail before construction. Restore
 # the injected byte only after the actual optional gateway has refused it.
 canon,catalog,before=baseline();lo,_,root=arena(f,before);page=root[104];at=lo+page*4096+64+3
 def typed_byte(offset,value):
  # An actual checked typed53 write, not an emulator memory substitution.
  # It correctly revokes PAGE proof; C45 is already admitted and its R36
  # lookup must independently validate the damaged payload CRC.
  f.m.load(f.s['se_object_id'],f.read(f.s['se_bc_arena'],5));f.put('se_object_offset',offset-lo);f.put('se_object_length',1,2);f.put('se_object_c64',F+575,2);f.m.write(F+575,value)
  r=f.call('se_object_copy',0);assert not r.p&1
 value=before[at];begin();advance(lambda:f.m.read(0x9135)==45 and f.m.read(0x9096)==1);typed_byte(at,value^1)
 advance(lambda:f.m.read(0x9135)==25 and f.m.read(0x9136)==3)
 assert not any(t[0]in(47,49)for t in f.trace) and f.get('se_bc_flags',1)&128 and not f.get('se_doc_read_locks',1)
 typed_byte(at,value);f.settle();pixels();clean(canon,catalog);interval(before,f.reu());retry(canon,catalog)
 groups.append('actual-CR-page-payloadCRC-refusal-no-publication');print('AUTO_FAULT_PASS',groups[-1],flush=True)
 # A stale saved provider epoch must not decrement seven unrelated leases.
 canon,catalog,before=baseline();begin();advance(points['producer'])
 f.m.write(F+173+27,f.m.read(F+173+27)^1);f.put('se_doc_read_locks',7,1);last=f.reu();f.queued(3);service()
 assert f.get('se_doc_read_locks',1)==7 and not f.get('se_fs_owned',1) and not f.get('se_bc_flags',1)&8 and f.reu()==last
 f.put('se_doc_read_locks',0,1);clean(canon,catalog);retry(canon,catalog);groups.append('stale-epoch-STOP-preserves-seven-foreign-leases');print('AUTO_FAULT_PASS',groups[-1],flush=True)
 # Dense actual code overflows the bounded562-span page. It must neither ACK
 # the rejected span nor publish a CR/root lexical capability, and must stay
 # on strict fallback for all later windows of this baseline.
 dense=geos.native_text('Intro\r:::basic\r')+geos.native_text('10 PRINT "x":')*200+geos.native_text('\r:::\rTail.')
 canon,catalog,before=baseline(dense);f.job_budget=100000;begin();advance(lambda:f.m.read(0x9096)==6 and int.from_bytes(f.read(F+83,2),'little')==562)
 feeds_at_capacity=int.from_bytes(f.read(F+41,3),'little');f.settle();pixels(dense);clean(canon,catalog)
 lo,sel,root=arena(f,f.reu());assert root[31]==1 and f.get('se_bc_flags',1)&128 and f.observed_pages
 assert sum(t[0:2]==(47,0)for t in f.trace)==1 and not any(t[0]==49 for t in f.trace)
 interval(before,f.reu());retry(canon,catalog,dense)
 # Identical larger total-job budget is required by the unchanged dense-code
 # C25 fallback, not by an unbounded new producer or relaxed service limit.
 g.source(dense);g.typed(geos.native_text('syntax markdown'));g.command(99);g.render();g.job_budget=100000;g.typed(geos.native_text('syntax full'));g.render()
 assert g.read(0x6000,8000)==f.read(0x6000,8000) and g.read(0x4000,1000)==f.read(0x4000,1000)
 f.job_budget=g.job_budget=25000
 groups.append('actual-STREAM562-no-root-publication-no-retry-packaged-dense-control');print('AUTO_FAULT_PASS',groups[-1],feeds_at_capacity,flush=True)
 # Unsupported >oneCRpage topology gets one gateway attempt and no producer.
 many=data+geos.native_text('Line.\r')*48
 canon,catalog,before=baseline(many);begin();f.settle();pixels(many);clean(canon,catalog)
 assert not any(t[0]in(47,49)for t in f.trace) and f.get('se_bc_flags',1)&128
 interval(before,f.reu());retry(canon,catalog,many);groups.append('unsupported-multiCRpage-bounded-fallback');print('AUTO_FAULT_PASS',groups[-1],flush=True)
 # Public presets and shortcode bypass must leave original overlay costs and
 # source semantics alone. No gateway, producer or linker is admitted.
 for preset in ('plain','markdown'):
  canon,catalog,before=baseline();f.trace=[];f.typed(geos.native_text('syntax '+preset));f.render()
  assert not any(t[0]in(45,47,49)for t in f.trace) and not f.get('se_bc_flags',1)&128
  bits,attrs,_=plain.expected(f,data,fonts,0 if preset=='plain'else 1)
  assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
  clean(canon,catalog);interval(before,f.reu());groups.append('actual-'+preset+'-bypass');print('AUTO_FAULT_PASS',groups[-1],flush=True)
 short=geos.native_text('Intro\r:::basic\r10 PRINT "Hi":REM tail\r:::\rTail.')
 canon,catalog,before=baseline(short);begin();f.settle();pixels(short);clean(canon,catalog)
 assert not any(t[0]in(45,47,49)for t in f.trace) and not f.get('se_bc_flags',1)&128
 interval(before,f.reu());groups.append('actual-short-bypass');print('AUTO_FAULT_PASS',groups[-1],flush=True)
 # Foreground owner checks happen before shared BC/CI/parent reads or writes.
 # The loader itself is allowed its normal slot/code-RAM changes, never phase.
 for id_,slot in ((45,1),(47,1),(49,1),(36,0),(37,0)):
  for owner in (0,1,2,3,5,255):
   f.put('se_f_owner',owner,1);f.m.load(F,bytes((i*73+19)&255 for i in range(576)));phase=f.read(F,576);ctx=f.read(0x9096,86);parent=f.read(0x9134,68);reu=f.reu()
   f.put('se_overlay_frame',0,1);r,n=f.fast_call(f.s['se_overlay_call'],a=id_,x=slot);f.total_instructions+=n
   assert r.p&1 and r.a==0xb2 and f.read(F,576)==phase and f.read(0x9096,86)==ctx and f.read(0x9134,68)==parent and f.reu()==reu and f.read(0xc600,1024)==f.shim
 f.put('se_f_owner',0,1);groups.append('30actual-foreign-owner-phaseopaque')
 # Competing ACTIVE BEGIN must not overwrite its context, flags or lease.
 for id_,slot in ((45,1),(47,1),(49,1)):
  f.put('se_f_owner',4,1);f.put('se_bc_flags',9,1);phase=f.read(F,576);ctx=f.read(0x9096,86);reu=f.reu();f.put('se_overlay_frame',0,1)
  r,n=f.fast_call(f.s['se_overlay_call'],a=id_,x=slot);f.total_instructions+=n
  assert r.p&1 and f.get('se_bc_flags',1)==9 and f.read(F,576)==phase and f.read(0x9096,86)==ctx and f.reu()==reu
 f.put('se_f_owner',0,1);groups.append('competing-ACTIVE-BEGIN-preserves-job')
 # Fresh source initialization clears private128; real baseline commit also
 # clears it (same-byte R33 mask specialization), rather than host retry clear.
 baseline();assert not f.get('se_bc_flags',1)&128;groups.append('fresh-source-initialization-revokes-private-attempt')
 f.source(data);f.typed(geos.native_text('syntax markdown'));f.command(99);f.call('se_editor_render')
 advance(lambda:f.m.read(0x9135)==34 and f.m.read(0x9136)==1 and f.get('se_bc_flags',1)&8)
 canon=f.canonical();catalog=f.catalog();f.put('se_bc_flags',f.get('se_bc_flags',1)|128,1);f.settle();f.render()
 assert f.get('se_bc_flags',1)&143==1 and f.canonical()==canon and f.catalog()==catalog and f.read(0xc600,1024)==f.shim and f.merged()==data
 groups.append('actual-fresh-baseline-R33-commit-revokes-private-attempt');print('AUTO_FAULT_PASS',groups[-1],flush=True)
 (out/'fault-groups.json').write_text(json.dumps(groups,indent=2)+'\n');return groups
