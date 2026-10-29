"""Private C6 leading-star admission; actual public editor/full/source oracles.

Only C6 SEO is privately substituted. No staged capsule, glyph/style packet,
producer certificate or source edit is host-replaced. The forced-full comparison
only clears its derived edit/GCC witnesses before the actual renderer runs.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_semantic_editor as semantic
geos=semantic.geos
BASE=ROOT/'build/geos-incremental-editor/20261025T122004452115Z/fixture'
D=ROOT/'src/render/geos/style-leading-candidate'

def run(out,base,variant,packaged=False):
 if packaged:
  assert variant=='candidate','Packaged mode tests the actual promoted behavior, not the historical control'
  raw=(base/'build/overlays/window.seo').read_bytes();assert raw[5:7]==bytes([1,6]) and len(raw)-36<=4096
  budget=dict(packaged_C6=len(raw)-36,sha256=hashlib.sha256(raw).hexdigest());frozen=base
 else:
  spec=importlib.util.spec_from_file_location('leading_build',D/'build.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder);images,budget=builder.build(out/'link',base)
  frozen=out/'private-input';shutil.copytree(base,frozen);(frozen/'build/overlays/window.seo').write_bytes(images[variant]);identity=json.loads((frozen/'freeze.json').read_text());identity['assets']['window']=hashlib.sha256(images[variant]).hexdigest();(frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 frozen,identity=geos.freeze(out,frozen);geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out)
 f=geos.Fixture(out,frozen,dll,True);g=geos.Fixture(out,frozen,dll,True);fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)};frames=[];data=b''
 def setup(source,at):
  nonlocal data
  data=bytes(source)
  for x in(f,g):x.source(data);x.command(99);x.position(at);x.render()
 def check(tag,fast=None,worker=30,namespace=0x42,producer=None):
  if producer is not None:assert f.m.read(0x9149)==producer,(tag,'C6producer',f.m.read(0x9149),producer)
  before=f.reu();canonical=f.canonical();catalog=f.catalog();started=f.total_instructions;loads=f.get('se_overlay_loads',2)
  f.render();used=f.total_instructions-started
  g.m.write(0xcfe8,0);g.m.write(0xcf90,0);started=g.total_instructions;g.render();fullused=g.total_instructions-started
  active=f.get('se_overlay_active',1);actualworker=f.m.read(f.s['se_overlay_ids']+active-1)if active else 0;direct=actualworker in(30,31)
  if fast is not None:assert direct==fast,(tag,'directpath',actualworker,f.m.read(0x9149),fast)
  if fast:assert actualworker==worker and f.m.read(0xcbd5)==namespace,(tag,'worker/window',actualworker,f.m.read(0xcbd5))
  assert f.canonical()==canonical and f.catalog()==catalog and f.merged()==data==g.merged(),(tag,'canonical/catalog/source')
  bits,attrs,rows,sem=semantic.expected(f,data,fonts)
  assert f.read(0x6000,8000)==bits==g.read(0x6000,8000),(tag,'independent/fullpixels')
  assert f.read(0x4000,1000)==attrs==g.read(0x4000,1000),(tag,'independent/fullattrs')
  assert f.read(0xc600,1024)==f.shim and all(f.get(n,1)==0 for n in ['se_f_owner','se_doc_read_locks','se_fs_owned']),(tag,'lease/shim')
  handle=f.get('se_gc_handle',1);bank=f.m.read(f.s['se_reu_map']+handle);assert handle and bank and f.m.read(f.s['se_reu_logical_owner']+handle)==0xfe and f.m.read(f.s['se_reu_physical_owner']+bank)==0xfe
  now=f.reu();cursor=0;base=bank*65536
  # Same declared active FE spans as the existing public styled-typing gate;
  # font table, cache tail and all canonical/history/other banks stay exact.
  for a,b in [(base,base+64),(base+0x200,base+0xe568)]:assert now[cursor:a]==before[cursor:a],(tag,'foreign/FEgapREU',cursor,a);cursor=b
  assert now[cursor:]==before[cursor:],(tag,'font/cachetail/otherREU')
  geos.png(bits,attrs,out/(tag+'.png'));frames.append(dict(tag=tag,source_bytes=len(data),direct=direct,worker=actualworker,namespace=f.m.read(0xcbd5),instructions=used,full_instructions=fullused,loads=(f.get('se_overlay_loads',2)-loads)&65535,bitmap_sha256=hashlib.sha256(bits).hexdigest(),attrs_sha256=hashlib.sha256(attrs).hexdigest()));print('PASS',frames[-1],flush=True)
 def event(tag,key,fast=None,worker=30,namespace=0x42,producer=None,command=None):
  nonlocal data
  at=f.get('se_hot_caret');assert at==g.get('se_hot_caret');input_started=f.total_instructions
  if command==4:data=data[:at]+data[at+1:]
  elif key==0x14:data=data[:at-1]+data[at:]
  else:data=data[:at]+bytes([key])+data[at:]
  for x in(f,g):x.command(command)if command else x.key(key)
  input_used=f.total_instructions-input_started
  if producer==1 and data.startswith(b'*'):assert f.m.read(0x9162)!=0,(tag,'oldGPR_INLINE')
  check(tag,fast,worker,namespace,producer)
  frames[-1]['input_instructions']=input_used;frames[-1]['input_render_instructions']=input_used+frames[-1]['instructions']
 try:
  tail='\rSecond plain row\rThird plain row\rTail.'
  for name,delim in [('plain',''),('bold','**'),('italic','*'),('combined','***')]:
   source=geos.native_text(delim+'interiorwords'+delim+' omega.'+tail);at=source.index(geos.native_text('interiorwords'))+3;setup(source,at);fast=variant=='candidate'or name=='plain'
   event(name+'-insert',geos.native_text('X')[0],fast,producer=int(fast));event(name+'-backspace',0x14,fast,producer=int(fast))
   if name=='combined':
    for i in range(4):event('combined-repeat-'+str(i),geos.native_text('Q')[0]if i%2==0 else 0x14,fast,producer=int(fast))
   assert f.merged()==source
   # Real pending undo/redo still goes through existing journal paths; no
   # direct-worker assertion because replay has a distinct publication route.
   for x in(f,g):x.command(16)
   data=f.merged();check(name+'-undo')
   for x in(f,g):x.command(17)
   data=f.merged();check(name+'-redo')
  # Marker, escape adjacency, bullet/list and neighboring colored ink remain
  # conservative; C6 may issue a certificate for punctuation, but C32 must
  # refuse its non-alnum local grammar before touching the bitmap.
  cases=[('bullet','* words **interiorwords** omega.'+tail,'interiorwords',3,geos.native_text('X')[0],0),('heading','# **interiorwords** omega.'+tail,'interiorwords',3,geos.native_text('X')[0],0),('star-marker','**interiorwords** omega.'+tail,'interiorwords',3,42,0),('near-open','**interiorwords** omega.'+tail,'interiorwords',0,geos.native_text('X')[0],None),('near-close','**interiorwords** omega.'+tail,'interiorwords',13,geos.native_text('X')[0],None),('space-inside','**interiorwords** omega.'+tail,'interiorwords',3,32,None),('colored-next','**interiorwords** omega.\r- .\rTail.','interiorwords',3,geos.native_text('X')[0],0),('colored-previous','- .\r**interiorwords** omega.\rTail.','interiorwords',3,geos.native_text('X')[0],0)]
  for name,text,word,offset,key,producer in cases:
   source=geos.native_text(text);setup(source,source.index(geos.native_text(word))+offset);event('fallback-'+name,key,False,producer=producer)
  # Explicit derived-metadata fault: actual checked FE DMA removes only the
  # old possible-inline flag. This is not a forged positive certificate. The
  # candidate must refuse even though old glyph styles remain nonzero.
  source=geos.native_text('**interiorwords** omega.'+tail);setup(source,5)
  cache,bank=f.raw_cache();row=cache[42];handle=f.get('se_gc_handle',1)
  canonical=f.canonical();f.call('se_doc_invalidate');f.m.load(0x8000,b'\0')
  for n,v,w in [('se_reu_logical',handle,1),('se_reu_offset',0x200+row*0x800+23,2),('se_reu_length',1,2),('se_reu_c64',0x8000,2)]:f.put(n,v,w)
  assert not f.call('se_reu_copy',0).p&1 and f.canonical()==canonical
  event('fallback-old-inline-zero',geos.native_text('X')[0],False,producer=0)
  # Both valid stage namespaces are reached through actual GOTO/keys. This
  # executes real C32→C31→C32 replacement; no $5000 writes or counter tricks.
  source=geos.native_text('**interiorwords** omega.\rSecond plain row\rThird plain row\r:::basic\r10 PRINT "HELLO"\r:::\rTail.')
  setup(source,0)
  for turn,word in enumerate(['interiorwords','HELLO','interiorwords']):
   at=source.index(geos.native_text(word))+2;line=source[:at].count(b'\r')+1;column=at-(source.rfind(b'\r',0,at)+1)
   for x in(f,g):
    x.typed(geos.native_text('goto '+str(line)))
    for _ in range(column):x.key(0x1d)
    assert x.get('se_hot_caret')==at;x.render()
   worker,namespace=(31,0x41)if word=='HELLO'else(30,0x42);fast=word=='HELLO'or variant=='candidate'
   event('namespace-'+str(turn)+'-insert',geos.native_text('Q')[0],fast,worker,namespace,int(fast and worker==30));event('namespace-'+str(turn)+'-backspace',0x14,fast,worker,namespace,int(fast and worker==30));assert data==source
  result=dict(status='passed',packaged=packaged,variant=variant,identity=identity,budget=budget,frames=frames,pixels=len(frames)*64000,attributes=len(frames)*1000,whole_REU_guard=16777216,scope=('Actualpackagedimages; 'if packaged else'Only C6 private SEO delta; ')+'actualpublickey/root/R30/C32/R31/C31 path, forcedfullrenderer and canonicalrawfont oracle. Namespace reuse is actual executable borrowing, not host load-counter change. CPU only.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException as e:
  (out/'failure.json').write_text(json.dumps(dict(error=repr(e),frames=len(frames),source=list(data)))+'\n');(out/'failure-c64.bin').write_bytes(f.read(0,65536));raise
 finally:f.close();g.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--packaged',action='store_true');p.add_argument('--variant',choices=['control','candidate'],default='candidate');a=p.parse_args();out=ROOT/'build/geos-style-leading'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.variant,a.packaged)
