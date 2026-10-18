from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-select-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import ctypes as C,struct,unittest,json
from test_browser import F,L
for n,r,a in [('native_runtime_control_enable',None,[C.c_void_p]),('dos64_graphics_color_enable',None,[C.c_void_p]),('dos64_cia_clock_enable',None,[C.c_void_p]),('dos64_cia_clock_advance',None,[C.c_void_p,C.c_uint32]),('dos64_native_display_enable',None,[C.c_void_p]),('dos64_host_input_model_enable',None,[C.c_void_p]),('dos64_host_input_model_keys',None,[C.c_void_p,C.c_void_p]),('bulk_model_commands',C.c_uint32,[C.c_void_p]),('bulk_model_command',C.c_uint8,[C.c_void_p,C.c_uint32,C.c_uint32])]:
 f=getattr(L,n);f.restype=r;f.argtypes=a
REPORT={}
class UI:
 def __init__(self,capacity=0x400000):
  self.f=F();f=self.f;g=bytearray(f.guard)
  if capacity!=0x400000:
   L.dos64_enable_reu_sized.argtypes=[C.c_void_p,C.c_uint32];L.dos64_enable_reu_sized.restype=C.c_uint8
   installed=8192 if capacity<=0x800000 else 16384
   assert L.dos64_enable_reu_sized(f.m,installed)==1
  for at,size in [(0,2),(0xc6,1),(0x277,10),(0x400,1000),(0xd800,1000),(f.labels['__UIBSS_RUN__'],f.labels['__UIBSS_SIZE__']),(0xfffa,2),(f.labels['_ps_color'],1),(0xdf01,10)]:g[at:at+size]=b'\1'*size
  for at in [0xd019,0xd01a,0xd011,0xd016,0xd018,0xd015,0xd020,0xd021,0xdc00,0xdc02,0xdc03,0xdc0d,0xdd00,0xdd02,0xdd04,0xdd05,0xdd06,0xdd07,0xdd0d,0xdd0e,0xdd0f]:g[at]=1
  f.guard=bytes(g);L.dos64_poke(f.m,0,0x2f);L.dos64_poke(f.m,1,0x35)
  for n in ['native_runtime_control_enable','dos64_graphics_color_enable','dos64_cia_clock_enable','dos64_native_display_enable','dos64_host_input_model_enable']:getattr(L,n)(f.m)
  self.call('_ps_init');assert (L.browser_bank(f.m)&255)==0x2f and ((L.browser_bank(f.m)>>8)&7)==5;assert self.call('_sc_begin',0xa5)==1
  for now in range(20000):
   f.write('_sc_now',struct.pack('<H',now//32));state=self.call('_sc_poll')
   if state!=1:break
  assert state==2 and self.call('_sc_ready')==1
  if '_sl_install' in f.labels:
   g=bytearray(f.guard);at=f.labels['__HIGH_CODE_RUN__'];n=f.labels['__HIGH_CODE_SIZE__'];g[at:at+n]=b'\1'*n;old=f.guard;f.guard=bytes(g)
   try:assert self.call('_sl_install')==1
   finally:f.guard=old
  f.write('_so_request',struct.pack('<BIH',0xa5,capacity,1000)+bytes(128));assert self.call('_so_prepare')==1
  f.write('_so_phase_request',b'\1');assert self.call('_so_enter')==1;self.ticket=int.from_bytes(f.read('_so_result',10)[8:10],'little')
  self.state=0
 def call(self,n,arg=0x71):
  f=self.f;old=f.guard
  if n in ['_so_prepare','_so_poll']:
   g=bytearray(old);g[0x6000:0xb000]=b'\1'*0x5000;f.guard=bytes(g)
  try:return f.call(n,arg,budget=12000000)
  finally:f.guard=old
 def begin(self,owner=0xa5):
  self.f.write('_ss_test_owner',bytes([owner]));self.f.write('_ss_test_timeout',struct.pack('<H',1000));self.call('_ss_test_begin');return self.f.byte('_ss_test_value')
 def poll(self):
  L.dos64_cia_clock_advance(self.f.m,1024);self.state=self.call('_ss_poll');return self.state
 def ready(self):
  for _ in range(3000):
   self.poll()
   if self.f.byte('_db_result')!=1:return self.state
  raise AssertionError('bounded selection directory job')
 def key(self,row,col,shift=False):
  keys=bytearray(8);keys[row]|=1<<col
  if shift:keys[1]|=128
  L.dos64_host_input_model_keys(self.f.m,bytes(keys));self.poll();L.dos64_host_input_model_keys(self.f.m,bytes(8));self.poll();return self.ready()
 def directory(self,path,rows):self.f.directory(path,rows)
 def screen(self):return self.f.readat(0x400,1000)
 def leave(self):self.f.write('_so_ticket',struct.pack('<H',self.ticket));return self.call('_so_leave')
 def close(self):self.f.close()
 def choices(self):
  f=self.f;at=int.from_bytes(f.read('_ss_choices',2),'little');raw=f.readat(at,642)
  return {'paths':[raw[i*128:(i+1)*128].split(b'\0')[0]for i in range(5)],'profile':raw[640],'existing_present':raw[641]}
class Selection(unittest.TestCase):
 def setUp(self):self.ui=UI()
 def tearDown(self):self.ui.close()
 def home(self):
  u=self.ui;u.directory(b'/',[(0x10,b'Home')]);u.directory(b'/Home',[(0x20,b'DOS 1.img'),(0x20,b'DOS 2.img'),(0x20,b'DOS 3.img'),(0x20,b'OLD C.IMG')]);self.assertEqual(u.begin(),1);self.assertEqual(u.ready(),1);u.key(0,1);self.assertEqual(u.f.page()['path'],b'/Home');u.key(0,4);self.assertEqual(u.f.byte('_ss_stage'),1)
 def test_real_CIA_complete_selections_skip_C_and_confirm(self):
  self.home();u=self.ui
  u.key(0,1);self.assertEqual(u.f.byte('_ss_stage'),2)
  u.key(0,7);u.key(0,1);self.assertEqual(u.f.byte('_ss_stage'),3)
  u.key(0,7);u.key(0,7);u.key(0,1);self.assertEqual(u.f.byte('_ss_stage'),4)
  u.key(0,4);self.assertEqual(u.f.byte('_ss_stage'),5)
  u.key(0,7);u.key(0,1);self.assertEqual(u.f.byte('_ss_stage'),6);self.assertEqual(u.state,1)
  self.assertEqual(u.key(0,1),2);self.assertEqual(u.choices(),{'paths':[b'/Home',b'/Home/DOS 1.img',b'/Home/DOS 2.img',b'/Home/DOS 3.img',b''],'profile':1,'existing_present':0})
  self.assertEqual(L.bulk_model_commands(u.f.m),2);self.assertEqual(u.leave(),1)
  REPORT['complete']=u.choices();REPORT['screen_codes_hex']=u.screen().hex()
 def disks(self):
  self.home();u=self.ui;u.key(0,1);u.key(0,7);u.key(0,1);u.key(0,7);u.key(0,7);u.key(0,1)
 def test_existing_C_selection_and_2MiB_profile(self):
  self.disks();u=self.ui
  for _ in range(3):u.key(0,7)
  u.key(0,1);self.assertEqual(u.f.byte('_ss_stage'),5);u.key(0,1);u.key(0,1)
  self.assertEqual(u.state,2);self.assertEqual(u.choices()['paths'][4],b'/Home/OLD C.IMG');self.assertEqual(u.choices()['profile'],0);self.assertEqual(u.choices()['existing_present'],1);self.assertEqual(u.leave(),1)
 def test_duplicate_source_remains_at_same_stage(self):
  self.home();u=self.ui;u.key(0,1);self.assertEqual(u.f.byte('_ss_stage'),2);u.key(0,1);self.assertEqual(u.f.byte('_ss_stage'),2);self.assertEqual(u.choices()['paths'][2],b'');self.assertEqual(u.state,1);self.assertEqual(L.bulk_model_commands(u.f.m),2)
 def test_home_root_refused_then_browse_parent_and_paginate(self):
  u=self.ui;u.directory(b'/',[(0x10,('Home %02d'%i).encode())for i in range(25)]);u.directory(b'/Home 12',[])
  u.begin();u.ready();u.key(0,4);self.assertEqual(u.f.byte('_ss_stage'),0)
  u.key(0,6);self.assertEqual(u.f.page()['first'],12);u.key(0,1);self.assertEqual(u.f.page()['path'],b'/Home 12')
  u.key(0,0);self.assertEqual(u.f.page()['path'],b'/');u.key(0,6);u.key(0,5);self.assertEqual(u.f.page()['first'],0)
 def test_long_selected_path_scroll_keeps_raw_identity(self):
  u=self.ui;name=b'Image '+b'X'*70+b'.IMG';u.directory(b'/',[(0x10,b'Home')]);u.directory(b'/Home',[(0x20,name)])
  u.begin();u.ready();u.key(0,1);u.key(0,4);before=u.screen()[960:1000]
  for _ in range(45):u.key(0,2)
  after=u.screen()[960:1000];self.assertNotEqual(before,after);u.key(0,1);self.assertEqual(u.choices()['paths'][1],b'/Home/'+name)
 def test_idle_RunStop_and_held_key_do_not_repeat(self):
  self.home();u=self.ui;keys=bytes([128])+bytes(7);L.dos64_host_input_model_keys(u.f.m,keys)
  for _ in range(8):u.poll()
  L.dos64_host_input_model_keys(u.f.m,bytes(8));u.poll();self.assertEqual(u.f.page()['count'] if 'count'in u.f.page()else len(u.f.page()['rows']),4)
  self.assertEqual(u.key(7,7),3);self.assertEqual(u.f.byte('_ss_error'),3);self.assertEqual(u.leave(),1)
 def test_selection_observations_cannot_grant_done(self):
  self.home();u=self.ui;u.f.write('_ss_stage',b'\6');u.f.write('_ss_error',b'\0');self.assertEqual(u.poll(),1);self.assertEqual(u.choices()['paths'][3],b'')
 def test_escaped_filename_display_is_distinct_and_raw_choice_exact(self):
  u=self.ui;u.directory(b'/',[(0x10,b'Home')]);u.directory(b'/Home',[(0x20,b'A_B.IMG'),(0x20,b'A-B.IMG'),(0x20,b'A%5FB.IMG'),(0x20,b'A{B.IMG'),(0x20,b'A[B.IMG')]);u.begin();u.ready();u.key(0,1);u.key(0,4)
  screen=u.screen();names=[screen[(5+i)*40+2:(5+i)*40+30].rstrip(b' ')for i in range(5)];self.assertEqual(len(set(names)),5)
  self.assertIn(b'%5F',names[0]);self.assertIn(b'%25',names[2]);self.assertIn(b'%7B',names[3]);u.key(0,1);self.assertEqual(u.choices()['paths'][1],b'/Home/A_B.IMG')
 def test_encoded_long_path_scroll_exceeds_255_cells(self):
  u=self.ui;name=b'_'*110+b'.IMG';u.directory(b'/',[(0x10,b'Home')]);u.directory(b'/Home',[(0x20,name)]);u.begin();u.ready();u.key(0,1);u.key(0,4)
  for _ in range(330):u.key(0,2)
  tail=u.screen()[960:1000];self.assertIn(b'.IMG',tail);u.key(0,1);self.assertEqual(u.choices()['paths'][1],b'/Home/'+name)
 def test_directory_status_failure_returns_failed_closed_without_OPEN(self):
  u=self.ui;u.directory(b'/',[(0x10,b'Home')]);L.dir_model_fault(u.f.m,0x14,0,5);u.begin();self.assertEqual(u.ready(),3);self.assertEqual(u.f.byte('_ss_error'),2);self.assertEqual(u.leave(),1);self.assertEqual(L.bulk_model_commands(u.f.m),2)
 def test_cancel_directory_drains_before_ticket_release(self):
  u=self.ui;u.directory(b'/',[(0x10,('Folder %02d'%i).encode())for i in range(25)]);self.assertEqual(u.begin(),1);self.assertEqual(u.leave(),0)
  self.assertEqual(u.key(7,7),3);self.assertEqual(u.f.byte('_ss_error'),3);self.assertEqual(u.f.result()[4],0);self.assertEqual(u.leave(),1);self.assertEqual(L.bulk_model_commands(u.f.m),2)
 def test_disabled_begin_no_directory_wire(self):
  u=self.ui;self.assertEqual(u.begin(0),0);self.assertEqual(u.f.wire(),[]);self.assertEqual(u.leave(),1)
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Selection));(P.parent/'SELECT_RESULTS.json').write_text(json.dumps(REPORT,indent=2,default=lambda b:b.decode('ascii'))+'\n');sys.exit(not r.wasSuccessful())
