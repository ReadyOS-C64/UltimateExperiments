"""Read-only instruction observer derived from the existing cost profilers."""
from pathlib import Path
import ctypes as C,subprocess,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_observer as observer
ORIGINAL=observer.runner

def build(out):
 old=ORIGINAL(out);p=out/'runner.cpp';source=p.read_text()
 needle='static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);'
 assert source.count(needle)==1
 extra=r'''
#include <cstdlib>
static bool hp_on=false;static uint16_t hp_active,hp_frame,hp_seq,hp_prior,hp_point[8],hp_crc_return[8];
static unsigned hp_returns,hp_depth;static uint8_t hp_gtype,hp_code;
static uint64_t hp_total,hp_first,hp_self[68],hp_first_self[68],hp_calls[65],hp_ops[65][256],hp_crc,hp_crcs,hp_crc_start;
static bool hp_crc_live=false;
struct HPFrame{unsigned group;uint64_t start,payload,end,children;};static HPFrame hp_stack[64];
static uint64_t hp_groups[128][5];
extern "C" void hp_config(uint16_t active,uint16_t frame,uint16_t seq,const uint16_t*points,unsigned n,const uint16_t*returns,uint8_t gtype,uint8_t code){hp_active=active;hp_frame=frame;hp_seq=seq;memcpy(hp_point,points,sizeof(hp_point));hp_returns=n;memcpy(hp_crc_return,returns,n*2);hp_gtype=gtype;hp_code=code;}
extern "C" void hp_begin(uint16_t seq){hp_prior=seq;hp_total=hp_first=hp_crc=hp_crcs=hp_depth=0;hp_crc_live=false;memset(hp_self,0,sizeof(hp_self));memset(hp_first_self,0,sizeof(hp_first_self));memset(hp_calls,0,sizeof(hp_calls));memset(hp_ops,0,sizeof(hp_ops));memset(hp_groups,0,sizeof(hp_groups));hp_on=true;}
extern "C" void hp_end(){hp_on=false;}
extern "C" uint64_t hp_get(unsigned field,unsigned i){if(field==0)return i==0?hp_total:i==1?hp_first:i==2?hp_crc:i==3?hp_crcs:hp_depth;if(field==1)return hp_self[i];if(field==2)return hp_first_self[i];if(field==3)return hp_calls[i];return 0;}
extern "C" uint64_t hp_op(unsigned tag,unsigned op){return hp_ops[tag][op];}
extern "C" uint64_t hp_group(unsigned group,unsigned field){return hp_groups[group][field];}
static void hp_step(ZeroPagePeddle*m,const decltype(zeropage_peddle_regs((ZeroPagePeddle*)nullptr))&r){if(!hp_on)return;
 uint16_t seq=zeropage_peddle_read(m,hp_seq)|(zeropage_peddle_read(m,hp_seq+1)<<8);
 if(seq!=hp_prior){if(!hp_first){hp_first=hp_total;memcpy(hp_first_self,hp_self,sizeof(hp_self));}hp_prior=seq;}
 if(r.pc==hp_point[0]){if(hp_depth>=64 || r.a>=64 || r.x>1)abort();hp_stack[hp_depth++]={unsigned(r.x)*64+r.a,hp_total,0,0,0};}
 if(r.pc==hp_point[1]){if(!hp_depth)abort();hp_stack[hp_depth-1].payload=hp_total;}
 if(r.pc==hp_point[2]){if(!hp_depth)abort();hp_stack[hp_depth-1].end=hp_total;}
 if(r.pc==hp_point[3]){if(!hp_depth)abort();auto q=hp_stack[--hp_depth];auto g=hp_groups[q.group];uint64_t total=hp_total-q.start;g[0]++;g[1]+=total;g[2]+=q.payload-q.start;g[3]+=q.end-q.payload;g[4]+=q.end-q.payload-q.children;if(hp_depth)hp_stack[hp_depth-1].children+=total;}
 if(r.pc==hp_point[4]){hp_crcs++;hp_crc_live=true;hp_crc_start=hp_total;}
 if(hp_crc_live)for(unsigned i=0;i<hp_returns;i++)if(r.pc==hp_crc_return[i]){hp_crc+=hp_total-hp_crc_start;hp_crc_live=false;break;}
 unsigned tag=0;if(r.pc>=0xa000 && r.pc<0xc000)tag=zeropage_peddle_read(m,hp_active+(r.pc>=0xb000));
 if(tag>64)abort();unsigned category=tag;
 if(r.pc>=0x5000 && r.pc<0x6000){auto active=zeropage_peddle_read(m,hp_active);auto stamp=zeropage_peddle_read(m,0xcbd5);if(active==hp_gtype && stamp==0x42)category=65;else if(active==hp_code && stamp==0x41)category=66;}
 if(tag && (r.pc==0xa010 || r.pc==0xb010)){hp_calls[tag]++;hp_ops[tag][zeropage_peddle_read(m,hp_frame)]++;}
 hp_self[category]++;hp_total++;
}
'''
 source=source.replace(needle,extra+needle+'hp_step(m,r);');p.write_text(source)
 ext='.dylib'if sys.platform=='darwin'else'.so';path=out/('hotpath-runner'+ext)
 subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib'if sys.platform=='darwin'else'-shared','-fPIC','-I'+str(observer.geos.grid.VENDOR),p,ROOT/('build/libse_peddle'+ext),'-o',path],check=True)
 dll=C.CDLL(str(path))
 for name in ('gm_rom','gm_rom_count','gm_profile','gm_metric','gm_run','gm_idle','gm_read','gm_reu','fr_begin','fr_end','fr_mask','fr_bad','fr_writes','pb_config','pb_begin','pb_end','pb_get','pb_fault_get','ob_ring','ob_ring_get'):
  a,b=getattr(old,name),getattr(dll,name);b.argtypes,b.restype=a.argtypes,a.restype
 dll.hp_config.argtypes=[C.c_uint16,C.c_uint16,C.c_uint16,C.c_void_p,C.c_uint,C.c_void_p,C.c_uint8,C.c_uint8]
 dll.hp_begin.argtypes=[C.c_uint16];dll.hp_get.argtypes=[C.c_uint,C.c_uint];dll.hp_get.restype=C.c_uint64
 dll.hp_op.argtypes=[C.c_uint,C.c_uint];dll.hp_op.restype=C.c_uint64
 dll.hp_group.argtypes=[C.c_uint,C.c_uint];dll.hp_group.restype=C.c_uint64
 return dll
