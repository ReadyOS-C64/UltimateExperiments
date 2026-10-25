"""Private C22 literal identity affinities, ABI2 comparison only.

Actual C21 produces every row. The test explicitly poisons both derived affinity
arrays through resident checked DMA, then invokes the actual candidate painter.
No product files/build/native emulator are changed; ABI3 migration is separate.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,subprocess,sys,zipfile,ctypes as C
import test_geos_fold_editor as fold
import test_geos_semantic_editor as semantic
from test_geos_nowrap_editor import nowrap_expected
from dataclasses import replace
from overlays import wrap,HEADER
ROOT=fold.ROOT;BASE=ROOT/'build/geos-incremental-editor/20261025T081538083121Z/fixture'
CANDIDATE=ROOT/'src/render/geos/identity-candidate/page-paint.s'


def command(*a):
 p=subprocess.run(list(map(str,a)),cwd=ROOT,capture_output=True,text=True);assert not p.returncode,p.stdout+p.stderr


def build(out,frozen):
 out.mkdir();original=out/'original';original.mkdir()
 with zipfile.ZipFile(frozen/'product-sources.zip')as z:
  for n in z.namelist():
   if n.startswith(('src/','cfg/')):z.extract(n,original)
 policy=(ROOT/'src/render/geos/tail-policy.inc').read_bytes()
 assert policy.decode().index('lda R+GPR_TAIL_VALID')<policy.decode().index('lda R+GPR_FLAGS'),'parent offscreen-tail policy fix not released'
 (original/'src/render/geos/tail-policy.inc').write_bytes(policy) #sole explicit baseline source fix
 r=json.loads((frozen/'build/editor-report.json').read_text());s=r['symbols'];seal=r['resident_binding']['digest'];api=out/'api';api.mkdir()
 (api/'editor-api.inc').write_text('.import se_overlay_call,se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+seal[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 objs=[]
 for tag,path in [('entry',original/'src/render/geos/page-paint-entry.s'),('paint',CANDIDATE),('pan',original/'src/render/geos/native-pan.s'),('cache',original/'src/render/geos/cache-paint.s')]:
  obj=out/(tag+'.o');command('ca65','-g','-I',api,'-I',original/'src','-o',obj,path);objs.append(obj)
 command(sys.executable,'tools/module_bindings.py','--report',frozen/'build/editor-report.json','--output',out/'bindings.s',*objs);command('ca65','-o',out/'bindings.o',out/'bindings.s')
 command('ld65','-C',original/'cfg/geos-editor-page.cfg','-o',out/'paint.bin','-Ln',out/'paint.lbl','-m',out/'paint.map',*objs,out/'bindings.o')
 raw=(out/'paint.bin').read_bytes();image=wrap(raw,1,22,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(seal));(out/'paint.seo').write_bytes(image)
 # Independently retain original C22 code with the same zero-growth tail fix.
 command('ca65','-g','-I',api,'-I',original/'src','-o',out/'baseline-paint.o',original/'src/render/geos/page-paint.s')
 baseobjs=[objs[0],out/'baseline-paint.o',*objs[2:]]
 command('ld65','-C',original/'cfg/geos-editor-page.cfg','-o',out/'baseline.bin',*baseobjs,out/'bindings.o')
 baseline=(out/'baseline.bin').read_bytes();assert len(baseline)==4096
 baseimage=wrap(baseline,1,22,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(seal));(out/'baseline.seo').write_bytes(baseimage)
 return image,baseimage


class Fixture(fold.Fixture):
 def invoke(self,op):
  self.put('se_overlay_frame',op,1);before=self.read(0,65536);canonical=self.canonical();r,n=self.fast_call(self.s['se_overlay_call'],a=22,x=1)
  after=self.read(0,65536);want=bytearray(before)
  names=[('se_overlay_active',2),('se_overlay_busy',2),('se_overlay_frame',16),('se_overlay_loads',2),('se_overlay_hits',2),('se_overlay_calls',2),('candidate',1),('call_slot',1),('call_id',1),('call_result',1),('crc_remaining',2),('se_crc_value',2),('ovl_ptr',2),('se_v_length',3),('se_v_span',3),('se_v_old_span',3),('se_v_hot_end',3),('se_v_cache_count',2),('se_v_cache_base',3),('se_v_cache_end',3),('se_v_phys',3),('se_v_pos',3),('se_object_id',12),('se_overlay_header',36),('validate_index',1),('validate_extent',1),('validate_type',1),('doc_cache_slot',1),('screen_ptr',2),('text_ptr',2)]
  ranges=[(self.s[k],self.s[k]+w)for k,w in names]+[(0x100,0x200),(0x4000,0x43E8),(0x5000,0x6000),(0x6000,0x7F40),(0x8000,0x8800),(0x8880,0x8C00),(0x8D00,0x9040),(0x9178,0x917E),(0xA000,0xC000),(0xCBD5,0xCBD6),(self.s['se_reu_c64'],self.s['dma_physical']+1),(0xDF00,0xDF0B)]
  for a,b in ranges:want[a:b]=after[a:b]
  assert after==want,('wholeRAM',op,next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,want))if a!=b))
  assert not self.dll.fr_writes() and not self.dll.fr_bad() and self.canonical()==canonical and self.read(0xC600,1024)==self.shim,('read-only painter',op)
  return r,n
 def poison(self,seed):
  raw,bank=self.raw_cache();handle=self.get('se_gc_handle',1)
  for row in range(raw[1]):
   for at in range(842,1814,128):
    count=min(128,1814-at);data=bytes((seed+row*13+i*71)&255 for i in range(at,at+count));self.m.load(0x9000,data)
    self.put('se_reu_logical',handle,1);self.put('se_reu_offset',0x200+row*2048+at,2);self.put('se_reu_c64',0x9000,2);self.put('se_reu_length',count,2)
    r=self.call('se_reu_copy',0);assert not r.p&1,('derived-map poison',r.a)
  after,_=self.raw_cache()
  for row in range(raw[1]):
   at=0x200+row*2048;assert after[at:at+842]==raw[at:at+842]
  return after


def run(out,previous,smoke=False):
 frozen,identity=semantic.geos.freeze(out,previous);image,baseimage=build(out/'candidate',frozen)
 print('FIT',len(image)-HEADER,flush=True)
 semantic.geos.grid.editor_fixture.ROOT=semantic.geos.grid.cpu_editor.ROOT=frozen;semantic.geos.grid.editor_fixture.NAMES=semantic.geos.grid.cpu_editor.NAMES=identity['names']
 dll=fold.retention.runner(out);f=Fixture(out,frozen,dll,True);g=fold.Fixture(out,frozen,dll,True);f.assets['geospaint']=image;g.assets['geospaint']=baseimage
 fonts={n:(frozen/'fonts'/n).read_bytes()for n in semantic.geos.GEOS_FONTS+('native8.bin',)};cases=[]
 def plain_expected(data):
  # Canonical parser knows an unterminated code fence owns the empty EOF row.
  # Extend only this local oracle's geometry; no emitted packet is consulted.
  original=semantic.geos.source_lines;kind=semantic.classify(data).eof_kind
  def lines(raw,widths,**kwargs):
   result=list(original(raw,widths,**kwargs))
   if kind==5 and result and result[-1].start==len(raw):
    last=result[-1];top=(last.top+7)&~7
    if top>=192:result.pop()
    else:result[-1]=replace(last,top=top,height=8)
   return tuple(result)
  semantic.geos.source_lines=lines
  try:return nowrap_expected(f,data,fonts)
  finally:semantic.geos.source_lines=original
 def check(data,tag,folds=None,first=2,end=24,poison=True):
  f.m.write(0xCF90,0);f.m.write(0x9148,0);f.render();g.render();canonical=f.canonical();expected=plain_expected(data)if folds is None else folded_expected(data,folds)
  actual=(f.read(0x6000,8000),f.read(0x4000,1000));baseline=(g.read(0x6000,8000),g.read(0x4000,1000))
  if actual!=expected[:2]:
   for name,raw in [('candidate',b''.join(actual)),('baseline',b''.join(baseline)),('expected',expected[0]+expected[1]),('ram',f.read(0,65536)),('cache',f.raw_cache()[0])]: (out/(tag+'-'+name+'.bin')).write_bytes(raw)
   raise AssertionError((tag,'normal integrated candidate',{'baseline_equal':actual==baseline,'bitmap_diff':[(i,a,b)for i,(a,b)in enumerate(zip(actual[0],expected[0]))if a!=b][:12],'attr_diff':[(i,a,b)for i,(a,b)in enumerate(zip(actual[1],expected[1]))if a!=b][:12]}))
  assert(f.read(0x6000,8000),f.read(0x4000,1000))==(g.read(0x6000,8000),g.read(0x4000,1000)),(tag,'baseline A/B')
  before=f.raw_cache()[0];f.poison(37)if poison else None
  # Deliberate pixel poison outside/inside bands makes unintended full repaint
  # or missed dirty strip writes visible, independently of source-map poisoning.
  eb,ea=expected[:2];bits=bytearray(eb);attrs=bytearray(ea)
  for i in range(640,7680):bits[i]^=(i*13+37)&255
  for i in range(80,960):attrs[i]^=0xEF
  f.m.load(0x6000,bits);f.m.load(0x4000,attrs)
  f.m.write(0x9148,2 if(first,end)!=(2,24)else 0);f.m.write(0x914E,first);f.m.write(0x914F,end);f.put('se_f_owner',4,1);f.m.load(0x8B40,b'\0\0')
  reu=f.reu();f.audit_begin()
  r,used=f.invoke(0);assert not r.p&1 and r.a==1,(tag,'begin',r.a,r.p);steps=0
  while r.a:
   r,n=f.invoke(1);used+=n;steps+=1;assert not r.p&1 and steps<8000,(tag,'step',r.a,r.p,steps,f.read(0x8B40,16).hex())
  f.dll.fr_end();assert f.reu()==reu,(tag,'whole16MiB changed')
  wb=bytearray(bits);wa=bytearray(attrs);wb[first*320:end*320]=eb[first*320:end*320];wa[first*40:end*40]=ea[first*40:end*40]
  actual=f.read(0x6000,8000);colors=f.read(0x4000,1000)
  assert actual==wb,(tag,'poisoned arrays bitmap',next((i,a,b)for i,(a,b)in enumerate(zip(actual,wb))if a!=b))
  assert colors==wa,(tag,'poisoned arrays attrs',next((i,a,b)for i,(a,b)in enumerate(zip(colors,wa))if a!=b))
  assert f.canonical()==canonical;f.put('se_f_owner',0,1)
  cases.append(dict(tag=tag,rows=before[1],first=first,end=end,poisoned_affinity_bytes=before[1]*972,steps=steps,instructions=used));print('PASS',cases[-1],flush=True)
 def folded_expected(data,folds):
  bits,attrs,rows,model=fold.raster(data,fonts,folds,top=f.get('se_v_top'),caret=f.get('se_hot_caret'),anchor=f.get('se_sel_anchor')if f.get('se_sel_mark',1)else None,nowrap=bool(f.get('se_l_mode',1)),pan=f.get('se_l_pan'))
  matrix,colors,popup=semantic.geos.grid.logical_ui(f,data);bits,attrs=semantic.geos.with_chrome(bits,attrs,matrix,colors,fonts['native8.bin'],popup);return bits,attrs,rows,model
 def setup(data,at=0,top=None):
  for x in(f,g):
   x.source(data);x.command(99)
   if at:x.position(at)
   if top is not None:x.put('se_v_top',top)
 try:
  data=semantic.FIXTURE;setup(data,15);check(data,'mixed-full')
  if not smoke:
   for tag,data,at in [('inline',semantic.INLINE_FIXTURE,5),('empty',b'',0),('CRs',b'\r\r\r',2),('exact320',b'.'*160+b'\rTail',160),('eof-native',semantic.geos.native_text(':::basic\r10 PRINT "Hi"\r'),22)]:
    setup(data,min(at,len(data)));check(data,tag)
   for tag,anchor,caret in [('forward',10,55),('reverse',55,10),('zero',15,15)]:
    data=semantic.FIXTURE;setup(data,caret)
    for x in(f,g):x.put('se_sel_mark',1,1);x.put('se_sel_anchor',anchor)
    check(data,'selection-'+tag)
   data=fold.TINY;setup(data)
   for x in(f,g):x.command(115)
   folds=[replace(v,flags=1)for v in fold.tree(data)];check(data,'folded',folds)
   region=folds[0]
   for x in(f,g):x.position(region.end);x.put('se_sel_mark',1,1);x.put('se_sel_anchor',region.hidden+1)
   check(data,'folded-hidden-selection',folds)
   for pan in(1,5,7,319):
    data=semantic.geos.native_text('**'+'Wim '*30+'**\r:::basic\r10 PRINT "'+'W'*50+'"\r:::\rTail.')
    setup(data,8)
    for x in(f,g):x.command(75);x.put('se_l_pan',pan);x.put('se_l_manual',1,1);x.put('se_sel_mark',1,1);x.put('se_sel_anchor',2)
    check(data,'nowrap-pan-'+str(pan))
   # Canonical borrow/carry across64KiB remains full24bit, never glyph-sized.
   for top in(0xFFF8,0x10000):
    data=b'x'*(top-1)+b'\r'+semantic.geos.native_text('Ordinary high source.\rFollowing row.\rTail.')
    setup(data,top+9,top)
    for x in(f,g):x.put('se_sel_mark',1,1);x.put('se_sel_anchor',top+4)
    check(data,'high-canonical-'+hex(top))
   data=fold.TINY;setup(data)
   for x in(f,g):x.command(115)
   folds=[replace(v,flags=1)for v in fold.tree(data)];region=folds[0]
   marker_width=sum(fonts['bsw9-widths.bin'][semantic.geos.native(v)]for v in data[region.start:region.hidden-1])
   for pan in(5,marker_width+2):
    for x in(f,g):
     x.position(region.hidden-1);x.put('se_l_mode',1,1);x.put('se_l_manual',1,1);x.put('se_l_pan',pan);x.put('se_sel_mark',1,1);x.put('se_sel_anchor',region.end)
    check(data,'fold-marker-clipped-'+str(pan),folds)
   # Operation entry ownership must remain opaque even with poisoned maps.
   foreign_reu=f.reu();f.audit_begin();owner_calls=0
   for owner in(0,1,2,3,5,255):
    f.put('se_f_owner',owner,1)
    for op in(0,1,2):
     phase=f.read(0x8B40,192);pixels=f.read(0x6000,8000)+f.read(0x4000,1000);r,n=f.invoke(op)
     assert r.p&1 and r.a==0xB2 and f.read(0x8B40,192)==phase and f.read(0x6000,8000)+f.read(0x4000,1000)==pixels,('foreign owner',owner,op,r.a)
     owner_calls+=1
   f.dll.fr_end();assert f.reu()==foreign_reu;f.put('se_f_owner',0,1)
   data=semantic.FIXTURE;setup(data,15)
   for first,end in[(2,3),(3,4),(4,8),(19,24)]:check(data,'dirty-'+str(first)+'-'+str(end),first=first,end=end)
  result=dict(status='passed',identity=identity,tail_policy_sha256=hashlib.sha256((ROOT/'src/render/geos/tail-policy.inc').read_bytes()).hexdigest(),baseline_tail_fix=True,payload_bytes=len(image)-HEADER,cases=cases,foreign_owner_calls=0 if smoke else owner_calls,pixels_checked=len(cases)*64000,attrs_checked=len(cases)*1000,scope='Private ABI2 comparator only: actual C21 packets, A/B original C22 with identical parent offscreen-tail fix, poisoned identity-affinity arrays, full pixel/source/shim/RAM and read-only16MiB guards. ABI3 production migration not performed.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close();g.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--smoke',action='store_true');a=p.parse_args();out=ROOT/'build/geos-identity-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture,a.smoke)
