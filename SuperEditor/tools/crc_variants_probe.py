"""Execute CRC machine code and audit exact NMOS6510 instruction-cycle costs.

The existing Peddle wrapper's clock is calibrated separately: its stepping path
executes cycles but never advances the exposed clock. The audit is explicit,
not a fabricated runtime cycle counter. It includes RTS and indexed read stalls;
it excludes the caller's JSR (reported separately) and external VIC/REU stalls.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
# (opcode length, NMOS6502/6510 cycles), only legal opcodes in these routines.
FIXED={0x4D:(3,4),0x8D:(3,4),0x4A:(1,2),0xAA:(1,2),0x8A:(1,2),
       0x0A:(1,2),0xAD:(3,4),0x60:(1,6),0x29:(2,2),0x48:(1,3),
       0x68:(1,4),0xEA:(1,2),0xA9:(2,2)}
INDEXED={0x5D:(3,4),0xBD:(3,4)}
class CRCProbe:
 def __init__(self):
  self.s={p[2].lstrip('.'):int(p[1],16) for line in (ROOT/'build/crc_variants/probe.lbl').read_text().splitlines() if (p:=line.split()) and p[0]=='al'}
  self.m=Machine();self.m.load(0x8000,(ROOT/'build/crc_variants/probe.bin').read_bytes())
 def close(self):self.m.close()
 def read(self,address,count):return bytes(self.m.read(address+i) for i in range(count))
 def value(self):return int.from_bytes(self.read(self.s['crc_value'],2),'little')
 def call(self,name,a=0,seed=None,y=0x5A,carry=0,sp=0xFD,decimal=0,trace=False):
  if seed is not None:self.m.load(self.s['crc_value'],seed.to_bytes(2,'little'))
  for field,value in [('a',a),('x',0xA7),('y',y),('p',0x24|carry|(decimal<<3)),('sp',sp),('pc',self.s[name])]:
   getattr(self.m.lib,'zeropage_peddle_set_'+field)(self.m.handle,value)
  self.m.write(0x100+((sp+1)&255),0xFE);self.m.write(0x100+((sp+2)&255),0x02)
  before=self.m.regs();cycles=count=0;crossings=0;log=[]
  while (regs:=self.m.regs()).pc!=0x02FF:
   assert count<80,hex(regs.pc)
   opcode=self.m.read(regs.pc)
   if opcode in INDEXED:
    length,cost=INDEXED[opcode];base=self.m.read(regs.pc+1)|(self.m.read(regs.pc+2)<<8)
    cross=int((base&255)+regs.x>255);cost+=cross;crossings+=cross
   else:length,cost=FIXED[opcode]
   if trace:log.append(dict(pc=regs.pc,opcode=opcode,bytes=self.read(regs.pc,length).hex(),x=regs.x,sp=regs.sp,a=regs.a,cycles=cost))
   cycles+=cost;count+=1;self.m.lib.zeropage_peddle_step_instruction(self.m.handle)
  assert int(regs.instructions)-int(before.instructions)==count
  return dict(regs=regs,instructions=count,audited_cycles=cycles,indexed_read_crossings=crossings,
              exposed_clock_delta=int(regs.cycles)-int(before.cycles),trace=log)
