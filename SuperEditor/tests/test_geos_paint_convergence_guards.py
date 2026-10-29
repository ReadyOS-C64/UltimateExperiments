"""Private genuine public convergence refusal/late-fault/phase qualification."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,importlib.util,json
import test_cache_observer as observer
import test_cache_hotpath_profile as hot
import test_plain_geos as plain
ROOT=observer.ROOT;BASE=ROOT/'build/cache-rebase-churn/general4-fixture';LINK=ROOT/'build/paint-convergence-probe/base-fit1'

def run(out,base,link):
 out.mkdir(parents=True);(out/'verifier.py').write_bytes(Path(__file__).read_bytes());identity=json.loads((base/'freeze.json').read_text())
 spec=importlib.util.spec_from_file_location('cv_guard_runner',ROOT/'src/render/geos/paint-convergence-probe/runner.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
 old,freeze=observer.runner,observer.geos.freeze;observer.runner=r.build;observer.geos.freeze=lambda *_:(base,identity)
 try:g=observer.Gate(out,base)
 finally:observer.runner=old;observer.geos.freeze=freeze
 f=g.f;f.assets['geospage']=(link/'geospage.seo').read_bytes();f.assets['convergence']=(link/'convergence.seo').read_bytes();native=observer.geos.native_text
 data=native('Ordinary words make a continuing paragraph with enough text to wrap. '*6+'\rTail remains.\r');source=data[:85]+native('Q')+data[85:]
 fonts={n:(base/'fonts'/n).read_bytes()for n in observer.geos.GEOS_FONTS+('native8.bin',)};cases=[]
 def pixels(raw,tag):
  bits,attrs,rows=plain.expected(f,raw,fonts,3);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'independent pixels')
  cache,_=f.raw_cache();assert cache[0]==1 and cache[1]==len(rows)
  for i,row in enumerate(rows):
   p=cache[0x200+i*0x800:0x220+i*0x800]
   assert tuple(int.from_bytes(p[j:j+3],'little')for j in(0,3,6))==(row.start,row.end,row.next)and(p[14],p[15])==(row.height,row.top)
  return cache
 def setup(raw=data):
  f.source(raw);f.typed(native('syntax full'));f.command(99);hot.drain(f);f.position(85);f.render();hot.drain(f);f.typed(native('syntax plain'));hot.drain(f);f.typed(native('syntax full'));hot.drain(f)
  cache=pixels(raw,'setup');assert cache[0xdd68]==0xa5 and cache[0xdd69]==5
  points=[f.s[n]for n in('se_reu_copy','se_reu_c64','se_reu_length','se_reu_logical','se_gc_handle','se_i_ready','se_i_count','se_n_cache_count')]+[0x912c,0x912d,f.s['se_doc_read_locks'],f.s['se_s_active'],f.s['se_s_owned'],f.s['se_f_owner'],f.s['se_bc_flags'],0x8b40+21]
  g.dll.loan_config((C.c_uint16*16)(*points));return cache
 def transfer(offset,value):
  f.m.load(0x8000,bytes((value,)));f.put('se_reu_logical',f.get('se_gc_handle',1),1);f.put('se_reu_offset',offset,2);f.put('se_reu_c64',0x8000,2);f.put('se_reu_length',1,2);assert not f.call('se_reu_copy',0).p&1
 def record(tag,**kw):
  assert f.read(0xc600,1024)==f.shim
  item=dict(tag=tag,loans=int(g.dll.loan_get(0)),loan_bad=int(g.dll.loan_get(1)),**kw);assert not item['loan_bad'],item;cases.append(item);(out/'progress.json').write_text(json.dumps(cases,indent=2)+'\n');print('PASS',item,flush=True)
 try:
  for fault in ('certificate','VICbitmap','VICattrs','base','GCCsequence','GCChandle','GCCepoch','GCCphysical','GCCkey'):
   cache=setup()
   if fault=='certificate':transfer(0xdd68+126,cache[0xdd68+126]^1)
   elif fault=='base':transfer(0xb200+640,cache[0xb200+640]^1)
   elif fault=='VICbitmap':f.m.write(0x6000+640,f.m.read(0x6000+640)^1)
   elif fault=='VICattrs':f.m.write(0x4000+80,f.m.read(0x4000+80)^0x10)
   else:
    at={'GCCsequence':0xcf91,'GCChandle':0xcf93,'GCCepoch':0xcf95,'GCCphysical':0xcf94,'GCCkey':0xcf97}[fault];f.m.write(at,f.m.read(at)^1)
   stable,catalog=g.stable(),f.catalog();oldbody=f.read(0x6000+640,7040);oldattrs=f.read(0x4000+80,880);before=g.audit_begin();f.key(native('Q')[0])
   # Error publication can follow bounded service slices; observe the terminal
   # state before choosing strict-error versus optional-fallback assertions.
   for _ in range(200000):
    if hot.quiet(f):break
    f.tick()
   else:raise AssertionError('fault did not terminate')
   error=f.get('se_e_error',1)
   if error:
    # Real R27 independently rejects corrupted typed base bindings. This is
    # a strict18 beforepixels, not an optional-miss/full-repair claim.
    assert fault in('GCChandle','GCCepoch','GCCphysical')and error==0x18,(fault,error)
    assert f.read(0x6000+640,7040)==oldbody and f.read(0x4000+80,880)==oldattrs
   else:hot.drain(f)
   g.audit_end(before,fault)
   assert f.merged()==source and g.stable()==stable and f.catalog()==catalog
   if not error:pixels(source,fault)
   assert f.m.read(0x914a)!=0xa7,(fault,'bad authority produced convergence')
   record(fault,source_preserved=True,full_fallback=not bool(error),error=error)
   f.command(16);hot.drain(f);assert f.merged()==data;pixels(data,fault+'-undo')
  # Actual public operation held between bounded completion steps. The first
  # four comparisons have completed but no C22 draw/publication has occurred.
  for fault in ('late-packet','late-count','late-epoch','late-busy','late-header','STOP'):
   cache=setup();stable,catalog=g.stable(),f.catalog();before=g.audit_begin();oldbody=f.read(0x6000+640,7040);oldattrs=f.read(0x4000+80,880)
   f.put('se_e_key',native('Q')[0],1);f.put('se_e_mods',0,1);f.call('se_editor_input')
   for step in range(10000):
    if f.get('se_e_job',1)==11 and f.m.read(0x9134)==15 and f.read(0x9149,2)==bytes((0xa6,0xa7)) and 4<=f.m.read(0x914b)<22:break
    assert not f.get('se_e_error',1),f.debug();f.tick()
   else:raise AssertionError('no bounded completion suspension')
   assert f.read(0x6000+640,7040)==oldbody and f.read(0x4000+80,880)==oldattrs
   undo=[]
   if fault in('late-packet','late-count'):
    # First not-yet-verified shadow prefix, actual checked FE DMA.
    raw,_=f.raw_cache();row=f.m.read(0x914b);assert row<raw[1],(row,raw[1])
    at=0x200+row*0x800+0x480+(12 if fault=='late-count'else 14);transfer(at,162 if fault=='late-count'else raw[at]^1)
   elif fault=='late-header':
    raw,_=f.raw_cache();undo=[('FE',2,raw[2])];transfer(2,raw[2]^1)
   elif fault=='late-epoch':
    at=f.s['se_gc_epoch'];undo=[(at,f.read(at,2))];f.put('se_gc_epoch',(f.get('se_gc_epoch',2)+1)&65535,2)
   elif fault=='late-busy':at=f.s['se_doc_busy'];undo=[(at,f.read(at,1))];f.m.write(at,1)
   else:f.queued(3)
   for step in range(10000):
    if not f.get('se_e_job',1):break
    f.call('se_editor_service')
   else:raise AssertionError('late failure did not terminate')
   error=f.get('se_e_error',1);g.audit_end(before,fault)
   if fault!='STOP':assert error in((0x90,0xb1)if fault=='late-count'else(0xb1,0x18,0x74)),(fault,error)
   else:assert error==0
   assert f.read(0x6000+640,7040)==oldbody and f.read(0x4000+80,880)==oldattrs,(fault,'wrote VIC before completion')
   assert not f.get('se_f_owner',1)and not f.get('se_doc_read_locks',1)and f.read(0x912c,2)==b'\0\0'
   for item in undo:
    if item[0]=='FE':transfer(item[1],item[2])
    else:at,raw=item;f.m.load(at,raw)
   assert f.merged()==source and g.stable()==stable and f.catalog()==catalog
   record(fault,error=error,unchanged_before_publication=True,source_preserved=True)
   f.command(16);hot.drain(f);assert f.merged()==data;pixels(data,fault+'-undo')
  large=data+native('Far prose row.\r')*6000;setup(large)
  before=g.audit_begin();f.key(native('Q')[0]);hot.drain(f);g.audit_end(before,'far-index-edit');large_new=large[:85]+native('Q')+large[85:];pixels(large_new,'far-index-edit')
  assert g.dll.loan_get(0)>0 and not g.dll.loan_get(1)
  for command in(97,98):
   f.command(command);hot.drain(f);(bits,attrs),_,_,_=observer.geos.grid.expected(f,large_new)
   assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs
  f.typed(native('goto 6000'));hot.drain(f);at=sum(len(line)+1 for line in large_new.split(b'\r')[:5999]);assert at>65535 and f.get('se_hot_caret')==at,(at,f.get('se_hot_caret'))
  (bits,attrs),_,_,_=observer.geos.grid.expected(f,large_new);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs and f.merged()==large_new
  record('GEOSloan then60→80/GOTO>64KiB',caret=at,source_bytes=len(large_new),source_preserved=True)
  f.command(16);hot.drain(f);assert f.merged()==large
  setup();frame=f.read(0x8d00,0x480);phase=f.read(0x9149,47);before=g.reu()
  for owner in(0,1,2,3,5,255):
   f.put('se_f_owner',owner,1);f.put('se_overlay_frame',0,1);regs,used=f.m.call(f.s['se_overlay_call'],a=63,x=0,limit=2000000);f.total_instructions+=used
   assert regs.p&1 and regs.a==0xb2 and f.read(0x8d00,0x480)==frame and f.read(0x9149,47)==phase and g.reu()==before,(owner,'opaque')
  f.put('se_f_owner',0,1);record('six foreign owners',opaque=True)
  result=dict(status='PASS',identity=identity,cases=cases,scope=__doc__,private_images={n:hashlib.sha256((link/(n+'.seo')).read_bytes()).hexdigest()for n in('geospage','convergence')});(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--link',type=Path,default=LINK);p.add_argument('--out',type=Path);a=p.parse_args();out=a.out or ROOT/'build/paint-convergence-probe'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-guards');print('RUN',out,flush=True);run(out.resolve(),a.fixture.resolve(),a.link.resolve())
