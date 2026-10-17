from pathlib import Path
import sys,os
W=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(W/('.absent-binding-tests-'+str(os.getpid())))
if Path(sys.pycache_prefix).exists():raise RuntimeError('Absent source-only cache')
import unittest,json,hashlib,tempfile,socket
socket.socket.connect=lambda *a,**k:(_ for _ in ()).throw(AssertionError('Offline network forbidden'))
from stage_transport import StageREST,StageClient
from stage_backend import Backend
from stage_model import StageModel,Clock
from protocol import Source
from current_bundle import prepare
from cold_session import FrozenSources,native_contract
from preserved_stage import closed_terminal

class Tests(unittest.TestCase):
 def lane(self):
  clock=Clock();streams={r:((W/(r+'-stream.prg')).read_bytes(),bytes.fromhex((W/(r+'-NONCE.hex')).read_text()))for r in ['initial','changed','final']};baseline=(W/'BASELINE.reu').read_bytes();service=(W/'service.prg').read_bytes();source=Source((W/'stager.prg').read_bytes(),(W/'stager.labels').read_text(),b'/usb1/DOS64_TEST/current9-live172800')
  model=StageModel(streams,service,baseline,clock,source);wire=StageREST('10.0.0.79',streams,service,baseline,source,factory=model,clock=clock)
  temp=tempfile.TemporaryDirectory(prefix='current9-binding-');self.addCleanup(temp.cleanup);out=Path(temp.name)/'session';assets=prepare(source.home,W/'assets',(W/'CANDIDATE_RESULT.json').read_bytes(),bytes.fromhex('17280000000000000000000000000004'))
  contracts={k:native_contract((W/'stream-template.prg').read_bytes(),v[0],(W/'stream.labels').read_text(),v[1])for k,v in streams.items()};pins={str(W/n):hashlib.sha256((W/n).read_bytes()).hexdigest()for n in ['stage_backend.py','stage_transport.py','preserved_stage.py','driver.py','changed_driver.py','protocol.py','put_io.py','service.prg']}
  session=Backend(wire,streams,baseline,out,stager=source,assets=assets,contracts=contracts,audit=FrozenSources(pins),clock=clock,sleep=clock.sleep)
  return clock,model,wire,session,assets
 def test_full_HTTP_binding_ten_files_three_snapshots_one_restore(self):
  clock,m,w,s,a=self.lane();r=s.run();assert r['status']=='passed'and len(m.files)==10 and all(bytes(m.files[k])==v for k,v in a.items());assert m.restores==1 and w.stream_done=={'initial','changed','final'}and w.global_acks==384 and w.global_full==387
  assert (s.out/'initial4MiB.bin').read_bytes()==s.baseline==(s.out/'final4MiB.bin').read_bytes();assert(s.out/'changed4MiB.bin').read_bytes()!=s.baseline
  assert m.turbo_control=='C64U Turbo Registers'and not any(x['method']=='POST'for x in m.calls)
  assert s.machine.calls['native_restore']==1 and s.machine.facts['original_settings_verified']and s.machine.facts['BASIC_cleanup_verified']
  (W.parent/'BINDING_POSITIVE.json').write_text(json.dumps({'status':'PASS_LOCAL_HTTP_FIXTURE_NOT_NATIVE_OR_PHYSICAL','HTTP_requests':len(m.calls),'PUT_memory_chunks':len(m.writes),'stage_jobs':len(m.stage_jobs),'files':len(m.files),'stream_full_GETs':w.global_full,'stream_ACKs':w.global_acks,'native_restore_attempts':m.restores,'clock_model_seconds':clock.t,'same_core_endpoint':s.machine.end},indent=2)+'\n')
 def test_disabled_command_interface_refused_before_mutation(self):
  c,m,w,s,a=self.lane();old=m.response
  def response(method,path,body):
   value=old(method,path,body)
   if path=='/v1/configs/C64%20and%20Cartridge%20Settings':
    v=json.loads(value);v['C64 and Cartridge Settings']['Command Interface']='Disabled';return json.dumps(v).encode()
   return value
  m.response=response
  with self.assertRaises(ValueError):s.run()
  assert not m.restores and not any(x['method']!='GET'for x in m.calls)
 def test_live_main_or_non_READY_refused_before_profile_or_reset(self):
  c,m,w,s,a=self.lane();m.ram[0xc6]=1
  with self.assertRaises(ValueError):s.run()
  assert not m.restores and not any(x['path'].startswith('/v1/configs/U64%20Specific%20Settings:')or x['path']=='/v1/machine:reset'for x in m.calls)
 def test_stage_unknown_handle_blocks_replacement_restore_but_profile_finally(self):
  c,m,w,s,a=self.lane();m.stage_unknown=True
  with self.assertRaises(BaseException):s.run()
  assert not m.restores and 'changed'not in w.stream_done and not w.restore_start_attempted and m.turbo_control=='C64U Turbo Registers'
  assert s.machine.calls['profile_restore']==1
 def test_ambiguous_GO_preserves_exact_first_no_reissue(self):
  c,m,w,s,a=self.lane();fired=[False]
  def fault(model,i,method,path):
   if 'address=200&data=22'in path and not fired[0]:fired[0]=True;return'reset'
  m.fault=fault
  with self.assertRaises(ConnectionResetError)as seen:s.run()
  assert seen.exception is m.error and len([x for x in m.calls if 'address=200&data=22'in x['path']])==1 and m.turbo_control=='C64U Turbo Registers'
 def test_restore_failure_unknown_writer_no_final_reset_profile_still_restored(self):
  c,m,w,s,a=self.lane();m.native_failure=True
  with self.assertRaises(ValueError):s.run()
  assert m.restores==1 and not w.restore_done and 'final'not in w.stream_done and m.turbo_control=='C64U Turbo Registers'
  assert 'cleanup_reset'not in w.calls
 def test_source_corruption_terminal_prevents_helper_overwrite(self):
  c,m,w,s,a=self.lane();m.stage_source_bad=True
  with self.assertRaises(ValueError):s.run()
  assert not m.restores and 'changed'not in w.source_loads and m.turbo_control=='C64U Turbo Registers'
 def test_primary_native_stage_failure_survives_secondary_restore_failure(self):
  c,m,w,s,a=self.lane();m.stage_error=3;m.native_failure=True
  from protocol import NativeFailure
  with self.assertRaises(NativeFailure)as e:s.run()
  assert e.exception is s.protocol.first and e.exception is s.machine.first and e.exception is s.first
  assert m.restores==1 and m.turbo_control=='C64U Turbo Registers'and 'cleanup_reset'not in w.calls
 def test_secondary_terminal_orchestration_interrupt_never_skips_profile(self):
  c,m,w,s,a=self.lane();m.stage_error=3
  def abort(end):raise KeyboardInterrupt('terminal orchestration')
  s.terminal_cb=abort
  from protocol import NativeFailure
  with self.assertRaises(NativeFailure)as e:s.run()
  assert e.exception is s.protocol.first and s.machine.calls['profile_restore']==1 and m.turbo_control=='C64U Turbo Registers'and not m.restores
 def test_source_role_order_closed_flag_observation_not_authority(self):
  c,m,w,s,a=self.lane()
  w.stage_closed=True # public positive observation cannot replace a raw terminal receipt.
  for role in ['changed','restore','final']:
   with self.assertRaises(ValueError):w.cold_begin(role)
  with self.assertRaises(ValueError):w.stage_exchange(object(),'PUT','machine:reset',12)
 def test_result_write_failure_reports_failed_after_verified_cleanup(self):
  c,m,w,s,a=self.lane();original=s.writer;first=OSError('local RESULT retention failure')
  def writer(path,b):
   if path.name=='RESULT.json':raise first
   return original(path,b)
  s.writer=writer
  with self.assertRaises(OSError)as e:s.run()
  assert e.exception is first and s.report['status']=='failed'and s.report['callback_report']['facts']['original4MiB_verified']and m.turbo_control=='C64U Turbo Registers'
 def test_no_POST_arbitrary_memory_and_same_source_reentry(self):
  c,m,w,s,a=self.lane();w.archive_request=lambda x:None;w.archive_write=lambda *a:None
  for method,route in [('POST','runners:load_prg'),('PUT','machine:writemem?address=1&data=35')]:
   with self.assertRaises(ValueError):w._exchange(method,route,12)
  assert not m.calls

if __name__=='__main__':unittest.main(verbosity=2)
