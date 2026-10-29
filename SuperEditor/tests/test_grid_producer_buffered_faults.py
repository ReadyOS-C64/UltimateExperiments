"""Actualowner2 RAM producer failures cannot finalize a partial record after repair."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,binascii
import test_geos_fold_editor as fold,test_grid_modes as grid
import font_fixture
ROOT=Path(__file__).resolve().parents[1]
def run(out,base):
 ident=json.load(open(base/'freeze.json'));grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=base;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=ident['names'];dll=fold.retention.runner(out);f=fold.Fixture(out,base,dll,True);cases=[]
 data=grid.native_text('Alpha '+('word '*300)+'*'+('word '*200)+'\rTail.')
 def live():
  f.source(data);f.command(98);f.position(22);f.render();f.finish_style();f.key(32);f.begin_style()
  for _ in range(10000):
   if f.get('se_f_owner',1)==2 and f.get('st_phase',1)==4 and f.m.read(0x89c3)==1 and f.m.read(0x89c4)==165:break
   f.tick()
  else:raise AssertionError(('missing actual livejob',f.debug()))
  h=f.get('se_gc_handle',1);bank=f.m.read(f.s['se_reu_map']+h);return h,bank
 def end(tag,canonical,reu):
  assert f.canonical()==canonical and f.reu()==reu and f.read(0xc600,1024)==f.shim,(tag,'source/whole16MiB beforefinalization')
  assert f.m.read(0x89c4)==0 and f.m.read(0x89c3)==128,(tag,'stickyjobpoison')
  f.finish_style();h=f.get('se_gc_handle',1);bank=f.m.read(f.s['se_reu_map']+h);q=f.reu()[bank*65536+0x1600:bank*65536+0x1680];assert q[:4]==b'SP\2\0' and binascii.crc_hqx(q[:126],65535)==int.from_bytes(q[126:],'little'),(tag,'BEGINrevocationremains')
  want,attrs=grid.expected(f,f.merged())[0];assert f.read(0x6000,8000)==want and f.read(0x4000,1000)==attrs and f.canonical()==canonical,(tag,'fullstyleworksdespiteoptionalrefusal');cases.append(dict(tag=tag))
 try:
  for address,count in [(0x8a00,128),(0x89c0,128),(0x89ff,128),(0x8a7f,2),(0x8880,128),(0x8d6e,0),(0x8d6e,129)]:
   h,bank=live();f.put('se_fs_buffer',address,2);f.put('se_fs_count',count,1);canonical=f.canonical();reu=f.reu();working=f.read(0x8a00,128);f.put('se_overlay_frame',2,1);r,n=f.fast_call(f.s['se_overlay_call'],a=14,x=0);assert r.p&1 and r.a==0xB0 and f.read(0x8a00,128)==working,(hex(address),count,r.a,r.p);end('READtarget-'+hex(address)+'-'+str(count),canonical,reu)
  for name,width in [('se_gc_epoch',2)]:
   h,bank=live();old=f.get(name,width);f.put(name,old^1,width);canonical=f.canonical();reu=f.reu();f.put('se_overlay_frame',2,1);r,n=f.fast_call(f.s['se_overlay_call'],a=14,x=0);f.put(name,old,width)
   assert (r.p&1)if name=='se_reu_epoch'else(not(r.p&1)and r.a==0);end(name+'-repairdoesnotrevive',canonical,reu)
  for name,width in [('se_st_generation',2),('se_st_rows',1),('se_st_descriptor',1),('se_st_key',1),('se_doc_epoch',2)]:
   h,bank=live();old=f.get(name,width);f.put(name,old^1,width);canonical_before=f.canonical();reu=f.reu();f.put('se_overlay_frame',5,1);r,n=f.fast_call(f.s['se_overlay_call'],a=14,x=0);assert r.p&1 and r.a==2 and f.reu()==reu;f.put(name,old,width);canonical=f.canonical();end(name+'-failedFINISHrepair',canonical,reu)
  # The revoked FE workingcopy is not authority. Corrupting it midjob must
  # be repaired from the genuine RAM parser result, not fetched/re-approved.
  h,bank=live();canonical=f.canonical();q=bytes((i*73+19)&255 for i in range(128));f.m.load(0x8b00,q);f.put('se_reu_logical',h,1);f.put('se_reu_offset',0x1600,2);f.put('se_reu_c64',0x8b00,2);f.put('se_reu_length',128,2);assert not f.call('se_reu_copy',0).p&1;before=f.reu();f.finish_style();after=f.reu();start=bank*65536;allowed=bytearray(before)
  for lo,hi in [(0,22*240),(0x1500,0x1680)]:allowed[start+lo:start+hi]=after[start+lo:start+hi]
  assert bytes(allowed)==after and f.canonical()==canonical;record=after[start+0x1600:start+0x1680];assert record[:4]==b'SP\2\xa5' and record[111:114]==b'\0\0\0' and binascii.crc_hqx(record[:126],65535)==int.from_bytes(record[126:],'little');want,attrs=grid.expected(f,f.merged())[0];assert f.read(0x6000,8000)==want and f.read(0x4000,1000)==attrs;cases.append(dict(tag='corrupt-revokedFE-repaired-from-actualRAMparse'))
  # A globalproviderepoch fault is refused by residentoverlayadmission before
  # R14executes. Exercise actualC14scheduler cleanup instead of pretending its
  # private READerror hook ran; revokedFE plus ownerrelease is the barrier.
  # Existing fs_end deliberately does not decrement a lease after provider
  # epoch replacement. Do not fake rollback as a usable continuation.
  h,bank=live();canonical=f.canonical();old=f.get('se_reu_epoch',2);f.put('se_reu_epoch',old^1,2);f.tick();f.put('se_reu_epoch',old,2);assert f.get('se_f_owner',1)==0 and f.get('se_fs_owned',1)==0 and f.get('se_doc_read_locks',1)==1 and f.canonical()==canonical;assert f.reu()[bank*65536+0x1603]==0;cases.append(dict(tag='provider-epoch-realadmission-no-foreignlease-release',old_context_requires_provider_reinit=True))
  # Real cancellation returns the lease/owner; the revoked backing record is
  # never silently approved from the abandonedRAMjob. A future BEGIN rebuilds.
  h,bank=live();canonical=f.canonical();f.key(3);assert f.get('se_f_owner',1)==0 and f.get('se_fs_owned',1)==0 and f.get('se_doc_read_locks',1)==0 and f.canonical()==canonical;assert f.reu()[bank*65536+0x1603]==0;cases.append(dict(tag='publicSTOP-leaseandrevocation'))
  result=dict(status='passed',cases=cases,scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure-reu.bin').write_bytes(f.reu());raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();out=ROOT/'build/grid-producer-buffered-faults'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)
