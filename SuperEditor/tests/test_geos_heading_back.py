"""Private inverse-heading BACK gate; actual public editor and forced full renderer."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_semantic_editor as semantic
geos=semantic.geos;D=ROOT/'src/render/geos/heading-back-candidate'
BASE=ROOT/'build/geos-incremental-editor/20261025T133435860867Z/fixture'
STATE=0x9149

def run(out,base,variant,smoke=False,packaged=False,diverse=False):
 if packaged:
  assert variant=='candidate'
  raw=(base/'build/overlays/geosdelta.seo').read_bytes();budget=dict(packaged_R28=len(raw)-36,sha256=hashlib.sha256(raw).hexdigest());private=base
 else:
  spec=importlib.util.spec_from_file_location('heading_back_build',D/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);images,budget=b.build(out/'link',base)
  private=out/'private-input';shutil.copytree(base,private);(private/'build/overlays/geosdelta.seo').write_bytes(images[variant]);identity=json.loads((private/'freeze.json').read_text());identity['assets']['geosdelta']=hashlib.sha256(images[variant]).hexdigest();(private/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 frozen,identity=geos.freeze(out,private);geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out)
 f=geos.Fixture(out,frozen,dll,True);g=geos.Fixture(out,frozen,dll,True);fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)};frames=[];data=b''
 def setup(raw,at=0):
  nonlocal data
  data=bytes(raw)
  for x in(f,g):x.source(data);x.command(99);x.position(at);x.render()
 def check(tag,incremental):
  canonical=f.canonical();before=f.reu();catalog=f.catalog();start=f.total_instructions;loads=f.get('se_overlay_loads',2)
  f.render();used=f.total_instructions-start;g.m.write(0xcfe8,0);g.m.write(0xcf90,0);start=g.total_instructions;g.render();fullused=g.total_instructions-start
  fast=f.m.read(STATE+0) #transaction phase must be complete
  assert fast==0,(tag,'unfinishedR28phase',fast)
  # C21's FAST_PAINT remains2 only after a successful bounded row transaction.
  actual=f.m.read(0x9148)==2
  assert actual==incremental,(tag,'incremental',actual,incremental,f.read(0x9134,68).hex())
  assert f.canonical()==canonical and f.catalog()==catalog and f.merged()==data==g.merged(),(tag,'source/history/catalog')
  bits,attrs,rows,sem=semantic.expected(f,data,fonts)
  assert f.read(0x6000,8000)==bits==g.read(0x6000,8000),(tag,'independent/fullbitmap')
  assert f.read(0x4000,1000)==attrs==g.read(0x4000,1000),(tag,'independent/fullattrs')
  # Retain public verifier's complete canonical source/bottom/anchor geometry.
  cache,bank=f.cache();assert cache[0]==1 and cache[1]==len(rows)
  for i,row in enumerate(rows):
   p=cache[0x200+i*0x800:0x220+i*0x800];assert int.from_bytes(p[:3],'little')==row.start and int.from_bytes(p[3:6],'little')==row.end and int.from_bytes(p[6:9],'little')==row.next and int.from_bytes(p[9:12],'little')==row.start and int.from_bytes(p[12:14],'little')==row.end-row.start and p[14]==row.height and p[15]==row.top,(tag,'allrows',i,row,p.hex())
  assert f.get('se_v_bottom')==rows[-1].next
  assert f.read(0xc600,1024)==f.shim and all(f.get(n,1)==0 for n in ['se_f_owner','se_doc_read_locks','se_fs_owned'])
  handle=f.get('se_gc_handle',1);assert handle and bank and f.m.read(f.s['se_reu_logical_owner']+handle)==0xfe and f.m.read(f.s['se_reu_physical_owner']+bank)==0xfe
  now=f.reu();start=bank*65536;cursor=0
  for a,b in[(start,start+64),(start+0x200,start+0xe568)]:assert now[cursor:a]==before[cursor:a],(tag,'foreign/FEgap',cursor,a);cursor=b
  assert now[cursor:]==before[cursor:],(tag,'font/tail/foreignREU')
  geos.png(bits,attrs,out/(tag+'.png'));frames.append(dict(tag=tag,incremental=actual,instructions=used,full_instructions=fullused,loads=(f.get('se_overlay_loads',2)-loads)&65535,source_bytes=len(data),rows=[dict(start=r.start,end=r.end,next=r.next,top=r.top,height=r.height)for r in rows]));print('PASS',frames[-1]|{'rows':len(rows)},flush=True)
 def back(tag,expected=True):
  nonlocal data
  at=f.get('se_hot_caret');assert at>0
  data=data[:at-1]+data[at:]
  for x in(f,g):x.key(0x14)
  check(tag,expected and variant=='candidate')
 try:
  if diverse:
   import test_grid_editor_vice as doc
   setup(geos.native_text('Q')+doc.fixture(),1);back('back-diverse422')
  else:
   setup(geos.native_text('Q# Heading words.\rSecond plain row.\rTail.'),1);back('back-leading-heading')
  if not smoke:
   for level in range(1,7):
    setup(geos.native_text('Q'+'#'*level+' Heading words.\rNext row.\rTail.'),1);back('back-level-'+str(level))
   setup(geos.native_text('Q## Last heading at EOF'),1);back('back-eof')
   raw=geos.native_text('Prelude\rQ### Heading words.\rFollowing row.\rTail.');setup(raw,9);back('back-after-CR')
   # A real preceding region remains in the same parser carry state.
   setup(geos.native_text(':::region A\rQ# Heading\rbody\r:::end\rTail.'),13);back('back-heading-in-region')
   for tag,text,at in [
    ('ordinary','QOrdinary words\rTail.',1),('space',' # Heading words\rTail.',1),
    ('seven','Q####### Heading\rTail.',1),('no-space','Q#Heading\rTail.',1),
    ('bullet','Q* Bullet\rTail.',1),('inline','Q# **bold** words\rTail.',1),
    ('code',':::basic\rQ# Heading\r:::\rTail.',10),
    ('interior','Q# Heading words\rTail.',5),
    ('wrapped','Q# '+'Widewords '*25+'\rFollowing.\rTail.',1)]:
    setup(geos.native_text(text),at);back('fallback-'+tag,False)
   # DEL is forward-delete, not this strictly corrective BACK contract.
   setup(geos.native_text('Q# Heading words\rTail.'),0);data=data[1:]
   for x in(f,g):x.command(4)
   check('fallback-forward-delete',False)
   # Two observed pending edits cannot use a single-event row certificate.
   setup(geos.native_text('QQ# Heading words\rTail.'),2)
   for x in(f,g):x.key(0x14);x.key(0x14)
   data=data[2:];check('fallback-two-pending',False)
   # Existing forward transition remains optimized in both modules.
   setup(geos.native_text('# Heading words\rFollowing row.\rTail.'),0)
   data=geos.native_text('Q')+data
   for x in(f,g):x.key(geos.native_text('Q')[0])
   check('forward-still-optimized',True)
   # Fresh complete row after a real flush supports the inverse operation.
   for x in(f,g):x.typed(geos.native_text('goto 1'));x.command(2);x.render()
   back('back-after-forward-flush')
   faults=[('flags',22,b'\1'),('inline',23,b'\1'),('kind',16,b'\1'),('height',14,b'\10'),('top',15,b'\21'),('role',356,b'\2'),('style',194,b'\1'),('first',9,b'\1'),('raster',24,b'\1'),('reason',17,b'\0'),('count-high',13,b'\1'),('raw-alpha',32,b'Z')]
   for name,offset,value in faults:
    setup(geos.native_text('Q# Heading words\rFollowing row.\rTail.'),1)
    cache,bank=f.raw_cache();handle=f.get('se_gc_handle',1);row=cache[42];canonical=f.canonical();f.call('se_doc_invalidate');f.m.load(0x8000,value)
    for n,v,w in [('se_reu_logical',handle,1),('se_reu_offset',0x200+row*0x800+offset,2),('se_reu_length',len(value),2),('se_reu_c64',0x8000,2)]:f.put(n,v,w)
    assert not f.call('se_reu_copy',0).p&1 and f.canonical()==canonical
    back('malformed-'+name,False)
  result=dict(status='passed',packaged=packaged,variant=variant,identity=identity,budget=budget,frames=frames,pixels=len(frames)*64000,attributes=len(frames)*1000,whole_REU_guard=16777216,scope='PrivateR28 inverseBACK; actualC24/C20/root/fullrenderer/independentsemanticfont/source/history/allanchors. No nativeclaim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException as e:
  (out/'failure.json').write_text(json.dumps(dict(error=repr(e),frames=len(frames),source=list(data)))+'\n');(out/'failure-c64.bin').write_bytes(f.read(0,65536));raise
 finally:f.close();g.close()

def forward_regression(out,base):
 import inspect
 import test_geos_heading_transition as original
 original.D=D
 text=inspect.getsource(original.run)
 old="data=raw;check('fallback-restores-heading',False)"
 new="data=raw;check('fallback-restores-heading',variant=='candidate')"
 assert text.count(old)==1,'Review the sole inverse expected-path change'
 namespace=dict(vars(original));exec(compile(text.replace(old,new),str(Path(__file__))+'::inverse-path','exec'),namespace)
 (out/'private-predicate-update.json').write_text(json.dumps(dict(original_sha256=hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest(),old=old,new=new,scope='Only inverseBACK expectedpath changes; all original actualfull/source/pixel/REU checks unchanged.'),indent=2)+'\n')
 return namespace['run'](out,base,'candidate')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--variant',choices=['control','candidate'],default='candidate');p.add_argument('--smoke',action='store_true');p.add_argument('--forward-regression',action='store_true');p.add_argument('--packaged',action='store_true');p.add_argument('--diverse',action='store_true');a=p.parse_args();out=ROOT/'build/geos-heading-back'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 if a.forward_regression:forward_regression(out,a.fixture.resolve())
 else:run(out,a.fixture.resolve(),a.variant,a.smoke,a.packaged,a.diverse)
