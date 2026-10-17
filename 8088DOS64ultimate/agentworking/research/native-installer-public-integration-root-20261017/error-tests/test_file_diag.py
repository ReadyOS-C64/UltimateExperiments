from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-file-test-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import ctypes as C,json,unittest,importlib.util,hashlib
PAR=Path('/Users/karlprosserpp/dev/c64projects/UltimateExperiments/8088DOS64ultimate/agentworking/scratch/native-installer-bootstrap-diagnostics-20261017')
spec=importlib.util.spec_from_file_location('frozen_boot',PAR/'test_boot.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
L=b.L;Regs=b.Regs;REPORT=[]
class M(b.M):
 def __init__(self):
  self.kind='setup';j=json.loads((P/os.environ.get('DIAG_TEST_RESULT','bankguard/RESULT.json')).read_text());self.w=Path(j['work'])/'build';self.s={x.split()[2].lstrip('.'):int(x.split()[1],16)for x in(self.w/'setup.labels').read_text().splitlines()if x.startswith('al ')};self.m=L.dos64_create();data=(self.w/'setup.prg').read_bytes();L.dos64_load(self.m,int.from_bytes(data[:2],'little'),data[2:],len(data)-2)
  for n in ['native_runtime_control_enable','dos64_graphics_color_enable','dos64_cia_clock_enable','dos64_native_display_enable','dos64_host_input_model_enable','dos64_enable_reu','bulk_model_enable']:getattr(L,n)(self.m)
  L.dos64_uci_model_enable(self.m,0xdf1c,3,0xc9);L.dos64_poke(self.m,0,0x2f);L.dos64_poke(self.m,1,0x37);L.native_runtime_require_nmi_order.argtypes=[C.c_void_p,C.c_uint16];L.native_runtime_require_nmi_order(self.m,self.s['ps_rti']);L.native_runtime_nmi_checked.argtypes=[C.c_void_p];L.native_runtime_nmi_checked.restype=C.c_uint8;L.dos64_set_regs(self.m,Regs(0x80d,0xfd,0,0,0,0x24,0,0));L.dos64_clear_writes(self.m)
 def call(self,name,a=0,x=0,budget=50000000):
  r=L.dos64_get_regs(self.m);sp=r.sp;self.put(0x100+sp,b'\x02');self.put(0x100+((sp-1)&255),b'\xff');L.dos64_set_regs(self.m,Regs(self.addr(name),(sp-2)&255,a,x,0,0x24,r.cycles,r.instructions));v=self.run(0x300,budget);assert v.status in [0,2] and v.regs.pc==0x300,(name,v.status,hex(v.regs.pc));return v.regs.a+(v.regs.x<<8)
 def boot(self,t):
  self.at(t,'_su_begin');t.assertEqual(L.native_runtime_nmi_checked(self.m),1);t.assertEqual(self.get(1)[0]&7,5);t.assertEqual(self.get('phase_verified'),b'\1');t.assertEqual(self.get('sp',2),b'\xff\xcf');t.assertEqual(self.call('_sc_ready'),1);t.assertEqual(self.call('_bc_files_closed'),1)
  # Interface component only: retire authentic UI ticket, admit caller's canonical home.
  ticket=self.call('_so_ui_ticket');t.assertNotEqual(ticket,0);self.put('_so_ticket',ticket.to_bytes(2,'little'));t.assertEqual(self.call('_so_leave'),1);self.put(self.s['_so_request']+7,b'/Home'.ljust(128,b'\0'));t.assertEqual(self.call('_so_bind_home'),1)
 def stack(self,t):
  t.assertEqual(self.get('sp',2),b'\xff\xcf');low=min((a for a in range(0xcd00,0xd000)if L.dos64_was_written(self.m,a)),default=0xcfff);t.assertGreaterEqual(low,0xcd00);return low
 def load_phase(self,t,phase,blob):
  name=b'/Home/SETUP.FAT'if phase==2 else b'/Home/SETUP.PUB'
  if blob is not None:L.bulk_model_seed(self.m,name,blob,len(blob))
  self.put('_so_phase_request',bytes([phase]));self.put('_so_now',self.get('_ps_ticks',2));t.assertEqual(self.call('_so_begin'),1)
  for i in range(10000):
   L.dos64_cia_clock_advance(self.m,1024);t.assertEqual(self.call('_ps_clock_poll'),1);self.put('_so_now',self.get('_ps_ticks',2));self.call('_so_poll');state=self.call('_so_state')
   if state!=1:break
  else:t.fail('bounded asset loader')
  return state
 def pane(self,t,file,op,closed,source=False):
  # Invoke real root phase-failure continuation only after actual private loader FAILED.
  
  if not source:t.assertEqual(self.call('_so_state'),3);self.call('phase_failed')
  t.assertEqual(self.call('_rc_state'),5);before=L.bulk_model_commands(self.m);helper=self.get(0xbfa0,94);L.dos64_clear_writes(self.m);self.call('_rc_poll');screen=self.get(0x748,160)
  for at,txt in [(0,b'ERR'),(15,op),(45,file),(80,b'CLOSE:'+closed)]:t.assertEqual(screen[at:at+len(txt)],bytes(x&63 for x in txt),screen)
  t.assertEqual(L.bulk_model_commands(self.m),before);t.assertEqual(self.get(0xbfa0,94),helper)
  allowed=set(range(0x748,0x7e8))|set(range(0xdb48,0xdbe8))|set(range(0x100,0x200))|{self.s['ptr1'],self.s['ptr1']+1,self.s['failure_shown']}
  bad=[a for a in range(65536)if L.dos64_was_written(self.m,a)and a not in allowed];t.assertEqual(bad,[])
  L.dos64_host_input_model_keys(self.m,bytes([2,0,0,0,0,0,0,128]))
  for _ in range(20):self.call('_rc_poll')
  t.assertEqual(L.bulk_model_commands(self.m),before);t.assertEqual(self.call('_rc_state'),5)
  return screen
class Cases(unittest.TestCase):
 def test_missing_FAT_and_PUB_open_knownclose(self):
  for phase in [2,3]:
   with self.subTest(phase=phase):
    m=M()
    try:
     m.boot(self);low=m.stack(self);self.assertEqual(m.load_phase(self,phase,None),3);low=m.stack(self);screen=m.pane(self,b'SETUP.FAT'if phase==2 else b'SETUP.PUB',b'OPEN',b'Y');REPORT.append({'phase':phase,'fault':'missing','software_stack_low':low,'screen':screen.hex(),'actual_boot_owned_public_loader_API':True})
    finally:m.close()
 def test_short_FAT_and_PUB_info_knownclose(self):
  for phase in [2,3]:
   with self.subTest(phase=phase):
    m=M()
    try:
     m.boot(self);name='SETUP.FAT'if phase==2 else'SETUP.PUB';d=(m.w/name).read_bytes()[:-1];self.assertEqual(m.load_phase(self,phase,d),3);low=m.stack(self);m.pane(self,name.encode(),b'INFO',b'Y');REPORT.append({'phase':phase,'fault':'short','software_stack_low':low})
    finally:m.close()
 def test_short_INFO_then_failed_CLOSE_keeps_firstdetail_and_blocks(self):
  m=M()
  try:
   m.boot(self);n=L.bulk_model_commands(m.m);L.bulk_model_faults(m.m,n+3,-1,-1,0,-1);d=(m.w/'SETUP.FAT').read_bytes()[:-1];self.assertEqual(m.load_phase(self,2,d),3);low=m.stack(self);m.pane(self,b'SETUP.FAT',b'INFO',b'?');self.assertEqual(L.bulk_model_open(m.m,1),1);REPORT.append({'fault':'short then CLOSE failure','unknown_close':True,'first_INFO_detail_retained':True,'software_stack_low':low})
  finally:m.close()
 def test_corrupt_FAT_and_PUB_CRC_knownclose_no_phase_instructions(self):
  for phase in [2,3]:
   with self.subTest(phase=phase):
    m=M()
    try:
     m.boot(self);name='SETUP.FAT'if phase==2 else'SETUP.PUB';d=bytearray((m.w/name).read_bytes());d[-1]^=1;L.boot_pc_observe(m.m,0x6000,0xb000);self.assertEqual(m.load_phase(self,phase,bytes(d)),3);self.assertEqual(L.boot_pc_hits(m.m),0);low=m.stack(self);m.pane(self,name.encode(),b'CRC ',b'Y');REPORT.append({'phase':phase,'fault':'CRC','no_partial_overlay_PC':True,'software_stack_low':low})
    finally:m.close()
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases));(P/'FILE_TEST_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'records':REPORT,'scope':'actual cold SYS ownership, public SO API asset-loader fault components/root failure continuation plus true CIA START.INO dispatcher fault; no full output publication'},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
