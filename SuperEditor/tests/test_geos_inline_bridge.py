"""Actual editor C20→C26→C20 inline metrics, identities, leases and plan lifetime."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,json,hashlib,zipfile
import test_geos_semantic_editor as semantic
from supermark_model import inline
geos=semantic.geos;ROOT=geos.ROOT
CONT=0x8BE7
DATA=geos.native_text('# Heading **bold** and *italic*\r- ***both*** and @@code **literal**@@\r'
    'A **'+('Wim '*22)+'nested *italic* end** tail\rEscaped \\*literal* and **yes**.\r')

def classify(data):
 base=semantic.classify(data);styles=bytearray(base.styles);roles=bytearray(base.roles);exclusive=bytearray(len(data))
 for event in base.events:
  if event['kind']>=4:continue
  a,b=event['body'],event['end']
  for kind,style,width,start,end in inline(data[a:b],start=a,body_column=a-event['start'] if a>event['start'] else None):
   if kind!=1:continue
   for at in range(start+width,end):
    if style==4:styles[at]=0;roles[at]=4;exclusive[at]=1
    elif not exclusive[at]:styles[at]|=(1 if style&2 else 0)|(2 if style&1 else 0)
 return semantic.Semantic(bytes(styles),bytes(roles),base.reverse,base.code,base.events,base.eof_kind,base.eof_language)

def expected(f,data,fonts):
 model=classify(data);bits,attrs,rows=semantic.raster(data,fonts,top=f.get('se_v_top'),caret=f.get('se_hot_caret'),anchor=f.get('se_sel_anchor') if f.get('se_sel_mark',1) else None,styles=model.styles,roles=model.roles,reverse=model.reverse,code=model.code)
 attrs=bytearray(attrs)
 for row in rows:
  if row.height==8:
   for col,at in enumerate(range(row.start,row.end)):attrs[(row.top//8)*40+col]=(semantic.PALETTE[model.roles[at]]<<4)|6
 matrix,colors,popup=geos.grid.logical_ui(f,data);bits,attrs=geos.with_chrome(bits,bytes(attrs),matrix,colors,fonts['native8.bin'],popup)
 return bits,attrs,rows,model

def run(out,previous=None,smoke=False):
 frozen,identity=geos.freeze(out,previous);assert len(identity['names'])==32
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 fonts={n:(frozen/'fonts'/n).read_bytes() for n in geos.GEOS_FONTS+('native8.bin',)};dll=geos.grid.runner(out);f=geos.Fixture(out,frozen,dll,True);frames=[];faults=[]
 plan=bytes((i*19+31)&255 for i in range(1024))
 def whole():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(f.m.handle,len(b),b);return b.raw
 def reservation_guard(checkpoint=False):
  # Sparse canonical anchors are reserved but not yet produced by this bridge
  # increment. Its packed continuation occupies525B after the486B reservation.
  # cp_valid47E3 aliases savedpacketbyte16: only require0 after restore/END.
  assert f.read(0x4400,486)==plan[:486],'bridge overwrote reserved canonical anchors'
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
  idx=next(i for i in range(f.s['se_overlay_capacity']) if f.m.read(f.s['se_overlay_ids']+i)==id_ and f.m.read(f.s['image_slot']+i)==slot)
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
     want_plan=bytearray(plan);want_plan[f.s['se_st_cp_valid']-0x4400]=0
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
   # The overwritten inactive40-column plan must never be used after mode return.
   f.source(DATA);f.command(99);f.m.load(0x4400,plan);check(DATA,'before-source40-return',True)
   f.command(96);f.render();f.recolor();assert f.get('se_st_valid',1)
   (matrix,colors),_,_,_=geos.grid.expected(f,DATA);assert f.read(0x4000,1000)==matrix and bytes(c&15 for c in f.read(0xD800,1000))==colors
   f.command(99);check(DATA,'after-source40-roundtrip');faults.append('inactive source40 plan invalidated and rebuilt across mode roundtrip')
  result=dict(status='passed',identity=identity,frames=frames,faults=faults,scope='Actual public C20/C26 bridge, independent inline styles/metrics/pixels and lifetime recovery; CPU only')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status='passed',frames=len(frames),faults=len(faults),out=str(out)),indent=2));return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-inline-bridge'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,a.fixture,a.smoke)
