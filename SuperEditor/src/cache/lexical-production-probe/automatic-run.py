"""Private actual parent-window automatic construction, no host begin/link."""
from pathlib import Path
import importlib.util,json,sys,binascii
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_lexical_production as prior
import test_cache_lexical as lexical
from overlays import wrap
geos=prior.geos;plain=prior.plain;F=0x8d00
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class Fixture(geos.Fixture):
 def settle(self,error=0,render=False):
  if getattr(self,'job_budget',25000)==25000:return super().settle(error,render)
  steps=0
  while self.get('se_e_job',1):
   self.call('se_editor_service');steps+=1
   assert steps<self.job_budget,('private total-job budget',self.get('se_e_job',1),self.get('se_e_error',1))
  super().settle(error,render);return steps
 def call(self,name,a=0):
  if name!='se_editor_service':return super().call(name,a)
  job=self.get('se_e_job',1);q=self.m.read(0x9135);op=self.m.read(0x9136);cs=self.m.read(0x9096);flags=self.get('se_bc_flags',1)
  r=super().call(name,a)
  if job==11 and q in (25,45,47,49):
   item=(q,op,cs,flags,r.a,r.p&1,self.m.read(0x9135),self.m.read(0x9136),self.m.read(0x9096),self.m.read(F+4),self.m.read(F+2),self.m.read(0x9096+24),self.m.read(0x9096+26))
   self.trace=getattr(self,'trace',[])+[item]
  return r

def run(out,base,build_only=False,faults_only=False,costs_only=False):
 out.mkdir(parents=True);frozen,identity=geos.freeze(out,base)
 b,l,budget=module('automatic_profile_builder',Path(__file__).with_name('automatic-build.py')).build(out/'automatic',frozen)
 if build_only:return
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out)
 f=Fixture(out,frozen,dll,True);g=Fixture(out,frozen,dll,True);frames=[]
 digest=bytes.fromhex(json.load(open(frozen/'build/editor-report.json'))['resident_binding']['digest']);api=f.s['se_overlay_call'],f.s['se_overlay_frame']
 assignments=[('lexgate45','gateway',1,45),('lexresolve36','resolver',0,36),('lexpage37','roles',0,37),('lexproducer47','producer',1,47),('lexlink49','writer',1,49),('inln','query',1,35),('page','forward',1,37),('geospage','page',1,21),('line','inline',1,39),('rangeio','rangeio',0,19),('fold','arena-writer',0,33)]
 for x in(f,g):
  for name,key,slot,id_ in assignments:x.assets[name]=wrap(b[key],slot,id_,api=api,binding_digest=digest)
 f.assets['geoslex']=wrap(b['strict'],1,25,api=api,binding_digest=digest)
 fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
 def arena(x,reu):
  token=x.read(x.s['se_bc_arena'],5);assert x.m.read(x.s['object_owner']+token[0])==0x53
  logical=x.m.read(x.s['object_extents']+token[0]*16);bank=x.m.read(x.s['se_reu_map']+logical)
  assert x.m.read(x.s['se_reu_logical_owner']+logical)==0x53 and x.m.read(x.s['se_reu_physical_owner']+bank)==0x53
  lo=bank*65536
  roots=[(i,reu[lo+i:lo+i+128])for i in(0,128)if reu[lo+i:lo+i+6]==b'BCA1\1\1']
  roots=[(i,r)for i,r in roots if int.from_bytes(r[119:121],'little')==binascii.crc_hqx(r[:5]+r[6:119]+r[121:],65535)]
  i,r=max(roots,key=lambda pair:int.from_bytes(pair[1][18:22],'little'));return lo,i,r
 def check(x,data,tag,construct=False):
  before=x.reu();lo,selected,root=arena(x,before);canon=x.canonical();catalog=x.catalog();x.trace=[]
  start=x.total_instructions;loads=x.get('se_overlay_loads',2)
  dll.gm_profile(x.s['se_overlay_active']+1,list(x.assets).index('lexproducer47')+1,list(x.assets).index('geoslex')+1,l['producer']['se_sl_feed'],0,0,(l['strict']['se_sl_feed']if x is f else l['fallback']['se_sl_feed']))
  x.typed(geos.native_text('syntax full'));x.render()
  producer_feeds=dll.gm_metric(0);strict_feeds=dll.gm_metric(2);dll.gm_profile(0,0,0,0,0,0,0)
  after=x.reu();lo2,sel2,r2=arena(x,after);assert lo==lo2
  bits,attrs,rows=plain.expected(x,data,fonts,3)
  assert x.read(0x6000,8000)==bits and x.read(0x4000,1000)==attrs,(tag,'independent pixels')
  assert x.canonical()==canon and x.catalog()==catalog and x.merged()==data and x.read(0xc600,1024)==x.shim
  wanted=bytearray(before);cache,bank=x.raw_cache();fe=bank*65536
  for a,z in [(0,64),(0x200,0xEA88)]:wanted[fe+a:fe+z]=after[fe+a:fe+z]
  newpages=[]
  for page in range(1,16):
   at=lo+256+page*8
   if before[at:at+8]!=after[at:at+8]:
    assert before[at:at+8]==bytes(8),'old reachable directory changed'
    newpages.append(page);wanted[at:at+8]=after[at:at+8]
    a=lo+page*4096;wanted[a:a+4096]=after[a:a+4096]
  if construct:
   assert root[31]==1 and r2[31]==5 and r2[98]==1 and len(newpages)==2,(tag,'genuine automatic publication',r2[31],newpages,x.trace[:15],x.trace[-10:])
   assert sel2!=selected and after[lo+selected:lo+selected+128]==before[lo+selected:lo+selected+128]
   wanted[lo+sel2:lo+sel2+128]=after[lo+sel2:lo+sel2+128]
   assert any(t[0:2]==(47,0)for t in x.trace) and any(t[0:2]==(49,0)for t in x.trace),'actual foreground producer/linker'
   body=data.index(geos.native_text('10 PRINT'if b'basic' in data.lower()else'label'))
   end=data.index(13,body)
   assert producer_feeds==end-body and strict_feeds==0,('actualBODYonce',producer_feeds,end-body,strict_feeds)
  else:assert not newpages and after[lo:lo+65536]==before[lo:lo+65536]
  assert after==wanted,(tag,'whole16MiB outside new page/directory/alternate root/sourceFE')
  assert not any(x.get(n,1)for n in ('se_e_error','se_f_owner','se_e_job','se_doc_read_locks','se_fs_owned'))
  assert not x.get('se_bc_flags',1)&8,'ACTIVE must be released'
  geos.png(bits,attrs,out/(tag+'.png'))
  row=dict(tag=tag,instructions=x.total_instructions-start,loads=(x.get('se_overlay_loads',2)-loads)&65535,root_flags=r2[31],new_pages=newpages,producer_feeds=producer_feeds,strict_feeds=strict_feeds,worker_begins=sum(t[0:2]==(47,0)for t in x.trace),linker_begins=sum(t[0:2]==(49,0)for t in x.trace),gateway_calls=sum(t[0]==45 for t in x.trace),trace=x.trace)
  frames.append(row);(out/(tag+'-trace.json')).write_text(json.dumps(row,indent=2)+'\n');print('AUTO_FRAME_PASS',{k:v for k,v in row.items()if k!='trace'},flush=True)
 try:
  configs=([('basic',238,'basic-256'),('basic',494,'basic-512'),('basic',750,'basic-768')]if costs_only else[('basic',980,'basic'),('asm',980,'asm')])
  for language,fill,tag in ([]if faults_only else configs):
   data=geos.native_text('Intro\r:::'+language+'\r'+('10 PRINT "Hi":REM 'if language=='basic'else'label lda #42 ; '))+geos.native_text('x')*fill+geos.native_text('\r:::\rTail.')
   for x in(f,g):x.source(data);x.typed(geos.native_text('syntax markdown'));x.command(99);x.render()
   check(f,data,tag+'-automatic-first',fill>=750);check(g,data,tag+'-packaged-C25-control')
   if costs_only:continue
   for x in(f,g):x.key(0x8a);x.key(0x8a)
   check(f,data,language+'-automatic-warm');check(g,data,language+'-packaged-warm-control')
  fault_groups=[]if costs_only else module('automatic_fault_qualification',Path(__file__).with_name('automatic-faults.py')).qualify(f,g,dll,b,l,fonts,out,geos,plain,arena)
  result=dict(fault_groups=fault_groups,status='PASS-automatic-parent',budget=budget,frames=[{k:v for k,v in r.items()if k!='trace'}for r in frames],scope='Private IDs C45/R36/R37/C47/C49; actual C25 public window initiates producer and COW linker without host begin/link. Private bit128 only, first eligible CR per baseline; no canonical or hardware claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('AUTO_PASS',result,flush=True)
 except BaseException:
  (out/'failed-trace.json').write_text(json.dumps(getattr(f,'trace',[]),indent=2)+'\n');(out/'failed-ram.bin').write_bytes(f.read(0,65536));(out/'failed-reu.bin').write_bytes(f.reu());raise
 finally:f.close();g.close()
