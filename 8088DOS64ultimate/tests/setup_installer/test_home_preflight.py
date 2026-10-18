from pathlib import Path
import sys,os
sys.dont_write_bytecode=True
sys.pycache_prefix=str(Path(__file__).resolve().parent/('.absent-home-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import unittest,ctypes as C,struct,json,hashlib
from test_coordinator import Coordinator,L
REPORT={}
class Home(unittest.TestCase):
 def setUp(self):
  self.u=Coordinator();self.addCleanup(self.u.close);self.u.ui();self.u.ready();f=self.u.f
  # After authentic relocation/cache/UI entry, every live code byte is read-only.
  g=bytearray(f.guard)
  for name in ['UI_CODE','UI_RO','HIGH_CODE','AUX_CODE','AUX_RO']:
   at=f.labels['__'+name+'_RUN__'];n=f.labels['__'+name+'_SIZE__'];g[at:at+n]=bytes(n)
  f.guard=bytes(g)
 def mask(self,path):
  f=self.u.f;f.write('_d64_path_source',path.ljust(128,b'\0'));ptr=f.labels['_d64_path_source'];return f.call('_db_output_conflicts',ptr&255,x=ptr>>8)
 def scan(self,path,rows,first=0,folders=1):
  f=self.u.f;f.directory(path,rows);f.request(path=path,first=first,folders=folders);self.assertEqual(f.call('_db_begin'),1);self.assertEqual(self.mask(path),128)
  return self.finish()
 def finish(self):
  f=self.u.f;now=int.from_bytes(f.read('_db_now',2),'little')
  for i in range(20000):
   if f.call('_db_state')!=1:return f.call('_db_state')
   f.write('_db_now',struct.pack('<H',(now+i//32)&65535));f.call('_db_poll')
  self.fail('bounded directory completion')
 def test_all_raw_names_before_filter_page_and_casefold(self):
  f=self.u.f;before=L.bulk_model_commands(f.m);rows=[(16,('Folder %02d'%i).encode())for i in range(15)]+[(32,b'a.img'),(1,b'B.ImG'),(16,b'c.IMG'),(2,b'sTaRt.PrG'),(4,b'DoS64.CfG')]
  self.assertEqual(self.scan(b'/All',rows),2);self.assertEqual(self.mask(b'/All'),31);p=f.page();self.assertEqual((p['scanned'],p['total'],len(p['rows'])),(20,16,12));self.assertEqual(self.mask(b'/Other'),128)
  f.write('_db_result',bytes(10));f.write('_db_request',bytes(135));ptr=int.from_bytes(f.read('_db_page',2),'little');L.dos64_load(f.m,ptr,bytes(128),128)
  self.assertEqual(self.mask(b'/All'),31);self.assertEqual(L.bulk_model_commands(f.m),before)
  for name,bit in [(b'A.IMG',1),(b'B.IMG',2),(b'C.IMG',4),(b'START.PRG',8),(b'DOS64.CFG',16)]:
   self.assertEqual(self.scan(b'/One',[(32,name)]),2);self.assertEqual(self.mask(b'/One'),bit)
 def test_exact_raw_names_and_empty_directory(self):
  rows=[(32,n)for n in [b' A.IMG',b'A.IMG ',b'A.IMG.',b'AA.IMG',b'A.IMGx',b'XSTART.PRG',b'DOS64.CFG.old',b'A.IMG\0',b'X'*255]]
  self.assertEqual(self.scan(b'/Similar',rows),2);self.assertEqual(self.mask(b'/Similar'),0)
  self.assertEqual(self.scan(b'/Empty',[]),2);self.assertEqual(self.mask(b'/Empty'),0);self.assertEqual(self.mask(b'/Similar'),128)
 def test_late_status_failure_and_cancel_never_publish_partial_clear(self):
  f=self.u.f;self.assertEqual(self.scan(b'/Owned',[(32,b'A.IMG')]),2);self.assertEqual(self.mask(b'/Owned'),1)
  f.directory(b'/Next',[(32,('File%d'%i).encode())for i in range(20)]);L.dir_model_fault(f.m,0x14,19,1);f.request(path=b'/Next',folders=1);self.assertEqual(f.call('_db_begin'),1);self.assertEqual(self.finish(),3)
  f.write('_db_result',bytes([2])+bytes(9));self.assertEqual(self.mask(b'/Next'),128);self.assertEqual(self.mask(b'/Owned'),128)
  L.dir_model_fault(f.m,0,0,0);f.directory(b'/Cancel',[(32,b'B.IMG')]*20);f.request(path=b'/Cancel');self.assertEqual(f.call('_db_begin'),1);f.call('_db_cancel');self.assertEqual(self.finish(),3);self.assertEqual(self.mask(b'/Cancel'),128)
 def test_busy_public_forgery_and_rejected_request_are_path_bound(self):
  f=self.u.f;self.assertEqual(self.scan(b'/Good',[]),2);self.assertEqual(self.mask(b'/Good'),0)
  f.request(path=b'/Bad/..');self.assertEqual(f.call('_db_begin'),0);self.assertEqual(self.mask(b'/Bad/..'),128);self.assertEqual(self.mask(b'/Good'),0)
  f.directory(b'/Busy',[(32,b'A.IMG')]*20);f.request(path=b'/Busy');self.assertEqual(f.call('_db_begin'),1);f.write('_db_result',bytes([2])+bytes(9));self.assertEqual(self.mask(b'/Busy'),128);self.assertEqual(self.finish(),2);self.assertEqual(self.mask(b'/Busy'),1)
 def test_actual_F1_refuses_existing_home_then_accepts_fresh_home(self):
  u=self.u;f=u.f;u.directory(b'/Home',[(32,b'DOS 1.img'),(32,b'a.img'),(32,b'START.PRG')]);u.directory(b'/Fresh',[])
  # Existing root page has Home; refresh it through actual backspace after entry.
  u.key(0,1);self.assertEqual(f.page()['path'],b'/Home');before=L.bulk_model_commands(f.m);u.key(0,4)
  self.assertEqual(f.byte('_ss_stage'),0);self.assertEqual(u.choices()['paths'][0],b'');self.assertEqual(u.call('_rc_source_ready'),0)
  self.assertEqual(u.screen()[920:960],bytes(c-96 if 97<=c<=122 else c for c in b'Files exist; choose another home folder.').ljust(40,b' '));self.assertEqual(L.bulk_model_commands(f.m),before)
  u.directory(b'/',[(16,b'Home'),(16,b'Fresh')]);u.key(0,0);u.key(0,7);u.key(0,1);self.assertEqual(f.page()['path'],b'/Fresh');u.key(0,4)
  self.assertEqual(f.byte('_ss_stage'),1);self.assertEqual(u.choices()['paths'][0],b'/Fresh');self.assertEqual(L.bulk_model_commands(f.m),before)
  REPORT['F1']={'stage':f.byte('_ss_stage'),'home':u.choices()['paths'][0].decode(),'native':hashlib.sha256(Path('build/setup.prg').read_bytes()).hexdigest()}
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Home));Path('../HOME_PREFLIGHT_RESULTS.json').write_text(json.dumps(REPORT,indent=2)+'\n');sys.exit(not r.wasSuccessful())
