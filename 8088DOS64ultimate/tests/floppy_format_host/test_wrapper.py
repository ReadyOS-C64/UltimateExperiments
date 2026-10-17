from pathlib import Path
import sys,os
ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True;sys.pycache_prefix=str(ROOT/'build'/'.absent-format-host')
import importlib.util,json,tempfile,unittest
from unittest.mock import patch
s=importlib.util.spec_from_file_location('format_host',ROOT/'build_support/floppy_format_tests.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
REPORT=[]
class Host(unittest.TestCase):
 def setUp(self):
  (ROOT/'build').mkdir(exist_ok=True)
  self.tmp=tempfile.TemporaryDirectory(prefix='format-host-',dir=ROOT/'build');self.p=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def out(self,n):
  d=self.p/n;d.mkdir();(d/'OWNER.json').write_text(json.dumps(m.OWNER));(d/'RESULT.json').write_bytes(b'{"status":"passed","testfixture":"old unchanged"}\n');return d
 def check(self,d,old):self.assertEqual((d/'RESULT.json').read_bytes(),old)
 def test_ownedrun_creation_error_clears_ownlock_preservespointer(self):
  d=self.out('mkdir-fail');old=(d/'RESULT.json').read_bytes();primary=OSError('peer mkdir')
  with patch.object(m.tempfile,'mkdtemp',side_effect=primary):
   with self.assertRaises(OSError)as ex:m.build(d)
  self.assertIs(ex.exception,primary);self.check(d,old);self.assertFalse((d/'LOCK').exists());REPORT.append({'run_creation_error_firstcause_exact':True,'ownedlock_removed':True,'oldpointer_exact':True})
 def test_runtime_interrupt_and_report_failures_keep_primary(self):
  d=self.out('interrupt');old=(d/'RESULT.json').read_bytes();primary=KeyboardInterrupt('peer exact primary');real=m.atomic
  def atom(p,v):
   if p.name in ['FAILURE.json','LAST_FAILURE.json']:raise OSError('peer report failure')
   return real(p,v)
  with patch.object(m.runtime,'build',side_effect=primary),patch.object(m,'atomic',side_effect=atom):
   with self.assertRaises(KeyboardInterrupt)as ex:m.build(d)
  self.assertIs(ex.exception,primary);self.check(d,old);self.assertFalse((d/'LOCK').exists());REPORT.append({'interrupt_and_two_report_failures_primary_exact':True,'oldpointer_exact':True,'ownedlock_removed':True})
 def test_existing_lock_is_not_removed_or_overwritten(self):
  d=self.out('existing-lock');old=(d/'RESULT.json').read_bytes();(d/'LOCK').write_bytes(b'other live owner')
  with self.assertRaises(FileExistsError):m.build(d)
  self.check(d,old);self.assertEqual((d/'LOCK').read_bytes(),b'other live owner');REPORT.append({'foreign_lock_preserved':True,'oldpointer_exact':True})
 def test_lock_fd_close_failure_clears_ownlock_preserves_firstcause(self):
  d=self.out('fd-close');old=(d/'RESULT.json').read_bytes();primary=OSError('peer close failure');real=m.os.close
  # Exact host close boundary, no runtime/model/native execution or changed SUT.
  def close(fd):real(fd);raise primary
  with patch.object(m.os,'close',side_effect=close):
   with self.assertRaises(OSError)as ex:m.build(d)
  self.assertIs(ex.exception,primary);self.check(d,old);self.assertFalse((d/'LOCK').exists());REPORT.append({'lock_fd_close_firstcause_exact':True,'ownedlock_removed':True,'oldpointer_exact':True,'qualification':'first close failure remains exact; no orphan build lock'})
if __name__=='__main__':unittest.main(verbosity=2)
