from pathlib import Path
import os,sys
sys.dont_write_bytecode=True
sys.pycache_prefix=str(Path(__file__).resolve().parent/('.absent-source-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import ctypes as C,struct,unittest,zlib,json,hashlib
from test_capsule import UI,L,prepare,reu
for name,ret,args in [('bulk_model_read',C.c_uint8,[C.c_void_p,C.c_char_p,C.c_void_p,C.c_uint32]),('bulk_model_open',C.c_uint8,[C.c_void_p,C.c_uint8]),('bulk_model_faults',None,[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int]),('dos64_uci_model_stuck',None,[C.c_void_p,C.c_uint8])]:
 f=getattr(L,name);f.restype=ret;f.argtypes=args
DATA=[bytes((i*17+(i>>8)+k*37)&255 for i in range(n))for k,n in enumerate([368640,368640,368640,18432,64])]
PATHS=[b'/Home/DOS 1.img',b'/Home/DOS 2.img',b'/Home/DOS 3.img',b'/Home/START.TPL',b'/Home/START.REL']
ADDR=[0x100000,0x180000,0x380000,0x2e0000,0x3fec00];REPORT={}
class Loading(unittest.TestCase):
 def setUp(self):
  self.u=UI();u=self.u;prepare(u);self.assertEqual(u.call('_sq_publish'),1);self.capsule=reu(u);u.f.write('_ns_io_owner',b'\xa5');u.f.write('_ns_capacity',struct.pack('<I',0x400000))
  for path,data in zip(PATHS,DATA):L.bulk_model_seed(u.f.m,path,data,len(data))
 def tearDown(self):self.u.close()
 def start(self,k=0):
  self.u.f.write('_sl_kind',bytes([k]));self.u.f.write('_sl_timeout',struct.pack('<H',1000));return self.u.call('_sl_begin')
 def poll(self,advance=1024):
  L.dos64_cia_clock_advance(self.u.f.m,advance);self.u.call('_sl_poll');return self.u.call('_sl_state')
 def result(self):return tuple(self.u.f.read('_sl_result',6))
 def finish(self):
  for _ in range(100000):
   if self.u.call('_sl_state')!=1:return self.result()
   self.poll()
  self.fail('bounded native source job')
 def until(self,phase):
  for _ in range(100000):
   if self.result()[2]==phase:return
   self.assertEqual(self.poll(),1)
  self.fail('source phase bound')
 def bytes(self,a,n):
  b=C.create_string_buffer(n);self.assertEqual(L.dos64_reu_read(self.u.f.m,a,b,n),1);return b.raw
 def fact(self,k):
  u=self.u;u.f.write('_sl_kind',bytes([k]));u.f.write('_sl_generation',self.capsule[8:10]);u.f.write('_sl_identity',self.capsule[700:704]);r=u.call('_sl_fact');return r,struct.unpack('<HIII',u.f.read('_sl_receipt',14))
 def test_all_five_sources_exact_twice_read_closed_private_bound_receipts(self):
  u=self.u;facts=[]
  for k,data in enumerate(DATA):
   self.assertEqual(self.start(k),1);self.assertEqual(self.finish()[:2],(2,0));self.assertEqual(self.bytes(ADDR[k],len(data)),data);self.assertEqual(L.bulk_model_open(u.f.m,1),0);ok,fact=self.fact(k);self.assertEqual(ok,1);self.assertEqual(fact,(1,int.from_bytes(self.capsule[700:704],'little'),len(data),zlib.crc32(data)));facts.append(fact)
  for path,data in zip(PATHS,DATA):
   b=C.create_string_buffer(len(data));self.assertEqual(L.bulk_model_read(u.f.m,path,b,len(data)),1);self.assertEqual(b.raw,data)
  self.assertEqual(reu(u),self.capsule);self.assertEqual(self.start(0),0);REPORT['facts']=facts
 def test_uppercase_lowercase_and_mixed_firmware_hex_receipts(self):
  for fault in [0,10,11]:
   t=Loading();t.setUp()
   try:
    self.assertEqual(t.start(4),1);t.until(3)
    count=L.bulk_model_commands(t.u.f.m)
    L.bulk_model_faults(t.u.f.m,-1,-1,count+1,fault,-1)
    self.assertEqual(t.finish()[:2],(2,0));self.assertEqual(t.bytes(ADDR[4],64),DATA[4]);self.assertEqual(t.fact(4)[0],1)
   finally:t.tearDown()
 def test_missing_or_wrong_size_never_grants_receipt(self):
  L.bulk_model_seed(self.u.f.m,PATHS[0],DATA[0][:-1],len(DATA[0])-1);self.assertEqual(self.start(),1);self.assertEqual(self.finish()[:2],(3,2));self.assertEqual(self.fact(0)[0],0);self.assertEqual(self.start(),0)
 def test_suppressed_or_corrupt_LOAD_cannot_match_independent_poison(self):
  for kind in [-2,0]:
   t=Loading();t.setUp()
   try:
    L.bulk_model_faults(t.u.f.m,-1,-1,-1,0,kind);self.assertEqual(t.start(4),1);self.assertEqual(t.finish()[:2],(3,4));self.assertEqual(t.fact(4)[0],0)
   finally:t.tearDown()
 def test_partial_poison_DMA_prevents_LOAD_and_private_DONE(self):
  self.assertEqual(self.start(4),1);self.until(3);L.dos64_reu_fail_after(self.u.f.m,0,7);self.assertEqual(self.finish()[:2],(3,3));self.assertEqual(self.fact(4)[0],0)
 def test_RunStop_final_CLOSE_and_public_DONE_forgery_never_grant_fact(self):
  self.assertEqual(self.start(4),1);self.until(13);L.dos64_host_input_model_keys(self.u.f.m,bytes(7)+b'\x80');self.assertEqual(self.finish()[:2],(3,5));self.u.f.write('_sl_result',b'\2'+bytes(5));self.assertEqual(self.fact(4)[0],0);self.assertEqual(self.u.call('_sl_state'),3)
 def test_private_paths_ignore_forged_selection_and_public_request_mutation(self):
  u=self.u;at=int.from_bytes(u.f.read('_ss_choices',2),'little');L.dos64_load(u.f.m,at,b'/WRONG'+bytes(636),642);self.assertEqual(self.start(4),1);u.f.write('_sl_kind',b'\0');u.f.write('_sl_timeout',b'\0\0');self.assertEqual(self.finish()[:2],(2,0));self.assertEqual(self.bytes(ADDR[4],64),DATA[4]);self.assertEqual(self.fact(4)[0],1);self.assertEqual(self.fact(0)[0],0)
 def test_HIGH_copy_exact_and_code_survives_UI_to_FAT_retirement(self):
  u=self.u;f=u.f;load=f.labels['__HIGH_CODE_LOAD__'];run=f.labels['__HIGH_CODE_RUN__'];n=f.labels['__HIGH_CODE_SIZE__'];code=f.readat(run,n)
  # The load-only source aliases live UI BSS after relocation. Compare the
  # independent cold artifact, not memory now occupied by selected paths.
  cold=Path('build/setup.prg').read_bytes();at=load-0x0801+2
  self.assertEqual(code,cold[at:at+n]);self.assertEqual(self.start(4),1);self.assertEqual(self.finish()[:2],(2,0));self.assertEqual(u.leave(),1);f.write('_so_request',struct.pack('<BIH',0xa5,0x400000,1000)+b'/Home'.ljust(128,b'\0'));self.assertEqual(u.call('_so_bind_home'),1)
  fat=Path('build/SETUP.FAT').read_bytes();L.bulk_model_seed(f.m,b'/Home/SETUP.FAT',fat,len(fat));f.write('_so_phase_request',b'\2');self.assertEqual(u.call('_so_begin'),1)
  for i in range(20000):
   L.dos64_cia_clock_advance(f.m,1024);u.call('_ps_clock_poll');f.write('_so_now',f.read('_ps_ticks',2));u.call('_so_poll')
   if u.call('_so_state')!=1:break
  self.assertEqual(u.call('_so_state'),2);self.assertEqual(f.readat(run,n),code);self.assertEqual(self.fact(4)[0],1);self.assertEqual(u.call('_sl_state'),2)
 def test_configuration_capacity_change_revokes_job_before_MORE_LOAD(self):
  self.assertEqual(self.start(4),1);self.until(3);self.u.f.write('_ns_capacity',struct.pack('<I',0x800000));self.assertEqual(self.finish()[:2],(3,3));self.assertEqual(self.fact(4)[0],0)
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Loading));Path('../SOURCE_LOAD_RESULTS.json').write_text(json.dumps(REPORT,indent=2)+'\n');sys.exit(not r.wasSuccessful())
