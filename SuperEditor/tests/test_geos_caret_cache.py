"""Private sealed R27 against a REAL current-editor FE page; no product build.

Owner4 acquisition/release and the root postpaint publication leg are explicit
component seams until the combined C21/R27 product is released. Glyph/layout/
source/cache bytes are produced by the actual editor, never host seeded.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,subprocess,sys,shutil
from dataclasses import replace
import test_geos_fold_editor as fold
from overlays import wrap,HEADER
from geos_fold_model import raster
from geos_fold_model import classify,native
ROOT=fold.ROOT
DEFAULT=ROOT/'build/geos-fold-editor/20261025T060733594632Z/fixture'
STATE=0xCF90
def command(*args):
 p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True)
 if p.returncode:raise AssertionError(p.stdout+p.stderr)
def build(out,frozen,leaf_source):
 out.mkdir();r=json.loads((frozen/'build/editor-report.json').read_text());digest=r['resident_binding']['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2] for i in range(0,32,2))+'\n.endmacro\n')
 (out/'render/geos').mkdir(parents=True)
 for name in ('caret-cache.s','caret-cache.inc','cache.s','editor.inc'):shutil.copy2(leaf_source/name,out/'render/geos'/name)
 objects=[]
 for name in ('caret-cache','cache'):
  obj=out/(name+'.o');command('ca65','-g','-I',out,'-I','src','-o',obj,out/'render/geos'/(name+'.s'));objects.append(obj)
 if 'se_gcc_status' in (out/'render/geos/caret-cache.s').read_text():
  # Geometry-only component seam: owner4 never calls the new root/UI helpers.
  # A deliberately failing stub makes accidental use visible to this test.
  (out/'uncalled-ui.s').write_text('.setcpu "6502"\n.export se_gcc_status,se_gcc_cell\n.segment "CODE"\nse_gcc_status:\nse_gcc_cell:\nlda #$EE\nsec\nrts\n')
  command('ca65','-o',out/'uncalled-ui.o',out/'uncalled-ui.s');objects.append(out/'uncalled-ui.o')
 command(sys.executable,'tools/module_bindings.py','--report',frozen/'build/editor-report.json','--output',out/'aliases.s',*objects)
 command('ca65','-g','-o',out/'aliases.o',out/'aliases.s');(out/'leaf.cfg').write_text('MEMORY {R:file=%O,start=$A000,size=$1000;} SEGMENTS {CODE:load=R,type=ro;RODATA:load=R,type=ro;}')
 command('ld65','-C',out/'leaf.cfg','-o',out/'caret-cache.bin','-Ln',out/'caret-cache.lbl','-m',out/'caret-cache.map',*objects,out/'aliases.o')
 payload=(out/'caret-cache.bin').read_bytes();s=r['symbols'];image=wrap(payload,0,27,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/'caret-cache.seo').write_bytes(image);return payload,image

class Fixture(fold.Fixture):
 def import_leaf(self,image):
  self.m.load(self.s['se_overlay_header'],image[:HEADER]);self.m.load(0x5000,image[HEADER:]);assert not self.call('se_overlay_import').p&1
 def invoke(self,op,payload):
  self.put('se_overlay_frame',op,1);before=self.read(0,65536);canonical=self.canonical()
  if op==0 and getattr(self,'trace_once',False):
   self.trace_once=False
   for k,v in [('pc',self.s['se_overlay_call']),('sp',0xFD),('p',0x24),('a',27),('x',0),('y',0)]:getattr(self.m.lib,'zeropage_peddle_set_'+k)(self.m.handle,v)
   self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);trace=[];n=0
   for _ in range(100000):
    r=self.m.regs()
    if r.pc==0x2FF:break
    trace.append((hex(r.pc),self.m.read(r.pc),r.a,r.x,r.y,r.p));trace=trace[-160:];self.m.lib.zeropage_peddle_step_instruction(self.m.handle);n+=1
   self.trace_path.write_text(json.dumps(trace,indent=2)+'\n')
  else:r,n=self.fast_call(self.s['se_overlay_call'],a=27,x=0)
  after=self.read(0,65536)
  wanted=bytearray(before)
  pairs=[('se_overlay_active',2),('se_overlay_busy',2),('se_overlay_loads',2),('se_overlay_hits',2),('se_overlay_calls',2),('candidate',1),('call_slot',1),('call_id',1),('call_result',1),('crc_remaining',2),('se_crc_value',2),('ovl_ptr',2),('se_v_length',3),('se_v_span',3),('se_v_old_span',3),('se_v_hot_end',3),('se_v_cache_count',2),('se_object_id',12),('validate_index',1),('validate_extent',1),('validate_type',1),('doc_cache_slot',1),('screen_ptr',2)]
  allowed=[(self.s[k],self.s[k]+w) for k,w in pairs]+[(0x100,0x200),(STATE,STATE+82),(0x8080,0x8088),(0x8100,0x8120),(0x8500,0x8540),(0x9178,0x917E),(0x4000,0x43E8),(0x6000,0x7F40),(0x5000,0x5000+len(payload)),(0xA000,0xA000+len(payload)),(self.s['se_reu_c64'],self.s['dma_physical']+1),(self.s['se_overlay_header'],self.s['se_overlay_header']+36),(0xDF00,0xDF0B)]
  for a,b in allowed:wanted[a:b]=after[a:b]
  assert after==wanted,('wholeRAM',op,next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,wanted)) if a!=b))
  assert self.canonical()==canonical and self.get('se_f_owner',1)==before[self.s['se_f_owner']]
  return r,n

def run(out,previous,smoke=False,leaf_source=ROOT/'src/render/geos',faults_only=False,pan_miss=False):
 frozen,identity=fold.geos.freeze(out,previous);payload,image=build(out/'leaf',frozen,leaf_source)
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=frozen;fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=identity['names']
 fonts={n:(frozen/'fonts'/n).read_bytes() for n in fold.geos.GEOS_FONTS+('native8.bin',)}
 dll=fold.retention.runner(out);f=Fixture(out,frozen,dll,True);cases=[]
 try:
  data=fold.geos.native_text('Wim. Mixed text\rSecond line\rTail.');f.source(data);f.command(99);f.render();f.import_leaf(image)
  matrix,colors,popup=fold.geos.grid.logical_ui(f,data)
  def expected(caret):
   b,a,_,_=raster(data,fonts,[],top=f.get('se_v_top'),caret=caret,nowrap=bool(f.get('se_l_mode',1)),pan=f.get('se_l_pan'))
   return fold.geos.with_chrome(b,a,matrix,colors,fonts['native8.bin'],popup)
  assert (f.read(0x6000,8000),f.read(0x4000,1000))==expected(f.get('se_hot_caret'))
  beforebits=f.read(0x6000,8000);beforeattrs=f.read(0x4000,1000);reu=f.reu();cache,bank=f.raw_cache();f.put('se_f_owner',4,1)
  r,n=f.invoke(2,payload);assert not r.p&1 and r.a==0,(r.a,r.p)
  assert f.read(0x6000,8000)==beforebits and f.read(0x4000,1000)==beforeattrs
  base=bank*65536;after=f.reu();want=bytearray(reu);plainbits,plainattrs=expected(None);want[base+0xB200:base+0xD140]=plainbits;want[base+0xD140:base+0xD528]=plainattrs;assert after==want,'capture whole16MiB/base without caret'
  assert not f.call('se_er_published').p&1
  f.put('se_f_owner',0,1);f.command(2);assert f.get('se_hot_caret')==1;f.put('se_f_owner',4,1)
  preattempt=f.read(STATE,82);preattempt_header=f.raw_cache()[0][:64];f.trace_once=True;f.trace_path=out/'first-attempt-trace.json'
  r,used=f.invoke(0,payload);assert not r.p&1 and r.a==1,(r.a,r.p,dict(state=preattempt.hex(),header=preattempt_header.hex(),sequence=f.get('se_e_draw_sequence',2),mode=f.get('se_mode',1),ui=f.get('se_e_ui',1),presentation=f.get('se_r_presentation',1),keydiff=[(i,a,b) for i,(a,b) in enumerate(zip(preattempt[7:44],preattempt_header[4:41])) if a!=b]));steps=0
  while r.a==1:
   r,n0=f.invoke(1,payload);used+=n0;steps+=1;assert not r.p&1 and steps<25,(r.a,r.p)
  assert r.a==0 and (f.read(0x6000,8000),f.read(0x4000,1000))==expected(1)
  newcache,_=f.raw_cache();allowed=[(0,64)]+[(0x200+i*0x800,0x220+i*0x800) for i in range(cache[1])];want=bytearray(after);newreu=f.reu()
  for a,b in allowed:want[base+a:base+b]=newreu[base+a:base+b]
  assert newreu==want,'restore writes outside header/prefixes'
  cases.append(dict(tag='actualFE-capture-unselected-base/realhot-right/exactbitmapattrs',steps=steps,instructions=used))
  print('FIRST R27 PASS: real C21 FE page -> exact caret-free bitmapcache -> actual hot-right -> exact independent pixels/attributes; source/shim/wholeRAM/16MiB guards',flush=True)
  if not smoke:
   f.call('se_er_published');saved=f.read(STATE,82)
   def unchanged_call(op,expected_a,carry=False):
    bits=f.read(0x6000,8000)+f.read(0x4000,1000);reu=f.reu();r,n=f.invoke(op,payload)
    assert r.a==expected_a and bool(r.p&1)==carry,('fault-result',op,r.a,r.p,expected_a,carry)
    assert f.read(0x6000,8000)+f.read(0x4000,1000)==bits and f.reu()==reu,'refusal wrote VIC/REU'
    return n
   # Wrong phase owners must be opaque even when the entire private frame is
   # poisoned. CF90..CFFF stops immediately before I/O; never poison D000.
   for owner in (0,1,2,3,5,255):
    for op in ((0,2,255) if owner in (0,1) and pan_miss else (0,1,2,255)):
     f.put('se_f_owner',owner,1);f.m.load(STATE,bytes([0xA5])*112);phase=f.read(0x8D00,1152);cold=f.read(STATE,112)
     unchanged_call(op,0xB2,True)
     assert f.read(STATE,112)==cold and f.read(0x8D00,1152)==phase,'wrongowner inspected phase'
   f.put('se_f_owner',4,1);f.m.load(STATE,saved)
   unchanged_call(255,0x90,True)
   # All of these are explicit service/context fault injections. They do not
   # claim physical input, a real provider reset, or production fault recovery.
   for name,size in [('se_e_draw_sequence',2),('se_gc_epoch',2),('se_gc_handle',1),('se_v_top',3),('se_l_pan',3),('se_ef_generation',2),('se_r_revision',4),('se_reu_epoch',2)]:
    if name not in f.s:continue
    original=f.read(f.s[name],size);f.m.load(STATE,saved);f.m.write(f.s[name],original[0]^1)
    unchanged_call(0,0x18 if name=='se_reu_epoch' else 2,name=='se_reu_epoch');f.m.load(f.s[name],original)
   f.m.load(STATE,saved);f.put('se_sel_mark',1,1);f.put('se_sel_anchor',0);unchanged_call(0,2);f.put('se_sel_mark',0,1)
   # Actual typed cache transport writes malformed row prefixes; no physical
   # bank shortcut is used to inject them. Every STEP must reject before paint.
   labels={line.split()[2].lstrip('.'):int(line.split()[1],16) for line in (out/'leaf/caret-cache.lbl').read_text().splitlines() if line.startswith('al ')}
   prefix=bytes(f.raw_cache()[0][0x200:0x220])
   def cache_write(offset,raw):
    f.m.load(0x8080,raw);f.m.load(0x9178,offset.to_bytes(2,'little')+bytes([0x80,0x80])+len(raw).to_bytes(2,'little'))
    r,n=f.fast_call(labels['se_gp_cache_write']);assert not r.p&1,(r.a,r.p)
   for off,value in ((15,15),(15,192),(14,7),(14,10),(12,162),(13,1)):
    f.m.load(STATE,saved);r,_=f.invoke(0,payload);assert r.a==1 and not r.p&1
    mutant=bytearray(prefix);mutant[off]=value;cache_write(0x200,mutant)
    unchanged_call(1,0x90,True);cache_write(0x200,prefix)
   # The previous rectangle comes from an earlier completed paint. Corrupted
   # geometry must not reach even the first tiny tile-restoration DMA.
   for off,value in ((49,2),(50,15),(50,192),(51,0),(51,33),(52,7),(52,10),(53,2)):
    f.m.load(STATE,saved);f.m.write(STATE+off,value);r,_=f.invoke(0,payload);assert r.a==1 and not r.p&1
    unchanged_call(1,0x90,True)
   for name,size in [('se_hot_caret',3),('se_sel_anchor',3),('se_sel_mark',1)]:
    f.m.load(STATE,saved);r,_=f.invoke(0,payload);assert r.a==1 and not r.p&1
    original=f.read(f.s[name],size);f.m.write(f.s[name],original[0]^1);unchanged_call(1,2);f.m.load(f.s[name],original)
   handle=f.get('se_gc_handle',1);physical=f.m.read(f.s['se_reu_map']+handle)
   for name,index in [('se_reu_logical_owner',handle),('se_reu_physical_owner',physical),('se_reu_map',handle)]:
    at=f.s[name]+index;original=f.m.read(at);f.m.load(STATE,saved);f.m.write(at,0);unchanged_call(0,2);f.m.write(at,original)
    f.m.load(STATE,saved);r,_=f.invoke(0,payload);assert r.a==1 and not r.p&1
    f.m.write(at,0);unchanged_call(1,0x18,True);f.m.write(at,original)
   # Actual X map pair for caret1: reverse it to require an impossible negative
   # glyph width. This is service fault injection, not host-produced geometry.
   packet=f.raw_cache()[0];oldx=bytes(packet[0x200+518+2:0x200+518+6]);f.m.load(STATE,saved);r,_=f.invoke(0,payload);assert r.a==1
   cache_write(0x200+518+2,bytes([10,0,9,0]));unchanged_call(1,0x90,True);cache_write(0x200+518+2,oldx)
   f.m.load(STATE,saved);cases.append(dict(tag='ownership/context/prefix/previous-rectangle-refusal',wrong_owner_calls=22 if pan_miss else 24,context_faults=8,malformed_prefixes=6,malformed_rectangles=8,midstep_input_changes=3,foreign_capability_refusals=6,nonmonotonic_xmap=1))
   print('FAULT R27 PASS: owner opacity, selection/context misses, typed malformed-prefix and old-rectangle refusal before VIC/REU writes',flush=True)
   (out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
  if not smoke and not faults_only:
   def exercise(raw,tag,target,*,nowrap=False,pan=0,folded=False,origin=0,initial_visible=True):
    nonlocal data,matrix,colors,popup
    data=raw;f.put('se_f_owner',0,1);f.source(data);f.command(99)
    folds=[]
    if folded:
     f.command(115);folds=[replace(t,flags=1) for t in fold.tree(data)]
    if nowrap:f.command(77)
    if origin:f.position(origin)
    if pan:
     f.put('se_l_pan',pan);f.put('se_l_manual',1,1)
    f.render();f.import_leaf(image);matrix,colors,popup=fold.geos.grid.logical_ui(f,data)
    def model(caret):
     b,a,rr,sem=raster(data,fonts,folds,top=f.get('se_v_top'),caret=caret,nowrap=nowrap,pan=pan)
     b,a=fold.geos.with_chrome(b,a,matrix,colors,fonts['native8.bin'],popup);return b,a,rr
    baseline=(f.read(0x6000,8000),f.read(0x4000,1000));wanted_model=model(origin if initial_visible else None)[:2]
    if baseline!=wanted_model:
     (out/(tag+'-initial-actual.bin')).write_bytes(baseline[0]+baseline[1]);(out/(tag+'-initial-expected.bin')).write_bytes(wanted_model[0]+wanted_model[1])
     raise AssertionError((tag,'initialfullpaintoracle',dict(pan=f.get('se_l_pan'),manual=f.get('se_l_manual',1),mode=f.get('se_l_mode',1),caret=f.get('se_hot_caret'),top=f.get('se_v_top')),[(i,a,b)for i,(a,b)in enumerate(zip(baseline[0],wanted_model[0]))if a!=b][:16],[(i,a,b)for i,(a,b)in enumerate(zip(baseline[1],wanted_model[1]))if a!=b][:16]))
    cache,bank=f.raw_cache();reu=f.reu();f.put('se_f_owner',4,1)
    if pan and pan_miss:
     unchanged_call(2,2);assert f.read(STATE,1)==bytes(1)
     cases.append(dict(tag=tag,nonzero_pan_capture_miss=True,unchanged_actual_fullpaint=True));return
    r,capinstructions=f.invoke(2,payload);assert not r.p&1 and r.a==0,(tag,'capture',r.a,r.p)
    assert (f.read(0x6000,8000),f.read(0x4000,1000))==baseline
    plainb,plaina,_=model(None);want=bytearray(reu);base=bank*65536;want[base+0xB200:base+0xD140]=plainb;want[base+0xD140:base+0xD528]=plaina;assert f.reu()==want,(tag,'exactbasecapture/wholeREU')
    beforehit=f.reu();f.call('se_er_published');f.put('se_f_owner',0,1)
    # Actual window micromodule moves, no PC/data-seeded caret or cached maps.
    for _ in range(abs(target-origin)):
     r=f.call('se_hot_call',7 if target>origin else 6);assert not r.p&1,(tag,'hotmove',r.a)
    assert f.get('se_hot_caret')==target;f.put('se_f_owner',4,1)
    dmabefore=f.get('se_reu_dma_calls',2);bytesbefore=f.get('se_reu_dma_bytes')
    r,used=f.invoke(0,payload);assert not r.p&1 and r.a==1,(tag,'try',r.a,r.p)
    steps=0
    while r.a==1:
     r,n0=f.invoke(1,payload);used+=n0;steps+=1;assert not r.p&1 and steps<=23,(tag,'step',r.a,r.p)
    assert r.a==0;bits,attrs,rr=model(target)
    if (f.read(0x6000,8000),f.read(0x4000,1000))!=(bits,attrs):
     (out/(tag+'-actual.bin')).write_bytes(f.read(0x6000,8000)+f.read(0x4000,1000));(out/(tag+'-expected.bin')).write_bytes(bits+attrs)
     raise AssertionError((tag,'pixeloracle',[(i,a,b) for i,(a,b) in enumerate(zip(f.read(0x6000,8000),bits)) if a!=b][:12]))
    index=next(i for i,row in enumerate(rr) if row.start<=target<row.end or target==row.end and row.reason in (1,2))
    styles,_,_,code=classify(data);row=rr[index]
    def advance(at):return 8 if code[at] else fonts['bsw9-widths.bin'][native(data[at])]+(styles[at]&1)+(styles[at]&2)
    xx=sum(advance(at) for at in range(row.start,target))-(pan if nowrap else 0)
    width=advance(target) if target<row.end else 6 if row.marker else 8 if row.height==8 else 5
    visible=int(max(0,xx)<min(320,xx+width));xout=max(0,xx) if visible else 0
    after=f.reu();wanted=bytearray(beforehit);oldrow=cache[42]
    wanted[base+41]=1;wanted[base+42]=index;wanted[base+43:base+45]=xout.to_bytes(2,'little');wanted[base+45]=visible
    if oldrow!=index:
     at=base+0x200+oldrow*0x800;wanted[at+18:at+21]=bytes(3);wanted[at+26]=0
    at=base+0x200+index*0x800;wanted[at+18]=visible;wanted[at+19:at+21]=xout.to_bytes(2,'little');wanted[at+26]=1
    assert after==wanted,(tag,'exactheader/prefixwitness/whole16MiB',next((hex(i-base),a,b) for i,(a,b) in enumerate(zip(after,wanted)) if a!=b))
    cases.append(dict(tag=tag,steps=steps,instructions=used,capture_instructions=capinstructions,caret=target,row=index,x=xout,visible=visible,dma_commands=(f.get('se_reu_dma_calls',2)-dmabefore)&65535,dma_bytes=(f.get('se_reu_dma_bytes')-bytesbefore)&0xFFFFFF))
    (out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
   exercise(fold.geos.native_text('First\rSecond line\rLast.'),'proseCR-tail5',5)
   exercise(fold.geos.native_text('First\rSecond line\rLast.'),'proseEOF-tail5',23)
   code=fold.geos.native_text(':::basic\r10 PRINT "HI"\r:::\rLast.')
   exercise(code,'BASIC-native-code-tail8',code.index(13,code.index(b'10')))
   asm=fold.geos.native_text(':::asm\rloop: lda #$01 ;comment\r:::\rLast.')
   exercise(asm,'ASM-native-code-glyph',asm.index(fold.geos.native_text('lda'))+1)
   region=fold.geos.native_text(':::region A\rhidden\r:::end\rTail')
   exercise(region,'collapsed-region-plus-tail6',region.index(13),folded=True)
   rows=fold.geos.native_text('\r'.join(f'Row{i:02}' for i in range(24)))
   exercise(rows,'ninthrow-clipped-at-bottom',rows.index(fold.geos.native_text('Row19')))
   exercise(b'.'*200+fold.geos.native_text('\rTail'),'nowrap161glyph-rightpartial',160,nowrap=True,pan=1,initial_visible=False)
   exercise(fold.geos.native_text('Wim. **bold** and *italic* ')*4+fold.geos.native_text('\rTail'),'nowrap-signedleftpartial',2,nowrap=True,pan=3,initial_visible=not pan_miss)
  result=dict(status='passed',scope='private R27 component on frozen realFE page; explicitowner4/postpaint-publication seams, no integrated speed/native claim',resident_sha256=identity['prg_sha256'],disk_sha256=identity['disk_sha256'],payload_bytes=len(payload),cases=cases)
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=DEFAULT);p.add_argument('--out',type=Path);p.add_argument('--smoke',action='store_true');p.add_argument('--faults-only',action='store_true');p.add_argument('--pan-miss',action='store_true');p.add_argument('--leaf-source',type=Path,default=ROOT/'src/render/geos');a=p.parse_args();out=a.out or ROOT/'build/geos-caret-cache'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True,exist_ok=True);run(out,a.base,a.smoke,a.leaf_source,a.faults_only,a.pan_miss)
