from pathlib import Path
P=Path(__file__).resolve().parent
import ctypes as C
from setup_observer import SetupObserver
import json,hashlib
r=(P/"OBSERVER_BINDING.json").read_bytes();contract=SetupObserver(r,hashlib.sha256(r).hexdigest(),{n:(P/"observer_inputs"/n).read_bytes()for n in json.loads(r)["files"]});files=contract.files
class Regs(C.Structure):_fields_=[('pc',C.c_uint16),('sp',C.c_uint8),('a',C.c_uint8),('x',C.c_uint8),('y',C.c_uint8),('p',C.c_uint8),('cycles',C.c_uint64),('instructions',C.c_uint64)]
class Result(C.Structure):_fields_=[('regs',Regs),('status',C.c_uint),('stack',C.c_uint8)]
L=C.CDLL(str(P/'observer_inputs/model.dylib'));v=C.c_void_p;u8=C.c_uint8;u16=C.c_uint16;u32=C.c_uint32;u64=C.c_uint64
for n,r,a in [('dos64_create',v,[]),('dos64_destroy',None,[v]),('dos64_load',None,[v,u16,v,C.c_size_t]),('dos64_peek',u8,[v,u16]),('dos64_poke',None,[v,u16,u8]),('dos64_set_regs',None,[v,Regs]),('dos64_get_regs',Regs,[v]),('dos64_step',None,[v]),('dos64_run',Result,[v,u16,u64]),('dos64_uci_model_enable',None,[v,u16,u32,u8]),('bulk_model_commands',u32,[v]),('dos64_cia_clock_advance',None,[v,u32])]:f=getattr(L,n);f.restype=r;f.argtypes=a
for n in ['native_runtime_control_enable','dos64_graphics_color_enable','dos64_cia_clock_enable','dos64_native_display_enable','dos64_host_input_model_enable','dos64_enable_reu','bulk_model_enable']:getattr(L,n).argtypes=[v]
class M:
 def __init__(self):
  self.m=L.dos64_create();b=files['setup.prg'];L.dos64_load(self.m,0x801,b[2:],len(b)-2)
  for n in ['native_runtime_control_enable','dos64_graphics_color_enable','dos64_cia_clock_enable','dos64_native_display_enable','dos64_host_input_model_enable','dos64_enable_reu','bulk_model_enable']:getattr(L,n)(self.m)
  L.dos64_uci_model_enable(self.m,0xdf1c,3,0xc9);L.dos64_poke(self.m,0,0x2f);L.dos64_poke(self.m,1,0x37);L.dos64_set_regs(self.m,Regs(0x80d,0xfd,0,0,0,0x24,0,0))
 def close(self):L.dos64_destroy(self.m)
 def ram(self):return bytes(L.dos64_peek(self.m,a)for a in range(65536))
 def loop(self):
  for i in range(3000):
   r=L.dos64_run(self.m,contract.at('setup_loop'),40000000);assert r.status in[0,2]and r.regs.pc==contract.at('setup_loop'),(r.status,hex(r.regs.pc));b=self.ram()
   if b[contract.p('coordinator','state')]==2:return b,i
   L.dos64_step(self.m);L.dos64_cia_clock_advance(self.m,1024)
  raise AssertionError('Actual startup bounded3000 loops')
