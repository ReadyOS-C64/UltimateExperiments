"""Private sealed R30 plain nine-pixel row shift primitive; no editor fastpath.
Explicit caret-free bitmap/glyph inputs; independent bit-list shift/redraw oracle.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,random,re,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_row_leaf as leaf
from bindings import verify
from overlays import wrap
F=0x8b40;BASE=0x8200;TEMP=0x8380;SIZE=96

def run(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
def build(out,base):
 s=json.loads((base/'build/editor-report.json').read_text())['symbols'];d=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest'];(out/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2] for i in range(0,32,2))+'\n.endmacro\n');objects=[]
 for name in ['entry','patch']:
  p=out/(name+'.o');run('ca65','-g','-I',out,'-I','src','-o',p,ROOT/'src/render/geos/typing-candidate'/(name+'.s'));objects.append(p)
 run(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects);run('ca65','-g','-o',out/'aliases.o',out/'aliases.s');run('ld65','-C','cfg/overlay-r.cfg','-o',out/'typing.bin','-Ln',out/'typing.lbl','-m',out/'typing.map',*objects,out/'aliases.o')
 payload=(out/'typing.bin').read_bytes();assert len(payload)<4096 and payload[:16]==bytes.fromhex(d);ls={p[2].lstrip('.'):int(p[1],16) for line in (out/'typing.lbl').read_text().splitlines() if (p:=line.split()) and p[0]=='al'};assert ls['gt_base']==s['text_ptr'] and ls['gt_bitmap']==s['screen_ptr'];image=wrap(payload,0,30,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(out/'typing.seo').write_bytes(image)
 segments={}
 for name,p in zip(['entry','patch'],objects):
  t=subprocess.check_output(['od65','--dump-segments',p],text=True);segments[name]={n:int(v) for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',t,re.S)};assert all(segments[name].get(n,0)==0 for n in ['BSS','DATA','ZEROPAGE'])
 (out/'build.json').write_text(json.dumps(dict(payload_bytes=len(payload),new_BSS=0,new_ZP=0,caller_frame_bytes=SIZE,caller_base_bytes=360,caller_temp_bytes=40,segments=segments),indent=2)+'\n');return ls,payload,image

def bits(raw):return [(b>>(7-i))&1 for b in raw for i in range(8)]
def packed(row):return bytes(sum(row[j*8+i]<<(7-i) for i in range(8)) for j in range(40))
def at(y,col):return 0x6000+(y//8)*320+col*8+(y&7)
class Fixture(leaf.Fixture):
 def check(self,base,op,x,advance,oldwidth,top=16,glyph=None,caret=5,attr=0x16,mutate=None,error=0,owner=4,operation=0):
  glyph=glyph or bytes(9);assert len(base)==360 and len(glyph)==9;frame=bytes([op,0,top,advance])+x.to_bytes(2,'little')+oldwidth.to_bytes(2,'little')+bytes([caret,attr])+glyph+bytes([0xa7])*(SIZE-19)
  self.m.load(F,frame);self.m.load(BASE,base);self.m.load(TEMP,b'\xa7'*40);self.m.load(0x4000+(top//8)*40,bytes([attr])*80)
  # Actual live pixels may contain oldcaret. The trusted base is caret-free.
  for r in range(9):
   for c in range(40):self.m.write(at(top+r,c),base[r*40+c]^((r*31+c*7)&255))
  if mutate:mutate(self)
  self.put('se_f_owner',owner,1);self.m.load(self.s['se_overlay_frame'],bytes([operation]));before=self.read(0,65536);canonical=self.canonical();leases=self.get('se_doc_read_locks',1);r,used=self.m.call(self.s['se_overlay_call'],a=30,x=0,limit=3_000_000);after=self.read(0,65536);assert r.a==error and bool(r.p&1)==bool(error),(op,x,advance,oldwidth,top,error,r.a,r.p);self.last_used=used;self.row_calls+=1
  assert self.canonical()==canonical and self.get('se_doc_read_locks',1)==leases and self.read(0xc600,1024)==self.shim
  wanted=bytearray(before);self.loader_expected(wanted,before,after)
  if owner==4 and not operation:
   wanted[F+20:F+SIZE]=after[F+20:F+SIZE]
   for n in ['text_ptr','screen_ptr']:p=self.s[n];wanted[p:p+2]=after[p:p+2]
  if not error:
   assert after[F+19]==1 and after[F:F+19]==frame[:19]
   wanted[F+19]=1;wanted[TEMP:TEMP+40]=after[TEMP:TEMP+40]
   for y in range(9):
    old=bits(base[y*40:(y+1)*40]);ink=bits(bytes([glyph[y]]))[:advance];new=old[:x]+(ink+old[x:oldwidth] if op==0 else old[x+advance:oldwidth]);new=(new+[0]*320)[:320];cx=x+advance if op==0 else x
    for i in range(cx,min(320,cx+caret)):new[i]^=1
    for c,b in enumerate(packed(new)):wanted[at(top+y,c)]=b
  assert after==wanted,('wholeRAM/pixels/input/shim/neighbor/attrs/source guard',op,x,advance,top,next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,wanted)) if a!=b))
  return used

def makebase(rng,width):return b''.join(packed([rng.randrange(2) if x<width else 0 for x in range(320)]) for _ in range(9))
def font_gate(out,base):
 import importlib.util
 import test_geos_fold_editor as fold
 spec=importlib.util.spec_from_file_location('typing_font_build',ROOT/'src/render/geos/typing-candidate/build-font.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
 b=out/'font';ls,payload,image=builder.build(b,base);fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=base;names=json.loads((base/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names;dll=fold.geos.grid.runner(b);f=fold.Fixture(b,base,dll,True);calls=0;peak=0
 try:
  data=fold.geos.native_text('Plain row for font cache\rSecond plain row.');f.source(data);f.command(99);f.render()
  f.m.load(f.s['se_overlay_header'],image[:36]);f.m.load(0x5000,image[36:]);assert not f.call('se_overlay_import').p&1
  canonical=f.canonical();before=f.reu();oldram=f.read(0,65536);cache,bank=f.raw_cache();f.put('se_f_owner',4,1)
  def invoke(op):
   nonlocal calls,peak
   f.m.write(f.s['se_overlay_frame'],op);r,n=f.fast_call(f.s['se_overlay_call'],a=30,x=1);calls+=1;peak=max(peak,n);return r,n
  r,n=invoke(0);assert not r.p&1 and r.a==1,(r.a,r.p)
  steps=0
  while r.a==1:
   r,n=invoke(1);steps+=1;assert not r.p&1 and steps<140,(r.a,r.p,steps)
  assert r.a==0 and steps==133,(r.a,steps)
  font=(ROOT/'assets/fonts/generated/bsw9.bin').read_bytes();widths=(ROOT/'assets/fonts/generated/bsw9-widths.bin').read_bytes();expected=bytes(font[c*18+y*2] for c in range(128) for y in range(9))+widths;after=f.reu();start=bank*65536;assert after[start+0xe568:start+0xea68]==expected
  header=after[start+0xea68:start+0xea88];assert header[0]==0xa5 and header[1:6]==b'GTF1\1' and header[6:22]==payload[:16]
  wanted=bytearray(before);wanted[start+0xe568:start+0xea88]=after[start+0xe568:start+0xea88];assert after==wanted,'C30foreignREU/page/cacheprefix/basebitmapguard'
  assert f.canonical()==canonical and f.read(0xc600,1024)==f.shim
  # Full RAM guard, usingthe exact known foreground scratch andloader fields.
  now=f.read(0,65536);want=bytearray(oldram)
  fields=[('se_f_owner',1),('se_overlay_frame',1),('se_overlay_active',2),('se_overlay_busy',2),('se_overlay_loads',2),('se_overlay_hits',2),('se_overlay_calls',2),('candidate',1),('call_slot',1),('call_id',1),('call_result',1),('crc_remaining',2),('se_crc_value',2),('ovl_ptr',2),('se_v_length',3),('se_v_span',3),('se_v_old_span',3),('se_v_hot_end',3),('se_v_cache_count',2),('se_object_id',12),('validate_index',1),('validate_extent',1),('validate_type',1),('doc_cache_slot',1),('text_ptr',2),('screen_ptr',2)]
  allowed=[(f.s[k],f.s[k]+w) for k,w in fields]+[(0x100,0x200),(0x8b40,0x8b40+77),(0x8ba0,0x8ba5),(0x9000,0x9100),(0x8500,0x8540),(0x9178,0x917e),(0xb000,0xb000+len(payload)),(0x5000,0x5000+len(payload)),(f.s['se_reu_c64'],f.s['dma_physical']+1),(f.s['se_overlay_header'],f.s['se_overlay_header']+36),(0xdf00,0xdf0b)]
  for a,z in allowed:want[a:z]=now[a:z]
  assert now==want,('fontwholeRAM',next((hex(i),a,z) for i,(a,z) in enumerate(zip(now,want)) if a!=z))
  ready_reu=f.reu();r,n=invoke(0);assert not r.p&1 and r.a==0 and f.reu()==ready_reu
  # Wrongowners beforeframeaccess areopaque, includinga corruptframe/control.
  for owner in [0,1,2,3,5,255]:
   f.put('se_f_owner',owner,1);f.m.load(0x8b40,b'\xa7'*192);opaque=f.read(0x8b40,192)
   for op in [0,1,2,255]:r,n=invoke(op);assert r.a==0xb2 and r.p&1 and f.read(0x8b40,192)==opaque and f.reu()==ready_reu
  f.put('se_f_owner',4,1);faultgroups=[]
  def write_fe(offset,raw):
   f.m.load(0x8080,raw);f.put('se_reu_logical',f.get('se_gc_handle',1),1);f.put('se_reu_offset',offset,2);f.put('se_reu_c64',0x8080,2);f.put('se_reu_length',len(raw),2);assert not f.call('se_reu_copy',0).p&1
  def fresh():
   write_fe(0xea68,b'\0');r,n=invoke(0);assert r.a==1 and not r.p&1
  def finish(r):
   for _ in range(140):
    if r.p&1 or not r.a:return r
    r,n=invoke(1)
   raise AssertionError('unboundedC30')
  # Every cancellation checkpoint leaves READY0; onlyderivedtailmaychange.
  for stop in [0,1,64,127,128,129,132]:
   fresh()
   for _ in range(stop):r,n=invoke(1);assert r.a==1 and not r.p&1
   snapshot=f.reu();r,n=invoke(2);assert r.a==0 and not r.p&1 and f.reu()==snapshot and f.raw_cache()[0][0xea68]==0 and f.m.read(0x8ba0)==0
  faultgroups.append('cancelat0/1/64/127/128/129/132keepsREADY0')
  # CheckedDMA corruption ofactualwritten glyph must fail the real readbackCRC.
  fresh();r,n=invoke(1);assert r.a==1 and not r.p&1;actual=f.raw_cache()[0][0xe568];write_fe(0xe568,bytes([actual^1]));r=finish(r);assert r.a==0x94 and r.p&1 and f.raw_cache()[0][0xea68]==0
  fresh();r,n=invoke(1);r=finish(r);assert not r.p&1 and r.a==0 and f.raw_cache()[0][0xe568:0xea68]==expected
  faultgroups.append('checkedglyphcorruptionreadbackCRC94/noREADY/realrebuildretry')
  # Malformedcontinuations never reach arbitrarytypedREU offsets.
  for phase,index,block in [(3,0,0),(255,0,0),(1,128,0),(1,255,0),(2,0,5),(2,0,255)]:
   fresh();f.m.load(0x8ba0,bytes([phase,index,block]));snapshot=f.reu();r,n=invoke(1);assert r.a==0x90 and r.p&1 and f.reu()==snapshot and f.m.read(0x8ba0)==0
  faultgroups.append('phase/index/blockboundsbeforeDMA')
  handle=f.get('se_gc_handle',1);physical=f.m.read(f.s['se_reu_map']+handle)
  for name,index in [('se_gc_epoch',0),('se_reu_logical_owner',handle),('se_reu_physical_owner',physical),('se_reu_map',handle),('se_r_revision',0),('se_doc_epoch',0)]:
   fresh();at=f.s[name]+index;old=f.m.read(at);f.m.write(at,old^1 if name in ['se_r_revision','se_gc_epoch','se_doc_epoch'] else 0);snapshot=f.reu();r,n=invoke(1);assert r.p&1 and r.a and f.reu()==snapshot and f.m.read(0x8ba0)==0,(name,r.a,r.p);f.m.write(at,old)
  faultgroups.append('epoch/fullsourcekey/logicalphysicalFEownershipfaultsnoDMA')
  assert f.canonical()==canonical and f.read(0xc600,1024)==f.shim
  final=f.reu();wanted=bytearray(before);wanted[start+0xe568:start+0xea88]=final[start+0xe568:start+0xea88];assert final==wanted
  result=dict(status='passed',payload_bytes=len(payload),glyphs=128,readback_steps=5,build_steps=steps,wholeRAM=65536,wholeREU=16777216,foreign_owner_refusals=24,fault_groups=faultgroups,peak_instructions=peak,scope='PrivateC30 realGG+typedFEcache onactualrootpaintedpage; noR30editing integration.')
  (b/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('FONT C30 PASS',result,flush=True);return result
 finally:f.close()

def certificate_gate(out,base):
 import importlib.util,binascii
 import test_geos_fold_editor as fold
 spec=importlib.util.spec_from_file_location('typing_c6_build',ROOT/'src/render/geos/typing-candidate/build-c6.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder);b=out/'c6';payload,image=builder.build(b,base)
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=base;names=json.loads((base/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names;dll=fold.geos.grid.runner(b);f=fold.Fixture(b,base,dll,True)
 try:
  data=fold.geos.native_text('Plain row having ample room\rSecond plain row\rTail.');f.source(data);f.command(99);f.render()
  # Replace the C6 catalogentry using the actualchecked importer.
  for i in range(f.s['se_overlay_capacity']):
   if f.m.read(f.s['se_overlay_ids']+i)==6 and f.m.read(f.s['image_slot']+i)==1:f.m.write(f.s['se_overlay_ids']+i,0);f.m.write(f.s['se_overlay_active']+1,0)
  f.m.load(f.s['se_overlay_header'],image[:36]);f.m.load(0x5000,image[36:]);assert not f.call('se_overlay_import').p&1
  f.position(7);f.render();old,bank=f.raw_cache();row=old[42];prefix=old[0x200+row*0x800:0x220+row*0x800];revision=f.get('se_r_revision',4);v=fold.geos.native_text('X')[0];f.key(v);cert=f.read(0x9149,47)
  assert cert[0]==1,('certificate-notpublished',cert.hex(),f.read(0xcfe8,20).hex(),prefix.hex())
  assert cert[1]==row and cert[2:34]==prefix and cert[38]==7 and int.from_bytes(cert[40:44],'little')==revision
  assert int.from_bytes(cert[45:47],'little')==binascii.crc_hqx(cert[1:45],65535)
  assert f.merged()==data[:7]+bytes([v])+data[7:] and f.get('se_hot_pending',1)==1 and not f.get('se_f_owner',1)
  result=dict(status='passed',C6_payload_bytes=len(payload),certificate47=cert.hex(),source_bytes=len(data),scope='ActualC6MARK certificates afterrealpendinginsert, beforeR30consumer; nointegratedfastpath.')
  (b/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('C6 CERTIFICATE PASS',result,flush=True);return result
 except BaseException:
  (b/'failure-c64.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()

def worker_gate(out,base):
 """Actual C6 mutation -> independently guarded R30; resident route is explicit seam."""
 import importlib.util
 import test_geos_fold_editor as fold
 import test_geos_semantic_editor as semantic
 b=out/'worker-gate';b.mkdir(parents=True,exist_ok=True)
 def builder(name):
  spec=importlib.util.spec_from_file_location('typing_'+name,ROOT/'src/render/geos/typing-candidate'/('build-'+name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 _,font_payload,font_image=builder('font').build(b/'font',base)
 c6_payload,c6_image=builder('c6').build(b/'c6',base)
 labels,worker_payload,worker_image=builder('worker').build(b/'worker',base)
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=base
 names=json.loads((base/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names
 dll=fold.geos.grid.runner(b);f=fold.Fixture(b,base,dll,True);g=fold.Fixture(b,base,dll,True);frames=[];faults=[]
 fonts={n:(base/'fonts'/n).read_bytes() for n in fold.geos.GEOS_FONTS+('native8.bin',)}
 def install(image):
  slot,ident=image[5:7]
  for i in range(f.s['se_overlay_capacity']):
   if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)==slot:f.m.write(f.s['se_overlay_ids']+i,0)
  f.m.write(f.s['se_overlay_active']+slot,0);f.m.load(f.s['se_overlay_header'],image[:36]);f.m.load(0x5000,image[36:]);assert not f.call('se_overlay_import').p&1
 try:
  data=fold.geos.native_text('Plain row having ample room\rSecond plain row\rTail.')
  f.source(data);f.command(99);f.position(7);f.render();g.source(data);g.command(99);g.position(7);g.render();install(font_image);f.put('se_f_owner',4,1)
  f.m.write(f.s['se_overlay_frame'],0);r,n=f.fast_call(f.s['se_overlay_call'],a=30,x=1)
  for _ in range(140):
   if not r.a or r.p&1:break
   f.m.write(f.s['se_overlay_frame'],1);r,n=f.fast_call(f.s['se_overlay_call'],a=30,x=1)
  assert not r.p&1 and not r.a,('fontcache',r.a,r.p)
  f.put('se_f_owner',0,1);install(c6_image);install(worker_image)
  for tag,byte in [('insert-X',fold.geos.native_text('X')[0]),('insert-i',fold.geos.native_text('i')[0]),('backspace',0x14)]:
   f.key(byte);g.key(byte);before=f.canonical();data=f.merged();reu=f.reu();assert f.m.read(0x9149)==1,('cert',tag,f.read(0x9149,47).hex())
   f.m.write(f.s['se_overlay_frame'],3);r,n=f.fast_call(f.s['se_overlay_call'],a=30,x=0)
   print('R30',tag,r.a,r.p,n,'phase',f.m.read(0x8bcf),flush=True)
   assert not r.p&1 and r.a==0,(tag,'R30',r.a,r.p)
   assert not f.get('se_f_owner',1) and f.canonical()==before and f.merged()==data
   # Root publication seam: production integration will invoke this after A0.
   assert not f.call('se_er_published').p&1
   eb,ea,_,_=semantic.expected(f,data,fonts);actual=f.read(0x6000,8000);attrs=f.read(0x4000,1000)
   (b/(tag+'-actual.bin')).write_bytes(actual+attrs);(b/(tag+'-expected.bin')).write_bytes(eb+ea)
   assert actual==eb,(tag,'pixel',[(i,a,z) for i,(a,z) in enumerate(zip(actual,eb)) if a!=z][:12])
   assert attrs==ea,(tag,'attrs',[(i,a,z) for i,(a,z) in enumerate(zip(attrs,ea)) if a!=z][:12])
   g.m.write(0xcfe8,0);g.render();fc,_=f.raw_cache();gc,_=g.raw_cache()
   assert fc[0]==gc[0]==1 and fc[3]==gc[3]==3
   assert fc[32:46]==gc[32:46],(tag,'header geometry',fc[:64].hex(),gc[:64].hex())
   for row in range(fc[1]):
    off=0x200+row*0x800
    assert fc[off:off+842]==gc[off:off+842],(tag,'ABI3packet',row,[(i,a,z) for i,(a,z) in enumerate(zip(fc[off:off+842],gc[off:off+842])) if a!=z][:12])
   (b/(tag+'-cache.bin')).write_bytes(fc);(b/(tag+'-fullcache.bin')).write_bytes(gc)
   assert fc[0xb480:0xd000]==gc[0xb480:0xd000] and fc[0xd190:0xd500]==gc[0xd190:0xd500],(tag,'caret-free base bitmap/attributes')
   assert f.read(0xc600,1024)==f.shim
   whole=f.reu();handle=f.get('se_gc_handle',1);bank=f.m.read(f.s['se_reu_map']+handle);start=bank*65536
   assert whole[:start]==reu[:start] and whole[start+65536:]==reu[start+65536:]
   fold.geos.png(actual,attrs,b/(tag+'.png'));frames.append(dict(tag=tag,instructions=n,source_bytes=len(data)))
  # Readonly role-band refusal must preserve the existing R28 certificate.
  f.key(fold.geos.native_text('j')[0]);assert f.m.read(0x9149)==1
  before=f.canonical();reu=f.reu();pixels=f.read(0x6000,8000);old=f.m.read(0x4050);f.m.write(0x4050,0x76)
  f.m.write(f.s['se_overlay_frame'],3);r,n=f.fast_call(f.s['se_overlay_call'],a=30,x=0)
  assert r.a==2 and not r.p&1 and f.m.read(0xcf90)==1 and f.m.read(0xcfe8)==1 and f.reu()==reu and f.read(0x6000,8000)==pixels and f.canonical()==before,('miss',r.a,r.p,f.m.read(0xcf90),f.m.read(0xcfe8),f.reu()==reu,f.read(0x6000,8000)==pixels,f.canonical()==before)
  f.m.write(0x4050,old);faults.append('readonly-neighbor-role-refusal preservesGCC/GEC/FE/pixels/source')
  # Foreign file/modal phase is opaque before any owner4 state access.
  f.put('se_f_owner',1,1);phase=f.read(0x8b40,192)+f.read(0x9149,47);reu=f.reu();f.m.write(f.s['se_overlay_frame'],3);r,n=f.fast_call(f.s['se_overlay_call'],a=30,x=0)
  assert r.a==2 and not r.p&1 and f.get('se_f_owner',1)==1 and f.read(0x8b40,192)+f.read(0x9149,47)==phase and f.reu()==reu
  f.put('se_f_owner',0,1);faults.append('foreign-owner1 opaque')
  result=dict(status='passed',faults=faults,C6=len(c6_payload),R30=len(worker_payload),frames=frames,scope='Private actual C6 and R30, explicit resident routing/publication seam, independent full pixel/source oracle; no native/latency claim.')
  (b/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('WORKER PASS',result,flush=True);return result
 except BaseException:
  (b/'failure-c64.bin').write_bytes(f.read(0,65536));(b/'failure-reu.bin').write_bytes(f.reu());raise
 finally:f.close();g.close()

def worker_fault_gate(out,base):
 import importlib.util
 import test_geos_fold_editor as fold
 import test_geos_semantic_editor as semantic
 b=out/'worker-faults';b.mkdir(parents=True,exist_ok=True)
 def builder(name):
  spec=importlib.util.spec_from_file_location('typing_fault_'+name,ROOT/'src/render/geos/typing-candidate'/('build-'+name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 _,_,font=builder('font').build(b/'font',base);_,c6=builder('c6').build(b/'c6',base);_,_,worker=builder('worker').build(b/'worker',base)
 fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=base;names=json.loads((base/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names
 dll=fold.geos.grid.runner(b);f=fold.Fixture(b,base,dll,True);results=[]
 fonts={n:(base/'fonts'/n).read_bytes() for n in fold.geos.GEOS_FONTS+('native8.bin',)}
 def install(image):
  slot,ident=image[5:7]
  for i in range(f.s['se_overlay_capacity']):
   if f.m.read(f.s['se_overlay_ids']+i)==ident and f.m.read(f.s['image_slot']+i)==slot:f.m.write(f.s['se_overlay_ids']+i,0)
  f.m.write(f.s['se_overlay_active']+slot,0);f.m.load(f.s['se_overlay_header'],image[:36]);f.m.load(0x5000,image[36:]);assert not f.call('se_overlay_import').p&1
 def prepare(data,at=7,byte=None):
  f.source(data);f.command(99);f.position(at);f.render();install(font);f.put('se_f_owner',4,1);f.m.write(f.s['se_overlay_frame'],0);r,n=f.fast_call(f.s['se_overlay_call'],a=30,x=1)
  for _ in range(140):
   if not r.a or r.p&1:break
   f.m.write(f.s['se_overlay_frame'],1);r,n=f.fast_call(f.s['se_overlay_call'],a=30,x=1)
  assert r.a==0 and not r.p&1
  f.put('se_f_owner',0,1);install(c6);install(worker);f.key(byte if byte is not None else fold.geos.native_text('X')[0])
 def write_fe(offset,raw):
  f.m.load(0x8080,raw);f.put('se_reu_logical',f.get('se_gc_handle',1),1);f.put('se_reu_offset',offset,2);f.put('se_reu_c64',0x8080,2);f.put('se_reu_length',len(raw),2);assert not f.call('se_reu_copy',0).p&1
 def invoke(tag,error=False,fallback=False):
  before=f.canonical();reu=f.reu();pixels=f.read(0x6000,8000);attrs=f.read(0x4000,1000);gcc=f.m.read(0xcf90);gec=f.m.read(0xcfe8)
  f.m.write(f.s['se_overlay_frame'],3);r,n=f.fast_call(f.s['se_overlay_call'],a=30,x=0)
  assert bool(r.p&1)==error and (r.a!=0 if error else r.a==2),(tag,r.a,r.p)
  assert f.canonical()==before and not f.get('se_f_owner',1) and f.reu()==reu and f.read(0x6000,8000)==pixels and f.read(0x4000,1000)==attrs,(tag,'refusal mutated source/REU/pixels/attrs/owner')
  if not error:assert f.m.read(0xcf90)==gcc and f.m.read(0xcfe8)==gec,(tag,'readonly fallback lost GCC/GEC')
  if fallback:
   data=f.merged();f.render();eb,ea,_,_=semantic.expected(f,data,fonts);assert f.read(0x6000,8000)==eb and f.read(0x4000,1000)==ea,(tag,'actualR28/fullfallback pixels')
  results.append(dict(tag=tag,result=r.a,carry=r.p&1,instructions=n));print('FAULT',results[-1],flush=True)
 try:
  plain=fold.geos.native_text('Plain row with enough room\rSecond row\rTail.')
  # First-character edits cannot reuse a prior whole-line lexical class.
  prepare(plain,0);invoke('index-zero',fallback=True)
  # Exact320 is a C20 FULL boundary, not the old CR/EOF row shape.
  for width in [312,318]:
   text='A'+'W'*((width-6)//8)+'.'*(((width-6)%8)//2)
   prepare(fold.geos.native_text(text+'\rFollowing row.'),7,fold.geos.native_text('W')[0]);assert f.m.read(0x9149)==1
   invoke('new-width-'+str(width+8),fallback=True)
  prepare(plain);cache,_=f.raw_cache();code=fold.geos.native(fold.geos.native_text('X')[0]);off=0xe568+code*9;write_fe(off,bytes([cache[off]^1]));invoke('font-payload-corrupt',fallback=True)
  prepare(plain);at=f.s['se_doc_original'];old=f.m.read(at+1);f.m.write(at+1,old^1);invoke('source-token-generation',error=True);f.m.write(at+1,old)
  prepare(plain);handle=f.get('se_gc_handle',1);at=f.s['se_reu_map']+handle;old=f.m.read(at);f.m.write(at,0);invoke('FE-physical-map');f.m.write(at,old)
  result=dict(status='passed',cases=results,scope='Private actual C6/R30 readonly endpoints/provider/font faults, actual old-root R28/full fallback where marked. No native/root-routing acceptance.')
  (b/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:
  (b/'failure-c64.bin').write_bytes(f.read(0,65536));(b/'failure-reu.bin').write_bytes(f.reu());raise
 finally:f.close()

def worker_main():
 p=argparse.ArgumentParser(description='Private complete C6/R30 gate, with explicit root routing seam')
 p.add_argument('--worker',action='store_true');p.add_argument('--faults',action='store_true');p.add_argument('--base',type=Path,default=ROOT/'build/geos-incremental-editor/20261025T085903355763Z/fixture');p.add_argument('--out',type=Path)
 a=p.parse_args();out=a.out or ROOT/'build/geos-typing-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True,exist_ok=True);base=out/'fixture';shutil.copytree(a.base,base)
 result=worker_gate(out,base)
 if a.faults:result['fault_gate']=worker_fault_gate(out,base)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print('RUN',out,flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--smoke',action='store_true');p.add_argument('--font',action='store_true');p.add_argument('--certificate',action='store_true');p.add_argument('--base',type=Path,default=ROOT/'build/geos-incremental-editor/20261025T081538083121Z/fixture');a=p.parse_args();stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'build/geos-typing-candidate'/stamp;out.mkdir(parents=True);base=out/'fixture';shutil.copytree(a.base,base);names=json.loads((base/'freeze.json').read_text())['names'];leaf.resident.cpu_editor.ROOT=leaf.resident.editor_fixture.ROOT=base;leaf.resident.cpu_editor.NAMES=leaf.resident.editor_fixture.NAMES=names;ls,payload,image=build(out,base);f=Fixture(out,ls,payload,image);rng=random.Random(0x651030);cases=0;faults=0;profiles=[]
 try:
  reu=f.reu();source=makebase(rng,200);f.check(source,0,63,5,200,glyph=bytes([0xf8,0x88,0xf8,0x88,0x88,0,0,0,0]));cases+=1
  (out/'first-gate.json').write_text(json.dumps(dict(status='passed',payload_bytes=len(payload),instructions=f.last_used,bitmap_sha256=hashlib.sha256(f.read(0x6000,8000)).hexdigest()))+'\n');print('FIRST primitive PASS',len(payload),'bytes',f.last_used,'instructions',flush=True)
  for op in [0,1]:
   for advance in range(1,9):
    width=320-advance if op==0 else 320;positions=[0,1,7,8,15,63,127,255,320-advance] if a.smoke else range(321-advance)
    for x in positions:
     source=makebase(rng,width);glyph=bytes(rng.randrange(256)&(255<<(8-advance)) for _ in range(9));used=f.check(source,op,x,advance,width,top=16+(x%168),glyph=glyph,caret=1+(x%8));cases+=1
     if x==63:profiles.append(dict(op=op,advance=advance,instructions=used))
  # Empty/short actualrow, bothbandalignments, tailcaret clipped at320.
  for width in [0,1,7,8,19,127,255,312]:
   for x in [0,width]:
    for advance in [1,8]:
     if width+advance<=320:f.check(makebase(rng,width),0,x,advance,width,top=183,glyph=bytes([255<<(8-advance)&255])*9,caret=8);cases+=1
  # The real compiled BSW face, notonly synthetic width-bounded bitplanes.
  widths=(ROOT/'assets/fonts/generated/bsw9-widths.bin').read_bytes();font=(ROOT/'assets/fonts/generated/bsw9.bin').read_bytes();packed_font=(ROOT/'assets/fonts/generated/bsw9-original.bin').read_bytes()
  row_asset=next((base/'build/overlays'/(n+'.seo')).read_bytes() for n in names if (base/'build/overlays'/(n+'.seo')).read_bytes()[5:7]==bytes([0,21]));assert row_asset[36+0xbf3:36+0xbf3+744]==packed_font
  for code,advance in enumerate(widths):
   glyph=bytes(font[code*18+row*2] for row in range(9));assert all(not(font[code*18+row*2+1]) for row in range(9))
   f.check(makebase(rng,240),0,(code*17)%241,advance,240,top=16+(code%168),glyph=glyph,caret=5);cases+=1
  for leases in [1,7]:
   for _ in range(leases):assert not f.call('se_doc_read_acquire').p&1
   f.check(makebase(rng,240),0,63,5,240,glyph=bytes([0xf8])*9);cases+=1;assert f.get('se_doc_read_locks',1)==leases
   for _ in range(leases):assert not f.call('se_doc_read_release').p&1
  source=makebase(rng,160)
  for field,value in [(0,2),(1,1),(1,2),(1,4),(1,8),(1,16),(2,15),(2,184),(3,0),(3,9),(8,0),(8,9),(5,2),(7,2)]:
   f.check(source,0,5,5,160,mutate=lambda f,field=field,value=value:f.m.write(F+field,value),error=0x90);faults+=1
  for op,x,advance,width in [(0,10,8,313),(0,161,5,160),(1,158,5,160),(1,0,8,7)]:f.check(source,op,x,advance,width,error=0x90);faults+=1
  f.check(source,0,5,5,160,glyph=b'\1'*9,error=0x90);faults+=1
  for off in [0,39,40,79]:
   f.check(source,0,5,5,160,mutate=lambda f,off=off:f.m.write(0x4050+off,0x76),error=0x90);faults+=1
  for owner in [0,1,2,3,5,255]:
   f.check(source,0,5,5,160,owner=owner,error=0xb2);faults+=1
  f.check(source,0,5,5,160,operation=255,error=0x90);faults+=1
  assert f.reu()==reu
  result=dict(status='passed',resident_sha256=json.loads((base/'build/editor-report.json').read_text())['sha256'],payload_bytes=len(payload),cases=cases,faults=faults,profiles=profiles,wholeRAM=65536,wholeREU=16777216,shim=1024,new_BSS=0,new_ZP=0,scope='Private actualsealedR30 CPU plain9px bitmapshift primitive. Explicittrustedcaret-freebase/glyph inputseam; no GEC/FEauthority, integratedediting, cycle/nativeorlatencyclaim.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 except BaseException as e:(out/'failure.json').write_text(json.dumps(dict(error=repr(e),cases=cases,faults=faults))+'\n');(out/'failure-c64.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
 if a.font:
  result['font']=font_gate(out,base);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 if a.certificate:
  result['certificate']=certificate_gate(out,base);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 evidence=ROOT/'agentsworking/evidence/M8'/(stamp+'-geos-typing-candidate');evidence.mkdir(parents=True);shutil.copytree(out,evidence/'build')
 with zipfile.ZipFile(evidence/'verification-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for n in [*Path('src/render/geos/typing-candidate').glob('*'),Path('tests/test_geos_typing_candidate.py'),Path('tests/test_geos_row_leaf.py'),*[Path('assets/fonts/generated')/n for n in ['bsw9-widths.bin','bsw9.bin','bsw9-original.bin']]]:z.write(n,n)
 print('EVIDENCE',evidence)
if __name__=='__main__':
 if '--worker' in sys.argv:worker_main()
 else:main()
