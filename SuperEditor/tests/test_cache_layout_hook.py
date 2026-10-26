"""Private combined-hook fit/public proof; no canonical registration or promotion."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,sys,json
import test_cache_layout_compact as component
ROOT=component.ROOT
SOURCE=ROOT/'src/cache/layout-hook-probe'
def build(out,base):
 out.mkdir(parents=True,exist_ok=True);cmd=component.cmd
 cmd([sys.executable,ROOT/'src/fold/editor-leaves/binding.py','--report',base/'build/editor-report.json','--output',out/'editor-api.inc']);objects=[]
 for n in ('entry','memo','transport','hook'):
  obj=out/(n+'.o');args=['ca65','-g','-I',out,'-I',ROOT/'src','-o',obj,'-l',out/(n+'.lst')]
  if n=='transport':args+=['-D','SE_GP_CACHE_WARM_ONLY=1']
  cmd(args+[SOURCE/(n+'.s')]);objects.append(obj)
 cmd([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects]);cmd(['ca65',out/'aliases.s','-o',out/'aliases.o']);objects.append(out/'aliases.o')
 cmd(['ld65','-C',ROOT/'cfg/overlay-r.cfg','-o',out/'image.bin','-m',out/'image.map','-Ln',out/'image.lbl',*objects]);return len((out/'image.bin').read_bytes())
def build_pair(out,base):
 import shutil
 from overlays import wrap
 cmd=component.cmd;out.mkdir(parents=True,exist_ok=True);r=json.loads((base/'build/editor-report.json').read_text());sy=r['symbols'];digest=bytes.fromhex(r['resident_binding']['digest'])
 n=build(out/'R34',base);api=out/'R34'
 assert (ROOT/'build/overlays/rangeio.seo').read_bytes()==(base/'build/overlays/rangeio.seo').read_bytes()
 assert (ROOT/'build/overlays/lifectrl.seo').read_bytes()==(base/'build/overlays/lifectrl.seo').read_bytes()
 shutil.copy2(ROOT/'build/geos-prod/consumer-witness.inc',api/'consumer-witness.inc')
 images={}
 def link(name,entries,existing,cfg,slot,id,prefix=()):
  work=out/name;work.mkdir();objects=list(prefix)
  for tag,source,flags in entries:
   obj=work/(tag+'.o');cmd(['ca65','-g',*flags,'-I',api,'-I',ROOT/'src','-o',obj,'-l',work/(tag+'.lst'),source]);objects.append(obj)
  objects+=existing
  cmd([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',work/'aliases.s',*objects]);cmd(['ca65',work/'aliases.s','-o',work/'aliases.o']);objects.append(work/'aliases.o')
  cmd(['ld65','-C',cfg,'-o',work/'image.bin','-m',work/'image.map','-Ln',work/'image.lbl',*objects]);raw=(work/'image.bin').read_bytes();image=wrap(raw,slot,id,api=(sy['se_overlay_call'],sy['se_overlay_frame']),binding_digest=digest);(work/'image.seo').write_bytes(image);return image
 images['layoutmemo']=wrap((out/'R34/image.bin').read_bytes(),0,34,api=(sy['se_overlay_call'],sy['se_overlay_frame']),binding_digest=digest)
 (out/'R34/image.seo').write_bytes(images['layoutmemo'])
 images['geospage']=link('C21',[('page',SOURCE/'page.s',[]),('cache',SOURCE/'page-cache.s',[])],[],ROOT/'cfg/geos-editor-page.cfg',1,21)
 others=[ROOT/q for q in ('build/engine/range-entry.o','build/engine-code/range.o','build/editor_fold/journal-code.o')]
 tail=[ROOT/'build/geos-prod/cache-warm.o']
 control=link('R19-control',[('outgoing',ROOT/'src/render/geos/checkpoint/outgoing.s',[])],tail,ROOT/'cfg/range-journal.cfg',0,19,prefix=others)
 assert control==(base/'build/overlays/rangeio.seo').read_bytes(),'R19 control must be byte identical'
 images['rangeio']=link('R19',[('outgoing',SOURCE/'r19-outgoing.s',[])],tail,ROOT/'cfg/range-journal.cfg',0,19,prefix=others)
 control=link('C29-control',[('resume',ROOT/'src/lifecycle/resume.s',['-D','EDITOR_MANAGED_CODE=1'])],[],ROOT/'cfg/lifecycle-controller.cfg',1,29,prefix=[ROOT/'build/lifecycle-prod/adapter.o',ROOT/'build/lifecycle-prod/preflight.o'])
 assert control==(base/'build/overlays/lifectrl.seo').read_bytes(),'C29 control must be byte identical'
 images['lifectrl']=link('C29',[('resume',SOURCE/'resume.s',['-D','EDITOR_MANAGED_CODE=1'])],[],ROOT/'cfg/lifecycle-controller.cfg',1,29,prefix=[ROOT/'build/lifecycle-prod/adapter.o',ROOT/'build/lifecycle-prod/preflight.o'])
 result=dict(status='private-combined-fit-not-qualified',R34bytes=n,C21bytes=len(images['geospage'])-36,R19bytes=len(images['rangeio'])-36,C29bytes=len(images['lifectrl'])-36,permission='privatebit64: newFE/resume revoke and explicit R19defined-mask clone; no main ABI change',public_revisit_proven=False)
 (out/'fit.json').write_text(json.dumps(result,indent=2)+'\n');return images,result
def run_public(out,base,images,fit):
 import ctypes as C,hashlib
 geos=component.geos;semantic=component.semantic
 ident=json.loads((base/'freeze.json').read_text());geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=base;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=ident['names']
 dll=component.profiled_runner(out);f=geos.Fixture(out,base,dll,True);record=[]
 def monitor():dll.gm_lm_monitor(f.s['se_overlay_active']+1,*[ident['names'].index(n)+1 for n in ('geosline','geossema','geoslex','geosinln')])
 def profile():return {n:dict(calls=dll.gm_lm_metric(i*2),instructions=dll.gm_lm_metric(i*2+1))for i,n in enumerate(('C20','C24','C25','C26'))}
 def whole():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(f.m.handle,len(b),b);return b.raw
 try:
  f.assets.update({k:v for k,v in images.items()if k!='layoutmemo'});f.assets['layoutmemo']=images['layoutmemo']
  from test_grid_editor_vice import fixture
  data=fixture();f.source(data);assert not f.get('se_bc_flags',1)&64,'cold/H_INIT must revokepermission'
  f.command(99);monitor();start=f.total_instructions;f.render();costA=f.total_instructions-start;rawA,physical=f.raw_cache();assert f.get('se_v_top')==0;print('A',f.get('se_v_top'),costA,profile(),flush=True)
  fonts={n:(base/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
  bits,attrs,_,_=semantic.expected(f,data,fonts);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
  history=lambda:b''.join(f.read(f.s[n],w)for n,w in [('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4),('se_h_group',1),('se_h_open_group',1),('se_clip_token',5),('se_clip_length',3)])
  immutable_history=history();canonical=f.canonical();sourcekey=f.read(f.s['se_doc_meta'],15)+f.read(f.s['se_doc_generation'],2)+f.read(f.s['se_r_revision'],4);shim=f.read(0xC600,1024)
  # These are actual public commands; no TOP/packet/key/phase seed is made.
  f.command(35);monitor();start=f.total_instructions;f.render();costB=f.total_instructions-start;rawB,_=f.raw_cache();assert rawB[32:35]!=rawA[32:35];assert f.get('se_bc_flags',1)&64;eb,ea,_,_=semantic.expected(f,data,fonts);assert f.read(0x6000,8000)==eb and f.read(0x4000,1000)==ea and history()==immutable_history;print('B',f.get('se_v_top'),costB,profile(),flush=True)
  before=whole();f.command(34);monitor();start=f.total_instructions;f.render();costReturn=f.total_instructions-start;counts=profile();rawR,_=f.raw_cache();print('RETURN',f.get('se_v_top'),costReturn,counts,flush=True)
  assert f.get('se_v_top')==0 and all(v['calls']==0 for v in counts.values()),counts
  from geos_packet import rows
  assert rows(rawR)==rows(rawA);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs and f.merged()==data and f.read(0xC600,1024)==shim
  assert f.read(f.s['se_doc_meta'],15)+f.read(f.s['se_doc_generation'],2)+f.read(f.s['se_r_revision'],4)==sourcekey
  # Public W_LOAD may change gap representation but never canonical source.
  after=whole();startbank=physical*65536
  spans=component.SPANS+component.live_primary(rawA)+component.live_primary(rawB)+[(0xB200,0xD528)]
  spans=sorted(spans);cursor=0
  for a,b in spans:
   a+=startbank;b+=startbank
   if a>cursor:assert before[cursor:a]==after[cursor:a],('publicreturn outside preciseFE',hex(cursor),hex(a))
   cursor=max(cursor,b)
  assert before[cursor:]==after[cursor:] and history()==immutable_history

  geos.png(bits,attrs,out/'returned-A.png')
  record.append(dict(case='actual-public-E_BOTTOM-E_TOP',A=costA,B_with_capture=costB,return_A=costReturn,TOP_B=int.from_bytes(rawB[32:35],'little'),final_profile=counts,manual_TOP_or_FE_seed=False))
  # A real freshFEallocation must not authorize old retained bytes.
  handle=f.get('se_gc_handle',1);f.put('se_f_owner',0,1);freed,_=f.fast_call(f.s['se_reu_free'],x=handle);assert not freed.p&1
  f.command(35);monitor();f.render();assert not f.get('se_bc_flags',1)&64;assert profile()['C20']['calls']>0;assert f.merged()==data
  record.append(dict(case='actual-freshFE-allocation-revokes',old_logical=handle,new_logical=f.get('se_gc_handle',1),profile=profile()))
  # Execute the actual newly compiled resume prefix, stopping before its
  # first managed-unverify call. This proves revocation, not a whole snapshot.
  template=images['lifectrl'][36+0x800:36+0x900];assert len(template)==256;f.m.load(0xA00,template);oldflags=f.get('se_bc_flags',1)|64;f.put('se_bc_flags',oldflags,1);f.m.lib.zeropage_peddle_set_pc(f.m.handle,0xA00)
  for steps in range(3000):
   if f.m.regs().pc==f.s['se_doc_invalidate']:break
   f.m.lib.zeropage_peddle_step_instruction(f.m.handle)
  else:raise AssertionError('resume revoke prefix did not reach actualdocinvalidate')
  assert f.get('se_bc_flags',1)==oldflags&~64 and f.merged()==data
  record.append(dict(case='actual-private-C29-resume-prefix',instructions=steps,flags_before=oldflags,flags_after=f.get('se_bc_flags',1),scope='revocationprefix through actualunverify, before doc_invalidate; no fullsnapshotclaim'))
  # Only one R19 immediate differs; all remaining strict API code is exact.
  ctrl=(out/'R19-control/image.bin').read_bytes();new=(out/'R19/image.bin').read_bytes();diff=[i for i,(a,b)in enumerate(zip(ctrl,new))if a!=b]
  assert len(diff)==1 and ctrl[diff[0]]==0xEF and new[diff[0]]==0xAF
  from peddle import Machine
  policy=[]
  for variant in ('R19-control','R19'):
   labels={a[2].lstrip('.'):int(a[1],16)for ln in(out/variant/'image.lbl').read_text().splitlines()if len(a:=ln.split())==3}
   m=Machine();m.load(0xA000,(out/variant/'image.bin').read_bytes());accepted=[]
   try:
    for flags in range(256):
     for queue in (0,1):
      m.write(f.s['se_bc_flags'],flags);m.write(f.s['se_bc_count'],queue);m.write(0x1FE,0xFE);m.write(0x1FF,2)
      for field,value in [('pc',labels['gsc_cached_carry']),('sp',0xFD),('p',0x24)]:getattr(m.lib,'zeropage_peddle_set_'+field)(m.handle,value)
      for i in range(50):
       pc=m.regs().pc
       if pc in (f.s['se_crc_init'],0x2FF):break
       m.lib.zeropage_peddle_step_instruction(m.handle)
      else:raise AssertionError('R19flagpolicy did not decide')
      ok=m.regs().pc==f.s['se_crc_init'];expect=queue==0 and flags in((33,49)if variant=='R19-control'else(33,49,97,113));assert ok==expect,(variant,flags,queue)
      if ok:accepted.append(flags)
   finally:m.close()
   policy.append(dict(variant=variant,cases=512,accepted=accepted,scope='actual compiled pre-CRC flag gate only; rest of R19 byteidentical'))
  record.append(dict(case='private-R19-defined-mask',payload_differences=diff,policies=policy))
  # Unmodified current53 renderer with the same extra checked import provides
  # an actual same-public-command comparator; no single-frame cache seed.
  control=geos.Fixture(out,base,dll,True)
  try:
   control.assets['layoutmemo']=images['layoutmemo'];control.source(data);control.command(99);start=control.total_instructions;control.render();controlA=control.total_instructions-start
   control.command(35);start=control.total_instructions;control.render();controlB=control.total_instructions-start
   control.command(34);start=control.total_instructions;control.render();controlReturn=control.total_instructions-start
   assert control.read(0x6000,8000)==bits and control.read(0x4000,1000)==attrs and control.merged()==data and control.get('se_v_top')==0
  finally:control.close()
  record.append(dict(case='same-public-sequence-current53-control',A=controlA,B=controlB,return_A=controlReturn,candidate_B_plus_return=costB+costReturn,control_B_plus_return=controlB+controlReturn,candidate_all3=costA+costB+costReturn,control_all3=controlA+controlB+controlReturn,scope='render intervals only; both use actual E_BOTTOM/E_TOP, no physicaltimeclaim'))
  result=dict(status='passed-private-public-revisit-and-revocation',fit=fit,cases=record,source_bytes=len(data),full_REU_bytes=16777216,scope='ActualC21/R34hook andpublicBOTTOM/TOP; no manualFE/TOP seed; privateC29prefix only',promotion=False)
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--run',action='store_true');a=p.parse_args();out=ROOT/'build/cache-layout-hook'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);images,result=build_pair(out,a.fixture.resolve());print(json.dumps(result,indent=2),flush=True)
 if a.run:print(json.dumps(run_public(out,a.fixture.resolve(),images,result),indent=2))
