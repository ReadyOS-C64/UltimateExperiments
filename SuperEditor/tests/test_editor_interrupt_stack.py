"""Local IRQ/NMI stack bound on frozen editor + pinned unmodified KERNAL03.

Hardware entry is an explicit three-byte host-installed equivalent frame. Every
subsequent instruction is real ROM/editor code. Fixed CIA column samples are a
CPU path fixture, not electrical keyboard/IEC/IRQ timing emulation. Does not turn
observed foreground depth into a global foreground/IEC worst-case bound.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
BASE=ROOT/'build/geos-incremental-editor/20261025T085903355763Z/fixture'
ROM=Path('/opt/homebrew/share/vice/C64/kernal-901227-03.bin')

def run(out,base,rompath):
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];prg=(base/'build/editor.prg').read_bytes();rom=rompath.read_bytes();assert len(rom)==8192
 assert rom[0x1ffa:0x2000]==bytes.fromhex('43fee2fc48ff'),'requires stock FE43 NMI/FF48 IRQ entry'
 # Exact call/scan evidence; the short path graph is audited in the companion
 # session note, including stock scanner callback $028F=$EB48.
 for address,raw in [(0xff48,'488a489848'),(0xea81,'68a868aa6840'),(0xff9f,'4c87ea'),(0xffea,'4c9bf6'),(0xfe43,'786c1803'),(0xeaaa,'48'),(0xeab6,'48')]:
  assert rom[address-0xe000:address-0xe000+len(bytes.fromhex(raw))]==bytes.fromhex(raw),(hex(address),'ROM changed')
 m=Machine();runs=[];minimum=255;peak=None
 def regs(**values):
  for n,v in values.items():getattr(m.lib,'zeropage_peddle_set_'+n)(m.handle,v)
 def push(value):
  r=m.regs();m.write(0x100+r.sp,value);regs(sp=(r.sp-1)&255)
 def entry(vector,pc,status):
  push(pc>>8);push(pc&255);push(status&~0x10);regs(pc=m.read(vector)+256*m.read(vector+1),p=status|4)
 def setup(column,base_sp=255):
  m.load(0x100,bytes([0xa5])*256);m.load(int.from_bytes(prg[:2],'little'),prg[2:]);m.load(0xe000,rom)
  m.load(0xc600,bytes((i*73+29)&255 for i in range(1024)))
  for name in ('se_input_head','se_input_tail','se_input_nmi_pending','se_input_irq_ticks','se_input_backpressure'):m.write(s[name],0)
  m.write(s['se_input_irq_ticks']+1,0xff)
  for at,v in [(0x314,s['se_input_irq']&255),(0x315,s['se_input_irq']>>8),(0x318,s['se_input_nmi']&255),(0x319,s['se_input_nmi']>>8),(0x28f,0x48),(0x290,0xeb),(0x289,10),(0x28a,0x80),(0x28b,4),(0x28c,16),(0xc6,0),(0xdc01,column)]:m.write(at,v)
  regs(pc=0x200,sp=base_sp,p=0x20,a=0x21,x=0x43,y=0x65);entry(0xfffe,0x200,0x20)
 def interrupt_here():
  interrupted=m.regs();entry(0xfffa,interrupted.pc,interrupted.p);low=m.regs().sp;steps=0
  while True:
   low=min(low,m.regs().sp);m.lib.zeropage_peddle_step_instruction(m.handle);steps+=1;low=min(low,m.regs().sp)
   if m.regs().pc==interrupted.pc:break
   assert steps<100,'NMI did not return'
  r=m.regs();assert (r.sp,r.a,r.x,r.y,r.p&0xcf)==(interrupted.sp,interrupted.a,interrupted.x,interrupted.y,interrupted.p&0xcf)
  assert m.read(s['se_input_nmi_pending'])==1
  return low,steps
 def execute(column,inject=None,base_sp=255):
  setup(column,base_sp);low=m.regs().sp;steps=0;pcs=[];at_peak=None;nmi_steps=0
  while m.regs().pc!=0x200:
   r=m.regs();pcs.append(r.pc)
   assert r.p&4,'maskable IRQ unexpectedly enabled inside IRQ path'
   if inject==steps:
    v,n=interrupt_here();nmi_steps+=n
    if v<low:low=v;at_peak=r.pc
   r=m.regs();old=r.sp;opcode=m.read(r.pc);m.lib.zeropage_peddle_step_instruction(m.handle);steps+=1;r=m.regs()
   assert not ((opcode==0x20 and old<2)or(opcode in(0x48,0x08)and old==0)),'stack wrapped'
   if r.sp<low:low=r.sp;at_peak=pcs[-1]
   assert steps<5000,('IRQ stalled',column,hex(r.pc))
  r=m.regs();assert(r.sp,r.a,r.x,r.y)==(base_sp,0x21,0x43,0x65)
  assert bytes(m.read(0xc600+i)for i in range(1024))==bytes((i*73+29)&255 for i in range(1024))
  assert bytes(m.read(0x100+i)for i in range(low+1))==bytes([0xa5])*(low+1)
  return dict(column=column,irq_instructions=steps,nmi_instructions=nmi_steps,minimum_sp=low,incremental_bytes=base_sp-low,peak_pc=at_peak),pcs
 try:
  for col in range(256):
   result,pcs=execute(col);assert result['incremental_bytes']<=10; runs.append(result)
  assert max(r['incremental_bytes']for r in runs)==10
  # Overlap at EVERY IRQ instruction boundary of the deepest fixed-matrix path,
  # including ROM prologue/helper epilogue and editor drain. Independent NMI
  # edges are serialized one per IRQ; arbitrary nested edge storms are excluded.
  worst=next(r for r in runs if r['incremental_bytes']==10);_,pcs=execute(worst['column']);overlaps=[]
  for index in range(len(pcs)):
   result,_=execute(worst['column'],index);assert result['incremental_bytes']<=16;overlaps.append(result)
  assert max(r['incremental_bytes']for r in overlaps)==16
  setup(0);regs(pc=0x200,sp=255,p=0x20)
  nmi_low,nmi_steps=interrupt_here();assert nmi_low==249 and not m.regs().p&4
  composed,_=execute(worst['column'],next(i for i,r in enumerate(overlaps)if r['incremental_bytes']==16),base_sp=0xde)
  assert composed['minimum_sp']==0xce and composed['incremental_bytes']==16
  result=dict(status='passed',fixture=str(base),resident_sha256=hashlib.sha256(prg).hexdigest(),binding=report['resident_binding']['digest'],rom_path=str(rompath),rom_sha256=hashlib.sha256(rom).hexdigest(),irq_bound=10,one_nmi_bound=6,foreground_nmi=dict(minimum_sp=nmi_low,instructions=nmi_steps,restores_I0=True),combined_incremental_bound=16,fixed_CIA_cases=runs,nmi_overlap_cases=overlaps,composed_observed_foreground_example=composed,scope='Actual ROM/editor instructions after explicit equivalent hardware entry frame; fixed CIA samples and stock scanner vector. Local additive bound only; foreground33 is historical observed depth, not static IEC/foreground maximum.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',out,'IRQ10; NMI6; one-overlap16;',len(overlaps),'boundaries',flush=True);return result
 finally:m.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--rom',type=Path,default=ROM);a=p.parse_args();out=ROOT/'build/interrupt-stack-audit'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture,a.rom)
