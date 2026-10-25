"""Private bounded R28 heading→prose transition through actual public editor."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_semantic_editor as semantic
import test_grid_editor_vice as diverse
geos=semantic.geos;D=ROOT/'src/render/geos/heading-transition-candidate'
BASE=ROOT/'build/geos-incremental-editor/20261025T130401385558Z/fixture'
STATE=0x9149

def run(out,base,variant,smoke=False,packaged=False):
 if packaged:
  assert variant=='candidate','Packaged mode validates the promoted behavior'
  raw=(base/'build/overlays/geosdelta.seo').read_bytes();assert raw[5:7]==bytes([0,28])and len(raw)-36<=4096
  budget=dict(packaged_R28=len(raw)-36,sha256=hashlib.sha256(raw).hexdigest());private=base
 else:
  spec=importlib.util.spec_from_file_location('heading_build',D/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);images,budget=b.build(out/'link',base)
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
   p=cache[0x200+i*0x800:0x220+i*0x800];assert int.from_bytes(p[:3],'little')==row.start and int.from_bytes(p[3:6],'little')==row.end and int.from_bytes(p[6:9],'little')==row.next and p[14]==row.height and p[15]==row.top,(tag,'allrows',i,row,p.hex())
  assert f.get('se_v_bottom')==rows[-1].next
  assert f.read(0xc600,1024)==f.shim and all(f.get(n,1)==0 for n in ['se_f_owner','se_doc_read_locks','se_fs_owned'])
  handle=f.get('se_gc_handle',1);assert handle and bank and f.m.read(f.s['se_reu_logical_owner']+handle)==0xfe and f.m.read(f.s['se_reu_physical_owner']+bank)==0xfe
  now=f.reu();start=bank*65536;cursor=0
  for a,b in[(start,start+64),(start+0x200,start+0xe568)]:assert now[cursor:a]==before[cursor:a],(tag,'foreign/FEgap',cursor,a);cursor=b
  assert now[cursor:]==before[cursor:],(tag,'font/tail/foreignREU')
  geos.png(bits,attrs,out/(tag+'.png'));frames.append(dict(tag=tag,incremental=actual,instructions=used,full_instructions=fullused,loads=(f.get('se_overlay_loads',2)-loads)&65535,source_bytes=len(data),rows=[dict(start=r.start,end=r.end,next=r.next,top=r.top,height=r.height)for r in rows]));print('PASS',frames[-1]|{'rows':len(rows)},flush=True)
 def insert(tag,at=None,byte=None,expect=True):
  nonlocal data
  if at is not None:
   for x in(f,g):x.position(at);x.render()
  at=f.get('se_hot_caret');byte=geos.native_text('Q')[0]if byte is None else byte;data=data[:at]+bytes([byte])+data[at:]
  for x in(f,g):x.key(byte)
  check(tag,expect and variant=='candidate')
 try:
  setup(diverse.fixture());insert('diverse-leading-heading')
  if not smoke:
   for level in range(1,7):
    source=geos.native_text('#'*level+' Heading words.\rSecond plain row.\rTail.');setup(source);insert('heading-level-'+str(level))
   setup(geos.native_text('## Last heading at EOF'));insert('heading-eof')
   setup(geos.native_text('# Heading with **boldword**\rPlain next row\rTail.'));insert('heading-inline')
   raw=geos.native_text('Prelude\r### Heading words.\rFollowing row.\rTail.');setup(raw,8);insert('heading-after-CR')
   # BACK restoring a heading is deliberately outside the one-way extension.
   for x in(f,g):x.key(0x14)
   data=raw;check('fallback-restores-heading',False)
   # A previously complete CR row which now wraps must abandon the staged
   # transaction and rebuild the full page before publishing pixels.
   width=fonts['bsw9-widths.bin'];raw=geos.native_text('# ')
   while sum(width[geos.native(v)]for v in raw)+width[geos.native(46)]<=320:raw+=b'.'
   while sum(width[geos.native(v)]for v in raw)>=320:raw=raw[:-1]
   assert sum(width[geos.native(v)]for v in raw)+width[geos.native(geos.native_text('Q')[0])]>320
   setup(raw+geos.native_text('\rFollowing row.\rTail.'));oldheader,_=f.raw_cache();assert oldheader[0x200+17]==1,'oldrow must be completeCR before newwrap'
   insert('fallback-new-wrap',expect=False)
   if variant=='candidate':
    after,_=f.raw_cache();assert after[0xd528:0xd568]==oldheader[:64], 'actualR28 admitted/bankedoldheader before VERIFY rejected newwrap'
   raw=geos.native_text('# '+'Widewords '*18+'\rFollowing row.\rTail.');setup(raw);insert('fallback-old-wrap',expect=False)
   # Fence/region openers change carry and remain excluded. A genuine heading
   # inside a region changes no region count, and is still a permitted case.
   for name,text,at,allowed in [('fence-opener',':::basic\r10 PRINT 1\r:::\rTail.',0,False),('fenced-code',':::basic\r# Heading\r:::\rTail.',9,False),('region-opener',':::region A\r# Heading\rbody\r:::end\rTail.',0,False),('heading-in-region',':::region A\r# Heading\rbody\r:::end\rTail.',12,True),('unsupported-seven','####### Plain words\rTail.',0,False),('ordinary-start','Ordinary words\rTail.',0,False),('inline-code-role','# Heading @@literal@@ words\rTail.',0,False),('heading-interior','# Heading words\rTail.',5,False)]:
    setup(geos.native_text(text),at);insert('boundary-'+name,expect=allowed)
   setup(geos.native_text('# Heading words\rFollowing row\rTail.'))
   for byte in geos.native_text('QR'):
    at=f.get('se_hot_caret');data=data[:at]+bytes([byte])+data[at:]
    for x in(f,g):x.key(byte)
   check('fallback-two-pending-edits',False)
   # Corrupt only declared derived metadata through the checked FE provider.
   # Reject before accepting a false row geometry or semantic class witness.
   faults=[('flags',22,b'\0'),('kind',16,b'\1'),('height',14,b'\10'),('plausible-top',15,b'\21'),('past-top',15,b'\270'),('raster',24,b'\1'),('reason',17,b'\0'),('first',9,b'\1'),('next',6,b'\377'),('count-high',13,b'\1'),('role-zero',356,b'\0'),('role-invalid',356,b'\16'),('not-hash',32,b'!'),('seven-hashes',32,b'####### ')]
   for name,offset,value in faults:
    setup(geos.native_text('# Heading words\rFollowing row\rTail.'))
    cache,bank=f.raw_cache();handle=f.get('se_gc_handle',1);row=cache[42];canonical=f.canonical();f.call('se_doc_invalidate');f.m.load(0x8000,value)
    for n,v,w in [('se_reu_logical',handle,1),('se_reu_offset',0x200+row*0x800+offset,2),('se_reu_length',len(value),2),('se_reu_c64',0x8000,2)]:f.put(n,v,w)
    assert not f.call('se_reu_copy',0).p&1 and f.canonical()==canonical
    insert('malformed-'+name,expect=False)
   # Real collapsed fold + pending edit drops its changed heading hint. The
   # full pipeline must expose the former hidden source, not reuse row packets.
   import test_geos_fold_editor as fold
   fd=out/'fold-case';fd.mkdir();rdll=fold.retention.runner(fd);af=fold.Fixture(fd,frozen,rdll,True);ag=fold.Fixture(fd,frozen,rdll,True)
   try:
    raw=geos.native_text('# Heading words\rHidden body\rVisible tail.')
    for x in(af,ag):x.source(raw);x.command(99);x.command(115);x.render();assert x.get('se_ef_valid',1)and x.get('se_ef_count',2)==1
    for x in(af,ag):x.key(geos.native_text('Q')[0])
    changed=geos.native_text('Q')+raw;canonical=af.canonical();reu=af.reu();af.audit_begin()
    try:af.render()
    finally:af.dll.fr_end()
    writes=af.audit_end(reu,'folded-fallback');ag.m.write(0xcfe8,0);ag.m.write(0xcf90,0);ag.render()
    eb,ea,rr,_=semantic.expected(af,changed,fonts)
    assert af.m.read(0x9148)==0 and af.canonical()==canonical and af.merged()==changed==ag.merged()
    assert af.read(0x6000,8000)==eb==ag.read(0x6000,8000)and af.read(0x4000,1000)==ea==ag.read(0x4000,1000)
    assert af.read(0xc600,1024)==af.shim and not any(af.get(n,1)for n in ['se_f_owner','se_doc_read_locks','se_fs_owned'])
    geos.png(eb,ea,out/'fallback-collapsed-fold.png');frames.append(dict(tag='fallback-collapsed-fold',incremental=False,source_bytes=len(changed),typed46_FE_stashes=writes))
   finally:af.close();ag.close()
   # Explicit leaf entry barrier proof; separate from the public command lane.
   f.m.load(0xa000,(frozen/'build/overlays/geosdelta.seo').read_bytes()[36:]);f.m.load(0x8d00,bytes((i*31+7)&255 for i in range(1152)))
   for owner,op,error in [(1,0,0xb2),(2,0,0xb2),(3,0,0xb2),(5,0,0xb2),(255,0,0xb2),(4,255,0x90)]:
    f.put('se_f_owner',owner,1);f.m.write(f.s['se_overlay_frame'],op);before=f.read(0,65536);reu=f.reu();r,n=f.fast_call(0xa010);after=f.read(0,65536);want=bytearray(before);want[0x100:0x200]=after[0x100:0x200]
    assert r.p&1 and r.a==error and after==want and f.reu()==reu,('opaqueentry',owner,op,r.a)
  result=dict(status='passed',packaged=packaged,variant=variant,identity=identity,budget=budget,frames=frames,pixels=len(frames)*64000,attributes=len(frames)*1000,whole_REU_guard=16777216,scope='Only private R28 SEO delta; actualC24/C20/C22 publicroot rebuild, independentfont/semantic/fullrenderer/allrowgeometry/source/history/16MiB guards. No nativeclaim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException as e:
  (out/'failure.json').write_text(json.dumps(dict(error=repr(e),frames=len(frames),source=list(data)))+'\n');(out/'failure-c64.bin').write_bytes(f.read(0,65536));raise
 finally:f.close();g.close()
def incremental_regression(out,base):
 # The sole old expectation changed by this feature is the last PREFIX edit.
 # Transplant only that predicate into this private verifier; no old file edit.
 import inspect
 import test_geos_incremental_editor as original
 text=inspect.getsource(original.run)
 old="check(('dirty-' if classes and tag in ('inline','basic')else 'fallback-')+tag,classes and tag in ('inline','basic'))"
 new="check(('dirty-' if classes and tag in ('inline','basic','prefix')else 'fallback-')+tag,classes and tag in ('inline','basic','prefix'))"
 assert text.count(old)==1,'Original verifier changed; manually review the one expected-path update'
 transplanted=text.replace(old,new);namespace=dict(vars(original));exec(compile(transplanted,str(Path(__file__))+'::expected-prefix-path','exec'),namespace)
 (out/'private-predicate-update.json').write_text(json.dumps(dict(original_verifier=str(Path(original.__file__)),original_sha256=hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest(),old=old,new=new,scope='Only PREFIX expected-path/label changes; original actualfull/source/pixel/REU checks unchanged.'),indent=2)+'\n')
 return namespace['run'](out,base)


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--packaged',action='store_true');p.add_argument('--variant',choices=['control','candidate'],default='candidate');p.add_argument('--incremental-regression',action='store_true');p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-heading-transition'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 if a.incremental_regression:incremental_regression(out,a.fixture.resolve())
 else:run(out,a.fixture.resolve(),a.variant,a.smoke,a.packaged)
