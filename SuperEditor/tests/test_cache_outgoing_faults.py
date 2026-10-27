"""Actual checked C35 output→C21 capture→R19; isolated authority-fault gate."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,json,sys,binascii,shutil,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_semantic_editor as semantic
from cache_job_build import editor_pair_index
geos=semantic.geos
G=0x8B40;PROOF=G+29;CAPTURED=G+182;INCOMING=G+170;P=0x9134

def run(out,base):
 frozen,identity=geos.freeze(out,base);geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out);f=geos.Fixture(out,frozen,dll,True)
 def reu():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(f.m.handle,len(b),b);return b.raw
 def invoke(ident,op):
  f.put('se_overlay_frame',op,1);r,n=f.fast_call(f.s['se_overlay_call'],a=ident,x=0 if ident==19 else 1);return r
 try:
  data=geos.native_text('# Heading\rA **bold** paragraph.\r:::basic\r10 PRINT "Hi"\r:::\rTail.')
  f.source(data);f.command(99);f.render();assert f.get('se_bc_flags',1)&1
  # Actual checked query. Only public operation/caller inputs are set, never
  # parser outputs/source/carry/certificatebytes. Root integration is public15.
  f.put('se_f_owner',4,1);f.m.load(G,bytes(192));r=invoke(35,0);steps=0
  while not r.p&1 and r.a==1:r=invoke(35,1);steps+=1;assert steps<10000
  assert not r.p&1 and r.a==0 and f.m.read(G+24)==0
  f.m.write(P,14);f.m.write(P+3,0);f.m.load(P+5,bytes(3));f.m.write(P+20,0)
  r=invoke(21,1);assert not r.p&1 and r.a==1 and f.m.read(CAPTURED)==2 and f.m.read(G+28)==0
  assert f.m.read(P+1)==20,'C21 must request realC20 onlyaftercertificatepublication'
  token=f.get('se_gc_handle',1);physical=f.m.read(f.s['se_reu_map']+token);assert f.m.read(f.s['se_reu_physical_owner']+physical)==0xFE;base_reu=reu();base_ram=f.read(0,65536)
  (out/'actual-c35-c21-r19-phase.bin').write_bytes(base_ram);(out/'actual-c35-c21-r19-reu.bin').write_bytes(base_reu)
  expected_next=base_ram[INCOMING:INCOMING+3];expected_carry=base_ram[INCOMING+3:INCOMING+9];key=base_reu[physical*65536+4:physical*65536+32]
  def restore():f.m.load(2,base_ram[2:0xD000])
  def snapshot():return f.canonical(),f.read(0xC600,1024),f.get('se_doc_read_locks',1)
  positives=[];faults=[]
  for row in range(22):
   restore();f.m.write(P+3,row);before=reu();canonical,shim,locks=snapshot();r=invoke(19,7);assert not r.p&1 and r.a==0
   after=reu();lo=physical*65536+0x700+row*0x800;record=after[lo:lo+64]
   assert record[:4]==b'C\2\x40\1' and record[4:7]==expected_next and record[7:35]==key and record[35:41]==expected_carry and record[41:44]==base_ram[f.s['se_v_top']:f.s['se_v_top']+3]
   assert int.from_bytes(record[62:64],'little')==binascii.crc_hqx(record[:62],65535)
   assert before[:lo]==after[:lo] and before[lo+64:]==after[lo+64:],'whole16MiB outside onecertificate'
   assert snapshot()==(canonical,shim,locks) and f.m.read(G+28)==0
   positives.append({'row':row,'record':record.hex()})
  # Every failure must notwriteREU. Hostmutations are controlled inputfaults;
  # comparedbefore/after includesfull16MiB pluscanonical/shim/leasepreservation.
  def reject(tag,edits,owner_error=False):
   restore()
   for a,v in edits:f.m.write(a,v)
   before=reu();canonical,shim,locks=snapshot();phase=f.read(G,192)+f.read(0x8D00,576)+f.read(0x9040,86);r=invoke(19,7)
   assert f.read(G,192)+f.read(0x8D00,576)+f.read(0x9040,86)==phase,(tag,'opaque parser/proof/reader phase changed')
   assert (r.p&1 and r.a==0xB2)if owner_error else((r.p&1 and r.a==0x18)if tag=='provider-epoch'else(not r.p&1 and r.a==0)),(tag,r.a,r.p)
   assert reu()==before,(tag,'REUwriteonrefusal');assert snapshot()==(canonical,shim,locks),(tag,'canonical/lease/shim')
   faults.append(tag)
  for i in range(85):reject('proof-byte-'+str(i),[(PROOF+i,base_ram[PROOF+i]^1)])
  for i in range(13):reject('live-auth-'+str(i),[(f.s['se_bc_arena']+i,base_ram[f.s['se_bc_arena']+i]^1)])
  for flags in range(256):
   if flags not in (33,49):reject('flags-'+str(flags),[(f.s['se_bc_flags'],flags)])
  for count in (1,2,3,255):reject('queued-'+str(count),[(f.s['se_bc_count'],count)])
  for owner in (0,1,2,3,5,255):reject('foreign-owner-'+str(owner),[(f.s['se_f_owner'],owner)],True)
  reject('dirtytransaction-preservesoldwitness',[(P+20,2)]);reject('wrong-logical-anchor',[(P+5,1)])
  reject('provider-epoch',[(f.s['se_reu_epoch'],base_ram[f.s['se_reu_epoch']]^1)])
  reject('source-revision',[(f.s['se_r_revision'],base_ram[f.s['se_r_revision']]^1)])
  reject('foreign-FE',[(f.s['se_reu_physical_owner']+physical,7)])
  index=editor_pair_index(1,24)
  assert base_ram[f.s['se_overlay_ids']+index]==24 and base_ram[f.s['image_slot']+index]&1==1
  reject('missing-C24-capability',[(f.s['se_overlay_ids']+index,0)])
  (out/'opcode-result.json').write_text(json.dumps(dict(status='passed',positives=positives,faults=faults,opaque_phase=True),indent=2)+'\n')
  # Internal64-byte serializer differential. Both actualadmittedR19s use
  # exactlythe same actualguardedpage key. Syntheticcarry vectors here test
  # serialization only, not parser semantic meaning. Public15 coversrealcarry.
  from overlays import HEADER
  import re
  fit=ROOT/'build/cache-outgoing-fit/20261026T004107457274Z'
  def labels(tag):return {n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(fit/(tag+'.lbl')).read_text())}
  record_digest=[]
  offsets=[0x600,0x640]+[0x700+i*0x800 for i in range(22)]
  original_fixture=f
  for variant,imagepath in [('control',ROOT/'build/cache-editor-product/20261026T001942640938Z/fixture/build/overlays/rangeio.seo'),('candidate',frozen/'build/overlays/rangeio.seo')]:
   variant_root=out/('factory-'+variant);shutil.copytree(frozen,variant_root)
   image=imagepath.read_bytes();(variant_root/'build/overlays/rangeio.seo').write_bytes(image)
   geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=variant_root
   f=geos.Fixture(out,variant_root,dll,True);f.source(data);f.command(99);f.render();f.put('se_f_owner',4,1)
   f.m.write(CAPTURED,0);f.m.write(G+28,0);rr=invoke(19,7);assert not rr.p&1
   assert f.read(0x8504,28)==key
   digest=__import__('hashlib').sha256();before=reu();canonical,shim,locks=snapshot()
   for off in offsets:
    for value in range(256):
     incoming=bytes([value,0xFE,1,value,(value+1)&255,(value+2)&255,value^0xA5,value^0x5A,255-value])
     f.m.load(INCOMING,incoming);f.m.load(G+30,key);f.m.write(G+188,off&255);f.m.write(G+189,off>>8)
     rr,used=f.fast_call(labels(variant)['gsc_record_write']);assert not rr.p&1 and rr.a==0
     record=f.read(0x9000,64);expected=bytearray(64);expected[:4]=bytes([0x53 if off in(0x600,0x640)else 0x43,2,64,1]);expected[4:7]=incoming[:3];expected[7:35]=key;expected[35:41]=incoming[3:];expected[41:44]=base_ram[f.s['se_v_top']:f.s['se_v_top']+3];expected[62:64]=binascii.crc_hqx(expected[:62],65535).to_bytes(2,'little')
     assert record==expected,(variant,hex(off),value,'serializer')
     target=physical*65536+off;actual=bytes(f.m.lib.zeropage_peddle_read_reu(f.m.handle,target+j)for j in range(64));assert actual==expected,(variant,hex(off),value,'VALIDlastfinal')
     digest.update(record)
   after=reu();cursor=0
   for off in sorted(offsets):
    lo=physical*65536+off;assert after[cursor:lo]==before[cursor:lo],(variant,'REUoutsidefactoryrecord');cursor=lo+64
   assert after[cursor:]==before[cursor:] and snapshot()==(canonical,shim,locks)
   record_digest.append(digest.hexdigest());f.close()
  f=original_fixture
  assert record_digest[0]==record_digest[1]
  result=dict(status='passed',identity=identity,positives=positives,faults=faults,legacy_serializer_cases_each=24*256,legacy_serializer_sha256=record_digest[0],scope='ActualpubliccheckedC35 output andactualC21opcodeSTEP capture/R19 publication. ComponentR19opcode7 authorityfaults+22slotformat; all16MiB exactoutsideone64Brecord onpositive/noREUwritesonrefusal, source/shim/foreignlease preserved. Separatepublic15 provesunseededcallerflow; nofakeparserCP.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,'rows',len(positives),'faults',len(faults),flush=True);return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();out=ROOT/'build/cache-outgoing-faults'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)
