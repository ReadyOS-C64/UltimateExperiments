from pathlib import Path
import sys,os
W=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(W/('.absent-ui-purpose-tests-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import unittest,json,tempfile,copy,socket
socket.socket.connect=lambda *a,**k:(_ for _ in ()).throw(AssertionError('No network in purpose controls'))
import purpose
class Tests(unittest.TestCase):
 def make(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);p=Path(t.name);m=json.loads((W/'LAUNCH_MANIFEST.json').read_text());m['schema']='V1_NATIVE_SETUP_UI_LOCAL_TEST_1';m['runs_root']=str(p);m['run']=str(p/m['run_id']);m['active']=str(p/'ACTIVE.json');Path(m['active']).write_bytes(Path(m['predecessor']).read_bytes());return m
 def test_exact_constructor_and_final_intake(self):
  m=self.make();r=purpose.preflight(m,local=True);self.assertEqual(r['files'],16);self.assertEqual(r['native_jobs'],380);self.assertFalse(r['hidden_preSYS_RAM_verified']);self.assertTrue(r['human_CIA_only']);self.assertFalse(r['final_V1_acceptance']);self.assertEqual(r['historical_backup']['historical_files_verified'],325)
 def test_finite_bounds_not_user_tunable_or_infinite(self):
  for k in ['human_window_seconds','restore_reserve_seconds','product_start_reserve_seconds','product_registered_LOAD_count','product_SYS_count','shared_core_seconds','product_header_poll_max']:
   for v in [float('nan'),float('inf'),0,True]:
    m=self.make();m[k]=v
    with self.assertRaises(ValueError):purpose.preflight(m,local=True)
 def test_capabilities_no_hidden_authority_or_synthetic_input(self):
  for k in ['POST','FTP','upper12MiB_access','original_CPU_restore','native_CIA_input_injected','hidden_preSYS_RAM_verified','final_V1_acceptance','live_MAIN_takeover','automatic_retry','START_DOS_execution']:
   m=self.make();m[k]=True
   with self.assertRaises(ValueError):purpose.preflight(m,local=True)
 def test_asset_binding_and_observer_refuse_other_product(self):
  m=self.make();m['assets']['SETUP.PRG']=m['assets']['CONFIG.PRG']
  with self.assertRaises(ValueError):purpose.preflight(m,local=True)
  m=self.make();m['observer_binding_sha256']='0'*64
  with self.assertRaises(ValueError):purpose.preflight(m,local=True)
 def test_every_consumed_authority_path_must_be_pinned(self):
  m=self.make();paths=[m[k]for k in ['intake','stager','stager_labels','main_labels','main_map','predecessor_terminal','predecessor_stream']]+list(m['observer_files'].values())+[p for role in m['streams'].values()for p in role.values()]
  for path in paths:
   n=copy.deepcopy(m);n['files'].pop(path)
   with self.assertRaises(ValueError):purpose.preflight(n,local=True)
 def test_context_and_currentpredecessor_and_replay_guard(self):
  m=self.make();ctx=purpose.local_context(m);m['purpose_nonce']='0'*32
  with self.assertRaises(ValueError):ctx.check(m)
  m=self.make();Path(m['active']).write_text('{}')
  with self.assertRaises(ValueError):purpose.preflight(m,local=True)
  m=self.make();Path(m['run']).mkdir()
  with self.assertRaises(ValueError):purpose.preflight(m,local=True)
 def test_no_live_factory_for_localcontext_and_changedsource(self):
  m=self.make()
  with self.assertRaises(ValueError):purpose.live(m,purpose.local_context(m))
  m['files'][next(iter(m['files']))]='0'*64
  with self.assertRaises(ValueError):purpose.preflight(m,local=True)
if __name__=='__main__':unittest.main(verbosity=2)
