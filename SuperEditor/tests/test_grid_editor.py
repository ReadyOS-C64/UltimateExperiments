"""C16 narrow source producer/finalizer against immutable actual resident.

Only build/grid-editor is written; no shared editor build or VICE. The map is
built by actual C11, source reads use actual pending-gap view APIs, leaves use
the same frozen resident binding, and pixels use an independent Python oracle.
"""
from pathlib import Path
import ctypes as C,json,hashlib,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import cpu_editor,editor_fixture
from editor_fixture import EditorFixture
from peddle import VENDOR
from overlays import wrap,HEADER
from redraw_model import source40
from test_grid_assets import build as build_leaves
from test_narrow_rows import oracle
OUT=ROOT/'build/grid-editor';BASE=OUT/'frozen'
NAMES=['eedit','eplay','window','text40','menu40','engine','navigate','search','block','layout','fileio','aux','styler','viewsource','lexical']
PALETTE=bytes([1,7,3,7,3,3,3,3,3,3,14,14,14,14])
def run(args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
def build():
 r=json.loads((BASE/'build/editor-report.json').read_text());assert r['sha256']=='46c8b06fbb1b59776d8491d9547b89c446e8aea7aa0649dd78ba9ec299c08003'
 s=r['symbols'];extra=['text_ptr','screen_ptr','tui_putc40','tui_color','tui_box_x','tui_box_y','tui_box_w','tui_box_h'];d=r['resident_binding']['digest']
 api='\n'.join(f'{n} = ${v:04X}' for n,v in s.items() if n.startswith('se_') or n in extra)+'\n.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2] for i in range(0,32,2))+'\n.endmacro\n';(OUT/'editor-api.inc').write_text(api)
 objs=[]
 for n,p in [('grid','src/overlays/grid-editor.s'),('chrome','src/tui/editor-chrome40.s'),('header','src/tui/header40.s'),('mode','src/render/grid/mode.s')]:
  q=OUT/(n+'.o');run(['ca65','-g','-D','EDITOR_OVERLAY=1','-I',OUT,'-I','src','-o',q,p]);objs.append(q)
 run(['ld65','-C','cfg/overlay-c.cfg','-o',OUT/'grid.bin','-Ln',OUT/'grid.lbl','-m',OUT/'grid.map',*objs]);payload=(OUT/'grid.bin').read_bytes();assert len(payload)<=4096
 image=wrap(payload,1,16,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(OUT/'grid-editor.seo').write_bytes(image)
 leaves=build_leaves(OUT/'leaves',BASE)
 return r,{'grid-editor':image,**{f'grid{m}':Path(leaves['records'][m]['path']).read_bytes() for m in [60,80]}}
def runner():
 cpp=OUT/'runner.cpp';cpp.write_text('\n'.join(['#include "zeropage_peddle.h"','extern "C" uint64_t gr_run(ZeroPagePeddle*m,uint64_t limit){auto start=zeropage_peddle_regs(m).instructions;for(uint64_t i=0;i<limit;i++){if(zeropage_peddle_regs(m).pc==0x2ff)return zeropage_peddle_regs(m).instructions-start;zeropage_peddle_step_instruction(m);}return 0;}','extern "C" void gr_read(ZeroPagePeddle*m,uint16_t a,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read(m,a+i);}','extern "C" void gr_reu(ZeroPagePeddle*m,uint32_t n,uint8_t*out){for(uint32_t i=0;i<n;i++)out[i]=zeropage_peddle_read_reu(m,i);}']))
 ext='.dylib' if sys.platform=='darwin' else '.so';lib=OUT/('runner'+ext);run(['clang++','-std=c++20','-O2','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC','-I'+str(VENDOR),cpp,ROOT/('build/libse_peddle'+ext),'-o',lib]);dll=C.CDLL(str(lib));dll.gr_run.argtypes=[C.c_void_p,C.c_uint64];dll.gr_run.restype=C.c_uint64;dll.gr_read.argtypes=[C.c_void_p,C.c_uint16,C.c_uint32,C.c_void_p];dll.gr_reu.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p];return dll
class Fixture(EditorFixture):
 def __init__(self,extras):
  self.runner=runner();super().__init__();self.assets.update(extras);self.extras=extras;self.calls=0
  self.m.call=self.fast_call
 def fast_call(self,address,a=0,x=0,y=0,limit=1_000_000):
  for name,v in [('pc',address),('sp',0xFD),('a',a),('x',x),('y',y),('p',0x24)]:getattr(self.m.lib,'zeropage_peddle_set_'+name)(self.m.handle,v)
  self.m.write(0x1FE,0xFE);self.m.write(0x1FF,2);n=self.runner.gr_run(self.m.handle,limit);assert n,('nonreturn',hex(address),hex(self.m.regs().pc));return self.m.regs(),n
 def read(self,a,n):
  b=C.create_string_buffer(n);self.runner.gr_read(self.m.handle,a,n,b);return b.raw
 def source(self,data,banks=2,physical=32):
  return super().source(data,banks,physical)
 def invoke(self,op,error=None):
  self.put('se_overlay_frame',op,1);r,n=self.m.call(self.s['se_overlay_call'],a=16,x=1,limit=3_000_000);self.calls+=1
  assert bool(r.p&1)==(error is not None),(op,r.a,error)
  assert r.a==(error or 0),(op,r.a,error)
  return r,n
 def layout(self,mode,nowrap=False,top=0):
  self.put('se_v_columns',mode,1);self.put('se_l_mode',int(nowrap),1);self.put('se_v_top',top);self.put('se_l_valid',0,1)
  r=self.call('se_navigation_call',4);assert not r.p&1,('layout begin',r.a)
  for _ in range(5000):
   r=self.call('se_navigation_call',5);assert not r.p&1,('layout step',r.a)
   if r.a==0:break
  else:raise AssertionError('layout unbounded')
 def reu(self):
  b=C.create_string_buffer(2*1024*1024);self.runner.gr_reu(self.m.handle,len(b),b);return b.raw
 def preserved(self):
  return {n:self.read(self.s[n],w) for n,w in [('se_doc_meta',15),('se_doc_generation',2),('se_doc_length',3),('se_doc_read_locks',1),('se_hot_caret',3),('se_hot_pending',1),('se_h_current',4),('se_h_saved',4),('se_sel_anchor',3),('se_sel_mark',1),('se_v_rows',66),('se_v_bottom',3)]}|{'hot':self.read(0x9200,2048),'phase':self.read(0x8D00,1152),'nav':self.read(0x9180,128),'diag':self.read(0x8800,128),'shim':self.read(0xC600,1024),'checkpoint':self.read(0x4400,2048)}

def model(f,data,width):
 pos=f.get('se_v_top');nowrap=f.get('se_l_mode',1);pan=f.get('se_l_pan') if nowrap else 0;caret=f.get('se_hot_caret');mark=f.get('se_sel_mark',1);lo,hi=sorted([caret,f.get('se_sel_anchor')]) if mark else (0,0);rows=[];seen=None;bits=bytearray(8000);attrs=bytearray([0x16])*1000;anchors=[]
 font=(ROOT/f'assets/fonts/generated/narrow{5 if width==60 else 4}.bin').read_bytes()
 for row in range(22):
  anchors.append(pos);chars=[];flags=[]
  if nowrap:
   end=data.find(b'\r',pos);end=len(data) if end<0 else end;next_=end+1 if end<len(data) else end
  else:
   p=pos;count=0
   while p<len(data) and count<width:
    value=data[p];p+=1
    if value==13:break
    count+=1
   next_=p;end=p-1 if p>pos and data[p-1]==13 else p
  for col in range(width):
   p=pos+pan+col;v=data[p] if p<end else 32;flag=0
   if p<=end:
    if mark and lo<=p<hi:flag|=2
    if p==caret and seen is None:flag|=4;seen=(row,col)
   chars.append(v);flags.append(flag)
  b,a=oracle(width,chars,[0]*width,flags,PALETTE,6,0,font);bits[(row+2)*320:(row+3)*320]=b;attrs[(row+2)*40:(row+3)*40]=a;rows.append((bytes(chars),bytes(flags)));pos=next_
 anchors.append(pos)
 return bits,attrs,tuple(anchors),seen

def main():
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'result.json').unlink(missing_ok=True);report,extras=build();cpu_editor.ROOT=editor_fixture.ROOT=BASE;cpu_editor.NAMES=editor_fixture.NAMES=NAMES
 f=Fixture(extras);cases=[];screens=0;peak=0
 def check(data,width,tag,popup=None):
  nonlocal screens,peak
  saved=f.preserved();reu=f.reu();catalog=f.read(0x7F40,192)
  _,n=f.invoke(1);peak=max(peak,n);assert f.get('se_l_need_wrap',1)==0,tag
  assert f.preserved()==saved,(tag,'source/phase/navigation/shim changed')
  bits,attrs,anchors,seen=model(f,data,width)
  actual=tuple(int.from_bytes(f.read(f.s['se_v_rows']+i*3,3),'little') for i in range(22))+(f.get('se_v_bottom'),);assert actual==anchors,(tag,actual,anchors)
  assert f.read(0x6000+640,7040)==bits[640:7680],(tag,'body pixels')
  assert f.read(0x4050,880)==attrs[80:960],(tag,'body attributes')
  assert f.get('se_v_seen',1)==int(seen is not None),(tag,'caret seen',seen)
  if seen:assert (f.get('se_v_caret_row',1),f.get('se_v_caret_col',1))==seen
  # Logical header/status independent oracle, then a deliberately dense popup.
  chrome=source40(data,f.get('se_v_top'),f.get('se_hot_caret'),marked=bool(f.get('se_sel_mark',1)),anchor=f.get('se_sel_anchor'),pending=bool(f.get('se_hot_pending',1)),dirty=bool(f.get('se_h_dirty',1)))
  for row in [0,1,24]:assert f.read(0x4000+row*40,40)==chrome.matrix[row*40:(row+1)*40]
  ui=bytearray(f.read(0x4000,1000));colors=bytearray(f.read(0xD800,1000));cells={(r,c) for r in [0,1,24] for c in range(40)}
  if popup:
   x,y,w,h=popup
   for n,v in [('tui_box_x',x),('tui_box_y',y),('tui_box_w',w),('tui_box_h',h)]:f.put(n,v,1)
   f.put('se_e_ui',3,1)
   for row in range(y,y+h):
    for col in range(x,x+w):
     i=row*40+col;ui[i]=(i*37+11)&255;colors[i]=(i*3)&15;cells.add((row,col))
   f.m.load(0x4000,ui);f.m.load(0xD800,colors)
  else:f.put('se_e_ui',0,1)
  font=(ROOT/'assets/fonts/generated/native8.bin').read_bytes()
  for row,col in cells:
   i=row*40+col;code=ui[i];bits[row*320+col*8:row*320+col*8+8]=bytes(v^(255 if code&128 else 0) for v in font[(code&127)*8:(code&127)*8+8]);attrs[i]=((colors[i]&15)<<4)|6
  _,n=f.invoke(2);peak=max(peak,n)
  assert f.read(0x6000,8000)==bits,(tag,'final bitmap')
  assert f.read(0x4000,1000)==attrs,(tag,'final attributes')
  assert f.read(0x7F40,192)==catalog and f.reu()==reu,(tag,'REU/catalog changed')
  assert f.preserved()==saved,(tag,'finalize changed source/phase/shim')
  f.put('se_e_ui',0,1);screens+=1;cases.append(tag)
 try:
  data=bytes([0x41,0xC1,0x5D,0xA1,0xFF,0x21])*37+b'\r'+bytes(range(32,128))+b'\r\r'+b'last line'
  for width in [60,80]:
   for nowrap in [False,True]:
    f.source(data);f.layout(width,nowrap);check(data,width,f'{width}/'+('nowrap' if nowrap else 'wrap'))
    f.put('se_sel_mark',1,1);f.put('se_sel_anchor',2);f.position(90);f.layout(width,nowrap);check(data,width,f'{width}/selection-caret-union',popup=(3,5,34,16))
    if nowrap:
     f.put('se_l_manual',1,1);f.put('se_l_pan',150);check(data,width,f'{width}/manual-hidden')
     f.put('se_l_manual',0,1);check(data,width,f'{width}/autopan-left')
   for size in [0,width-1,width,width+1,2*width]:
    for cr in [False,True]:
     data2=b'A'*size+(b'\r' if cr else b'');f.source(data2);f.position(len(data2));f.layout(width);check(data2,width,f'{width}/EOF-{size}-CR{cr}',popup=(0,0,40,25) if size==0 else None)
  # Actual pending source, no flush. Current view may exceed hot gap into REU.
  f.source(b'A'*256+b'\rTAIL');f.position(73);f.key(0xC2);data3=b'A'*73+bytes([0xC2])+b'A'*(256-73)+b'\rTAIL';assert f.get('se_hot_pending',1)
  f.layout(80);check(data3,80,'pending-gap-no-flush')
  # Long logical lines exercise24-bit caret columns, auto-pan subtraction,
  # source window reads beyond64KiB and explicit manual-pan overflow blanks.
  data4=b'A'*66000+b'\rEND';f.source(data4);f.position(65580);f.layout(60,True);check(data4,60,'24bit-autopan')
  assert f.get('se_l_pan')==65580-59
  f.put('se_l_manual',1,1);f.put('se_l_pan',0xFFFFFF);check(data4,60,'24bit-manual-overflow-blank')
  # Live owner1 phase is opaque; producer must not reinterpret its851 bytes.
  f.source(data);f.layout(80);f.put('se_f_owner',1,1);f.m.load(0x8D00,bytes((i*31+7)&255 for i in range(851)));check(data,80,'owner1-opaque-filephase');f.put('se_f_owner',0,1)
  # A missing renderer leaf fails before any body/chrome output.
  ids=f.read(f.s['se_overlay_ids'],24);where=ids.index(16);f.m.write(f.s['se_overlay_ids']+where,0)
  before=f.read(0x4000,1024)+f.read(0x6000,8192);f.invoke(1,error=0x17);assert f.read(0x4000,1024)+f.read(0x6000,8192)==before;f.m.load(f.s['se_overlay_ids'],ids)
  # Each stale context path must refuse before leaf catalog/pixel writes.
  f.source(data);f.layout(80);f.invoke(1)
  for name,w in [('se_l_valid',1),('se_n_view_columns',1),('se_l_original',1),('se_l_generation',1),('se_l_revision',1),('se_l_top',1)]:
   old=f.read(f.s[name],w);f.m.write(f.s[name],old[0]^1);before=f.read(0x4000,1024)+f.read(0x6000,8192)+f.read(f.s['se_overlay_active'],2);f.invoke(1);assert f.get('se_l_need_wrap',1)==1 and f.read(0x4000,1024)+f.read(0x6000,8192)+f.read(f.s['se_overlay_active'],2)==before,(name,'stale wrote outputs');f.m.load(f.s[name],old)
  # Malformed monotonic/oversized rows also require a new C11 map.
  for offset,value in [(3,0xFFFFFF),(3,81)]:
   old=f.read(f.s['se_v_rows']+offset,3);f.m.load(f.s['se_v_rows']+offset,value.to_bytes(3,'little'));before=f.read(0x4000,1024)+f.read(0x6000,8192);f.invoke(1);assert f.get('se_l_need_wrap',1)==1 and f.read(0x4000,1024)+f.read(0x6000,8192)==before;f.m.load(f.s['se_v_rows']+offset,old)
  f.put('se_v_columns',40,1);f.invoke(1,error=0x7B)
  result=dict(status='passed',resident_sha256=report['sha256'],payload_bytes=len((OUT/'grid.bin').read_bytes()),workspace_first=0x8880,workspace_end_exclusive=0x8A42,new_BSS=0,new_ZP=0,screens=screens,pixels=screens*64000,peak_call_instructions=peak,cases=cases,scope='Actual frozen resident+C11/view/pending reader+C16+C-to-R leaves; CPU pixels/ownership only, no native/editor mode integration claim')
  (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:f.close()
if __name__=='__main__':main()
