"""Private packaged59 root5 lexical-cache controlled standalone lifecycle."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_lexical_registered as reg
geos=reg.geos;plain=reg.plain
BASE=ROOT/'agentsworking/evidence/M8/20261026T085227798430Z-cache-lexical-registration/run/fixture'
PROJECT=ROOT/'build/cache-lexical-registration/candidate-59b/project'
helper=reg.module('lexical_controlled_resume',ROOT/'src/cache/lexical-resume-probe/controlled.py')
files=reg.module('lexical_resume_files',ROOT/'src/cache/lexical-resume-probe/files.py')

def run(out,base,project,pending=False,motion=False,io=False):
 out.mkdir(parents=True);frozen,identity=geos.freeze(out,base);assert len(identity['names'])==59
 geos.grid.cpu_editor.ROOT=geos.grid.editor_fixture.ROOT=frozen;geos.grid.cpu_editor.NAMES=geos.grid.editor_fixture.NAMES=identity['names']
 import font_fixture
 font_fixture.ROOT=frozen
 dll=geos.grid.runner(out);f=None;frames=[];cases=[]
 fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
 producer=reg.labels(project/'build/lexical/ical.lbl');strict=reg.labels(project/'build/overlays/geoslex.lbl')
 def render(data,tag):
  canonical=f.canonical();catalog=f.catalog();before=f.reu();lo,sel,root=reg.arena(f,before);f.trace=[];start=f.total_instructions;loads=f.get('se_overlay_loads',2)
  dll.gm_profile(f.s['se_overlay_active']+1,list(f.assets).index('ical')+1,list(f.assets).index('geoslex')+1,producer['se_sl_feed'],0,0,strict['se_sl_feed']);f.render();pf,sf=dll.gm_metric(0),dll.gm_metric(2);dll.gm_profile(0,0,0,0,0,0,0)
  after=f.reu();current_fs=helper.fs_identity(f,project);fs_changes=[i for i,(a,b)in enumerate(zip(root[32:91],current_fs))if a!=b];bits,attrs,rows=plain.expected(f,data,fonts,3)
  assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'independentpixels')
  assert f.canonical()==canonical and f.catalog()==catalog and f.merged()==data and f.read(0xc600,1024)==f.shim
  _,bank=f.raw_cache();fe=bank*65536;wanted=bytearray(before)
  for a,b in[(0,64),(0x200,0xea88)]:wanted[fe+a:fe+b]=after[fe+a:fe+b]
  # No sourceedit occurs inside this interval. Both armed-cache reuse and
  # LOST fallback leave the entire53allocation exactlyunchanged.
  assert after[lo:lo+65536]==before[lo:lo+65536]and after==wanted,(tag,'whole16MiBread-onlyoutsidepreciseFE')
  assert not any(f.get(n,1)for n in('se_e_error','se_f_owner','se_e_job','se_doc_read_locks','se_fs_owned'))
  geos.png(bits,attrs,out/(tag+'.png'));r=dict(tag=tag,root_FS59_equal=not fs_changes,root_FS59_changed_offsets=fs_changes,instructions=f.total_instructions-start,loads=(f.get('se_overlay_loads',2)-loads)&65535,producer_feeds=pf,strict_feeds=sf,gateway_calls=sum(t[0]==45 for t in f.trace),producer_begins=sum(t[:2]==(47,0)for t in f.trace),linker_begins=sum(t[:2]==(49,0)for t in f.trace),flags=f.get('se_bc_flags',1),bc=helper.bc_state(f));frames.append(r);print('RESUME_FRAME_PASS',r,flush=True);return r
 try:
  for language in('basic','asm'):
   for policy in(['unchanged']+(['pending']if pending else[])+(['motion']if motion else[])):
    dirty=policy=='pending'
    if f:f.close()
    f=(files.Fixture if io else reg.automatic.Fixture)(out,frozen,dll,True)
    data=geos.native_text('Intro\r:::'+language+'\r'+('10 PRINT "Hi":REM 'if language=='basic'else'label lda #42 ; '))+geos.native_text('x')*980+geos.native_text('\r:::\rTail.')
    f.source(data);assert not f.call('se_clip_init').p&1;f.typed(geos.native_text('syntax markdown'));f.command(99);f.render();f.typed(geos.native_text('syntax full'));f.render()
    before=f.reu();lo,_,root=reg.arena(f,before);assert root[31]==5 and root[98]==1 and f.get('se_bc_flags',1)&129==129 and not f.get('se_bc_flags',1)&64
    assert helper.fs_identity(f,project)==root[32:91],'initialactualFS59rootbinding'
    tag=language+'-'+policy
    if dirty:
     f.key(geos.native_text('Q')[0]);data=geos.native_text('Q')+data;assert f.get('se_hot_pending',1)==1 and f.merged()==data
     # Do not render away a queued edit beforecapture. Actual observer state
     # (ticket/queue/LOST/attempt) is part of the snapshot and must survive.
     assert not f.get('se_bc_flags',1)&12 and f.get('se_bc_count',1)>0 and f.get('se_bc_ticket',4)>0
    authority=helper.bc_state(f);saved=helper.suspend_resume(f,dll,frozen,project,out/(tag+'-lifecycle'));assert helper.bc_state(f)==authority
    if policy=='motion':f.command(2) #realpublicRIGHT: samecontent, changedhotgaprepresentation
    f.key(0x8a);f.key(0x8a) #actual public policy changes revoke both geometry/bitmap shortcuts
    r=render(data,tag+'-after-resume')
    if policy=='unchanged':assert r['producer_feeds']==r['strict_feeds']==r['producer_begins']==r['linker_begins']==0 and r['flags']&129==129 and r['gateway_calls']>0 and r['root_FS59_equal'],'unchangedroot5warmedreuse'
    else:
     assert r['producer_begins']==r['linker_begins']==0 and r['strict_feeds']>0 and r['flags']&128 and not r['root_FS59_equal'],'changedsourceguardedfallback'
     if dirty:assert f.get('se_bc_count',1)>0
     else:assert f.get('se_bc_count',1)==f.get('se_bc_ticket',4)==0,'motionmustnotinventedit'
    file_result=None
    if io and policy=='unchanged':
     file_result=files.save_reopen(f,data,language,out/(language+'-save-reopen'))
     # ActualFile/H_INIT reset128. The next realFull viewport may construct
     # a freshbaseline/lexroot; do not seedflags/ref/producer/linkoperations.
     f.trace=[];dll.gm_profile(f.s['se_overlay_active']+1,list(f.assets).index('ical')+1,list(f.assets).index('geoslex')+1,producer['se_sl_feed'],0,0,strict['se_sl_feed']);f.render()
     fresh_feeds=dll.gm_metric(0);fresh_strict=dll.gm_metric(2);dll.gm_profile(0,0,0,0,0,0,0)
     lo,sel,newroot=reg.arena(f,f.reu());assert newroot[31]==5 and newroot[98]==1 and f.get('se_bc_flags',1)&129==129 and not f.get('se_bc_flags',1)&64
     body=data.index(geos.native_text('10 PRINT'if language=='basic'else'label'));end=data.index(13,body)
     assert fresh_feeds==end-body and fresh_strict==0 and sum(t[:2]==(47,0)for t in f.trace)==sum(t[:2]==(49,0)for t in f.trace)==1,'actualreopenedtrigger'
     file_result.update(fresh_producer_feeds=fresh_feeds,fresh_strict_feeds=fresh_strict,fresh_automatic_root_flags=5,incarnation_after_baseline=f.get('se_bc_incarnation',4))
     f.key(0x8a);f.key(0x8a);fresh=render(data,language+'-reopened-warm');assert fresh['gateway_calls']>0 and fresh['producer_feeds']==fresh['strict_feeds']==0
    cases.append(dict(tag=tag,lifecycle=saved,frame=r,files=file_result))
  result=dict(status='PASS-root5-controlled-resume',identity=identity,cases=cases,frames=len(frames),scope='Private59 actualautomaticconstruction then packagedC29/R26 capture/freshtrustedbootstrap/resume; exactBC17+ring96 preserved; noReadyOS/native/hardware/oldstackclaim')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('LEXICAL_RESUME_PASS',len(cases),flush=True)
 except BaseException:
  assert f
  (out/'failed-ram.bin').write_bytes(f.read(0,65536));(out/'failed-reu.bin').write_bytes(f.reu());(out/'failed-trace.json').write_text(json.dumps(getattr(f,'trace',[]),indent=2)+'\n');raise
 finally:
  if f:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--project',type=Path,default=PROJECT);p.add_argument('--pending',action='store_true');p.add_argument('--motion',action='store_true');p.add_argument('--io',action='store_true');a=p.parse_args();out=ROOT/'build/cache-lexical-resume'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.project.resolve(),a.pending,a.motion,a.io)
