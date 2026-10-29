"""Private genuine59 build/packaged startup and automatic lexical registration.

All assets come from the real privately rebuilt D81. The CPU runner has only
its established ROM IEC import/font and chargen-read seams; no capsule, parser
result, CR reference, producer BEGIN, or linker BEGIN is substituted/seeded.
This is not native, hardware, final lifecycle, or canonical registration proof.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_lexical_production as production
from d81_image import D81Image
geos=production.geos;plain=production.plain

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
builder=module('registration_source_builder',ROOT/'src/cache/lexical-registration-probe/build.py')
automatic=module('sealed_automatic_runtime',ROOT/'src/cache/lexical-production-probe/automatic-run.py')
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def labels(path):
 return {p[2].lstrip('.'):int(p[1],16)for line in path.read_text().splitlines()if len(p:=line.split())==3 and p[0]=='al'}

def arena(x,reu):
 token=x.read(x.s['se_bc_arena'],5);assert x.m.read(x.s['object_owner']+token[0])==0x53
 logical=x.m.read(x.s['object_extents']+token[0]*16);bank=x.m.read(x.s['se_reu_map']+logical)
 assert x.m.read(x.s['se_reu_logical_owner']+logical)==x.m.read(x.s['se_reu_physical_owner']+bank)==0x53
 lo=bank*65536;roots=[]
 for at in(0,128):
  r=reu[lo+at:lo+at+128]
  if r[:6]==b'BCA1\1\1'and int.from_bytes(r[119:121],'little')==binascii.crc_hqx(r[:5]+r[6:119]+r[121:],65535):roots.append((at,r))
 assert roots;at,r=max(roots,key=lambda p:int.from_bytes(p[1][18:22],'little'));return lo,at,r

def run(out,project,base,bypass=False,mixed=False,faults=False):
 out.mkdir(parents=True);frozen,identity=builder.freeze_project(project,out/'fixture',base)
 assert len(identity['names'])==59
 disk=D81Image((frozen/'build/supereditor.d81').read_bytes())
 for n in identity['names']:assert disk.read(n.upper().encode(),kind=1).data==(frozen/f'build/overlays/{n}.seo').read_bytes()
 assert len(set((disk.read(n.upper().encode(),kind=1).data[5],disk.read(n.upper().encode(),kind=1).data[6])for n in identity['names']))==59
 # Every actual cold filename is decoded by the real startup loop. Only the
 # ROM transport is supplied bytes already compared with the packaged D81.
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 import font_fixture
 font_fixture.ROOT=frozen
 original=geos.grid.cpu_editor.startup;imports=[]
 def cold(*args,**kw):
  receipt=original(*args,**kw);imports.append(receipt);return receipt
 geos.grid.cpu_editor.startup=cold
 dll=geos.grid.runner(out);f=None;frames=[]
 try:
  class RegisteredFixture(automatic.Fixture):
   def call(self,name,a=0):
    q=self.m.read(0x9135)if name=='se_editor_service'and self.get('se_e_job',1)==11 else 0
    op=self.m.read(0x9136)if q==39 else 0
    r=super().call(name,a)
    if q==39:self.source_trace=getattr(self,'source_trace',[])+[(q,op,self.m.read(0x9135),self.m.read(0x9136))]
    return r
  f=RegisteredFixture(out,frozen,dll,True);assert imports==[identity['names']]
  assert sum(f.m.read(f.s['se_overlay_ids']+i)!=0 for i in range(f.s['se_overlay_capacity']))==59
  # Actual catalog remains64 entries, with publication53..58 retaining exact
  # identity fields under managed verification-bit normalization only.
  catalog=f.catalog();cold_ids=[f.m.read(f.s['se_overlay_ids']+i)for i in range(59)]
  assert cold_ids==[(frozen/f'build/overlays/{n}.seo').read_bytes()[6]for n in identity['names']]
  code_handles=f.read(f.s['se_overlay_asset'],4)
  assert len(set(code_handles))==4 and all(h and f.m.read(f.s['se_reu_logical_owner']+h)==2 and f.m.read(f.s['se_reu_physical_owner']+f.m.read(f.s['se_reu_map']+h))==2 for h in code_handles)
  startup=dict(names=imports[0],code_handles=list(code_handles),code_banks=4,catalog_sha256=sha(catalog),catalog_count=sum(f.m.read(f.s['se_overlay_ids']+i)!=0 for i in range(f.s['se_overlay_capacity'])),catalog_capacity=f.s['se_overlay_capacity'],readyos_sha256=sha(f.read(0xc600,1024)))
  (out/'startup.json').write_text(json.dumps(startup,indent=2)+'\n');print('COLD59_PASS',startup['catalog_count'],flush=True)
  fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
  prod=labels(project/'build/lexical/ical.lbl');strict=labels(project/'build/overlays/geoslex.lbl')
  def check(data,tag,construct=False,source_hits=False,caps=3):
   before=f.reu();lo,selected,root=arena(f,before);canon=f.canonical();cat=f.catalog();f.trace=[]
   start=f.total_instructions;loads=f.get('se_overlay_loads',2);f.source_trace=[]
   dll.gm_profile(f.s['se_overlay_active']+1,list(f.assets).index('ical')+1,list(f.assets).index('geoslex')+1,prod['se_sl_feed'],0,0,strict['se_sl_feed'])
   f.typed(geos.native_text({3:'syntax full',1:'syntax markdown',0:'syntax plain'}[caps]));f.render()
   pf,sf=dll.gm_metric(0),dll.gm_metric(2);dll.gm_profile(0,0,0,0,0,0,0)
   after=f.reu();lo2,sel2,r2=arena(f,after);assert lo2==lo
   bits,attrs,rows=plain.expected(f,data,fonts,caps)
   assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'independent320x200+1000')
   assert f.canonical()==canon and f.catalog()==cat and f.merged()==data and f.read(0xc600,1024)==f.shim
   wanted=bytearray(before);_,bank=f.raw_cache();fe=bank*65536
   for a,b in [(0,64),(0x200,0xEA88)]:wanted[fe+a:fe+b]=after[fe+a:fe+b]
   pages=[]
   for page in range(1,16):
    at=lo+256+page*8
    if before[at:at+8]!=after[at:at+8]:
     assert before[at:at+8]==bytes(8),'reachable old directory changed'
     pages.append(page);wanted[at:at+8]=after[at:at+8];a=lo+page*4096;wanted[a:a+4096]=after[a:a+4096]
   if construct:
    assert root[31]==1 and r2[31]==5 and r2[98]==1 and len(pages)==2 and sel2!=selected
    assert before[lo+selected:lo+selected+128]==after[lo+selected:lo+selected+128]
    wanted[lo+sel2:lo+sel2+128]=after[lo+sel2:lo+sel2+128]
    assert any(t[:2]==(47,0)for t in f.trace)and any(t[:2]==(49,0)for t in f.trace),('actualC47C49',f.trace)
    body=data.index(geos.native_text('10 PRINT'if b'basic'in data.lower()else'label'));end=data.index(13,body)
    assert pf==end-body and sf==0,('BODYonce',pf,end-body,sf)
   else:assert not pages and after[lo:lo+65536]==before[lo:lo+65536]
   assert after==wanted,(tag,'outside exact new2pages/dir8/alternate128/sourceFE')
   assert not any(f.get(n,1)for n in('se_e_error','se_f_owner','se_e_job','se_doc_read_locks','se_fs_owned'))
   assert not f.get('se_bc_flags',1)&8
   geos.png(bits,attrs,out/(tag+'.png'))
   r=dict(tag=tag,instructions=f.total_instructions-start,loads=(f.get('se_overlay_loads',2)-loads)&65535,producer_feeds=pf,strict_feeds=sf,root_flags=r2[31],new_pages=pages,rows=len(rows),worker_begins=sum(t[:2]==(47,0)for t in f.trace),linker_begins=sum(t[:2]==(49,0)for t in f.trace),source_hits=sum(t[2:]==(20,1)for t in f.source_trace),source_fallbacks=sum(t[2:]==(26,5)for t in f.source_trace))
   frames.append(r);(out/(tag+'-trace.json')).write_text(json.dumps(f.trace,indent=2)+'\n');print('PACKAGED_FRAME_PASS',r,flush=True)
   return r
  for language in('basic','asm'):
   data=geos.native_text('Intro\r:::'+language+'\r'+('10 PRINT "Hi":REM 'if language=='basic'else'label lda #42 ; '))+geos.native_text('x')*980+geos.native_text('\r:::\rTail.')
   f.source(data);f.typed(geos.native_text('syntax markdown'));f.command(99);f.render()
   check(data,language+'-first',True)
   f.key(0x8a);f.key(0x8a);warm=check(data,language+'-warm');assert warm['producer_feeds']==warm['strict_feeds']==warm['worker_begins']==warm['linker_begins']==0
   if bypass:
    check(data,language+'-plain',caps=0);check(data,language+'-markdown',caps=1)
  if mixed:
   for language in('basic','asm'):
    data=geos.native_text('Intro\r:::'+language+'\r'+('10 PRINT "Hi":REM 'if language=='basic'else'label lda #42 ; '))+geos.native_text('x')*980+geos.native_text('\r:::\rSparse **bold** ')+geos.native_text('alpha ')*850+geos.native_text(' and *last*.')
    f.source(data);f.typed(geos.native_text('syntax markdown'));f.command(99);f.command(77);f.render()
    check(data,language+'-mixed-root5-first',True)
    f.key(0x8a);f.key(0x8a);r=check(data,language+'-mixed-root5-warm')
    assert r['source_hits']>0 and r['source_fallbacks']==0 and r['producer_feeds']==r['strict_feeds']==0,('root5genuineC39SOURCE',r)
  fault_groups=[]
  if faults:
   # Reuse the first nine published automatic fault gates unmodified: actual
   # four STOP phases + five missing-worker admissions. Later component fault
   # groups are already sealed; no claim to rerun them in this registration.
   import inspect
   fm=module('registered_component_faults',ROOT/'src/cache/lexical-production-probe/automatic-faults.py')
   source=inspect.getsource(fm.qualify);cut=source.index(' # A changed live source/typed authority')
   source=source[:cut]+' return groups\n';namespace=dict(fm.__dict__);exec(compile(source,str(Path(__file__))+':packaged-nine-faults','exec'),namespace)
   fault_groups=namespace['qualify'](f,None,dll,None,None,fonts,out,geos,plain,arena);assert len(fault_groups)==9
  result=dict(status='PASS-packaged59',identity=identity,startup=startup,frames=frames,fault_groups=fault_groups,maximum_service_instructions=f.max_service,scope='Real private resident+59source-built capsules+D81; actual startup decoded all59; real publicC25 automaticC45/C47/C49 trigger. No hostBEGIN/link/reference/capsule substitutions. Native/physical/lifecycle/staticstack remain separate.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS_PACKAGED59',flush=True)
 except BaseException:
  if f:
   (out/'failed-trace.json').write_text(json.dumps(getattr(f,'trace',[]),indent=2)+'\n');(out/'failed-ram.bin').write_bytes(f.read(0,65536));(out/'failed-reu.bin').write_bytes(f.reu())
  raise
 finally:
  geos.grid.cpu_editor.startup=original
  if f:f.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--fixture',type=Path,default=builder.BASE);p.add_argument('--bypass',action='store_true');p.add_argument('--mixed',action='store_true');p.add_argument('--faults',action='store_true');a=p.parse_args()
 out=ROOT/'build/cache-lexical-registered'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.project.resolve(),a.fixture.resolve(),a.bypass,a.mixed,a.faults)
