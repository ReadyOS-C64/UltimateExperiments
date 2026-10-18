import sys,os
from pathlib import Path
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.pycache_prefix=str(P/('.absent-controller-cache-'+str(os.getpid())))
if Path(sys.pycache_prefix).exists():raise RuntimeError('source-only cache prefix must be absent')
import struct,zlib,unittest,ctypes as C,json,time
from test_actual import F,L,Regs
from make_release import descriptor
L.dos64_clear_writes.argtypes=[C.c_void_p];L.dos64_clear_writes.restype=None
L.lc_check_writes.argtypes=[C.c_void_p,C.c_void_p];L.lc_check_writes.restype=C.c_uint32
ROOT=P.parent/'inputs'
HOME=b'/usb1/DOS Start';A=b'/usb1/Images/A.IMG';B=b'/usb1/Other Disks/B.IMG'
def path(out,at,s):out[at:at+128]=s.ljust(128,b'\0')
def cfg(a,b=None,cap=0x400000):
 v=bytearray(576);v[:8]=b'D64C\x01\x40\x02\0';path(v,8,HOME);path(v,136,A)
 if b is not None:path(v,264,B)
 path(v,392,HOME+b'/C.IMG');v[522]=1;v[524]=2 if b else 0;v[525]=7 if b is not None else 5
 struct.pack_into('<IIHI',v,528,zlib.crc32(a),zlib.crc32(b) if b is not None else 0,1,cap)
 struct.pack_into('<I',v,572,zlib.crc32(v[:572]));return bytes(v)
def release_fixture():
 main=(ROOT/'build/dos64.prg').read_bytes();labels=(ROOT/'build/dos64.labels').read_text()
 assert main[0x3fe0-0x0801+2]==0
 return main,descriptor(main,labels)
class Controller(F):
 def __init__(self,prefix="controller"):
  self.high=0;self.calls=0;super().__init__(prefix);self.call('_lc_init')
 def call(self,n,budget=12_000_000,a=0x71):
  ret=self.at('fixture_return')-1;L.dos64_poke(self.m,0x1ff,ret>>8);L.dos64_poke(self.m,0x1fe,ret&255)
  L.dos64_set_regs(self.m,Regs(self.at(n),0xfd,a,0x82,0x93,0x24,0,0))
  L.dos64_clear_writes(self.m)
  r=L.dos64_run(self.m,self.at('fixture_return'),budget)
  if r.status:raise AssertionError((n,r.status,hex(r.regs.pc),r.regs.cycles))
  if self.read('sp',2)!=b'\xff\xcf':raise AssertionError(('software stack imbalance',n,self.read('sp',2)))
  self.high=max(self.high,r.stack);self.calls+=1;self.guard()
  if r.stack>=120:raise AssertionError(('hardware stack bound',r.stack))
  return r.regs.a
 def control(self,owner=0xa5,home=HOME):self.write('_lc_control',bytes([owner])+struct.pack('<H',0xdf1c)+home.ljust(128,b'\0'))
 def seedfile(self,name,data):L.bulk_model_seed(self.m,name,data,len(data))
 def lc(self):return self.read('_lc_result',13)
 def poll_lc(self):
  self.tick+=1;self.write('_lc_now',struct.pack('<H',(500+self.tick//32)&65535));self.call('_lc_poll')
 def finish_lc(self):
  for _ in range(30000):
   if self.lc()[0]!=1:return self.lc()
   self.poll_lc()
  raise AssertionError('bounded launcher poll count')
 def seed_inputs(self,both=False):
  refs=sorted((ROOT/'reference').glob('*.img'));a=refs[0].read_bytes();b=refs[1].read_bytes() if both else None
  main,rel=release_fixture();config=cfg(a,b)
  for n,d in [(HOME+b'/DOS64.CFG',config),(HOME+b'/DOS64.REL',rel),(HOME+b'/DOS64.PRG',main),(A,a)]:self.seedfile(n,d)
  if b is not None:self.seedfile(B,b)
  self.control();self.write('_lc_now',struct.pack('<H',500));return a,b,main,rel,config
 def guard(self):
  smc=set()
  for n in ['uci_status_read','uci_control_write','uci_id_read','uci_command_write','uci_data_read','uci_stat_read','read','store']:smc.update([self.at(n)+1,self.at(n)+2])
  bs=self.at('__BSS_RUN__');be=self.at('__DEVICESTATE_RUN__')+self.at('__DEVICESTATE_SIZE__');zp_end=self.at('regbank')+6
  assert zp_end<=0x3e
  allowed=lambda a:a in [0,1] or 0x20<=a<zp_end or 0x100<=a<0x200 or bs<=a<be or self.at('_br_config')<=a<self.at('_br_config')+134 or 0xcd00<=a<0xd000 or 0xc000<=a<0xc800 or 0xc900<=a<0xcd00 or 0xdf00<=a<=0xdf0a or a in [0xdf1c,0xdf1d] or a in smc
  if not hasattr(self,'write_mask'):self.write_mask=bytes(int(allowed(a)) for a in range(65536))
  bad=L.lc_check_writes(self.m,self.write_mask)
  if bad!=65536:raise AssertionError(('unexpected native write',hex(bad)))
  if (L.dos64_peek(self.m,0)&7)!=7 or (L.dos64_peek(self.m,1)&7)!=5:raise AssertionError('RAM/I/O mapping changed')
class Actual(unittest.TestCase):
 def setUp(self):self.f=Controller()
 def tearDown(self):self.f.guard();self.f.close()
 def test_default_disabled_serialized_home_and_rejected_paths(self):
  f=self.f;self.assertEqual(f.read('_lc_control',1),b'\xff');self.assertEqual(f.call('_lc_begin'),0)
  for home in [b'/usb1//bad',b'/usb1/a/../b',b'/usb1/a.',b'/usb1/'+b'x'*120]:
   f.control(home=home);self.assertEqual(f.call('_lc_begin'),0)
  self.assertEqual(L.bulk_model_commands(f.m),0)
 def test_full_A_B_own_paths_verified_patch_and_anchor(self):
  f=self.f;a,b,main,rel,c=f.seed_inputs(True)
  self.assertEqual(f.call('_lc_begin'),1);self.assertEqual(f.call('_lc_begin'),0)
  # Public launch control changed after acceptance cannot redirect the run.
  f.control(owner=0,home=b'/usb1/wrong');r=f.finish_lc()
  self.assertEqual(r[:5],bytes([2,0,0,8,5]));self.assertEqual(f.result()[3],0)
  self.assertEqual(f.reu(0x100000,len(a)),a);self.assertEqual(f.reu(0x180000,len(b)),b)
  staged=f.reu(0x3e0000,len(main));n,h,flag=struct.unpack_from('<III',rel,28)
  spans=[(n,n+142),(h,h+140),(flag,flag+1)]
  for i,(old,new) in enumerate(zip(main,staged)):
   if old!=new:self.assertTrue(any(lo<=i<hi for lo,hi in spans),i)
  self.assertEqual(staged[n:n+10],b'D64N\xa5\x04\x01'+bytes([len(A)+1])+b'\x1c\xdf')
  self.assertEqual(staged[h:h+12],b'D64H\xa5\x01\x01\x00\x00\x02\x20'+bytes([len(HOME+b'/C.IMG')+1]))
  self.assertEqual(staged[flag],0xa5)
  head=f.reu(0x3ff000,32);self.assertEqual(head[:8],b'D64R\x01\xa5\x20\0')
  self.assertEqual(struct.unpack_from('<I',head,8)[0],zlib.crc32(c[:572]));self.assertEqual(struct.unpack_from('<I',head,12)[0],zlib.crc32(staged))
  self.assertEqual(head[16:24],c[528:536]);self.assertEqual(head[24:28],b'\x1c\xdf\x01\x02')
  self.assertEqual(struct.unpack_from('<I',head,28)[0],zlib.crc32(head[:28]));self.assertEqual(f.reu(0x3ff020,576),c)
  for name,data in [(HOME+b'/DOS64.CFG',c),(HOME+b'/DOS64.REL',rel),(HOME+b'/DOS64.PRG',main),(A,a),(B,b)]:
   out=C.create_string_buffer(len(data));self.assertTrue(L.bulk_model_read(f.m,name,out,len(data)));self.assertEqual(out.raw,data)
  self.assertEqual(L.bulk_model_commands(f.m),20)
 def test_wrong_CFG_size_closes_and_keeps_anchor_unready(self):
  f=self.f;f.seed_inputs();f.seedfile(HOME+b'/DOS64.CFG',b'x'*575);f.seed(b'\xa5',0x3ff005)
  self.assertEqual(f.call('_lc_begin'),1);r=f.finish_lc();self.assertEqual(r[:3],b'\x03\x03\0');self.assertEqual(f.reu(0x3ff005,1),b'\0');self.assertEqual(f.result()[3],0)
 def test_invalid_CFG_CRC_never_loads_main(self):
  f=self.f;*_,c=f.seed_inputs();b=bytearray(c);b[100]^=1;f.seedfile(HOME+b'/DOS64.CFG',bytes(b))
  self.assertEqual(f.call('_lc_begin'),1);self.assertEqual(f.finish_lc()[:3],b'\x03\x06\0');self.assertEqual(L.bulk_model_commands(f.m),4)
 def test_wrong_main_CRC_never_loads_A(self):
  f=self.f;_,_,main,rel,_=f.seed_inputs();bad=bytearray(main);bad[100]^=1;f.seedfile(HOME+b'/DOS64.PRG',bytes(bad))
  self.assertEqual(f.call('_lc_begin'),1);self.assertEqual(f.finish_lc()[:3],b'\x03\x04\0');self.assertEqual(L.bulk_model_commands(f.m),12);self.assertEqual(f.reu(0x3ff005,1),b'\0')
 def test_partial_LOAD_is_failure_and_cleanup_closes(self):
  f=self.f;f.seed_inputs();f.faults(short=3);self.assertEqual(f.call('_lc_begin'),1);r=f.finish_lc();self.assertEqual(r[:3],b'\x03\x02\0');self.assertEqual(f.result()[3],0);self.assertEqual(L.bulk_model_commands(f.m),4);self.assertEqual(f.read('_lc_result',16)[13:15],b'\x21\x05')
 def test_cancel_is_once_and_never_publishes(self):
  f=self.f;f.seed_inputs();self.assertEqual(f.call('_lc_begin'),1);f.call('_lc_cancel');f.call('_lc_cancel');r=f.finish_lc();self.assertEqual(r[0],3);self.assertEqual(r[1],8);self.assertEqual(f.reu(0x3ff005,1),b'\0');self.assertEqual(f.result()[3],0)
 def test_bad_release_CRC_never_loads_main(self):
  f=self.f;_,_,_,rel,_=f.seed_inputs();bad=bytearray(rel);bad[8]^=1;f.seedfile(HOME+b'/DOS64.REL',bytes(bad))
  self.assertEqual(f.call('_lc_begin'),1);self.assertEqual(f.finish_lc()[:3],b'\x03\x05\0');self.assertEqual(L.bulk_model_commands(f.m),8)
 def test_serialized_home_survives_BSS_startup_and_CFG_mismatch_fails(self):
  f=self.f;*_,c=f.seed_inputs();saved=f.read('_lc_control',131);f.call('runtime_init');f.call('_lc_init');self.assertEqual(f.read('_lc_control',131),saved);f.write('_lc_now',struct.pack('<H',500))
  bad=bytearray(c);path(bad,8,b'/usb1/Different Home');struct.pack_into('<I',bad,572,zlib.crc32(bad[:572]));f.seedfile(HOME+b'/DOS64.CFG',bytes(bad))
  self.assertEqual(f.call('_lc_begin'),1);self.assertEqual(f.finish_lc()[:3],b'\x03\x06\0');self.assertEqual(L.bulk_model_commands(f.m),4)
 def test_initial_REU_failure_cannot_leave_ready(self):
  f=self.f;f.seed_inputs();f.seed(b'\0',0x3ff005);L.dos64_reu_fail_after(f.m,0,0)
  self.assertEqual(f.call('_lc_begin'),1);self.assertEqual(f.lc()[:3],b'\x03\x07\0');self.assertEqual(f.reu(0x3ff005,1),b'\0');self.assertEqual(L.bulk_model_commands(f.m),0)
 def test_wrong_B_CRC_refuses_complete_configuration(self):
  f=self.f;*_,c=f.seed_inputs(True);bad=bytearray(c);bad[532]^=1;struct.pack_into('<I',bad,572,zlib.crc32(bad[:572]));f.seedfile(HOME+b'/DOS64.CFG',bytes(bad))
  self.assertEqual(f.call('_lc_begin'),1);r=f.finish_lc();self.assertEqual(r[:4],b'\x03\x04\0\x05');self.assertEqual(f.reu(0x3ff005,1),b'\0');self.assertEqual(f.result()[3],0)
if __name__=='__main__':unittest.main(verbosity=2)
