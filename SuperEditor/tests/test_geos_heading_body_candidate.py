"""Private heading-body single-alnum INSERT/BACK with complete prefix and real row rebuild."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_semantic_editor as semantic
geos=semantic.geos;D=ROOT/'src/render/geos/heading-body-candidate'
BASE=ROOT/'build/geos-incremental-editor/20261025T161722424199Z/fixture'
STATE=0x9149

class Fixture(geos.Fixture):
 def settle(self,error=0,render=False):
  # A>64KiB cold proportional reveal streams the canonical prefix. Keep
  # actual bounded root STEP calls/leak guards; only the total job budget grows.
  steps=0
  while self.get('se_e_job',1):
   self.call('se_editor_service');steps+=1
   assert steps<200000,(self.get('se_e_job',1),self.get('se_e_error',1))
  assert self.get('se_e_error',1)==error,(hex(self.get('se_e_error',1)),hex(error))
  for n in ['se_doc_read_locks','se_s_owned','se_s_active','se_v_nav_busy','se_n_owned','se_b_phase','se_clip_busy']:assert self.get(n,1)==0,n
  if render and not error:self.render();assert self.get('se_v_seen',1)==1
  return steps

def run(out,base,variant,smoke=False,packaged=False,diverse=False,append=False):
 if packaged:
  assert variant=='candidate'
  raw=(base/'build/overlays/geosdelta.seo').read_bytes();budget=dict(packaged_R28=len(raw)-36,sha256=hashlib.sha256(raw).hexdigest());private=base
 else:
  spec=importlib.util.spec_from_file_location('heading_body_build',D/('append-build.py'if append else'build.py'));b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);images,budget=b.build(out/'link',base)
  private=out/'private-input';shutil.copytree(base,private);(private/'build/overlays/geosdelta.seo').write_bytes(images[variant]);identity=json.loads((private/'freeze.json').read_text());identity['assets']['geosdelta']=hashlib.sha256(images[variant]).hexdigest()
  # Coherent private source/disk identity, not a live shared build. The byte-exact
  # control proves the frozen assembler/binding before any candidate replacement.
  source=D/('append-edit-cache.s'if append else'edit-cache.s')if variant=='candidate'else out/'link/frozen-sources/src/render/geos/edit-cache.s'
  shutil.copy2(private/'product-sources.zip',private/'baseline-product-sources.zip')
  with zipfile.ZipFile(private/'baseline-product-sources.zip')as z,zipfile.ZipFile(private/'product-sources.zip','w',zipfile.ZIP_DEFLATED)as w:
   for name in z.namelist():w.writestr(name,source.read_bytes()if name=='src/render/geos/edit-cache.s'else z.read(name))
  identity.setdefault('sources',{})['src/render/geos/edit-cache.s']=hashlib.sha256(source.read_bytes()).hexdigest()
  disk=private/'build/supereditor.d81';p=subprocess.run(['c1541','-attach',str(disk),'-delete','geosdelta','-write',str(private/'build/overlays/geosdelta.seo'),'geosdelta,s'],capture_output=True,text=True);(out/'package.log').write_text(p.stdout+p.stderr);assert not p.returncode
  from d81_image import D81Image
  before=D81Image((base/'build/supereditor.d81').read_bytes());after=D81Image(disk.read_bytes());assert after.read(b'GEOSDELTA',kind=1).data==images[variant]
  for entry in before.entries():
   if entry.name!=b'GEOSDELTA':assert before.read(entry.name).data==after.read(entry.name).data and before.read(entry.name).sectors==after.read(entry.name).sectors
  identity['disk_sha256']=hashlib.sha256(disk.read_bytes()).hexdigest();(private/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 frozen,identity=geos.freeze(out,private);geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names'];dll=geos.grid.runner(out)
 f=Fixture(out,frozen,dll,True);g=Fixture(out,frozen,dll,True);fonts={n:(frozen/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)};frames=[];data=b''
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
  geos.png(bits,attrs,out/(tag+'.png'));frames.append(dict(tag=tag,incremental=actual,edit_class=f.m.read(STATE+46),instructions=used,full_instructions=fullused,loads=(f.get('se_overlay_loads',2)-loads)&65535,source_bytes=len(data),rows=[dict(start=r.start,end=r.end,next=r.next,top=r.top,height=r.height)for r in rows]));print('PASS',frames[-1]|{'rows':len(rows)},flush=True);(out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
 def edit(tag,op='insert',expected=True,byte=None,legacy=False):
  nonlocal data
  at=f.get('se_hot_caret');byte=geos.native_text('Q')[0]if byte is None else byte
  if op=='insert':
   data=data[:at]+bytes([byte])+data[at:]
   for x in(f,g):x.key(byte)
  elif op=='back':
   assert at>0;data=data[:at-1]+data[at:]
   for x in(f,g):x.key(0x14)
  elif op=='delete':
   data=data[:at]+data[at+1:]
   for x in(f,g):x.command(4)
  else:raise AssertionError(op)
  check(tag,expected and(variant=='candidate'or legacy))
 try:
  raw=geos.native_text('# Heading words.\rSecond plain row.\rTail.')
  setup(raw,5);edit('heading-body-insert')
  setup(raw,6);edit('heading-body-back','back')
  setup(raw,5);edit('heading-body-digit',byte=ord('9'))
  if append:
   for tag,text in [('CR','# Heading words.\rFollowing row.\rTail.'),('EOF','## Heading words.')]:
    raw=geos.native_text(text);at=raw.find(b'\r');at=len(raw)if at<0else at
    setup(raw,at);edit('heading-append-'+tag)
    edit('heading-append-then-BACK-'+tag,'back')
   raw=geos.native_text('# Heading words.\rFollowing row.\rTail.')
   setup(raw,16);edit('heading-end-forward-delete','delete',False)
   raw=geos.native_text('# '+'Widewords '*25+'\rFollowing row.\rTail.')
   setup(raw,0);cache,_=f.raw_cache();at=int.from_bytes(cache[0x203:0x206],'little')
   for x in(f,g):x.position(at);x.render()
   edit('heading-soft-boundary',expected=False)
  if diverse:
   import test_grid_editor_vice as document
   raw=document.fixture();at=raw.index(geos.native_text('SuperEditor'))+3
   setup(raw,at);edit('heading-body-diverse422')
  if not smoke:
   for level in range(1,7):
    raw=geos.native_text('#'*level+' Heading words.\rSecond plain row.\rTail.')
    setup(raw,level+4);edit('level-'+str(level)+'-insert')
    setup(raw,level+5);edit('level-'+str(level)+'-back','back')
   raw=geos.native_text('## Heading words.\rFollowing row.\rTail.')
   setup(raw,3);edit('first-body-insert')
   setup(raw,4);edit('first-body-back','back')
   raw=geos.native_text('# Heading9 words.\rTail.')
   setup(raw,10);edit('digit-back','back')
   setup(raw,5);edit('native-high-alpha',byte=0xC1)
   raw=geos.native_text('Prelude\r### Heading words.\rFollowing row.\rTail.')
   setup(raw,14);edit('after-CR-shared-tile')
   raw=b'P'*253+geos.native_text('\r# Heading words.\rFollowing row.\rTail.')
   setup(raw,258);edit('lowbyte-offset-wrap')
   raw=geos.native_text('## Last heading at EOF')
   setup(raw,len(raw)-1);edit('heading-EOF-insert')
   setup(raw,len(raw));edit('heading-EOF-back','back')
   raw=geos.native_text(':::region A\r# Heading words.\rBody.\r:::end\rTail.')
   setup(raw,17);edit('heading-in-region')
   raw=geos.native_text('# Heading words.\r:::basic\r10 PRINT "Hi"\r:::\rTail.')
   setup(raw,5);edit('heading-before-fence-carry')
   raw=geos.native_text('# Heading **strong** words.\rPlain following row.\rTail.')
   setup(raw,5);edit('heading-inline-outside')
   setup(raw,raw.index(geos.native_text('strong'))+2);edit('heading-inline-inside')
   raw=geos.native_text('prefix\r')*9400+geos.native_text('# Heading words.\rFollowing row.\rTail.')
   at=raw.index(geos.native_text('# Heading'))+5;assert at>65536
   setup(raw,at);edit('heading-offset24')
   # A fresh published pending page is a valid new baseline; no cumulative
   # hot-window delta is guessed. Two unpainted edits still refuse the ticket.
   raw=geos.native_text('# Heading words.\rFollowing row.\rTail.')
   setup(raw,5);edit('pending-first')
   assert f.get('se_hot_pending',1)
   edit('pending-next-published')
   assert f.get('se_hot_pending',1)
   setup(raw,5)
   for x in(f,g):x.key(geos.native_text('Q')[0]);x.key(geos.native_text('R')[0])
   data=raw[:5]+geos.native_text('QR')+raw[5:];check('fallback-two-unpainted',False)
   negatives=[
    ('prefix-hash','## Heading words.\rTail.',1,'insert',None),
    ('prefix-space','# Heading words.\rTail.',1,'insert',None),
    ('prefix-back-space','# Heading words.\rTail.',2,'back',None),
    ('prefix-back-hash','# Heading words.\rTail.',1,'back',None),
    ('body-space','# Heading words.\rTail.',5,'insert',32),
    ('body-punctuation','# Heading words.\rTail.',5,'insert',ord('.')),
    ('body-forward-delete','# Heading words.\rTail.',5,'delete',None),
    ('body-CR','# Heading words.\rTail.',5,'insert',13),
    ('join-CR','# Heading words.\rTail.',17,'back',None),
    ('seven-hashes','####### Heading words.\rTail.',11,'insert',None),
    ('no-marker-space','#Heading words.\rTail.',5,'insert',None),
    ('inline-code-role','# Heading @@literal@@ words.\rTail.',5,'insert',None),
    ('region-opener',':::region A\r# Heading words.\rBody.\r:::end\rTail.',10,'insert',None),
    ('fence-opener',':::basic\r10 PRINT 1\r:::\rTail.',4,'insert',None),
    ('old-wrap','# '+'Widewords '*25+'\rFollowing row.\rTail.',5,'insert',None)]
   for tag,text,at,op,byte in negatives:
    raw=geos.native_text(text);setup(raw,at);edit('fallback-'+tag,op,False,byte)
   # A code-body heading-looking byte string remains the original class1,
   # never class4 and never a generalized fence-carry transition.
   raw=geos.native_text(':::basic\r# Heading words.\r:::\rTail.')
   setup(raw,14);edit('existing-code-class','insert',True,legacy=True)
   assert f.m.read(STATE+46)==1
   # Existing START class2/3 semantics must survive the new class dispatcher.
   raw=geos.native_text('# Heading words.\rFollowing row.\rTail.')
   setup(raw,0);edit('existing-heading-to-prose','insert',True,legacy=True)
   raw=geos.native_text('Q# Heading words.\rFollowing row.\rTail.')
   setup(raw,1);edit('existing-prose-to-heading','back',True,legacy=True)
   widths=fonts['bsw9-widths.bin'];raw=geos.native_text('# ')
   while sum(widths[geos.native(v)]for v in raw)+widths[geos.native(46)]<=320:raw+=b'.'
   while sum(widths[geos.native(v)]for v in raw)>=320:raw=raw[:-1]
   assert sum(widths[geos.native(v)]for v in raw)+widths[geos.native(geos.native_text('Q')[0])]>320
   setup(raw+geos.native_text('\rFollowing row.\rTail.'),3);old,_=f.raw_cache()
   assert old[0x200+17]==1
   edit('fallback-new-wrap',expected=False)
   if variant=='candidate':
    after,_=f.raw_cache();assert after[0xd528:0xd568]==old[:64], 'admitted then actualVERIFY rejected wrap before dirtypaint'
   raw=geos.native_text('# Heading words.\rFollowing row.\rTail.')
   setup(raw,5)
   for x in(f,g):x.command(68)
   edit('fallback-empty-mark',expected=False)
   setup(raw,7)
   for x in(f,g):x.command(68);x.command(1);x.command(1);x.key(geos.native_text('Q')[0])
   data=raw[:5]+geos.native_text('Q')+raw[7:];check('fallback-reverse-selection',False)
   faults=[('flags',22,b'\0'),('kind',16,b'\1'),('height',14,b'\10'),('top',15,b'\21'),('role',356,b'\0'),('first',9,b'\1'),('raster',24,b'\1'),('reason',17,b'\0'),('count-high',13,b'\1'),('not-hash',32,b'!'),('seven-hashes',32,b'####### '),('next',6,b'\377')]
   for name,offset,value in faults:
    setup(raw,5);cache,bank=f.raw_cache();handle=f.get('se_gc_handle',1);row=cache[42];canonical=f.canonical();f.call('se_doc_invalidate');f.m.load(0x8000,value)
    for n,v,w in [('se_reu_logical',handle,1),('se_reu_offset',0x200+row*0x800+offset,2),('se_reu_length',len(value),2),('se_reu_c64',0x8000,2)]:f.put(n,v,w)
    assert not f.call('se_reu_copy',0).p&1 and f.canonical()==canonical
    edit('malformed-'+name,expected=False)
   # A real collapsed heading map refuses the row hint; modifying its opener
   # drops that affected hint under the separately verified retention oracle.
   import test_geos_fold_editor as fold
   fd=out/'fold-case';fd.mkdir();rdll=fold.retention.runner(fd);af=fold.Fixture(fd,frozen,rdll,True);ag=fold.Fixture(fd,frozen,rdll,True)
   try:
    raw=geos.native_text('# Heading words\rHidden body\rVisible tail.')
    for x in(af,ag):x.source(raw);x.command(99);x.position(5);x.command(115);x.render();assert x.get('se_ef_valid',1)and x.get('se_ef_count',2)==1
    for x in(af,ag):x.key(geos.native_text('Q')[0])
    changed=raw[:5]+geos.native_text('Q')+raw[5:];canonical=af.canonical();reu=af.reu();af.audit_begin()
    try:af.render()
    finally:af.dll.fr_end()
    writes=af.audit_end(reu,'folded-fallback');ag.m.write(0xcfe8,0);ag.m.write(0xcf90,0);ag.render()
    eb,ea,rr,_=semantic.expected(af,changed,fonts)
    assert af.m.read(0x9148)==0 and af.canonical()==canonical and af.merged()==changed==ag.merged()
    assert af.read(0x6000,8000)==eb==ag.read(0x6000,8000)and af.read(0x4000,1000)==ea==ag.read(0x4000,1000)
    assert af.read(0xc600,1024)==af.shim and not any(af.get(n,1)for n in ['se_f_owner','se_doc_read_locks','se_fs_owned'])
    geos.png(eb,ea,out/'fallback-collapsed-fold.png');frames.append(dict(tag='fallback-collapsed-fold',incremental=False,source_bytes=len(changed),typed46_FE_stashes=writes))
   finally:af.close();ag.close()
   f.m.load(0xa000,(frozen/'build/overlays/geosdelta.seo').read_bytes()[36:]);f.m.load(0x8d00,bytes((i*31+7)&255 for i in range(1152)))
   for owner,op,error in [(1,0,0xb2),(2,0,0xb2),(3,0,0xb2),(5,0,0xb2),(255,0,0xb2),(4,255,0x90)]:
    f.put('se_f_owner',owner,1);f.m.write(f.s['se_overlay_frame'],op);before=f.read(0,65536);reu=f.reu();r,n=f.fast_call(0xa010);after=f.read(0,65536);want=bytearray(before);want[0x100:0x200]=after[0x100:0x200]
    assert r.p&1 and r.a==error and after==want and f.reu()==reu,('opaqueentry',owner,op,r.a)
  result=dict(status='passed',packaged=packaged,variant=variant,identity=identity,budget=budget,frames=frames,pixels=len(frames)*64000,attributes=len(frames)*1000,whole_REU_guard=16777216,scope='PrivateR28 headingbodyINSERT/BACK; actualC24/C20/root/fullrenderer/independentsemanticfont/source/history/allanchors. No nativeclaim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException as e:
  (out/'failure.json').write_text(json.dumps(dict(error=repr(e),frames=len(frames),source=list(data)))+'\n');(out/'failure-c64.bin').write_bytes(f.read(0,65536));(out/'failure-reu.bin').write_bytes(f.reu());raise
 finally:f.close();g.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--variant',choices=['control','candidate'],default='candidate');p.add_argument('--smoke',action='store_true');p.add_argument('--packaged',action='store_true');p.add_argument('--diverse',action='store_true');p.add_argument('--append',action='store_true');a=p.parse_args();out=ROOT/'build/geos-heading-body'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 run(out,a.fixture.resolve(),a.variant,a.smoke,a.packaged,a.diverse,a.append)
