"""Undeployed INLINE query budget + actual unmodified event-paint fragment.

The image is deliberately linked at6000 in an8KiB private probe, NOT wrapped
as a legal C35 asset. CPU stops at the real ACK boundary before source service;
no host-created packet is represented as a successful checked cache result.
"""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib,re,subprocess,ctypes as CT
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_query as query
from peddle import Machine,VENDOR
command=query.command
S=0x8880;R=S+161;H=R+161;P=H+21;IO=0x8ec0

def build(out):
 out.mkdir();base=query.BASE;report=json.loads((base/'build/editor-report.json').read_text());digest=report['resident_binding']['digest'];objects=[];sizes={}
 (out/'editor-api.inc').write_text('.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 for name in ('inline-entry','query','source','records'):
  obj=out/(name+'.o');command('ca65','-g','-I',out,'-I','src','-D','BCQ_EDITOR_ACTIVE=1','-D','BCQ_SELECTOR_OWNS_OWNER=1','-o',obj,ROOT/'src/cache/query'/('probes/inline-entry.s'if name=='inline-entry'else name+'.s'));objects.append(obj)
 for name in('core','open','page'):
  obj=out/(name+'.o');command('ca65','-g','-I','src','-D','BCA_READONLY_OPEN=1','-o',obj,ROOT/'src/cache/arena'/(name+'.s'));objects.append(obj)
 for obj in objects:sizes[obj.stem]=sum(int(v)for v in re.findall(r'Size:\s+(\d+)',subprocess.check_output(['od65','--dump-segments',str(obj)],text=True)))
 seam={'se_bc_arena':0x9fb5,'se_bc_ticket':0x9fba,'se_bc_incarnation':0x9fbe,'se_bc_flags':0x9fc2,'se_bc_head':0x9fc3,'se_bc_tail':0x9fc4,'se_bc_count':0x9fc5,'se_bc_ring':0x9d85};(out/'state.s').write_text('\n'.join(f'.export {n}: absolute\n{n}=${v:04X}'for n,v in seam.items())+'\n');command('ca65','-o',out/'state.o',out/'state.s');objects.append(out/'state.o')
 command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects);command('ca65','-o',out/'aliases.o',out/'aliases.s');objects.append(out/'aliases.o')
 (out/'budget.cfg').write_text('MEMORY { C:file=%O,start=$6000,size=$2000; } SEGMENTS { CODE:load=C,type=ro; RODATA:load=C,type=ro; }');command('ld65','-C',out/'budget.cfg','-o',out/'budget.bin','-Ln',out/'budget.lbl','-m',out/'budget.map',*objects)
 return (out/'budget.bin').read_bytes(),query.labels(out/'budget.lbl'),sizes

def run(out):
 raw,s,sizes=build(out/'link');assert len(raw)>4096 # exactfailedfit is deliberate
 # Reuse releasedqueryprobe's symbol-only CPU inspector, not its source mocks.
 ext='.dylib'if sys.platform=='darwin'else'.so'
 (out/'paint.cpp').write_text('#include "zeropage_peddle.h"\n#include<cstdint>\nextern "C" uint64_t paint(ZeroPagePeddle*m,unsigned stop){auto b=zeropage_peddle_regs(m).instructions;for(unsigned i=0;i<50000;i++){auto r=zeropage_peddle_regs(m);if(r.pc==stop||r.pc==0x2ff)return r.instructions-b;zeropage_peddle_step_instruction(m);}return 0;}extern "C" void inspect(ZeroPagePeddle*m,unsigned char*p,int reu){unsigned n=reu?16777216:65536;for(unsigned i=0;i<n;i++)p[i]=reu?zeropage_peddle_read_reu(m,i):zeropage_peddle_read(m,i);}')
 command('clang++','-O2','-std=c++20','-dynamiclib'if sys.platform=='darwin'else'-shared','-fPIC','-I'+str(VENDOR),out/'paint.cpp',ROOT/('build/libse_peddle'+ext),'-o',out/('paint'+ext));lib=CT.CDLL(str(out/('paint'+ext)));lib.paint.argtypes=[CT.c_void_p,CT.c_uint];lib.paint.restype=CT.c_uint64;lib.inspect.argtypes=[CT.c_void_p,CT.c_void_p,CT.c_int]
 m=Machine();m.load(0,bytes((i*29+7)&255 for i in range(65536)));m.load(0x6000,raw)
 def read(a,n):return bytes(m.read(a+i)for i in range(n))
 def snap(reu=False):
  buf=CT.create_string_buffer(16777216 if reu else 65536);lib.inspect(m.handle,buf,int(reu));return buf.raw
 before_reu=snap(True);vectors=0;calls=0;instructions=0
 try:
  for count in (0,1,7,8,31,32,33,127,128,160,161):
   for first in (0,1,65535,65536):
    for kind,style,width in [(1,1,1),(1,2,2),(1,3,3),(1,4,2),(2,0,1)]:
     for displacement in (-8,0,3,150):
      opened=max(0,first+displacement);closed=opened+width if kind==2 else opened+width+11
      m.load(S,bytes(161));m.load(R,bytes([7])*161);m.load(H,bytes(21));m.write(P+4,count)
      initial=bytearray(IO+19-IO);initial[0:3]=bytes([kind,style,width]);initial[3:6]=opened.to_bytes(3,'little');initial[6:9]=closed.to_bytes(3,'little');initial[10:13]=(opened+width).to_bytes(3,'little');initial[13:16]=(closed+width).to_bytes(3,'little');initial[16:19]=first.to_bytes(3,'little');m.load(IO,initial);m.write(P+22,0);m.write(P+25,128 if style==4 else((style&2)>>1)|((style&1)<<1))
      start=snap()
      for _ in range(10):
       for n,v in [('pc',s['paint']),('sp',0xfd),('p',0x24),('a',0),('x',0),('y',0)]:getattr(m.lib,'zeropage_peddle_set_'+n)(m.handle,v)
       m.write(0x1fe,0xfe);m.write(0x1ff,2);used=lib.paint(m.handle,s['acknowledge']);assert used;calls+=1;instructions+=used
       if m.regs().pc==s['acknowledge']:break
      else:raise AssertionError('unboundedpaint')
      styles=bytearray(161);roles=bytearray([7]*161);hidden=bytearray(21)
      for i in range(count):
       pos=first+i
       if opened<=pos<opened+width or(kind==1 and closed<=pos<closed+width):hidden[i//8]|=128>>(i%8)
       if kind==1 and opened+width<=pos<closed:
        styles[i]=128 if style==4 else((style&2)>>1)|((style&1)<<1)
        if style==4:roles[i]=4
      assert read(S,161)==styles and read(R,161)==roles and read(H,21)==hidden,(count,first,kind,style,displacement)
      after=snap();wanted=bytearray(start)
      for lo,hi in [(S,H+21),(P+22,P+24),(IO+16,IO+19),(0x100,0x200)]:wanted[lo:hi]=after[lo:hi]
      assert after==wanted,('RAM',next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,wanted))if a!=b));assert read(0x6000,len(raw))==raw;vectors+=1
  assert snap(True)==before_reu
  result={'status':'BUDGET_REFUSED/componentPASS','bytes':len(raw),'over4096':len(raw)-4096,'sizes':sizes,'event_paint_vectors':vectors,'bounded32cell_calls':calls,'instructions':instructions,'wholeRAM_intervals':vectors,'whole16MiB':'exactunchanged','scope':'Unpackaged6000privatecandidate; directunmodifiedpaintfragmentstopsBEFOREactualACK; noguard/source/cachehit/publicationqualification'};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
 finally:m.close()
if __name__=='__main__':
 out=ROOT/'build/cache-inline-probe'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
