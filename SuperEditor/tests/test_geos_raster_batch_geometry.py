"""Pure actual-code range constructor seam; component gate supplies API authority proof."""
from pathlib import Path
from datetime import datetime,timezone
import ctypes as C,hashlib,json,subprocess,sys
import test_geos_raster_batch_probe as batch
import test_geos_literal_byte_candidate as proof
F=0x8880;P=F+658;ROOT=batch.ROOT

def run(out,base):
 d,src,s,ls,raw,image,mods=batch.prepare(out,base,'candidate');f=proof.Fixture(d,base,src,s,ls,raw)
 # Begin/stop are derived from byte-identical assembled scalar code. No host
 # seeded semantic result, font authority, or application admission is claimed.
 needle=bytes([0xAD,(F+16)&255,(F+16)>>8,0x18,0x69,7,0xAA]);assert raw.count(needle)==1;start=0xA000+raw.index(needle)
 endneedle=bytes([0x8D,(P+13)&255,(P+13)>>8,0xCD,(P+11)&255,(P+11)>>8]);at=raw.index(endneedle,start-0xA000);stop=0xA000+at+3
 cpp=out/'geometry.cpp';cpp.write_text(r'''#include "zeropage_peddle.h"
extern "C" unsigned geo_all(ZeroPagePeddle*m,unsigned start,unsigned stop,unsigned f,unsigned p){
 unsigned cases=0;
 for(unsigned l=0;l<=320;l++)for(unsigned r=l;r<=320;r++){
  zeropage_peddle_write(m,f+14,l);zeropage_peddle_write(m,f+15,l>>8);zeropage_peddle_write(m,f+16,r);zeropage_peddle_write(m,f+17,r>>8);
  zeropage_peddle_set_pc(m,start);zeropage_peddle_set_p(m,0x24);
  unsigned n=0;while(zeropage_peddle_regs(m).pc!=stop){
   auto pc=zeropage_peddle_regs(m).pc;auto op=zeropage_peddle_read(m,pc);
   if(op!=0xad&&op!=0x18&&op!=0x69&&op!=0xaa&&op!=0x4a&&op!=0x8a&&op!=0x6a&&op!=0x8d)return 5;
   if(op==0x8d){unsigned a=zeropage_peddle_read(m,pc+1)|(zeropage_peddle_read(m,pc+2)<<8);if(a!=p+11&&a!=p+13)return 1;}
   zeropage_peddle_step_instruction(m);if(++n>64)return 2;
  }
  unsigned first=zeropage_peddle_read(m,p+13),end=zeropage_peddle_read(m,p+11);
  if(first!=l/8||end!=(r+7)/8||end>40||first>end)return 3;
  for(unsigned t=0;t<40;t++)if((t>=first&&t<end)!=(t*8<r&&(t+1)*8>l))return 4;
  cases++;
 }return cases;
}''')
 ext='.dylib'if sys.platform=='darwin'else'.so';lib=out/('geometry'+ext);subprocess.run(['clang++','-std=c++20','-O2','-dynamiclib'if sys.platform=='darwin'else'-shared','-fPIC','-I'+str(proof.profile.VENDOR),str(cpp),str(ROOT/('build/libse_peddle'+ext)),'-o',str(lib)],check=True)
 dll=C.CDLL(str(lib));dll.geo_all.argtypes=[C.c_void_p]+[C.c_uint]*4;dll.geo_all.restype=C.c_uint
 try:
  before=f.read(0,65536);reu=f.reu();n=dll.geo_all(f.m.handle,start,stop,F,P);assert n==51681,n;after=f.read(0,65536);wanted=bytearray(before)
  for a,w in [(F+14,4),(P+11,1),(P+13,1)]:wanted[a:a+w]=after[a:a+w]
  assert after==wanted and f.reu()==reu
  result=dict(status='PASS',cases=n,tile_memberships=n*40,whole_RAM_terminal_guard=65536,whole_REU_guard=16777216,runtime_store_targets=[hex(P+11),hex(P+13)],scope='Pure actual linear constructor seam, validated scalar0..320 inputs supplied by host; application authority/clipping/attributes proven separately by actual R21 component/public gates. All stores before stop checked to two exact scratch bytes.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
 finally:f.close()
if __name__=='__main__':
 p=__import__('argparse').ArgumentParser();p.add_argument('--fixture',type=Path,default=batch.BASE);a=p.parse_args();out=ROOT/'build/geos-raster-batch-geometry'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)
