from pathlib import Path
import sys,os
ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True;sys.pycache_prefix=str(ROOT/('.absent-profile-host-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import importlib.util,unittest,tempfile,json
from unittest.mock import patch
s=importlib.util.spec_from_file_location('profile_builder',ROOT/'build_support/config_generation.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class StopLink(Exception):pass
class Host(unittest.TestCase):
 def commands(self,**flags):
  commands=[]
  def record(argv):
   commands.append([str(x)for x in argv])
   if argv[0]=='ld65':raise StopLink()
  with tempfile.TemporaryDirectory()as d:
   with self.assertRaises(StopLink):m.native(Path(d),dict(cc65='cc65',ca65='ca65',ld65='ld65',library='none.lib'),record,**flags)
  return commands
 def test_default_profiles_have_no_new_feature_defines_or_ASM(self):
  before=list(m.ASM);c=self.commands();self.assertEqual(m.ASM,before)
  self.assertEqual(c[-1][2],'publisher.cfg');self.assertFalse(any('RELOCATION' in x or 'INPLACE' in x or 'ALL_FILE_DIAGNOSTICS' in x for row in c for x in row));self.assertFalse(any(x.endswith('/relocation.o')for x in c[-1]))
 def test_relocation_only_explicit_graph(self):
  c=self.commands(relocation=True);self.assertEqual(c[-1][2],'publisher-relocation.cfg');self.assertTrue(any(x.endswith('/relocation.o')for x in c[-1]));self.assertTrue(any('D64_CONFIG_INPLACE=1'in row for row in c));self.assertFalse(any('DOS64_ALL_FILE_DIAGNOSTICS=1'in row for row in c))
 def test_combined_graph_selects_exact_linker_and_flags(self):
  c=self.commands(relocation=True,all_file_diagnostics=True,startup_diagnostics=True);self.assertEqual(c[-1][2],'all-file-relocation.cfg');self.assertTrue(any('DOS64_CONFIG_RELOCATION=1'in row and 'D64_CONFIG_INPLACE=1'in row and 'DOS64_ALL_FILE_DIAGNOSTICS=1'in row for row in c));self.assertTrue(any('DOS64_BOOT_DIAGNOSTICS=1'in row for row in c))
 def test_diagnostics_requires_bootstrap_before_output_or_tools(self):
  with tempfile.TemporaryDirectory()as d:
   out=Path(d)/'absent'
   with patch.object(m,'tools',side_effect=AssertionError('tools must not run')):
    with self.assertRaisesRegex(ValueError,'requires startup'):m.build(out,Path(d)/'none',False,None,all_file_diagnostics=True)
   self.assertFalse(out.exists())
 def test_source_inventory_public_only_and_complete(self):
  j=json.loads((ROOT/'build_support/config_sources.json').read_text());self.assertEqual(j['relocation.s'],'tools/config/relocation.s')
  for dest,source in j.items():
   self.assertEqual(Path(dest).name,dest);self.assertFalse('agentworking'in source);self.assertFalse('..'in Path(source).parts);self.assertTrue((ROOT/source).is_file(),source)
  self.assertEqual((ROOT/j['all-file-relocation.cfg']).read_bytes(),(ROOT/'tools/config/all-file-relocation.cfg').read_bytes())
 def test_native_tools_never_resolve_optional_dependencies(self):
  calls=[]
  def tool(n,*args):calls.append(n);return Path('/opt/homebrew/bin')/n
  with tempfile.TemporaryDirectory()as d:
   lib=Path(d)/'none.lib';lib.write_bytes(b'fixture')
   with patch.object(m,'tool',side_effect=tool),patch.dict(os.environ,{'DOS64_CC65_LIB':str(lib)}):t=m.tools(False)
  self.assertEqual(calls,['cc65','ca65','ld65']);self.assertNotIn('zig',t);self.assertNotIn('clang++',t)
 def test_compiler_environment_scrubs_untracked_sources_keeps_explicit_tools(self):
  poison={k:'poison'for k in ['PYTHONPATH','PYTHONPYCACHEPREFIX','CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG']};poison['DOS64_CC65']='chosen'
  with patch.dict(os.environ,poison):env=m.command_environment()
  self.assertEqual(env['DOS64_CC65'],'chosen');self.assertTrue(all(k not in env for k in poison if k!='DOS64_CC65'))
 def test_changed_declared_source_refuses(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d)/'source';p.write_bytes(b'first');record={str(p):m.digest(p)};p.write_bytes(b'other')
   with self.assertRaisesRegex(RuntimeError,'Source/product changed'):m.verify(record)
if __name__=='__main__':
 r=unittest.main(exit=False).result;passed=r.wasSuccessful()and r.testsRun==8
 if os.environ.get('DOS64_CONFIG_HOST_REPORT'):Path(os.environ['DOS64_CONFIG_HOST_REPORT']).write_text(json.dumps({'tests_run':r.testsRun,'successful':passed},indent=2)+'\n')
 sys.exit(not passed)
