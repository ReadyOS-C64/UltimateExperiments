import sys,os
from pathlib import Path
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.pycache_prefix=str(P/('.absent-start-cache-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import ctypes as C,struct,zlib,json,hashlib,unittest,time
from test_actual import L,bind,ptr,u8,u16,u32,u64,Regs
from test_controller import ROOT,HOME,A,B,cfg,release_fixture
from dos_lane import Lane,MAIN
bind('dos64_graphics_color_enable',None,[ptr]);bind('dos64_get_regs',Regs,[ptr]);bind('dos64_cia_clock_enable',None,[ptr]);bind('dos64_native_display_enable',None,[ptr]);bind('dos64_host_input_model_enable',None,[ptr]);bind('native_runtime_control_enable',None,[ptr]);bind('native_runtime_require_nmi_order',None,[ptr,u16]);bind('native_runtime_nmi_checked',u8,[ptr]);bind('lc_clock_model_ratio',None,[ptr,u32]);bind('lc_nmi_at_pc',None,[ptr,u16]);bind('lc_nmi_count',u32,[ptr]);bind('lc_final_dma_nmi_arm',None,[ptr]);bind('lc_final_dma_seen',u32,[ptr]);bind('lc_nmi_vector_index',u16,[ptr,u8]);bind('lc_nmi_opcode_index',u8,[ptr,u8]);bind('bulk_model_open',u8,[ptr,u8]);bind('lc_check_writes',u32,[ptr,ptr]);bind('dos64_clear_writes',None,[ptr])
SYMS={l.split()[2].lstrip('.'):int(l.split()[1],16) for l in (P/'controller.labels').read_text().splitlines() if l.startswith('al ')}
REPORT={}
def sha(b):return hashlib.sha256(b).hexdigest()
class Start:
 def __init__(self,owner=0xff,home=HOME,base=0xdf1c):
  self.m=L.dos64_create();self.labels=SYMS;self.a=self.b=None
  self.template=(P/'controller.prg').read_bytes();assert self.template[:14]==b'\x01\x08\x0b\x08\x0a\x00\x9e2061\x00\x00\x00'
  self.prg=bytearray(self.template);at=self.at('_lc_control')-0x0801+2
  patch=bytes([owner])+struct.pack('<H',base)+home.ljust(128,b'\0');assert len(patch)==131
  self.prg[at:at+131]=patch
  assert self.prg[:at]==self.template[:at] and self.prg[at+131:]==self.template[at+131:]
  # Generate persistent-home DATA before native startup, never only in REU/BSS.
  L.dos64_load(self.m,0x0801,bytes(self.prg[2:]),len(self.prg)-2)
  L.dos64_load(self.m,0x8000,b'\xa5'*8192,8192)
  L.dos64_poke(self.m,0,0x2f);L.dos64_poke(self.m,1,0x37)
  L.dos64_enable_reu(self.m);L.dos64_uci_model_enable(self.m,0xdf1c,3,0xc9);L.bulk_model_enable(self.m)
  L.dos64_graphics_color_enable(self.m);L.dos64_cia_clock_enable(self.m);L.dos64_native_display_enable(self.m);L.dos64_host_input_model_enable(self.m);L.native_runtime_control_enable(self.m);L.lc_clock_model_ratio(self.m,64)
  L.native_runtime_require_nmi_order(self.m,self.at('ps_rti'))
  guard=self.template[self.at('_ps_guard')-0x0801+2:];offset=guard.index(b'\xa9\x35\x85\x01\x60')+4
  L.lc_nmi_at_pc(self.m,self.at('_ps_guard')+offset)
  L.dos64_clear_writes(self.m);L.dos64_set_regs(self.m,Regs(2061,0xff,0,0,0,0x24,0,0))
 def at(self,n):return self.labels[n]
 def byte(self,n):return L.dos64_peek(self.m,self.at(n))
 def read(self,n,count):return bytes(L.dos64_peek(self.m,self.at(n)+i) for i in range(count))
 def seed(self,b,addr):L.bulk_reu_seed(self.m,addr,b,len(b))
 def reu(self,a,n):b=C.create_string_buffer(n);assert L.dos64_reu_read(self.m,a,b,n);return b.raw
 def seedfiles(self,both=True,bad_main=False):
  refs=sorted((ROOT/'reference').glob('*.img'));self.a=refs[0].read_bytes();self.b=refs[1].read_bytes() if both else None
  main,rel=release_fixture();config=bytearray(cfg(self.a,self.b));config[392:520]=bytes(128);config[522]=0;config[524]=3 if both else 1;config[525]=3 if both else 1;struct.pack_into('<I',config,572,zlib.crc32(config[:572]))
  if bad_main:main=main[:100]+bytes([main[100]^1])+main[101:]
  for name,b in [(HOME+b'/DOS64.CFG',bytes(config)),(HOME+b'/DOS64.REL',rel),(HOME+b'/DOS64.PRG',main),(A,self.a)]+([(B,self.b)] if both else []):L.bulk_model_seed(self.m,name,b,len(b))
  self.config=bytes(config);self.main=main;return main,rel
 def run(self,sentinel,budget=600_000_000):return L.dos64_run(self.m,sentinel,budget)
 def screen(self):return bytes(L.dos64_peek(self.m,0x0400+i) for i in range(1000))
 def close(self):L.dos64_destroy(self.m)
 def startup_guard(self):
  smc=set()
  for n in ['uci_status_read','uci_control_write','uci_id_read','uci_command_write','uci_data_read','uci_stat_read','read','store']:smc.update([self.at(n)+1,self.at(n)+2])
  bs=self.at('__BSS_RUN__');be=self.at('__DEVICESTATE_RUN__')+self.at('__DEVICESTATE_SIZE__')
  allowed=lambda a:a in [0,1,0xfffa,0xfffb,0x5882,self.at('sf_entered'),self.at('_ps_color')] or 0x20<=a<0x3e or 0x100<=a<0x300 or 0x400<=a<0x7e8 or bs<=a<be or self.at('_br_config')<=a<self.at('_br_config')+134 or self.at('__PRELAUNCH_RUN__')<=a<self.at('__PRELAUNCH_RO_RUN__')+self.at('__PRELAUNCH_RO_SIZE__') or 0xcd00<=a<0xd000 or 0xc000<=a<0xc800 or 0xc900<=a<0xcd00 or 0xd800<=a<0xdbe8 or 0xdf00<=a<=0xdf0a or a in [0xdf1c,0xdf1d,0xd019,0xd01a,0xd011,0xd016,0xd018,0xd015,0xd020,0xd021,0xdc00,0xdc02,0xdc03,0xdc0d,0xdd00,0xdd02,0xdd04,0xdd05,0xdd06,0xdd07,0xdd0d,0xdd0e,0xdd0f] or a in smc
  mask=bytes(int(allowed(a)) for a in range(65536));bad=L.lc_check_writes(self.m,mask);assert bad==65536,('unexpected START RAM write',hex(bad))
class ActualStart(unittest.TestCase):
 def tearDown(self):
  if hasattr(self,'f'):self.f.close()
 def stopped(self,owner=0xff,home=HOME,base=0xdf1c,bad=False):
  f=self.f=Start(owner,home,base)
  if bad:f.seedfiles(False,True)
  r=f.run(SYMS['sf_entry_idle']);assert r.status==0,(r.status,hex(r.regs.pc));f.startup_guard()
  assert f.byte('_sf_status')==3 and L.native_runtime_nmi_checked(f.m)==1
  assert L.lc_nmi_count(f.m)==1 and L.lc_nmi_vector_index(f.m,0)==f.at('ps_rti') and L.lc_nmi_opcode_index(f.m,0)==0x40
  REPORT[self._testMethodName]={'status':'PASS_ACTUAL_BASIC_SYS_ENTRY_REFUSAL','wire':L.bulk_model_commands(f.m),'screen_codes_hex':f.screen().hex(),'sf_error':f.byte('_sf_error'),'lc_result':f.read('_lc_result',16).hex(),'nmi':1}
  return f
 def test_disabled_template_actual_SYS_screen_no_file_IO(self):
  f=self.stopped();self.assertEqual(L.bulk_model_commands(f.m),0);self.assertEqual(f.read('_lc_control',1),b'\xff')
  expected=b'R\x15\x0e SETUP.';self.assertEqual(f.screen()[80:80+len(expected)],expected)
 def test_bad_absolute_path_actual_SYS_before_file_IO(self):
  f=self.stopped(0xa5,b'/usb1//wrong');self.assertEqual(L.bulk_model_commands(f.m),0)
 def test_bad_base_actual_SYS_before_file_IO(self):
  f=self.stopped(0xa5,base=0xdf20);self.assertEqual(L.bulk_model_commands(f.m),0)
 def test_main_CRC_failure_actual_SYS_closes_no_handoff(self):
  f=self.stopped(0xa5,bad=True);self.assertEqual(L.bulk_model_commands(f.m),14);self.assertEqual(f.read('_lc_result',3),b'\x03\x04\0');self.assertEqual(L.bulk_model_open(f.m,1),0);self.assertEqual(f.reu(0x3ff005,1),b'\0')
 def test_generated_persistent_home_SYS_dynamic_handoff_real_DOS(self):
  f=self.f=Start(0xa5);main,rel=f.seedfiles(True);L.lc_final_dma_nmi_arm(f.m)
  r=f.run(SYMS['trampoline_start']);assert r.status in [0,2] and r.regs.pc==0x0200,(r.status,hex(r.regs.pc))
  f.startup_guard();assert f.byte('_sf_status')==2 and f.read('_lc_result',2)==b'\x05\0'
  assert f.read('_lc_control',131)==bytes([0xa5])+struct.pack('<H',0xdf1c)+HOME.ljust(128,b'\0')
  staged=f.reu(0x3e0000,len(main));screen=f.screen();assert L.bulk_model_commands(f.m)==22 and L.bulk_model_open(f.m,1)==0
  assert bytes(L.dos64_peek(f.m,SYMS['dma_fields']+i) for i in range(2))==rel[16:18]
  assert bytes(L.dos64_peek(f.m,SYMS['dma_fields']+5+i) for i in range(2))==rel[18:20]
  for sym,offset in [('main_start_operand',20),('main_loop_operand',22),('checked_main_idle',24)]:assert bytes(L.dos64_peek(f.m,SYMS[sym]+i) for i in range(2))==rel[offset:offset+2]
  r=f.run(SYMS['trampoline_loaded'],20_000);assert not r.status,(r.status,hex(r.regs.pc))
  assert bytes(L.dos64_peek(f.m,0x0801+i) for i in range(len(main)-2))==staged[2:]
  assert L.lc_nmi_count(f.m)==2 and [L.lc_nmi_vector_index(f.m,i) for i in range(2)]==[SYMS['ps_rti'],0x5882]
  r=f.run(MAIN['dos64_native_loop']);assert not r.status,(r.status,hex(r.regs.pc))
  assert L.dos64_peek(f.m,MAIN['dos64_native_diag'])==4 and f.reu(0x3ff005,1)==b'\0'
  L.lc_clock_model_ratio(f.m,0);lane=Lane(f,f.a);result=lane.run()
  assert f.reu(0x100000,len(f.a))==f.a and f.reu(0x180000,len(f.b))==f.b and L.bulk_model_commands(f.m)==22
  result.update({'START_template_sha256':sha(f.template),'generated_START_sha256':sha(f.prg),'persistent_home_survives_poisoned_BSS':True,'BASIC_SYS_entry':2061,'entry_execution':'decoded actual BASIC SYS line, executed linked startup; no BASIC/KERNAL ROM interpreter modeled','dynamic_fields_from_checked_descriptor':True,'startup_screen_codes_hex':screen.hex(),'nmi_vectors':[SYMS['ps_rti'],0x5882],'nmi_delivered':2,'wire_commands':22})
  REPORT[self._testMethodName]=result
if __name__=='__main__':
 t=time.monotonic();r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ActualStart));REPORT['elapsed_seconds']=time.monotonic()-t
 (P.parent/'START_RESULTS.json').write_text(json.dumps(REPORT,indent=2)+'\n');sys.exit(not r.wasSuccessful())
