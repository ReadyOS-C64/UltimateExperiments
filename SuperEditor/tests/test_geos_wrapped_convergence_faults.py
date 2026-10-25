"""Private complete-line convergence authority/cancellation/failure regression."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_wrapped_convergence as q
c=q.c

def run(out,project):
 frozen,identity=q.hook.freeze_project(out,project);c.geos.grid.editor_fixture.ROOT=c.geos.grid.cpu_editor.ROOT=frozen;c.geos.grid.editor_fixture.NAMES=c.geos.grid.cpu_editor.NAMES=identity['names'];dll=c.geos.grid.runner(out);f=c.Fixture(out,frozen,dll,True);fonts={n:(frozen/'fonts'/n).read_bytes()for n in c.geos.GEOS_FONTS+('native8.bin',)};cases=[];data=b''
 def clean():assert not any(f.get(n,1)for n in['se_e_error','se_e_job','se_f_owner','se_fs_owned','se_doc_read_locks','se_e_draw_busy'])and f.read(0xc600,1024)==f.shim,f.debug()
 def done(tag,**kw):cases.append(dict(tag=tag,**kw));print('PASS',cases[-1],flush=True);(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
 def setup():
  nonlocal data
  data=c.geos.native_text('Long '+('wide words '*20)+'\rNext untouched.\rThird unchanged.\rTail.');f.source(data);f.command(99);f.position(70);f.render();clean()
  cache,_=f.raw_cache();assert cache[0x700:0x704]==bytes([0x43,2,64,1])
 def edit():
  nonlocal data
  at=f.get('se_hot_caret');data=data[:at]+b'*'+data[at:];f.key(ord('*'))
 def exact(tag,dirty=None):
  before=f.reu();canonical=f.canonical();catalog=f.catalog();used=f.total_instructions;f.render();assert f.merged()==data and f.canonical()==canonical and f.catalog()==catalog;q.outside(f,before,tag);clean();bits,attrs,rows=c.exact_pixels(f,data,fonts,tag)
  if dirty is not None:assert (f.m.read(0x9134+20)==2)==dirty,(tag,'convergence',f.m.read(0x9134+20))
  c.geos.png(bits,attrs,out/(tag+'.png'));return f.total_instructions-used
 def write(offset,raw):
  f.m.load(0x9000,raw)
  for n,v,w in [('se_reu_logical',f.get('se_gc_handle',1),1),('se_reu_offset',offset,2),('se_reu_c64',0x9000,2),('se_reu_length',len(raw),2)]:f.put(n,v,w)
  assert not f.call('se_reu_copy',0).p&1
 def mutate(at,crc):
  cache,_=f.raw_cache();raw=bytearray(cache[0x700:0x740]);raw[at]^=1
  if crc:raw[62:64]=binascii.crc_hqx(raw[:62],65535).to_bytes(2,'little')
  write(0x700,raw)
 def remove(id,slot):
  index=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==id and f.m.read(f.s['image_slot']+i)&127==slot);f.m.write(f.s['se_overlay_ids']+index,0);f.m.write(f.s['se_overlay_active']+slot,0);return index
 try:
  # Each certificate byte is covered by CRC. Semantically meaningful fields
  # with recomputedCRC still cannot manufacture a convergence authority.
  for at in range(64):setup();mutate(at,False);edit();done('bad-crc-'+str(at),instructions=exact('bad-crc-'+str(at),False))
  for at in [0,1,2,3,4,5,6,7,12,17,22,28,31,33,35,36,37,38,39,40,41,42,43]:
   setup();mutate(at,True);edit();done('CRC-correct-field-'+str(at),instructions=exact('CRC-correct-field-'+str(at),False))
  # No newphase fields are interpreted for a foreign owner, including the
  # newR19op7 dispatch and oldR28 op0 dispatch through the real loader.
  for asset,slot,op in[(19,0,7),(28,0,0)]:
   setup();f.put('se_f_owner',1,1);f.m.load(0x8880,bytes([0x5a])*0x900);phase=f.read(0x8880,0x900);before=f.reu();canonical=f.canonical();f.m.write(f.s['se_overlay_frame'],op);r,n=f.fast_call(f.s['se_overlay_call'],a=asset,x=slot);assert r.p&1 and r.a==0xb2 and f.read(0x8880,0x900)==phase and f.canonical()==canonical and f.reu()==before and f.get('se_f_owner',1)==1;f.put('se_f_owner',0,1);done('foreign-owner-'+str(asset),instructions=n)
  # STOP afterheaderVALID0 admission and again afternewrow verification:
  # no C22 pixels published yet; subsequent ordinary repaint mustrecover.
  for phase in ['admitted','verified']:
   setup();edit();canonical=f.canonical();catalog=f.catalog();before=f.reu();body=f.read(0x6000,8000);f.call('se_editor_render')
   for steps in range(20000):
    if f.get('se_e_job',1)==11 and f.m.read(0x9134+20)==2 and ((phase=='admitted'and f.m.read(0x9134)!=12)or(phase=='verified'and f.m.read(0x9134)==12)):break
    assert f.get('se_e_job',1)==11,('missingpending',phase,f.debug());f.call('se_editor_service')
   else:raise AssertionError('pendingbudget')
   assert f.read(0x6000,8000)==body;f.queued(3);f.call('se_editor_service');assert f.canonical()==canonical and f.catalog()==catalog and f.read(0x6000,8000)==body;q.outside(f,before,phase+'STOP');clean();done('STOP-'+phase,steps=steps,repaint_instructions=exact('STOP-'+phase+'-repaint',False))
  # Optional publisher absence mustneverrejectsource. MissingmandatoryR28
  # propagates17 andleaves ownedcleanup/recovery intact.
  setup();edit();idx=remove(19,0);done('missing-publisher-existing-authority',instructions=exact('missing-publisher-existing-authority',True));f.m.write(f.s['se_overlay_ids']+idx,19)
  setup();idx=remove(19,0);write(0x703,b'\0');edit();done('missing-publisher-no-authority-fullfallback',instructions=exact('missing-publisher-no-authority-fullfallback',False));f.m.write(f.s['se_overlay_ids']+idx,19)
  setup();edit();canonical=f.canonical();before=f.reu();body=f.read(0x6000,8000);idx=remove(28,0);f.call('se_editor_render');assert f.get('se_e_error',1)==0x17 and not any(f.get(n,1)for n in['se_e_job','se_f_owner','se_fs_owned','se_doc_read_locks'])and f.canonical()==canonical and f.read(0x6000,8000)==body;q.outside(f,before,'missingR28');f.m.write(f.s['se_overlay_ids']+idx,28);f.key(0x8b);f.key(0x8b);done('missingR28-recovered',instructions=exact('missingR28-recovered'))
  # Actualpublic C21->R28 VALID-last write fails at protectedC600. Sourceedit
  # remains canonical/pending; incomplete metadata/header cannot be trusted.
  setup();edit();canonical=f.canonical();before=f.reu();body=f.read(0x6000,8000);f.call('se_editor_render')
  for steps in range(20000):
   if f.get('se_e_job',1)==11 and f.m.read(0x9134+20)==2 and f.m.read(0x9134)==4 and f.m.read(0x9135)==21 and f.m.read(0x9137)==f.m.read(0x9149+28):break
   assert f.get('se_e_job',1)==11;f.call('se_editor_service')
  else:raise AssertionError('beforeverifybudget')
  for n,v in [('pc',f.s['se_editor_service']),('sp',0xfd),('p',0x24),('a',0),('x',0),('y',0)]:getattr(f.m.lib,'zeropage_peddle_set_'+n)(f.m.handle,v)
  f.m.write(0x1fe,0xfe);f.m.write(0x1ff,2);injected=0
  for instructions in range(200000):
   if f.m.regs().pc==0x2ff:break
   if f.m.regs().pc==f.s['se_reu_copy']and f.get('se_reu_logical',1)==f.get('se_gc_handle',1)and f.get('se_reu_offset',2)==0x703 and f.get('se_reu_length',2)==1:
    assert not injected;f.put('se_reu_c64',0xc600,2);injected+=1
   f.m.lib.zeropage_peddle_step_instruction(f.m.handle)
  else:raise AssertionError('providerfaultreturnbudget')
  cache,_=f.raw_cache();assert injected==1 and cache[0]==0 and cache[0x703]==0 and f.get('se_e_error',1)and not any(f.get(n,1)for n in['se_e_job','se_f_owner','se_fs_owned','se_doc_read_locks'])and f.canonical()==canonical and f.read(0x6000,8000)==body and f.read(0xc600,1024)==f.shim;q.outside(f,before,'actualVALIDlastfailure');error=f.get('se_e_error',1);f.key(0x8b);f.key(0x8b);done('actualVALIDlast-provider-refusal-recovered',original_error=error,injected=injected,instructions=exact('actualVALIDlast-provider-refusal-recovered'))
  result=dict(status='passed',identity=identity,cases=cases,scope='Actualcoherentprivate48asset loadedpublicedit/render. Every64certificatebytebadCRC +CRCcorrect semanticidentity/carry/TOP, foreignphaseopaque, STOPpre/postverify andmissingworker recovery. Whole16MiB exactoutside declaredspans, canonical/history/pixels/anchors/shim. CPUonly.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure-reu.bin').write_bytes(f.reu());raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',type=Path,default=q.DEFAULT);a=p.parse_args();out=ROOT/'build/geos-wrapped-convergence-faults'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.project.resolve());print('RESULT',r['status'],len(r['cases']))
