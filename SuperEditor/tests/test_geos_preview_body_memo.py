"""Private managed preview body memo: actual full resident, guards and pixels.

No product/shared build writes. Unnotified raw REU mutation is outside the
managed callback contract; checked writes and fresh resume always revoke.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,inspect,json,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_preview_cache_candidate as old
from overlays import wrap
PRIVATE=ROOT/'src/render/geos/preview-body-memo-candidate'
DEFAULT=ROOT/'build/geos-preview-body-memo/20261025T124523372904Z'
MEMO=0xCC4D

def cmd(*args):
 p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True)
 assert p.returncode==0,(args,p.stdout,p.stderr)
 return p.stdout

def control_image(out,fixture,product):
 inc=out/'strict-includes';inc.mkdir()
 with zipfile.ZipFile(Path(json.loads((product.parent/'fit.json').read_text())['base'])/'product-sources.zip')as z:
  for name in z.namelist():
   if name.startswith('src/')and name.endswith(('.s','.inc')):
    p=inc/name[4:];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
 d=out/'strict';d.mkdir();report=fixture/'build/editor-report.json';s=json.loads(report.read_text())
 cmd(sys.executable,ROOT/'tools/overlay_api.py','--all-public','--symbols','text_ptr','screen_ptr','--report',report,'--output',d/'editor-api.inc')
 cmd('ca65','-g','-I',d,'-I',inc,'-o',d/'preview.o',inc/'render/geos/preview.s')
 cmd(sys.executable,ROOT/'tools/module_bindings.py','--report',report,'--output',d/'binding.s',d/'preview.o');cmd('ca65','-g','-o',d/'binding.o',d/'binding.s')
 cmd('ld65','-C',product/'cfg/geos-editor-page.cfg','-o',d/'preview.bin','-m',d/'preview.map','-Ln',d/'preview.lbl',d/'preview.o',d/'binding.o')
 raw=(d/'preview.bin').read_bytes();assert len(raw)==4095
 return wrap(raw,1,27,api=(s['symbols']['se_overlay_call'],s['symbols']['se_overlay_frame']),binding_digest=bytes.fromhex(s['resident_binding']['digest']))

def cache_gate(out,base):
 source=inspect.getsource(old)
 source=source.replace("ROOT/'build/geos-preview-cache-candidate'",'CACHE_OUTPUT')
 source=source.replace("f.m.read(s['image_slot']+i)==0","(f.m.read(s['image_slot']+i)&1)==0")
 source=source.replace("if __name__=='__main__':main()",'')
 ns={'__name__':'private_cache_gate','__file__':str(ROOT/'tests/test_geos_preview_cache_candidate.py'),'CACHE_OUTPUT':out};exec(compile(source,str(out/'executed-cache-gate.py'),'exec'),ns);(out/'executed-cache-gate.py').write_text(source)
 def build(path,previous):
  frozen,identity=old.geos.freeze(path,previous);s=json.loads((frozen/'build/editor-report.json').read_text())['symbols'];candidate=(frozen/'build/overlays/geospreview.seo').read_bytes();control=control_image(path,frozen,base/'product')
  old.geos.grid.editor_fixture.ROOT=old.geos.grid.cpu_editor.ROOT=frozen;old.geos.grid.editor_fixture.NAMES=old.geos.grid.cpu_editor.NAMES=identity['names']
  return frozen,identity,s,dict(control=control,candidate=candidate),dict(control=len(control)-36,candidate=len(candidate)-36)
 ns['build']=build;argv=sys.argv;sys.argv=['private-cache','--run','--previous',str(base/'fixture')]
 try:ns['main']()
 finally:sys.argv=argv
 return next(out.glob('*/result.json'))


def spy_runner(out,s):
 base=old.profiled_runner(out,s);p=out/'runner.cpp';text=p.read_text();text=text.replace('static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);',
  'static uint64_t writes=0,bad=0;extern "C" uint64_t memo_writes(){return writes;}extern "C" uint64_t memo_bad(){return bad;}extern "C" void memo_zero(){writes=bad=0;}\nstatic void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);if(zeropage_peddle_read(m,r.pc)==0x8D&&zeropage_peddle_read(m,uint16_t(r.pc+1))==1&&zeropage_peddle_read(m,uint16_t(r.pc+2))==0xDF&&!(r.a&1)){writes++;if(zeropage_peddle_read(m,0xCC4D)!=0)bad++;}')
 p.write_text(text);path=out/'spy.dylib';cmd('clang++','-std=c++20','-O2','-dynamiclib','-fPIC','-I'+str(old.geos.grid.VENDOR),p,ROOT/'build/libse_peddle.dylib','-o',path);dll=C.CDLL(str(path))
 for name in ('gm_rom','gm_rom_count','gm_profile','gm_metric','gm_run','gm_idle','gm_read','gm_reu','pc_config','pc_calls','pc_zero'):
  getattr(dll,name).argtypes=getattr(base,name).argtypes;getattr(dll,name).restype=getattr(base,name).restype
 for name in ('memo_writes','memo_bad'):getattr(dll,name).restype=C.c_uint64
 dll.pc_config(s['se_overlay_call']);return dll


def callbacks(out,base):
 out.mkdir();frozen,identity=old.geos.freeze(out,base/'fixture');s=json.loads((frozen/'build/editor-report.json').read_text())['symbols'];old.geos.grid.editor_fixture.ROOT=old.geos.grid.cpu_editor.ROOT=frozen;old.geos.grid.editor_fixture.NAMES=old.geos.grid.cpu_editor.NAMES=identity['names'];dll=spy_runner(out,s);f=old.Fixture(out,frozen,dll,True);cases=[]
 try:
  data=old.geos.native_text('# Heading\rPlain body **bold** *italic* @@code@@.\rLast.');f.source(data,physical=256);f.command(99);f.render();f.command(102);f.render();assert f.m.read(MEMO)==1
  # Compare same C27 byte image with sticky witness versus forced fresh CRC.
  for label,memo in [('verified',1),('first-verify',0),('verified-again',1)]:
   f.m.write(MEMO,memo);canonical=f.canonical();reu=f.reu();dll.pc_zero();start=f.total_instructions;f.page();n=f.total_instructions-start
   assert f.canonical()==canonical and f.reu()==reu and f.m.read(MEMO)==1 and f.read(0xc600,1024)==f.shim
   cases.append(dict(case=label,instructions=n,R14=dll.pc_calls(14),whole_REU_readonly=True))
  # Every legal owner2..254 checked CPU->REU write clears before publishing;
  # rejection and all reads preserve a known verified witness.
  checked=[];dll.memo_zero()
  for owner in range(2,255):
   r=f.call('se_reu_alloc',owner);assert not r.p&1;handle=r.a
   f.m.write(MEMO,1);f.m.load(0x8000,b'X');f.put('se_reu_logical',handle,1);f.put('se_reu_c64',0x8000,2);f.put('se_reu_offset',0xB200,2);f.put('se_reu_length',1,2)
   before=f.reu();r=f.call('se_reu_copy',0);assert not r.p&1 and f.m.read(MEMO)==0,(owner,'stash revocation')
   f.m.write(MEMO,1);r=f.call('se_reu_copy',1);assert not r.p&1 and f.m.read(MEMO)==1,(owner,'fetch revocation')
   guard=f.reu();f.put('se_reu_length',0,2);r=f.call('se_reu_copy',0);assert r.p&1 and f.m.read(MEMO)==1 and f.reu()==guard
   # Exact one-byte mutation only in the owned bank.
   after=f.reu();bank=f.m.read(s['se_reu_map']+handle);want=bytearray(before);want[bank*65536+0xB200]=ord('X');assert after==want
   r,_=f.fast_call(s['se_reu_free'],x=handle);assert not r.p&1
   checked.append(owner)
  f.m.write(MEMO,1);before=f.reu();f.call('se_overlay_unverify');assert f.m.read(MEMO)==0 and f.reu()==before
  assert dll.memo_writes()>=253 and dll.memo_bad()==0,('DF01 preflight witness',dll.memo_writes(),dll.memo_bad())
  cases.append(dict(case='all253typedowners',owners=checked,stash_clears=True,fetch_preserves=True,invalid_request_preserves=True,whole_REU_exact=True))
  (out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n')
  # Direct R26 DMA internal seam: full actual validated callback path before
  # each stash. Wrapper establishes its normal capability on real C29BEGIN.
  assert not f.call('se_clip_init').p&1
  f.put('se_e_ui',0,1);f.put('se_r_presentation',0,1);f.put('se_e_redraw',0,1);f.put('se_status',1,1)
  report=json.loads((frozen/'build/editor-report.json').read_text());f.m.load(0x800,bytes.fromhex(report['resident_binding']['digest'])+bytes(64));image=f.assets['lifectrl'];f.m.load(0xa00,image[36+0x800:36+0x900]);r,_=f.fast_call(0xae0,a=0);assert not r.p&1 and r.a==1,('C29BEGIN',r.a,r.p,f.debug())
  direct=[]
  for i in range(4):
   f.m.write(MEMO,1);r,_=f.fast_call(0xae0,a=1);assert not r.p&1 and f.m.read(MEMO)==0,('actual R26 capture write',i,r.a,r.p);direct.append(i)
  r,_=f.fast_call(0xae0,a=2);assert not r.p&1
  # Actual fresh prelude must revoke restored1 before any overlay execution.
  f.m.write(MEMO,1);f.m.load(0xa00,image[36+0x800:36+0x900]);before=f.reu()
  for name,v in [('pc',0xa00),('sp',0xff),('p',0x24)]:getattr(f.m.lib,'zeropage_peddle_set_'+name)(f.m.handle,v)
  for steps in range(5000):
   if f.m.regs().pc==s['se_doc_invalidate']:break
   f.m.lib.zeropage_peddle_step_instruction(f.m.handle)
  else:raise AssertionError('prelude did not reach invalidation')
  assert f.m.read(MEMO)==0 and f.reu()==before and f.read(0xc600,1024)==f.shim
  assert dll.memo_bad()==0,('R26 direct DF01 witness',dll.memo_bad())
  cases.append(dict(case='R26direct-stash-and-C29-fresh-prelude',capture_callbacks=direct,restored_memo_disarmed_before_first_overlay=True))
 finally:f.close()
 result=dict(status='passed',cases=cases,before_DF01_stashes=dll.memo_writes(),before_DF01_bad=dll.memo_bad(),scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result


def generic(out,base):
 import test_overlay_tail as tail
 out.mkdir();original=out/'original';candidate=out/'candidate'
 with zipfile.ZipFile(Path(json.loads((base/'fit.json').read_text())['base'])/'product-sources.zip')as z:
  for name in z.namelist():
   if name.startswith('src/')and name.endswith(('.s','.inc')):
    p=original/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
 shutil.copytree(original,candidate)
 for name,dst in [('cache.s','overlay/cache.s'),('dma.s','reu/dma.s')]:shutil.copy2(PRIVATE/name,candidate/'src'/dst)
 previous_root,previous_out=tail.ROOT,tail.OUT;tail.OUT=out;cases=[]
 try:
  for fast in (False,True):
   images=[];symbols=[]
   for label,source in [('before',original),('after',candidate)]:
    tail.ROOT=source;path,syms=tail.compile_variant(label+str(fast),capacity=15,fast=fast);images.append((path/'probe.bin').read_bytes());symbols.append(syms)
   assert images[0]==images[1]and symbols[0]==symbols[1],('generic byte/symbol difference',fast)
   cases.append(dict(fast=fast,bytes=len(images[0]),sha256=hashlib.sha256(images[0]).hexdigest(),symbol_identity=True))
 finally:tail.ROOT=previous_root;tail.OUT=previous_out
 result=dict(status='passed',cases=cases,scope='Managed flag undefined: actual full cache/provider/DMA/header/CRC linked capsule byte and complete-symbol identity.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)


def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=DEFAULT);p.add_argument('--cache-only',action='store_true');p.add_argument('--generic-only',action='store_true');p.add_argument('--interleaved-only',action='store_true');p.add_argument('--callbacks-only',action='store_true');a=p.parse_args();out=a.base/('callbacks-'+datetime.now(timezone.utc).strftime('%H%M%S')if a.callbacks_only else('interleaved-gate'if a.interleaved_only else'generic-gate'if a.generic_only else'cache-gate'));out.mkdir();print('RUN',out,flush=True)
 if a.interleaved_only:interleaved(out/'interleaved',a.base)
 elif a.generic_only:generic(out/'generic',a.base)
 elif a.callbacks_only:callbacks(out/'callbacks',a.base)
 else:print(cache_gate(out,a.base),flush=True)


def interleaved(out,base,expect_old_failure=False):
 out.mkdir();frozen,identity=old.geos.freeze(out,base/'fixture');s=json.loads((frozen/'build/editor-report.json').read_text())['symbols'];old.geos.grid.editor_fixture.ROOT=old.geos.grid.cpu_editor.ROOT=frozen;old.geos.grid.editor_fixture.NAMES=old.geos.grid.cpu_editor.NAMES=identity['names'];dll=old.profiled_runner(out,s);f=old.Fixture(out,frozen,dll,True)
 try:
  data=old.geos.native_text('# Heading\rPlain body **bold** *italic*.\rLast.');f.source(data,physical=256);f.command(99);f.render();f.command(102);f.render();expected=f.read(0x6000,8000)+f.read(0x4000,1000);canonical=f.canonical();f.m.write(MEMO,0);f.put('se_e_redraw',1,1);f.call('se_editor_render')
  for _ in range(20):
   if f.get('se_f_owner',1)==4 and f.m.read(0xcc00)==10 and f.m.read(0xcc44)==0 and int.from_bytes(f.read(0xcc45,2),'little')==128:break
   f.call('se_editor_service')
  else:raise AssertionError('did not reach verified-first-chunk yield')
  bank,physical=f.raw_cache();print('INTERLEAVE',f.read(0xcc43,11).hex(),bank[0xb200],bank[0xea88+214:0xea88+216].hex(),flush=True);f.patch_cache(0xb200,bank[0xb200]^1);assert f.m.read(MEMO)==0;print('PATCHED',f.raw_cache()[0][0xb200],flush=True)
  f.settle();print('AFTER',f.read(0xcc43,11).hex(),f.raw_cache()[0][0xb200],flush=True);after=f.read(0x6000,8000)+f.read(0x4000,1000)
  if expect_old_failure:assert after!=expected,'expected historical stale sweep reproduction'
  else:assert after==expected and f.m.read(MEMO)==1,'interleaved checked write not rebuilt'
  assert f.canonical()==canonical and f.merged()==data and f.read(0xc600,1024)==f.shim and not f.get('se_doc_read_locks',1)
  old.geos.png(after[:8000],after[8000:],out/'after.png');old.geos.png(expected[:8000],expected[8000:],out/'expected.png')
  result=dict(status='known-failure-reproduced'if expect_old_failure else'passed',memo_after=f.m.read(MEMO),source_preserved=True,lease_released=True,case='checked write to already scanned body byte between CRC slices',matches_reference=after==expected);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
 finally:f.close()

if __name__=='__main__':main()
