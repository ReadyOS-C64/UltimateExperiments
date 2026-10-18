"""First-cause and cleanup regressions for the opt-in full recovery coordinator.

These host tests use an in-memory Ultimate oracle; they make no device calls.
"""
import json,tempfile,unittest,socket,sys
from pathlib import Path
from unittest.mock import patch
PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'build_support'))
import c64u_full_recovery as r
import test_bulk_reu_recovery as f
class Hook:
 def __init__(self,error=None,value=None):self.interruption=error;self.value=value if value is not None else {'status':'failed','errors':[repr(error)]}
 def preflight(self):pass
 def run(self,*args):return self.value
class Cases(unittest.TestCase):
 def workflow(self,hook,later=None,guest=None):
  client=f.Fake();td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);out=Path(td.name)/'run'
  class S(r.Service):
   def restore(self,*a,**kw):
    if later is not None:raise later
    return super().restore(*a,**kw)
  def app(c,o):
   c.reu[17]^=1
   if guest is not None:raise guest
   return {'status':'passed'}
  caught=None
  try:
   with patch.object(socket.socket,'connect',side_effect=AssertionError('No network permitted')):
    report=r.run_with_recovery(client,f.PRG,out,app,service_factory=S,restore_attempts=1,pre_restore_evidence=hook)
  except BaseException as error:caught=error;report=error.dos64_recovery_report
  self.assertTrue(report['configuration_restored']);self.assertTrue(report['reset_resumed']);self.assertEqual(client.events[-1],'machine:resume')
  self.assertEqual(json.loads((out/'result.json').read_text())['status'],'failed')
  return caught,report,client
 def test_equal_repr_errors_preserve_actual_retention_first_object(self):
  first=ConnectionResetError(54,'Connection reset by peer');later=ConnectionResetError(54,'Connection reset by peer')
  self.assertIsNot(first,later);self.assertEqual(repr(first),repr(later))
  caught,report,_=self.workflow(Hook(first),later);self.assertIs(caught,first);self.assertFalse(report['reu_restored']);self.assertEqual(len(report['restore_errors']),1)
 def test_retention_interrupt_survives_later_reset_and_marks_cancelled(self):
  first=KeyboardInterrupt('retention');caught,report,_=self.workflow(Hook(first),ConnectionResetError(54,'later'))
  self.assertIs(caught,first);self.assertTrue(report['cancelled'])
 def test_earlier_guest_failure_stays_first(self):
  guest=ValueError('guest');caught,_,_=self.workflow(Hook(ConnectionResetError(54,'retention')),RuntimeError('restore'),guest);self.assertIs(caught,guest)
 def test_retention_object_precedes_bad_serialization_and_cleanup_completes(self):
  first=SystemExit('retention');caught,report,client=self.workflow(Hook(first,{'status':'failed','invalid':object()}))
  self.assertIs(caught,first);self.assertTrue(report['reu_restored']);self.assertEqual(client.reu[:len(f.ORIGINAL)],f.ORIGINAL)
 def test_failed_report_without_exception_retains_compatibility(self):
  caught,report,_=self.workflow(Hook(None,{'status':'failed','reason':'reported failure'}));self.assertIsNone(caught);self.assertTrue(report['reu_restored'])
 def test_restore_error_first_when_retention_passed(self):
  later=ConnectionResetError(54,'restore');caught,_,_=self.workflow(Hook(None,{'status':'passed'}),later);self.assertIs(caught,later)
 def test_invalid_interruption_refuses_and_still_restores(self):
  caught,report,_=self.workflow(Hook('not an exception'));self.assertIsInstance(caught,TypeError);self.assertTrue(report['reu_restored'])
 def test_reported_pass_cannot_hide_retained_interruption(self):
  first=ValueError('retained');caught,report,_=self.workflow(Hook(first,{'status':'passed'}));self.assertIs(caught,first);self.assertEqual(report['status'],'failed');self.assertTrue(report['reu_restored'])
class Peer(unittest.TestCase):
 def test_retention_first_survives_first_restore_interrupt_and_second_success(self):
  first=ConnectionResetError(54,'same');second=KeyboardInterrupt('restore-second');c=f.Fake();calls=[]
  class S(r.Service):
   def restore(self,*args,**kwargs):
    calls.append('restore')
    if len(calls)==1:raise second
    return super().restore(*args,**kwargs)
  with tempfile.TemporaryDirectory()as tmp:
   with self.assertRaises(ConnectionResetError)as caught:r.run_with_recovery(c,f.PRG,Path(tmp)/'run',lambda c,o:{'status':'passed'},service_factory=S,restore_attempts=2,pre_restore_evidence=Hook(first))
   self.assertIs(caught.exception,first);report=first.dos64_recovery_report;self.assertTrue(report['reu_restored']);self.assertEqual(c.reu[:len(f.ORIGINAL)],f.ORIGINAL);self.assertEqual(len(calls),2);self.assertTrue(report['configuration_restored']);self.assertTrue(report['reset_resumed'])
 def test_legacy_hook_without_optional_attribute_remains_successful(self):
  class Legacy:
   def preflight(self):pass
   def run(self,*args):return {'status':'passed'}
  c=f.Fake()
  with tempfile.TemporaryDirectory()as tmp:report=r.run_with_recovery(c,f.PRG,Path(tmp)/'run',lambda c,o:{'status':'passed'},restore_attempts=1,pre_restore_evidence=Legacy())
  self.assertEqual(report['status'],'passed');self.assertTrue(report['reu_restored']);self.assertTrue(report['configuration_restored']);self.assertTrue(report['reset_resumed'])

if __name__=='__main__':unittest.main(verbosity=2)
