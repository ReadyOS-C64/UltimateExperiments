"""Actual6510 operation-sized unaligned native8 tile compositor proof.

Independent source/font ink-vote model; no shared editor build/native claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import ctypes as C,hashlib,json,re,subprocess,sys,zipfile,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_row as row
from peddle import Machine
from test_geos_glyphs import native
F=0x8F00;SIZE=48
PRIORITY=[0,6,7,8,0,0,0,5,3,4,1,5,2,0]
PALETTE=[1,3,7,10,14,1,1,7,13,5,15,7,3,1]
def cmd(*args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
def build(out):
 (out/'aliases.s').write_text('.export se_f_owner,se_gnp_palette\n.exportzp text_ptr,screen_ptr\nse_f_owner=$0400\ntext_ptr=$F0\nscreen_ptr=$F2\n.segment \"RODATA\"\nse_gnp_palette:.byte 1,3,7,10,14,1,1,7,13,5,15,7,3,1\n')
 objects=[]
 for name,path in [('worker',ROOT/'src/render/geos/native-pan.s'),('petscii',ROOT/'src/tui/petscii.s'),('aliases',out/'aliases.s')]:
  obj=out/(name+'.o');cmd('ca65','-g','-I','src','-o',obj,path);objects.append(obj)
 cmd('ld65','-C','cfg/geos-native-pan-test.cfg','-o',out/'worker.bin','-Ln',out/'worker.lbl','-m',out/'worker.map',*objects)
 symbols={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(out/'worker.lbl').read_text())}
 dump=subprocess.check_output(['od65','--dump-segments',str(objects[0])],text=True)
 sizes={n:int(v) for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',dump,re.S)}
 assert sizes['CODE']<=650 and all(sizes.get(n,0)==0 for n in ['BSS','DATA','ZEROPAGE'])
 return symbols,sizes

def run(out):
 s,sizes=build(out);row.OUT=out;dll=row.runner();m=Machine();m.load(0,bytes((i*73+19)&255 for i in range(65536)))
 m.load(0x1000,(out/'worker.bin').read_bytes());font=(ROOT/'assets/fonts/generated/native8.bin').read_bytes();m.load(0x4800,font);m.write(0x400,4)
 calls=steps=cases=invalid=0;peak=0;coverage=[]
 def read(a,n):
  b=C.create_string_buffer(n);dll.gr_read(m.handle,a,n,b);return b.raw
 def reu():
  b=C.create_string_buffer(16*1024*1024);dll.gr_reu(m.handle,len(b),b);return b.raw
 def invoke(name):
  nonlocal calls,peak
  for n,v in [('pc',s[name]),('sp',0xFD),('a',0),('x',0),('y',0),('p',0x24)]:getattr(m.lib,'zeropage_peddle_set_'+n)(m.handle,v)
  m.write(0x1FE,0xFE);m.write(0x1FF,2);n=dll.gr_run(m.handle,1_000_000);assert n,('nonreturn',name)
  calls+=1;peak=max(peak,n);return m.regs()
 def allowed(before,after,tile=None,row_=None):
  expected=bytearray(before)
  for a,b in [(F+10,F+SIZE),(0xF0,0xF4),(0x100,0x200)]:expected[a:b]=after[a:b]
  if tile is not None:
   a=0x6000+row_*320+tile*8;expected[a:a+8]=after[a:a+8];a=0x4000+row_*40+tile;expected[a]=after[a]
  assert after==expected,('fullRAM/outputtile/font/source/shim/catalog',next((hex(i),a,b) for i,(a,b) in enumerate(zip(after,expected)) if a!=b))
 def setup(chars,roles,flags,origin=0,row_=2):
  n=len(chars);assert 1<=n<=64 and len(roles)==len(flags)==n
  m.load(0x8D20,chars);m.load(0x8DA0,bytes(roles));m.load(0x8DE0,bytes(flags))
  frame=bytes([row_])+(origin&65535).to_bytes(2,'little')+bytes([n])+b'\x20\x8D\xA0\x8D\xE0\x8D'
  m.load(F,frame+bytes([0xA7])*(SIZE-10));return frame
 def model(chars,roles,flags,origin,row_):
  result={}
  for tile in range(max(0,origin//8),min(40,(origin+len(chars)*8+7)//8)):
   pixels=bytearray(8);weights=[0]*14
   for i,(value,role,flag) in enumerate(zip(chars,roles,flags)):
    x=origin+i*8
    if x+8<=tile*8 or x>=tile*8+8:continue
    glyph=font[native(value)*8:native(value)*8+8]
    for y,ink in enumerate(glyph):
     if flag&1:ink^=255
     for bit in range(8):
      px=x+bit
      if not tile*8<=px<tile*8+8:continue
      base=bool(ink&(128>>bit));weights[role]+=base
      if base^bool(flag&6):pixels[y]|=128>>(px%8)
   role=max(range(14),key=lambda r:(weights[r],PRIORITY[r] if weights[r] else 0,-r))
   result[tile]=(bytes(pixels),(PALETTE[role]<<4)|6,weights)
  return result
 def check(chars,roles,flags,origin=0,row_=2):
  nonlocal steps,cases
  frame=setup(chars,roles,flags,origin,row_);want=model(chars,roles,flags,origin,row_)
  before=read(0,65536);r=invoke('se_gnp_begin');after=read(0,65536)
  assert not r.p&1 and r.a==1 and after[F:F+10]==frame;allowed(before,after)
  for i,(tile,(pixels,color,weights)) in enumerate(want.items()):
   assert m.read(F+11)==tile
   before=read(0,65536);r=invoke('se_gnp_step');after=read(0,65536)
   assert not r.p&1 and r.a==int(i+1<len(want)),('step',origin,len(chars),i,hex(r.a),r.p)
   a=0x6000+row_*320+tile*8
   assert after[a:a+8]==pixels,('pixels',origin,tile,after[a:a+8].hex(),pixels.hex(),list(chars),list(flags))
   assert after[0x4000+row_*40+tile]==color,('majority',tile,weights,after[0x4000+row_*40+tile],color)
   assert after[F+24:F+38]==bytes(weights),('inkweights',tile,list(after[F+24:F+38]),weights)
   allowed(before,after,tile,row_);steps+=1
  assert not m.read(F+10) and after[F:F+10]==frame
  before=read(0,65536);r=invoke('se_gnp_step');after=read(0,65536);assert r.p&1 and r.a==0x70;allowed(before,after)
  cases+=1
 try:
  original_reu=reu()
  for origin in list(range(-7,8))+[8,17,159,311,319]:
   for n in [1,2,3,41,64]:
    chars=bytes((i*29+origin)&255 for i in range(n));check(chars,[(i+origin)%14 for i in range(n)],[(i+origin)%8 for i in range(n)],origin,(origin+n)%22+2)
  for value in range(256):
   flag=value%8;check(bytes([value,255-value]),[value%14,(value+7)%14],[flag,flag],-1 if value%2 else 3,value%22+2)
  # Every flag union and semantic role. Inverse counts feed tile-color voting;
  # selected+caret together produces the same pixels as either flag alone.
  for flag in range(8):
   for role in range(14):check(b'Wim ',[role]*4,[flag]*4,-4,2+role)
  for a,b in [(1,2),(2,3),(7,11),(9,8),(12,10)]:check(b'  ',[a,b],[1,1],-4)
  check(b'  ',[3,2],[0,0],3) #allblank defaultsrole0
  coverage.extend(['all256nativebytes','negative-7..-1/positive0..319','allroles/flags/union','same-role-combinedvotes/semanticpriorityties/blankrole0','oneaffectedtileperSTEP/fullRAMguards'])
  # MalformedBEGIN must not publish any pixels/attributes. Only owned private
  # validation scratch/ZP/stack may change, never any input byte or source.
  mutations=[(0,1),(0,24),(3,0),(3,65),(2,2),(2,0xFE),(5,0x8C),(5,0x8F),(7,0x8C)]
  for at,value in mutations:
   setup(b'Valid',[0]*5,[0]*5);m.write(F+at,value);before=read(0,65536);r=invoke('se_gnp_begin');after=read(0,65536)
   assert r.p&1 and r.a==0x90,(at,value,hex(r.a));allowed(before,after);invalid+=1
  setup(b'Valid',[0]*5,[0]*5);m.load(F+1,b'\xF8\xFF')
  before=read(0,65536);r=invoke('se_gnp_begin');after=read(0,65536);assert r.p&1 and r.a==0x90;allowed(before,after);invalid+=1
  setup(b'Valid',[0]*5,[0]*5);m.load(F+4,b'\xFE\x8E')
  before=read(0,65536);r=invoke('se_gnp_begin');after=read(0,65536);assert r.p&1 and r.a==0x90;allowed(before,after);invalid+=1
  for at,value in [(0x8DA0,14),(0x8DE0,8)]:
   setup(b'Valid',[0]*5,[0]*5);m.write(at,value);before=read(0,65536);r=invoke('se_gnp_begin');after=read(0,65536)
   assert r.p&1 and r.a==0x90;allowed(before,after);invalid+=1
  for owner in [0,1,2,3,5,255]:
   m.write(0x400,owner);m.load(F,bytes([0xA5])*SIZE)
   for name in ['se_gnp_begin','se_gnp_step']:
    before=read(0,65536);r=invoke(name);after=read(0,65536);assert r.p&1 and r.a==0xB2
    expected=bytearray(before);expected[0x100:0x200]=after[0x100:0x200];assert after==expected;invalid+=1
  m.write(0x400,4);assert reu()==original_reu
  result=dict(status='passed',code_bytes=sizes['CODE'],RODATA_bytes=sizes['RODATA'],linked_worker_bytes=sum(sizes[n] for n in ['CODE','RODATA']),caller_frame_bytes=SIZE,new_BSS=0,new_ZP=0,borrowed_ZP_bytes=4,cases=cases,tile_steps=steps,invalid_frames=invalid,calls=calls,peak_call_instructions=peak,full_RAM_guard_bytes=65536,full_REU_unchanged=16777216,coverage=coverage,scope='Actualnative8tilemicromodule independentpixel/inkvote/flag/source/origin oracle; no editorbinding/nativeVIC claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');archive=ROOT/'agentsworking/evidence/M7'/(out.name+'-geos-native-pan');archive.mkdir(parents=True)
  for n in ['result.json','worker.bin','worker.lbl','worker.map']:shutil.copy2(out/n,archive/n)
  with zipfile.ZipFile(archive/'sources.zip','w',zipfile.ZIP_DEFLATED) as z:
   for p in ['src/render/geos/native-pan.s','src/render/geos/native-pan.inc','cfg/geos-native-pan-test.cfg','tests/test_geos_native_pan.py']:z.write(ROOT/p,p)
  (ROOT/'agentsworking/evidence/M7/geos-native-pan-checkpoint.json').write_text(json.dumps(dict(status='passed',evidence=str(archive.relative_to(ROOT)),code_bytes=sizes['CODE'],total_bytes=result['linked_worker_bytes'],cases=cases,tile_steps=steps),indent=2)+'\n');print(json.dumps(result,indent=2));return result
 finally:m.close()
if __name__=='__main__':
 out=ROOT/'build/geos-native-pan'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out)
