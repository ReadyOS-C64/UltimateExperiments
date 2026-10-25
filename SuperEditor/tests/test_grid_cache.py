"""Private exact-input REU row-cache proof. Actual provider/DMA, no editor build.

A clean result must equal a successfully committed240-byte packet in the same
width/context. Every input byte is independently changed, including unused60
suffixes. Invalid dimensions do not write; service faults are explicitly injected.
"""
from pathlib import Path
from datetime import datetime,timezone
import ctypes as C,hashlib,json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine,VENDOR
from test_bitmap_cells import labels
from test_narrow_rows import oracle
PACKET=0x88C4;TEMP=0x8A44;SIZE=240

def run(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True,capture_output=True)
def build(out):
 (out/'config.cfg').write_text('MEMORY { C:file=%O,start=$1000,size=$1800; B:file="",start=$3000,size=$1000; } SEGMENTS { CODE:load=C,type=ro; RODATA:load=C,type=ro; BSS:load=B,type=bss,define=yes; }')
 (out/'banks.s').write_text('.export se_reu_banks\n.segment "BSS"\nse_reu_banks: .res 2\n')
 objs=[]
 for n,p in [('cache','src/render/grid/cache.s'),('state','src/render/grid/cache-state.s'),('provider','src/reu/provider.s'),('dma','src/reu/dma.s'),('banks',out/'banks.s')]:
  obj=out/f'{n}.o';run('ca65','-g','-I','src','-o',obj,p);objs.append(obj)
 run('ld65','-C',out/'config.cfg','-o',out/'cache.bin','-m',out/'cache.map','-Ln',out/'cache.lbl',*objs)
 # Both supported compilation profiles must link to identical cache bytes.
 s=labels(out/'cache.lbl');names=[n for n in s if n.startswith('se_reu') or n.startswith('se_gc_')]
 (out/'editor-api.inc').write_text('\n'.join(f'{n} = ${s[n]:04X}' for n in names)+'\n')
 run('ca65','-g','-D','EDITOR_OVERLAY=1','-I',out,'-I','src','-o',out/'overlay.o','src/render/grid/cache.s')
 (out/'overlay.cfg').write_text('MEMORY { C:file=%O,start=$1000,size=$1000; } SEGMENTS { CODE:load=C,type=ro; RODATA:load=C,type=ro; }')
 run('ld65','-C',out/'overlay.cfg','-o',out/'overlay.bin','-m',out/'overlay.map',out/'overlay.o')
 (out/'aliases.s').write_text('\n'.join(f'.export {n}\n{n} = ${s[n]:04X}' for n in names)+'\n')
 run('ca65','-o',out/'aliases.o',out/'aliases.s')
 run('ld65','-C',out/'overlay.cfg','-o',out/'standalone-only.bin',out/'cache.o',out/'aliases.o')
 code=(out/'overlay.bin').read_bytes();assert (out/'standalone-only.bin').read_bytes()==code;assert len(code)<=650
 return s,len(code)

class Fixture:
 def __init__(self,out,s):
  self.s=s;self.m=Machine();self.calls=0;self.hits=0;self.dirty=0;self.peak=0
  cpp=out/'runner.cpp';cpp.write_text('''#include "zeropage_peddle.h"
extern "C" uint64_t run_cache(ZeroPagePeddle*m){auto b=zeropage_peddle_regs(m).instructions;for(int i=0;i<20000;i++){if(zeropage_peddle_regs(m).pc==0x2ff)return zeropage_peddle_regs(m).instructions-b;zeropage_peddle_step_instruction(m);}return 0;}
extern "C" void read_cache(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read(m,a+i);}
extern "C" void reu_cache(ZeroPagePeddle*m,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read_reu(m,i);}
extern "C" void seed_cache(ZeroPagePeddle*m){for(int bank=0;bank<256;bank++){for(int i=2;i<10;i++)zeropage_peddle_write(m,0xdf00+i,0);zeropage_peddle_write(m,0xdf06,bank);zeropage_peddle_write(m,0xdf0a,0);zeropage_peddle_write(m,0xdf01,0x90);}}
''')
  ext='.dylib' if sys.platform=='darwin' else '.so';lib=out/('runner'+ext);run('clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),cpp,ROOT/('build/libse_peddle'+ext),'-o',lib)
  self.r=C.CDLL(str(lib));self.r.run_cache.argtypes=[C.c_void_p];self.r.run_cache.restype=C.c_uint64
  self.r.read_cache.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];self.r.reu_cache.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p];self.r.seed_cache.argtypes=[C.c_void_p]
  self.m.load(0,bytes((i*73+(i>>8)*19+31)&255 for i in range(65536)));self.r.seed_cache(self.m.handle);self.expected_reu=bytearray(self.reu());self.m.load(0x1000,(out/'cache.bin').read_bytes())
  self.m.load(0x3000,bytes(0x1000));self.put('se_reu_banks',256,2);self.call('se_reu_provider_init',guard=False)
  self.allowed=[(s['se_gc_handle'],s['se_gc_handle']+9),(s['se_reu_c64'],s['dma_physical']+1),(0x100,0x200),(0xDF01,0xDF0B)]
 def read(self,a,n):
  b=C.create_string_buffer(n);self.r.read_cache(self.m.handle,a,n,b);return b.raw
 def reu(self):
  b=C.create_string_buffer(16*1024*1024);self.r.reu_cache(self.m.handle,len(b),b);return b.raw
 def get(self,n,w=1):return int.from_bytes(self.read(self.s[n],w),'little')
 def put(self,n,v,w=1):self.m.load(self.s[n],v.to_bytes(w,'little'))
 def call(self,n,a=0,x=0,guard=True,temp=False):
  before=self.read(0,65536) if guard else None
  for k,v in [('pc',self.s[n]),('sp',0xFD),('p',0x24),('a',a),('x',x),('y',0)]:getattr(self.m.lib,'zeropage_peddle_set_'+k)(self.m.handle,v)
  self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);used=self.r.run_cache(self.m.handle);assert used,('nonreturn',n,hex(self.m.regs().pc));self.calls+=1;self.peak=max(self.peak,used);r=self.m.regs()
  if guard:
   after=self.read(0,65536);want=bytearray(before)
   extra=[]
   if n=='se_reu_provider_init':extra=[(self.s['se_reu_map'],self.s['provider_owner']+1)]
   elif n=='se_grid_cache_begin':
    # Exactly one allocator-selected slot, or no allocation at all.
    extra=[(self.s['provider_owner'],self.s['provider_owner']+1)]
    h=after[self.s['se_gc_handle']]
    if h and h!=before[self.s['se_gc_handle']]:
     ph=after[self.s['se_reu_map']+h]
     extra += [(self.s['se_reu_map']+h,self.s['se_reu_map']+h+1),(self.s['se_reu_logical_owner']+h,self.s['se_reu_logical_owner']+h+1),(self.s['se_reu_physical_owner']+ph,self.s['se_reu_physical_owner']+ph+1)]
   for lo,hi in self.allowed+extra+([(TEMP,TEMP+SIZE)] if temp else []):want[lo:hi]=after[lo:hi]
   assert after==want,('RAM/shim/source/output guard',n,next((hex(i),b,c) for i,(b,c) in enumerate(zip(after,want)) if b!=c))
  return r
 def begin(self,width=80,ui=0):
  r=self.call('se_grid_cache_begin',width,ui);assert not r.p&1 and r.a==0
 def row(self,row,packet,dirty):
  self.m.load(PACKET,packet);r=self.call('se_grid_cache_row',row,temp=True);assert not r.p&1 and r.a==dirty,('row',row,dirty,r.a,r.p)
  if dirty:self.dirty+=1
  else:
   self.hits+=1
   assert self.read(TEMP,SIZE)==packet,'false clean result/cache packet mismatch'
 def commit(self,row,packet,success=True):
  self.m.load(PACKET,packet);r=self.call('se_grid_cache_commit',row);assert not r.p&1 and r.a==0
  if success and self.get('se_gc_handle'):
   physical=self.m.read(self.s['se_reu_map']+self.get('se_gc_handle'));at=physical*65536+(row-2)*SIZE;self.expected_reu[at:at+SIZE]=packet
 def check_reu(self):assert self.reu()==self.expected_reu,'foreign/source/history/clipboard REU or cache extent changed'
 def close(self):self.m.close()

def main():
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'build/grid-cache'/stamp;out.mkdir(parents=True);s,code=build(out);f=Fixture(out,s);cases=[];mutations=0;pixels=0
 palette=bytes([1,3,7,10,14,1,1,7,13,5,15,7,3,1]);packets={row:bytes((row*31+i*73)&255 for i in range(80))+bytes((row+i)%14 for i in range(80))+bytes((row+i)%8 for i in range(80)) for row in range(2,24)}
 try:
  assert s['se_gc_current_ui']+1-s['se_gc_handle']==9
  # Allocate a high logical handle mapped noncontiguously, never bank=handle.
  for i in range(1,200):f.m.write(s['se_reu_logical_owner']+i,4)
  for i in range(1,32):f.m.write(s['se_reu_physical_owner']+i,4)
  f.begin();assert f.get('se_gc_handle')==200 and f.m.read(s['se_reu_map']+200)==32
  for width in [80,60]:
   f.begin(width)
   font=(ROOT/f'assets/fonts/generated/narrow{4 if width==80 else 5}.bin').read_bytes()
   for row,p in packets.items():
    f.row(row,p,1);f.commit(row,p);f.row(row,p,0)
    # Exact packet identity implies exact independent glyph/attribute output.
    first=oracle(width,p[:width],[v%14 for v in p[80:80+width]],p[160:160+width],palette,6,0,font)
    cached=f.read(TEMP,SIZE);second=oracle(width,cached[:width],cached[80:80+width],cached[160:160+width],palette,6,0,font);assert first==second;pixels+=2560
   f.call('se_grid_cache_finish');f.check_reu()
   for row,p in packets.items():
    for i in range(SIZE):
     q=bytearray(p);q[i]^=1
     f.row(row,q,1)
     # Aborted/partial paint leaves old packet dirty until successfully repaired.
     f.row(row,p,1);f.commit(row,p);f.row(row,p,0);mutations+=1
   f.check_reu();cases.append(f'all22rows/every240byte/{width}')
  # No publication before successful paint; and a failed stash never publishes.
  p=packets[2];q=bytes(v^255 for v in p);f.row(2,q,1);f.row(2,p,1);f.commit(2,p);f.row(2,p,0)
  dma=s['se_reu_copy'];saved=f.read(dma,4);f.m.load(dma,b'\xA9\x04\x38\x60')
  f.row(2,p,1);f.commit(2,q,False);f.m.load(dma,saved);f.row(2,p,1);f.commit(2,p);f.row(2,p,0);f.check_reu();cases.append('injected-fetch-and-stash-failure-no-publication')
  # Popup active, closed, and interrupted: all rows repaint in each affected frame.
  for current,finish in [(1,True),(1,False),(0,True)]:
   f.begin(60,current)
   for row,p in packets.items():f.row(row,p,1);f.commit(row,p)
   if finish:f.call('se_grid_cache_finish')
  f.begin(60,0)
  for row,p in packets.items():f.row(row,p,0)
  f.call('se_grid_cache_finish');f.check_reu();cases.append('current-previous-unfinished-popup-repair')
  f.call('se_grid_cache_invalidate');f.begin(60)
  for row,p in packets.items():f.row(row,p,1);f.commit(row,p)
  f.check_reu();cases.append('mode80-40-80-explicit-invalidation')
  # Invalid dimensions must be wholly write-free, including request/state/temp.
  invalid=0
  for name,values in [('se_grid_cache_begin',[v for v in range(256) if v not in [60,80]]),('se_grid_cache_row',[v for v in range(256) if not 2<=v<=23]),('se_grid_cache_commit',[v for v in range(256) if not 2<=v<=23])]:
   for v in values:
    before=f.read(0,65536);r=f.call(name,v);after=f.read(0,65536);want=bytearray(before);want[0x100:0x200]=after[0x100:0x200];assert r.p&1 and r.a==0x7B and after==want,(name,v);invalid+=1
  f.check_reu();cases.append('invalid-dimensions-before-all-writes')
  # Owner, mapping, epoch and retirement faults cannot read/stash another bank.
  logical=f.get('se_gc_handle');physical=f.m.read(s['se_reu_map']+logical)
  for n,at,value in [('logical-owner',s['se_reu_logical_owner']+logical,5),('physical-owner',s['se_reu_physical_owner']+physical,4),('physical-zero',s['se_reu_map']+logical,0),('epoch',s['se_gc_epoch'],f.get('se_gc_epoch')^1),('retired',s['se_reu_retired'],1),('zero-epoch',s['se_reu_epoch'],0)]:
   frame=f.read(s['se_gc_handle'],9);old=f.m.read(at);f.m.write(at,value);f.row(2,p,1);f.commit(2,q,False);assert not f.get('se_gc_handle');f.check_reu();f.m.write(at,old);f.m.load(s['se_gc_handle'],frame);cases.append(n+'-safe-dirty')
  # Exhaustion falls back without touching REU or unrelated live owners.
  state=f.read(s['se_gc_handle'],9);tables=f.read(s['se_reu_map'],768);f.put('se_gc_handle',0)
  f.m.load(s['se_reu_physical_owner'],bytes([4])*256);f.begin();assert f.get('se_gc_handle')==0
  f.row(2,p,1);f.commit(2,q,False);f.check_reu();f.m.load(s['se_reu_map'],tables);f.m.load(s['se_gc_handle'],state);cases.append('allocation-exhaustion-render-all')
  # Provider reset invalidates token; no stale free/reads, then lazy reacquire.
  f.call('se_reu_provider_init');f.row(2,p,1);f.commit(2,q,False);f.check_reu();f.begin();assert f.get('se_gc_epoch',2)==f.get('se_reu_epoch',2)
  f.row(2,q,1);f.commit(2,q);f.row(2,q,0);f.check_reu();cases.append('actual-provider-reset-reallocation')
  result=dict(status='passed',code_and_constants_bytes=code,resident_state_bytes=9,new_ZP=0,packet_bytes=240,rows=22,comparison_buffer=[TEMP,TEMP+SIZE],independent_single_byte_mutations=mutations,invalid_write_free_calls=invalid,cache_hits=f.hits,dirty_results=f.dirty,total_CPU_calls=f.calls,peak_call_instructions=f.peak,oracle_pixels=pixels,full_RAM_guards=65536,whole_REU_oracle_bytes=16777216,cases=cases,fit=dict(existing_C16=3241,cache=code,combined=3241+code,remaining=4096-3241-code),limits='Private emitted-code CPU proof, actual allocator/checked DMA. Fetch/stash failures explicitly injected; no integrated editor/native/performance claim. Cache may alter only its owned FE bank5280 bytes. Caller must invalidate every output/font/palette/mode change and COMMIT only after successful leaf.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 except BaseException as e:(out/'failure.json').write_text(json.dumps(dict(error=repr(e)),indent=2)+'\n');(out/'failure-c64.bin').write_bytes(f.read(0,65536));raise
 finally:f.close()
 evidence=ROOT/'agentsworking/evidence/M6'/(stamp+'-grid-cache');evidence.mkdir(parents=True);shutil.copytree(out,evidence/'build')
 for name in ['src/render/grid/cache.s','src/render/grid/cache-state.s','src/render/grid/cache.inc','tests/test_grid_cache.py','src/reu/provider.s','src/reu/dma.s','src/render/grid/api.inc','tests/test_narrow_rows.py','tools/peddle.py']:
  target=evidence/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
 print('EVIDENCE',evidence)
if __name__=='__main__':main()
