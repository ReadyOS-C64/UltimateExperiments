"""Private feature3-aware actual classification, preserving baseline C35.

The host performs only the root REQUEST/OP scheduling seam; every worker is an
actual imported capsule and every source/typed/page proof is executed 6502.
No host semantic records, CP, flags or source-key certificates are fabricated.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,hashlib,binascii
import test_cache_observer as ob
import test_cache_splice as sp
from supermark_model import blocks,inline
ROOT=ob.ROOT
BASE=ROOT/'build/cache-editor-product/20261026T045019460982Z/fixture'
F=0x8D00;G=0x8B40
DATA=ob.geos.native_text('Alpha ordinary text.\rMiddle ordinary line.\rOmega tail.\r')
FIELDS=[('kind',5,1),('language',6,1),('level',7,1),('marker',8,1),('start',9,3),('end',12,3),('body',15,3),('role',18,1),('reverse',19,1),('height',20,1),('inline',169,1)]

def build(out,base):
 p=ROOT/'src/cache/splice-query-probe/build.py';s=importlib.util.spec_from_file_location('querybuilder',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m.build(out,base)

def expected(data,pos):
 events=blocks(data)+[dict(kind=255,start=len(data),end=len(data),body=len(data),language=0,level=0)]
 e=next(v for v in events if v['start']<=pos<=v['end']);kind=e['kind']if e['kind']!=255 else 0
 # The same semantic projection as the parser, derived from canonical source.
 # INLINE is only an absence hint: completed eventless records prove0. Tests
 # use no inline delimiters, so every actual complete record certifies empty.
 return dict(kind=kind,language=e['language'],level=e['level'],marker=(e['body']-e['start'])if e['body']-e['start']<256 else 0,start=e['start'],end=e['end'],body=e['body'],role=2 if kind==2 else 1 if kind==3 else 4 if kind in(4,5,6)else 0,reverse=int(kind==2),height=8 if kind==5 else 9,inline=int(e['kind']==255 or(kind<4 and bool(inline(data[e['body']:e['end']]+b'\r',body_column=e['body']-e['start'])))))

def run(out,base,smoke=False,region=False,mixed=False,inline_case=False):
 (out/'verifier.py').write_bytes(Path(__file__).read_bytes())
 images=build(out/'build',base);gate=ob.Gate(out/'gate',base);f=gate.f
 for n,image in images.items():f.assets[n]=image
 calls=[];queries=[];faults=[];source=DATA
 if region:source=ob.geos.native_text(':::region Group\rAlpha ordinary text.\rMiddle ordinary line.\r:::end\rOmega tail.\r')
 if inline_case:source=ob.geos.native_text('Alpha **strong** text.\rMiddle ordinary line.\rOmega *tail* @@code@@.\r')
 if mixed:source=ob.geos.native_text('# Heading\rAlpha ordinary text.\rMiddle ordinary line.\r- item\r:::basic\r10 PRINT "X"\r:::\r:::region Group\rOmega tail.\r:::end\r')
 def invoke(ident,op):
  f.put('se_overlay_frame',op,1);r,n=f.fast_call(f.s['se_overlay_call'],a=ident,x=1)
  calls.append(dict(id=ident,op=op,a=r.a,carry=r.p&1,instructions=n,state=f.m.read(F+1),qstate=f.m.read(F+53),request=f.m.read(0x9135),next_op=f.m.read(0x9136)));return r
 def arena():
  token=f.read(f.s['se_bc_arena'],5);logical=f.m.read(f.s['object_extents']+token[0]*16);bank=f.m.read(f.s['se_reu_map']+logical);return bank,gate.reu()[bank*65536:(bank+1)*65536]
 def queue():return f.read(f.s['se_bc_arena'],13)+f.read(f.s['se_bc_head'],3)+f.read(f.s['se_bc_ring'],96)
 def seed():
  f.source(source);f.typed(ob.geos.native_text('syntax markdown'));f.command(99);f.render();assert f.get('se_bc_count',1)==0 and f.get('se_bc_flags',1)&1
 def input_at(pos):
  # All outputs begin poisoned, but caller input and parent controller retained.
  f.m.load(G,pos.to_bytes(3,'little')+b'\x02\xA0'+bytes([0xA5])*187);f.m.write(G+21,0)
  f.m.load(0x8100,bytes((i*47+29)&255 for i in range(768)))
  f.m.load(0x9134,bytes((i*31+17)&255 for i in range(68)))
  f.put('se_f_owner',4,1)
 def consume(data,pos,route):
  input_at(pos);before=gate.reu();stable=gate.stable();canonical=f.canonical();q=queue();parent=f.read(0x9134,68);packet=f.read(0x8100,768);display=f.read(0x4000,0x1000)+f.read(0x6000,0x2000);count=len(calls)
  r=invoke(41,0);seen=[]
  for _ in range(200):
   assert not r.p&1,('consumer',pos,r.a,calls[-15:])
   assert gate.reu()==before,'query wrote REU'
   assert queue()==q,'query changed arena/ticket/incarnation/queue'
   assert gate.stable()==stable and f.canonical()==canonical,'query changed canonical/history/hot window'
   assert f.merged()==data,'query changed source'
   assert f.read(0x8100,768)==packet,'parent source buffers'
   assert f.read(0x4000,0x1000)+f.read(0x6000,0x2000)==display,'classification touched display/style storage'
   now=f.read(0x9134,68);assert now[:1]+now[3:]==parent[:1]+parent[3:],'parent controller'
   assert f.read(G,5)==pos.to_bytes(3,'little')+b'\x02\xA0'
   if r.a==0:break
   assert r.a==1
   target=f.m.read(0x9135);op=f.m.read(0x9136);assert target in(35,41)
   seen.append(target);r=invoke(target,op)
  assert r.a==0 and not r.p&1 and not f.get('se_doc_read_locks',1)and not f.get('se_bc_flags',1)&8 and f.get('se_f_owner',1)==4
  actual={name:int.from_bytes(f.read(G+off,width),'little')for name,off,width in FIELDS}
  assert actual==expected(data,pos),(pos,actual,expected(data,pos))
  assert f.m.read(G+21)==0 and f.m.read(G+24)==0 and f.m.read(G+28)==0
  assert f.read(0xC600,1024)==f.shim
  assert (35 in seen)==(route=='legacy'),(route,seen)
  if route=='mapped':
   cr=f.read(F+291,96);origin=f.m.read(F+54);ticket=int.from_bytes(cr[12:16],'little');assert ticket==(f.get('se_bc_ticket',4)if origin else int.from_bytes(old[2][22:26],'little'))
   assert binascii.crc_hqx(cr[1:74]+cr[76:],65535)==int.from_bytes(cr[74:76],'little')
  queries.append(dict(position=pos,route=route,actual=actual,calls=len(calls)-count,instructions=sum(c['instructions']for c in calls[count:]),origin=f.m.read(F+54)))
 def rebase():
  seed();at=source.index(ob.geos.native_text('ordinary'),source.index(ob.geos.native_text('Middle')))+3;f.position(at);f.key(ob.Q);wanted=source[:at]+bytes([ob.Q])+source[at:];assert f.merged()==wanted and f.get('se_bc_count',1)==1
  bank,raw=arena();old=sp.roots(raw);before=gate.reu();stable=gate.stable();q=queue();f.put('se_f_owner',4,1);r=invoke(40,0)
  for _ in range(200):
   assert not r.p&1,('rebase',r.a,calls[-15:])
   if r.a==0:break
   assert r.a==1 and gate.stable()==stable and queue()==q
   r=invoke(40,1)
  assert r.a==0 and f.get('se_bc_count',1)==0 and f.merged()==wanted
  after=gate.reu();allowed=bytearray(before)
  for lo,hi in((old[1]^128,(old[1]^128)+128),(0x178,0x180),(0x900,0x920),(0xF000,0xF120)):allowed[bank*65536+lo:bank*65536+hi]=after[bank*65536+lo:bank*65536+hi]
  assert after==allowed and after[bank*65536+old[1]:bank*65536+old[1]+128]==old[2]
  return wanted,bank,old,stable
 try:
  seed()
  # Baseline0 dispatch is actual unchanged C35, never a selector reimplementation.
  legacy_asset=f.assets['inln'];legacy_sha=hashlib.sha256(legacy_asset).hexdigest()
  for pos in(0,source.index(ob.geos.native_text('Middle')),len(source)):consume(source,pos,'legacy')
  if inline_case:
   # Released one-SPLICE producer is explicitly one-CR-page only. An unchanged
   # inline stream can produce additional CR pages, so preserve that refusal
   # rather than expanding edit/schema support in this consumer task.
   seed();at=source.index(ob.geos.native_text('ordinary'))+3;f.position(at);f.key(ob.Q);wanted=source[:at]+bytes([ob.Q])+source[at:];full=gate.reu();q=queue();canonical=f.canonical();f.put('se_f_owner',4,1);r=invoke(40,0)
   for _ in range(100):
    if r.p&1 or r.a!=1:break
    r=invoke(40,1)
   assert r.p&1 and r.a==0xC1 and gate.reu()==full and queue()==q and f.canonical()==canonical and f.merged()==wanted and not f.get('se_doc_read_locks',1)
   (out/'source-before.bin').write_bytes(source);(out/'source-after.bin').write_bytes(wanted)
   (out/'result.json').write_text(json.dumps(dict(status='PASS-private-baseline-inline-and-preserved-splice-refusal',fixture=gate.identity,budget=json.loads((out/'build/budget.json').read_text()),queries=queries,calls=calls,faults=['unsupported-multiple-CR-pages-refused-C1'],production_C35_sha256=legacy_sha),indent=2)+'\n')
   print('SPLICE QUERY INLINE BASELINE + NARROW REFUSAL PASS',out,flush=True);return
  wanted,bank,old,stable=rebase();(out/'source-before.bin').write_bytes(source);(out/'source-after.bin').write_bytes(wanted);parser_feeds=int.from_bytes(f.read(F+58,3),'little');before=gate.reu();baseline=f.assets['inln'];assert baseline==legacy_asset
  # The original classifier continues to refuse feature3; only C41 understands it.
  input_at(0);r=invoke(35,0)
  for _ in range(100):
   if r.p&1 or r.a!=1:break
   r=invoke(35,1)
  assert r.p&1 and r.a==0xC2 and not f.get('se_doc_read_locks',1)and gate.reu()==before
  positions=(0,wanted.index(ob.geos.native_text('Middle')),len(wanted))if smoke else range(len(wanted)+1)
  for pos in positions:consume(wanted,pos,'mapped')
  if not smoke:
   # Cancellation at each selector/mapped transport yield leaves cache/queue,
   # source, history and semantic output uncommitted. No record is retired.
   for state,sub in [(7,0)]+[(6,n)for n in range(1,8)]:
    input_at(0);full=gate.reu();q=queue();stable=gate.stable();r=invoke(41,0)
    for _ in range(150):
     assert not r.p&1 and r.a==1
     if f.m.read(F+1)==state and(state==7 or f.m.read(F+53)==sub):break
     r=invoke(41,1)
    assert f.m.read(F+1)==state and(state==7 or f.m.read(F+53)==sub)
    outputs=f.read(G+5,16)+f.read(G+169,1);r=invoke(41,2)
    assert not r.p&1 and r.a==0 and f.read(G+5,16)+f.read(G+169,1)==outputs and not f.get('se_doc_read_locks',1)
    assert gate.reu()==full and queue()==q and gate.stable()==stable and f.merged()==wanted
    faults.append(f'cancel-{state}-{sub}')
    print('CANCEL PASS',state,sub,flush=True)
  if not smoke:
   def pending(sub=1):
    input_at(0);r=invoke(41,0)
    for _ in range(150):
     assert not r.p&1 and r.a==1
     if f.m.read(F+1)==6 and f.m.read(F+53)==sub:return
     r=invoke(41,1)
    raise AssertionError('target yield not reached')
   def finish_fault(label):
    full=gate.reu();q=queue();stable_=gate.stable();outputs=f.read(G+5,16)+f.read(G+169,1)
    r=invoke(41,1)
    for _ in range(150):
     if r.p&1 or r.a!=1:break
     r=invoke(41,1)
    assert r.p&1 or r.a==2,(label,r.a)
    assert gate.reu()==full,(label,'REU changed')
    assert queue()==q,(label,'queue changed')
    assert gate.stable()==stable_,(label,'canonical/history changed')
    assert f.merged()==wanted,(label,'source bytes',f.merged(),wanted)
    assert f.read(G+5,16)+f.read(G+169,1)==outputs,(label,'premature semantic publication')
    assert not f.get('se_doc_read_locks',1)and not f.get('se_bc_flags',1)&8,(label,'lease')
    faults.append(label);print('FAULT PASS',label,hex(r.a),flush=True)
   # Real missing-leaf catalog faults, source/observer identity change, and
   # mode loss across a yield must release via the resident END capability.
   for ident in (14,34):
    pending();idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)&1==0)
    f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active'],0)
    finish_fault('missing-R'+str(ident));f.m.write(f.s['se_overlay_ids']+idx,ident)
   for label,name,width,value in [('revision','se_r_revision',4,None),('ticket','se_bc_ticket',4,None),('caps','se_render_caps',1,0),('queue-head','se_bc_head',1,3)]:
    pending();saved=f.get(name,width);f.put(name,saved+1 if value is None else value,width)
    finish_fault('changed-'+label);f.put(name,saved,width)
   # The owner guard is opaque even while a legitimate reader is live.
   pending();phase=f.read(F,576);scratch=f.read(0x8880,0x2C0);gs=f.read(G,192);full=gate.reu();q=queue()
   for owner in (0,1,2,3,5,255):
    f.put('se_f_owner',owner,1)
    for op in (0,1,2):
     r=invoke(41,op);assert r.p&1 and r.a==0xB2 and f.read(F,576)==phase and f.read(0x8880,0x2C0)==scratch and f.read(G,192)==gs and gate.reu()==full and queue()==q
   f.put('se_f_owner',4,1);r=invoke(41,2);assert r.a==0 and not r.p&1
   faults.append('six-foreign-owners-three-ops-opaque')
   input_at(0);phase=f.read(F,576);scratch=f.read(0x8880,0x2C0);gs=f.read(G,192);f.put('se_render_caps',0,1);full=gate.reu();r=invoke(41,0)
   assert r.a==2 and not r.p&1 and f.read(F,576)==phase and f.read(0x8880,0x2C0)==scratch and f.read(G,192)==gs and gate.reu()==full
   f.put('se_render_caps',1,1);faults.append('Plain-before-frame')
   def stash(offset,payload):
    # Explicit fault injection through actual checked logical object API;
    # never fabricated positive semantic/cache records.
    token=f.read(f.s['se_bc_arena'],5);f.m.load(f.s['se_object_id'],token);f.put('se_object_offset',offset);f.put('se_object_length',len(payload),2);f.put('se_object_c64',0x8000,2);f.m.load(0x8000,payload)
    r=f.call('se_object_copy',0);assert not r.p&1,hex(r.a)
    f.call('se_doc_invalidate') # discard derived leaf authority after an explicit fault-injection loan
   b,raw=arena();live=sp.roots(raw)
   for feature in (0,2,5,7,255):
    bad=bytearray(live[2]);bad[31]=feature;bad[119:121]=binascii.crc_hqx(bad[:5]+bad[6:119]+bad[121:],65535).to_bytes(2,'little');stash(live[1],bad)
    input_at(0);full=gate.reu();q=queue();r=invoke(41,0)
    for _ in range(150):
     if r.p&1 or r.a!=1:break
     r=invoke(41,1)
    assert r.p&1 and r.a in (0xC1,0xC2)and gate.reu()==full and queue()==q and not f.get('se_doc_read_locks',1)
    assert f.read(G+5,16)==bytes([0xA5])*16 and f.m.read(G+169)==0xA5
    stash(live[1],live[2]);faults.append('unknown-feature-'+str(feature))
   # An ordinary typed-page corruption is not a hint to reuse unverified CRs.
   bad=bytes([raw[0xF040]^1]);stash(0xF040,bad);pending();finish_fault('mapped-page-CRC');stash(0xF040,raw[0xF040:0xF041])
   input_at(0);f.put('se_overlay_frame',0,1);r,n=f.fast_call(f.s['se_overlay_call'],a=14,x=0);assert not r.p&1 and f.get('se_doc_read_locks',1)==1
   phase=f.read(F,576);gs=f.read(G,192);full=gate.reu();r=invoke(41,0)
   assert r.a==2 and not r.p&1 and f.read(F,576)==phase and f.read(G,192)==gs and gate.reu()==full and f.get('se_doc_read_locks',1)==1 and f.get('se_fs_owned',1)==1
   f.call('se_fs_end');assert not f.get('se_doc_read_locks',1);faults.append('foreign-actual-reader-lease-not-ended')
   # Missing outer C41 is safe under the actual resident unavailable-worker
   # cleanup: its BC_ACTIVE/saved86 format is intentionally the existing ABI.
   pending();q=queue();full=gate.reu();stable_=gate.stable();idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==41 and f.m.read(f.s['image_slot']+i)&1==1)
   f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active']+1,0);f.put('se_e_job',11,1);f.m.load(0x9135,bytes((41,1)));f.call('se_editor_service')
   assert f.get('se_e_error',1)==0x17 and f.get('se_e_job',1)==0 and f.get('se_f_owner',1)==0 and not f.get('se_doc_read_locks',1)and not f.get('se_bc_flags',1)&8 and gate.reu()==full and queue()==q and gate.stable()==stable_
   f.m.write(f.s['se_overlay_ids']+idx,41);faults.append('missing-C41-resident-cancel')
   # Retired first SPLICE is not permission to hide a second real edit.
   f.put('se_f_owner',0,1);f.key(ob.Q);second=f.merged();assert second!=wanted
   input_at(0);phase=f.read(F,576);full=gate.reu();q=queue();r=invoke(41,0)
   assert r.a==2 and not r.p&1 and f.read(F,576)==phase and gate.reu()==full and queue()==q and f.merged()==second
   faults.append('second-public-edit-unread-SPLICE-refused')
   # A real typed-object eviction invalidates the consumer capability. This
   # test deliberately releases it; the query itself never frees anything.
   wanted,bank,old,stable=rebase();pending();token=f.read(f.s['se_bc_arena'],5);f.m.load(f.s['se_object_id'],token);r=f.call('se_object_release');assert not r.p&1
   finish_fault('actual-type53-release-across-yield')

  result=dict(status='PASS-private-feature3-classification',fixture=gate.identity,budget=json.loads((out/'build/budget.json').read_text()),production_C35_sha256=legacy_sha,source_bytes=len(wanted),actual_reparsed_dirty_line_feeds=parser_feeds,queries=queries,faults=faults,calls=calls,whole16MiB_queries_unchanged=True,original_C35_unknown_feature_refusal='C2',scheduling='host only schedules actual REQUEST/OP; no nested C calls')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('SPLICE QUERY PASS',out,len(queries),'classifications',len(faults),'faultgroups',flush=True)
 except BaseException as e:
  (out/'failure.json').write_text(json.dumps(dict(error=repr(e),calls=calls,queries=queries),indent=2)+'\n');(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--smoke',action='store_true');p.add_argument('--region',action='store_true');p.add_argument('--mixed',action='store_true');p.add_argument('--inline',dest='inline_case',action='store_true');a=p.parse_args();out=ROOT/'build/cache-splice-query'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture,a.smoke,a.region,a.mixed,a.inline_case)
