from pathlib import Path
import sys,os
W=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(W/('.absent-stage-purpose-'+str(os.getpid())))
if Path(sys.pycache_prefix).exists():raise RuntimeError('Absent source-only cache')
import unittest,json,tempfile,socket,http.client
socket.socket=lambda *a,**k:(_ for _ in ()).throw(AssertionError('Offline network forbidden'))
import purpose
from stage_model import StageModel,Clock

class Tests(unittest.TestCase):
 def make(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name);m=json.loads((W/'LAUNCH_MANIFEST.json').read_text());m['schema']='CURRENT9_STAGING_PUT_LOCAL_TEST_1';m['runs_root']=str(root);m['run']=str(root/m['run_id']);active=root/'ACTIVE.json';active.write_bytes(Path(m['predecessor']).read_bytes());m['active']=str(active);return m
 def test_exact_constructor_historical_source_no_network(self):
  m=self.make();r=purpose.preflight(m,local=True);assert r['files']==10 and r['historical_backup']['historical_files_verified']==325 and not r['final_V1_installation_accepted']
 def test_scope_bounds_roles_and_asset_mutations_before_factory(self):
  for k,v in [('live_MAIN_takeover',True),('SETUP_CONFIG_UI_execution',True),('full_snapshots',2),('native_jobs',118),('shared_core_seconds',601),('stager_REU_end_exclusive',2113537),('schema','OLD')]:
   m=self.make();m[k]=v
   with self.assertRaises(ValueError):purpose.preflight(m,local=True)
  m=self.make();m['assets']['START.INO']=m['assets']['SETUP.FAT']
  with self.assertRaises(ValueError):purpose.preflight(m,local=True)
 def test_context_change_current_predecessor_and_replay(self):
  m=self.make();ctx=purpose.local_context(m);m['purpose_nonce']='0'*32
  with self.assertRaises(ValueError):ctx.check(m)
  m=self.make();Path(m['active']).write_text('{}')
  with self.assertRaises(ValueError):purpose.preflight(m,local=True)
  m=self.make();Path(m['run']).mkdir()
  with self.assertRaises(ValueError):purpose.preflight(m,local=True)
 def test_full_concrete_model_source_copy_ledger_and_independent_acceptance(self):
  m=self.make();c=Clock();models=[]
  def factory(streams,service,base,stager,ledger):
   model=StageModel(streams,service,base,c,stager);models.append(model);return purpose.PurposeWire(m['host'],streams,service,base,stager,ledger=ledger,factory=model,clock=c)
  r=purpose.execute(m,purpose.local_context(m),factory,clock=c,sleep=c.sleep);assert r['status']=='passed'and not r['physical']and r['physical_acceptance']=='NOT_ACCEPTED'and r['source_closure_passed'];assert models[0].restores==1
  a=json.loads(Path(m['active']).read_text());assert a['hardware_reserved']and a['original_ac43_verified_restored']and not a['possible_native_execution']
  assert len(list((Path(m['run'])/'session/actual-files').iterdir()))==10
  with self.assertRaises(ValueError):purpose.execute(m,purpose.local_context(m),factory,clock=c,sleep=c.sleep)
 def test_ambiguous_stager_GO_exact_first_and_reserved_cleanup(self):
  m=self.make();c=Clock();models=[];once=[False]
  def factory(streams,service,base,stager,ledger):
   model=StageModel(streams,service,base,c,stager);models.append(model)
   def fault(f,i,method,path):
    if 'address=200&data=22'in path and not once[0]:once[0]=True;return'reset'
   model.fault=fault;return purpose.PurposeWire(m['host'],streams,service,base,stager,ledger=ledger,factory=model,clock=c)
  with self.assertRaises(ConnectionResetError)as e:purpose.execute(m,purpose.local_context(m),factory,clock=c,sleep=c.sleep)
  assert e.exception is models[0].error;a=json.loads(Path(m['active']).read_text());assert a['hardware_reserved']and a['original_ac43_verified_restored']and a['settings_media_equal']
  assert len([r for r in models[0].calls if 'address=200&data=22'in r['path']])==1
 def test_direct_live_local_context_and_changed_source_refused(self):
  m=self.make()
  with self.assertRaises(ValueError):purpose.live(m,purpose.local_context(m))
  m['files'][next(iter(m['files']))]='0'*64
  with self.assertRaises(ValueError):purpose.preflight(m,local=True)
 def test_primary_GO_reset_survives_outer_result_write_failure(self):
  m=self.make();c=Clock();models=[];once=[False];original=purpose.durable
  def factory(streams,service,base,stager,ledger):
   model=StageModel(streams,service,base,c,stager);models.append(model)
   def fault(f,i,method,path):
    if 'address=200&data=22'in path and not once[0]:once[0]=True;return'reset'
   model.fault=fault;return purpose.PurposeWire(m['host'],streams,service,base,stager,ledger=ledger,factory=model,clock=c)
  def writer(path,b):
   if path.name=='final-result.json':raise OSError('later outer result error')
   return original(path,b)
  purpose.durable=writer
  try:
   with self.assertRaises(ConnectionResetError)as e:purpose.execute(m,purpose.local_context(m),factory,clock=c,sleep=c.sleep)
  finally:purpose.durable=original
  assert e.exception is models[0].error;active=json.loads(Path(m['active']).read_text());assert active['status']=='CURRENT9_STAGING_FAILED_RESERVED'and active['settings_media_equal']
  retained=json.loads((Path(m['run'])/'terminal-failure.json').read_text());assert retained['first_type']=='ConnectionResetError'and retained['library_report']['callback_report']['facts']['original4MiB_verified']

if __name__=='__main__':unittest.main(verbosity=2)
