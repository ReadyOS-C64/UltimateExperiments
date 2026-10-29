"""Private actual-C27 body-image cache candidate. No product/shared build writes."""
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import replace
import argparse, ctypes as C, hashlib, json, shutil, subprocess, sys, zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_editor as geos
import test_grid_editor_vice as native
from geos_preview_model import render,FontCatalog,with_chrome
from overlays import wrap
from geos_fold_model import preview as folded_preview
from test_geos_fold_editor import tree,TINY
PREVIOUS=ROOT/'build/geos-preview-editor/20261025T092601658437Z/fixture'
PRIVATE=ROOT/'src/render/geos/preview-cache-candidate'

def command(*args):
 p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True)
 assert p.returncode==0,(args,p.stdout,p.stderr)

def build(out,previous):
 frozen,identity=geos.freeze(out,previous)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=list(identity['names'])
 inc=out/'includes';inc.mkdir()
 with zipfile.ZipFile(frozen/'product-sources.zip') as z:
  for n in z.namelist():
   if n.startswith('src/') and n.endswith('.inc'):
    p=inc/n[4:];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
  source=z.read('src/render/geos/preview.s').decode();cfg=z.read('cfg/geos-editor-page.cfg')
 for n in ('cache.inc','cache.s'):
  p=inc/'render/geos/preview-cache-candidate'/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PRIVATE/n,p)
 candidate=source.replace(' lda PP_PHASE\n cmp #6',' lda PP_PHASE\n cmp #8\n bcc :+\n jsr pc_step\n jcs failed\n cmp #1\n jeq pending\n cmp #2\n jeq complete\n jmp preview_uncached\n:\n lda PP_PHASE\n cmp #6',1)
 needle=' COPY24 se_v_top,PP_POSITION\n ; All176'
 assert needle in candidate
 candidate=candidate.replace(needle,' COPY24 se_v_top,PP_POSITION\n jsr pc_begin\n jcs failed\n cmp #1\n jeq pending\npreview_uncached:\n ; All176',1)
 candidate=candidate.replace(' COPY24 GFQ_RESULT,se_v_top\n',' COPY24 GFQ_RESULT,se_v_top\n lda PPC_ARMED\n beq :+\n COPY24 se_v_top,PPC_META+PPC_TOP\n:\n',1)
 needle=' COPY24 PP_POSITION,se_v_bottom\n lda #1'
 assert needle in candidate
 candidate=candidate.replace(needle,' COPY24 PP_POSITION,se_v_bottom\n jsr pc_capture_begin\n jcs failed\n cmp #1\n jeq pending\n lda #1',1)
 candidate=candidate.replace(' beq classify\n',' jeq classify\n')
 candidate+='\n.include "render/geos/preview-cache-candidate/cache.s"\n'
 # Shared constants precede integration references; guarded helper include is safe.
 candidate=candidate.replace('.include "render/geos/preview.inc"','.include "render/geos/preview.inc"\n.include "render/geos/preview-cache-candidate/cache.inc"',1)
 report=json.loads((frozen/'build/editor-report.json').read_text());s=report['symbols'];images={};sizes={}
 for label,text in [('control',source),('candidate',candidate)]:
  d=out/label;d.mkdir();(d/'preview.s').write_text(text);(d/'leaf.cfg').write_bytes(cfg)
  command(sys.executable,ROOT/'tools/overlay_api.py','--all-public','--symbols','text_ptr','screen_ptr','--report',frozen/'build/editor-report.json','--output',d/'editor-api.inc')
  command('ca65','-g','-I',d,'-I',inc,'-o',d/'preview.o',d/'preview.s')
  command(sys.executable,ROOT/'tools/module_bindings.py','--report',frozen/'build/editor-report.json','--output',d/'bindings.s',d/'preview.o')
  command('ca65','-g','-o',d/'bindings.o',d/'bindings.s')
  command('ld65','-C',d/'leaf.cfg','-o',d/'preview.bin','-m',d/'preview.map','-Ln',d/'preview.lbl',d/'preview.o',d/'bindings.o')
  raw=(d/'preview.bin').read_bytes();sizes[label]=len(raw)
  if label=='control':assert raw==(frozen/'build/overlays/geospreview.seo').read_bytes()[36:]
  images[label]=wrap(raw,1,27,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(report['resident_binding']['digest']))
  print('LINK',label,len(raw),flush=True)
 return frozen,identity,s,images,sizes

def profiled_runner(out,s):
 base=geos.grid.runner(out);cpp=out/'runner.cpp';text=cpp.read_text()
 text=text.replace('static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);int offset=-1;',
  'static uint16_t overlay=0;static uint64_t calls[256]={};\nextern "C" void pc_config(uint16_t a){overlay=a;}\nextern "C" void pc_zero(){for(auto &v:calls)v=0;}\nextern "C" uint64_t pc_calls(int i){return calls[i];}\nstatic void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);if(r.pc==overlay)calls[r.a]++;int offset=-1;')
 cpp.write_text(text);path=out/'profiled.dylib'
 command('clang++','-std=c++20','-O2','-dynamiclib','-fPIC','-I'+str(geos.grid.VENDOR),cpp,ROOT/'build/libse_peddle.dylib','-o',path)
 dll=C.CDLL(str(path))
 for name in ('gm_rom','gm_rom_count','gm_profile','gm_metric','gm_run','gm_idle','gm_read','gm_reu'):
  getattr(dll,name).argtypes=getattr(base,name).argtypes;getattr(dll,name).restype=getattr(base,name).restype
 dll.pc_config.argtypes=[C.c_uint16];dll.pc_calls.argtypes=[C.c_int];dll.pc_calls.restype=C.c_uint64;dll.pc_config(s['se_overlay_call'])
 return dll

class Fixture(geos.Fixture):
 def source(self,*args,**kwargs):
  self.folds=None;return super().source(*args,**kwargs)
 def reu(self):
  b=C.create_string_buffer(16*1024*1024);self.dll.gm_reu(self.m.handle,len(b),b);return b.raw
 def patch_cache(self,offset,value):
  self.m.write(0x8000,value);self.put('se_reu_logical',self.get('se_gc_handle',1),1);self.put('se_reu_offset',offset,2);self.put('se_reu_length',1,2);self.put('se_reu_c64',0x8000,2)
  r=self.call('se_reu_copy');assert not r.p&1,('patch',r.a)
 def page(self):
  self.put('se_e_redraw',1,1);return self.render()

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--previous',type=Path,default=PREVIOUS);a=p.parse_args()
 out=ROOT/'build/geos-preview-cache-candidate'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
 frozen,identity,s,images,sizes=build(out,a.previous)
 verification=[Path(__file__),*PRIVATE.glob('*'),ROOT/'tests/test_geos_editor.py',ROOT/'tests/test_grid_modes.py',ROOT/'tools/geos_preview_model.py',ROOT/'tools/geos_fold_model.py',ROOT/'tests/test_geos_fold_editor.py',ROOT/'tools/supermark_model.py',ROOT/'tools/editor_fixture.py',ROOT/'tools/cpu_editor.py',ROOT/'tools/font_fixture.py']
 with zipfile.ZipFile(out/'verification-sources.zip','w',zipfile.ZIP_DEFLATED)as z:
  for p in verification:
   if p.is_file():z.write(p,p.relative_to(ROOT))
 (out/'identity.json').write_text(json.dumps(dict(identity=identity,sizes=sizes),indent=2)+'\n')
 print('BUILT',out,flush=True)
 if not a.run:return
 shutil.copytree(ROOT/'build/geos-font-catalog',frozen/'genuine',dirs_exist_ok=True)
 fonts=FontCatalog(frozen/'genuine/catalog.json',native=(frozen/'fonts/native8.bin').read_bytes())
 dll=profiled_runner(out,s);results=[]
 def check(f,data,tag,*,hit=False,reference=None):
  canonical=f.canonical();catalog=f.catalog();reu=f.reu();dll.pc_zero();start=f.total_instructions;loads=f.get('se_overlay_loads',2)
  f.page()
  expected=(folded_preview(data,f.read(s['se_editor_settings'],64),f.folds,catalog=fonts,top=f.get('se_v_top'))if f.folds is not None else render(data,f.read(s['se_editor_settings'],64),catalog=fonts,top=f.get('se_v_top')))
  m,c,rect=geos.grid.logical_ui(f,data);eb,ea=with_chrome(expected.bitmap,expected.attrs,m,c,fonts.native)
  assert f.read(0x6000,8000)==eb and f.read(0x4000,1000)==ea,(tag,'pixels')
  assert f.read(0xcc07,3)==expected.bottom.to_bytes(3,'little'),(tag,'bottom')
  assert [int.from_bytes(f.read(s['se_v_rows']+3*i,3),'little')for i in range(len(expected.anchors))]==list(expected.anchors),(tag,'canonicalanchors')
  assert f.canonical()==canonical and f.catalog()==catalog and f.merged()==data and f.read(0xc600,1024)==f.shim and f.get('se_f_owner',1)==0 and f.get('se_doc_read_locks',1)==0,(tag,'canonical/lease')
  after=f.reu();bank,physical=f.raw_cache();base=physical*65536
  if hit:
   assert after==reu,(tag,'readonlyhitREU')
   assert not any(dll.pc_calls(i)for i in (23,24,25,26)),(tag,'semantic/fontcalls',{i:dll.pc_calls(i)for i in (23,24,25,26)})
   if reference:assert f.read(s['se_v_rows'],66)==reference,(tag,'all66anchors')
  else:
   assert after[:base+0xB200]==reu[:base+0xB200] and after[base+0xD0F0:base+0xEA88]==reu[base+0xD0F0:base+0xEA88] and after[base+0xEA88+225:]==reu[base+0xEA88+225:],(tag,'outofcacheREU')
  result=dict(case=tag,hit=hit,instructions=f.total_instructions-start,loads=(f.get('se_overlay_loads',2)-loads)&65535,calls={str(i):dll.pc_calls(i)for i in (14,16,23,24,25,26,27)},rows=len(expected.anchors),source_bytes=len(data),bitmap_sha256=hashlib.sha256(eb).hexdigest())
  results.append(result);print('PASS',result,flush=True)
  return f.read(s['se_v_rows'],66)
 control=Fixture(out,frozen,dll,True)
 try:
  control.assets['geospreview']=images['control'];sample=native.fixture();control.source(sample,physical=256);control.command(99);control.render();control.command(102)
  check(control,sample,'control-diverse422-full')
 finally:control.close()
 f=Fixture(out,frozen,dll,True)
 try:
  f.assets['geospreview']=images['candidate']
  for label,data in [('diverse422',native.fixture()),('prefixes',geos.native_text('# Heading\rProse **bold** /italic/ @@code@@.\r- list\r12. number\r')),('empty',b''),('long',geos.native_text('# Head\r'+('ABcd plain '*45)+'\rLast\r'))]:
   f.source(data,physical=256);f.command(99);f.render();f.command(102)
   anchors=check(f,data,label+'-capture')
   for tag in ('hit1','hit2'):check(f,data,label+'-'+tag,hit=True,reference=anchors)
   if label=='diverse422':
    # All64 bytes, including the header and inactive H profiles, must miss.
    # Invalid bytes are stopped before any semantic worker consumes them.
    original=f.read(s['se_editor_settings'],64)
    witness_reu=f.reu();witness_source=f.canonical()
    for index in range(64):
     f.m.write(s['se_editor_settings']+index,original[index]^1)
     f.put('se_e_redraw',1,1);r=f.call('se_editor_render');assert not r.p&1
     for _ in range(10):
      if f.m.read(0xcc00)==1 and f.m.read(0x9135)==24:break
      f.call('se_editor_service')
     else:raise AssertionError(('settingsbyte-not-missed',index,f.m.read(0xcc00)))
     f.queued(3);f.call('se_editor_service')
     assert f.get('se_e_job',1)==0 and f.get('se_f_owner',1)==0 and f.get('se_doc_read_locks',1)==0
     f.m.load(s['se_editor_settings'],original)
     assert f.reu()==witness_reu and f.canonical()==witness_source,(index,'settingscancelchangedsource/cache')
    results.append(dict(case='all64-settings-key-bytes',misses=64,stopped_before_semantic_consumer=True))
    check(f,data,'after-settings-key-probes',hit=True)
    settings=bytearray(original);settings[12]=3 # BODYFG cyan, valid session profile.
    f.m.load(s['se_editor_settings'],settings);check(f,data,'body-color-change');check(f,data,'body-color-hit',hit=True)
    f.m.load(s['se_editor_settings'],original);check(f,data,'body-color-restore')
    for tag,key in [('page2',0x87),('page1',0x86)]:
     f.key(key);check(f,data,tag);check(f,data,tag+'-hit',hit=True)
    # Checked provider writes model an overwritten image and malformed header.
    for offset in (0xB200,0xCD7F,0xCD80,0xD0EF,0xEA88,0xEA88+223):
     bank,_=f.raw_cache();f.patch_cache(offset,bank[offset]^1)
     check(f,data,'corrupt-'+hex(offset));check(f,data,'repaired-'+hex(offset),hit=True)
    # Literal source capture uses a different full8000/1000 packed layout.
    f.command(67);f.render();assert f.merged()==data
    f.command(102);check(f,data,'literal-return');check(f,data,'literal-return-hit',hit=True)
  # Canonical source mutation forces a real producer then a new readonly hit.
  data=geos.native_text('Plain body\rSecond line\r');f.source(data,physical=256);f.command(99);f.render();f.command(102);check(f,data,'before-edit')
  f.command(67);f.key(ord('Q'));f.render();data=b'Q'+data;f.command(102);check(f,data,'pending-source-change');check(f,data,'pending-source-hit',hit=True)
  f.command(67);f.command(16);f.render();data=data[1:];f.command(102);check(f,data,'undo-source-change');check(f,data,'undo-source-hit',hit=True)
  # Real fold publication/generation changes; no synthetic map records.
  f.source(TINY,physical=256);f.command(99);f.command(115);f.folds=[replace(q,flags=1)for q in tree(TINY)];f.command(102)
  check(f,TINY,'folded-capture');check(f,TINY,'folded-hit',hit=True)
  f.command(67);f.command(116);f.folds=[];f.command(102)
  check(f,TINY,'unfolded-capture');check(f,TINY,'unfolded-hit',hit=True)
  # 24-bit source/page key: logical row2 starts above65535.
  data=b'A'*65540+geos.native_text('\r# Far heading\rFar **styled** line\rLast.\r')
  f.source(data,banks=2,physical=256);f.command(99);f.typed(geos.native_text('goto 2'));f.render();f.command(102)
  assert f.get('se_v_top')>65535
  check(f,data,'far64k-capture');check(f,data,'far64k-hit',hit=True)
 finally:f.close()
 # Fresh real fixtures keep fault/lease identities independent.
 faults=[]
 for fault in ('STOP-hit','STOP-capture','missingR14','FEowner','FEmap','provider-retired','source-revision','settings-midstep','foreign-readlease','foreign-phase','fold-owner','fold-count','fold-generation','font-owner','font-ready'):
  f=Fixture(out,frozen,dll,True)
  try:
   f.assets['geospreview']=images['candidate'];data=geos.native_text('Plain body\rSecond line\r')
   f.source(data,physical=256);f.command(99);f.render()
   if fault.startswith('fold-'):
    data=TINY;f.source(data,physical=256);f.command(99);f.command(115);f.folds=[replace(q,flags=1)for q in tree(TINY)]
   f.command(102);check(f,data,fault+'-seed')
   if fault=='foreign-phase':
    f.put('se_f_owner',1,1);phase=f.read(0x8d00,1152);scratch=f.read(0xcc00,256);reu=f.reu()
    f.put('se_overlay_frame',1,1);f.fast_call(s['se_overlay_call'],27,1)
    assert f.get('se_f_owner',1)==1 and f.read(0x8d00,1152)==phase and f.read(0xcc00,256)==scratch and f.reu()==reu
    faults.append(dict(fault=fault,opaque1152=True));continue
   if fault=='foreign-readlease':
    f.put('se_doc_read_locks',1,1);f.put('se_e_redraw',1,1);f.call('se_editor_render')
    for _ in range(25000):
     if not f.get('se_e_job',1):break
     f.call('se_editor_service')
    else:raise AssertionError('foreignlease-nonconvergence')
    assert f.get('se_doc_read_locks',1)==1 and f.get('se_fs_owned',1)==0
    f.put('se_doc_read_locks',0,1);check(f,data,'foreign-lease-after',hit=True)
    faults.append(dict(fault=fault,preserved_foreign_lock=True));continue
   if fault=='STOP-capture':
    f.patch_cache(0xea88,0) #force fullproducer, then stop afterVALID0 capture
   f.put('se_e_redraw',1,1);f.call('se_editor_render')
   for _ in range(25000):
    if f.get('se_f_owner',1)==4 and f.m.read(0xcc00)==10 and bool(f.m.read(0xcc44))==(fault=='STOP-capture'):break
    f.call('se_editor_service')
   else:raise AssertionError(('faultphase',fault,f.debug()))
   handle=f.get('se_gc_handle',1);physical=f.m.read(s['se_reu_map']+handle)
   if fault=='missingR14':
    ix=next(i for i in range(s['se_overlay_capacity'])if f.m.read(s['se_overlay_ids']+i)==14 and f.m.read(s['image_slot']+i)==0)
    f.m.write(s['se_overlay_ids']+ix,0);f.m.write(s['se_overlay_active'],0)
   elif fault=='FEowner':f.m.write(s['se_reu_logical_owner']+handle,0xFD)
   elif fault=='FEmap':f.m.write(s['se_reu_map']+handle,1)
   elif fault=='provider-retired':f.put('se_reu_retired',1,1)
   elif fault=='source-revision':f.put('se_r_revision',f.get('se_r_revision',4)+1,4)
   elif fault=='settings-midstep':f.m.write(s['se_editor_settings']+12,3)
   elif fault=='fold-generation':f.put('se_ef_generation',f.get('se_ef_generation',2)+1,2)
   elif fault=='fold-count':f.put('se_ef_count',65535,2)
   elif fault=='fold-owner':
    oid=f.m.read(s['se_ef_token']);f.m.write(s['object_owner']+oid,0x45)
   elif fault=='font-ready':f.m.write(0xcbc0,0)
   elif fault=='font-owner':f.m.write(s['se_reu_logical_owner']+f.m.read(0xcbc1),0xFC)
   body=f.read(0x6280,7040);attrs=f.read(0x4050,880);canonical=f.canonical();reu=f.reu();catalog=f.catalog()
   if fault.startswith('STOP'):f.queued(3)
   f.call('se_editor_service')
   assert f.get('se_e_job',1)==0 and f.get('se_f_owner',1)==0 and f.get('se_doc_read_locks',1)==0 and f.get('se_fs_owned',1)==0,(fault,'cleanup',f.debug())
   assert f.read(0x6280,7040)==body and f.read(0x4050,880)==attrs and f.canonical()==canonical and f.reu()==reu and f.catalog()==catalog and f.read(0xc600,1024)==f.shim,(fault,'failed hit changedbody/source/REU')
   if fault=='STOP-capture':assert reu[physical*65536+0xea88+5]==0,'capturepublishedbeforepayload'
   faults.append(dict(fault=fault,error=f.get('se_e_error',1),body_unchanged=True,source_unchanged=True,whole_reu_unchanged=True,lease=0));print('FAULTPASS',faults[-1],flush=True)
  finally:f.close()
 (out/'result.json').write_text(json.dumps(dict(status='passed cache gate',identity=identity,sizes=sizes,results=results,faults=faults,limits='Private validSEO C27 replacement only; actual CPU instructions not native cycles. No shared product/build/loader CRC changes.'),indent=2)+'\n')
 print('DONE',out,flush=True)
if __name__=='__main__':main()
