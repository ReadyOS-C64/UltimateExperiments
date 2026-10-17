from pathlib import Path
import sys,os
W=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(W/('.absent-bound-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import unittest,json,hashlib,tempfile,socket
socket.socket.connect=lambda *a,**k:(_ for _ in ()).throw(AssertionError('Offline network forbidden'))
from stage_transport import StageREST
from cold_backend import ColdBackend as Backend
from cold_entry import ColdEntry
from stage_model import StageModel,Clock
from protocol import Source,NativeFailure
from bound_release import BoundRelease,NAMES
from cold_session import FrozenSources,native_contract
sha=lambda b:hashlib.sha256(b).hexdigest()
class Tests(unittest.TestCase):
 def release(self):
  raw=(W.parent/'STAGING_INVENTORY.json').read_bytes();return BoundRelease(raw,sha(raw),{n:(W.parent/'assets'/n).read_bytes()for n in NAMES})
 def lane(self):
  c=Clock();streams={r:((W/(r+'-stream.prg')).read_bytes(),bytes.fromhex((W/(r+'-NONCE.hex')).read_text()))for r in ['initial','changed','final']};baseline=(W/'BASELINE.reu').read_bytes();service=(W/'service.prg').read_bytes();source=Source((W/'stager.prg').read_bytes(),(W/'stager.labels').read_text(),b'/usb1/DOS64_TEST/release16-component')
  m=StageModel(streams,service,baseline,c,source);wire=StageREST('10.0.0.79',streams,service,baseline,source,factory=m,clock=c);temp=tempfile.TemporaryDirectory(prefix='release16-binding-');self.addCleanup(temp.cleanup)
  release=self.release();a=release.assets(source.home,bytes.fromhex('17780000000000000000000000000016'));contracts={k:native_contract((W/'stream-template.prg').read_bytes(),v[0],(W/'stream.labels').read_text(),v[1])for k,v in streams.items()};pins={str(W/n):sha((W/n).read_bytes())for n in ['bound_release.py','stage_backend.py','stage_transport.py','preserved_stage.py','driver.py','changed_driver.py','protocol.py','put_io.py','service.prg']}
  entry=ColdEntry((W.parent/'ACTIVE-predecessor.json').read_bytes(),(W.parent/'predecessor-terminal-RAM.bin').read_bytes(),(W.parent/'predecessor-stream.prg').read_bytes())
  s=Backend(wire,streams,baseline,Path(temp.name)/'session',stager=source,assets=a,contracts=contracts,release=release,entry=entry,audit=FrozenSources(pins),clock=c,sleep=c.sleep);return c,m,wire,s,a
 def test_01_exact16_three_snapshots_one_restore(self):
  c,m,w,s,a=self.lane();m.ram[:]=(W.parent/'predecessor-terminal-RAM.bin').read_bytes();r=s.run();self.assertEqual(s.entry_fact['cold_entry'],'EXACT_OWNED_FAILED_READONLY_STREAM');self.assertEqual(r['status'],'passed');self.assertEqual(len(m.files),16);self.assertEqual(len(m.stage_jobs),380);self.assertEqual(w.global_acks,384);self.assertEqual(w.global_full,387);self.assertEqual(m.restores,1);self.assertTrue(all(bytes(m.files[k])==v for k,v in a.items()));self.assertEqual((s.out/'initial4MiB.bin').read_bytes(),s.baseline);self.assertEqual((s.out/'final4MiB.bin').read_bytes(),s.baseline);self.assertNotEqual((s.out/'changed4MiB.bin').read_bytes(),s.baseline);self.assertEqual(m.turbo_control,'C64U Turbo Registers');self.assertTrue(s.machine.facts['BASIC_cleanup_verified']);self.assertTrue(s.machine.facts['original_settings_verified'])
  (W.parent/'ACTUAL_BINDING.json').write_text(json.dumps({'status':'LOCAL_HTTP_COMPOSITION_MODEL_ONLY','files':16,'native_jobs_modeled':380,'healthy_full_GETs':w.global_full,'healthy_ACKs':w.global_acks,'HTTP_requests':len(m.calls),'native_restore_attempts_modeled':m.restores,'same_core_end':s.machine.end,'clock_model_seconds':c.t,'scope':r['scope'],'actual_native_release16_parent':'a1aae34f; not reexecuted by this HTTP fixture','physical':False},indent=2)+'\n')
 def test_02_pinned_successor_cannot_transfer_identity(self):
  b=(W.parent/'STAGING_INVENTORY.json').read_bytes();a={n:(W.parent/'assets'/n).read_bytes()for n in NAMES};old=sha(b);j=json.loads(b);j['files']['SETUP.PRG']['sha256']='0'*64;changed=json.dumps(j).encode()
  for raw,expected,assets in [(changed,old,a),(b,sha(changed),a),(b,old,dict(a,**{'DOS3.IMG':b'bad'})),(b,old,{k:v for k,v in a.items()if k!='START.RFW'}),(b,old,dict(a,**{'A.IMG':b'bad'}))]:
   with self.assertRaises(ValueError):BoundRelease(raw,expected,assets)
  j=json.loads(b);a=dict(a);a['SETUP.PRG']=bytes([a['SETUP.PRG'][0]^1])+a['SETUP.PRG'][1:];j['files']['SETUP.PRG']={'bytes':len(a['SETUP.PRG']),'sha256':sha(a['SETUP.PRG'])};raw=json.dumps(j).encode();BoundRelease(raw,sha(raw),a)
 def test_03_unknown_stager_blocks_replacement_profile_finally(self):
  c,m,w,s,a=self.lane();m.stage_unknown=True
  with self.assertRaises(BaseException):s.run()
  self.assertEqual(m.restores,0);self.assertNotIn('changed',w.stream_done);self.assertEqual(m.turbo_control,'C64U Turbo Registers');self.assertEqual(s.machine.calls['profile_restore'],1)
 def test_04_ambiguousGO_once_first_preserved(self):
  c,m,w,s,a=self.lane();fired=[False]
  def fault(model,i,method,path):
   if 'address=200&data=22'in path and not fired[0]:fired[0]=True;return 'reset'
  m.fault=fault
  with self.assertRaises(ConnectionResetError)as e:s.run()
  self.assertIs(e.exception,m.error);self.assertEqual(len([x for x in m.calls if 'address=200&data=22'in x['path']]),1);self.assertEqual(m.turbo_control,'C64U Turbo Registers')
 def test_05_restore_unknown_blocksfinalreset(self):
  c,m,w,s,a=self.lane();m.native_failure=True
  with self.assertRaises(ValueError):s.run()
  self.assertEqual(m.restores,1);self.assertNotIn('final',w.stream_done);self.assertNotIn('cleanup_reset',w.calls);self.assertEqual(m.turbo_control,'C64U Turbo Registers')
 def test_06_secondary_terminal_interrupt_preservesfirst_and_profile(self):
  c,m,w,s,a=self.lane();m.stage_error=3
  def abort(end):raise KeyboardInterrupt('terminal orchestration')
  s.terminal_cb=abort
  with self.assertRaises(NativeFailure)as e:s.run()
  self.assertIs(e.exception,s.protocol.first);self.assertIs(e.exception,s.first);self.assertEqual(s.machine.calls['profile_restore'],1);self.assertEqual(m.turbo_control,'C64U Turbo Registers')
if __name__=='__main__':unittest.main(verbosity=2)
