import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build_support'))
from dos_gwbasic_fixture import derive,REMOVE,SOURCE_SHA,BASIC_DISK_SHA
from dos_disk_inspect import Volume,sha
ROOT=Path(__file__).resolve().parents[2]
class GWBasicFixtureTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.a=(ROOT/'reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img').read_bytes()
  cls.b=(ROOT/'reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 3 of 3.img').read_bytes()
  cls.game=(ROOT/'build_support/dos_fixture_assets/hangman.bas').read_text().replace('\n','\r\n').encode('ascii')
 def test_complete_disposable_filesystem_and_payloads(self):
  raw,report=derive(self.a,self.b,self.game);v=Volume(raw);original=Volume(self.a)
  self.assertEqual(raw[:512],self.a[:512]);self.assertEqual(sha(self.a),SOURCE_SHA);self.assertEqual(sha(self.b),BASIC_DISK_SHA)
  self.assertEqual(set(v.payloads),set(original.payloads)-set(REMOVE)|{'GWBASIC.EXE','HANGMAN.BAS'})
  for name,data in original.payloads.items():
   if name not in REMOVE:self.assertEqual(v.payloads[name],data)
  self.assertEqual(v.payloads['GWBASIC.EXE'],Volume(self.b).payloads['GWBASIC.EXE'])
  self.assertEqual(v.payloads['HANGMAN.BAS'],self.game);self.assertEqual(v.free_clusters*v.spc*v.bps,report['free_bytes'])
  self.assertEqual(len(report['kept']),34)
 def test_source_identity_rejects_changed_boot_or_program(self):
  for disk in (0,1):
   values=[self.a,self.b];p=bytearray(values[disk]);p[100]^=1;values[disk]=bytes(p)
   with self.assertRaisesRegex(ValueError,'source identity'):derive(*values,self.game)
 def test_reject_non_ascii_bad_line_endings_and_oversize(self):
  for game in [b'',b'10 END\n',b'10 END\x00\r\n',b'\xff\r\n',b'1'+b' '*8192]:
   with self.assertRaises((ValueError,UnicodeDecodeError)):derive(self.a,self.b,game)
 def test_fixture_corruption_rejected_by_independent_volume(self):
  raw,_=derive(self.a,self.b,self.game);p=bytearray(raw);p[512+5]^=1
  with self.assertRaisesRegex(ValueError,'FAT size/copies'):Volume(p)
if __name__=='__main__':unittest.main()
