"""Private selector-union primitive: exact fullrow oracle + all64KiB guards.

This disposable executable probes the same included xor_changes/xor_cell code.
It supplies certified changed-cell lists explicitly; actual source/guard/root
integration is independently exercised by test_grid_caret_candidate_integration.
No production/shared build/native. No font cache/table/new persistent state.
"""
from pathlib import Path
from datetime import datetime,timezone
import ctypes as C,hashlib,json,random,subprocess,sys
import test_narrow_rows as oracle
import test_fold_retention as retention
from peddle import Machine
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/geos-incremental-editor/20261025T140326098391Z/fixture'
def run(out):
 source=ROOT/'src/render/grid/caret-candidate/xor/paint.s';asm=out/'probe.s';asm.write_text('''.setcpu "6502"
.export xor_changes,xor_cell
.exportzp text_ptr,screen_ptr
text_ptr=$02
screen_ptr=$04
NC_C=$89C0
C=NC_C
P=$88C4
PTR=C+6
W=C+1
ROW=C+3
.segment "CODE"
'''+source.read_text());obj=out/'probe.o';subprocess.run(['ca65','-g','-o',obj,asm],check=True);cfg=out/'probe.cfg';cfg.write_text('MEMORY {IMAGE:file=%O,start=$2000,size=$1000;} SEGMENTS {CODE:load=IMAGE,type=ro;RODATA:load=IMAGE,type=ro,optional=yes;}');subprocess.run(['ld65','-C',cfg,'-o',out/'probe.bin','-Ln',out/'probe.lbl',obj],check=True)
 symbols={p[2].lstrip('.'):int(p[1],16) for l in (out/'probe.lbl').read_text().splitlines() if len(p:=l.split())==3 and p[0]=='al'};dll=retention.runner(out);m=Machine();rng=random.Random(905211);cases=[]
 def read(a,n):b=C.create_string_buffer(n);dll.gm_read(m.handle,a,n,b);return b.raw
 def reu():b=C.create_string_buffer(16*1024*1024);dll.gm_reu(m.handle,len(b),b);return b.raw
 def call(addr):
  for n,v in [('pc',addr),('sp',0xfd),('p',0x24),('a',0),('x',0),('y',0)]:getattr(m.lib,'zeropage_peddle_set_'+n)(m.handle,v)
  m.write(0x1fe,0xfe);m.write(0x1ff,2);count=dll.gm_run(m.handle,1000000);assert count and not m.regs().p&1;return count
 try:
  # Real6510 processor port setup: RAM glyphs/bitmap, visible I/O.
  m.load(0x800,bytes.fromhex('a92f8500a936850160'));call(0x800)
  canonical=bytes((i*73+19)&255 for i in range(65536));code=(out/'probe.bin').read_bytes();initialREU=reu();palette=bytes([1,3,7,10,14,1,1,7,13,5,15,7,3,1]);maxTiles=0
  for width in (60,80):
   font=(BASE/'fonts'/('narrow5.bin' if width==60 else 'narrow4.bin')).read_bytes();pitch=5 if width==60 else 4;origin=10 if width==60 else 0
   vectors=[(old,(old+1)%width) for old in range(width)]+[(old,(old-1)%width)for old in range(width)]+[(rng.randrange(width),rng.randrange(width))for _ in range(50)]
   for k,(old,new) in enumerate(vectors):
    row=(0,1,10,21)[k%4];chars=bytes(rng.randrange(256)for _ in range(width));roles=bytes(rng.randrange(14)for _ in range(width));baseflags=bytes(rng.randrange(4)for _ in range(width));oldflags=bytearray(baseflags);newflags=bytearray(baseflags);oldflags[old]|=4;newflags[new]|=4
    oldbits,oldattrs=oracle.oracle(width,chars,roles,oldflags,palette,6,0,font);newbits,newattrs=oracle.oracle(width,chars,roles,newflags,palette,6,0,font)
    changed=[i for i in range(width) if bool(oldflags[i]&6)!=bool(newflags[i]&6)];assert len(changed)<=2
    m.load(0,canonical);m.load(0x2000,code);m.load(0xa800,font);m.load(0x6000+(row+2)*320,oldbits);m.load(0x4000+(row+2)*40,oldattrs);m.write(0x89c1,width);m.write(0x89c3,row);m.load(0x89c6,(0x88c4).to_bytes(2,'little'));m.write(0x89ec,len(changed));m.load(0x89ee,bytes(changed));before=read(0,65536)
    n=call(symbols['xor_changes']);after=read(0,65536);expected=bytearray(before);expected[0x6000+(row+2)*320:0x6000+(row+3)*320]=newbits;expected[0x4000+(row+2)*40:0x4000+(row+3)*40]=newattrs
    # All actual outputs are the mathematically affected mask bytes; every
    # other byte except borrowedZP/CPUstack/privateCOWscratch must be identical.
    for a,z in [(2,6),(0x100,0x200),(0x89c0,0x8a00)]:expected[a:z]=after[a:z]
    assert after==expected,(width,k,old,new,[(hex(i),a,b)for i,(a,b)in enumerate(zip(after,expected))if a!=b][:10])
    tiles=set(t for c in changed for t in range((origin+c*pitch)//8,(origin+c*pitch+pitch-1)//8+1));maxTiles=max(maxTiles,len(tiles));cases.append(dict(width=width,row=row,old=old,new=new,cells=len(changed),tiles=len(tiles),instructions=n))
  assert reu()==initialREU,'whole16MiB unchanged';assert maxTiles>=3,'exercise real60-column3tile counterexample'
  result=dict(status='passed',cases=len(cases),max_tiles_per_row=maxTiles,payload=len(code),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),instructions=dict(min=min(c['instructions']for c in cases),max=max(c['instructions']for c in cases)),vectors=cases,scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='vectors'},indent=2),flush=True);return result
 finally:m.close()
if __name__=='__main__':
 out=ROOT/'build/grid-caret-xor-unit'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
