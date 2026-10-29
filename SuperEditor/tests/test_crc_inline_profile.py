"""Canonical optional inline half-CRC: real CPU/all lengths/reference/guards."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,ctypes as C,hashlib,json,re,subprocess,sys,struct,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine,VENDOR,library
from overlays import wrap
DEFAULT=ROOT/'build/geos-semantic-editor/20261025T030943698099Z/fixture'
FLAGS=['FAST_EDITOR_CRC=1','EDITOR_HALF_CRC=1','EDITOR_CATALOG_TAIL=1','EDITOR_FIXED_ENTRY=1','OVL_LIMIT=32']
def command(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
def labels(p):return {n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',p.read_text())}
def build(out,base,source,inline=False):
 out.mkdir(parents=True);r=json.loads((base/'build/editor-report.json').read_text());s=r['symbols']
 cfg=f'''MEMORY {{ C:file=%O,start=$7000,size=$0F00; Z:file="",start=${s['ovl_ptr']:04X},size=2; B:file="",start=${s['se_overlay_asset']:04X},size=$100; T:file="",start=${s['se_overlay_ids']:04X},size=$C0; }} SEGMENTS {{ CODE:load=C,type=ro,define=yes; RODATA:load=C,type=ro; ZEROPAGE:load=Z,type=zp; BSS:load=B,type=bss; OVERLAY_CATALOG:load=T,type=bss; }}'''
 (out/'cache.cfg').write_text(cfg);cmd=['ca65','-g','-I','src','-o',out/'cache.o']
 for flag in FLAGS+(['EDITOR_INLINE_HALF_CRC=1'] if inline else []):cmd+=['-D',flag]
 command(*cmd,source);command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',out/'cache.o');command('ca65','-o',out/'aliases.o',out/'aliases.s')
 command('ld65','-C',out/'cache.cfg','-o',out/'cache.bin','-Ln',out/'cache.lbl','-m',out/'cache.map',out/'cache.o',out/'aliases.o');lab=labels(out/'cache.lbl')
 for n in ['se_overlay_asset','se_overlay_ids','se_overlay_active','se_overlay_frame','ovl_ptr','crc_remaining']:assert lab[n]==s[n],(n,lab[n],s[n])
 return lab

def driver(out):
 library();p=out/'runner.cpp';p.write_text('''#include "zeropage_peddle.h"
#include <cstdint>
static uint16_t hp,ht;static uint64_t hits;
extern "C" void ci_hook(uint16_t p,uint16_t t){hp=p;ht=t;}
extern "C" uint64_t ci_hits(){return hits;}
extern "C" uint16_t ci_call(ZeroPagePeddle*m,uint16_t pc,uint8_t a,uint8_t x,uint8_t y){
zeropage_peddle_set_pc(m,pc);zeropage_peddle_set_sp(m,0xfd);zeropage_peddle_set_p(m,0x24);zeropage_peddle_set_a(m,a);zeropage_peddle_set_x(m,x);zeropage_peddle_set_y(m,y);zeropage_peddle_write(m,0x1fe,0xfe);zeropage_peddle_write(m,0x1ff,2);hits=0;
for(int i=0;i<1000000;i++){auto r=zeropage_peddle_regs(m);if(r.pc==0x2ff)return r.a|(r.p<<8);if(r.pc==hp||r.pc==ht)hits++;zeropage_peddle_step_instruction(m);}return 0xffff;}
extern "C" void ci_ram(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*p){for(uint32_t i=0;i<n;i++)p[i]=zeropage_peddle_read(m,a+i);}
extern "C" void ci_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*p){for(uint32_t i=0;i<n;i++)p[i]=zeropage_peddle_read_reu(m,i);}
extern "C" int ci_case(ZeroPagePeddle*m,uint16_t pc,uint16_t ptr,uint16_t head,uint16_t value,uint16_t bytepc,uint16_t tailpc,uint16_t n,uint16_t crc,uint8_t error,uint64_t*out){
zeropage_peddle_write(m,head+8,n);zeropage_peddle_write(m,head+9,n>>8);zeropage_peddle_write(m,head+12,crc);zeropage_peddle_write(m,head+13,crc>>8);
zeropage_peddle_set_pc(m,pc);zeropage_peddle_set_sp(m,0xfd);zeropage_peddle_set_p(m,0x24);zeropage_peddle_write(m,0x1fe,0xfe);zeropage_peddle_write(m,0x1ff,2);
auto before=zeropage_peddle_regs(m);unsigned fed=0,steps=0;
for(;steps<100000;steps++){auto r=zeropage_peddle_regs(m);if(r.pc==0x2ff)break;if(r.pc==bytepc || r.pc==tailpc){uint16_t addr=uint16_t(zeropage_peddle_read(m,ptr)|(zeropage_peddle_read(m,ptr+1)<<8))+r.y;if(addr!=0x5000+fed)return 4;fed++;}zeropage_peddle_step_instruction(m);}
auto r=zeropage_peddle_regs(m);out[0]=r.instructions-before.instructions;out[1]=r.cycles-before.cycles;out[2]=fed;
if(steps==100000)return 1;if(error){if(!(r.p&1)||r.a!=error)return 2;}else if(r.p&1)return 3;
if(error!=0x11 && fed!=n)return 5;if(error==0x11 && fed)return 6;
if(error==0 && (zeropage_peddle_read(m,value)|(zeropage_peddle_read(m,value+1)<<8))!=crc)return 7;return 0;}
''');ext='.dylib' if sys.platform=='darwin' else '.so';lib=out/('runner'+ext);command('clang++','-std=c++20','-O2','-dynamiclib' if ext=='.dylib' else '-shared','-fPIC','-I'+str(VENDOR),p,ROOT/('build/libse_peddle'+ext),'-o',lib);d=C.CDLL(str(lib));d.ci_case.argtypes=[C.c_void_p]+[C.c_uint16]*8+[C.c_uint8,C.POINTER(C.c_uint64)];d.ci_case.restype=C.c_int;d.ci_call.argtypes=[C.c_void_p,C.c_uint16,C.c_uint8,C.c_uint8,C.c_uint8];d.ci_call.restype=C.c_uint16;d.ci_hook.argtypes=[C.c_uint16,C.c_uint16];d.ci_hits.restype=C.c_uint64;d.ci_ram.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];d.ci_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p];return d

def main(out,base):
 r=json.loads((base/'build/editor-report.json').read_text());s=r['symbols'];digest=bytes.fromhex(r['resident_binding']['digest']);prg=(base/'build/editor.prg').read_bytes();assert hashlib.sha256(prg).hexdigest()==r['sha256']
 baseline_source=out/'baseline-cache.s'
 with zipfile.ZipFile(base/'product-sources.zip') as archive:baseline_source.write_bytes(archive.read('src/overlay/cache.s'))
 old=build(out/'baseline',base,baseline_source);default=build(out/'candidate-default',base,ROOT/'src/overlay/cache.s');new=build(out/'candidate',base,ROOT/'src/overlay/cache.s',True)
 assert (out/'baseline/cache.bin').read_bytes()==(out/'candidate-default/cache.bin').read_bytes(),'generic flag-absent cache changed'
 original_flags=list(FLAGS)
 for variant,flags in [('generic-full',[f for f in original_flags if f!='EDITOR_HALF_CRC=1']),('generic-slow',[f for f in original_flags if f not in ['EDITOR_HALF_CRC=1','FAST_EDITOR_CRC=1']])]:
  FLAGS[:]=flags;build(out/(variant+'-baseline'),base,baseline_source);build(out/(variant+'-candidate'),base,ROOT/'src/overlay/cache.s');assert (out/(variant+'-baseline')/'cache.bin').read_bytes()==(out/(variant+'-candidate')/'cache.bin').read_bytes(),variant
 FLAGS[:]=original_flags
 rejected=[]
 for remove in [('FAST_EDITOR_CRC=1','EDITOR_HALF_CRC=1'),('FAST_EDITOR_CRC=1',),('EDITOR_HALF_CRC=1',)]:
  flags=[f for f in FLAGS if f not in remove]+['EDITOR_INLINE_HALF_CRC=1'];cmd=['ca65','-I','src','-o',str(out/'invalid-config.o')]
  for flag in flags:cmd+=['-D',flag]
  proc=subprocess.run(cmd+['src/overlay/cache.s'],cwd=ROOT,text=True,capture_output=True);assert proc.returncode and 'EDITOR_INLINE_HALF_CRC requires' in proc.stderr,(flags,proc.stderr);rejected.append(dict(missing=list(remove),diagnostics=proc.stderr))
 delta=new['__CODE_SIZE__']-old['__CODE_SIZE__'];gap=next(x['start'] for x in r['segments'] if x['name']=='CRC_TABLE')-max(x['end']+1 for x in r['segments'] if x['name'] in ['ENTRY','CODE','CORE','RODATA']);assert delta<=gap,(delta,gap)
 dll=driver(out);metrics={};source=digest+bytes(((i*73+29)^(i>>8))&255 for i in range(16,4096));crcs=[binascii.crc_hqx(source[:n],0xFFFF) for n in range(1,4097)]
 for name,lab in [('baseline',old),('candidate',new)]:
  m=Machine();m.load(int.from_bytes(prg[:2],'little'),prg[2:]);m.load(0x7000,(out/name/'cache.bin').read_bytes());m.load(0x5000,source);shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim)
  before=bytes(m.read(i) for i in range(65536));cases=[];faults=[]
  def case(n,crc,error=0):
   stats=(C.c_uint64*3)();code=dll.ci_case(m.handle,lab['crc_stage'],lab['ovl_ptr'],s['se_overlay_header'],s['se_crc_value'],lab['se_overlay_crc_page_byte'],lab['se_overlay_crc_tail_byte'],n,crc,error,stats);assert not code,(name,n,error,code,list(stats));return list(stats)
  try:
   for n,crc in enumerate(crcs,1):cases.append(case(n,crc))
   for n in [17,31,127,128,255,256,257,511,512,513,1023,1024,1025,2047,2048,2049,4095,4096]:
    # Actual changed payload, expected original checksum.
    for offset in sorted(set([16,n-1,n//2 if n//2>=16 else 16])):
     m.write(0x5000+offset,source[offset]^1);case(n,crcs[n-1],0x14);m.write(0x5000+offset,source[offset]);faults.append([n,offset,0x14])
    m.write(0x5000,source[0]^1);case(n,crcs[n-1],0x11);m.write(0x5000,source[0]);faults.append([n,0,0x11])
   after=bytes(m.read(i) for i in range(65536));want=bytearray(before)
   for a,n in [(0x100,256),(s['se_overlay_header']+8,2),(s['se_overlay_header']+12,2),(s['se_crc_value'],2),(lab['ovl_ptr'],2),(lab['crc_remaining'],2)]:want[a:a+n]=after[a:a+n]
   assert after==want,(name,'wholeRAMsource/table/shim/active/REUdescriptor changed',[(i,a,b) for i,(a,b) in enumerate(zip(after,want)) if a!=b][:10])
   metrics[name]=dict(code_bytes=lab['__CODE_SIZE__'],all_lengths=4096,total_instructions=sum(x[0] for x in cases),total_cycles=sum(x[1] for x in cases),source_bytes=sum(x[2] for x in cases),faults=faults,representative={str(n):cases[n-1] for n in [1,17,255,256,257,4095,4096]})
  finally:m.close()
 public=public_gate(out,base,r,new,dll,source)
 result=dict(status='passed',resident=r['sha256'],metrics=metrics,code_delta=delta,available_gap=gap,generic_default_byte_identical=True,required_flag_rejections=rejected,canonical_source_sha256=hashlib.sha256((ROOT/'src/overlay/cache.s').read_bytes()).hexdigest(),baseline_source_sha256=hashlib.sha256(baseline_source.read_bytes()).hexdigest(),public_cache=public,wholeRAM_guard=65536,oracle='binascii.crc_hqx(payload,0xFFFF)',scope='Actual canonical cache with optional EDITOR_INLINE_HALF_CRC, all-length and public-cache gates; root default flag remains disabled, no integrated/native speed claim')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
def public_gate(out,base,r,lab,dll,source):
 s=r['symbols'];digest=bytes.fromhex(r['resident_binding']['digest']);m=Machine();prg=(base/'build/editor.prg').read_bytes();m.load(int.from_bytes(prg[:2],'little'),prg[2:]);m.load(0x7000,(out/'candidate/cache.bin').read_bytes());shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim);dll.ci_hook(lab['se_overlay_crc_page_byte'],lab['se_overlay_crc_tail_byte']);cases=[];rejects=[]
 def read(a,n):
  b=C.create_string_buffer(n);dll.ci_ram(m.handle,a,n,b);return b.raw
 def reu():
  b=C.create_string_buffer(8*65536);dll.ci_reu(m.handle,len(b),b);return b.raw
 def get(n,size=1):return int.from_bytes(read(s[n],size),'little')
 def put(n,value,size=1):m.load(s[n],value.to_bytes(size,'little'))
 def call(pc,a=0,x=0,y=0,error=None):
  v=dll.ci_call(m.handle,pc,a,x,y);assert v!=65535,('nonreturn',hex(pc));actual=v&255;carry=(v>>8)&1
  if error!=-1:assert (carry and actual==error) if error is not None else not carry,(hex(pc),actual,carry,error)
 def image(data,id_=91):return wrap(data,0,id_,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=digest)
 def import_(blob,error=None):
  m.load(s['se_overlay_header'],blob[:36]);m.load(0x5000,blob[36:]);call(lab['se_overlay_import'],error=error)
 def patch(offset,byte):
  put('se_reu_logical',get('se_overlay_asset'));put('se_reu_offset',offset,3);put('se_reu_c64',0x8000,2);put('se_reu_length',1,2);m.write(0x8000,byte);call(s['se_reu_copy'])
 try:
  for n in [17,18,20,127,128,255,256,257,511,512,513,1023,1024,1025,2047,2048,2049,4095,4096]:
   call(s['se_clear_state']);put('se_reu_banks',8,2);call(s['se_reu_provider_init']);call(s['se_reu_bind'],a=4,x=200,y=1);call(lab['se_overlay_init'])
   token=get('se_overlay_asset');physical=m.read(s['se_reu_map']+token);assert token==1 and physical==2
   before_reu=reu();data=bytearray(source[:n]);data[16:20]=b'\xA9\x61\x18\x60'[:n-16] if n>=20 else b'\x18\x60'[:n-16]
   if n==17:data[16]=0x60
   data=bytes(data);import_(image(data));assert dll.ci_hits()==n
   call(lab['se_overlay_call'],a=91,x=0,error=-1 if n==17 else None);assert dll.ci_hits()==n and read(0xA000,n)==data
   dm=get('se_reu_dma_calls',2);call(lab['se_overlay_call'],a=91,x=0,error=-1 if n==17 else None);assert not dll.ci_hits() and get('se_reu_dma_calls',2)==dm
   other=digest+b'\xA9\x62\x18\x60';import_(image(other,92));call(lab['se_overlay_call'],a=92,x=0)
   for offset in sorted(set([16,n-1,0])):
    patch(offset,data[offset]^1);active=read(s['se_overlay_active'],2);slot=read(0xA000,4096);whole=reu();loads=get('se_overlay_loads',2);dm=get('se_reu_dma_calls',2)
    call(lab['se_overlay_call'],a=91,x=0,error=0x11 if offset==0 else 0x14)
    assert dll.ci_hits()==(0 if offset==0 else n) and read(0xA000,4096)==slot and read(s['se_overlay_active'],2)==active and get('se_overlay_loads',2)==loads and reu()==whole
    assert get('se_reu_dma_calls',2)==dm+1 and read(s['se_overlay_busy'],2)==bytes(2)
    patch(offset,data[offset]);cases.append(dict(length=n,corrupt_offset=offset,error=0x11 if offset==0 else 0x14))
   after=reu();start=physical*65536;want=bytearray(before_reu);want[start:start+n]=data;want[start+4096:start+4116]=other;assert after==want
   assert read(0xC600,1024)==shim
  for declared in [0,16,4097]:
   blob=bytearray(image(digest+b'\x18\x60\xEA\xEA',93));blob[8:10]=struct.pack('<H',declared);blob[14:16]=struct.pack('<H',binascii.crc_hqx(blob[:14]+blob[16:36],0xFFFF));dm=get('se_reu_dma_calls',2);active=read(s['se_overlay_active'],2);import_(blob,error=0x13);assert not dll.ci_hits() and get('se_reu_dma_calls',2)==dm and read(s['se_overlay_active'],2)==active;rejects.append(declared)
  blob=bytearray(image(digest+b'\x18\x60\xEA\xEA',93));blob[14]^=1;dm=get('se_reu_dma_calls',2);import_(blob,error=0x10);assert not dll.ci_hits() and get('se_reu_dma_calls',2)==dm
  return dict(valid_lengths=19,corruption_cases=cases,invalid_lengths_before_payloadCRC=rejects,bad_header_before_payloadCRC=True,cache_hits_no_DMA_or_CRC=True,active_slot_preserved_on_corruption=True,full_REU_bytes=8*65536,nonidentity_mapping=[1,2])
 finally:m.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=DEFAULT);a=p.parse_args();out=ROOT/'build/crc-inline'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);main(out,a.fixture)
