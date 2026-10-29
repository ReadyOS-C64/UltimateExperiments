"""Scoped authenticated C33→R25 graph and data-only CRC phase component proof."""
from pathlib import Path
import inspect,importlib.util,json,re,binascii,random
import test_grid_raw_boundary as boundary
def capture_stack(out,base):
 """Decode the real R25 bytes only in C33's authenticated direct-entry graph."""
 import test_editor_staged_stack as staged
 source=inspect.getsource(staged.original.foreground_proof);old="[(0xb000,image[36:])],Ccall)";new="[(0xb000,image[36:])]+([(0xa000,images['geostail'][36:])]if name=='grid'else[]),Ccall)";assert source.count(old)==1
 # Supply actual helper instructions, not an opaque edge or global R mapping.
 # Every other C image retains the original unknown-R-entry refusal.
 out.mkdir(parents=True);p=out/'foreground-capture.py';p.write_text(source.replace(old,new));module=type(staged.original)('capture_graph');module.__dict__.update(staged.original.__dict__);exec(compile(p.read_text(),str(p),'exec'),module.__dict__)
 prior=staged.original.foreground_proof;staged.original.foreground_proof=module.foreground_proof
 try:return staged.run(out,base,staged.original.ROM)
 finally:staged.original.foreground_proof=prior
def crc_component(out,base,labels):
 """Internal arithmetic probe only; public authority remains in public tests."""
 out.mkdir();g=boundary.raw.caret.profile.observer.Gate(out,base);f=g.f;rng=random.Random(3176)
 symbol={n:int(a,16)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',labels.read_text())};payload=(base/'build/overlays/grid.seo').read_bytes()[36:]
 try:
  # Explicit component loading cannot demonstrate public overlay admission.
  f.m.load(0xb000,payload);f.m.load(0x8d00,b'\x5a'*512);before=f.read(0,65536);r,n=f.fast_call(symbol['capture_tables']);after=f.read(0,65536);want=bytearray(before);want[0x100:0x200]=after[0x100:0x200]
  table=[binascii.crc_hqx(bytes((i,)),0)for i in range(256)];expected=bytes(x&255 for x in table)+bytes(x>>8 for x in table);want[0x8d00:0x8f00]=expected;assert after==want,'table build whole64KiB guard/independent polynomial'
  crc=f.s['se_crc_value'];cases=[]
  for i in range(132):
   packet=bytes((i,))*240 if i<4 else bytes(rng.randrange(256)for _ in range(240));f.m.load(0x88c4,packet);f.m.write(0x89c0,0);before=f.read(0,65536);r,n=f.fast_call(symbol['packet_crc']);after=f.read(0,65536);want=bytearray(before);want[0x100:0x200]=after[0x100:0x200];want[crc:crc+2]=binascii.crc_hqx(packet,65535).to_bytes(2,'little');assert after==want,(i,'CRC/all outsideRAM guard');cases.append(n)
  result=dict(status='PASS',cases=len(cases),instruction_min=min(cases),instruction_max=max(cases),phase=[0x8d00,0x8f00],scope='Internal actual6510 CRC component, independent binascii polynomial, whole64KiB guard. No public-authority claim.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
def capture_refusals(out,base):
 out.mkdir();g=boundary.raw.caret.profile.observer.Gate(out,base);f=g.f;cases=[]
 try:
  for width in(60,80):
   for name,value in [('se_f_owner',1),('se_doc_read_locks',1),('se_st_request',1),('se_e_draw_busy',1)]:
    f.source(b'Plain source.\rTail.',physical=256);f.typed(boundary.raw.caret.profile.observer.geos.native_text('syntax plain'));f.command(97 if width==60 else 98);boundary.raw.caret.profile.drain(f)
    f.put(name,value,1);phase=f.read(0x8d00,512);reu=g.reu();pixels=f.read(0x6000,8000)+f.read(0x4000,1000);f.put('se_overlay_frame',0,1);r,n=f.fast_call(f.s['se_overlay_call'],a=33,x=1)
    assert r.a==2 and not r.p&1 and f.read(0x8d00,512)==phase and g.reu()==reu and f.read(0x6000,8000)+f.read(0x4000,1000)==pixels,(width,name,'capture refusal changed borrowedphase/REU/pixels')
    f.put(name,0,1);cases.append(dict(width=width,refused=name,instructions=n))
  result=dict(status='PASS',cases=cases);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--labels',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir();crc_component(a.out/'crc',a.fixture.resolve(),a.labels.resolve());capture_stack(a.out/'stack',a.fixture.resolve())
