"""Actual public C21 optional-seed recovery; original errors are not cache misses."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_semantic_consumer as c
F=c.F

def run(out,base):
 spec=importlib.util.spec_from_file_location('consumer_build',c.D/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);budget=b.build(out/'link',base)
 frozen,identity=c.geos.freeze(out,base);c.geos.grid.editor_fixture.ROOT=c.geos.grid.cpu_editor.ROOT=frozen;c.geos.grid.editor_fixture.NAMES=c.geos.grid.cpu_editor.NAMES=identity['names'];dll=c.geos.grid.runner(out);f=c.Fixture(out,frozen,dll,True)
 seed=(out/'link/seed/geossema.seo').read_bytes();page=(out/'link/producer/geospage.seo').read_bytes();old=(frozen/'build/overlays/geossema.seo').read_bytes();f.assets['geossema']=seed;f.assets['geospage']=page
 fonts={n:(frozen/'fonts'/n).read_bytes()for n in c.geos.GEOS_FONTS+('native8.bin',)};cases=[];data=b''
 def clean():
  assert not any(f.get(n,1)for n in ['se_e_job','se_f_owner','se_doc_read_locks','se_fs_owned','se_e_error','se_e_draw_busy']),f.debug()
  assert f.read(0xc600,1024)==f.shim
 def setup(old_worker=False):
  nonlocal data
  f.assets['geossema']=old if old_worker else seed
  pre=c.geos.native_text('prefix\r')*300;data=pre+c.geos.native_text('# Heading words.\rFollowing row.\rTail.')
  f.source(data);f.command(99);f.position(len(pre)+5);f.render();clean()
 def edit():
  nonlocal data
  at=f.get('se_hot_caret');data=data[:at]+c.geos.native_text('Q')+data[at:];f.key(c.geos.native_text('Q')[0])
 def exact(tag):
  canonical=f.canonical();catalog=f.catalog();before=f.reu();f.events=[];f.trace=True;f.render();f.trace=False
  bits,attrs,rows=c.exact_pixels(f,data,fonts,tag);assert f.merged()==data and f.canonical()==canonical and f.catalog()==catalog
  c.outside_cache(f,before,tag);clean();c.geos.png(bits,attrs,out/(tag+'.png'));return list(f.events)
 def record(tag,**kw):
  cases.append(dict(tag=tag,**kw));print('PASS',cases[-1],flush=True);(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
 def pending():
  f.events=[];f.trace=True;r=f.call('se_editor_render');assert not r.p&1
  for n in range(20000):
   assert f.get('se_e_job',1)==11,('ended-before-op3',f.debug())
   if f.m.read(0x9135)==24 and f.m.read(0x9136)==3:return n
   f.call('se_editor_service')
  raise AssertionError('op3 not reached')
 def remove(id,slot):
  idx=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==id and f.m.read(f.s['image_slot']+i)&0x7f==slot)
  f.m.write(f.s['se_overlay_ids']+idx,0);f.m.write(f.s['se_overlay_active']+slot,0);return idx
 try:
  # A real checked DMA changes only the disclosed current record's CRC byte.
  # Both current and predecessor must miss, because predecessor authenticates
  # the current V2 record before trusting its own full-key binding.
  setup();edit();cache,bank=f.raw_cache();f.m.write(0x9000,cache[0x63e]^0x80)
  for n,v,w in [('se_reu_logical',f.get('se_gc_handle',1),1),('se_reu_offset',0x63e,2),('se_reu_c64',0x9000,2),('se_reu_length',1,2)]:f.put(n,v,w)
  assert not f.call('se_reu_copy',0).p&1
  events=exact('crc-bad-fallback');tries=[e for e in events if e['op']==3];assert len(tries)==2 and all(e['proof']==0 for e in tries),events
  assert max(e['READS']for e in events)>60,events
  record('crc-bad-fallback',tries=tries,source_READS=max(e['READS']for e in events),scope='Actual checkedDMA CRC fault; real C24 BOF fallback, canonical/full16MiB guards and all pixels/anchors.')
  # A fresh producer can publish trusted records again, not a permanently
  # poisoned cache or a manufactured success with ignored CRC.
  at=f.get('se_hot_caret');data=data[:at-1]+data[at:];f.key(0x14);events=exact('crc-repaired-next-BACK');assert any(e['op']==3 and e['proof']==2 for e in events)
  record('crc-repaired-next-BACK',source_READS=max(e['READS']for e in events))

  # New C21 with the actual old worker must never use unsupported op3 nor a
  # poisoned new CAPTURED field which that old worker does not initialize.
  setup(True);cache,bank=f.raw_cache();pair=cache[0x600:0x680];f.m.write(F+182,1);f.m.load(F+170,(f.get('se_v_top')).to_bytes(3,'little')+bytes([3,1,16,9,9,9]));edit();events=exact('old-C24-stale-phase');after,_=f.raw_cache();assert not any(e['op']==3 for e in events)and after[0x600:0x680]==pair
  record('old-C24-stale-phase',source_READS=max(e['READS']for e in events),scope='Exact old2781B sealed worker; unsupported op3 and metadata producer both skipped despite poisoned CAPTURED/incoming fields.')

  setup();edit();canonical=f.canonical();catalog=f.catalog();before=f.reu();pixels=f.read(0x6000,8000);steps=pending();f.queued(3);f.call('se_editor_service');f.trace=False
  assert f.canonical()==canonical and f.catalog()==catalog and f.read(0x6000,8000)==pixels;clean();c.outside_cache(f,before,'STOP-op3')
  exact('STOP-op3-repaint');record('STOP-op3-repaint',steps_to_op3=steps,scope='Actual queuedIRQ STOP before op3 service; owned lease/phase cleanup, last complete pixels and canonical pending edit retained; real next render recovers.')

  for id,slot in [(24,1),(14,0)]:
   setup();edit();canonical=f.canonical();catalog=f.catalog();before=f.reu();pixels=f.read(0x6000,8000);steps=pending();idx=remove(id,slot);f.call('se_editor_service');f.trace=False
   assert f.get('se_e_error',1)==0x17,('original-missing-error',id,f.debug())
   assert not any(f.get(n,1)for n in ['se_e_job','se_f_owner','se_fs_owned','se_doc_read_locks','se_e_draw_busy'])and f.canonical()==canonical and f.read(0x6000,8000)==pixels
   c.outside_cache(f,before,'missing-'+str(id));f.m.write(f.s['se_overlay_ids']+idx,id)
   # Harmless actual input acknowledges original error, no host error clearing.
   f.key(0x8b);f.key(0x8b);exact('missing-'+str(id)+'-recovered');assert f.catalog()==catalog
   record('missing-'+str(id)+'-recovered',error=0x17,steps_to_op3=steps)

  # A counted foreign source lease survives both optional seed and normal
  # parse/render; drain actual public service without fixture's zero-lock
  # settle precondition, then release only the separately acquired lease.
  setup();edit();assert not f.call('se_doc_read_acquire').p&1;canonical=f.canonical();before=f.reu();catalog=f.catalog();seq=f.get('se_e_draw_sequence',2);f.events=[];f.trace=True
  for outer in range(16):
   r=f.call('se_editor_render');assert not r.p&1
   for step in range(20000):
    if not f.get('se_e_job',1):break
    f.call('se_editor_service')
   else:raise AssertionError('foreign-lease service budget')
   if f.get('se_e_draw_sequence',2)!=seq:break
  else:raise AssertionError('foreign-lease render convergence')
  f.trace=False;assert f.get('se_doc_read_locks',1)==1 and f.get('se_fs_owned',1)==0 and f.canonical()==canonical and f.catalog()==catalog;c.exact_pixels(f,data,fonts,'foreignlease');c.outside_cache(f,before,'foreignlease');assert any(e['op']==3 and e['proof']==2 for e in f.events);assert not f.call('se_doc_read_release').p&1;clean();record('foreign-read-lease-preserved')

  # Full actual C->resident->C admission with foreign FILE owner; C21 refuses
  # before any semantic/FS/phase union reads/writes, not just a direct stub.
  setup();f.put('se_f_owner',1,1);f.m.load(0x8b40,bytes([0xa5])*192);f.m.load(0x8d00,bytes([0x5a])*1152);phase=f.read(0x8b40,192)+f.read(0x8d00,1152);before=f.reu();canonical=f.canonical();f.m.write(f.s['se_overlay_frame'],0);r,n=f.fast_call(f.s['se_overlay_call'],a=21,x=1)
  assert r.p&1 and r.a==0xb2 and f.get('se_f_owner',1)==1 and f.read(0x8b40,192)+f.read(0x8d00,1152)==phase and f.reu()==before and f.canonical()==canonical and f.read(0xc600,1024)==f.shim;f.put('se_f_owner',0,1);record('actual-C21-foreign-owner-opaque',error=0xb2,instructions=n)
  result=dict(status='passed',budget=budget,identity=identity,cases=cases,scope='Actual public root/C21/C24/R14 optional checkpoint recovery, old sealed worker compatibility, original errors preserved; whole16MiB guards including dead R28 backups. No native/cycles/public C23 routing claim.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure-reu.bin').write_bytes(f.reu());raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=c.BASE);a=p.parse_args();out=ROOT/'build/geos-semantic-consumer-recovery'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.fixture.resolve());print('RESULT',r['status'],r['budget'],'cases',len(r['cases']))
