import unittest,tempfile,shutil
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"build_support"))
from verify_native_workflows import Fat12,verify
BASE=Path(__file__).resolve().parents[2]
SOURCE=(BASE/'reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img').read_bytes()
class OracleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.d=Path(self.tmp.name)
  for p in (BASE/'build').glob('workflow-*.img'):shutil.copyfile(p,self.d/p.name)
 def tearDown(self):self.tmp.cleanup()
 def mutate(self,step,fn):
  p=self.d/f'workflow-step-{step}.img';b=bytearray(p.read_bytes());fn(b);p.write_bytes(b)
 def rejected(self):
  with self.assertRaises(AssertionError):verify(self.d,SOURCE)
 def test_actual_checkpoint_sequence(self):self.assertEqual(verify(self.d,SOURCE)['final_free_bytes'],9216)
 def test_mirror_corruption_rejected(self):self.mutate(2,lambda b:b.__setitem__(512+10,b[522]^1));self.rejected()
 def test_original_metadata_change_rejected(self):
  fs=Fat12(SOURCE);off=fs.root_lba*512+next(i for i in range(0,fs.root_sectors*512,32) if SOURCE[fs.root_lba*512+i:][:11]==b'CONFIG  SYS')
  self.mutate(3,lambda b:b.__setitem__(off+21,b[off+21]^1));self.rejected()
 def test_original_data_change_rejected(self):
  fs=Fat12(SOURCE);e=fs.root['CONFIG.SYS'];off=(fs.data_lba+(e['cluster']-2)*fs.spc)*512
  self.mutate(3,lambda b:b.__setitem__(off,b[off]^1));self.rejected()
 def test_copied_data_change_rejected(self):
  fs=Fat12((self.d/'workflow-step-2.img').read_bytes());e=fs.directory(fs.root['D64TEST'])['T.TXT'];off=(fs.data_lba+(e['cluster']-2)*fs.spc)*512
  self.mutate(2,lambda b:b.__setitem__(off,b[off]^1));self.rejected()
 def test_deleted_file_resurrection_rejected(self):
  fs=Fat12((self.d/'workflow-step-7.img').read_bytes());off=(fs.data_lba+(fs.root['D64TEST']['cluster']-2)*fs.spc)*512+64
  self.mutate(7,lambda b:b.__setitem__(off,ord('R')));self.rejected()
 def test_directory_not_removed_rejected(self):shutil.copyfile(self.d/'workflow-step-9.img',self.d/'workflow-step-10.img');self.rejected()
 def test_missing_sector_rejected(self):
  p=self.d/'workflow-step-4.img';p.write_bytes(p.read_bytes()[:-512]);self.rejected()
 def test_deleted_slack_permitted(self):
  fs=Fat12((self.d/'workflow-step-10.img').read_bytes());cluster=Fat12((self.d/'workflow-step-0.img').read_bytes()).root['D64TEST']['cluster'];offset=(fs.data_lba+(cluster-2)*fs.spc)*512+500
  for name in ['workflow-step-10.img','workflow-final.img']:
   p=self.d/name;b=bytearray(p.read_bytes());b[offset]^=123;p.write_bytes(b)
  self.assertEqual(verify(self.d,SOURCE)['final_free_bytes'],9216)
if __name__=='__main__':unittest.main()
