"""Offline source-only relocated-host trust controls; no external fixture or LAN."""
import unittest,tempfile,shutil,subprocess,sys,json,py_compile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HOST=ROOT/'build_support/ac_development'
class Layout(unittest.TestCase):
 def run_case(self,edit,script='ac_runner.py'):
  with tempfile.TemporaryDirectory(dir=ROOT/'agentworking',prefix='ac-layout-') as d:
   target=Path(d)/'build_support/ac_development';shutil.copytree(HOST,target,ignore=shutil.ignore_patterns('__pycache__','.source-import-cache-disabled'));edit(target)
   return subprocess.run([sys.executable,'-B',str(target/script),'--help'],cwd=ROOT,capture_output=True,text=True)
 def test_dependency_source_change_rejected_before_cli(self):
  def edit(h):(h/'support/c64u_native_application_support.py').write_text('# altered source\n')
  r=self.run_case(edit);self.assertNotEqual(r.returncode,0);self.assertIn('Reviewed dependency source differs',r.stderr)
 def test_dependency_manifest_change_rejected_before_cli(self):
  def edit(h):(h/'DEPENDENCIES.json').write_text('{}')
  r=self.run_case(edit);self.assertNotEqual(r.returncode,0);self.assertIn('Reviewed dependency manifest differs',r.stderr)
 def test_existing_source_cache_prefix_rejects_all_entrypoints(self):
  for script in ['ac_runner.py','ac_freeze.py','stage_ac.py']:
   r=self.run_case(lambda h:(h/'.source-import-cache-disabled').mkdir(),script);self.assertNotEqual(r.returncode,0);self.assertIn('Source-only cache path must remain absent',r.stderr)
 def test_foreign_project_support_preload_rejected(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'agentworking',prefix='ac-layout-') as d:
   work=Path(d);h=work/'build_support/ac_development';shutil.copytree(HOST,h)
   foreign=work/'build_support/foreign.py';foreign.write_text('pass')
   code="import sys,types; m=types.ModuleType('foreign');m.__file__="+repr(str(foreign))+";sys.modules['foreign']=m;sys.path.insert(0,"+repr(str(h))+");import bootstrap"
   r=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertIn('Fresh process required',r.stderr)
 def test_stale_normal_pycache_positive_and_guarded_control(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'agentworking',prefix='ac-layout-') as d:
   h=Path(d)/'build_support/ac_development';shutil.copytree(HOST,h);source=h/'support/c64u_native_application_support.py';poison=Path(d)/'poison.py';poison.write_text("raise RuntimeError('AC_RELOCATED_STALE_CACHE_CONTROL')\n");previous=sys.pycache_prefix;sys.pycache_prefix=str(Path(d)/'normalcache');cache=Path(__import__('importlib.util',fromlist=['cache_from_source']).cache_from_source(str(source)));sys.pycache_prefix=previous;cache.parent.mkdir(parents=True,exist_ok=True);py_compile.compile(str(poison),cfile=str(cache),invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
   code='import sys;sys.path.insert(0,'+repr(str(h/'support'))+');import c64u_native_application_support'
   bad=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,env=dict(os.environ,PYTHONPYCACHEPREFIX=str(Path(d)/'normalcache')));self.assertNotEqual(bad.returncode,0);self.assertIn('AC_RELOCATED_STALE_CACHE_CONTROL',bad.stderr)
   good=subprocess.run([sys.executable,'-B',str(h/'ac_runner.py'),'--help'],capture_output=True,text=True,env=dict(os.environ,PYTHONPYCACHEPREFIX=str(Path(d)/'normalcache')));self.assertEqual(good.returncode,0,good.stderr);self.assertNotIn('AC_RELOCATED_STALE_CACHE_CONTROL',good.stderr)
 def test_direct_host_test_rejects_timestamp_valid_bootstrap_before_execution(self):
  # Reproduce the actual pre-import defect with a positive poisoned-cache
  # control, then prove the public entry rejects before that bytecode runs.
  import importlib.util,struct
  with tempfile.TemporaryDirectory(dir=ROOT/'agentworking',prefix='ac-entry-cache-') as d:
   work=Path(d);host=work/'build_support/ac_development'
   shutil.copytree(HOST,host,ignore=shutil.ignore_patterns('__pycache__','.source-import-cache-disabled'))
   entry=work/'tests/tooling/ac_development/test_ac_host.py';entry.parent.mkdir(parents=True)
   original=(ROOT/'tests/tooling/ac_development/test_ac_host.py').read_text()
   guard="if Path(sys.pycache_prefix).exists():raise RuntimeError('Source-only cache path must remain absent')\n"
   self.assertEqual(original.count(guard),1)
   fixture=work/'fixture';fixture.mkdir();manifest=fixture/'MANIFEST.json';manifest.write_text('{}')
   context=work/'context.json';context.write_text(json.dumps({'fixture_root':str(fixture),'source_host_manifest_sha256':__import__('hashlib').sha256(manifest.read_bytes()).hexdigest()}))
   env=dict(os.environ,DOS64_AC_TEST_CONTEXT=str(context),DOS64_AC_TEST_CONTEXT_SHA=__import__('hashlib').sha256(context.read_bytes()).hexdigest())
   bootstrap_source=host/'bootstrap.py';poison=work/'poison.py';poison.write_text("raise RuntimeError('DIRECT_TEST_CACHED_BOOTSTRAP_EXECUTED')\n")
   previous=sys.pycache_prefix;sys.pycache_prefix=str(host/'.source-import-cache-disabled')
   cache=Path(importlib.util.cache_from_source(str(bootstrap_source)));sys.pycache_prefix=previous
   cache.parent.mkdir(parents=True,exist_ok=True);py_compile.compile(str(poison),cfile=str(cache),invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
   raw=cache.read_bytes();stat=bootstrap_source.stat();cache.write_bytes(raw[:8]+struct.pack('<II',int(stat.st_mtime)&0xffffffff,stat.st_size&0xffffffff)+raw[16:])
   entry.write_text(original.replace(guard,'',1))
   old=subprocess.run([sys.executable,'-B',str(entry)],cwd=work,env=env,capture_output=True,text=True)
   self.assertNotEqual(old.returncode,0);self.assertIn('DIRECT_TEST_CACHED_BOOTSTRAP_EXECUTED',old.stderr)
   entry.write_text(original)
   new=subprocess.run([sys.executable,'-B',str(entry)],cwd=work,env=env,capture_output=True,text=True)
   self.assertNotEqual(new.returncode,0);self.assertIn('Source-only cache path must remain absent',new.stderr);self.assertNotIn('DIRECT_TEST_CACHED_BOOTSTRAP_EXECUTED',new.stderr)

if __name__=='__main__':unittest.main(verbosity=2)
