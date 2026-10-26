"""Private production-ID lexical milestones. No canonical/shared output writes.

First milestone: genuine root5 with long sparse prose, real C39 SOURCE reuse.
Producer/link setup is explicit here and is NOT an automatic product trigger.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_lexical as lexical
import test_cache_lexical_link as link
import test_plain_geos as plain
from overlays import wrap
geos=lexical.geos;BASE=link.BASE;F=0x8d00
spec=importlib.util.spec_from_file_location('production_probe_builder',ROOT/'src/cache/lexical-production-probe/build.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

class Fixture(geos.Fixture):
 def job(self,id_,slot,op):
  self.put('se_overlay_frame',op,1);r,n=self.fast_call(self.s['se_overlay_call'],a=id_,x=slot);self.total_instructions+=n;return r
 def call(self,name,a=0):
  request=self.m.read(0x9135)if name=='se_editor_service' else 0
  op=self.m.read(0x9136)if name=='se_editor_service' else 0
  r=super().call(name,a)
  if request==39:self.trace=getattr(self,'trace',[])+[(request,op,self.m.read(0x9135),self.m.read(0x9136))]
  return r

def run(out,base,build_only=False):
 out.mkdir(parents=True);frozen,identity=geos.freeze(out,base)
 binaries,ls,budget=builder.build(out/'adapter',frozen)
 worker,wl,wb=lexical.build(out/'producer',frozen);page,pl,pb=lexical.build_page(out/'page',frozen);writer,ll,lb=link.build(out/'link',frozen)
 if build_only:return
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out)
 f=Fixture(out,frozen,dll,True);g=Fixture(out,frozen,dll,True);frames=[]
 digest=bytes.fromhex(json.load(open(frozen/'build/editor-report.json'))['resident_binding']['digest']);api=(f.s['se_overlay_call'],f.s['se_overlay_frame'])
 for x in(f,g):
  # All original eplay/lifecycle/gtype/line assets retain their proper meaning.
  for name,raw,slot,id_ in [('lexproducer47',worker,1,47),('lexpage37',page,0,37),('lexlink49',writer,1,49),('inln',binaries['query'],1,35),('page',binaries['forward'],1,37),('geospage',binaries['page'],1,21)]:x.assets[name]=wrap(raw,slot,id_,api=api,binding_digest=digest)
 f.assets['line']=wrap(binaries['inline-lexcap'],1,39,api=api,binding_digest=digest)
 fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
 def drive(x,id_,slot):
  for i in range(20000):
   r=x.job(id_,slot,1)
   if r.p&1 or r.a!=1:return r,i+1
  raise AssertionError('boundedsteps')
 def setup(x,data,target):
  x.source(data);x.command(99);x.render();assert x.get('se_bc_flags',1)&15==1
  for n in ('se_i_ready','se_i_count','se_n_cache_count'):x.put(n,0,1)
  x.put('se_f_owner',4,1);x.m.write(0x8b55,0);x.m.load(0x8b40,target.to_bytes(3,'little'));r=x.job(35,1,0)
  while r.a==1 and not r.p&1:r=x.job(35,1,1)
  assert not r.p&1 and not r.a and x.m.read(0x8b45)==5,('actualcodeCR',r.a,r.p)
  before=x.total_instructions;loads=x.get('se_overlay_loads',2)
  assert not x.job(47,1,0).p&1;assert not x.job(37,0,0).p&1;r,_=drive(x,37,0);assert not r.p&1 and not r.a
  while True:
   r=x.job(47,1,1);assert not r.p&1
   if x.m.read(F+4)==1:assert not x.job(37,0,3).p&1;x.job(47,1,3)
   elif x.m.read(F+4)==2:
    x.job(37,0,5);r,_=drive(x,37,0);assert not r.p&1 and not r.a;x.job(47,1,3);break
  assert not x.job(49,1,0).p&1;r,_=drive(x,49,1);assert not r.p&1 and not r.a
  token=x.read(x.s['se_bc_arena'],5);assert x.m.read(x.s['object_owner']+token[0])==0x53
  logical=x.m.read(x.s['object_extents']+token[0]*16);bank=x.m.read(x.s['se_reu_map']+logical);reu=x.reu();root=max((reu[bank*65536+i:bank*65536+i+128]for i in(0,128)if reu[bank*65536+i+5]==1),key=lambda r:int.from_bytes(r[18:22],'little'));assert root[31]==5 and root[98]==1
  x.put('se_f_owner',0,1);return dict(instructions=x.total_instructions-before,loads=(x.get('se_overlay_loads',2)-loads)&65535,arena_bank=bank)
 def check(x,data,tag):
  canon=x.canonical();catalog=x.catalog();before=x.reu();start=x.total_instructions;loads=x.get('se_overlay_loads',2);x.trace=[]
  dll.gm_profile(x.s['se_overlay_active']+1,list(x.assets).index('geosinln')+1,0,ls['c26']['se_si_feed'],0,0,0)
  x.key(0x8a);x.key(0x8a);x.render();feeds=dll.gm_metric(0);dll.gm_profile(0,0,0,0,0,0,0)
  bits,attrs,rows=plain.expected(x,data,fonts,3);assert x.read(0x6000,8000)==bits and x.read(0x4000,1000)==attrs
  cache,bank=x.raw_cache();after=x.reu();wanted=bytearray(before);lo=bank*65536
  for a,b in [(0,64),(0x200,0xEA88)]:wanted[lo+a:lo+b]=after[lo+a:lo+b]
  assert after==wanted,'whole16MiB outside existing sourceFE/wholetyped53readonly'
  assert x.canonical()==canon and x.catalog()==catalog and x.merged()==data and x.read(0xc600,1024)==x.shim
  assert not any(x.get(n,1)for n in('se_e_error','se_f_owner','se_e_job','se_doc_read_locks'))
  hits=sum(t[2:]==(20,1)for t in x.trace);miss=sum(t[2:]==(26,5)for t in x.trace)
  geos.png(bits,attrs,out/(tag+'.png'));record=dict(tag=tag,instructions=x.total_instructions-start,loads=(x.get('se_overlay_loads',2)-loads)&65535,inline_feeds=feeds,source_hits=hits,source_fallbacks=miss,rows=len(rows),trace=x.trace);frames.append(record);print('FRAME_PASS',record,flush=True);return record
 try:
  for language in('basic','asm'):
   prose=geos.native_text('Sparse **bold** text ')+geos.native_text('alpha ')*850+geos.native_text(' and *last*.')
   code=geos.native_text('10 PRINT "Hi":REM ' if language=='basic'else'label lda #42 ; ')+geos.native_text('x')*980
   data=prose+geos.native_text('\r:::'+language+'\r')+code+geos.native_text('\r:::\rTail.')
   target=len(prose)+len(geos.native_text('\r:::'+language+'\r'))
   construction=[setup(x,data,target)for x in(f,g)]
   a=check(f,data,language+'-root5-C39-mask');b=check(g,data,language+'-root5-old-C39-control')
   assert a['source_hits']>0 and a['source_fallbacks']==0 and a['inline_feeds']==0,('genuineC39reuse',a)
   assert b['source_fallbacks']>0 and b['inline_feeds']>0 and b['source_hits']==0,('oldkindcontrol',b)
   print('COEXISTENCE_PASS',language,'source',len(data),'proseBODY',len(prose),'construction',construction,flush=True)
  result=dict(status='PASS-mixed-root5',budget=budget,frames=frames,scope='Actual C39 SOURCE reuse under genuine root5, long sparse prose+BASIC/ASM. Assigned C47/R37/C49 imports; explicit component setup is not an automatic trigger. Entiretyped53 readonly in parentintervals; no canonical/Git/native changes.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',result,flush=True)
 except BaseException:
  (out/'failed-ram.bin').write_bytes(f.read(0,65536));(out/'failed-reu.bin').write_bytes(f.reu());raise
 finally:f.close();g.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--build-only',action='store_true');p.add_argument('--auto',action='store_true');p.add_argument('--auto-faults-only',action='store_true');p.add_argument('--auto-costs-only',action='store_true');a=p.parse_args();out=ROOT/('build/cache-lexical-automatic'if a.auto else'build/cache-lexical-production')/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True)
 if a.auto:
  s=importlib.util.spec_from_file_location('private_automatic_qualification',ROOT/'src/cache/lexical-production-probe/automatic-run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.run(out,a.fixture.resolve(),a.build_only,a.auto_faults_only,a.auto_costs_only)
 else:run(out,a.fixture.resolve(),a.build_only)
