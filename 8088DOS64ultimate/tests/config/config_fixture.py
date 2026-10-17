from pathlib import Path
import sys,os
sys.dont_write_bytecode=True;sys.pycache_prefix=str(Path.cwd()/('.absent-test-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import ctypes as C,struct,zlib,json,unittest,hashlib
P=Path(__file__).resolve().parent;assert Path.cwd()==P
L=C.CDLL(str(P/'config-peddle.dylib'));ptr=C.c_void_p;u8=C.c_uint8;u16=C.c_uint16;u32=C.c_uint32;u64=C.c_uint64
class Regs(C.Structure):_fields_=[('pc',u16),('sp',u8),('a',u8),('x',u8),('y',u8),('p',u8),('cycles',u64),('instructions',u64)]
class Result(C.Structure):_fields_=[('regs',Regs),('status',C.c_uint),('stack',u8)]
for n,r,a in [('dos64_create',ptr,[]),('dos64_destroy',None,[ptr]),('dos64_load',None,[ptr,u16,ptr,C.c_size_t]),('dos64_peek',u8,[ptr,u16]),('dos64_poke',None,[ptr,u16,u8]),('dos64_clear_writes',None,[ptr]),('dos64_set_regs',None,[ptr,Regs]),('dos64_get_regs',Regs,[ptr]),('dos64_run',Result,[ptr,u16,u64]),('browser_bad_write',u32,[ptr,ptr]),('browser_bank',u16,[ptr]),('dos64_uci_model_enable',None,[ptr,u16,u32,u8]),('dos64_enable_reu',None,[ptr]),('bulk_model_enable',None,[ptr]),('bulk_model_seed',None,[ptr,C.c_char_p,ptr,u32]),('bulk_model_seed_open',None,[ptr,u8,C.c_char_p,u8,u32]),('bulk_model_commands',u32,[ptr]),('bulk_model_command',u8,[ptr,u32,u32]),('bulk_model_size',u32,[ptr,C.c_char_p]),('bulk_model_open',u8,[ptr,u8]),('bulk_model_read',u8,[ptr,C.c_char_p,ptr,u32]),('bulk_model_faults',None,[ptr,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int]),('dos64_cia_clock_advance',None,[ptr,u32]),('dos64_cia_clock_step',None,[ptr,u32]),('dos64_uci_model_stuck',None,[ptr,u8]),('dos64_host_input_model_keys',None,[ptr,ptr]),('fw_stop_after_error_write',None,[ptr,u16]),('dos64_reu_read',u8,[ptr,u32,ptr,C.c_size_t])]:
 f=getattr(L,n);f.restype=r;f.argtypes=a
for n in ['native_runtime_control_enable','dos64_graphics_color_enable','dos64_cia_clock_enable','dos64_native_display_enable','dos64_host_input_model_enable']:getattr(L,n).argtypes=[ptr]
def cfg(home=b'/Home',ro=0):
 b=bytearray(576);b[:7]=b'D64C\1\x40\2'
 for at,p in [(8,home),(136,b'/usb1/Media/A.IMG'),(264,b'/sd/Media/B.IMG'),(392,b'/usb1/HD/C.IMG')]:b[at:at+len(p)]=p
 b[524]=ro;b[525]=7;b[536]=1;struct.pack_into('<I',b,538,0x400000);struct.pack_into('<I',b,572,zlib.crc32(b[:572]));return bytes(b)
for n,r,a in [('dir_model_enable',None,[ptr]),('dir_model_path',None,[ptr,C.c_char_p]),('dir_model_row',None,[ptr,C.c_char_p,u8,ptr,u32]),('dir_model_fault',None,[ptr,C.c_int,C.c_int,C.c_int]),('dir_model_commands',u32,[ptr]),('dir_model_cmd_size',u32,[ptr,u32]),('dir_model_cmd_byte',u8,[ptr,u32,u32])]:
 f=getattr(L,n);f.restype=r;f.argtypes=a
REPORT={'instances':0,'max_hardware_stack':0,'max_native_call_cycles':0,'native_calls':0}
class F:
 def __init__(self,stale=(),auto=True):
  self.labels={x.split()[2].lstrip('.'):int(x.split()[1],16)for x in Path('config.labels').read_text().splitlines()if x.startswith('al ')};self.m=L.dos64_create();data=Path('config.prg').read_bytes();L.dos64_load(self.m,int.from_bytes(data[:2],'little'),data[2:],len(data)-2)
  self.guard=bytearray(65536)
  for a,n in [(0,2),(0x20,96),(0x100,256),(0xcd00,768),(0x400,1000),(0xd800,1000),(0xfffa,2),(0xc000,2048),(self.labels['__BSS_RUN__'],self.labels['__BSS_SIZE__']),(self.labels['__DEVICESTATE_RUN__'],self.labels['__DEVICESTATE_SIZE__']),(self.labels['__RIBSS_RUN__'],self.labels['__RIBSS_SIZE__']),(self.labels['__RMBSS_RUN__'],self.labels['__RMBSS_SIZE__']),(0xdf1c,2),(0xdf00,11),(0xc900,1024),(self.labels['__CONFIG_PUBSTATE_RUN__'],self.labels['__CONFIG_PUBSTATE_SIZE__']),(self.labels['_ps_color'],1),(self.labels['_br_config'],134)]:self.guard[a:a+n]=bytes([1])*n
  self.guard[0xc6]=1;self.guard[0x277:0x281]=bytes([1])*10
  for a in [0xd019,0xd01a,0xd011,0xd016,0xd018,0xd015,0xd020,0xd021,0xdc00,0xdc02,0xdc03,0xdc0d,0xdd00,0xdd02,0xdd04,0xdd05,0xdd06,0xdd07,0xdd0d,0xdd0e,0xdd0f]:self.guard[a]=1
  for n in ['uci_status_read','uci_control_write','uci_id_read','uci_command_write','uci_data_read','uci_stat_read']:self.guard[self.labels[n]+1:self.labels[n]+3]=b'\1\1'
  for n in ['dos64_uci_upload_operand','dos64_uci_drain_operand']:
   if n in self.labels:self.guard[self.labels[n]:self.labels[n]+2]=b'\1\1'
  self.guard=bytes(self.guard);self.maxstack=0;self.total=0
  for n in ['native_runtime_control_enable','dos64_graphics_color_enable','dos64_cia_clock_enable','dos64_native_display_enable','dos64_host_input_model_enable']:getattr(L,n)(self.m)
  L.dos64_uci_model_enable(self.m,0xdf1c,3,0xc9);L.bulk_model_enable(self.m);L.dos64_enable_reu(self.m)
  self.initial_guard=bytes(self.guard)
  self.guard=bytearray(self.guard);a=self.labels['__CONFIG_HIGH_RUN__'];n=self.labels['__CONFIG_HIGH_TOTAL__'];self.guard[a:a+n]=bytes([1])*n;self.guard=bytes(self.guard)
  if '__FD_SAFE_RUN__'in self.labels:
   self.guard=bytearray(self.guard);a=self.labels['__FD_SAFE_RUN__'];n=self.labels['__FD_SAFE_SIZE__'];self.guard[a:a+n]=bytes([1])*n;self.guard=bytes(self.guard)
  if auto:self.call('runtime_init',budget=20000000)
  self.guard=self.initial_guard
  for t in stale:L.bulk_model_seed(self.m,b'/Old',b'UNCHANGED',9);L.bulk_model_seed_open(self.m,t,b'/Old',3,7)
  L.dir_model_enable(self.m)
  if auto:assert self.call('_cg_boot')==1
 def close(self):REPORT['instances']+=1;L.dos64_destroy(self.m)
 def read(self,n,c):return bytes(L.dos64_peek(self.m,self.labels[n]+i)for i in range(c))
 def write(self,n,b):L.dos64_load(self.m,self.labels[n],b,len(b))
 def call(self,n,a=0x71,budget=10000000):
  L.dos64_clear_writes(self.m);ret=self.labels['fixture_return']-1;L.dos64_poke(self.m,0x1ff,ret>>8);L.dos64_poke(self.m,0x1fe,ret&255);before=L.dos64_get_regs(self.m).cycles;L.dos64_set_regs(self.m,Regs(self.labels[n],0xfd,a,0x82,0x93,0x24,0,0));r=L.dos64_run(self.m,self.labels['fixture_return'],budget)
  assert r.status==0,(n,r.status,hex(r.regs.pc),r.regs.cycles);assert L.browser_bad_write(self.m,self.guard)==65536,(n,hex(L.browser_bad_write(self.m,self.guard)));assert self.read('sp',2)==b'\xff\xcf';assert r.stack<120;self.maxstack=max(self.maxstack,r.stack);self.total+=r.regs.cycles-before;REPORT['native_calls']+=1;REPORT['max_hardware_stack']=max(REPORT['max_hardware_stack'],r.stack);REPORT['max_native_call_cycles']=max(REPORT['max_native_call_cycles'],r.regs.cycles-before);return r.regs.a
 def start(self,data=None,home=b'/Home',timeout=1000):
  if data is None:data=cfg(home)
  L.bulk_model_seed(self.m,home+b'/DOS64.CFG',data,len(data));self.write('_ri_request',b'\xa5'+struct.pack('<IH',0x400000,timeout)+home.ljust(128,b'\0'));return self.call('_ri_begin')
 def poll(self):L.dos64_cia_clock_advance(self.m,1024);self.call('_ri_poll');return self.call('_ri_state')
 def finish(self):
  for i in range(5000):
   if self.call('_ri_state')!=1:return self.call('_ri_state')
   self.poll()
  raise AssertionError('bounded terminal')
 def result(self):return self.read('_ri_result',8)
 def query(self,home=b'/Home',session=1):self.write('_ri_query_home',home.ljust(128,b'\0'));self.write('_ri_query_session',struct.pack('<H',session));return self.call('_ri_get')
 def commands(self):return [bytes(L.bulk_model_command(self.m,i,j)for j in range(2))for i in range(L.bulk_model_commands(self.m))]
