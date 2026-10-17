from pathlib import Path
import sys,os,ctypes as C,struct,unittest,json,zlib
sys.dont_write_bytecode=True
from test_ui_session import Session
from test_browser import F,Regs
from test_capsule import L,reu
from test_source_load import PATHS,DATA
REPORT={}
class Coordinator(Session):
 def __init__(self):
  # Cold binary/model. Unlike UI fixture, bootstrap owns platform, close gates,
  # HIGH relocation and SO prepare/enter; no injected ticket or private facts.
  self.f=F();f=self.f;g=bytearray(f.guard)
  for a,n in [(0,2),(0x400,1000),(0xd800,1000),(0x6000,0x5000),(0xfffa,2),(f.labels['_ps_color'],1),(f.labels['__HIGH_CODE_RUN__'],f.labels['__HIGH_CODE_SIZE__']),(f.labels['__AUX_CODE_RUN__'],f.labels['__AUX_CODE_SIZE__']+f.labels.get('__AUX_RO_SIZE__',0)),(0xdf01,10)]:g[a:a+n]=b'\1'*n
  for a in [0xd019,0xd01a,0xd011,0xd016,0xd018,0xd015,0xd020,0xd021,0xdc00,0xdc02,0xdc03,0xdc0d,0xdd00,0xdd02,0xdd04,0xdd05,0xdd06,0xdd07,0xdd0d,0xdd0e,0xdd0f]:g[a]=1
  f.guard=bytes(g);L.dos64_poke(f.m,0,0x2f);L.dos64_poke(f.m,1,0x35)
  for n in ['native_runtime_control_enable','dos64_graphics_color_enable','dos64_cia_clock_enable','dos64_native_display_enable','dos64_host_input_model_enable']:getattr(L,n)(f.m)
  self.seed();asset=Path('build/SETUP.FAT').read_bytes();L.bulk_model_seed(f.m,b'/Home/SETUP.FAT',asset,len(asset))
  self.directory(b'/',[(16,b'Home')]);self.directory(b'/Home',[(32,b'DOS 1.img'),(32,b'DOS 2.img'),(32,b'DOS 3.img')])
  assert f.labels['setup_boot']==0x80d
  L.dos64_set_regs(f.m,Regs(0x80d,0xe0,0,0,0,0x24,0,0));L.dos64_clear_writes(f.m)
  r=L.dos64_run(f.m,f.labels['setup_loop'],12000000)
  assert r.status==0 and r.regs.pc==f.labels['setup_loop'],('boot',r.status,hex(r.regs.pc))
  assert L.browser_bad_write(f.m,f.guard)==65536,hex(L.browser_bad_write(f.m,f.guard))
  assert self.call('_rc_state')==1 and self.call('_sc_ready')==0
  self.state=1
 def poll(self):
  L.dos64_cia_clock_advance(self.f.m,1024);self.call('_rc_poll');self.state=self.call('_rc_state');return self.state
 def ui(self):
  for _ in range(3000):
   self.poll()
   if self.state==2:return
   assert self.state==1,('startup',self.state,self.call('_rc_error'))
  raise AssertionError('bounded close/bootstrap')
 def ready(self):
  if self.call('_db_state')!=1:return self.state
  for _ in range(3000):
   self.poll()
   if self.call('_db_state')!=1:return self.state
  raise AssertionError('directory bound')
 def select(self):
  self.ui();self.ready();self.key(0,1);self.key(0,4)
  self.key(0,1);self.key(0,7);self.key(0,1);self.key(0,7);self.key(0,7);self.key(0,1)
  self.key(0,4);self.key(0,7);self.key(0,1);self.key(0,1)
 def finish(self):
  for _ in range(100000):
   s=self.call('_rc_state')
   if s in [4,5]:return s
   self.poll()
  raise AssertionError('coordinator bound')
class Actual(unittest.TestCase):
 def setUp(self):self.u=Coordinator()
 def tearDown(self):self.u.close()
 def test_real_SYS_boot_select_source_capture_retire_UI_load_enter_FAT(self):
  u=self.u;u.select();self.assertEqual(u.finish(),4);self.assertEqual(u.call('_rc_error'),0)
  self.assertEqual(u.call('_rc_source_ready'),1);self.assertEqual(u.f.byte('_rc_source_mask'),31)
  capsule=reu(u);self.assertEqual(u.f.read('_rc_generation',2),capsule[8:10]);self.assertEqual(u.f.read('_rc_identity',4),capsule[700:704]);self.assertEqual(u.f.byte('_rc_flags'),1)
  home=int.from_bytes(u.f.read('_rc_home',2),'little');self.assertEqual(u.f.readat(home,128).split(b'\0')[0],b'/Home')
  size,crcs,outputs,valid=struct.unpack('<4H',u.f.read('_rc_record_layout',8));self.assertEqual((size,crcs,outputs,valid),(183,134,154,181));self.assertEqual(struct.unpack('<5I',u.f.readat(home+crcs,20)),tuple(zlib.crc32(d)for d in DATA));self.assertEqual(u.f.readat(home+outputs,24),bytes(24))
  self.assertEqual(u.call('_so_ui_ticket'),0);self.assertEqual(u.call('_bc_files_closed'),1)
  fat=Path('build/fat-overlay.bin').read_bytes();self.assertEqual(u.f.readat(0x6000,len(fat)),fat)
  # Source receipts remain authoritative after UI code/state have been replaced.
  u.f.write('_rc_identity',bytes(4));u.f.write('_rc_source_mask',b'\0');self.assertEqual(u.call('_rc_source_ready'),1)
  cmds=[[L.bulk_model_command(u.f.m,i,j)for j in range(2)]for i in range(L.bulk_model_commands(u.f.m))]
  self.assertTrue(all(c[1]not in [5,0x22]for c in cmds));REPORT['complete']={'commands':len(cmds),'software_stack_min':hex(u.f.soft_min),'source_bytes':sum(map(len,DATA)),'coordinator_state':4}
 def test_source_fault_never_retires_UI_or_enters_FAT(self):
  u=self.u;L.bulk_model_faults(u.f.m,-1,-1,-1,0,0);u.select();self.assertEqual(u.finish(),5);self.assertEqual(u.call('_rc_error'),0x34);self.assertEqual(u.call('_rc_source_ready'),0)
  self.assertNotEqual(u.call('_so_ui_ticket'),0);self.assertEqual(u.call('_bc_files_closed'),1)
 def test_RunStop_selection_terminal_without_disk_writes(self):
  u=self.u;u.ui();u.ready();L.dos64_host_input_model_keys(u.f.m,bytes(7)+b'\x80');self.assertEqual(u.finish(),5);self.assertEqual(u.call('_rc_error'),0x13);self.assertEqual(u.call('_rc_source_ready'),0);self.assertEqual(u.call('_bc_files_closed'),1)
 def test_early_capture_and_public_DONE_forgery_cannot_make_receipts(self):
  u=self.u;u.ui();u.f.write('_rc_expected_ticket',b'\1\0');u.f.write('_sl_result',b'\2'+bytes(5));u.f.write('_ss_stage',b'\6');u.f.write('_rc_source_mask',b'\x1f');self.assertEqual(u.call('_rc_capture'),0);self.assertEqual(u.call('_rc_source_ready'),0);self.assertEqual(u.call('_rc_state'),2)
 def test_clock_failure_startup_preserves_cause_and_drains_bounded(self):
  u=self.u;L.dos64_cia_clock_step.argtypes=[C.c_void_p,C.c_uint32];L.dos64_cia_clock_step.restype=None;L.dos64_cia_clock_step(u.f.m,0x40000)
  self.assertEqual(u.finish(),5);self.assertEqual(u.call('_rc_error'),0xe1);self.assertEqual(u.call('_rc_source_ready'),0)
 def test_public_closer_phase_observations_and_second_begin_do_not_advance(self):
  u=self.u
  # Native startup CLOSE1/2 with malformed status is owned by the shared closer.
  # Busy-to-error coincidence is additionally covered by shared closer groups;
  # this integration asserts no public state can force an alternative entry.
  u.f.write('_sc_state',b'\2');u.f.write('_so_result',bytes([2,2,0,0,0,0,0,1,1,0]));self.assertEqual(u.call('_rc_state'),1);self.assertEqual(u.call('_rc_begin'),0);self.assertEqual(u.call('_rc_source_ready'),0)
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Actual));Path('../COORDINATOR_RESULTS.json').write_text(json.dumps(REPORT,indent=2)+'\n');sys.exit(not r.wasSuccessful())
