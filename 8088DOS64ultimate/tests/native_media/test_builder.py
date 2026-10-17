from pathlib import Path
import sys,os
ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True;sys.pycache_prefix=str(ROOT/'build'/('.absent-media-builder-test-'+str(os.getpid())))
if Path(sys.pycache_prefix).exists():raise RuntimeError('Source-only test cache prefix must be absent')
import importlib.util,unittest,tempfile,json,hashlib,shutil,subprocess
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('native_media_builder_source',ROOT/'build_support/native_media_tests.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='native-media-host-',dir=ROOT/'build');self.p=Path(self.temp.name);self.out=self.p/'out'
 def tearDown(self):self.temp.cleanup()
 def baseline(self):
  with patch.dict(os.environ,{'DOS64_ZIG':'/absent/optional/zig','DOS64_CLANGXX':'/absent/optional/clang'}):r=M.build(self.out,test=False)
  self.assertEqual(r['products']['dos64.prg']['sha256'],'46fa2e54275818c1d946400c06c3e23bfd1c066c33fa967c399d39270d7f554f');return (self.out/'RESULT.json').read_bytes(),{q['path']:Path(q['path']).read_bytes()for q in r['products'].values()}
 def unchanged(self,before):
  self.assertEqual((self.out/'RESULT.json').read_bytes(),before[0])
  for s,b in before[1].items():self.assertEqual(Path(s).read_bytes(),b)
 def test_01_real_native_only_ignores_optional_tools_and_default_exact(self):
  self.baseline();r=M.build(self.p/'default',test=False,default=True);self.assertEqual(r['products']['dos64.prg']['sha256'],'666089b57e5611a67b5d87ae84880256ef5dafb121b152e1de81b9ec1cc29064');self.assertEqual(r['products']['dos64-tests.prg']['sha256'],'b9e9cc9e7d87176848ccf8bae49dfe4f4ff0125b3aad5a1cb874341436b78df6')
 def test_02_partial_publish_copy_failure_preserves_previous(self):
  before=self.baseline();primary=OSError('copy-primary');real=shutil.copyfile
  def copy(s,d,*a,**kw):
   if Path(d).parent.name=='products'and Path(d).name=='dos64-tests.prg':raise primary
   return real(s,d,*a,**kw)
  with patch.object(M.shutil,'copyfile',copy):
   try:M.build(self.out,test=False);self.fail('expected failure')
   except OSError as e:self.assertIs(e,primary)
  self.unchanged(before);self.assertFalse((self.out/'LOCK').exists())
 def test_03_interrupt_during_publication_preserves_previous(self):
  before=self.baseline();primary=KeyboardInterrupt('atomic-primary');real=os.replace
  def replace(s,d):
   if Path(d)==self.out/'RESULT.json':raise primary
   return real(s,d)
  with patch.object(M.os,'replace',replace):
   try:M.build(self.out,test=False);self.fail('expected interrupt')
   except KeyboardInterrupt as e:self.assertIs(e,primary)
  self.unchanged(before);j=json.loads((self.out/'LAST_FAILURE.json').read_text());self.assertEqual(j['phase'],'publication');self.assertFalse((self.out/'LOCK').exists())
 def test_04_primary_survives_both_reporting_interrupts(self):
  before=self.baseline();primary=KeyboardInterrupt('run-result-primary');secondary=OSError('secondary-report');real=M.atomic_json
  def write(p,j):
   if p.name=='RESULT.json'and p.parent.name.startswith('run-'):raise primary
   if p.name in ['FAILURE.json','LAST_FAILURE.json']:raise secondary
   return real(p,j)
  with patch.object(M,'atomic_json',write):
   try:M.build(self.out,test=False);self.fail('expected interrupt')
   except KeyboardInterrupt as e:self.assertIs(e,primary)
  self.unchanged(before);self.assertFalse((self.out/'LOCK').exists())
 def test_05_run_creation_failure_cleans_owned_lock(self):
  before=self.baseline();primary=OSError('mkdir-primary')
  with patch.object(M.tempfile,'mkdtemp',side_effect=primary):
   try:M.build(self.out,test=False);self.fail('expected failure')
   except OSError as e:self.assertIs(e,primary)
  self.unchanged(before);self.assertFalse((self.out/'LOCK').exists())
 def test_06_unlock_failure_is_honest_and_does_not_publish(self):
  before=self.baseline();primary=OSError('unlink-primary');real=Path.unlink
  def unlink(p,*a,**kw):
   if p==self.out/'LOCK':raise primary
   return real(p,*a,**kw)
  with patch.object(Path,'unlink',unlink):
   try:M.build(self.out,test=False);self.fail('expected failure')
   except OSError as e:self.assertIs(e,primary)
  self.unchanged(before);self.assertTrue((self.out/'LOCK').exists());(self.out/'LOCK').unlink()
 def test_07_first_interrupt_survives_atomic_temp_cleanup_failure(self):
  q=self.p/'atomic.json';q.write_text('old');primary=KeyboardInterrupt('write-primary');secondary=OSError('unlink-secondary');write=Path.write_text;unlink=Path.unlink
  def w(p,*a,**kw):
   if p.name.startswith('atomic.json.tmp-'):write(p,*a,**kw);raise primary
   return write(p,*a,**kw)
  def u(p,*a,**kw):
   if p.name.startswith('atomic.json.tmp-'):raise secondary
   return unlink(p,*a,**kw)
  with patch.object(Path,'write_text',w),patch.object(Path,'unlink',u):
   try:M.atomic_json(q,{'new':1});self.fail('expected interrupt')
   except KeyboardInterrupt as e:self.assertIs(e,primary)
  self.assertEqual(q.read_text(),'old')
 def test_08_staged_source_change_before_closure_rejects(self):
  before=self.baseline();native=M.native
  def change(work,*a,**kw):
   r=native(work,*a,**kw);f=work/'src/native_save.s';f.write_text(f.read_text()+'\n; changed\n');return r
  with patch.object(M,'native',change):
   with self.assertRaisesRegex(RuntimeError,'Source/product changed'):M.build(self.out,test=False)
  self.unchanged(before)
 def test_09_bad_owner_lease_and_inventory_path_reject(self):
  self.out.mkdir();(self.out/'unrelated').write_text('keep')
  with self.assertRaisesRegex(RuntimeError,'empty'):M.build(self.out,test=False)
  self.assertEqual((self.out/'unrelated').read_text(),'keep')
  for s in ['../escape','/absolute','work/../escape','work\\evil','work//bad','./bad']:
   with self.assertRaises(RuntimeError):M.safe_relative(s)
 def test_10_environment_scrub_and_explicit_tool_resolution(self):
  bad={n:'poison'for n in ['PYTHONPATH','PYTHONPYCACHEPREFIX','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG','CPATH','MAKEFLAGS','ZIG_LIB_DIR']}
  with patch.dict(os.environ,bad):e=M.command_environment(self.p,{'ca65':Path('/fixed/ca65')})
  for n in bad:self.assertNotIn(n,e)
  self.assertEqual(e['DOS64_CA65'],'/fixed/ca65');self.assertEqual(e['ZIG_GLOBAL_CACHE_DIR'],str(self.p/'.zig-global-cache'))
 def test_11_native_inventory_has_no_vendor_media_or_private_paths(self):
  j=json.loads((ROOT/'build_support/native_media_sources.json').read_text())
  for mapping in [j['native'],j['test']]:
   for dest,src in mapping.items():
    self.assertNotIn('agentworking',src);self.assertNotIn('reference/',src);self.assertNotIn(Path(src).suffix.lower(),['.img','.exe','.com','.prg','.dylib','.so','.o']);self.assertTrue((ROOT/src).is_file())
 def test_12_existing_selected_cache_prefix_rejects_before_output(self):
  prefix=ROOT/'build/.absent-native-media-424242';self.assertFalse(prefix.exists());prefix.mkdir()
  try:
   code="import os,runpy;os.getpid=lambda:424242;runpy.run_path("+repr(str(ROOT/'build_support/native_media_tests.py'))+",run_name='__main__')"
   r=subprocess.run([sys.executable,'-B','-c',code,'--native-only','--out',str(self.out)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   self.assertNotEqual(r.returncode,0);self.assertIn(b'cache prefix must be absent',r.stderr);self.assertFalse(self.out.exists())
  finally:prefix.rmdir()
 def test_13_product_source_mutation_after_copy_rejects_before_pointer(self):
  before=self.baseline();real=shutil.copyfile
  def copy(s,d,*a,**kw):
   r=real(s,d,*a,**kw)
   if Path(d).parent.name=='products'and Path(d).name=='dos64.prg':
    q=Path(s);b=bytearray(q.read_bytes());b[-1]^=1;q.write_bytes(b)
   return r
  with patch.object(M.shutil,'copyfile',copy):
   with self.assertRaisesRegex(RuntimeError,'Source/product changed'):M.build(self.out,test=False)
  self.unchanged(before)
if __name__=='__main__':
 (ROOT/'build').mkdir(exist_ok=True);r=unittest.main(exit=False,verbosity=2).result
 report={'successful':r.wasSuccessful(),'tests':r.testsRun};(ROOT/'build/native-media-host-result.json').write_text(json.dumps(report,indent=2)+'\n');sys.exit(not r.wasSuccessful())
