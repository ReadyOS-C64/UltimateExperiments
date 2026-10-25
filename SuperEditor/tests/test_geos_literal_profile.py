"""Private PC profile of byte-identical frozen R21, with independent strip oracle.

No production changes, no loader bypass claim: entry A010 is invoked as an
explicit isolated-leaf seam after loading the frozen resident and exact payload.
Instruction counts are CPU work, not emulated VIC/IRQ cycles.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,re,subprocess,sys,zipfile,shutil
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_row as model
import test_geos_row_leaf as leaf
from peddle import Machine,VENDOR,library
from overlays import HEADER
from bindings import verify

def run(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(out,base,specialize=False,byte=False):
 src=out/'frozen-sources';src.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip') as z:z.extractall(src)
 (src/'assets/fonts/generated').mkdir(parents=True,exist_ok=True)
 for n in ['bsw9-original.bin','bsw9-widths.bin','bsw9.bin']:shutil.copy2(base/'fonts'/n,src/'assets/fonts/generated'/n)
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];binding=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_f_owner\n.importzp text_ptr,screen_ptr\n.macro OVL_BINDING\n.byte '+','.join('$'+binding[i:i+2] for i in range(0,32,2))+'\n.endmacro\n')
 objs=[]
 for n in leaf.SOURCES:
  p=out/(n.replace('/','-')+'.o');source=ROOT/f'src/render/geos/literal-byte-candidate/{n.rsplit("/",1)[1]}.s' if specialize and n.rsplit('/',1)[1] in (['measure','glyph','assets','row'] if byte else ['measure','glyph','assets']) else src/f'src/{n}.s';subprocess.run(list(map(str,['ca65','-g','-I',out,'-I',src/'src','-o',p,source])),cwd=src,check=True);objs.append(p)
 run(sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objs)
 run('ca65','-g','-o',out/'aliases.o',out/'aliases.s')
 run('ld65','-C',ROOT/'src/render/geos/literal-byte-candidate/row.cfg' if specialize else src/'cfg/geos-editor-row.cfg','-o',out/'geosrow.bin','-Ln',out/'geosrow.lbl','-m',out/'geosrow.map',*objs,out/'aliases.o')
 payload=(out/'geosrow.bin').read_bytes();sealed=(base/'build/overlays/geosrow.seo').read_bytes()
 assert specialize or payload==sealed[HEADER:],('frozen R21 reassembly mismatch',len(payload),len(sealed)-HEADER)
 labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(out/'geosrow.lbl').read_text())}
 # ld65 CODE module offsets are used instead of guessing spans from symbols.
 text=(out/'geosrow.map').read_text();modules={}
 for name,body in re.findall(r'^(\S+)\.o:\n(.*?)(?=^\S+\.o:|^Segment list:)',text,re.M|re.S):
  seg={n:(int(o,16),int(size,16)) for n,o,size in re.findall(r'^\s+(\w+)\s+Offs=([0-9A-F]+)\s+Size=([0-9A-F]+)',body,re.M)};modules[name]=seg
 return src,s,labels,payload,modules

def runner(out):
 library();p=out/'profile.cpp';p.write_text('''#include "zeropage_peddle.h"
#include <cstring>
static uint64_t pcs[65536];
extern "C" void lp_clear(){memset(pcs,0,sizeof(pcs));}
extern "C" void lp_counts(uint64_t*out){memcpy(out,pcs,sizeof(pcs));}
extern "C" uint64_t lp_run(ZeroPagePeddle*m,uint64_t max){for(uint64_t i=0;i<max;i++){auto r=zeropage_peddle_regs(m);if(r.pc==0x2ff)return i;pcs[r.pc]++;zeropage_peddle_step_instruction(m);}return 0;}
extern "C" void lp_read(ZeroPagePeddle*m,uint16_t at,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read(m,at+i);}
extern "C" void lp_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read_reu(m,i);}
''')
 ext='.dylib' if sys.platform=='darwin' else '.so';q=out/('profile'+ext)
 run('clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),p,ROOT/('build/libse_peddle'+ext),'-o',q)
 d=C.CDLL(str(q));d.lp_run.argtypes=[C.c_void_p,C.c_uint64];d.lp_run.restype=C.c_uint64;d.lp_counts.argtypes=[C.c_void_p];d.lp_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];d.lp_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p];return d

class Fixture:
 setup=leaf.Fixture.setup
 oracle=model.Fixture.oracle
 def __init__(self,out,base,src,s,ls,payload):
  self.s=s;self.ls=ls;self.m=Machine();self.r=runner(out)
  self.m.load(0,bytes((i*73+19)&255 for i in range(0xd000)))
  raw=(base/'build/editor.prg').read_bytes();self.m.load(int.from_bytes(raw[:2],'little'),raw[2:]);self.m.load(0xa000,payload)
  self.font=(src/'assets/fonts/generated/bsw9.bin').read_bytes();self.widths=(src/'assets/fonts/generated/bsw9-widths.bin').read_bytes();self.native=(base/'fonts/native8.bin').read_bytes();self.native_addr=0x4800
  self.m.load(self.native_addr,self.native);self.m.load(leaf.PALETTE,model.PALETTE)
 def read(self,a,n):
  p=C.create_string_buffer(n);self.r.lp_read(self.m.handle,a,n,p);return p.raw
 def reu(self):
  p=C.create_string_buffer(16777216);self.r.lp_reu(self.m.handle,len(p),p);return p.raw
 def close(self):self.m.close()
 def check(self,runs,row=2,clip=(0,320,0,8),reset=True,hist=None):
  frame,records=self.setup([(*r[:4],r[4]&65535,r[5]) for r in runs],row,clip,reset);self.m.write(self.s['se_f_owner'],4);self.m.load(self.s['se_overlay_frame'],bytes([0,0x80,0x88]));before=self.read(0,65536)
  want,weights,maps,dones=self.oracle(runs,row,clip,before,hist)
  self.r.lp_clear()
  for n,v in [('pc',0xa010),('sp',0xfd),('p',0x24),('a',0),('x',0),('y',0)]:getattr(self.m.lib,'zeropage_peddle_set_'+n)(self.m.handle,v)
  self.m.write(0x1fe,0xfe);self.m.write(0x1ff,2);used=self.r.lp_run(self.m.handle,3_000_000);assert used
  r=self.m.regs();after=self.read(0,65536);assert not r.p&1 and r.a==0,(r.a,r.p)
  assert after[leaf.F:leaf.F+20]==frame and after[leaf.F+20]==1
  assert after[leaf.F+98:leaf.F+658]==bytes(v for w in weights for v in w)
  for i,(at,n,arrays) in enumerate(records):
   expected=b''.join((v&65535).to_bytes(2,'little') for v in maps[i]);assert after[at:at+len(expected)]==expected
   assert after[at+len(expected):at+2*(n+1)]==b'\xa7'*(2*(n+1)-len(expected))
   desc=0x8d00+i*17+14;v=bytes([dones[i]])+(maps[i][-1]&65535).to_bytes(2,'little');assert after[desc:desc+3]==v
   want[at:at+len(expected)]=expected;want[desc:desc+3]=v
  for lo,hi in [(leaf.F+20,leaf.F+leaf.SIZE),(0x100,0x200),*( (self.s[n],self.s[n]+2) for n in ['text_ptr','screen_ptr'])]:want[lo:hi]=after[lo:hi]
  assert after==want,('fullRAM/bitmap/attrs/maps/votes/source/shim',next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,want)) if a!=b))
  counts=(C.c_uint64*65536)();self.r.lp_counts(counts);assert sum(counts)==used
  return used,list(counts),weights

def rec(chars,x=0,y=0,style=0,flag=0,role=0):
 n=len(chars);return chars,bytes([style])*n,bytes([role])*n,bytes([flag])*n,x,y

def main():
 p=argparse.ArgumentParser();p.add_argument('--byte',action='store_true');p.add_argument('--specialize',action='store_true');p.add_argument('--base',type=Path,default=ROOT/'build/geos-incremental-editor/20261025T115828132288Z/fixture');a=p.parse_args()
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'build/geos-literal-profile'/stamp;out.mkdir(parents=True)
 src,s,ls,payload,modules=build(out,a.base,a.specialize or a.byte,a.byte);f=Fixture(out,a.base,src,s,ls,payload);result=[]
 cases=[('blank',[],(0,320,0,8)),('empty-run',[rec(b'')],(0,320,0,8)),('prose',[rec(b'Wim. gjpqy Mixed UPPER/lower')],(0,320,0,8)),('dense',[rec(b'Wim. gjpqy '*9,style=3,role=7)],(0,320,0,8)),('selected',[rec(b'Wim. gjpqy '*9,style=3,flag=6,role=7)],(0,320,0,8)),('partial',[rec(b'Wim. gjpqy Mixed UPPER/lower')],(7,319,1,7)),('two-runs',[rec(b'gjpqy Previous line',y=-8,style=2,role=3),rec(b'Next logical line',y=1,style=1,flag=2,role=8)],(0,320,0,8)),('native-fallback',[rec(bytes([0x5c,0x5e,0x7f,0xa1,0xff])*10,style=3,role=2)],(0,320,0,8)),('signed-left',[rec(b'Wim. gjpqy',x=-15,style=3,flag=3,role=7)],(0,320,0,8))]
 try:
  reu=f.reu()
  for name,runs,clip in cases:
   used,counts,_=f.check(runs,clip=clip)
   groups={}
   for m,segs in modules.items():
    groups[m]=sum(sum(counts[0xa000+off:0xa000+off+size]) for seg,(off,size) in segs.items() if seg=='CODE')
   # Exclusive bins: main row functions form intervals; tail clear is separate.
   rowlabels=['se_geos_row','clear_slot','begin_runs','next_run','next_glyph','run_done','return','argument','boundary','input','descriptor','glyph_setup','glyph','clipped_left','clipped_right','pixel_address','histogram_address','validate','horizontal','frame_pointer','endpoint','phase_span','readable','resolve','complete','next_pixel','raster_next']
   ordered=sorted((ls[n],n) for n in rowlabels);bins={}
   # End intervals at the next row label or moduleCODEend, whichever first.
   rowoff,rowsize=modules['render-geos-row']['CODE'];rowend=0xa000+rowoff+rowsize
   for i,(lo,n) in enumerate(ordered):
    if lo<rowend:bins[n]=sum(counts[lo:min(ordered[i+1][0] if i+1<len(ordered) else rowend,rowend)])
   bins['tail_clear']=sum(counts[ls['row_clear']:ls['next_pixel']]);bins['next_pixel']=sum(counts[ls['next_pixel']:ls['raster_next']]);bins['raster_next']=sum(counts[ls['raster_next']:0xaff6])
   groups['tail_helpers']=sum(counts[0xaf5b:0xb000]);groups['outside_R21']=sum(counts[:0xa000])+sum(counts[0xb000:]);assert sum(groups.values())==used,groups
   result.append(dict(case=name,instructions=used,modules=groups,row_intervals=bins,hot_pcs=[dict(pc=hex(pc),executions=v) for pc,v in sorted(enumerate(counts),key=lambda q:-q[1])[:20]],glyphs=sum(len(r[0]) for r in runs),bitmap_sha256=hashlib.sha256(f.read(0x6280,320)).hexdigest(),attrs_sha256=hashlib.sha256(f.read(0x4050,40)).hexdigest()))
   print(name,used,groups,flush=True)
  assert f.reu()==reu
 finally:f.close()
 report=dict(status='passed',specialized=a.specialize,fixture=str(a.base),resident_sha256=sha(a.base/'build/editor.prg'),payload_sha256=hashlib.sha256(payload).hexdigest(),payload_bytes=len(payload),font=[hex(ls[n]) for n in ['se_geos_packed','se_geos_widths']],module_segments=modules,cases=result,scope='Nine actual isolated A010 R21 invocations. Frozen baseline byte-identical reassembly; optional private fixed-GG specialization separately labeled. Independent complete pixels/attributes/saturating-votes/maps, fullRAM and16MiB guards; PC counts only, no native cycle inference.')
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print('RESULT',out,flush=True)
if __name__=='__main__':main()
