"""Private actual C20 packet->R34scatter->CRC->packet component proof.

Canonical startup, source and C20/C21/C22/R21 are used unchanged. R34 is an
explicit additional component import, not a product startup/UI integration.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,shutil,subprocess,sys,binascii
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import test_geos_semantic_editor as semantic
geos=semantic.geos
from overlays import wrap
BASE=ROOT/'build/cache-editor-product/20261026T010418788084Z/fixture'
D=ROOT/'src/cache/layout';STATE=0x8D00;META=0x8880;BUF=0x8D40
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def cmd(args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
 assert p.returncode==0,(args,p.stdout,p.stderr)
def build(out,base):
 out.mkdir(parents=True,exist_ok=True)
 cmd([sys.executable,ROOT/'src/fold/editor-leaves/binding.py','--report',base/'build/editor-report.json','--output',out/'editor-api.inc'])
 objects=[]
 for name in ('entry','memo','transport'):
  obj=out/(name+'.o');args=['ca65','-g','-I',out,'-I',ROOT/'src','-o',obj,'-l',out/(name+'.lst')]
  if name=='transport':args+=['-D','SE_GP_CACHE_WARM_ONLY=1']
  cmd(args+[D/(name+'.s')]);objects.append(obj)
 cmd([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects])
 cmd(['ca65',out/'aliases.s','-o',out/'aliases.o']);objects.append(out/'aliases.o')
 cmd(['ld65','-C',ROOT/'cfg/overlay-r.cfg','-o',out/'image.bin','-m',out/'image.map','-Ln',out/'image.lbl',*objects])
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];raw=(out/'image.bin').read_bytes()
 image=wrap(raw,0,34,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(report['resident_binding']['digest']));(out/'layoutmemo.seo').write_bytes(image)
 return image

def profiled_runner(out):
 old=geos.grid.runner(out);cpp=out/'runner.cpp';source=cpp.read_text()
 extra=r'''
static uint16_t lm_active=0;static uint8_t lm_indices[4];static uint64_t lm_totals[8]={};static int lm_category=-1;static uint16_t lm_stop=0;static uint8_t lm_stack=0;
extern "C" void gm_lm_monitor(uint16_t active,uint8_t a,uint8_t b,uint8_t c,uint8_t d){lm_active=active;lm_indices[0]=a;lm_indices[1]=b;lm_indices[2]=c;lm_indices[3]=d;for(auto &v:lm_totals)v=0;lm_category=-1;}
extern "C" uint64_t gm_lm_metric(int i){return lm_totals[i];}
'''
 source=source.replace('static void step(ZeroPagePeddle*m)',extra+'static void step(ZeroPagePeddle*m)')
 needle='int offset=-1;'
 hook=r'if(lm_category<0 && lm_active && r.pc==0xB010){auto index=zeropage_peddle_read(m,lm_active);for(int i=0;i<4;i++)if(index==lm_indices[i]){lm_category=i;lm_totals[i*2]++;lm_stack=r.sp;lm_stop=uint16_t(zeropage_peddle_read(m,0x100+uint8_t(r.sp+1))|(zeropage_peddle_read(m,0x100+uint8_t(r.sp+2))<<8))+1;break;}}if(lm_category>=0)lm_totals[lm_category*2+1]++;'
 assert needle in source;source=source.replace(needle,needle+hook)
 needle='zeropage_peddle_step_instruction(m);'
 source=source.replace(needle,needle+r'if(lm_category>=0){auto after=zeropage_peddle_regs(m);if(after.pc==lm_stop && after.sp==uint8_t(lm_stack+2))lm_category=-1;}')
 cpp=out/'profile-runner.cpp';cpp.write_text(source);path=out/'profile-runner.dylib'
 cmd(['clang++','-std=c++20','-O2','-dynamiclib','-fPIC','-I'+str(geos.grid.VENDOR),cpp,ROOT/'build/libse_peddle.dylib','-o',path]);dll=C.CDLL(str(path))
 for name in ['gm_rom','gm_rom_count','gm_profile','gm_metric','gm_run','gm_idle','gm_read','gm_reu']:
  getattr(dll,name).argtypes=getattr(old,name).argtypes;getattr(dll,name).restype=getattr(old,name).restype
 dll.gm_lm_monitor.argtypes=[C.c_uint16,C.c_uint8,C.c_uint8,C.c_uint8,C.c_uint8];dll.gm_lm_metric.argtypes=[C.c_int];dll.gm_lm_metric.restype=C.c_uint64
 return dll

def spans():
 result=[]
 for i in range(22):
  start=0x600+i*0x800
  if i in (0,2):start+=128
  result.extend(((start,0x700+i*0x800),(0x740+i*0x800,0xA00+i*0x800)))
 assert sum(b-a for a,b in result)==20864
 return result
SPANS=spans()
def stream(raw):return b''.join(raw[a:b]for a,b in SPANS)
def packet_payload(raw):
 n=raw[1];return raw[:64]+b''.join(raw[0x200+i*0x800:0x200+i*0x800+842]+raw[0x700+i*0x800:0x740+i*0x800]for i in range(n))+raw[0x600:0x680]
def run(out,base):
 out.mkdir(parents=True);print('RUN',out,flush=True)
 # Reuse the immutable base directly; component build outputs remain private.
 frozen=base;identity=json.loads((base/'freeze.json').read_text());geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen;geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 image=build(out/'component',base);dll=profiled_runner(out);f=geos.Fixture(out,frozen,dll,True)
 def reu():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(f.m.handle,len(b),b);return b.raw
 metrics=[]
 def invoke(op):
  cycles=f.m.regs().cycles;calls=f.get('se_reu_dma_calls',2);count=f.get('se_reu_dma_bytes',3)
  f.put('se_overlay_frame',op,1);r,n=f.fast_call(f.s['se_overlay_call'],a=34,x=0)
  transfer=f.m.read(0xDF07)|(f.m.read(0xDF08)<<8)
  assert transfer<=128,('component last DMA exceeds128',op,transfer)
  metrics.append(dict(op=op,phase=f.m.read(STATE),A=r.a,C=r.p&1,instructions=n,cycles=r.cycles-cycles,DMA_calls=(f.get('se_reu_dma_calls',2)-calls)&65535,DMA_bytes=(f.get('se_reu_dma_bytes',3)-count)&0xFFFFFF,last_DMA_length=transfer))
  return r,n
 def drain(op):
  r,n=invoke(op);steps=1;cost=n
  while not r.p&1 and r.a==1:
   assert steps<10000
   r,n=invoke(18);steps+=1;cost+=n
  return r,steps,cost
 def admitted():
  f.m.load(f.s['se_overlay_header'],image[:36]);f.m.load(0x5000,image[36:]);assert not f.call('se_overlay_import').p&1
 def fs_snapshot():
  f.put('se_f_owner',4,1);f.put('se_overlay_frame',0,1)
  r,n=f.fast_call(f.s['se_overlay_call'],a=14,x=0);assert not r.p&1,('actual FS BEGIN',r.a)
  snapshot=f.read(f.s['se_fs_identity'],59);assert not f.call('se_fs_end').p&1
  f.put('se_f_owner',0,1);return snapshot.hex()
 def semantic_key():
  return dict(tokens=f.read(f.s['se_doc_meta'],15).hex(),generation=f.get('se_doc_generation',2),revision=f.get('se_r_revision',4),merged=f.get('se_v_length'),AUTH=f.read(f.s['se_bc_arena'],13).hex(),hot=f.read(f.s['se_hot_base'],3).hex(),pending=f.get('se_hot_pending',1))
 try:
  from test_grid_editor_vice import fixture as diverse422
  data=diverse422()
  def reset_profile():dll.gm_lm_monitor(f.s['se_overlay_active']+1,*[identity['names'].index(n)+1 for n in ('geosline','geossema','geoslex','geosinln')])
  def profile():return {n:dict(calls=dll.gm_lm_metric(i*2),inclusive_instructions=dll.gm_lm_metric(i*2+1))for i,n in enumerate(('C20','C24','C25','C26'))}
  f.source(data);admitted();reset_profile();f.command(99);f.render();producer_profile=profile();initial,physical=f.raw_cache();before=reu();canonical=f.canonical();catalog=f.catalog();shim=f.read(0xC600,1024)
  f.put('se_f_owner',4,1);f.m.load(STATE,bytes(64));r,steps,cost=drain(16)
  if r.p&1 or r.a:(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise AssertionError(('capture',r.a,r.p,f.m.read(STATE),steps,cost))
  raw,_=f.raw_cache();packed=stream(raw);meta=packed[:320];payload=packet_payload(initial)
  (out/'produced-layout.bin').write_bytes(payload);(out/'memo-metadata.bin').write_bytes(meta);(out/'source.bin').write_bytes(data)
  assert meta[0]==0xA5 and meta[1:3]==bytes((0x4C,1)),meta[:12].hex()
  assert packed[320:320+len(payload)]==payload,('payload',len(payload),next((i,a,b)for i,(a,b)in enumerate(zip(packed[320:],payload))if a!=b))
  assert int.from_bytes(meta[6:8],'little')==binascii.crc_hqx(payload,65535),'wholepayloadCRC'
  assert int.from_bytes(meta[8:10],'little')==binascii.crc_hqx(meta[1:8]+meta[10:],65535),'metadataCRC'
  after=reu();start=physical*65536;allowed=[(start+a,start+b)for a,b in SPANS];cursor=0
  for a,b in allowed:assert before[cursor:a]==after[cursor:a],('outside memo',cursor,a);cursor=b
  assert before[cursor:]==after[cursor:]
  assert f.canonical()==canonical and f.catalog()==catalog and f.read(0xC600,1024)==shim and f.merged()==data
  print('FIRST CAPTURE PASS',steps,cost,'bytes',len(payload),flush=True)
  (out/'capture.json').write_text(json.dumps(dict(status='passed',rows=initial[1],payload=len(payload),steps=steps,instructions=cost,metadata=meta.hex(),allowed=SPANS),indent=2)+'\n')
  # Actual public POSITION performs the real W_LOAD. Retain both identity
  # snapshots, rather than asserting that navigation leaves FS59 unchanged.
  f.put('se_f_owner',0,1);old=semantic_key();old['actual_FS59']=fs_snapshot();f.position(len(data));new=semantic_key();new['actual_FS59']=fs_snapshot();f.render();page_b,_=f.raw_cache();assert page_b[32:35]!=initial[32:35],'real second viewport must differ';restore_before=reu();canonical_B=f.canonical();pixels_B=f.read(0x6000,8000)+f.read(0x4000,1000)
  f.put('se_f_owner',4,1);f.m.load(STATE,bytes(64));f.m.load(STATE+26,initial[32:35]);r,steps2,cost2=drain(17)
  if r.p&1 or r.a:(out/'failure-ram.bin').write_bytes(f.read(0,65536));raise AssertionError(('restore',r.a,r.p,f.m.read(STATE),steps2,cost2,old,new))
  restored,_=f.raw_cache();(out/'restored-layout.bin').write_bytes(packet_payload(restored));assert packet_payload(restored)==payload,('restored packet mismatch',next((i,a,b)for i,(a,b)in enumerate(zip(packet_payload(restored),payload))if a!=b))
  assert f.merged()==data and f.read(0xC600,1024)==shim and f.canonical()==canonical_B
  assert f.read(0x6000,8000)+f.read(0x4000,1000)==pixels_B,'memo service never paints VIC/body'
  restore_after=reu();primary=[(0,64),(0x600,0x680)]+[(a,b)for i in range(initial[1])for a,b in ((0x200+i*0x800,0x200+i*0x800+842),(0x700+i*0x800,0x740+i*0x800))]
  cursor=0
  for a,b in sorted((start+a,start+b)for a,b in primary):assert restore_before[cursor:a]==restore_after[cursor:a],('restore outside primary',cursor,a);cursor=b
  assert restore_before[cursor:]==restore_after[cursor:]
  # Explicit viewport setup qualifies the current C21 packet consumer, not a
  # new public navigation route. A missing actual C20 capability makes any
  # accidental re-layout fail; expected pixels remain independent raw-font.
  f.put('se_f_owner',0,1);f.position(0);f.put('se_v_top',int.from_bytes(initial[32:35],'little'));f.m.write(0xCF90,0)
  c20=next(i for i in range(f.s['se_overlay_capacity'])if f.m.read(f.s['se_overlay_ids']+i)==20 and f.m.read(f.s['image_slot']+i)&1)
  f.m.write(f.s['se_overlay_ids']+c20,0);reset_profile();consumer_start=f.total_instructions;f.render();consumer_instructions=f.total_instructions-consumer_start;consumer_profile=profile();assert all(v['calls']==0 for v in consumer_profile.values()),consumer_profile;f.m.write(f.s['se_overlay_ids']+c20,20)
  fonts={n:(base/'fonts'/n).read_bytes()for n in geos.GEOS_FONTS+('native8.bin',)}
  bits,attrs,rows,model=semantic.expected(f,data,fonts)
  assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,'restored packets independent pixels'
  geos.png(bits,attrs,out/'restored-packet-consumer.png')
  assert f.merged()==data and f.read(0xC600,1024)==shim
  # Same-input warm forced-full control AFTER the restored consumer: same
  # caret/hotrepresentation. Only explicit derived validity is revoked.
  f.m.load(0x8000,bytes(1));f.put('se_reu_logical',f.get('se_gc_handle',1),1);f.put('se_reu_offset',0,2);f.put('se_reu_c64',0x8000,2);f.put('se_reu_length',1,2);assert not f.call('se_reu_copy',0).p&1;f.call('se_doc_invalidate')
  f.m.write(0xCF90,0);f.put('se_l_valid',0,1);f.put('se_r_valid',0,1);f.put('se_e_redraw',1,1);reset_profile();forced_start=f.total_instructions;f.render();forced_instructions=f.total_instructions-forced_start;forced_profile=profile()
  assert forced_profile['C20']['calls']>0,'forced control must execute realC20'
  assert f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs and f.merged()==data
  (out/'service-trace.json').write_text(json.dumps(metrics,indent=2)+'\n')
  result=dict(status='passed',component_bytes=len(image)-36,baseline=str(base),baseline_PRG=identity['prg_sha256'],capture=dict(steps=steps,instructions=cost),restore=dict(steps=steps2,instructions=cost2),max_service_cycles=None,CPU_clock_unavailable=not any(m['cycles']for m in metrics),max_service_instructions=max(m['instructions']for m in metrics),DMA_calls=sum(m['DMA_calls']for m in metrics),DMA_bytes=sum(m['DMA_bytes']for m in metrics),restored_consumer_without_C20=True,producer_profile=producer_profile,consumer_profile=consumer_profile,actual_second_TOP=int.from_bytes(page_b[32:35],'little'),restored_repaint_instructions=consumer_instructions,memo_restore_plus_repaint_instructions=cost2+consumer_instructions,same_input_forced_full_instructions=forced_instructions,same_input_forced_profile=forced_profile,payload_bytes=len(payload),metadata_bytes=320,capacity=20864,full_RAM_and_REU_scope='source/canonical/shim +16MiB outside exact scatter capture; actual W_LOAD identity field map',before_W_LOAD=old,after_W_LOAD=new,source_sha256={str(p.relative_to(ROOT)):SHA(p)for p in D.iterdir()if p.is_file()},product_integration=False)
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();run(ROOT/'build/cache-layout'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),a.fixture.resolve())
