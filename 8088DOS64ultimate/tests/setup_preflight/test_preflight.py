from pathlib import Path
import sys,os
D=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(D/'.absent-preflight-cache');assert not Path(sys.pycache_prefix).exists()
import ctypes as C,json,unittest,zlib,struct
from test_coordinator import Coordinator,L
from test_source_load import DATA,PATHS
ASSETS={n:(D/'release-assets'/n).read_bytes()for n in ['START.TPL','START.REL','DOS64.PRG','DOS64.REL','START.INO']}
ALLPATH=PATHS+[b'/Home/DOS64.PRG',b'/Home/DOS64.REL',b'/Home/START.INO']
ALLDATA=DATA[:3]+[ASSETS[n]for n in ['START.TPL','START.REL','DOS64.PRG','DOS64.REL','START.INO']]
for n,r,a in [('bulk_model_commands',C.c_uint32,[C.c_void_p]),('bulk_model_command',C.c_uint8,[C.c_void_p,C.c_uint32,C.c_uint32]),('bulk_model_open',C.c_uint8,[C.c_void_p,C.c_uint8])]:
 f=getattr(L,n);f.restype=r;f.argtypes=a
REPORT=[]
class Native(Coordinator):
 def seed(self):
  for path,data in zip(ALLPATH,ALLDATA):L.bulk_model_seed(self.f.m,path,data,len(data))
 def wire(self):
  out=[]
  for i in range(L.bulk_model_commands(self.f.m)):
   target=L.bulk_model_command(self.f.m,i,0);op=L.bulk_model_command(self.f.m,i,1);mode=L.bulk_model_command(self.f.m,i,2);name=bytes(L.bulk_model_command(self.f.m,i,j)for j in range(3,131)).split(b'\0')[0]
   out.append((target,op,mode,name))
  return out
 def no_create(self):assert not any(op==5 or(op==2 and mode&4)for _,op,mode,_ in self.wire())
class Tests(unittest.TestCase):
 def make(self):u=Native();self.addCleanup(u.close);return u
 def test_01_true_SYS_CIA_eight_sources_before_FAT_or_any_CREATE(self):
  u=self.make();u.select();self.assertEqual(u.finish(),4);self.assertEqual(u.call('_rc_error'),0);self.assertEqual(u.call('_bc_files_closed'),1);self.assertEqual(u.call('_rc_source_ready'),1);u.no_create()
  opened=[name for _,op,mode,name in u.wire()if op==2]
  for name in ALLPATH:self.assertEqual(opened.count(name),2,name)
  self.assertEqual(struct.unpack_from('<5I',u.f.read('_rc_retained',183),134),tuple(zlib.crc32(x)for x in ALLDATA[:5]))
  REPORT.append({'case':'true_SYS_CIA_eight_sources','native_state':4,'creates':0,'source_opens_each':2,'readonly':all(mode==1 for _,op,mode,_ in u.wire()if op==2)})
 def test_02_missing_new_runtime_asset_fails_before_CREATE(self):
  for k in [5,6,7]:
   u=Native()
   try:
    # Zero-length stand-in models absent/wrong INFO independently of loader.
    L.bulk_model_seed(u.f.m,ALLPATH[k],b'',0);u.select();self.assertEqual(u.finish(),5);self.assertEqual(u.call('_rc_error'),0x32);self.assertEqual(u.call('_bc_files_closed'),1);self.assertEqual(u.call('_rc_source_ready'),0);u.no_create()
   finally:u.close()
 def test_03_resigned_descriptor_same_full_CRC_is_rejected_before_CREATE(self):
  for k in [4,6]:
   u=Native()
   try:
    data=bytearray(ALLDATA[k]);data[12]^=1;data[60:64]=struct.pack('<I',zlib.crc32(data[:60]));self.assertEqual(zlib.crc32(data),zlib.crc32(ALLDATA[k]));L.bulk_model_seed(u.f.m,ALLPATH[k],bytes(data),len(data));u.select();self.assertEqual(u.finish(),5);self.assertEqual(u.call('_rc_error'),0x38);self.assertEqual(u.call('_bc_files_closed'),1);u.no_create()
   finally:u.close()
 def test_04_corrupt_main_and_overlay_are_rejected_before_CREATE(self):
  for k in [5,7]:
   u=Native()
   try:
    data=bytearray(ALLDATA[k]);data[-1]^=1;L.bulk_model_seed(u.f.m,ALLPATH[k],bytes(data),len(data));u.select();self.assertEqual(u.finish(),5);self.assertEqual(u.call('_rc_error'),0x38);u.no_create()
   finally:u.close()
if __name__=='__main__':
 r=unittest.main(exit=False,verbosity=2).result;(D/'PREFLIGHT_RESULTS.json').write_text(json.dumps({'passed':r.wasSuccessful(),'tests':r.testsRun,'receipts':REPORT},indent=2)+'\n');sys.exit(not r.wasSuccessful())
