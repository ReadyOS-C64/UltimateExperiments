def run(out,previous=None,smoke=False):
 frozen,identity=geos.freeze(out,previous);assert len(identity['names'])==48
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 fonts={n:(frozen/'fonts'/n).read_bytes() for n in geos.GEOS_FONTS+('native8.bin',)};dll=geos.grid.runner(out);f=geos.Fixture(out,frozen,dll,True);frames=[];faults=[]
 plan=bytes((i*19+31)&255 for i in range(1024))
 def whole():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(f.m.handle,len(b),b);return b.raw
 def reservation_guard(checkpoint=False):
  # Sparse canonical anchors are reserved but not yet produced by this bridge
  # increment. Its packed continuation occupies525B after the486B reservation.
  # cp_valid47E3 aliases savedpacketbyte16: only require0 after restore/END.
  assert f.read(0x4592,14)==plan[402:416] and f.read(0x45A8,62)==plan[424:486],'certificate overwrote unowned76B ledger suffix around exact8B BSCwork'
  tag=f.m.read(0x4400)
  if tag in(1,2):
   count=f.m.read(0x443F);assert 0<count<=161
   assert all(v<4 for v in f.read(0x444A,count))and all(v<14 for v in f.read(0x44EB,count))
   if tag==2:assert f.read(0x4401,59)==f.read(0x9040+27,59),'completecertificate notcurrentC20identity'
  assert f.read(0x47F3,13)==plan[1011:],'bridge overwrote13B inactiveplan tail'
  if checkpoint:assert not f.get('se_st_cp_valid',1),'sourcegrid checkpoint remained valid after continuation'
 def check(data,tag,plan_guard=False):
  canonical=f.canonical();catalog=f.catalog();before=whole();used=f.total_instructions;f.render();bits,attrs,rows,model=expected(f,data,fonts)
  actual=f.read(0x6000,8000);attributes=f.read(0x4000,1000)
  for n,b in [('actual-bitmap',actual),('expected-bitmap',bits),('actual-attrs',attributes),('expected-attrs',attrs),('source',data)]: (out/(tag+'-'+n+'.bin')).write_bytes(b)
  geos.png(actual,attributes,out/(tag+'-cpu.png'))
  assert actual==bits,(tag,'pixels',next((i,a,b) for i,(a,b) in enumerate(zip(actual,bits)) if a!=b))
  assert attributes==attrs,(tag,'attributes',next((i,a,b) for i,(a,b) in enumerate(zip(attributes,attrs)) if a!=b))
  cache,physical=f.cache();assert cache[0]==1 and cache[1]==len(rows)
  for i,row in enumerate(rows):
   at=0x200+i*0x800;record=cache[at:at+32];count=row.end-row.start
   assert tuple(int.from_bytes(record[p:p+3],'little') for p in (0,3,6))==(row.start,row.end,row.next),(tag,'anchors',i)
   assert int.from_bytes(record[12:14],'little')==count
   assert cache[at+32:at+32+count]==data[row.start:row.end]
   assert cache[at+192:at+192+count]==model.styles[row.start:row.end],(tag,'styles',i,cache[at+192:at+192+count].hex(),model.styles[row.start:row.end].hex())
   assert cache[at+352:at+352+count]==model.roles[row.start:row.end],(tag,'roles',i)
   x=[0]
   for p in range(row.start,row.end):x.append(x[-1]+(8 if row.height==8 else fonts['bsw9-widths.bin'][geos.native(data[p])]+(model.styles[p]&1)+(model.styles[p]&2)))
   assert [int.from_bytes(cache[at+512+j*2:at+514+j*2],'little') for j in range(count+1)]==x,(tag,'independentstyleXmap',i)
  after=whole();start=physical*65536;assert before[:start]==after[:start] and before[start+65536:]==after[start+65536:],(tag,'foreignREU')
  assert f.canonical()==canonical and f.catalog()==catalog and f.merged()==data and f.read(0xC600,1024)==f.shim
  assert not any(f.get(n,1) for n in ['se_f_owner','se_doc_read_locks','se_fs_owned','se_e_error'])
  if plan_guard:reservation_guard(checkpoint=True)
  frames.append(dict(tag=tag,source_bytes=len(data),rows=len(rows),instructions=f.total_instructions-used,bitmap_sha256=hashlib.sha256(bits).hexdigest()))
  (out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
 def start(data):
  f.source(data);f.command(99);f.m.load(0x4400,plan);assert not f.get('se_st_valid',1)
  r=f.call('se_editor_render');assert not r.p&1 and f.get('se_e_job',1)==11
 def until(predicate):
  for i in range(100000):
   reservation_guard()
   if predicate():return i
   r=f.call('se_editor_service');assert not r.p&1,('service',hex(r.a),f.debug())
   assert f.get('se_e_job',1) in (11,12),('unexpected end',f.debug())
  raise AssertionError('bridge state not reached')
 def remove(id_,slot):
  idx=next(i for i in range(f.s['se_overlay_capacity']) if f.m.read(f.s['se_overlay_ids']+i)==id_ and f.catalog()[f.s['se_overlay_capacity']+i]==slot)
  f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active']+slot,0);return idx
 def stop(tag,foreign=0):
  canonical=f.canonical();f.queued(3);f.call('se_editor_service');assert f.canonical()==canonical and f.get('se_doc_read_locks',1)==foreign
  assert not any(f.get(n,1) for n in ['se_f_owner','se_fs_owned','se_e_job','se_e_draw_busy']) and not f.m.read(0x912D),(tag,f.debug())
 try:
  f.source(DATA);f.command(99);f.m.load(0x4400,plan);check(DATA,'inline-metrics',True)
  if not smoke:
   # A styled cached-page navigation job also crosses C20/C26 and must resume
   # its owning C23, retaining a pixel preferred column, not a byte column.
   f.position(5);model=classify(DATA)
   _,_,nav_rows=semantic.raster(DATA,fonts,styles=model.styles,roles=model.roles,reverse=model.reverse,code=model.code)
   preferred=sum(fonts['bsw9-widths.bin'][geos.native(DATA[p])]+(model.styles[p]&1)+(model.styles[p]&2) for p in range(5))
   target=nav_rows[1];boundaries=[0]
   for p in range(target.start,target.end):boundaries.append(boundaries[-1]+fonts['bsw9-widths.bin'][geos.native(DATA[p])]+(model.styles[p]&1)+(model.styles[p]&2))
   wanted=target.start+min(range(len(boundaries)),key=lambda i:(abs(boundaries[i]-preferred),-i))
   f.command(37);assert f.get('se_hot_caret')==wanted and f.get('se_l_preferred')==preferred,('styledDOWN',wanted,f.get('se_hot_caret'),preferred,f.get('se_l_preferred'))
   check(DATA,'styled-nav-DOWN');f.command(36);assert f.get('se_hot_caret')==5 and f.get('se_l_preferred')==preferred;check(DATA,'styled-nav-UP')
   for text in ['No markers. Plain rows\rnext.', '**'+('W'*70)+'**\r', '*'+('Wim '*20)+'*\r', '***bold italic***\r', '**outer @@code *literal*@@ end**\r', 'unmatched **bold and @@code\r', '# **Heading** and *tail*\r- @@item@@ ***both***\r']:
    data=geos.native_text(text);f.source(data);f.command(99);f.m.load(0x4400,plan);check(data,'sample-'+str(len(frames)),True)
    if not any(c in data for c in b'*@'):
     want_plan=bytearray(plan);want_plan[f.s['se_st_cp_valid']-0x4400]=0;want_plan[0]=0;want_plan[396]=0 #explicitBEGIN certificate invalidation, no-lookahead path otherwiseunchanged
     assert f.read(0x4400,1024)==want_plan,'no-marker path performed lookahead/plan reuse'
   # Real pending edit within a pair changes metrics while preserving source.
   data=geos.native_text('**'+('Wim '*20)+'**\r');f.source(data);f.command(99);f.position(40);f.key(geos.native_text('Q')[0]);data=data[:40]+geos.native_text('Q')+data[40:];assert f.get('se_hot_pending',1);check(data,'pending-inline')
   # Stop while C20 has surrendered its old lease and C26 has acquired its own.
   for stage in ['handoff','child','resume']:
    start(DATA);assert not f.call('se_doc_read_acquire').p&1
    until(lambda:f.m.read(0x9135)==26 and f.m.read(0x9136)==3)
    assert f.get('se_doc_read_locks',1)==1 and not f.m.read(0x912D)
    if stage!='handoff':
     f.call('se_editor_service');assert f.get('se_doc_read_locks',1)==2
     if stage=='resume':
      until(lambda:f.m.read(0x9135)==20 and f.m.read(CONT)==1)
      assert f.get('se_doc_read_locks',1)==1 and not f.m.read(0x912D)
    stop('STOP-'+stage,1);assert not f.call('se_doc_read_release').p&1;faults.append('STOP-'+stage+' preserves foreign lease')
    check(DATA,'after-STOP-'+stage)
   # Change actual canonical revision exactly between C26 END and fresh C20 BEGIN.
   start(DATA);until(lambda:f.m.read(0x9135)==26 and f.m.read(0x9136)==3);f.call('se_editor_service');until(lambda:f.m.read(0x9135)==20 and f.m.read(CONT)==1)
   before=f.canonical();f.put('se_r_revision',f.get('se_r_revision',4)+1,4);r=f.call('se_editor_service');assert r.p&1 and r.a==0 and f.get('se_e_error',1)==0x74 and f.canonical()==before
   assert not any(f.get(n,1) for n in ['se_f_owner','se_doc_read_locks','se_fs_owned','se_e_job']);faults.append('fresh C20 reader rejects changed full source identity before feed')
   for id_,stage in [(26,'handoff'),(20,'resume'),(14,'resume')]:
    start(DATA);until(lambda:f.m.read(0x9135)==26 and f.m.read(0x9136)==3)
    if stage=='resume':f.call('se_editor_service');until(lambda:f.m.read(0x9135)==20 and f.m.read(CONT)==1)
    idx=remove(id_,0 if id_==14 else 1);r=f.call('se_editor_service');assert r.p&1 and r.a==0 and f.get('se_e_error',1)==0x17
    assert not any(f.get(n,1) for n in ['se_f_owner','se_doc_read_locks','se_fs_owned','se_e_job']);f.m.write(f.s['se_overlay_ids']+idx,id_);faults.append('missing'+str(id_)+' cleanup primary17')
   for stage in ('before-consume','after-consume'):
    start(DATA);until(lambda:f.m.read(0x9135)==20 and f.m.read(0x9136)==7)
    assert f.m.read(0x4400)==2 and not f.m.read(0x912D)
    if stage=='after-consume':
     r=f.call('se_editor_service');assert not r.p&1
    canonical=f.canonical();f.put('se_r_revision',f.get('se_r_revision',4)+1,4)
    for tick in range(3):
     r=f.call('se_editor_service')
     if r.p&1:break
    assert r.p&1 and f.get('se_e_error',1)==0x74,(stage,f.debug())
    assert f.canonical()==canonical and not any(f.get(n,1) for n in ['se_f_owner','se_doc_read_locks','se_fs_owned','se_e_job'])
    faults.append('certificate '+stage+' current-source guard rejects changedrevision before pixels')
   start(DATA);until(lambda:f.m.read(0x9135)==20 and f.m.read(0x9136)==7)
   assert not f.call('se_doc_read_acquire').p&1;stop('STOP-certificate',1);assert not f.call('se_doc_read_release').p&1
   faults.append('STOP completed-certificate handoff preservesforeignlease')
   for at,label in [(0x4401,'key'),(0x4440,'context'),(0x443F,'count')]:
    start(DATA);until(lambda:f.m.read(0x9135)==20 and f.m.read(0x9136)==7)
    f.m.write(at,0 if label=='count' else f.m.read(at)^1)
    r=f.call('se_editor_service');assert not r.p&1 and f.m.read(0x9135)==26 and f.m.read(0x9136)in(0,4),(label,f.debug())
    f.settle();check(DATA,'certificate-'+label+'-fallback');faults.append('certificate '+label+' mismatch usesoriginalC26')
   start(DATA);until(lambda:f.m.read(0x9135)==20 and f.m.read(0x9136)==7)
   for owner in(0,1,2,3,5,255):
    f.put('se_f_owner',owner,1);phase=f.read(0x8B40,0x640);certificate=f.read(0x4400,402);reu=whole()
    f.put('se_overlay_frame',7,1);r,n=f.fast_call(f.s['se_overlay_call'],a=20,x=1)
    assert r.p&1 and r.a==0xB2 and f.read(0x8B40,0x640)==phase and f.read(0x4400,402)==certificate and whole()==reu,(owner,'opaque consume refusal')
   f.put('se_f_owner',4,1);stop('opaque-certificate');faults.append('sixforeignowners op7 opaque entirephase/certificate/16MiB')
   def window_ready():
    return f.m.read(0x9135)==20 and f.m.read(0x9136)==1 and not f.m.read(CONT) and f.m.read(0x912C)==1 and f.m.read(0x458C)==1 and int.from_bytes(f.read(0x8D00+38,3),'little')+32<=int.from_bytes(f.read(0x458D,3),'little')+f.m.read(0x4590)
   start(DATA);until(window_ready)
   scan=int.from_bytes(f.read(0x8D00+38,3),'little');buf=f.read(0x8300,160)+f.read(0x8F36,160);reu=whole();canonical=f.canonical()
   r=f.call('se_editor_service');assert not r.p&1 and f.m.read(0x9135)!=26
   assert f.read(0x8300,160)+f.read(0x8F36,160)==buf,'R14/measure changed retainedC26outputs'
   n=f.m.read(0x8D00+29);assert n<=32 and f.read(0x90EC,n)==DATA[scan:scan+n],'window changed actual32byte nativepacket'
   assert whole()==reu and f.canonical()==canonical
   stop('after-window-hit');faults.append('actualwindowhit retains320B outputs/nativepacket32/full16MiB')
   start(DATA);until(window_ready);canonical=f.canonical();f.put('se_r_revision',f.get('se_r_revision',4)+1,4)
   r=f.call('se_editor_service');assert r.p&1 and f.get('se_e_error',1)in(0x74,0xB1)
   assert f.canonical()==canonical and not any(f.get(n,1)for n in('se_f_owner','se_fs_owned','se_doc_read_locks','se_e_job'))
   faults.append('windowhit originalR14 fullsourceguard rejects revisionchange')
   start(DATA);until(window_ready);assert not f.call('se_doc_read_acquire').p&1;stop('STOP-window',1);assert not f.call('se_doc_read_release').p&1
   faults.append('STOP held-windowlease preservesforeigncount')
   for address,value,label in((0x458C,2,'tag'),(0x4590,161,'count'),(0x458D,255,'query')):
    start(DATA);until(window_ready);f.m.write(address,value)
    r=f.call('se_editor_service');assert not r.p&1,(label,'window/cache refetch failed') #authenticatedFE may replace C26; independentpixels below unchanged
    f.settle();check(DATA,'window-'+label+'-fallback');faults.append('window '+label+' refusal/refetch exactpixels')
   # The overwritten inactive40-column plan must never be used after mode return.
   f.source(DATA);f.command(99);f.m.load(0x4400,plan);check(DATA,'before-source40-return',True)
   f.command(96);f.render();f.recolor();assert f.get('se_st_valid',1)
   (matrix,colors),_,_,_=geos.grid.expected(f,DATA);assert f.read(0x4000,1000)==matrix and bytes(c&15 for c in f.read(0xD800,1000))==colors
   f.command(99);check(DATA,'after-source40-roundtrip');faults.append('inactive source40 plan invalidated and rebuilt across mode roundtrip')
  result=dict(status='passed',identity=identity,frames=frames,faults=faults,scope='Actual public C20/C26 bridge, independent inline styles/metrics/pixels and lifetime recovery; CPU only')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status='passed',frames=len(frames),faults=len(faults),out=str(out)),indent=2));return result
 finally:f.close()
