"""Regression tests for review blockers; no sockets or physical devices."""
import importlib.util
import json
import multiprocessing.process
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'build_support'))
import c64u_bulk_reu_recovery as r
import c64u_hd_evidence as h
spec=importlib.util.spec_from_file_location('retention_fixture',Path(__file__).with_name('test_c64u_hd_evidence.py'))
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)

class Child:
    pid=None
    def __init__(self,always_interrupt=False,kill_fault=False):
        self.alive=True;self.killed=False;self.reaped=False;self.joins=0;self.exitcode=None
        self.always_interrupt=always_interrupt;self.kill_fault=kill_fault
    def start(self):pass
    def join(self,*args):
        self.joins+=1
        if self.joins==1 or self.always_interrupt:raise KeyboardInterrupt('Interrupted evidence parent wait')
        self.reaped=True;self.alive=False;self.exitcode=-9
    def is_alive(self):return self.alive
    def kill(self):
        self.killed=True
        if self.kill_fault:raise OSError('Injected child kill fault')
        self.alive=False;self.exitcode=-9

class Context:
    def __init__(self,child):self.child=child
    def Process(self,**kwargs):return self.child

class Hook:
    def __init__(self,value=None,error=None):self.value=value;self.error=error
    def preflight(self):pass
    def run(self,*args):
        if self.error:raise self.error
        return self.value

class Repairs(unittest.TestCase):
    def collector(self,**kwargs):return t.Tests().fixture(**kwargs)[0]
    def workflow(self,hook,primary=True):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        out=Path(temporary.name)/'run';fake=t.bulk.Fake()
        def application(client,output):
            client.reu[0x350000:0x350200]=b'N'*512
            client.reu[0x352000:0x352200]=b'H'*512
            client.ram[0x1234]=0x77
            if isinstance(hook,h.HdEvidenceCollector):client.ram[0xec09:0xec09+136]=hook.config[4:]
            if primary:raise ValueError('Primary guest failure')
            return {'status':'passed'}
        result=r.run_with_recovery(fake,t.bulk.PRG,out,application,pre_restore_evidence=hook)
        self.assertEqual(result['status'],'failed')
        self.assertTrue(result['reu_restored']);self.assertTrue(result['configuration_restored']);self.assertTrue(result['reset_resumed'])
        self.assertEqual(bytes(fake.reu[:r.SIZE]),t.bulk.ORIGINAL)
        self.assertEqual(fake.loads,2)
        if primary:self.assertEqual(result['error'],"ValueError('Primary guest failure')")
        self.assertEqual(json.loads((out/'result.json').read_text())['status'],'failed')
        return result,out,fake
    def test_review_reproduction_join_interrupt_kills_reaps_and_recovers(self):
        child=Child();collector=self.collector()
        with patch.object(h.multiprocessing,'get_context',return_value=Context(child)):
            result,_,_=self.workflow(collector)
        self.assertTrue(child.killed);self.assertTrue(child.reaped);self.assertEqual(child.joins,2)
        self.assertTrue(result['cancelled']);self.assertTrue(result['pre_restore_evidence']['cancelled'])
        self.assertTrue(result['pre_restore_evidence']['child_cleanup']['reaped'])
    def test_repeated_join_interrupt_is_failed_and_cannot_skip_machine_recovery(self):
        child=Child(always_interrupt=True)
        with patch.object(h.multiprocessing,'get_context',return_value=Context(child)):
            result,_,_=self.workflow(self.collector())
        self.assertTrue(child.killed);self.assertTrue(result['cancelled'])
        self.assertFalse(result['pre_restore_evidence']['child_cleanup']['reaped'])
    def test_kill_control_fault_is_retained_and_cannot_skip_machine_recovery(self):
        child=Child(kill_fault=True)
        with patch.object(h.multiprocessing,'get_context',return_value=Context(child)):
            result,_,_=self.workflow(self.collector())
        errors=result['pre_restore_evidence']['child_cleanup']['errors']
        self.assertTrue(any('kill fault' in error['error'] for error in errors))
    def test_cleanup_routine_systemexit_is_recorded_and_machine_recovery_continues(self):
        child=Child()
        with patch.object(h.multiprocessing,'get_context',return_value=Context(child)),patch.object(h,'stop_and_reap',side_effect=SystemExit('Injected cleanup cancellation')):
            result,_,_=self.workflow(self.collector())
        self.assertTrue(result['cancelled']);self.assertFalse(result['pre_restore_evidence']['child_cleanup']['reaped'])
    def test_actual_fork_blocked_collector_parent_interrupt_reaps_and_recovers(self):
        collector=self.collector(hang=True);collector.seconds=2
        original=multiprocessing.process.BaseProcess.join;calls=[]
        def interrupt_once(child,timeout=None):
            calls.append(child)
            if len(calls)==1:
                time.sleep(0.2)
                raise KeyboardInterrupt('Actual fork parent interrupted')
            return original(child,timeout)
        with patch.object(h,'SERVICE_SHA',r.sha(t.bulk.PRG)),patch.object(multiprocessing.process.BaseProcess,'join',interrupt_once):
            started=time.monotonic();result,out,_=self.workflow(collector)
        self.assertLess(time.monotonic()-started,4)
        self.assertTrue(result['cancelled']);self.assertTrue(result['pre_restore_evidence']['child_cleanup']['reaped'])
        self.assertIsNotNone(calls[0].exitcode);self.assertFalse(calls[0].is_alive())
        self.assertEqual((out/'hd-before-restore/authoritative-sector.bin').read_bytes(),b'N'*512)
        self.assertEqual((out/'hd-before-restore/guest-handoff.bin').read_bytes(),b'H'*512)
    def test_review_reproduction_unserializable_hook_result_is_safe_failed_record(self):
        result,_,_=self.workflow(Hook({'status':'failed','unserializable':object()}),primary=False)
        self.assertEqual(result['pre_restore_evidence']['type'],'TypeError')
        self.assertNotIn('unserializable',result['pre_restore_evidence'])
    def test_non_dictionary_malformed_status_nested_values_and_nonfinite_reject(self):
        for value in (None,[],True,'passed',{'status':None},{'status':1},{'status':'running'},
                      {'status':'passed','nested':{'bad':object()}},{'status':'passed','bad':float('nan')},
                      {'status':'failed','big':'x'*65536}):
            with self.subTest(value=type(value).__name__):
                result,_,_=self.workflow(Hook(value),primary=False)
                self.assertEqual(result['pre_restore_evidence']['status'],'failed')
    def test_keyboardinterrupt_and_systemexit_hook_results_keep_primary_error(self):
        for error in (KeyboardInterrupt('cancelled'),SystemExit(130)):
            result,_,_=self.workflow(Hook(error=error))
            self.assertTrue(result['cancelled']);self.assertTrue(result['pre_restore_evidence']['cancelled'])
    def test_progress_typeerror_after_evidence_cannot_skip_cleanup(self):
        original=r.dump
        def broken(path,value):
            if path.name=='progress.json' and value['stage']=='restore and full readback':raise TypeError('Injected progress serialization fault')
            return original(path,value)
        with patch.object(r,'dump',broken):result,_,_=self.workflow(Hook({'status':'failed'}))
        self.assertTrue(any(item['type']=='TypeError' for item in result['progress_errors']))
    def test_progress_keyboardinterrupt_after_evidence_is_retained_and_recovers(self):
        original=r.dump
        def broken(path,value):
            if path.name=='progress.json' and value['stage']=='restore and full readback':raise KeyboardInterrupt('Injected progress interruption')
            return original(path,value)
        with patch.object(r,'dump',broken):result,_,_=self.workflow(Hook({'status':'failed'}))
        self.assertTrue(result['cancelled'])
    def test_failed_readonly_collection_independently_verifies_complete_artifacts(self):
        collector,ftp=t.Tests().fixture(readonly=1);ftp.image=ftp.image[:-1]+b'x'
        fake=t.bulk.Fake();fake.ram[0xec09:0xec09+136]=collector.config[4:]
        with tempfile.TemporaryDirectory() as d,patch.object(h,'SERVICE_SHA',r.sha(t.bulk.PRG)):
            result=collector.run(fake,t.bulk.PRG,Path(d),lambda *a,**k:None)
        self.assertEqual(result['status'],'failed');self.assertTrue(result['parent_all_artifacts_verified'])
        self.assertEqual(len(result['parent_verified_artifacts']),5)
    def test_failed_resident_config_collection_independently_verifies_complete_artifacts(self):
        collector=self.collector()
        with tempfile.TemporaryDirectory() as d,patch.object(h,'SERVICE_SHA',r.sha(t.bulk.PRG)):
            result=collector.run(t.bulk.Fake(),t.bulk.PRG,Path(d),lambda *a,**k:None)
        self.assertEqual(result['status'],'failed');self.assertTrue(result['parent_all_artifacts_verified'])
        self.assertFalse(result['parent_resident_config_matches'])
    def test_failed_collection_tampered_complete_artifact_rejects_parent_readback(self):
        collector=self.collector();original=collector.collect
        def collect(*args,**kwargs):
            result=original(*args,**kwargs);path=Path(args[2])/'authoritative-sector.bin'
            path.chmod(0o644);path.write_bytes(b'X'*512)
            return result
        collector.collect=collect
        with tempfile.TemporaryDirectory() as d,patch.object(h,'SERVICE_SHA',r.sha(t.bulk.PRG)):
            with self.assertRaisesRegex(ValueError,'Independent parent evidence readback differs'):
                collector.run(t.bulk.Fake(),t.bulk.PRG,Path(d),lambda *a,**k:None)
    def test_evidence_failure_journal_fault_cannot_skip_machine_cleanup(self):
        original=r.Journal.__call__
        def broken(journal,event,**fields):
            if event=='pre_restore_evidence_failed':raise TypeError('Injected evidence journal serialization fault')
            return original(journal,event,**fields)
        with patch.object(r.Journal,'__call__',broken):
            result,_,_=self.workflow(Hook({'status':'failed','bad':object()}))
        self.assertTrue(any('journal serialization fault' in item['error'] for item in result['journal_errors']))
    def test_raw_reaping_fallback_retries_are_bounded_after_control_fault(self):
        child=Child(always_interrupt=True);child.pid=12345
        with patch.object(h.os,'waitpid',side_effect=KeyboardInterrupt('Repeated waitpid interruption')) as wait:
            result=h.stop_and_reap(child)
        self.assertTrue(child.killed);self.assertFalse(result['reaped']);self.assertEqual(wait.call_count,2)
    def test_actual_fork_timeout_keeps_durable_partial_image_and_all_new_authority(self):
        collector,ftp=t.Tests().fixture();collector.seconds=1
        original=ftp.retrbinary
        def block_after_first_image_chunk(command,consume):
            if command.endswith('DOSHD.IMG'):
                consume(ftp.image[:8192]);time.sleep(20)
            else:return original(command,consume)
        ftp.retrbinary=block_after_first_image_chunk
        with patch.object(h,'SERVICE_SHA',r.sha(t.bulk.PRG)):
            result,out,_=self.workflow(collector)
        self.assertTrue(result['pre_restore_evidence']['timed_out'])
        partial=out/'hd-before-restore/hd-visible.partial.img'
        self.assertEqual(partial.read_bytes(),collector.source[:8192])
        self.assertEqual((out/'hd-before-restore/authoritative-sector.bin').read_bytes(),b'N'*512)
        self.assertEqual((out/'hd-before-restore/guest-handoff.bin').read_bytes(),b'H'*512)

if __name__=='__main__':unittest.main()
