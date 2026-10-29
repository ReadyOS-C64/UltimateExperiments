"""Read-only nested R63 operation/region instruction attribution."""
from pathlib import Path
import ctypes as C,importlib.util,subprocess,sys
ROOT=Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location('cv_reflow_runner',ROOT/'src/render/geos/reflow-profile-probe/runner.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

def build(out):
 old=base.build(out);p=out/'runner.cpp';s=p.read_text()
 needle='static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);';assert s.count(needle)==1
 extra=r'''
static uint16_t loan_a[16];static bool loan_on=false;static uint32_t loan_count=0,loan_bad=0;
extern "C" void loan_config(const uint16_t*p){memcpy(loan_a,p,sizeof(loan_a));loan_count=loan_bad=0;loan_on=true;}
extern "C" uint32_t loan_get(unsigned i){return i?loan_bad:loan_count;}
static void loan(ZeroPagePeddle*m,uint16_t pc,uint8_t a){if(!loan_on||pc!=loan_a[0]||a!=1)return;
 auto b=[&](unsigned i){return zeropage_peddle_read(m,loan_a[i]);};
 if(b(1)!=0||zeropage_peddle_read(m,loan_a[1]+1)!=0x8d||b(2)!=0x4a||zeropage_peddle_read(m,loan_a[2]+1)!=3||b(3)!=b(4))return;
 loan_count++;for(unsigned i=5;i<13;i++)if(b(i))loan_bad|=1u<<(i-5);if(b(13)!=4)loan_bad|=256;if(b(14)&8)loan_bad|=512;if(b(15))loan_bad|=1024;
}
static bool cv_on=false,cv_live=false;static unsigned cv_op,cv_region,cv_depth,cv_n;static uint16_t cv_active,cv_frame,cv_points[64];static uint8_t cv_stack[64];static uint64_t cv_counts[6][64];
extern "C" void cv_config(uint16_t active,uint16_t frame,unsigned n,const uint16_t*p){cv_active=active;cv_frame=frame;cv_n=n;memcpy(cv_points,p,n*2);}
extern "C" void cv_begin(){memset(cv_counts,0,sizeof(cv_counts));cv_depth=0;cv_live=false;cv_on=true;}
extern "C" void cv_end(){cv_on=false;}
extern "C" uint64_t cv_get(unsigned op,unsigned region){return cv_counts[op][region];}
static void cv(ZeroPagePeddle*m,uint16_t pc){if(!cv_on)return;
 if(pc==0xa010&&zeropage_peddle_read(m,cv_active)==63){cv_op=zeropage_peddle_read(m,cv_frame);if(cv_op>=6)abort();cv_live=true;cv_depth=0;cv_region=0;}
 if(!cv_live)return;
 if(pc<0xa000||pc>=0xc000||zeropage_peddle_read(m,cv_active+(pc>=0xb000))==63)for(unsigned i=0;i<cv_n;i++)if(pc==cv_points[i]){cv_region=i+1;break;}
 cv_counts[cv_op][cv_region]++;
 auto op=zeropage_peddle_read(m,pc);if(op==0x20){if(cv_depth>=64)abort();cv_stack[cv_depth++]=cv_region;}
 if(op==0x60){if(cv_depth)cv_region=cv_stack[--cv_depth];else cv_live=false;}
}
'''
 s=s.replace(needle,extra+needle+'loan(m,r.pc,r.a);cv(m,r.pc);');p.write_text(s)
 ext='.dylib'if sys.platform=='darwin'else'.so';target=out/('convergence-runner'+ext)
 subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib'if sys.platform=='darwin'else'-shared','-fPIC','-I'+str(base.hot.observer.geos.grid.VENDOR),p,ROOT/('build/libse_peddle'+ext),'-o',target],check=True)
 dll=C.CDLL(str(target))
 for n in ('gm_rom','gm_rom_count','gm_profile','gm_metric','gm_run','gm_idle','gm_read','gm_reu','fr_begin','fr_end','fr_mask','fr_bad','fr_writes','pb_config','pb_begin','pb_end','pb_get','pb_fault_get','ob_ring','ob_ring_get','hp_config','hp_begin','hp_get','hp_op','hp_group','rp_begin','rp_get'):
  a,b=getattr(old,n),getattr(dll,n);b.argtypes,b.restype=a.argtypes,a.restype
 dll.cv_config.argtypes=[C.c_uint16,C.c_uint16,C.c_uint,C.c_void_p];dll.cv_get.argtypes=[C.c_uint,C.c_uint];dll.cv_get.restype=C.c_uint64
 dll.loan_config.argtypes=[C.c_void_p];dll.loan_get.argtypes=[C.c_uint];dll.loan_get.restype=C.c_uint32
 return dll
