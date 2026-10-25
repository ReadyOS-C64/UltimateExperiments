"""Independent real6510 4/5px row carry, allcolumns and wholeRAM guard."""
from pathlib import Path
from datetime import datetime,timezone
import ctypes as C,random,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools')]
from peddle import Machine
import test_grid_modes as grid
D=ROOT/'src/render/grid/long-prose-candidate'
def run(out):
 subprocess.run(['ca65','-g','-I',D,'-o',out/'shift.o',D/'shift-row.s'],check=True);(out/'aliases.s').write_text('.exportzp screen_ptr\nscreen_ptr=$04\n');subprocess.run(['ca65','-o',out/'aliases.o',out/'aliases.s'],check=True);subprocess.run(['ld65','-C',D/'shift-row.cfg','-o',out/'shift.bin','-Ln',out/'shift.lbl',out/'shift.o',out/'aliases.o'],check=True);image=(out/'shift.bin').read_bytes();symbols={p[2].lstrip('.'):int(p[1],16)for line in(out/'shift.lbl').read_text().splitlines()if(p:=line.split())and p[0]=='al'};dll=grid.runner(out);m=Machine();rng=random.Random(0x574150);cases=[]
 def read(a,n):b=C.create_string_buffer(n);dll.gm_read(m.handle,a,n,b);return b.raw
 def bits(v):return[(v>>(7-b))&1 for b in range(8)]
 def packed(v):return bytes(sum(v[i+j]<<(7-j)for j in range(8))for i in range(0,len(v),8))
 try:
  for width in(60,80):
   pitch=5 if width==60 else 4;origin=10 if width==60 else 0;mask=(0xff<<(8-pitch))&255
   for column in range(width):
    for direction in(0,1):
     for row in(0,10,21):
      canvas=bytes(rng.randrange(256)for _ in range(65536));m.load(0,canvas);m.load(0xa000,image);ink=bytes(rng.randrange(256)for _ in range(8));frame=bytes((width,row,column,direction))+ink+bytes(52);m.load(0x8d00,frame);before=read(0,65536);expected=bytearray(before);carry=[]
      for gy in range(8):
       base=0x6000+(row+2)*320;old=bytes(before[base+i*8+gy]for i in range(40));pixels=[b for v in old for b in bits(v)];end=origin+width*pitch;x=origin+column*pitch;cell=bits(ink[gy]&mask)[:pitch];carry.append(sum(pixels[end-pitch+j]<<(7-j)for j in range(pitch)))
       if direction==0:new=pixels[:x]+cell+pixels[x:end-pitch]+pixels[end:]
       else:new=pixels[:x]+pixels[x+pitch:end]+cell+pixels[end:]
       wanted=packed(new)
       for i,v in enumerate(wanted):expected[base+i*8+gy]=v
      regs,n=m.call(symbols['se_lp_shift_row']);assert not regs.p&1,(width,row,column,direction,'return');after=read(0,65536);assert after[0x8d0c:0x8d14]==bytes(carry),(width,row,column,direction,'normalizedcarry')
      # Only declaredframe/scratch/borrowedpointer/CPUstack+one320B tile-row.
      for a,z in[(4,6),(0x100,0x200),(0x8000,0x8028),(0x8d00,0x8d40)]:expected[a:z]=after[a:z]
      assert bytes(expected)==after,(width,row,column,direction,'fullRAM/pixels',[(hex(i),a,b)for i,(a,b)in enumerate(zip(expected,after))if a!=b][:4])
      cases.append(dict(width=width,column=column,row=row,direction=direction,instructions=n))
  faults=[]
  for frame in[bytes((40,0,0,0)),bytes((61,0,0,0)),bytes((80,22,0,0)),bytes((80,255,0,0)),bytes((80,0,80,0)),bytes((60,0,60,0)),bytes((80,0,0,2))]:
   m.load(0x8d00,frame+bytes(60));before=read(0,65536);r,n=m.call(symbols['se_lp_shift_row']);after=read(0,65536);wanted=bytearray(before);wanted[0x100:0x200]=after[0x100:0x200];assert r.p&1 and r.a==0x7b and bytes(wanted)==after,'refusalbeforewrites';faults.append(frame.hex())
  result=dict(status='passed',payload=len(image),cases=len(cases),faults=faults,instructions=dict(min=min(c['instructions']for c in cases),max=max(c['instructions']for c in cases),mean=sum(c['instructions']for c in cases)/len(cases)),scope='Pure caret-free same-role per-row primitive. No source/cache authority or editor integration yet.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True);return result
 finally:m.close()
if __name__=='__main__':
 out=ROOT/'build/grid-wrapped-shift'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
