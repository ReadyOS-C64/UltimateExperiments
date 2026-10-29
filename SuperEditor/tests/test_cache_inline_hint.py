"""Private C37 empty-inline hint: actual public rendering plus explicit local predicate seam."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,importlib.util,json,re,hashlib,sys,binascii
import test_cache_observer as observer
import test_plain_geos as plain
import test_grid_editor_vice as diverse
ROOT=observer.ROOT

def load_builder():
 p=ROOT/'src/cache/query/probes/hint/build.py';s=importlib.util.spec_from_file_location('emptyhint',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def symbols(p):return{n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\S+)',p.read_text())}

def run(out,base):
 g=observer.Gate(out,base);f=g.f;builder=load_builder();budget=builder.build(out/'build',g.frozen);original=dict(f.assets);candidate=(out/'build/hint/page.seo').read_bytes();cases=[]
 try:
  names=g.identity['names'];font={n:(g.frozen/'fonts'/n).read_bytes()for n in observer.geos.GEOS_FONTS+('native8.bin',)}
  labels=symbols(ROOT/'build/overlays/geosinln.lbl');assert(ROOT/'build/overlays/geosinln.bin').read_bytes()==original['geosinln'][36:]
  targets=[('entry',0xB010),('init',labels['se_si_init']),('feed',labels['se_si_feed'])]
  g.dll.pb_config(f.s['se_overlay_active'],len(targets),(C.c_uint16*3)(*(v[1]for v in targets)),(C.c_uint8*3)(2,2,2),(C.c_uint8*3)(*([names.index('geosinln')+1]*3)),(C.c_uint8*48)())
  def full():
   f.put('se_gc_width',0,1);f.m.write(0xCF90,0);f.m.write(0xCFE8,0);f.put('se_r_valid',0,1);f.put('se_l_valid',0,1);f.put('se_l_need_wrap',1,1);f.render()
  def setup(data,variant,caps):
   f.assets=dict(original)
   if variant=='hint':f.assets['page']=candidate
   f.source(data);f.typed(observer.geos.native_text('syntax full'if caps==3 else'syntax markdown'if caps==1 else'syntax plain'));f.command(99);f.render()
  def measure(tag,data,variant,caps=1,mutate=None,oracle_data=None):
   setup(data,variant,caps)
   if mutate:mutate()
   before=g.reu();canonical=g.stable();trace=[];call=f.call
   def tracked(name,a=0):
    requested=f.m.read(0x9135)if name=='se_editor_service'and f.get('se_e_job',1)==11 else 0
    r=call(name,a)
    if requested==37 and not f.m.read(0x8B40+21)and f.m.read(0x8B40+24)==0:
     cr=f.read(0x8D00+259,96);trace.append(dict(query=f.get('se_hot_caret'),kind=f.m.read(0x8B45),start=int.from_bytes(f.read(0x8B49,3),'little'),inline=f.m.read(0x8B40+169),flags=cr[2],events=int.from_bytes(cr[44:47],'little'),ref=cr[40:44].hex()))
    return r
   f.call=tracked;start=f.total_instructions;g.dll.pb_begin()
   try:full()
   finally:g.dll.pb_end();f.call=call
   used=f.total_instructions-start;counts={n:int(g.dll.pb_get(i))for i,(n,_)in enumerate(targets)}
   source=data if oracle_data is None else oracle_data
   bits,attrs,rows=plain.expected(f,source,font,caps);assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,variant,'independent pixels')
   assert f.merged()==source and g.stable()==canonical and f.read(0xC600,1024)==f.shim
   assert not any(f.get(n,1)for n in ('se_e_job','se_e_error','se_f_owner','se_doc_read_locks'))
   _,bank=f.raw_cache();after=g.reu();wanted=bytearray(before);spans=[(0,64),(0x600,0x680),(0xB200,0xD568),(0xE568,0xEA88),(0xFC00,0xFDA0)]+[(0x200+i*0x800,0x200+i*0x800+842)for i in range(22)]+[(0x700+i*0x800,0x740+i*0x800)for i in range(22)]
   for lo,hi in spans:wanted[bank*65536+lo:bank*65536+hi]=after[bank*65536+lo:bank*65536+hi]
   assert after==wanted,(tag,variant,'whole16MiB outside exact FE spans')
   observer.geos.png(bits,attrs,out/(tag+'-'+variant+'.png'))
   item=dict(tag=tag,variant=variant,caps=caps,bytes=len(data),instructions=used,c26=counts,queries=trace,bitmap_sha256=hashlib.sha256(bits).hexdigest(),attrs_sha256=hashlib.sha256(attrs).hexdigest());cases.append(item);print('PASS',tag,variant,used,counts,flush=True);return item
  sources=[('251-markdown',plain.SOURCE,1),('422-markdown',diverse.fixture(),1),('251-full',plain.SOURCE,3),('422-full',diverse.fixture(),3),('literal-unclosed',observer.geos.native_text('Prelude.\rLiteral unmatched * and @@ at EOF'),1),('native-pound-literal',observer.geos.native_text('Prelude.\rEscaped £* and ££ plus tail.\rEnd.'),1),('escapes',observer.geos.native_text('Prelude.\rEscaped £* and ££ plus tail.\rEnd.').replace(bytes([0xA3]),bytes([0x5C])),1),('head-list',observer.geos.native_text('Prelude.\r## Plain heading\r- Plain list\r\rTail.'),3),('nested',observer.geos.native_text('Prelude.\r***Bold and italic*** plus @@code **literal**@@\rTail.'),3),('256-events',observer.geos.native_text('Prelude.\r'+('**x** '*256)+'\rTail.'),1),('plain-bypass',diverse.fixture(),0)]
  for tag,data,caps in sources:
   old=measure(tag,data,'baseline',caps);new=measure(tag,data,'hint',caps);assert old['bitmap_sha256']==new['bitmap_sha256']and old['attrs_sha256']==new['attrs_sha256']
   if tag in ('251-markdown','422-markdown','literal-unclosed','head-list'):assert new['c26']['init']<old['c26']['init'],(tag,'no actual inline bypass')
   for q in new['queries']:
    expected=int(not(q['kind']<4 and q['flags']&4 and q['events']==0 and q['ref']=='ffffffff'))if q['kind']<4 else 0
    assert q['inline']==expected,(tag,q,'actual checked CR hint')
   if tag=='256-events':assert any(q['events']==256 and q['inline']==1 for q in new['queries'])
   if tag=='escapes':assert any(q['events']>=2 and q['inline']==1 for q in new['queries'])
   if caps==0:assert not new['queries']and not any(new['c26'].values())
  faults=[]
  faultdata=observer.geos.native_text('Prelude.\rSecond plain line.\rTail.')
  def object_write(offset,raw):
   token=f.read(f.s['se_bc_arena'],5);f.m.load(f.s['se_object_id'],token)
   for at in range(0,len(raw),128):
    chunk=raw[at:at+128];f.m.load(0x9000,chunk);f.put('se_object_offset',offset+at);f.put('se_object_c64',0x9000,2);f.put('se_object_length',len(chunk),2)
    r=f.call('se_object_copy',0);assert not r.p&1;assert not f.get('se_bc_flags',1)&32
  def patch_record(mode):
   token=f.read(f.s['se_bc_arena'],5);oid=token[0];logical=f.m.read(f.s['object_extents']+oid*16);physical=f.m.read(f.s['se_reu_map']+logical);bank=g.reu()[physical*65536:(physical+1)*65536]
   found=[]
   for pg in range(1,16):
    h=bank[pg*4096:pg*4096+64]
    if h[:2]!=b'BP'or h[5]!=1:continue
    used=int.from_bytes(h[21:23],'little');payload=bytearray(bank[pg*4096+64:pg*4096+64+used])
    for at in range(0,len(payload),96):
     cr=bytearray(payload[at:at+96])
     if int.from_bytes(cr[16:19],'little')!=9:continue
     assert int.from_bytes(cr[44:47],'little')==0 and cr[40:44]==bytes([255])*4
     if mode=='missing-finish':cr[2]&=~4
     elif mode=='nonnull-ref':cr[40]=1
     elif mode=='bad-record-crc':cr[2]^=4
     else:raise AssertionError(mode)
     if mode!='bad-record-crc':cr[74:76]=binascii.crc_hqx(cr[1:74]+cr[76:],0xffff).to_bytes(2,'little')
     payload[at:at+96]=cr;head=bytearray(h);head[39:41]=binascii.crc_hqx(payload,0xffff).to_bytes(2,'little');head[37:39]=binascii.crc_hqx(head[:3]+head[4:37]+head[39:],0xffff).to_bytes(2,'little')
     object_write(pg*4096+64,payload);object_write(pg*4096,head);found.append((pg,at))
   assert len(found)==1
  for mode in ('missing-finish','nonnull-ref'):
   result=measure('validcrc-'+mode,faultdata,'hint',mutate=lambda m=mode:patch_record(m))
   q=[q for q in result['queries']if q['start']==9];assert q and all(x['inline']==1 for x in q),(mode,'must conservatively retain C26',result)
   faults.append(mode+' valid record/payload/header CRC; checked classification succeeds with hint1')
  # A corrupt record cannot acquire false0 authority even with valid page/header CRC.
  setup(faultdata,'hint',1);patch_record('bad-record-crc');oldbits=f.read(0x6000,8000)+f.read(0x4000,1000);canonical=g.stable()
  try:full();raise RuntimeError('bad record unexpectedly rendered')
  except AssertionError:pass
  assert f.get('se_e_error',1)==0xC2 and not f.get('se_doc_read_locks',1)and f.get('se_f_owner',1)==0
  assert f.merged()==faultdata and g.stable()==canonical and f.read(0xC600,1024)==f.shim and f.read(0x6000,8000)+f.read(0x4000,1000)==oldbits
  faults.append('CRC-valid page with corrupt CR CRC refusesC2 before repaint; no owner/lease/source leak')
  # A visible pending edit must stay on the already-required legacy fallback.
  for variant in ('baseline','hint'):
   def insert():f.key(observer.Q);assert f.get('se_hot_pending',1)and f.get('se_bc_count',1)>0
   result=measure('pending-edit',faultdata,variant,mutate=insert,oracle_data=bytes([observer.Q])+faultdata)
   assert not result['queries'],'queued source edit entered optional C37 cache'
  faults.append('actual pending insertion/source preserved; queued edit never enters C37')
  # Fault only the visible revision after C37 owns its real read lease.
  setup(faultdata,'hint',1);canonical=g.stable();oldbits=f.read(0x6000,8000)+f.read(0x4000,1000);call=f.call;injected=[False]
  def change_source(name,a=0):
   if name=='se_editor_service'and not injected[0]and f.read(0x9135,2)==bytes((37,1))and f.get('se_doc_read_locks',1):
    f.put('se_r_revision',f.get('se_r_revision',4)+1,4);injected[0]=True
   return call(name,a)
  f.call=change_source
  try:
   try:full();raise RuntimeError('source revision fault unexpectedly rendered')
   except AssertionError:pass
  finally:f.call=call
  assert injected[0]and f.get('se_e_error',1)in(0xB1,0xC1)and not f.get('se_doc_read_locks',1)and f.get('se_f_owner',1)==0
  assert f.merged()==faultdata and g.stable()==canonical and f.read(0xC600,1024)==f.shim and f.read(0x6000,8000)+f.read(0x4000,1000)==oldbits
  faults.append('mid-C37 lease source revision fault refuses before repaint; actual reader cleanup')
  # Exact owner refusal stays before phase/presentation reads for the actual capsule.
  setup(faultdata,'hint',1)
  for owner in (0,1,2,3,5,255):
   f.put('se_f_owner',owner,1);phase=f.read(0x8D00,1152);semantic=f.read(0x8B40,192);reu=g.reu()
   for op in (0,1,2):
    f.put('se_overlay_frame',op,1);r,_=f.fast_call(f.s['se_overlay_call'],a=37,x=1)
    assert r.p&1 and r.a==0xB2 and f.read(0x8D00,1152)==phase and f.read(0x8B40,192)==semantic and g.reu()==reu
  f.put('se_f_owner',0,1);faults.append('six foreign owners/all3ops phaseopaque/whole16MiB unchanged')
  # Pure predicate CPU seam: execute only the actual new local instructions,
  # never claim these host-seeded inputs are authenticated semantic records.
  raw=candidate[36:];needle=bytes([0xAD,0x45,0x8B,0xC9,4,0xB0]);spots=[i for i in range(len(raw))if raw.startswith(needle,i)];assert len(spots)==1;start=0xB000+spots[0];stop=symbols(out/'build/hint/page.lbl')['@not_inline']
  f.m.load(0xB000,raw);cpp=out/'predicate.cpp';cpp.write_text('''#include "zeropage_peddle.h"
extern "C" unsigned hint_run(ZeroPagePeddle*m,unsigned stop){for(unsigned i=0;i<100;i++){if(zeropage_peddle_regs(m).pc==stop)return i;zeropage_peddle_step_instruction(m);}return 0;}
extern "C" void hint_read(ZeroPagePeddle*m,uint8_t*out){for(unsigned i=0;i<65536;i++)out[i]=zeropage_peddle_read(m,i);}
''');builder.command(['clang++','-std=c++20','-O2','-dynamiclib','-fPIC','-I'+str(observer.geos.grid.VENDOR),cpp,ROOT/'build/libse_peddle.dylib','-o',out/'predicate.dylib']);dll=C.CDLL(str(out/'predicate.dylib'));dll.hint_run.argtypes=[C.c_void_p,C.c_uint];dll.hint_read.argtypes=[C.c_void_p,C.c_void_p]
  def ram():v=C.create_string_buffer(65536);dll.hint_read(f.m.handle,v);return v.raw
  pure=0
  for kind in (0,1,2,3,5):
   for flags in range(16):
    for count in (0,1,256,65536):
     for ref in (bytes([255])*4,bytes(4),bytes([0,255,255,255]),bytes([255,0,255,255]),bytes([255,255,0,255]),bytes([255,255,255,0])):
      f.m.write(0x8B45,kind);f.m.write(0x8BE9,0);f.m.write(0x8D00+259+2,flags);f.m.load(0x8D00+259+44,count.to_bytes(3,'little'));f.m.load(0x8D00+259+40,ref)
      f.m.lib.zeropage_peddle_set_pc(f.m.handle,start);before=ram();used=dll.hint_run(f.m.handle,stop);assert used;after=ram();expected=int(kind<4 and not(flags&4 and count==0 and ref==bytes([255])*4));want=bytearray(before);want[0x8BE9]=expected
      assert after==want and f.m.regs().a==kind,('predicate whole64KiB/A',kind,flags,count,ref.hex());pure+=1
  result=dict(status='PASS',fixture=str(base),budget=budget,cases=cases,faults=faults,predicate_cases=pure,whole64KiB_predicate_intervals=pure,scope='Actual private C37 public renderer A/B with real C7/R33/C34/C35 source/CRC authority. Local predicate truth table is explicitly host-seeded component seam, not authenticated query proof. No shared product/native changes.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();out=ROOT/'build/cache-inline-hint'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)
