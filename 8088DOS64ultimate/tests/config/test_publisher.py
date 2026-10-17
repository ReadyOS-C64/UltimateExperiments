from pathlib import Path
import sys,os
sys.dont_write_bytecode=True;sys.pycache_prefix=str(Path.cwd()/('.absent-publisher-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import ctypes as C,struct,zlib,json,hashlib,unittest
from test_config_ui import UI
from config_fixture import L,REPORT
P=Path.cwd();assert P.name=='work'
def hd():
 b=bytearray(2097152);b[446:454]=bytes([128,1,1,0,1,1,0x10,127]);struct.pack_into('<II',b,454,16,4080);b[510:512]=b'\x55\xaa';o=8192;struct.pack_into('<H',b,o+11,512);b[o+13]=8;struct.pack_into('<H',b,o+14,1);b[o+16]=2;struct.pack_into('<HH',b,o+17,512,4080);b[o+21]=248;struct.pack_into('<HHHII',b,o+22,2,16,2,16,0);b[o+510:o+512]=b'\x55\xaa';return bytes(b)
A=bytes((i*17+(i>>8)*13+3)&255 for i in range(368640));B=bytes((i*29+(i>>9)+71)&255 for i in range(368640))
class Pipeline:
 def __init__(self,columns=80):
  self.u=UI(stale=(1,2));self.f=self.u.f;f=self.f
  for path,data in [(b'/usb1/Media/A.IMG',A),(b'/sd/Media/B.IMG',B),(b'/usb1/HD/C.IMG',hd())]:L.bulk_model_seed(f.m,path,data,len(data))
  assert self.u.finish(columns)==6
  r=self.u.receipt();self.original=self.u.original;self.session=r['session'];self.columns=columns
  f.write('_rm_request',b'\xa5'+struct.pack('<HH',2000,self.session)+b'/Existing'.ljust(128,b'\0'));assert f.call('_rm_begin',budget=10000000)==1
  for i in range(100000):
   L.dos64_cia_clock_advance(f.m,1024);f.call('_rm_poll');s=f.call('_rm_state')
   if s!=1:break
  assert s==2,('RM',f.read('_rm_result',11),i)
  for p in (P/'release-assets').iterdir():L.bulk_model_seed(f.m,b'/Release/'+p.name.encode(),p.read_bytes(),p.stat().st_size)
  self.before=f.commands();f.write('_cp_request',b'\xa5'+struct.pack('<H',4000))
 def close(self):self.u.close()
 def begin(self):return self.f.call('_cp_begin',budget=10000000)
 def poll(self):L.dos64_cia_clock_advance(self.f.m,1024);self.f.call('_cp_poll',budget=100000000);return self.f.call('_cp_state')
 def finish(self):
  for i in range(20000):
   s=self.poll()
   if s!=1:return s
  raise AssertionError(('CP bound',self.f.read('_cp_result',12),len(self.f.commands())))
 def readfile(self,n):
  name=b'/New launch/'+n.encode();n=L.bulk_model_size(self.f.m,name);b=C.create_string_buffer(n);assert L.bulk_model_read(self.f.m,name,b,n);return b.raw
class Publisher(unittest.TestCase):
 def make(self,**kw):p=Pipeline(**kw);self.addCleanup(p.close);return p
 def full(self,columns):
  p=self.make(columns=columns);f=p.f;self.assertEqual(p.begin(),1);self.assertEqual(p.finish(),2,(f.read('_cp_result',12),f.commands()[-10:]))
  self.assertEqual(f.call('_cp_get'),1);self.assertEqual(f.call('_cp_error'),0);self.assertEqual(f.call('_cp_closed_quiet'),1)
  self.assertEqual(f.read('_cp_result',12)[7],63)
  expected={n:(P/'release-assets'/n).read_bytes()for n in ['DOS64.PRG','DOS64.REL','START.INO']}
  tpl=bytearray((P/'release-assets/START.TPL').read_bytes());d=(P/'release-assets/START.REL').read_bytes();at=int.from_bytes(d[24:28],'little');tpl[at:at+131]=b'\xa5\x1c\xdf'+b'/New launch'.ljust(128,b'\0');expected['START.PRG']=bytes(tpl)
  expected['DOS64.INI']=b'[emulator]\r\ninitial_columns='+str(columns).encode()+b'\r\n'
  cfg=bytearray(p.original);cfg[8:136]=b'/New launch'.ljust(128,b'\0');struct.pack_into('<II',cfg,528,zlib.crc32(A),zlib.crc32(B));struct.pack_into('<I',cfg,572,zlib.crc32(cfg[:572]));expected['DOS64.CFG']=bytes(cfg)
  for n,b in expected.items():self.assertEqual(p.readfile(n),b,n)
  self.assertEqual([L.bulk_model_open(f.m,t)for t in [1,2]],[0,0]);self.assertEqual(f.commands().count(b'\2\x22'),6)
  for n,b in [(b'/Existing/DOS64.CFG',p.original),(b'/usb1/Media/A.IMG',A),(b'/sd/Media/B.IMG',B)]:o=C.create_string_buffer(len(b));self.assertEqual(L.bulk_model_read(f.m,n,o,len(b)),1);self.assertEqual(o.raw,b)
  out=P.parent/('full-output-'+str(columns));out.mkdir(exist_ok=True)
  for n in expected:(out/n).write_bytes(p.readfile(n))
  REPORT['full_pipeline_'+str(columns)]={'commands':len(f.commands()),'outputs':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}for n,b in expected.items()}}
 def test_full_native_CG_RI_RM_sources_six_outputs_CFG_last(self):self.full(80)
 def test_full_native_selected_40_columns_is_exact_same_home_INI(self):self.full(40)
 def test_public_CG_RM_results_cannot_authorize_without_private_completion(self):
  u=UI();self.addCleanup(u.close);f=u.f;before=f.commands();f.write('_cp_request',b'\xa5'+struct.pack('<H',4000));f.write('_cg_result',b'\6'+bytes(6)+b'\xa5');f.write('_cg_receipt',bytes(429));f.write('_rm_result',b'\2'+bytes(10));f.write('_rm_receipt',bytes(594));f.write('_cp_result',b'\2'+bytes(6)+b'\x3f'+bytes(4));self.assertEqual(f.call('_cp_begin'),0);self.assertEqual(f.call('_cp_get'),0);self.assertEqual(f.commands(),before)
 def test_frozen_transport_CANCEL_drain_is_256_and_never_ready(self):
  p=self.make();f=p.f;self.assertEqual(p.begin(),1);L.dos64_uci_model_stuck(f.m,1);f.call('_cp_cancel')
  for count in range(258):
   f.call('_cp_poll')
   if f.call('_cp_state')!=1:break
  self.assertLessEqual(count+1,256);self.assertEqual(f.call('_cp_state'),3);self.assertEqual(f.call('_cp_error'),7);self.assertEqual(f.call('_cp_get'),0);self.assertEqual(f.call('_cp_closed_quiet'),0)
 def test_re_signed_wrong_release_descriptor_refuses_before_CREATE(self):
  p=self.make();f=p.f;d=bytearray((P/'release-assets/DOS64.REL').read_bytes());d[20]^=1;struct.pack_into('<I',d,60,zlib.crc32(d[:60]));L.bulk_model_seed(f.m,b'/Release/DOS64.REL',bytes(d),64)
  self.assertEqual(p.begin(),1);self.assertEqual(p.finish(),3);self.assertEqual(f.call('_cp_error'),11);self.assertEqual(f.call('_cp_get'),0);self.assertEqual(f.call('_cp_closed_quiet'),1);self.assertFalse(any(c[0]==2 and c[1]in[2,0x22]for c in f.commands()[len(p.before):]))
 def test_CREATE_NEW_conflict_preserves_old_file_and_no_CFG(self):
  p=self.make();f=p.f;existing=b'KEEP ME';L.bulk_model_seed(f.m,b'/New launch/DOS64.PRG',existing,len(existing));self.assertEqual(p.begin(),1);self.assertEqual(p.finish(),3);self.assertEqual(f.call('_cp_error'),3);self.assertEqual(f.call('_cp_closed_quiet'),1);self.assertEqual(p.readfile('DOS64.PRG'),existing);self.assertEqual(L.bulk_model_size(f.m,b'/New launch/DOS64.CFG'),0xffffffff);self.assertEqual(f.call('_cp_get'),0)
 def test_native_source_LOAD_corruption_never_CREATES_even_if_public_ready_forged(self):
  p=self.make();f=p.f;L.bulk_model_faults(f.m,-1,-1,-1,0,0);self.assertEqual(p.begin(),1);self.assertEqual(p.finish(),3);self.assertEqual(f.call('_cp_error'),6);f.write('_cp_result',b'\2'+bytes(6)+b'\x3f'+bytes(4));f.write('_cg_receipt',bytes(429));self.assertEqual(f.call('_cp_get'),0);self.assertFalse(any(c[0]==2 and c[1]in[2,0x22]for c in f.commands()[len(p.before):]));self.assertEqual(f.call('_cp_closed_quiet'),1)
 def test_cancellation_during_source_READ_drains_and_closes_without_CFG(self):
  p=self.make();f=p.f;self.assertEqual(p.begin(),1)
  for _ in range(3000):
   p.poll()
   if f.read('_cp_result',12)[2]==5:break
  else:self.fail('source READ not reached')
  L.dos64_host_input_model_keys(f.m,bytes(7)+b'\x80');self.assertEqual(p.finish(),3);self.assertEqual(f.call('_cp_error'),7);self.assertEqual(f.call('_cp_closed_quiet'),1);self.assertEqual(f.call('_cp_get'),0);self.assertEqual(L.bulk_model_size(f.m,b'/New launch/DOS64.CFG'),0xffffffff)
 def test_failed_last_known_CLOSE_never_mints_completion(self):
  p=self.make();f=p.f;self.assertEqual(p.begin(),1)
  for _ in range(20000):
   p.poll();r=f.read('_cp_result',12)
   if r[3]==5 and r[2]==6:break
   self.assertEqual(f.call('_cp_state'),1,r)
  else:self.fail('final EOF not reached')
  # EOF command may not yet be pushed. Preserve it, fail the following CLOSE.
  while bytes(L.bulk_model_command(f.m,len(f.commands())-1,j)for j in range(4))!=b'\2\4\1\0':p.poll()
  n=len(f.commands());L.bulk_model_faults(f.m,n+1,-1,-1,0,-1);self.assertEqual(p.finish(),3);self.assertEqual(f.call('_cp_error'),3);self.assertEqual(f.call('_cp_closed_quiet'),0);self.assertEqual(L.bulk_model_open(f.m,2),1);f.write('_cp_result',b'\2'+bytes(6)+b'\x3f'+bytes(4));self.assertEqual(f.call('_cp_get'),0);self.assertEqual(f.commands().count(b'\2\3'),13)
if __name__=='__main__':
 result=unittest.main(exit=False).result
 REPORT['tests_run']=result.testsRun;REPORT['successful']=result.wasSuccessful()
 (P.parent/'PUBLISHER_TEST_REPORT.json').write_text(json.dumps(REPORT,indent=2)+'\n')
 sys.exit(0 if result.wasSuccessful() and result.testsRun else 1)
