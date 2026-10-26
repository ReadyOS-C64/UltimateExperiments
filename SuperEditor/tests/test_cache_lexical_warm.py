"""Private lexical batching/local same-call guard-hoist actual59 CPU proof."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_observer as ob
import test_plain_geos as plain
geos=ob.geos
BASE=ROOT/'build/capture-index-fixed/20261026T183928480377Z/fixture'
spec=importlib.util.spec_from_file_location('private_lexical_warm_build',ROOT/'src/cache/lexical-warm-probe/build.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


def arena(f,reu):
 token=f.read(f.s['se_bc_arena'],5);oid=token[0];assert token!=bytes(5)and oid<8
 assert f.m.read(f.s['object_owner']+oid)==0x53
 assert token[1:3]==bytes([f.m.read(f.s['object_gen_lo']+oid),f.m.read(f.s['object_gen_hi']+oid)])
 assert token[3:]==f.read(f.s['se_object_epoch'],2)==f.read(f.s['se_reu_epoch'],2)
 h=f.m.read(f.s['object_extents']+oid*16);bank=f.m.read(f.s['se_reu_map']+h)
 assert h and bank and f.m.read(f.s['se_reu_logical_owner']+h)==f.m.read(f.s['se_reu_physical_owner']+bank)==0x53
 lo=bank*65536;roots=[]
 for at in(0,128):
  r=reu[lo+at:lo+at+128]
  if r[:6]==b'BCA1\1\1'and binascii.crc_hqx(r[:5]+r[6:119]+r[121:],65535)==int.from_bytes(r[119:121],'little'):roots.append((at,r))
 assert roots;at,r=max(roots,key=lambda p:int.from_bytes(p[1][18:22],'little'));return lo,at,r


def document(language,mixed=False):
 text=('Mixed **bold** and @@native@@ prose.\r'if mixed else'Intro\r')+':::'+language+'\r'+('10 PRINT "Hi":REM 'if language=='basic'else'label lda #42 ; ')+'x'*980+'\r:::\rTail.'
 return geos.native_text(text)


def force(f):
 f.put('se_r_valid',0,1);f.m.load(f.s['se_gc_valid'],bytes(3))
 f.m.write(0xcf90,0);f.m.write(0xcfe8,0);f.put('se_gc_width',0,1)


def fault_matrix(out,g,f):
 """Yield-boundary faults, real checked writes, and actual queued STOP."""
 data=document('basic');f.source(data);f.typed(geos.native_text('syntax markdown'));f.command(99);f.render()
 f.typed(geos.native_text('syntax full'));f.render();fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
 records=[]
 def clean():
  assert not any(f.get(n,1)for n in('se_e_error','se_f_owner','se_e_job','se_doc_read_locks','se_fs_owned','se_e_draw_busy'))
  assert not f.get('se_bc_flags',1)&8 and f.read(0xc600,1024)==f.shim and f.merged()==data
 def check_pixels():
  bits,attrs,_=plain.expected(f,data,fonts,3);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
 def advance(predicate):
  for _ in range(10000):
   if predicate():return
   assert f.get('se_e_job',1)==11,('fault boundary closed',f.get('se_e_error',1))
   f.call('se_editor_service')
  raise AssertionError('fault boundary did not converge')
 def begin(phase):
  force(f);f.call('se_editor_render')
  advance(lambda:f.m.read(0x9135)==45 and f.m.read(0x9096)==phase)
 def recover():
  if f.get('se_e_error',1):f.key(3)
  force(f);f.render();check_pixels();clean()
 def passed(tag):
  records.append(tag);print('WARM_FAULT_PASS',tag,flush=True)
 for phase in(1,2,3):
  begin(phase);canon=f.canonical();q=g.queue();reu=g.reu();f.queued(3);f.call('se_editor_service')
  assert not f.get('se_e_job',1)and not f.get('se_f_owner',1)and not f.get('se_doc_read_locks',1)
  afterq=g.queue();expectedq=bytearray(q[0]);expectedq[13]&=~8
  assert g.reu()==reu,('STOP',phase,'whole16MiB')
  assert f.canonical()==canon,('STOP',phase,'canonical')
  assert afterq==(bytes(expectedq),q[1]),('STOP',phase,'only owned ACTIVE cleared',q[0].hex(),afterq[0].hex())
  recover();passed('queuedSTOP-phase'+str(phase))
 # Keep a genuine independently acquired read lease after canceling ours.
 assert not f.call('se_doc_read_acquire').p&1
 begin(3);assert f.get('se_doc_read_locks',1)==2
 reu=g.reu();f.queued(3);f.call('se_editor_service')
 assert f.get('se_doc_read_locks',1)==1 and not f.get('se_fs_owned',1)and g.reu()==reu
 assert not f.call('se_doc_read_release').p&1
 recover();passed('STOP-preserves-foreign-counted-lease')
 # A stale saved epoch is not authority to release unrelated live leases.
 begin(3);at=0x8d00+173+27;old=f.m.read(at);reu=g.reu()
 f.m.write(at,old^1);f.put('se_doc_read_locks',7,1);f.queued(3);f.call('se_editor_service')
 assert f.get('se_doc_read_locks',1)==7 and not f.get('se_fs_owned',1)and g.reu()==reu
 f.put('se_doc_read_locks',0,1);recover();passed('stale-reader-epoch-STOP-preserves-seven-foreign-leases')
 for id_,slot,phase in((45,1,2),(36,0,2),(37,0,3),(14,0,1)):
  begin(phase);canon=f.canonical();reu=g.reu();catalog=f.catalog()
  index=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==id_ and f.m.read(f.s['image_slot']+i)&1==slot)
  at=f.s['se_overlay_ids']+index;old=f.m.read(at);f.m.write(at,255);f.m.write(f.s['se_overlay_active']+slot,0)
  f.call('se_editor_service')
  f.m.write(at,old);f.m.write(f.s['se_overlay_active']+slot,0)
  assert f.canonical()==canon and f.catalog()==catalog and g.reu()==reu
  if f.get('se_e_job',1):f.settle(error=f.get('se_e_error',1))
  recover();passed('missing-'+str(id_)+'-'+str(slot))
 for name in('se_bc_ticket','se_bc_incarnation','se_r_revision','se_doc_generation'):
  begin(2);at=f.s[name];old=f.m.read(at);canon=f.canonical();reu=g.reu()
  f.m.write(at,old^1);f.call('se_editor_service');f.m.write(at,old)
  assert g.reu()==reu and f.canonical()==canon
  assert f.m.read(0x9135)==25 and f.m.read(0x9136)==3 and not f.get('se_doc_read_locks',1)
  f.settle();recover();passed('stale-'+name)
 # A valid typed capability with a foreign physical owner cannot DMA.
 begin(2);token=f.read(f.s['se_bc_arena'],5);logical=f.m.read(f.s['object_extents']+token[0]*16)
 bank=f.m.read(f.s['se_reu_map']+logical);at=f.s['se_reu_physical_owner']+bank;old=f.m.read(at);reu=g.reu()
 f.m.write(at,0x77);f.call('se_editor_service');f.m.write(at,old)
 assert g.reu()==reu and not f.get('se_doc_read_locks',1)
 f.settle();recover();passed('foreign-arena-owner-no-DMA')
 # Immutable actual parent context changes refuse rather than reseeding it.
 begin(3);at=0x8b44;old=f.m.read(at);canon=f.canonical();reu=g.reu()
 f.m.write(at,old^1);f.call('se_editor_service');f.m.write(at,old)
 assert not f.get('se_e_job',1)and f.get('se_e_error',1)==0xb1 and g.reu()==reu and f.canonical()==canon
 recover();passed('changed-GSEM-count')
 # Source packet bytes are compared against actual R14 READ before lookup.
 begin(1);at=0x8200;old=f.m.read(at);reu=g.reu();f.m.write(at,old^1);f.call('se_editor_service');f.m.write(at,old)
 assert g.reu()==reu and f.m.read(0x9135)==25 and not f.get('se_doc_read_locks',1)
 f.settle();recover();passed('changed-parent-source-packet')
 # Authenticated page CRC still runs. Use a real checked owner53 write
 # before that CRC, then restore only after the gateway has refused it.
 begin(2);before=g.reu();lo,_,root=arena(f,before);offset=root[104]*4096+64+3;old=before[lo+offset]
 def write(offset,value):
  f.m.load(f.s['se_object_id'],f.read(f.s['se_bc_arena'],5));f.put('se_object_offset',offset)
  f.put('se_object_length',1,2);f.put('se_object_c64',0x8f3f,2);f.m.write(0x8f3f,value)
  assert not f.call('se_object_copy',0).p&1
 write(offset,old^1)
 advance(lambda:f.m.read(0x9135)==25 and f.m.read(0x9136)==3)
 assert not f.get('se_doc_read_locks',1)and not f.get('se_bc_flags',1)&8
 write(offset,old);f.settle();recover();passed('checked-owner53-write-CR-CRC-refuses')
 # Actual shared owner check is before all private phase accesses.
 for id_,slot in((45,1),(36,0),(37,0)):
  for owner in(0,1,2,3,5,255):
   f.put('se_f_owner',owner,1);phase=f.read(0x8b40,0x640);reu=g.reu();pixels=f.read(0x4000,1000)+f.read(0x6000,8000)
   for op in(0,1,2):
    f.put('se_overlay_frame',op,1);r,n=f.fast_call(f.s['se_overlay_call'],a=id_,x=slot);f.total_instructions+=n
    assert r.p&1 and r.a==0xb2 and f.read(0x8b40,0x640)==phase and g.reu()==reu
    assert f.read(0x4000,1000)+f.read(0x6000,8000)==pixels
 f.put('se_f_owner',0,1);passed('54-foreign-owner-op-phase-opaque')
 f.put('se_f_owner',4,1);old=f.get('se_bc_flags',1);f.put('se_bc_flags',9,1)
 phase=f.read(0x8b40,0x640);reu=g.reu();f.put('se_overlay_frame',0,1)
 r,n=f.fast_call(f.s['se_overlay_call'],a=45,x=1);f.total_instructions+=n
 assert r.p&1 and r.a==0xb2 and f.get('se_bc_flags',1)==9 and f.read(0x8b40,0x640)==phase and g.reu()==reu
 f.put('se_bc_flags',old,1);f.put('se_f_owner',0,1);passed('competing-ACTIVE-BEGIN-phase-opaque')
 # Actual presets retain their independent rendering and never enter these
 # three capsules. Short Full code likewise keeps the unchanged C25 path.
 for preset,source,caps in [('plain',data,0),('markdown',data,1),
                           ('full',geos.native_text('Intro\r:::basic\r10 PRINT "Hi"\r:::\rTail.'),3)]:
  f.source(source);f.typed(geos.native_text('syntax '+preset));f.lex_services=[];f.command(99);f.render()
  assert not f.lex_services and not f.get('se_bc_flags',1)&128
  # Markdown's initial actual semantic baseline allocation is separate from
  # this read-only forced repaint, just as it is in the positive A/B cases.
  f.lex_services=[];before=g.reu();canon=f.canonical();queue=g.queue();force(f);f.render()
  bits,attrs,_=plain.expected(f,source,fonts,caps)
  assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
  assert not f.lex_services and not f.get('se_bc_flags',1)&128
  assert f.canonical()==canon and g.queue()==queue and f.merged()==source
  # Rendering may initialize/update its actual FE cache, no other REU bank.
  after=g.reu();_,bank=f.raw_cache();a=bank*65536;wanted=bytearray(before);wanted[a:a+65536]=after[a:a+65536]
  assert after==wanted and f.read(0xc600,1024)==f.shim
  passed('actual-'+preset+('-short'if preset=='full'else'')+'-bypass')
 (out/'fault-groups.json').write_text(json.dumps(records,indent=2)+'\n');return records


def run(out,base,smoke=False,faults_only=False,positive_only=False):
 out.mkdir(parents=True);rows=[];budgets={};originals={};fixtures=[];held={}
 # All three private profiles derive from the same immutable source/report.
 for label,batch,fused in([('fused4',4,True)]if faults_only else[('control',0,False),('batch4',4,False),('fused4',4,True)]):
  images,labels,budget=builder.build(out/label/'leaf',base,batch,fused);budgets[label]=budget
  g=ob.Gate(out/label/'gate',base);f=g.f;fixtures.append((label,g,f,labels));originals[label]=f.assets.copy()
  f.assets.update(images)
  actual=f.call;f.lex_services=[]
  def observed(name,a=0,f=f,actual=actual):
   request=f.m.read(0x9135)if name=='se_editor_service'and f.get('se_e_job',1)==11 else 0
   phase=f.m.read(0x9096);before=f.total_instructions;r=actual(name,a)
   if request==45:f.lex_services.append(dict(phase=phase,instructions=f.total_instructions-before))
   return r
  f.call=observed
 try:
  for language,mixed in([]if faults_only else[('basic',False)]if smoke else[('basic',False),('asm',False),('basic',True),('asm',True)]):
   data=document(language,mixed);expected_digest=None;expected_derived={}
   for label,g,f,labels in fixtures:
    f.source(data);f.typed(geos.native_text('syntax markdown'));f.command(99);f.render()
    before=g.reu();lo,selected,root=arena(f,before);assert root[31]==1
    fonts={n:(g.frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
    for phase in('first','warm'):
     canonical=f.canonical();queue=g.queue();catalog=f.catalog();start=f.total_instructions;loads=f.get('se_overlay_loads',2);f.lex_services=[]
     if phase=='first':f.typed(geos.native_text('syntax full'))
     else:
      f.put('se_r_valid',0,1);f.m.load(f.s['se_gc_valid'],bytes(3));f.m.write(0xcf90,0);f.m.write(0xcfe8,0);f.put('se_gc_width',0,1)
     f.render();cost=f.total_instructions-start
     bits,attrs,model=plain.expected(f,data,fonts,3)
     assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(label,language,mixed,phase,'independent pixels')
     digest=hashlib.sha256(bits+attrs).hexdigest()
     if expected_digest is None:expected_digest=digest
     assert digest==expected_digest
     assert f.canonical()==canonical,(label,language,phase,'canonical')
     current_queue=g.queue()
     assert current_queue[0][:13]+current_queue[0][14:]==queue[0][:13]+queue[0][14:]and current_queue[1]==queue[1],(label,language,phase,'queue/ticket/incarnation')
     assert current_queue[0][13]==(queue[0][13]|128)&~32,(label,language,phase,'only actual lexical-attempt/public paint-proof transition')
     assert f.catalog()==catalog and f.merged()==data and f.read(0xc600,1024)==f.shim,(label,language,phase,'catalog/source/shim')
     assert not any(f.get(n,1)for n in('se_e_error','se_f_owner','se_e_job','se_doc_read_locks','se_fs_owned','se_e_draw_busy'))
     assert not f.get('se_bc_flags',1)&8
     after=g.reu();where,chosen,now=arena(f,after);assert where==lo and now[31]==5 and now[98]==1
     wanted=bytearray(before)
     if phase=='first':
      assert chosen!=selected and after[lo+selected:lo+selected+128]==before[lo+selected:lo+selected+128]
      pages=[]
      for p in range(1,16):
       at=lo+256+p*8
       if before[at:at+8]!=after[at:at+8]:
        assert before[at:at+8]==bytes(8);pages.append(p);wanted[at:at+8]=after[at:at+8]
        a=lo+p*4096;wanted[a:a+4096]=after[a:a+4096]
      assert len(pages)==2;wanted[lo+chosen:lo+chosen+128]=after[lo+chosen:lo+chosen+128]
     else:assert after[lo:lo+65536]==before[lo:lo+65536]
     _,bank=f.raw_cache();a=bank*65536;wanted[a:a+65536]=after[a:a+65536]
     assert after==wanted,(label,language,mixed,phase,'whole16MiB outside exactCOW+FE')
     derived=(after[lo:lo+65536],after[a:a+65536])
     if phase not in expected_derived:expected_derived[phase]=derived
     assert derived==expected_derived[phase],(label,language,mixed,phase,'complete actual arena and FE bytes equal control, including maps/anchors')
     service=list(f.lex_services);r=dict(variant=label,language=language,mixed=mixed,phase=phase,instructions=cost,
      loads=(f.get('se_overlay_loads',2)-loads)&65535,C45_calls=len(service),C45_peak=max(x['instructions']for x in service),
      C45_by_phase={str(p):dict(calls=sum(x['phase']==p for x in service),instructions=sum(x['instructions']for x in service if x['phase']==p))for p in set(x['phase']for x in service)},pixels_sha256=digest,
      arena_sha256=hashlib.sha256(derived[0]).hexdigest(),FE_sha256=hashlib.sha256(derived[1]).hexdigest())
     rows.append(r);print('WARM_FRAME',r,flush=True)
     if label=='fused4':geos.png(bits,attrs,out/(language+('-mixed'if mixed else'')+'-'+phase+'.png'))
     before=after
  faults=[]
  if not positive_only:
   _,g,f,_=fixtures[-1];faults=fault_matrix(out,g,f)
  result=dict(status='PASS',scope=__doc__,fixture=str(base),budgets=budgets,frames=rows,fault_groups=faults,
   safety='Every helper entry retains its full source/arena guard. Only immediate duplicated internal arena guards are hoisted; no cross-yield memo or new flag.',new_BSS=0,new_ZP=0,new_assets=0)
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS_LEXICAL_WARM',out,flush=True);return result
 except BaseException as e:
  # Preserve exact failing RAM and compact REU identity, avoid repeated16MiB files.
  for label,g,f,_ in fixtures:
   (out/(label+'-failure-ram.bin')).write_bytes(f.read(0,65536))
  (out/'failure.json').write_text(json.dumps(dict(error=repr(e),frames=rows),indent=2)+'\n');raise
 finally:
  for _,_,f,_ in fixtures:f.close()


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--smoke',action='store_true');p.add_argument('--faults-only',action='store_true');p.add_argument('--positive-only',action='store_true');a=p.parse_args()
 out=ROOT/'build/cache-lexical-warm'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.smoke,a.faults_only,a.positive_only)
