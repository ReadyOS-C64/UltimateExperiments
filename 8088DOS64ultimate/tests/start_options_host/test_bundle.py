import sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True;sys.pycache_prefix=str(ROOT/'build'/('.absent-bundle-host-test-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import importlib.util,json,shutil,struct,tempfile,unittest,zlib
from unittest.mock import patch
s=importlib.util.spec_from_file_location('bundle_sut',ROOT/'build_support/start_ini_bundle.py');b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
class Bundle(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.r=json.loads((ROOT/'build/start-ini-bundle/RESULT.json').read_text());cls.release_run=Path(cls.r['run']);cls.labels=cls.release_run/'start/controller.labels';cls.map=cls.release_run/'start/controller.map';cls.mainlabels=cls.release_run/'main/build/dos64.labels';cls.mods={n:b.module('test_'+n,q)for n,q in b.dependencies().items()}
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.p=Path(self.t.name)/'bundle';shutil.copytree(self.release_run/'bundle',self.p)
 def tearDown(self):self.t.cleanup()
 def validate(self):return b.validate_bundle(self.p,self.labels,self.map,self.mainlabels,self.mods)
 def test_exact_real_five_assets_reproduce_matched_component(self):
  self.assertEqual(self.validate()['D64L_version'],2)
  expected={'START.TPL':'79bb0470','START.REL':'45b68eaf','START.INO':'eebb43ac','DOS64.PRG':'666089b5','DOS64.REL':'9eb1cd3a'}
  for n,h in expected.items():self.assertTrue(b.digest(self.p/n)['sha256'].startswith(h),n)
 def test_omitted_overlay_or_partial_extra_asset_refused(self):
  (self.p/'START.INO').unlink()
  with self.assertRaises(RuntimeError):self.validate()
  shutil.copyfile(self.release_run/'bundle/START.INO',self.p/'START.INO');(self.p/'START.PRG').write_bytes(b'x')
  with self.assertRaises(RuntimeError):self.validate()
 def test_every_mismatched_asset_is_refused(self):
  for n in b.ASSETS:
   q=self.p/n;old=q.read_bytes();bad=bytearray(old);bad[-1]^=1;q.write_bytes(bad)
   with self.assertRaises((RuntimeError,ValueError),msg=n):self.validate()
   q.write_bytes(old)
 def test_resigned_wrong_overlay_capsule_is_not_just_templateCRC_valid(self):
  q=self.p/'START.TPL';v=bytearray(q.read_bytes());at=self.validate()['capsule_file_offset'];v[at+8]^=1;q.write_bytes(v);(self.p/'START.REL').write_bytes(self.mods['template'].make(v,self.labels.read_text(),self.map.read_text()))
  with self.assertRaisesRegex(RuntimeError,'Overlay'):self.validate()
 def test_configured_template_cannot_replace_unconfigured_release(self):
  q=self.p/'START.TPL';d=(self.p/'START.REL').read_bytes();q.write_bytes(self.mods['template'].patch(d,q.read_bytes(),b'/Changed'))
  with self.assertRaises(ValueError):self.validate()
 def test_defaultv1_remains_reservedzero_and_newbundle_rejectsit(self):
  old=self.mods['release'].descriptor((self.p/'DOS64.PRG').read_bytes(),self.mainlabels.read_text());self.assertEqual(old[4],1);self.assertEqual(old[56:60],bytes(4));(self.p/'DOS64.REL').write_bytes(old)
  with self.assertRaises(RuntimeError):self.validate()
 def test_missing_or_wrong_capsule_DATA_address_refused(self):
  original=self.labels;self.labels=Path(self.t.name)/'changed.labels';text=original.read_text();text='\n'.join(l for l in text.splitlines()if not l.endswith('._so_overlay_spec'))+'\nal 006000 ._so_overlay_spec\n';self.labels.write_text(text)
  with self.assertRaises(RuntimeError):self.validate()
 def test_actual_failed_main_build_cannot_replace_previous_complete_result(self):
  out=Path(self.t.name)/'result';out.mkdir();prior=b'{"status":"passed","prior":"independent previously complete release"}\n';(out/'RESULT.json').write_bytes(prior)
  with patch.dict(os.environ,{'DOS64_MAKE':'/usr/bin/false'}):
   with self.assertRaises(Exception):b.build(out)
  self.assertEqual((out/'RESULT.json').read_bytes(),prior);runs=list(out.glob('run-*'));self.assertEqual(len(runs),1);self.assertTrue((runs[0]/'FAILURE.json').is_file());self.assertFalse((runs[0]/'RESULT.json').exists());self.assertFalse(list((runs[0]/'bundle').iterdir()))
if __name__=='__main__':unittest.main(verbosity=2)
