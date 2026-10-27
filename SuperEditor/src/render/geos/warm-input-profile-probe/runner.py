"""Read-only CPU PC/JSR/DMA counters; source-matched C32 stage attribution."""
from pathlib import Path
import ctypes as C,subprocess,sys
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_observer as observer
N=65536+65*4096
ORIGINAL=observer.runner

def build(out):
 old=ORIGINAL(out);p=out/'runner.cpp';s=p.read_text();needle='static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);'
 extra=r'''
#include <cstdlib>
static uint64_t wp_self[331776],wp_inc[331776],wp_calls[331776],wp_total,wp_modules[66],wp_dma[2][256][2];
static uint16_t wp_active,wp_copy,wp_req,wp_len,wp_owner,wp_stage_len;static uint8_t wp_sig[16];static bool wp_on=false;
static uint16_t wp_call,wp_frame,wp_gf;static uint8_t wp_gfprev;static uint32_t wp_prevkey;
struct WPEvent{uint64_t at;uint32_t key;uint8_t id,slot,op,kind;};static WPEvent wp_events[512];static unsigned wp_nevents;
extern "C" void wp_extra(uint16_t call,uint16_t frame,uint16_t gf){wp_call=call;wp_frame=frame;wp_gf=gf;}
extern "C" unsigned wp_event_count(){return wp_nevents;}
extern "C" uint64_t wp_event(unsigned n,unsigned field){auto&e=wp_events[n];switch(field){case 0:return e.at;case 1:return e.key;case 2:return e.id;case 3:return e.slot;case 4:return e.op;default:return e.kind;}}
struct WPFrame{uint32_t key;uint16_t ret;uint8_t sp;};static WPFrame wp_stack[128];static unsigned wp_depth=0;
extern "C" void wp_config(uint16_t active,uint16_t copy,uint16_t req,uint16_t len,uint16_t owner,uint16_t stage_len,const uint8_t*sig){wp_active=active;wp_copy=copy;wp_req=req;wp_len=len;wp_owner=owner;wp_stage_len=stage_len;memcpy(wp_sig,sig,16);}
extern "C" void wp_begin(){memset(wp_self,0,sizeof(wp_self));memset(wp_inc,0,sizeof(wp_inc));memset(wp_calls,0,sizeof(wp_calls));memset(wp_modules,0,sizeof(wp_modules));memset(wp_dma,0,sizeof(wp_dma));wp_total=0;wp_depth=0;wp_nevents=0;wp_gfprev=255;wp_prevkey=0;wp_on=true;}
extern "C" void wp_end(){wp_on=false;}
extern "C" uint64_t wp_count(){return wp_total;}
extern "C" unsigned wp_depth_left(){return wp_depth;}
extern "C" uint64_t wp_module(unsigned n){return wp_modules[n];}
extern "C" uint64_t wp_io(unsigned direction,unsigned owner,unsigned kind){return wp_dma[direction][owner][kind];}
extern "C" void wp_dump(unsigned type,uint64_t*out){memcpy(out,type==0?wp_self:type==1?wp_inc:wp_calls,sizeof(wp_self));}
static void wp(ZeroPagePeddle*m,const decltype(zeropage_peddle_regs((ZeroPagePeddle*)nullptr))&r){if(!wp_on)return;
 while(wp_depth && r.pc==wp_stack[wp_depth-1].ret && r.sp==wp_stack[wp_depth-1].sp)wp_depth--;
 unsigned tag=0;if(r.pc>=0xa000&&r.pc<0xc000)tag=zeropage_peddle_read(m,wp_active+(r.pc>=0xb000));
 uint32_t k=tag&&tag<=64?65536+(tag-1)*4096+(r.pc&4095):r.pc;
 if(r.pc>=0x5000&&r.pc<0x5000+wp_stage_len){bool stage=true;for(unsigned i=0;i<16;i++)if(zeropage_peddle_read(m,0x5000+i)!=wp_sig[i]){stage=false;break;}if(stage){tag=65;k=65536+64*4096+(r.pc-0x5000);}}
 uint8_t gf=zeropage_peddle_read(m,wp_gf);if(wp_nevents<512){if(wp_gfprev!=255&&gf!=wp_gfprev)wp_events[wp_nevents++]={wp_total,wp_prevkey,wp_gfprev,gf,0,1};if(r.pc==wp_call&&wp_nevents<512)wp_events[wp_nevents++]={wp_total,k,r.a,r.x,zeropage_peddle_read(m,wp_frame),0};}wp_gfprev=gf;wp_prevkey=k;
 wp_self[k]++;wp_total++;bool seen[66]={false};if(tag&&tag<=65)seen[tag]=true;
 for(unsigned i=0;i<wp_depth;i++)if(wp_stack[i].key>=65536)seen[1+(wp_stack[i].key-65536)/4096]=true;
 for(unsigned i=1;i<=65;i++)if(seen[i])wp_modules[i]++;
 if(r.pc==wp_copy && r.a<2){uint8_t logical=zeropage_peddle_read(m,wp_req),owner=zeropage_peddle_read(m,wp_owner+logical);uint32_t n=zeropage_peddle_read(m,wp_len)|(zeropage_peddle_read(m,wp_len+1)<<8);if(!n)n=65536;wp_dma[r.a][owner][0]++;wp_dma[r.a][owner][1]+=n;}
 if(zeropage_peddle_read(m,r.pc)==0x20){if(wp_depth>=128)abort();wp_calls[k]++;wp_stack[wp_depth++]={k,uint16_t(r.pc+3),r.sp};}
 for(unsigned i=0;i<wp_depth;i++)wp_inc[wp_stack[i].key]++;
}
'''
 assert s.count(needle)==1;s=s.replace(needle,extra+needle+'wp(m,r);');p.write_text(s)
 ext='.dylib' if sys.platform=='darwin'else'.so';lib=out/('warm-profile'+ext)
 subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib'if sys.platform=='darwin'else'-shared','-fPIC','-I'+str(observer.geos.grid.VENDOR),str(p),str(ROOT/('build/libse_peddle'+ext)),'-o',str(lib)],check=True)
 dll=C.CDLL(str(lib))
 for name in ('gm_rom','gm_rom_count','gm_profile','gm_metric','gm_run','gm_idle','gm_read','gm_reu','fr_begin','fr_end','fr_mask','fr_bad','fr_writes','pb_config','pb_begin','pb_end','pb_get','pb_fault_get','ob_ring','ob_ring_get'):
  a,b=getattr(old,name),getattr(dll,name);b.argtypes,b.restype=a.argtypes,a.restype
 dll.wp_config.argtypes=[C.c_uint16]*6+[C.c_void_p];dll.wp_count.restype=C.c_uint64;dll.wp_module.argtypes=[C.c_uint];dll.wp_module.restype=C.c_uint64;dll.wp_io.argtypes=[C.c_uint]*3;dll.wp_io.restype=C.c_uint64;dll.wp_dump.argtypes=[C.c_uint,C.c_void_p]
 dll.wp_extra.argtypes=[C.c_uint16]*3;dll.wp_event_count.restype=C.c_uint;dll.wp_event.argtypes=[C.c_uint,C.c_uint];dll.wp_event.restype=C.c_uint64
 return dll
