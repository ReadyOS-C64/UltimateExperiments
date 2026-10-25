"""Private byte-oriented packed-font R23 candidate; no production/build mutations.

Frozen resident/provider and real FD guard/DMA; actual private linked R23 A/B.
Default prepares; --smoke proves first glyph quickly; --run covers all faces.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,shutil,struct,subprocess,sys,zipfile
import test_geos_editor as geos
from test_geos_catalog_glyph import oracle
from d81_image import D81Image
ROOT=geos.ROOT
DEFAULT=ROOT/'build/geos-semantic-editor/20261025T084229230703Z/fixture'
CANDIDATE=ROOT/'src/render/geos/catalog-byte-candidate'

def command(*args):
 p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True)
 if p.returncode:print(p.stdout+p.stderr,flush=True)
 assert not p.returncode,args

def symbols(path):
 return {v[2].lstrip('.'):int(v[1],16)for line in path.read_text().splitlines()if len(v:=line.split())==3 and v[0]=='al'}

def build(out,frozen,candidate,source_dir=None):
 out.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(frozen/'product-sources.zip')as z:
  for name in ('font-store.s','catalog-glyph.s','preview-row-entry.s'):
   source_name='catalog-preview.s'if name=='catalog-glyph.s'else name
   (out/name).write_bytes(((source_dir or CANDIDATE)/source_name).read_bytes()if candidate and name!='font-store.s'else z.read('src/render/geos/'+source_name))
  # Freeze every actual include; no in-flight production edits may affect build.
  for name in z.namelist():
   if name.startswith('src/') and name.endswith('.inc'):
    p=out/'includes'/name[4:];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
 disk=D81Image((frozen/'build/supereditor.d81').read_bytes());(out/'font-pack.bin').write_bytes(disk.read(b'GEOSFONTS',kind=1).data)
 command(sys.executable,'tools/geos_font_store_meta.py','--pack',out/'font-pack.bin','--output',out/'geos-font-pack.inc')
 command(sys.executable,'src/fold/editor-leaves/binding.py','--report',frozen/'build/editor-report.json','--output',out/'editor-api.inc')
 with(out/'editor-api.inc').open('a')as f:f.write('.import se_f_owner\n.importzp text_ptr,screen_ptr\n')
 objs=[]
 for name in ('preview-row-entry','catalog-glyph','font-store'):
  obj=out/(name+'.o');flags=['-D','SE_GEOS_PREVIEW_FAST=1']if name=='font-store'else[]
  command('ca65','-g',*flags,'-I',out,'-I',out/'includes','-o',obj,out/(name+'.s'));objs.append(obj)
 command(sys.executable,'tools/module_bindings.py','--report',frozen/'build/editor-report.json','--output',out/'bindings.s',*objs)
 command('ca65','-g','-o',out/'bindings.o',out/'bindings.s')
 (out/'r23.cfg').write_text('MEMORY{IMAGE:file=%O,start=$A000,size=$1000,type=rw;} SEGMENTS{CODE:load=IMAGE,type=ro;RODATA:load=IMAGE,type=ro;}')
 command('ld65','-C',out/'r23.cfg','-o',out/'r23.bin','-m',out/'r23.map','-Ln',out/'r23.lbl',*objs,out/'bindings.o')
 raw=(out/'r23.bin').read_bytes()
 if not candidate:assert raw==(frozen/'build/overlays/geosfontrow.seo').read_bytes()[36:],'control mustmatch actualfrozenR23byteexact'
 return symbols(out/'r23.lbl'),len(raw)

class Fixture(geos.Fixture):
 def __init__(self,out,frozen,dll,leaf):
  super().__init__(out,frozen,dll,True);self.source(b'',physical=256)
  self.m.load(0xa000,(leaf/'r23.bin').read_bytes());self.symbols=symbols(leaf/'r23.lbl')
  self.m.write(self.s['se_f_owner'],4);self.m.write(0xcbd5,0)
  self.calls=0;self.used=0
 def reu(self):
  raw=C.create_string_buffer(16*1024*1024);self.dll.gm_reu(self.m.handle,len(raw),raw);return raw.raw
 def glyph(self,entry,value,style,inverse,clip=None,encoding=0,native=False,measure=False,ctx=0x8800,ink=False):
  if clip is None:
   assert ctx==0x8800
   profile=bytes((0,1,0,8,1,6,0))if native else bytes((0,0,0,9,1,6,0))if entry[0]==2 else bytes((1,entry[1],entry[2],entry[3],1,6,0))
   self.m.load(0xcc00+18,profile);self.m.write(0xcc00+34,value);self.m.write(0xcc00+32,style);self.m.write(0xcc00+65,inverse);self.m.write(0xcc00+33,0);self.m.write(0xcc00+35,0)
   target=self.symbols['entry'];x=y=0
  else:
   if not native:self.m.load(0xcbd0,entry[:4]);assert not self.fast_call(self.symbols['se_gf_fetch_preview'])[0].p&1
   fontptr=0 if native else 0x5000;length=0 if native else int.from_bytes(entry[11:13],'little')
   inputs=fontptr.to_bytes(2,'little')+length.to_bytes(2,'little')+(0x4800).to_bytes(2,'little')+bytes((value,encoding,style,inverse,*clip))
   self.m.load(ctx,inputs+bytes([0xa7])*226)
   target=self.symbols['se_geos_catalog_measure'+('_preview'if 'se_geos_catalog_measure_preview'in self.symbols else '')]if measure else self.symbols['se_geos_catalog_glyph'+('_preview'if 'se_geos_catalog_glyph_preview'in self.symbols else '')]
   if ink:target=self.symbols['se_geos_catalog_ink_preview']
   x=ctx&255;y=ctx>>8
  before=self.read(0,65536);self.last_before=before
  regs,used=self.fast_call(target,x=x,y=y)
  self.calls+=1;self.used+=used
  after=self.read(0,65536);want=bytearray(before)
  allowed=[(0x100,0x200),(0x5000,0x6072),(ctx,ctx+240),(0xcbc0,0xcc00),(0xdf00,0xdf0b),
           (self.s['text_ptr'],self.s['text_ptr']+2),(self.s['screen_ptr'],self.s['screen_ptr']+2),
           (self.s['se_reu_c64'],self.s['dma_physical']+1),(self.s['se_crc_value'],self.s['se_crc_value']+2)]
  for a,b in allowed:want[a:b]=after[a:b]
  assert after==want,('fullRAM',next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,want))if a!=b))
  return regs,self.read(ctx,240),used

def fault_suite(a,b,pack,entries):
 e=entries[0];offset=int.from_bytes(e[8:11],'little');length=int.from_bytes(e[11:13],'little');raw=pack[offset:offset+length]
 frames=0;groups=[]
 def inputs(**kw):
  args=dict(font=0x5000,length=length,native=0x4800,value=0x47,encoding=0,style=0,flags=0,clip=(0,32,0,24));args.update(kw)
  return args['font'].to_bytes(2,'little')+args['length'].to_bytes(2,'little')+args['native'].to_bytes(2,'little')+bytes((args['value'],args['encoding'],args['style'],args['flags'],*args['clip']))
 def direct(f,data,private=False,ctx=0x8800,measure=False):
  nonlocal frames
  if 0x1000<=ctx and ctx+240<=0xc600:f.m.load(ctx,data+bytes([0xa7])*226)
  before=f.read(0,65536)
  label='se_geos_catalog_measure'if measure else 'se_geos_catalog_glyph'
  if private:label+='_preview'
  r,_=f.fast_call(f.symbols[label],x=ctx&255,y=ctx>>8)
  after=f.read(0,65536);want=bytearray(before)
  allowed=[(0x100,0x200),(f.s['text_ptr'],f.s['text_ptr']+2),(f.s['screen_ptr'],f.s['screen_ptr']+2)]
  if 0x1000<=ctx and ctx+240<=0xc600:allowed.append((ctx+14,ctx+240))
  if private:allowed +=[(0x5000,0x6072),(0xcbc0,0xcc00),(f.s['se_reu_c64'],f.s['dma_physical']+1),(f.s['se_crc_value'],f.s['se_crc_value']+2),(0xdf00,0xdf0b)]
  for x,y in allowed:want[x:y]=after[x:y]
  assert after==want,('faultfullRAM',label,ctx,next((hex(i),x,y)for i,(x,y)in enumerate(zip(after,want))if x!=y))
  frames+=1;return r,f.read(ctx,240)if ctx+240<=65536 else b''
 def arm(f):
  f.m.write(f.s['se_f_owner'],4);f.m.load(0xcbd0,e[:4]);f.m.write(0xcbd5,0)
  r,_=f.fast_call(f.symbols['se_gf_fetch_preview']);assert not r.p&1
 for f in (a,b):arm(f)
 base_a=a.reu();base_b=b.reu()
 # Original public glyph/measure API is still strict in candidate image.
 invalid=[dict(encoding=3),dict(encoding=2,value=31),dict(encoding=2,value=129),dict(style=8),dict(flags=2),dict(clip=(33,32,0,24)),dict(clip=(0,33,0,24)),dict(clip=(0,32,25,24)),dict(clip=(0,32,0,25)),dict(font=0),dict(length=0),dict(font=0xc500),dict(font=0xfff0),dict(native=0xfff0),dict(native=0xc300),dict(native=0x8800),dict(font=0x8800)]
 for measure in (False,True):
  for kw in invalid:
   for f in (a,b):f.m.load(0x5000,raw)
   ar,af=direct(a,inputs(**kw),measure=measure);br,bf=direct(b,inputs(**kw),measure=measure)
   assert ar.p&1 and br.p&1 and ar.a==br.a==0x90,(measure,kw,ar.a,br.a)
  for ctx in (0x0fff,0xc511,0xc600,0xff80):
   ar,_=direct(a,inputs(),ctx=ctx,measure=measure);br,_=direct(b,inputs(),ctx=ctx,measure=measure)
   assert ar.p&1 and br.p&1 and ar.a==br.a==0x90
 groups.append('strictpublicscalar/context/spanrefusals A/B unchanged')
 malformed=[]
 for at in range(8):
  bad=bytearray(raw);bad[at]^=255;malformed.append(bytes(bad))
 for start,end in ((65535,0),(21,20),(0,512),(3,4)):
  bad=bytearray(raw);bad[8:12]=start.to_bytes(2,'little')+end.to_bytes(2,'little');malformed.append(bytes(bad))
 for bad in malformed:
  for f in (a,b):f.m.load(0x5000,bad)
  ar,_=direct(a,inputs());br,_=direct(b,inputs())
  assert ar.p&1 and br.p&1 and ar.a==br.a==0x94
 groups.append('strictpublicmalformedfontheader/globalindexrefusals retained')
 # Private route repeats all scalar/context checks BEFORE invoking guard.
 arm(b)
 for kw in invalid:
  r,_=direct(b,inputs(**kw),True);assert r.p&1 and r.a==0x90,(kw,r.a)
 for ctx in (0x0fff,0xc511,0xc600,0xff80):
  r,_=direct(b,inputs(),True,ctx=ctx);assert r.p&1 and r.a==0x90
 groups.append('privateentrycontext/scalar/native/fontspan admission retained')
 # No foreign owner may touch even the incoming frame or pointer loans.
 for owner in (0,1,2,3,5,255):
  b.m.write(b.s['se_f_owner'],owner)
  for label in ('entry','se_geos_catalog_glyph_preview','se_geos_catalog_measure_preview'):
   before=b.read(0,65536);r,_=b.fast_call(b.symbols[label],x=0,y=0x88);after=b.read(0,65536);want=bytearray(before);want[0x100:0x200]=after[0x100:0x200]
   assert r.p&1 and r.a==0xb2 and after==want,(owner,label,'foreignopaque')
   frames+=1
 b.m.write(b.s['se_f_owner'],4);groups.append('foreignowneropaque forwrapper andbothinternalentries')
 # Direct entry cannot use a caller's arbitrary pointer/length as trusted data.
 arm(b);r,_=direct(b,inputs(font=0x6000),True);assert r.p&1 and r.a==0x90
 r,_=direct(b,inputs(length=length-1),True);assert r.p&1 and r.a==0x90
 groups.append('trustedfontpointer5000/verifiedlength required')
 # Every direct private invocation executes the real runtime capability guard.
 for at,value,error in [(0xcbc0,0,0x18),(0xcbc5,1,0x91),(0xcbc1,0,0x18),(0xcbc2,0,0x18),(0xcbc3,255,0x18),(0xcbc4,255,0x18)]:
  arm(b);old=b.m.read(at);b.m.write(at,value);r,frame=direct(b,inputs(),True)
  assert r.p&1 and r.a==error and frame[14]==0 and b.m.read(0xcbd5)==0,(at,r.a)
  b.m.write(at,old)
 for handle in b.read(0xcbc1,2):
  physical=b.m.read(b.s['se_reu_map']+handle)
  for table,index in (('se_reu_logical_owner',handle),('se_reu_physical_owner',physical)):
   arm(b);at=b.s[table]+index;old=b.m.read(at);b.m.write(at,0x77);r,frame=direct(b,inputs(),True)
   assert r.p&1 and r.a==0x18 and frame[14]==0 and b.m.read(0xcbd5)==0
   b.m.write(at,old)
 groups.append('READY/busy/FDhandles/epochs/bothlogicalphysicalownership guarded actualCPU')
 arm(b);handles=b.read(0xcbc1,2);physical=[b.m.read(b.s['se_reu_map']+h)for h in handles]
 for h,ph in zip(handles,physical[::-1]):b.m.write(b.s['se_reu_map']+h,ph)
 r,frame=direct(b,inputs(),True);assert r.p&1 and r.a==0x94 and frame[14]==0
 for h,ph in zip(handles,physical):b.m.write(b.s['se_reu_map']+h,ph)
 groups.append('FDmappingchange forcesactualrefill/CRCrefusal')
 for change in ('stickyborrow','loadtag'):
  arm(b);b.m.load(0x5000,bytes([0xa5])*length)
  if change=='stickyborrow':b.m.write(0xcbd5,0)
  else:b.m.load(b.s['se_overlay_loads'],((b.get('se_overlay_loads',2)+1)&65535).to_bytes(2,'little'))
  r,frame=direct(b,inputs(),True);assert not r.p&1 and b.read(0x5000,length)==raw
 groups.append('stickyborrow/equalloadtag andchangedloadtag requireverifiedFDrefill')
 arm(b);b.m.write(0x500a,b.m.read(0x500a)^1);r,_=b.fast_call(b.symbols['se_gf_fetch'])
 assert r.p&1 and r.a==0x94 and b.m.read(0xcbd5)==0
 groups.append('strictFETCHstillCRCcheckseveryhit')
 # Existing internal selected-index bound helper tested independently at edges.
 for stride in (1,2,16,128,511):
  for end in (0,1,stride*8,stride*8+1,65535):
   b.m.load(0x8800+214,end.to_bytes(2,'little'));b.m.load(0x8800+216,stride.to_bytes(2,'little'))
   b.m.load(b.s['text_ptr'],(0x8800).to_bytes(2,'little'))
   r,_=b.fast_call(b.symbols['preview_selected_bounds']);assert bool(r.p&1)==(end>stride*8),(stride,end)
   frames+=1
 groups.append('selectedend<=stride*8 directinternalboundaryproof')
 assert a.reu()==base_a and b.reu()==base_b,'faults changed any16MiBREUbyte'
 return dict(status='passed',calls=frames,groups=groups,guard='Full64KiBRAM foreachdirectcall/whole16MiBREU; foreignownerallRAMexceptstack opaque. Directhelperboundtest usesdeclaredprivateframe/ZP inputs, notatrustedfontbypass.')


def synthetic_suite(a,b,fallback):
 # Explicit rawwidth0..24 × phase0..7 proof, with adjacent glyph bits poisoned.
 # This calls unchanged strict public CG semantics: synthetic data is NEVER
 # smuggled through the authenticated real-FD preview entry.
 calls=0;total_a=total_b=0;contexts=(0x8800,0x8801)
 baseline_a=a.reu();baseline_b=b.reu()
 for phase in range(8):
  for width in range(25):
   offsets=[0]+[phase]*33+[phase+width]*63
   raw=struct.pack('<BHBHH',6,4,9,8,202)+struct.pack('<97H',*offsets)+bytes((0xa5^(r*29)^(i*37))&255 for r in range(9)for i in range(4))
   assert len(raw)==238
   for ctx in contexts:
    for style in range(8):
     for inverse in range(2):
      clip=(0,32,0,24)if style<4 else(1,23,1,9)
      inputs=(0x5000).to_bytes(2,'little')+len(raw).to_bytes(2,'little')+(0x4800).to_bytes(2,'little')+bytes((65,2,style,inverse,*clip))
      frames=[]
      for f in (a,b):
       f.m.load(0x5000,raw);f.m.load(ctx,inputs+bytes([0xa7])*226);before=f.read(0,65536)
       regs,used=f.fast_call(f.symbols['se_geos_catalog_glyph'],x=ctx&255,y=ctx>>8);after=f.read(0,65536);want=bytearray(before)
       for x,y in ((0x100,0x200),(ctx+14,ctx+240),(f.s['text_ptr'],f.s['text_ptr']+2),(f.s['screen_ptr'],f.s['screen_ptr']+2)):want[x:y]=after[x:y]
       assert after==want,('syntheticRAM',phase,width,ctx,style)
       assert not regs.p&1,(phase,width,ctx,style,regs.a)
       frames.append(f.read(ctx,240))
       if f is a:total_a+=used
       else:total_b+=used
      met,ink,cov=oracle(raw,fallback,65,2,style,inverse,clip)
      assert frames[0][:212]==frames[1][:212],('syntheticA/B',phase,width,ctx,style,inverse)
      assert frames[1][14:20]==met and frames[1][20:116]==ink and frames[1][116:212]==cov,('syntheticoracle',phase,width,ctx,style,inverse)
      calls+=1
 assert a.reu()==baseline_a and b.reu()==baseline_b
 # Strict synthetic frame calls borrowed5000 without setting actual FS tag;
 # explicitly revoke that caller-local borrow before real FD guard fault suite.
 for f in (a,b):f.m.write(0xcbd5,0)
 return dict(cases=calls,phases=8,rawwidths=25,styles=8,inversions=2,contexts=[hex(x)for x in contexts],control_instructions=total_a,candidate_instructions=total_b,scope='Strict publicCG rawfont fixture; exact phase/width/adjoining-bit proof, not FD bypass. Full64KiBRAM everycall/all16MiBREU.')

def run(out,previous,smoke,faults_only=False):
 frozen,identity=geos.freeze(out,previous)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 cs,control_bytes=build(out/'control',frozen,False);ss,candidate_bytes=build(out/'candidate',frozen,True)
 print('LINKPASS',control_bytes,candidate_bytes,flush=True)
 dll=geos.grid.runner(out)
 a=Fixture(out,frozen,dll,out/'control');b=Fixture(out,frozen,dll,out/'candidate')
 pack=(out/'control/font-pack.bin').read_bytes();entries=[pack[32+i*16:48+i*16]for i in range(43)]
 fallback=(frozen/'fonts/native8.bin').read_bytes();cases=[];total=0
 try:
  reu_a=a.reu();reu_b=b.reu()
  for face,e in enumerate(entries[:0]if faults_only else entries[:1]if smoke else entries):
   offset=int.from_bytes(e[8:11],'little');raw=pack[offset:offset+int.from_bytes(e[11:13],'little')]
   start_a=a.used;start_b=b.used;count=0
   samples=[(0x41,0,0),(0x47,7,1),(0xc1,3,0)]if smoke else[(v,v&7,(v>>3)&1)for v in range(256)]
   for value,style,inverse in samples:
    ar,af,au=a.glyph(e,value,style,inverse);br,bf,bu=b.glyph(e,value,style,inverse)
    assert not(ar.p&1 or br.p&1),(face,value,ar.a,br.a)
    assert af[:212]==bf[:212],('A/B',face,value,style,inverse)
    met,ink,cov=oracle(raw,fallback,value,0,style,inverse,(0,32,0,24))
    assert bf[14:20]==met and bf[20:116]==ink and bf[116:212]==cov,('oracle',face,value,style,inverse)
    count+=1;total+=1
   if not smoke:
    # Every actual rawfaceglyph, all B/I/U combinations, both inversions.
    # Both A/B private entries execute actual FD guard; public API stays strict.
    for value in range(32,32+e[13]):
     for style in range(8):
      for inverse in range(2):
       ar,af,au=a.glyph(e,value,style,inverse,(0,32,0,24),encoding=2)
       br,bf,bu=b.glyph(e,value,style,inverse,(0,32,0,24),encoding=2)
       assert not(ar.p&1 or br.p&1),(face,value,'GEOSASCII',ar.a,br.a)
       assert af[:212]==bf[:212],('raw A/B',face,value,style,inverse)
       met,ink,cov=oracle(raw,fallback,value,2,style,inverse,(0,32,0,24))
       assert bf[14:20]==met and bf[20:116]==ink and bf[116:212]==cov,('raw oracle',face,value,style,inverse)
       count+=1;total+=1
    for style in range(8):
     for clip in [(0,0,0,0),(1,32,0,24),(0,31,0,24),(3,17,1,7),(32,0,24,0),(0,32,1,23),(7,19,8,18)]:
      ar,af,_=a.glyph(e,0x47,style,style&1,clip);br,bf,_=b.glyph(e,0x47,style,style&1,clip)
      assert not(ar.p&1 or br.p&1) and af[:212]==bf[:212],('clip A/B',face,style,clip)
      met,ink,cov=oracle(raw,fallback,0x47,0,style,style&1,clip)
      assert bf[14:20]==met and bf[20:116]==ink and bf[116:212]==cov,('cliporacle',face,style,clip)
      count+=1;total+=1
    # Arbitrary legal non8800 contexts retain the generic byte path, not a
    # silent fixed-frame assumption. Same actual FD guard and independent model.
    for ctx in (0x8801,0x8d00,0xb100):
     for value,style in ((0x20,0),(0x41,7),(0x5c,2),(0xff,5)):
      clip=(3,23,1,18)
      ar,af,_=a.glyph(e,value,style,style&1,clip,ctx=ctx);br,bf,_=b.glyph(e,value,style,style&1,clip,ctx=ctx)
      assert not(ar.p&1 or br.p&1)and af[:212]==bf[:212],('genericcontext',face,ctx,value,style)
      met,ink,cov=oracle(raw,fallback,value,0,style,style&1,clip)
      assert bf[14:20]==met and bf[20:116]==ink and bf[116:212]==cov
      count+=1;total+=1
    ar,af,_=a.glyph(e,0x61,3,1,(0,32,0,24),measure=True)
    br,bf,_=b.glyph(e,0x61,3,1,(0,32,0,24),measure=True)
    assert not(ar.p&1 or br.p&1) and af[:212]==bf[:212] and bf[14]==1
    count+=1;total+=1
   assert a.reu()==reu_a and b.reu()==reu_b,'all16MiB changed'
   item=dict(face=face,glyphs=count,control_instructions=a.used-start_a,candidate_instructions=b.used-start_b)
   item['ratio']=item['control_instructions']/item['candidate_instructions'];cases.append(item)
   print('FACEPASS',item,flush=True)
  native_cases=0
  if not smoke and not faults_only:
   for value in range(256):
    for style in range(8):
     for inverse in range(2):
      ar,af,_=a.glyph(entries[0],value,style,inverse,native=True)
      br,bf,_=b.glyph(entries[0],value,style,inverse,native=True)
      assert not(ar.p&1 or br.p&1) and af[:212]==bf[:212],('native A/B',value,style,inverse)
      met,ink,cov=oracle(b'',fallback,value,0,style,inverse,(0,32,0,24),native_only=True)
      assert bf[14:20]==met and bf[20:116]==ink and bf[116:212]==cov,('nativeoracle',value,style,inverse)
      native_cases+=1
  synthetic_result=synthetic_suite(a,b,fallback)if not smoke else None
  fault_result=fault_suite(a,b,pack,entries)if not smoke else None
  result=dict(status='passed',synthetic=synthetic_result,faults=fault_result,identity=identity,control_bytes=control_bytes,candidate_bytes=candidate_bytes,faces=cases,glyphs=total,native_cases=native_cases,scope='PrivateactualR23/frozenresident/provider/guard A/B; explicitCPUfontinstaller and privateleafRAMloading, noteditor/nativeintegration. Full64KiBRAM everycall/all16MiBREUperface.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,flush=True)
 finally:a.close();b.close()

def run_ink(out,previous,smoke):
 frozen,identity=geos.freeze(out,previous)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 _,control_bytes=build(out/'control',frozen,True,CANDIDATE)
 _,candidate_bytes=build(out/'candidate',frozen,True,CANDIDATE/'ink-only')
 assert hashlib.sha256((out/'control/r23.bin').read_bytes()).hexdigest()=='eed49e6d0e2873b60981df64047c7d20b16b4233e56b35f2f128c03da9001670','inkcontrolmustmatch released3820B bytecandidate'
 print('INKLINK',control_bytes,candidate_bytes,flush=True)
 dll=geos.grid.runner(out);a=Fixture(out,frozen,dll,out/'control');b=Fixture(out,frozen,dll,out/'candidate')
 pack=(out/'control/font-pack.bin').read_bytes();entries=[pack[32+i*16:48+i*16]for i in range(43)];fallback=(frozen/'fonts/native8.bin').read_bytes();faces=[];total=0
 try:
  reu_a=a.reu();reu_b=b.reu()
  def check(e,raw,value,style,inverse,clip=None,encoding=0,native=False):
   nonlocal total
   ar,af,au=a.glyph(e,value,style,inverse,clip,encoding=encoding,native=native)
   br,bf,bu=b.glyph(e,value,style,inverse,clip,encoding=encoding,native=native,ink=clip is not None)
   assert not(ar.p&1 or br.p&1),(value,style,inverse,ar.a,br.a)
   h=bf[18];assert af[:20]==bf[:20] and 1<=h<=24
   met,inkbits,cov=oracle(b''if native else raw,fallback,value,encoding,style,inverse,clip or(0,32,0,24),native_only=native)
   assert bf[14:20]==met and bf[20:20+h*4]==inkbits[:h*4],('inkonlyoracle',value,style,inverse)
   assert af[20:116]==inkbits and af[116:212]==cov
   assert bf[20+h*4:212]==b.last_before[0x8800+20+h*4:0x8800+212],'unusedcoverage/inkafterheightwritten'
   total+=1;return au,bu
  for face,e in enumerate(entries[:1]if smoke else entries):
   offset=int.from_bytes(e[8:11],'little');raw=pack[offset:offset+int.from_bytes(e[11:13],'little')];useda=usedb=0;start=total
   samples=[(0x41,0,0),(0x47,7,1),(0xc1,3,0)]if smoke else[(v,v&7,(v>>3)&1)for v in range(256)]
   for args in samples:
    x,y=check(e,raw,*args);useda+=x;usedb+=y
   if not smoke:
    for value in range(32,32+e[13]):
     for style in range(8):
      for inverse in range(2):
       x,y=check(e,raw,value,style,inverse,(0,32,0,24),encoding=2);useda+=x;usedb+=y
    for style in range(8):
     for clip in [(0,0,0,0),(1,32,0,24),(0,31,0,24),(3,17,1,7),(32,0,24,0),(0,32,1,23),(7,19,8,18)]:
      x,y=check(e,raw,0x47,style,style&1,clip);useda+=x;usedb+=y
    # Full-output generic API remains exact even after a short-output call.
    for ctx in (0x8800,0x8801,0x8d00):
     ar,af,_=a.glyph(e,0x41,7,1,(1,31,1,23),ctx=ctx);br,bf,_=b.glyph(e,0x41,7,1,(1,31,1,23),ctx=ctx)
     assert not(ar.p&1 or br.p&1)and af[:212]==bf[:212],('strictfullpostink',face,ctx)
   assert a.reu()==reu_a and b.reu()==reu_b,'all16MiBchanged'
   item=dict(face=face,cases=total-start,control_instructions=useda,candidate_instructions=usedb,ratio=useda/usedb);faces.append(item);print('INKFACE',item,flush=True)
  native_cases=0;fault_result=None
  if not smoke:
   for value in range(256):
    for style in range(8):
     for inverse in range(2):check(entries[0],b'',value,style,inverse,native=True);native_cases+=1
   # Explicit owner/frame rejection is before any source/frame/loan writes.
   for owner in (0,1,2,3,5,255):
    b.m.write(b.s['se_f_owner'],owner)
    before=b.read(0,65536);r,_=b.fast_call(b.symbols['se_geos_catalog_ink_preview'],x=0,y=0x88);after=b.read(0,65536);want=bytearray(before);want[0x100:0x200]=after[0x100:0x200]
    assert r.p&1 and r.a==0xb2 and after==want
   b.m.write(b.s['se_f_owner'],4)
   for ctx in (0,0x8801,0x8700,0x8d00,0xb100,0xc510,0xc600,0xff80):
    before=b.read(0,65536);r,_=b.fast_call(b.symbols['se_geos_catalog_ink_preview'],x=ctx&255,y=ctx>>8);after=b.read(0,65536);want=bytearray(before);want[0x100:0x200]=after[0x100:0x200]
    assert r.p&1 and r.a==0x90 and after==want,('inkcontextopaque',ctx)
   old=b.symbols['se_geos_catalog_glyph_preview'];b.symbols['se_geos_catalog_glyph_preview']=b.symbols['se_geos_catalog_ink_preview']
   try:fault_result=fault_suite(a,b,pack,entries)
   finally:b.symbols['se_geos_catalog_glyph_preview']=old
  result=dict(status='passed',kind='separateexplicitinternalink-only',identity=identity,control_bytes=control_bytes,candidate_bytes=candidate_bytes,faces=faces,cases=total,native_cases=native_cases,faults=fault_result,additional_owner_context_refusals=14 if not smoke else 0,scope='Newowner4/context8800 entry metrics+inkheightonly; coverageandinkafterheight MUSTstayuntouched. Strictfullpublic/privateCGoutputs exact. ActualFDguard/fullRAM/all16MiB, no production/native claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('INKPASS',out,flush=True)
 finally:a.close();b.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--ink-smoke',action='store_true');p.add_argument('--ink-run',action='store_true');p.add_argument('--run',action='store_true');p.add_argument('--smoke',action='store_true');p.add_argument('--faults',action='store_true');p.add_argument('--fixture',type=Path,default=DEFAULT);a=p.parse_args()
 if not(a.run or a.smoke or a.faults or a.ink_smoke or a.ink_run):print('Prepared privateR23candidate; --smoke firstactualface, --run fullsuite.');raise SystemExit
 out=ROOT/'build/geos-catalog-byte-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 if a.ink_smoke or a.ink_run:run_ink(out,a.fixture.resolve(),a.ink_smoke)
 else:run(out,a.fixture.resolve(),a.smoke,a.faults)
