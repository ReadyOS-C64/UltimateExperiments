"""Opt-in host controls; native fixture is built by setup_preflight_tests.py."""
from pathlib import Path
import sys,os
ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True;sys.pycache_prefix=str(ROOT/'build'/('.absent-preflight-host-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import importlib.util,json,unittest,tempfile,shutil,subprocess,struct,zlib,py_compile
spec=importlib.util.spec_from_file_location('preflight_builder',ROOT/'build_support/setup_installer.py');S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)
class Binding(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  path=os.environ.get('DOS64_SETUP_PREFLIGHT_FIXTURE')
  if not path:raise RuntimeError('Run the opt-in setup-installer-preflight-tests target')
  cls.fixture=json.loads(Path(path).read_text());cls.bound=json.loads(Path(cls.fixture['bound_result']).read_text());cls.baseline=json.loads(Path(cls.fixture['default_result']).read_text());cls.work=Path(cls.fixture['work'])
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=self.work.parent);self.p=Path(self.tmp.name);j=json.loads(Path(self.bound['release']['archived_result']).read_text());origin=Path(j['run']);run=self.p/'coupled';shutil.copytree(Path(j['bundle']),run/'bundle')
  for n in ['start/controller.labels','start/controller.map','main/build/dos64.labels']:
   p=run/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(origin/n,p)
  j.update(run=str(run),bundle=str(run/'bundle'));self.result=self.p/'coupled.json';self.result.write_text(json.dumps(j,indent=2)+'\n');self.j=j;self.bundle=run/'bundle'
 def tearDown(self):self.tmp.cleanup()
 def bind(self):
  work=Path(tempfile.mkdtemp(prefix='bind-',dir=self.p));record={};r=S.bind_release(self.result,work,record);S.verify(record);return r,work,record
 def edit(self):self.result.write_text(json.dumps(self.j,indent=2)+'\n')
 def cli(self,out,*args,env=None):return subprocess.run([sys.executable,'-B',ROOT/'build_support/setup_installer.py','--out',out,*args],cwd=ROOT,env=env or os.environ,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 def test_01_native_fixture_is_source_produced_and_release_bound(self):
  self.assertTrue(self.bound['runtime_preflight']);self.assertFalse(self.baseline['runtime_preflight']);self.assertNotEqual(S.digest(Path(self.bound['work'])/'build/setup.prg'),S.digest(Path(self.baseline['work'])/'build/setup.prg'))
  self.assertTrue(any(Path(n).name=='release_assets.h'for n in self.bound['source_inputs']));r,work,record=self.bind();self.assertEqual(r['assets'],self.j['assets']);self.assertEqual(r['result_identity'],S.digest(self.result));self.assertIn(str(work/'release_assets.h'),record)
 def test_02_missing_each_of_five_assets_refuses_binding(self):
  for p in self.bundle.iterdir():
   data=p.read_bytes();p.unlink()
   try:
    with self.assertRaises((RuntimeError,FileNotFoundError)):self.bind()
   finally:p.write_bytes(data)
 def test_03_corrupt_each_source_asset_refuses_binding(self):
  for p in self.bundle.iterdir():
   data=p.read_bytes();p.write_bytes(data[:-1]+bytes([data[-1]^1]))
   try:
    with self.assertRaises((RuntimeError,ValueError)):self.bind()
   finally:p.write_bytes(data)
 def test_04_resigned_descriptor_same_codewordCRC_and_rebound_hash_refuses(self):
  p=self.bundle/'DOS64.REL';old=p.read_bytes();bad=bytearray(old);bad[12]^=1;bad[60:64]=struct.pack('<I',zlib.crc32(bad[:60]));self.assertEqual(zlib.crc32(old),zlib.crc32(bad));p.write_bytes(bad);self.j['assets']['DOS64.REL']=S.digest(p);self.edit()
  with self.assertRaises(RuntimeError):self.bind()
 def test_05_failed_result_and_extra_asset_are_not_accepted(self):
  self.j['status']='failed';self.edit()
  with self.assertRaises(RuntimeError):self.bind()
  self.j['status']='passed';self.edit();(self.bundle/'extra').write_bytes(b'unexpected')
  with self.assertRaises(RuntimeError):self.bind()
 def test_06_outside_run_or_missing_metadata_refuses(self):
  self.j['run']=str(self.p/'other');self.edit()
  with self.assertRaises(RuntimeError):self.bind()
  self.j['run']=str(self.p/'coupled');self.edit();(self.p/'coupled/start/controller.map').unlink()
  with self.assertRaises(RuntimeError):self.bind()
 def test_07_cli_missing_binding_does_not_publish_native_or_pass(self):
  out=self.p/'missing';r=self.cli(out,'--bundle-result',self.p/'absent.json');self.assertNotEqual(r.returncode,0);j=json.loads((out/'RESULT.json').read_text());self.assertEqual(j['status'],'failed');self.assertFalse((out/'SETUP.PRG').exists())
 def test_08_native_default_scrubs_ambient_compiler_include_injection(self):
  t=S.toolchain();inc=Path(t['cc65']).parent.parent/'share/cc65/include/string.h';inject=self.p/'include';inject.mkdir();(inject/'string.h').write_bytes(inc.read_bytes()+b'\n#define strlen(x) 0\n');env=dict(os.environ,CC65_INC=str(inject),CC65_HOME=str(self.p/'hostile'),CA65_INC=str(inject),LD65_LIB=str(self.p/'missinglib'),LD65_CFG=str(self.p/'missingcfg'),DOS64_CLANGXX=str(self.p/'absent-clang'),DOS64_ZIG=str(self.p/'absent-zig'))
  out=self.p/'ambient';r=self.cli(out,env=env);self.assertEqual(r.returncode,0,r.stderr.decode());j=json.loads((out/'RESULT.json').read_text());self.assertFalse(j['runtime_preflight']);self.assertEqual(S.digest(Path(j['work'])/'build/setup.prg'),S.digest(Path(self.baseline['work'])/'build/setup.prg'));self.assertNotIn(str(inject/'string.h'),j['source_inputs'])
 def test_09_source_only_binding_ignores_valid_stale_helper_bytecode(self):
  source=ROOT/'build_support/config_generation.py';cached=Path(importlib.util.cache_from_source(str(source)))
  # Explicit default-cache destination; safe helper execution uses its absent
  # guarded prefix. Existing cache content is never overwritten by this test.
  cached=source.parent/'__pycache__'/('config_generation.'+sys.implementation.cache_tag+'.pyc');self.assertFalse(cached.exists());cached.parent.mkdir(exist_ok=True);evil=self.p/'evil.py';evil.write_text("raise RuntimeError('controlled-stale-helper-bytecode')\n");py_compile.compile(str(evil),cfile=str(cached),doraise=True);raw=bytearray(cached.read_bytes());struct.pack_into('<II',raw,8,int(source.stat().st_mtime),source.stat().st_size);cached.write_bytes(raw)
  saved=sys.pycache_prefix
  try:
   sys.pycache_prefix=None;s=importlib.util.spec_from_file_location('unsafe_preflight_helper_control',source);m=importlib.util.module_from_spec(s)
   with self.assertRaisesRegex(RuntimeError,'controlled-stale-helper-bytecode'):s.loader.exec_module(m)
   sys.pycache_prefix=saved;r,_,_=self.bind();self.assertEqual(r['assets'],self.j['assets'])
  finally:sys.pycache_prefix=saved;cached.unlink()
 def test_10_missing_explicit_compiler_does_not_fallback(self):
  out=self.p/'compiler';r=self.cli(out,env=dict(os.environ,DOS64_CC65=str(self.p/'missing-cc65')));self.assertNotEqual(r.returncode,0);self.assertFalse((out/'SETUP.PRG').exists())
 def test_11_future_control_capsule_block_boundary_is_explicitly_refused(self):
  # This is only the extra layout guard after generic bundle validation; the
  # mutated descriptor here does not claim to be a qualified native bundle.
  _,work,_=self.bind();p=work/'release-assets/START.REL';original=p.read_bytes()
  for offset in [0,1,261,380,381,512,512+381]:
   data=bytearray(original);data[24:28]=struct.pack('<I',offset);p.write_bytes(data);S.check_preflight_layout(work)
  for offset in [382,383,510,511,512+382,512+511]:
   data=bytearray(original);data[24:28]=struct.pack('<I',offset);p.write_bytes(data)
   with self.assertRaisesRegex(RuntimeError,'one512-byte source block'):S.check_preflight_layout(work)
if __name__=='__main__':unittest.main(verbosity=2)
