"""Execute the actual guest probe; inject only the two ROM file transports.

The native VICE test remains the authority for disk/ROM/IRQ behavior. This CPU
run predicts telemetry and inspects the same assembled guest control sequence.
"""
import hashlib
import json
from pathlib import Path
from peddle import Machine
from overlays import HEADER
ROOT=Path(__file__).resolve().parents[1]

def run_probe(banks=8):
 report=json.loads((ROOT/'build/history-probe-report.json').read_text());s=report['symbols'];m=Machine()
 try:
  m.load(0x801,(ROOT/'build/history-probe.prg').read_bytes()[2:]);m.call(s['se_clear_state']);m.load(s['se_reu_banks'],banks.to_bytes(2,'little'))
  shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim)
  for name,value in [('a',0),('x',0),('y',0),('p',0x24),('sp',0xFD),('pc',s['se_history_probe'])]:getattr(m.lib,'zeropage_peddle_set_'+name)(m.handle,value)
  m.write(0x1FE,0xFE);m.write(0x1FF,0x02);steps=0;imports=[]
  while m.regs().pc!=0x02FF:
   regs=m.regs()
   if regs.pc==s['import']:
    address=regs.x|(regs.y<<8);filename=bytes(m.read(address+i) for i in range(regs.a)).decode('ascii').lower()
    assert filename in ['hedit','hplay']
    image=(ROOT/f'build/overlays/{filename}.seo').read_bytes();stack=bytes(m.read(0x100+i) for i in range(256))
    m.load(s['se_overlay_header'],image[:HEADER]);m.load(0x5000,image[HEADER:]);result,_=m.call(s['se_overlay_import'])
    assert not result.p&1,(filename,hex(result.a))
    m.load(0x100,stack);return_pc=(stack[(regs.sp+1)&255]|(stack[(regs.sp+2)&255]<<8))+1
    for name,value in [('a',result.a),('x',result.x),('y',result.y),('p',result.p),('sp',(regs.sp+2)&255),('pc',return_pc)]:getattr(m.lib,'zeropage_peddle_set_'+name)(m.handle,value)
    imports.append(filename)
   else:m.lib.zeropage_peddle_step_instruction(m.handle)
   steps+=1;assert steps<3_000_000,hex(m.regs().pc)
  def value(name,width):return int.from_bytes(bytes(m.read(s[name]+i) for i in range(width)),'little')
  assert value('se_h_probe_result',1)==1,(value('se_h_probe_cases',1),value('se_h_probe_error',1))
  assert value('se_h_probe_cases',1)==15
  assert bytes(m.read(0xC600+i) for i in range(1024))==shim
  result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=report['sha256'],reu_banks=banks,
   probe_cases=value('se_h_probe_cases',1),dma_calls=value('se_reu_dma_calls',2),dma_bytes=value('se_reu_dma_bytes',3),
   document_bytes=value('se_doc_length',3),document_generation=value('se_doc_generation',2),
   node=value('se_h_current',4),saved_node=value('se_h_saved',4),counter=value('se_h_counter',4),
   journal_bytes=value('se_h_end',2),cursor=value('se_h_cursor',2),dirty=value('se_h_dirty',1),
   module_loads=value('se_overlay_loads',2),module_calls=value('se_overlay_calls',2),
   source_prefix_hex=bytes(m.read(0x8000+i) for i in range(3)).hex(),injected_transport=imports,
   overlay_sha256={name:hashlib.sha256((ROOT/f'build/overlays/{name}.seo').read_bytes()).hexdigest() for name in imports},
   shim_bytes_verified=1024,limitations='ROM SEQ transport injected; native test proves actual disk/IRQ integration.')
  return result
 finally:m.close()

if __name__=='__main__':
 result=run_probe();(ROOT/'build/history-probe-cpu-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
