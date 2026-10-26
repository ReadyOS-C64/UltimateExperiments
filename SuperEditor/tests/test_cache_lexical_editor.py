"""Private actual C21/C20/C25 retained lexicalwindow parent proof."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,sys,importlib.util
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_lexical as lexical
import test_cache_lexical_link as link
import test_geos_semantic_editor as semantic
import test_plain_geos as plain
geos=lexical.geos;F=lexical.F
from overlays import wrap
spec=importlib.util.spec_from_file_location('lexical_editor_build',ROOT/'src/cache/lexical-editor-probe/build.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
BASE=link.BASE
class Fixture(link.Fixture):
 def call(self,name,a=0):
  request=self.m.read(0x9135) if name=='se_editor_service' else 0
  r=super().call(name,a)
  if request==25 and self.m.read(0x9135)==39:
   item=dict(query=int.from_bytes(self.read(0x9097,3),'little'),count=self.m.read(0x909b),reason=self.m.read(0x90ae),phase=self.m.read(0x90af))
   self.window_trace=getattr(self,'window_trace',[])+[item]
  return r

def run(out,base,build_only=False):
 out.mkdir(parents=True);frozen,identity=geos.freeze(out,base);binaries,ls,budget=builder.build(out/'adapter',frozen)
 worker,wl,wb=lexical.build(out/'producer',frozen);page,pl,pb=lexical.build_page(out/'page',frozen);writer,ll,lb=link.build(out/'link',frozen)
 if build_only:return
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out);f=Fixture(out,frozen,dll,True);g=geos.Fixture(out,frozen,dll,True)
 digest=bytes.fromhex(json.load(open(frozen/'build/editor-report.json'))['resident_binding']['digest']);api=f.s['se_overlay_call'],f.s['se_overlay_frame'];original=f.assets.copy()
 for name,raw,slot,id_ in [('lifectrl',worker,1,29),('lifecopy',page,0,26),('eplay',writer,1,5),('geoslex',binaries['gateway'],1,25),('gtype',binaries['resolver'],0,30),('line',binaries['fallback'],1,39),('inln',binaries['query'],1,35)]:f.assets[name]=wrap(raw,slot,id_,api=api,binding_digest=digest)
 fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
 def drive(fn,op=1):
  for i in range(20000):
   r,n=fn(op)
   if r.p&1 or r.a!=1:return r
  raise AssertionError('bounded')
 try:
  data=geos.native_text('Intro\r:::basic\r10 PRINT "Hi":REM ')+geos.native_text('x')*980+geos.native_text('\r:::\rTail.');target=data.index(geos.native_text('10 PRINT'))
  # Initialpublicrender has no linkedLEXref; gateway must use actualfallback.
  f.source(data);f.command(99);f.render();print('INITIAL_PARENT_PASS',flush=True)
  for n in ('se_i_ready','se_i_count','se_n_cache_count'):f.put(n,0,1)
  f.put('se_f_owner',4,1);f.m.write(0x8b40+21,0);f.m.load(0x8b40,target.to_bytes(3,'little'));f.put('se_overlay_frame',0,1);r,n=f.fast_call(f.s['se_overlay_call'],a=35,x=1)
  while not r.p&1 and r.a==1:
   f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=35,x=1)
  assert not r.p&1 and not r.a
  cold_start=f.total_instructions;cold_loads=f.get('se_overlay_loads',2)
  assert not f.lx(0)[0].p&1;f.lp(0);assert not drive(f.lp).p&1
  while True:
   r,n=f.lx(1);assert not r.p&1
   if f.m.read(F+4)==1:f.lp(3);f.lx(3)
   elif f.m.read(F+4)==2:f.lp(5);assert not drive(f.lp).p&1;f.lx(3);break
  r,n=f.ll(0);assert not r.p&1;r=drive(f.ll);assert not r.p&1 and not r.a
  build_link_instructions=f.total_instructions-cold_start;build_link_loads=(f.get('se_overlay_loads',2)-cold_loads)&65535
  f.put('se_f_owner',0,1);g.source(data);g.command(99);g.render();frames=[]
  def check(tag,retained=True):
   canonical=f.canonical();catalog=f.catalog();before=f.reu();start=f.total_instructions;loads=f.get('se_overlay_loads',2)
   f.window_trace=[]
   dll.gm_profile(f.s['se_overlay_active']+1,list(f.assets).index('geoslex')+1,list(f.assets).index('line')+1,ls['gateway']['cache_hit'],0,0,ls['fallback']['se_sl_feed'])
   f.key(0x8a);f.key(0x8a);f.render();used=f.total_instructions-start;hits=dll.gm_metric(0);feeds=dll.gm_metric(2);load_delta=(f.get('se_overlay_loads',2)-loads)&65535
   print('WINDOW_TRACE',f.window_trace,flush=True)
   caps=f.get('se_render_caps',1)
   assert (hits>0 and feeds==0)if retained else (hits==0 and (feeds>0 if caps==3 else feeds==0)),(tag,'realcachedwindows/feed',hits,feeds,f.window_trace)
   bits,attrs,rows=plain.expected(f,data,fonts,caps);sem=semantic.classify(data);roles=bytes(0 if caps==0 else 4 if caps==1 and sem.code[i] else v for i,v in enumerate(sem.roles));assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
   cache,bank=f.cache()
   for i,row in enumerate(rows):
    at=0x200+i*0x800;count=row.end-row.start
    assert cache[at+352:at+352+count]==roles[row.start:row.end],(tag,'actualparentroles',i)
    assert tuple(int.from_bytes(cache[at+j:at+j+3],'little')for j in (0,3,6))==(row.start,row.end,row.next)
   after=f.reu();expected=bytearray(before);lo=bank*65536
   for a,b in [(lo,lo+64),(lo+0x200,lo+0xEA88)]:expected[a:b]=after[a:b]
   assert after==expected,(tag,'whole16MiB outside declaredsourceFE/typed53readonly')
   assert f.canonical()==canonical and f.catalog()==catalog and f.merged()==data and f.read(0xc600,1024)==f.shim and not f.get('se_doc_read_locks',1)
   dll.gm_profile(g.s['se_overlay_active']+1,list(g.assets).index('geoslex')+1,0,ls['fallback']['se_sl_feed'],0,0,0)
   start=g.total_instructions;loads=g.get('se_overlay_loads',2);g.key(0x8a);g.key(0x8a);g.render();baseline=g.total_instructions-start;baseline_feeds=dll.gm_metric(0);baseline_loads=(g.get('se_overlay_loads',2)-loads)&65535
   assert (baseline_feeds>0 if caps==3 else baseline_feeds==0) and g.read(0x6000,8000)==bits and g.read(0x4000,1000)==attrs and g.merged()==data
   dll.gm_profile(0,0,0,0,0,0,0)
   geos.png(bits,attrs,out/(tag+'.png'))
   frame=dict(tag=tag,render_instructions=used,loads=load_delta,actual_cache_windows=hits,actual_lexer_feeds=feeds,baseline_packaged_instructions=baseline,baseline_loads=baseline_loads,baseline_actual_lexer_feeds=baseline_feeds,rows=len(rows));frames.append(frame);print('FRAME_PASS',frame,flush=True)
  for i in range(3):check('linked-repeat-'+str(i))
  # Missing optionalmetadata workers must choose the actual strictfallback.
  for id_,name in ((30,'resolver'),(26,'consumer')):
   index=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==id_ and f.m.read(f.s['image_slot']+i)&127==0)
   f.m.write(f.s['se_overlay_ids']+index,255);f.m.write(f.s['se_overlay_active'],0)
   check('missing-'+name,False);f.m.write(f.s['se_overlay_ids']+index,id_)
  # Actual rootSTOP while a retainedmetadata/role window owns the sourcelease.
  f.key(0x8a);f.key(0x8a);canon=f.canonical();reu=f.reu();r=f.call('se_editor_render');assert not r.p&1
  for _ in range(20000):
   if f.m.read(0x9135)==25 and f.m.read(0x9096)==3 and f.get('se_doc_read_locks',1):break
   assert f.get('se_e_job',1)==11;f.call('se_editor_service')
  else:raise AssertionError('pendingcachedwindow')
  f.queued(3);f.call('se_editor_service');assert not any(f.get(n,1)for n in ('se_e_error','se_f_owner','se_e_job','se_doc_read_locks','se_fs_owned','se_e_draw_busy')) and f.canonical()==canon
  check('STOP-rebuild')
  # ImmutableactualGSEM request mustrefuse, not reseed fallback on newargs.
  f.key(0x8a);f.key(0x8a);canon=f.canonical();f.call('se_editor_render')
  for _ in range(20000):
   if f.m.read(0x9135)==25 and f.m.read(0x9096)==1 and f.get('se_doc_read_locks',1):break
   assert f.get('se_e_job',1)==11;f.call('se_editor_service')
  else:raise AssertionError('pendingverification')
  f.m.write(0x8b44,f.m.read(0x8b44)^1);f.call('se_editor_service')
  assert f.get('se_e_error',1)==0xb1 and not any(f.get(n,1)for n in ('se_f_owner','se_e_job','se_doc_read_locks','se_fs_owned','se_e_draw_busy')) and f.canonical()==canon
  f.key(0x8b);f.key(0x8b);check('changed-request-recovery')
  for name,caps in [('plain',0),('markdown',1)]:
   for x in (f,g):x.typed(geos.native_text('syntax '+name))
   check('bypass-'+name,False)
  # A shortactual public code line deliberately avoids retainedadmission.
  data=geos.native_text('Intro\r:::basic\r10 PRINT "Hi":REM tail\r:::\rTail.')
  for x in(f,g):x.source(data);x.command(99);x.render()
  check('short-body-fallback',False)
  result=dict(status='passed-parent',budget=budget,source_bytes=1023,BODY_bytes=998,build_link_instructions=build_link_instructions,build_link_loads=build_link_loads,frames=frames,classification='PrivatestrictC35 acceptsflags1/5 withlexABI0/1 andrealCRclassification; noPAGE_REUSE/CP79/outgoingcert claim.',scope='Private actualpublicC21/C20→C25gateway→committedrootCR/R26windows vs unchangedpackagedC25; no productionplacement/native claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',result,flush=True)

 except BaseException:
  (out/'failed-ram.bin').write_bytes(f.read(0,65536));(out/'failed-reu.bin').write_bytes(f.reu());raise
 finally:f.close();g.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--build-only',action='store_true');a=p.parse_args();out=ROOT/'build/cache-lexical-editor'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.build_only)
