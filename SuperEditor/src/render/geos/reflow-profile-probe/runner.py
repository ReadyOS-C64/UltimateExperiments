"""Read-only public instruction/overlay/DMA observer; adds checked R-slot PCs."""
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[4]
p=ROOT/'src/cache/hotpath-profile-probe/runner.py'
spec=importlib.util.spec_from_file_location('reflow_hot',p);hot=importlib.util.module_from_spec(spec);spec.loader.exec_module(hot)
ORIGINAL=hot.ORIGINAL

def build(out):
 def original_with_r_pc(out):
  # Add only an observer predicate before the existing final hotpath compile.
  old=ORIGINAL(out);p=out/'runner.cpp';s=p.read_text();needle='if(pb_kind[i]==2 && zeropage_peddle_read(m,pb_active+1)!=pb_tag[i])continue;'
  assert s.count(needle)==1;s=s.replace(needle,needle+'\n if(pb_kind[i]==4 && zeropage_peddle_read(m,pb_active)!=pb_tag[i])continue;')
  extra=r"""
static bool rp_on=false;static uint16_t rp_active;static uint8_t rp_tag;static uint64_t rp_rows[25],rp_parts[4];
extern "C" void rp_begin(uint16_t active,uint8_t tag){rp_active=active;rp_tag=tag;memset(rp_rows,0,sizeof(rp_rows));memset(rp_parts,0,sizeof(rp_parts));rp_on=true;}
extern "C" void rp_end(){rp_on=false;}
extern "C" uint64_t rp_get(unsigned part,unsigned i){return part?rp_parts[i]:rp_rows[i];}
static void rp(ZeroPagePeddle*m,uint16_t pc){if(!rp_on||pc<0xa000||pc>=0xb000||zeropage_peddle_read(m,rp_active)!=rp_tag)return;auto row=zeropage_peddle_read(m,0x8880);if(row<25)rp_rows[row]++;unsigned part=pc<0xa035?0:pc>=0xa83d&&pc<0xa93d?2:pc>=0xa93d&&pc<0xab57?3:1;rp_parts[part]++;}
"""
  needle='static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);';assert s.count(needle)==1;s=s.replace(needle,extra+needle+'rp(m,r.pc);');p.write_text(s);return old
 old=hot.ORIGINAL;hot.ORIGINAL=original_with_r_pc
 try:
  dll=hot.build(out)
  import ctypes as C
  dll.rp_begin.argtypes=[C.c_uint16,C.c_uint8];dll.rp_get.argtypes=[C.c_uint,C.c_uint];dll.rp_get.restype=C.c_uint64
  return dll
 finally:hot.ORIGINAL=old
