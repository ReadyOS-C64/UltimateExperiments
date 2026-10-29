"""Private body-cache exact source/lease/partial-publication refusal gates."""
from pathlib import Path
from datetime import datetime,timezone
import ctypes as C,inspect,json,sys,hashlib,binascii
import test_geos_body_style_cache as candidate
import test_geos_inline_bridge as bridge
import test_geos_semantic_editor as semantic
import test_geos_fold_editor as fold
import test_geos_inline_query_profile as profile
ROOT=candidate.ROOT;D=ROOT/'src/render/geos/body-style-cache-candidate'

def run(out,base=candidate.BASE):
 fixture=candidate.builder().install(out,base);gate=out/'bridge';gate.mkdir()
 text=(D/'bridge-regression.py').read_text();ns=dict(bridge.__dict__);exec(text,ns);regression=ns['run'](gate,fixture)
 isolated=out/'helper';isolated.mkdir();frozen,identity=semantic.geos.freeze(isolated,fixture)
 semantic.geos.grid.editor_fixture.ROOT=semantic.geos.grid.cpu_editor.ROOT=frozen;names=identity['names'];semantic.geos.grid.editor_fixture.NAMES=semantic.geos.grid.cpu_editor.NAMES=names
 dll=profile.runner(isolated);f=fold.Fixture(isolated,frozen,dll,True);faults=[]
 DATA=semantic.geos.native_text('**'+('Wim. '*170)+'end**\rTail.')
 fonts={n:(frozen/'fonts'/n).read_bytes()for n in semantic.geos.GEOS_FONTS+('native8.bin',)}
 def whole():return f.reu()
 def until(predicate):
  for i in range(20000):
   if predicate():return
   r=f.call('se_editor_service');assert not r.p&1,(hex(r.a),f.debug())
  raise AssertionError(('helper phase not reached',f.debug()))
 def active():return f.get('se_f_owner',1)==4 and f.m.read(0x9135)==20 and f.m.read(0x9136)==1 and f.m.read(0x912C)==1 and f.m.read(0x912D)==1 and not f.m.read(0x8BE7)
 def start():
  f.source(DATA);f.command(99)
  for n in ['se_r_valid','se_gc_valid','se_gc_width']:f.put(n,0,1)
  f.m.write(0xCF90,0);f.m.write(0xCFE8,0)
  f.call('se_editor_render');until(lambda:active() and f.m.read(0x458C)==1 and f.get('se_doc_read_locks',1)==1)
 def op(n):
  f.put('se_overlay_frame',n,1);return f.fast_call(f.s['se_overlay_call'],a=24,x=0)[0]
 def record():
  bank=f.m.read(f.s['se_reu_map']+f.get('se_gc_handle',1));return whole()[bank*65536+0xFC00:bank*65536+0xFDA0]
 def write_record(raw):
  assert len(raw)==416;f.call('se_doc_invalidate');f.m.load(0x8600,raw)
  for n,v,k in [('se_reu_c64',0x8600,2),('se_reu_logical',f.get('se_gc_handle',1),1),('se_reu_offset',0xFC00,2),('se_reu_length',416,2)]:f.put(n,v,k)
  assert not f.call('se_reu_copy',0).p&1
 def crc(raw):return binascii.crc_hqx(raw[1:80]+raw[82:],0xffff)
 def pixel(tag):
  before=f.canonical();f.audit_begin();reu=whole();f.settle();f.audit_end(reu,tag)
  want=semantic.expected(f,DATA,fonts);assert f.read(0x6000,8000)==want[0] and f.read(0x4000,1000)==want[1]
  assert f.canonical()==before and f.merged()==DATA and f.read(0xC600,1024)==f.shim
  assert not any(f.get(n,1)for n in('se_f_owner','se_doc_read_locks','se_fs_owned','se_e_job'))
 def stop():
  f.queued(3);f.call('se_editor_service');assert not any(f.get(n,1)for n in('se_f_owner','se_fs_owned','se_e_job','se_e_draw_busy'))
 try:
  start();original=record();assert original[0:4]==bytes([1,1,0xBC,160]);assert int.from_bytes(original[80:82],'little')==crc(original)
  assert not f.call('se_doc_read_acquire').p&1
  before=whole();r=op(3);assert not r.p&1 and r.a==0 and whole()==before
  assert f.get('se_doc_read_locks',1)==2;stop();assert f.get('se_doc_read_locks',1)==1;assert not f.call('se_doc_read_release').p&1
  faults.append('actualhelperhit exactCRC/currentkey readonly16MiB; STOP preservesforeignlease')
  for offset,value,label,recompute in [(0,0,'unpublished',False),(1,2,'version',False),(2,0,'magic',False),(3,161,'count161',False),(4,255,'windowstart',False),(7,0,'sourcekey',False),(66,255,'context',False),(76,0,'FElogical',False),(77,0,'FEphysical',False),(78,0,'FEepoch',False),(80,0,'CRC',False),(82,0,'C26producer',False),(96,4,'invalidstyle',True),(256,14,'invalidrole',True)]:
   start();raw=bytearray(record());raw[offset]=value if raw[offset]!=value else value^1
   if recompute:raw[80:82]=crc(raw).to_bytes(2,'little')
   write_record(raw);before=whole();outputs=f.read(0x8300,160)+f.read(0x8F36,160);r=op(3)
   assert not r.p&1 and r.a==2,(label,r.a,r.p)
   assert whole()==before and f.read(0x8300,160)+f.read(0x8F36,160)==outputs,(label,'failedlookup changedoutputs/REU')
   f.m.write(0x458C,0);pixel('refetch-'+label);faults.append('corrupt '+label+' miss/refetch exactpixels')
  start();canonical=f.canonical();before=whole();revision=f.get('se_r_revision',4);f.put('se_r_revision',revision+1,4);r=op(3)
  assert r.p&1 and r.a==0xB1 and whole()==before and f.canonical()==canonical
  stop();assert not f.get('se_doc_read_locks',1);faults.append('live revisionchange rejects before cache DMA/output')
  start()
  for owner in(0,1,2,3,5,255):
   f.put('se_f_owner',owner,1);phase=f.read(0x8B40,0x640);ledger=f.read(0x4400,1024);reu=whole()
   for operation in(3,4,5,6):
    r=op(operation);assert r.p&1 and r.a==0xB2 and f.read(0x8B40,0x640)==phase and f.read(0x4400,1024)==ledger and whole()==reu
  f.put('se_f_owner',4,1);stop();faults.append('24 foreignowner calls opaque wholephase/ledger/16MiB')
  start();r=op(6);assert not r.p&1 and record()[0]==0;f.m.write(0x458C,0);pixel('cancel-revoke');faults.append('explicitrevoke VALID0 then exactcheckedrefetch')
  # Pause only this private CPU invocation at the real checked bulk-DMA entry.
  # Fault injection is explicit; it is not concurrent foreground execution.
  for fault in ('revision-before-bulk','FEowner-before-bulk'):
   start();before=whole();canonical=f.canonical();handle=f.get('se_gc_handle',1)
   f.put('se_overlay_frame',4,1)
   for n,v in [('pc',f.s['se_overlay_call']),('sp',0xFD),('p',0x24),('a',24),('x',0),('y',0)]:getattr(f.m.lib,'zeropage_peddle_set_'+n)(f.m.handle,v)
   f.m.write(0x1FE,0xFE);f.m.write(0x1FF,2);seen=False;steps=0
   while f.m.regs().pc!=0x02FF:
    r=f.m.regs()
    if not seen and r.pc==f.s['se_reu_copy'] and r.a==0 and f.get('se_reu_offset',2)==0xFC00 and f.get('se_reu_length',2)==416:
     assert record()[0]==0,'old VALID was not revoked before bulkwrite'
     if fault.startswith('revision'):f.put('se_r_revision',f.get('se_r_revision',4)+1,4)
     else:f.m.write(f.s['se_reu_logical_owner']+handle,0xA5)
     seen=True
    f.m.lib.zeropage_peddle_step_instruction(f.m.handle);steps+=1;assert steps<200000
   assert seen and f.m.regs().p&1 and record()[0]==0,(fault,f.m.regs())
   if fault.startswith('FEowner'):f.m.write(f.s['se_reu_logical_owner']+handle,0xFE)
   after=whole();bank=f.m.read(f.s['se_reu_map']+handle);a=bank*65536+0xFC00;b=a+416
   assert before[:a]==after[:a] and before[b:]==after[b:] and f.canonical()==canonical and f.read(0xC600,1024)==f.shim
   stop();assert not f.get('se_doc_read_locks',1);faults.append(fault+' leaves unpublished0 and no foreignREU/sourcewrites')
  # A missing/old helper is a checked dependency failure, never a stale hit.
  for variant in ('missing','old'):
   start();assert not op(6).p&1;f.m.write(0x458C,0)
   index=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==24 and (f.m.read(f.s['image_slot']+i)&1)==0)
   if variant=='missing':
    f.m.write(f.s['se_overlay_ids']+index,0);f.m.write(f.s['se_overlay_active'],0)
   else:
    image=(base/'build/overlays/geosfold.seo').read_bytes();f.m.write(f.s['se_overlay_ids']+index,0);f.m.write(f.s['se_overlay_active'],0);f.m.load(f.s['se_overlay_header'],image[:36]);f.m.load(0x5000,image[36:]);r=f.call('se_overlay_import');assert not r.p&1,('oldhelperimport',r.a)
   canonical=f.canonical();r=f.call('se_editor_service')
   assert r.p&1 and f.get('se_e_error',1)==(0x17 if variant=='missing' else 0x90),(variant,r.a,f.debug(),f.get('se_e_error',1))
   assert f.canonical()==canonical and not any(f.get(n,1)for n in('se_f_owner','se_fs_owned','se_doc_read_locks','se_e_job'))
   if variant=='missing':f.m.write(f.s['se_overlay_ids']+index,24)
   else:
    image=f.assets['geosfold'];index=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==24 and(f.m.read(f.s['image_slot']+i)&1)==0);f.m.write(f.s['se_overlay_ids']+index,0);f.m.write(f.s['se_overlay_active'],0);f.m.load(f.s['se_overlay_header'],image[:36]);f.m.load(0x5000,image[36:]);r=f.call('se_overlay_import');assert not r.p&1,('restorehelperimport',r.a)
   f.put('se_e_error',0,1);f.render();want=semantic.expected(f,DATA,fonts);assert f.read(0x6000,8000)==want[0]and f.read(0x4000,1000)==want[1]
   faults.append(variant+' R24 dependency rejects then recovers exactpixels/source')
  result=dict(status='passed',bridge=regression,faults=faults,identity=identity,reservation={'FE':[0xFC00,0xFE00],'live_record':[0xFC00,0xFDA0],'CPU_docleaf':[0x8600,0x87A0],'work':[0x45A0,0x45A8]},scope='ActualR24 helper/currentR14 leases/C20 sourcebody. Corruption injection is explicit checkedFEwrite fixture. Full independentpixels/source/history/catalog/shim+typed16MiB guards retained. No native/canonical/sharedbuild.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':
 out=ROOT/'build/geos-body-style-cache-faults'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out);print('passed',len(r['faults']),flush=True)
