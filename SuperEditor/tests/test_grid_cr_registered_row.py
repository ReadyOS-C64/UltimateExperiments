"""Frozen production CR blitter versus independent glyph/flag native row model."""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,subprocess,sys
import test_grid_modes as grid
ROOT=grid.ROOT
def run(out,fixture):
 out.mkdir(parents=True);s=json.loads((fixture/'build/editor-report.json').read_text())['symbols']
 source=out/'production-raw-row.s';import zipfile;source.write_bytes(zipfile.ZipFile(fixture/'product-sources.zip').read('src/render/grid/cr/raw-row.s'));obj=out/'raw.o'
 subprocess.run(['ca65','-g','-o',obj,source],check=True)
 (out/'aliases.s').write_text('text_ptr=$'+format(s['text_ptr'],'04X')+'\nscreen_ptr=$'+format(s['screen_ptr'],'04X')+'\n.exportzp text_ptr,screen_ptr\nse_petscii_screen=$'+format(s['se_petscii_screen'],'04X')+'\n.export se_petscii_screen\n')
 subprocess.run(['ca65','-o',out/'aliases.o',out/'aliases.s'],check=True)
 (out/'link.cfg').write_text('MEMORY { CODE: start=$A000,size=$1000,file=%O; } SEGMENTS { CODE: load=CODE,type=ro; }')
 subprocess.run(['ld65','-C',out/'link.cfg','-o',out/'raw.bin','-Ln',out/'raw.lbl',obj,out/'aliases.o'],check=True)
 import re
 labels={n:int(a,16)for a,n in re.findall(r'al ([0-9a-fA-F]+) \.(\w+)',(out/'raw.lbl').read_text())};dll=grid.runner(out);m=grid.Machine();prg=(fixture/'build/editor.prg').read_bytes();m.load(int.from_bytes(prg[:2],'little'),prg[2:]);m.load(0xa000,(out/'raw.bin').read_bytes());cases=[];bad=[]
 def read(at,n):
  b=C.create_string_buffer(n);dll.gm_read(m.handle,at,n,b);return b.raw
 def call():
  for n,v in [('pc',labels['se_cr_raw_row']),('sp',0xfd),('p',0x24),('a',0),('x',0),('y',0)]:getattr(m.lib,'zeropage_peddle_set_'+n)(m.handle,v)
  m.write(0x1fe,0xfe);m.write(0x1ff,2);n=dll.gm_run(m.handle,2_000_000);assert n;return m.regs(),n
 def reuhash():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(m.handle,len(b),b);return hashlib.sha256(b.raw).hexdigest()
 try:
  beforeREU=reuhash()
  for width,name in [(60,'narrow5.bin'),(80,'narrow4.bin')]:
   font=(fixture/'fonts'/name).read_bytes();m.load(0x5000,font);m.write(0x89c1,width)
   for glyph in range(256):
    row=glyph%22;m.write(0x89c3,row)
    for flags in range(8):
     chars=bytes([glyph])*width;roles=bytes(width);fl=bytes([flags])*width;m.load(0x88c4,chars+bytes(80-width)+roles+bytes(80-width)+fl+bytes(80-width));m.load(0x8880,b'\xa7'*68)
     at=0x6000+(row+2)*320;attrs=0x4000+(row+2)*40;m.load(at,b'\x5a'*320);m.load(attrs,b'\x83'*40)
     before=read(0,65536);r,n=call();after=read(0,65536);assert not r.p&1,(width,glyph,flags,r.a)
     want=grid.narrow_row(chars,fl,width,font,roles,colored=True);assert(read(at,320),read(attrs,40))==want,(width,glyph,flags,'independent fullpixels/attrs')
     permitted=set(range(0x100,0x200))|set(range(0x8880,0x88c4))|set(range(at,at+320))|set(range(attrs,attrs+40))
     for ptr in('text_ptr','screen_ptr'):permitted.update(range(s[ptr],s[ptr]+2))
     differences=[i for i,(a,b)in enumerate(zip(before,after))if a!=b and i not in permitted];assert not differences,(width,glyph,flags,'outsideRAM',differences[:12]);cases.append(dict(width=width,glyph=glyph,flags=flags,instructions=n))
   print('PASS',width,'all256 x flags8',flush=True)
  for width,row,offset,value in [(0,0,None,0),(59,0,None,0),(60,22,None,0),(80,255,None,0),(60,0,80,1),(80,0,160,8)]:
   m.write(0x89c1,width);m.write(0x89c3,row);m.load(0x88c4,bytes(240))
   if offset is not None:m.write(0x88c4+offset,value)
   before=read(0,65536);r,n=call();after=read(0,65536);assert r.p&1;assert before[:0x100]==after[:0x100]and before[0x200:]==after[0x200:];bad.append(dict(width=width,row=row,offset=offset,instructions=n))
  assert beforeREU==reuhash();result=dict(status='PASS',scope=__doc__,size=len((out/'raw.bin').read_bytes()),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),cases=cases,faults=bad,wholeRAM=True,whole16MiB=True);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:m.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.out.resolve(),a.fixture.resolve())
