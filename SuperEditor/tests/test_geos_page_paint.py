"""Private actual C22 cache-backed GEOS page painter with real R21/R16 leaves.

No editor-mode or native claim. The cache is seeded through actual checked
logical-FE writes; canonical source/history remain independently guarded.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import test_geos_row_leaf as leaf
import test_fold_controller as resident
from bindings import verify
from overlays import wrap,HEADER
from redraw_model import native_text,screen_code

S=0x8B40;F=0x8880

def run(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(out,base,paint_source):
 assert (ROOT/'src/render/geos/cache.s').exists(),'parent cache implementation not released yet'
 seal=verify(base/'build/editor.prg',base/'build/editor.lbl');report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];digest=seal['digest']
 d=out/'paint';d.mkdir()
 cache_source=(ROOT/'src/render/geos/cache.s').read_text()
 imports=sorted(set(re.findall(r'\bse_\w+',cache_source))-{n for n in re.findall(r'\bse_gp_cache_\w+',cache_source)})
 (d/'editor-api.inc').write_text('.import '+','.join(imports)+'\n')
 (d/'entry.s').write_text('''.setcpu "6502"
.import se_f_owner,se_overlay_frame
.import se_gp_paint_begin,se_gp_paint_step,se_gp_paint_cancel
.import se_gp_cache_open,se_gp_cache_write,se_gp_cache_read,se_gp_cache_guard
.segment "CODE"
.byte '''+','.join('$'+digest[i:i+2] for i in range(0,32,2))+'''
.export entry
entry:
 lda se_f_owner
 cmp #4
 bne busy
 lda se_overlay_frame
 beq begin
 cmp #1
 beq step
 cmp #2
 beq cancel
 cmp #3
 beq open
 cmp #4
 beq write
 cmp #5
 beq read
 cmp #6
 beq guard
 lda #$90
 sec
 rts
begin:jmp se_gp_paint_begin
step:jmp se_gp_paint_step
cancel:jmp se_gp_paint_cancel
open:jmp se_gp_cache_open
write:jmp se_gp_cache_write
read:jmp se_gp_cache_read
guard:jmp se_gp_cache_guard
busy:lda #$B2
 sec
 rts
''')
 objects=[]
 for src in [d/'entry.s',paint_source,ROOT/'src/render/geos/cache.s']:
  p=d/(src.stem+'.o');run('ca65','-g','-I',d,'-I','src','-o',p,src);objects.append(p)
 run(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'bindings.s',*objects)
 run('ca65','-g','-o',d/'bindings.o',d/'bindings.s')
 (d/'image.cfg').write_text('MEMORY {IMAGE:file=%O,start=$B000,size=$1000;} SEGMENTS {CODE:load=IMAGE,type=ro;RODATA:load=IMAGE,type=ro;}\n')
 run('ld65','-C',d/'image.cfg','-o',d/'paint.bin','-Ln',d/'paint.lbl','-m',d/'paint.map',*objects,d/'bindings.o')
 payload=(d/'paint.bin').read_bytes();assert len(payload)<=4096
 image=wrap(payload,1,22,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(d/'paint.seo').write_bytes(image)
 return payload,image

class Fixture(leaf.Fixture):
 def import_image(self,image):
  # Replace only fixture-owned catalog identities, through real re-import after
  # removing their old entry. Canonical document/object ownership is unchanged.
  identity,slot=image[6],image[5]
  for i in range(self.s['se_overlay_capacity']):
   if self.m.read(self.s['se_overlay_ids']+i)==identity and self.m.read(self.s['image_slot']+i)==slot:
    self.m.write(self.s['se_overlay_ids']+i,0);self.m.write(self.s['se_overlay_active']+slot,0)
  super().import_image(image)
 def paint_call(self,op=1,owner=4):
  self.put('se_f_owner',owner,1);self.m.write(self.s['se_overlay_frame'],op)
  phase=self.m.read(S+3);dma=self.get('se_reu_dma_calls',2);instructions=self.total_instructions;calls=self.get('se_overlay_calls',2)
  r=self.call_overlay(22,1);self.calls+=1
  if op<2 and hasattr(self,'profile'):
   delta=(self.get('se_reu_dma_calls',2)-dma)&65535
   if op==1:assert delta<=3 and ((self.get('se_overlay_calls',2)-calls)&65535)<=2,('boundedSTEP-DMA-or-leafcalls',phase,delta)
   self.profile['instructions']+=self.total_instructions-instructions;self.profile['DMAs']+=delta
   self.profile['leaf_calls']+=((self.get('se_overlay_calls',2)-calls)&65535)-1
   if op==1 and phase in(1,14) and delta==2 and self.read(0x917a,4)==b'\x00\x81\x20\x00':self.profile['prefix_reads']+=1
  return r
 def call_overlay(self,identity,slot):
  r,n=self.m.call(self.s['se_overlay_call'],a=identity,x=slot,limit=4_000_000);self.total_instructions+=n;return r
 def cache_write(self,offset,data):
  self.m.load(0x8000,data);self.m.load(0x9178,offset.to_bytes(2,'little')+(0x8000).to_bytes(2,'little')+len(data).to_bytes(2,'little'))
  r=self.paint_call(4);assert not r.p&1,('cachewrite',r.a)
 def seed(self,records,caret_row=255):
  self.put('se_i_ready',0,1);self.put('se_l_valid',0,1);self.put('se_r_valid',0,1)
  self.put('se_f_owner',4,1);r=self.paint_call(3);assert not r.p&1,('cacheopen',r.a)
  header=bytearray(self.read(0x8500,64));header[0]=1;header[1]=len(records);header[42]=caret_row
  for i,record in enumerate(records):self.cache_write(0x200+i*0x800,record)
  self.cache_write(0,header)
 def page(self):
  self.profile=dict(instructions=0,DMAs=0,leaf_calls=0,prefix_reads=0)
  r=self.paint_call(0);assert not r.p&1 and r.a==1,('begin',r.a,r.p)
  steps=0;phases=[]
  while r.a:
   phases.append(self.read(S+3,4));r=self.paint_call();steps+=1
   assert not r.p&1,('paint',r.a,r.p,steps,self.read(S,32).hex())
   assert steps<20000,('nonconvergence',self.read(S,32).hex())
  assert self.m.read(S)==0 and self.m.read(S+1)==1
  return steps,phases

def record(chars,styles=None,roles=None,start=0,top=16,kind=0,height=9,caret=None,left=None,right=None,flags=0):
 n=len(chars);assert n<=160
 styles=styles if styles is not None else bytes(n);roles=roles if roles is not None else bytes(n)
 data=bytearray(1800);data[0:3]=start.to_bytes(3,'little');data[3:6]=(start+n).to_bytes(3,'little');data[6:9]=(start+n+1).to_bytes(3,'little');data[9:12]=start.to_bytes(3,'little');data[12:14]=n.to_bytes(2,'little');data[14:18]=bytes([height,top,kind,1]);data[21:23]=bytes([6,flags]);data[32:32+n]=chars;data[192:192+n]=styles;data[352:352+n]=roles
 # Independent existing expanded font oracle, not product metrics/maps.
 font=(ROOT/'assets/fonts/generated/bsw9.bin').read_bytes();widths=(ROOT/'assets/fonts/generated/bsw9-widths.bin').read_bytes();native=(ROOT/'assets/fonts/generated/native8.bin').read_bytes()
 x=[0]
 for c,style in zip(chars,styles):
  advance=8 if kind else widths[leaf.model.native(c)]+(style&1)+(style&2)
  x.append(x[-1]+advance)
 data[512:512+2*(n+1)]=b''.join(v.to_bytes(2,'little') for v in x)
 left=list(range(start,start+n+1)) if left is None else left;right=list(range(start,start+n+1)) if right is None else right
 data[834:834+3*(n+1)]=b''.join(v.to_bytes(3,'little') for v in left);data[1317:1317+3*(n+1)]=b''.join(v.to_bytes(3,'little') for v in right)
 if caret is not None:data[18]=1;data[19:21]=x[caret].to_bytes(2,'little')
 return bytes(data)

def oracle(f,records,before,caret_row=255):
 out=bytearray(before);palette=bytes([1,3,7,10,14,1,1,7,13,5,15,7,3,1]);leaf.model.PALETTE=palette
 caret=f.get('se_hot_caret');anchor=f.get('se_sel_anchor');marked=f.get('se_sel_mark',1);lo,hi=sorted([anchor,caret])
 for row in range(2,24):
  runs=[];code=None
  for line,rec in enumerate(records):
   count=int.from_bytes(rec[12:14],'little');top=rec[15];height=rec[14];y=top-row*8
   if not (-height<y<8):continue
   chars=rec[32:32+count];styles=rec[192:192+count];roles=rec[352:352+count];flags=[]
   left=[int.from_bytes(rec[834+i*3:837+i*3],'little') for i in range(count+1)]
   right=[int.from_bytes(rec[1317+i*3:1320+i*3],'little') for i in range(count+1)]
   for l,r in zip(left,right):flags.append((rec[22]&1) | (2 if marked and lo<=r<hi else 0) | (4 if line==caret_row and rec[18] and l<=caret<=r else 0))
   if rec[16]:code=(chars,roles,flags,y)
   else:
    runs.append((chars,styles,roles,bytes(flags[:-1]),int.from_bytes(rec[512:514],'little'),y))
    if flags[-1]&4:
     x=int.from_bytes(rec[19:21],'little')
     if x<320:runs.append((b' ',b'\0',b'\0',bytes([(rec[22]&1)|4]),x,y))
  out,_,_,_=leaf.model.Fixture.oracle(f,runs,row,(0,320,0,8),out)
  if code is not None:
   chars,roles,flags,y=code;assert y==0
   for col,(ch,role,flag) in enumerate(zip(chars,roles,flags)):
    if col==40:break
    screen=screen_code(ch)
    if flag&1:screen|=128
    if flag&6:screen^=128
    for scan in range(8):out[0x6000+row*320+col*8+scan]=f.native[(screen&127)*8+scan]^(255 if screen&128 else 0)
    out[0x4000+row*40+col]=(palette[role]<<4)|6
   if flags[-1]&4 and len(chars)<40:
    col=len(chars);screen=screen_code(32)|((0 if flags[-1]&1 else 1)<<7)
    for scan in range(8):out[0x6000+row*320+col*8+scan]=f.native[(screen&127)*8+scan]^(255 if screen&128 else 0)
    out[0x4000+row*40+col]=0x16
 return out

def assert_frame(f,records,before,caret_row=255):
 expected=oracle(f,records,before,caret_row)
 for row in range(2,24):
  for start,n in [(0x6000+row*320,320),(0x4000+row*40,40)]:
   actual=f.read(start,n);want=expected[start:start+n]
   assert actual==want,('pixel/attribute',row,hex(start),next((i,a,b) for i,(a,b) in enumerate(zip(actual,want)) if a!=b))
 # All chrome, bitmap tail, savedFS and parent page controller remain exact.
 for start,n in [(0x4000,80),(0x43c0,40),(0x6000,640),(0x7e00,512),(0x8ee0,0x254),(0xc600,1024)]:
  assert f.read(start,n)==before[start:start+n],('outsidebody/FS/page/shim',hex(start))
 return 56320

def main():
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');p.add_argument('--base',type=Path,default=ROOT/'agentsworking/evidence/M7/20261025T022319293214Z-geos-editor-poisoned-final-cpu/diverse/fixture');p.add_argument('--paint-source',type=Path,default=ROOT/'src/render/geos/page-paint.s');p.add_argument('--combined',action='store_true');p.add_argument('--geometry',action='store_true');a=p.parse_args();stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'build/geos-page-paint'/stamp;out.mkdir(parents=True)
 if a.base:
  base=out/'fixture';shutil.copytree(a.base,base);report=json.loads((base/'build/editor-report.json').read_text());names=json.loads((base/'freeze.json').read_text())['names']
 else:base,report,names=resident.freeze(out)
 resident.cpu_editor.ROOT=resident.editor_fixture.ROOT=base;resident.cpu_editor.NAMES=resident.editor_fixture.NAMES=names
 ls,rowpayload,rowimage=leaf.build(out,base);payload,image=build(out,base,a.paint_source);f=Fixture(out,ls,rowpayload,rowimage);f.calls=0;cases=[];frames=0;pixels=0;steps_all=0;profiles=[]
 paint_symbols={n:int(v,16) for v,n in re.findall(r'^al ([0-9A-Fa-f]+) \.([^\s]+)',(out/'paint/paint.lbl').read_text(),re.M)}
 def prepare(records,caret_row=255):
  f.put('se_f_owner',0,1);f.command(50);f.position(0)
  f.put('se_f_owner',4,1);f.seed(records,caret_row)
 def check(records,caret_row=255):
  nonlocal frames,pixels,steps_all
  f.seed(records,caret_row);before=f.read(0,65536);canonical=f.canonical();reu=f.reu();leases=f.get('se_doc_read_locks',1)
  steps,phases=f.page();steps_all+=steps
  assert f.canonical()==canonical,('canonical',frames,[(i,a,b) for i,(a,b) in enumerate(zip(canonical,f.canonical())) if a!=b][:20])
  assert f.reu()==reu and f.get('se_doc_read_locks',1)==leases
  assert f.read(0x4800,1024)==before[0x4800:0x4c00], 'nativefont changed'
  pixels+=assert_frame(f,records,before,caret_row);frames+=1
  profiles.append(dict(frame=frames,records=len(records),steps=steps,**f.profile,bitmap=hashlib.sha256(f.read(0x6280,7040)).hexdigest(),attributes=hashlib.sha256(f.read(0x4050,880)).hexdigest()))
  return before,phases
 try:
  f.import_image(image);f.source(native_text('i')*70000+b'\r',banks=2);f.import_image(rowimage);f.import_image(image);f.m.load(0x4800,f.native)
  chars=native_text('First GEOS live cache line');rec=record(chars);check([rec]);cases.append('firstactualC22/cacheOPEN-write-guard/R21/all22strips/ninthrow/source-history16MiBREU-shimguard')
  if not a.smoke:
   # Five64-byte fetch chunks exercise count160 and offset128*3 crossing255.
   check([record(native_text('i')*160)]);cases.append('160smallglyphs/64-64-32chunking/canonicaloffset384/appendhistogram')
   # Use exact-length plans, then a shared-strip second run and aligned code.
   text=native_text('gjpqy lower/UPPER');records=[record(text,styles=bytes(i%4 for i in range(len(text))),roles=bytes(i%14 for i in range(len(text))),top=16),record(native_text('Next line heading'),roles=bytes([2])*17,start=30,top=25,flags=1),record(native_text('lda #$12 ; code')+bytes([0xa0,0xff]),roles=bytes(i%14 for i in range(16)),start=60,top=40,kind=1,height=8),record(native_text('back to proportional'),start=90,top=48)]
   check(records);cases.append('twointersectingproseruns/9throw-descenders/majority-tilecolors/native8code/R21-R16-R21fontreload')
   records=[record(bytes((j*11+i)&255 for j in range(40)),roles=bytes((j+i)%14 for j in range(40)),start=i*41,top=16+i*8,kind=1,height=8) for i in range(22)]
   check(records);cases.append('22nativecodephysicalrows/all40cells/graphicsA0-FF/rolepalette')
   # Selection and caret use actual public selection/caret services before cache
   # capture. Prefix maps can retain canonical anchors above16-bit boundaries.
   for caret,anchor,index in [(0,None,0),(5,None,5),(16,None,16),(10,3,10),(3,10,3)]:
    f.put('se_f_owner',0,1);f.command(50)
    if anchor is not None:f.position(anchor);f.command(68)
    f.position(caret)
    rec=record(native_text('i')*16,caret=index)
    check([rec],0)
   f.put('se_f_owner',0,1);f.command(50);f.position(66005)
   left=list(range(66000,66017));right=list(left);left[5]=66003;right[5]=66007
   rec=record(native_text('i')*16,start=66000,caret=5,left=left,right=right)
   check([rec],0);cases.append('sourcecaret-first-middle-EOF/selectedcaret-union/reversedselection/LEFT-RIGHTpreimage/24bitanchors')
   for kind in [0,1]:
    f.put('se_f_owner',0,1);f.command(50);f.position(0)
    check([record(b'',caret=0,height=8 if kind else 9,kind=kind)],0)
   check([]);cases.append('emptyEOF-proseandnativecaret/empty22strip-page')
   # Same independently parsed422B fixture for before/after performance.
   import test_geos_editor as editor_model
   data=(ROOT/'agentsworking/evidence/M7/20261025T022319293214Z-geos-editor-poisoned-final-cpu/diverse/three-lines-source.bin').read_bytes()
   geometry=editor_model.source_lines(data,f.widths)
   records=[record(data[l.start:l.end],start=l.start,top=l.top,height=l.height) for l in geometry]
   check(records);cases.append('independentlyparsed422B-diverse20record-performancefixture')
   if a.combined:
    for kind in [0,1]:
     f.put('se_f_owner',0,1);f.command(50);f.position(2);f.command(68);f.position(7)
     rec=record(native_text('iiiiiiiiiiii'),flags=1,caret=7,kind=kind,height=8 if kind else 9)
     check([rec],0)
    cases.append('inverse-plus-selection-plus-caret-union/prose-and-native8')
   if a.geometry:
    records=[record(b'A',top=16+i*9) for i in range(20)]
    f.seed(records);assert not f.paint_call(0).p&1;before=f.read(0x4000,16000);canonical=f.canonical();reu=f.reu()
    for _ in range(7):r=f.paint_call();assert not r.p&1
    assert f.read(0x4000,16000)==before,'certification touched pixels'
    r=f.paint_call(2);assert not r.p&1 and r.a==0 and f.m.read(S)==f.m.read(S+1)==0 and f.canonical()==canonical and f.reu()==reu
    cases.append('cancel-mid-geometrycertification/no-pixels-source-REU-changes')


   # Wrong owners must not inspect or change opaquepaint/frame/phase storage.
   for owner in [0,1,2,3,5,255]:
    f.m.load(S,bytes((i*37+owner)&255 for i in range(192)));f.m.load(F,bytes((i*13+owner)&255 for i in range(704)));f.m.load(0x8d00,bytes((i*17+owner)&255 for i in range(1152)))
    for op in [0,1,2]:
     before=f.read(F,0x9180-F);reu=f.reu();r=f.paint_call(op,owner);assert r.p&1 and r.a==0xb2 and f.read(F,0x9180-F)==before and f.reu()==reu
     # Call the actual exported helper too: the private entry's own guard must
     # not conceal a missing owner check inside a reusable operation.
     name=['se_gp_paint_begin','se_gp_paint_step','se_gp_paint_cancel'][op]
     r,_=f.m.call(paint_symbols[name]);assert r.p&1 and r.a==0xb2 and f.read(F,0x9180-F)==before and f.reu()==reu
   f.m.load(S,bytes(192));cases.append('owner4beforeallstateaccess/foreignowner0-1-2-3-5-255/opaque704-192-1152bytes')
   # Real counted source leases are external; cancel/fault never releases them.
   f.put('se_f_owner',0,1);f.command(50);f.position(0)
   for _ in range(3):assert not f.call('se_doc_read_acquire').p&1
   f.seed([record(native_text('Cancelable'))]);r=f.paint_call(0);assert not r.p&1
   for _ in range(10):r=f.paint_call();assert not r.p&1
   before=f.canonical();reu=f.reu();r=f.paint_call(2);assert not r.p&1 and r.a==0 and f.m.read(S)==f.m.read(S+1)==0 and f.canonical()==before and f.reu()==reu and f.get('se_doc_read_locks',1)==3
   for _ in range(3):assert not f.call('se_doc_read_release').p&1
   cases.append('cancelpartiallypaintedpage/foreign3leases-retained/noREUwrite')
   # Resource faults are real catalog admissions, not substituted renderers.
   for missing,records in [('geosrow',[record(native_text('Missing R21'))]),('grid80',[record(native_text('Missing R16'),kind=1,height=8)])]:
    f.seed(records);r=f.paint_call(0);assert not r.p&1
    identity=21 if missing=='geosrow' else 16
    at=next(i for i in range(f.s['se_overlay_capacity']) if f.m.read(f.s['se_overlay_ids']+i)==identity and f.m.read(f.s['image_slot']+i)==0)
    f.m.write(f.s['se_overlay_ids']+at,0);f.m.write(f.s['se_overlay_active'],0);before=f.canonical();reu=f.reu()
    for _ in range(1000):
     r=f.paint_call()
     if r.p&1:break
    assert r.p&1 and r.a==0x17 and f.m.read(S)==f.m.read(S+1)==0 and f.canonical()==before and f.reu()==reu
    f.m.write(f.s['se_overlay_ids']+at,identity)
   cases.append('actualmissingR21-R16catalog/refuses-unpublishedpage/canonicalforeignREU-preserved')
   # Header/provider identity faults abort without trusting cached glyphs.
   for field,delta,error in [('se_gc_width',1,0x74),('se_gc_epoch',1,0x18),('se_r_revision',1,0x74)]:
    f.seed([record(native_text('Guard failure'))]);assert not f.paint_call(0).p&1
    width=2 if field=='se_gc_epoch' else 4 if field=='se_r_revision' else 1
    old=f.get(field,width);f.put(field,old^delta,width);before=f.read(0x4000,8000);reu=f.reu();r=f.paint_call();assert r.p&1 and r.a==error and f.m.read(S)==f.m.read(S+1)==0 and f.reu()==reu
    f.put(field,old,width)
   cases.append('injected-width-epoch-revision-witness-faults/failclosed-beforepaint')
   for kind,byte,value in [(0,14,7),(0,12,161),(0,16,2),(1,15,17)]:
    rec=bytearray(record(native_text('Bad record'),kind=kind,height=8 if kind else 9));rec[byte]=value;f.seed([rec]);assert not f.paint_call(0).p&1;before=f.canonical();reu=f.reu()
    for _ in range(100):
     r=f.paint_call()
     if r.p&1:break
    assert r.p&1 and r.a==0x90 and f.m.read(S)==f.m.read(S+1)==0 and f.canonical()==before and f.reu()==reu
   cases.append('invalidheight-count-kind-codealignment/refusal-beforeleaf/sourceunchanged')
   if a.geometry:
    for records in [[record(b'A',top=25),record(b'B',top=16)],[record(b'A',top=16),record(b'B',top=24)],[record(b'A',top=16),record(b'B',top=191),record(b'C',top=190)]]:
     f.seed(records);assert not f.paint_call(0).p&1;before=f.read(0x4000,16000);canonical=f.canonical();reu=f.reu()
     for _ in range(100):
      r=f.paint_call()
      if r.p&1:break
     assert r.p&1 and r.a==0x90 and f.m.read(S)==f.m.read(S+1)==0 and f.canonical()==canonical and f.reu()==reu
     assert f.read(0x4000,16000)==before,'geometry certification painted before rejection'
    cases.append('ordered-nonoverlapping-geometrycertification/unsorted-overlap-tailrefusal-beforepixels')

  result=dict(status='passed',resident_sha256=report['sha256'],paint_payload=len(payload),frames=frames,pixels=pixels,attributes=frames*880,steps=steps_all,calls=f.calls,peak_instructions=f.peak,cases=cases,profiles=profiles,scope='Private actual C22 cache+R21/R16; cache fixtures, not complete editor/native integration.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 except BaseException as e:
  (out/'failure.json').write_text(json.dumps(dict(error=repr(e),cases=cases),indent=2)+'\n');(out/'failure-c64.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
 print('OUTPUT',out)
 evidence=ROOT/'agentsworking/evidence/M7'/(stamp+'-geos-page-paint');evidence.mkdir(parents=True);shutil.copytree(out,evidence/'build')
 source_names=['src/render/geos/page-paint.s','src/render/geos/page-paint.inc','src/render/geos/cache.s','src/render/geos/editor.inc','src/render/geos/editor-row-entry.s','src/render/geos/row.s','src/render/geos/row.inc','src/render/geos/row-validate.s','src/render/geos/row-resolve.s','src/render/geos/measure.s','src/render/geos/glyph.s','src/render/geos/api.inc','src/render/geos/assets.s','src/render/narrow/grid.inc','cfg/geos-editor-row.cfg']
 with zipfile.ZipFile(evidence/'leaf-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for name in source_names:z.write(ROOT/name,name)
 with zipfile.ZipFile(evidence/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for name in ['tests/test_geos_page_paint.py','tests/test_geos_row_leaf.py','tests/test_geos_row.py','tests/test_geos_glyphs.py','tests/test_fold_controller.py','tests/test_fold_leaves.py','tools/editor_fixture.py','tools/cpu_editor.py','tools/peddle.py','tools/overlays.py','tools/bindings.py','tools/module_bindings.py']:z.write(ROOT/name,name)
 if (base/'product-sources.zip').exists():shutil.copy2(base/'product-sources.zip',evidence/'resident-product-sources.zip')
 shutil.copy2(a.paint_source,evidence/'paint-source-used.s')
 (evidence/'fonts').mkdir()
 for name in ['bsw9-original.bin','bsw9-widths.bin','bsw9.bin','native8.bin','manifest.json']:shutil.copy2(ROOT/'assets/fonts/generated'/name,evidence/'fonts'/name)
 print('EVIDENCE',evidence)
if __name__=='__main__':main()
