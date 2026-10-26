"""Exact packaged native-row scratch independence; no editor admission claim.

All 19 inputs are explicit. The 49 remaining NR bytes are poisoned, and actual
6510 output is compared with the independent per-pixel/vote model. No source,
provider or catalogue authority is fabricated: this is a pure leaf contract.
"""
from pathlib import Path
import argparse, ctypes as C, hashlib, json, random
import test_grid_modes as grid

ROOT=grid.ROOT
def run(out,fixture):
 out.mkdir(parents=True);dll=grid.runner(out);m=grid.Machine();prg=(fixture/'build/editor.prg').read_bytes();m.load(int.from_bytes(prg[:2],'little'),prg[2:]);s=json.loads((fixture/'build/editor-report.json').read_text())['symbols'];cases=[]
 def read(at,n):
  b=C.create_string_buffer(n);dll.gm_read(m.handle,at,n,b);return b.raw
 def call(at,x=0,y=0):
  for name,value in [('pc',at),('sp',0xfd),('p',0x24),('a',0),('x',x),('y',y)]:getattr(m.lib,'zeropage_peddle_set_'+name)(m.handle,value)
  m.write(0x1fe,0xfe);m.write(0x1ff,2);n=dll.gm_run(m.handle,2_000_000);assert n;return m.regs(),n
 def reuhash():
  b=C.create_string_buffer(16*1024*1024);dll.gm_reu(m.handle,len(b),b);return hashlib.sha256(b.raw).hexdigest()
 try:
  reu=reuhash();rng=random.Random(0x4e52)
  for width,name,fontname in [(60,'grid60','narrow5.bin'),(80,'grid80','narrow4.bin')]:
   image=(fixture/f'build/overlays/{name}.seo').read_bytes();raw=image[36:];assert len(raw)==4096 and raw[39]==0x4c
   m.load(0xa000,raw);entry=int.from_bytes(raw[40:42],'little');font=(fixture/'fonts'/fontname).read_bytes();assert raw[0x800:0xc00]==font
   for glyph in range(272):
    count=width if glyph<256 else rng.randrange(width+1);chars=bytes([glyph]*count)if glyph<256 else bytes(rng.randrange(256)for _ in range(count))
    roles=bytes((i+glyph)%14 for i in range(count));flags=bytes([(glyph&7)]*count)if glyph<256 else bytes(rng.randrange(8)for _ in range(count));row=2+glyph%22
    m.load(0x9000,chars);m.load(0x9050,roles);m.load(0x90a0,flags);m.load(0x9100,bytes([1,3,7,10,14,1,1,7,13,5,15,7,3,1]))
    frame=bytes([width,row,count,0,6])+b''.join(a.to_bytes(2,'little')for a in(0x6000,0x4000,0xa800,0x9000,0x9050,0x90a0,0x9100))
    assert len(frame)==19
    expected=grid.narrow_row(chars,flags,width,font,roles,colored=True);outputs=[];used=[]
    for poison in(0,0xa7):
     m.load(0x8880,frame+bytes([poison])*49);m.load(0x6000+row*320,bytes([0x5a])*320);m.load(0x4000+row*40,bytes([0x83])*40)
     # Include call's explicit return-address setup in the allowed stack page.
     before=read(0,65536);r,n=call(entry,x=0x80,y=0x88);after=read(0,65536);assert not r.p&1,(width,glyph,poison,r.a)
     actual=(read(0x6000+row*320,320),read(0x4000+row*40,40));assert actual==expected,(width,glyph,poison,'independent pixels/attributes')
     assert read(0x8880,19)==frame
     allowed=set(range(0x100,0x200))|set(range(0x8880,0x88c4))|set(range(0x6000+row*320,0x6000+(row+1)*320))|set(range(0x4000+row*40,0x4000+(row+1)*40))
     for ptr in('text_ptr','screen_ptr'):allowed.update(range(s[ptr],s[ptr]+2))
     bad=[i for i,(a,b)in enumerate(zip(before,after))if a!=b and i not in allowed];assert not bad,(width,glyph,poison,'outside RAM',bad[:12])
     outputs.append(actual);used.append(n)
    assert outputs[0]==outputs[1] and used[0]==used[1],(width,glyph,'scratch influenced output or control flow')
    cases.append(dict(width=width,glyph=glyph,count=count,instructions=used[0],digest=hashlib.sha256(b''.join(outputs[0])).hexdigest()))
   print('PASS scratch poison',width,272,'vectors',flush=True)
  assert reuhash()==reu
  result=dict(status='PASS',scope=__doc__,vectors=len(cases),calls=len(cases)*2,all256eachwidth=True,wholeRAM=True,whole16MiB=True,cases=cases);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:m.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.out.resolve(),a.fixture.resolve())
