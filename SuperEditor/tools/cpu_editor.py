"""Execute real editor startup, injecting ROM SEQ imports only (native proof separate)."""
import json
from pathlib import Path
from peddle import Machine
from overlays import HEADER
ROOT=Path(__file__).resolve().parents[1]
NAMES=['eedit','eplay','window','text40','menu40','engine','navigate','search','block','layout','fileio','aux','styler','viewsource','lexical','gridedit','grid80','grid60','foldparse','foldfinish','foldcore','foldctl','rangeio','foldxform','geosline','geospage','geosrow','geospaint','geosnav']
NAMES += ['geossema','geoslex','geosinln','popups','geospreview','geosfontrow','geosfontin','geosfold','geostail','geoscaret','lifectrl','lifecopy','geosdelta','gfont','gtype','code','clex','type','grid','hotcold']
NAMES += ['fold','sema','inln']

def startup(m,s,assets,banks=256):
 m.load(0x801,(ROOT/'build/editor.prg').read_bytes()[2:]);m.call(s['se_clear_state'])
 m.load(s['se_reu_banks'],banks.to_bytes(2,'little'))
 for name,value in [('a',0),('x',0),('y',0),('p',0x24),('sp',0xFD),('pc',s['se_editor_startup'])]:getattr(m.lib,'zeropage_peddle_set_'+name)(m.handle,value)
 m.write(0x1FE,0xFE);m.write(0x1FF,0x02);steps=0;imports=[]
 while m.regs().pc!=0x02FF:
  regs=m.regs()
  if regs.pc==s.get('se_editor_fonts_import'):
   # Explicit ROM IEC transport seam only. Real provider allocation + checked
   # DMA installs exact immutable pack; native gate exercises actual C28 IEC.
   from font_fixture import install_font_pack
   stack=bytes(m.read(0x100+i) for i in range(256))
   class FontFixture:
    def __init__(self):self.m=m;self.s=s
    def call(self,name,a=0):return m.call(s[name],a=a)[0]
    def read(self,address,count):return bytes(m.read(address+i) for i in range(count))
   install_font_pack(FontFixture())
   m.load(0x100,stack);pc=(stack[(regs.sp+1)&255]|(stack[(regs.sp+2)&255]<<8))+1
   for field,value in [('a',0),('x',0),('y',0),('p',regs.p&254),('sp',(regs.sp+2)&255),('pc',pc)]:getattr(m.lib,'zeropage_peddle_set_'+field)(m.handle,value)
  elif regs.pc==s['se_editor_import']:
   raw=bytes(m.read((regs.x|(regs.y<<8))+i) for i in range(regs.a))
   assert all(v<128 for v in raw),('asset filename',imports,hex(regs.x|(regs.y<<8)),regs.a,raw.hex())
   name=raw.decode('ascii').lower()
   image=assets[name];stack=bytes(m.read(0x100+i) for i in range(256))
   m.load(s['se_overlay_header'],image[:HEADER]);m.load(0x5000,image[HEADER:]);result,_=m.call(s['se_overlay_import']);assert not result.p&1,(name,result.a)
   m.load(0x100,stack);pc=(stack[(regs.sp+1)&255]|(stack[(regs.sp+2)&255]<<8))+1
   for field,value in [('a',result.a),('x',result.x),('y',result.y),('p',result.p),('sp',(regs.sp+2)&255),('pc',pc)]:getattr(m.lib,'zeropage_peddle_set_'+field)(m.handle,value)
   imports.append(name)
  else:m.lib.zeropage_peddle_step_instruction(m.handle)
  steps+=1;assert steps<3_000_000,hex(m.regs().pc)
 assert not m.regs().p&1,(m.regs().a,imports)
 assert imports==NAMES
 return imports
