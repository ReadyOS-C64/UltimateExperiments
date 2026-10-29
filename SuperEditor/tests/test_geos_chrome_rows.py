"""PrivateactualR27row4/C16threechrome rows; exactRAM/body/source/REU guard."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,ctypes as C,importlib.util,hashlib,re
import test_geos_preview_editor as public
ROOT=public.ROOT;D=ROOT/'src/render/geos/chrome-row-candidate'
from peddle import Machine

def build(out,base,candidate=True):
 spec=importlib.util.spec_from_file_location('rowbuild',D/'build.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m.build(out,base,candidate)

def run(out,base,smoke=False):
 frozen,identity=public.geos.freeze(out,base);budget=build(out/'leaf',frozen);public.geos.grid.editor_fixture.ROOT=public.geos.grid.cpu_editor.ROOT=frozen;public.geos.grid.editor_fixture.NAMES=public.geos.grid.cpu_editor.NAMES=identity['names'];dll=public.geos.grid.runner(out);m=Machine();s=json.loads((frozen/'build/editor-report.json').read_text())['symbols'];labels={n:int(a,16)for a,n in re.findall(r'al ([\da-fA-F]+) \.(\w+)',(out/'leaf/r27.lbl').read_text())};font=(frozen/'fonts/native8.bin').read_bytes();m.load(0,bytes((i*73+19)&255 for i in range(65536)));prg=(frozen/'build/editor.prg').read_bytes();m.load(int.from_bytes(prg[:2],'little'),prg[2:]);m.load(0xa000,(out/'leaf/r27.bin').read_bytes());m.load(0x4800,font);calls=valid=invalid=foreign=total=0
 def read(at,n):
  raw=C.create_string_buffer(n);dll.gm_read(m.handle,at,n,raw);return raw.raw
 def reu():
  raw=C.create_string_buffer(16*1024*1024);dll.gm_reu(m.handle,len(raw),raw);return raw.raw
 def row(owner,physical,value=65,color=1):
  nonlocal calls,valid,invalid,foreign,total
  okay=owner<2 and physical in(0,1,24);codes=bytes((value+c*13)&255 for c in range(40));colors=bytes(0xf0|((color+c)&15)for c in range(40))
  if physical in(0,1,24):m.load(0x4000+physical*40,codes);m.load(0xd800+physical*40,colors)
  m.write(s['se_f_owner'],owner);m.load(s['se_overlay_frame'],bytes((4,physical,0xa7,0x5a)));before=read(0,65536)
  for n,v in [('pc',labels['entry']),('sp',0xfd),('p',0x24),('a',0xa5),('x',0x5a),('y',0x55)]:getattr(m.lib,'zeropage_peddle_set_'+n)(m.handle,v)
  m.write(0x1fe,0xfe);m.write(0x1ff,2);used=dll.gm_run(m.handle,200000);assert used;total+=used;calls+=1;after=read(0,65536);want=bytearray(before);want[0x100:0x200]=after[0x100:0x200];r=m.regs();assert r.sp==255 and after[0x100:0x140]==before[0x100:0x140],'stackbalance/lower64canary'
  if okay:
   valid+=1;assert r.a==0 and not r.p&1
   want[0x4000+physical*40:0x4000+(physical+1)*40]=bytes(((c&15)<<4)|6 for c in colors)
   want[0x6000+physical*320:0x6000+(physical+1)*320]=b''.join(bytes(b^(255 if code&128 else 0)for b in font[(code&127)*8:(code&127)*8+8])for code in codes)
   for at,n in[(s['text_ptr'],2),(s['screen_ptr'],2),(0xcfe2,3)]:want[at:at+n]=after[at:at+n]
   assert m.read(0xcfe2)==40
  else:
   if owner>=2:foreign+=1;error=0xb2
   else:invalid+=1;error=0x90
   assert r.a==error and r.p&1,(owner,physical,r.a,r.p)
  assert after==want,('fullRAM',owner,physical,next((hex(i),a,b)for i,(a,b)in enumerate(zip(after,want))if a!=b))
 try:
  oldreu=reu()
  for r in(0,1,24):row(0,r,255,15);row(1,r,0,0)
  print('FIRST6ROWPASS',budget,flush=True)
  if not smoke:
   for value in range(256):
    for color in range(16):row(value&1,(0,1,24)[(value+color)%3],value,color)
   for physical in range(256):
    if physical not in(0,1,24):row(physical&1,physical)
   for owner in range(2,256):row(owner,255)
  assert reu()==oldreu,'whole16MiBREUchanged'
  result=dict(status='passed',budget=budget,calls=calls,valid=valid,invalid=invalid,foreign=foreign,instructions=total,wholeREU_sha256=hashlib.sha256(oldreu).hexdigest(),scope='ActualR27op4 allraw/inverseglyphs/colorpairs/40columns/3rows andowner0/1;invalidrows/foreignownersopaque;full64KiBRAMeverycallincludingbody/shim/font/source andwhole16MiBREUunchanged. No nativeperformanceclaim.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,flush=True)
 finally:m.close()
if __name__=='__main__':
 out=ROOT/'build/geos-chrome-rows'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out,Path(sys.argv[1]).resolve(),'--smoke'in sys.argv)
