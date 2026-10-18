"""Host-only observer tests; no target behavior is substituted or claimed."""
import importlib.util
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import test_c64u_native_application as fixture
r=fixture.r
ROOT=fixture.ROOT
TEMP_ROOT=ROOT/'agentworking/scratch/native-observer-tests'
TEMP_ROOT.mkdir(parents=True,exist_ok=True)


class ObserverTests(unittest.TestCase):
    def app(self,**kw):
        clock=fixture.Clock()
        return r.Application(fixture.PRG,fixture.LABELS,dict(fixture.MEDIA_RECORD),fixture.SOURCE,
                             b'\x01\x08dummy',fixture.support.sha(fixture.PRG),clock=clock,sleep=clock.sleep,**kw)

    def test_defaults_and_finite_closed_bounds_before_hardware(self):
        app=self.app();self.assertEqual(app.observation_interval,0.25);self.assertEqual(app.seconds,180)
        for name,values in [('observation_interval',[0.25,1,2]),('seconds',[10,180,360,600])]:
            for value in values:
                with self.subTest(name=name,value=value):self.app(**{name:value})
        for name,values in [('observation_interval',[True,None,'garbage',0.249,2.001,float('nan'),float('inf'),-float('inf')]),
                            ('seconds',[True,None,'garbage',9.99,600.01,float('nan'),float('inf'),-float('inf')])]:
            for value in values:
                with self.subTest(name=name,value=value),self.assertRaises(ValueError):self.app(**{name:value})

    def test_periodic_ah01_observation_retains_every_key_and_pagination(self):
        class Polling(fixture.Fake):
            def paint(self):
                super().paint();self.ram[0xea40]=0
        for interval in [0.25,1.0,2.0]:
            with self.subTest(interval=interval),tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
                app=self.app(observation_interval=interval);fake=Polling()
                with patch.object(r,'Service',fixture.Evidence):report=app(fake,Path(directory))
                self.assertTrue(report['script_result']['accepted']);self.assertEqual(len(fake.keys),14)
                self.assertEqual(report['script_result']['pagination_keys'],1)
                self.assertEqual(len(report['script_result']['seen_entries']),35)
                self.assertTrue(report['original_source_unchanged']);self.assertTrue(report['floppy_original_unchanged'])
                events=[json.loads(line) for line in (Path(directory)/'application-journal.jsonl').read_text().splitlines()]
                due=[e for e in events if e['event']=='native_observation_due']
                self.assertTrue(due);self.assertTrue(all(e['reason']=='periodic' for e in due))
                screens=report['script_result']['screens']
                times=[screen['host_elapsed_seconds'] for screen in screens]
                self.assertGreaterEqual(times[0]+1e-9,interval)
                self.assertTrue(all(b-a+1e-9>=interval for a,b in zip(times,times[1:])))
                self.assertEqual(report['observation_interval_seconds'],interval)

    def test_stable_ah00_input_serviced_before_two_second_period(self):
        app=self.app(observation_interval=2);fake=fixture.Fake()
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory,patch.object(r,'Service',fixture.Evidence):
            report=app(fake,Path(directory))
            self.assertTrue(report['script_result']['accepted']);self.assertEqual(len(fake.keys),14)
            self.assertLess(report['script_result']['screens'][0]['host_elapsed_seconds'],2)
            events=[json.loads(line) for line in (Path(directory)/'application-journal.jsonl').read_text().splitlines()]
            self.assertTrue(any(e['event']=='native_observation_due' and e['reason']=='stable_blocking_input' for e in events))

    def command_fixture(self,remaining):
        class NoAck(fixture.Fake):
            def __init__(self):super().__init__();self.publications=[]
            def command(self):pass
            def request(self,method,route,data,kind):
                super().request(method,route,data,kind)
                if route=='machine:writemem?address=EA03':self.publications.append(bytes(data))
        app=self.app();fake=NoAck();fake.started=True;fake.ram[0xea00]=4
        app.client=fake;app.deadline=app.clock()+remaining;events=[]
        app.journal=lambda name,**kw:events.append((name,kw))
        return app,fake,events

    def test_remaining_application_budget_is_not_a_twelve_second_native_hang(self):
        app,fake,events=self.command_fixture(0.36)
        with self.assertRaises(r.NativeDeadlineError) as caught:app.command(4,address=0x400,count=256)
        details=caught.exception.details
        self.assertEqual(details['scope'],'application');self.assertEqual(details['command'],4)
        self.assertLess(details['command_wait_seconds'],0.4)
        self.assertAlmostEqual(details['application_remaining_at_wait_start_seconds'],0.36)
        self.assertEqual(fake.publications,[b'\x04']);self.assertEqual(fake.ram[0xea03],4)
        self.assertTrue(details['command_will_not_be_reissued']);self.assertEqual(events[-1][0],'native_command_timeout')

    def test_ack_bound_expires_at_twelve_seconds_once_without_reissue(self):
        app,fake,events=self.command_fixture(60)
        with self.assertRaises(r.NativeDeadlineError) as caught:app.command(1,key=0x1c0d)
        self.assertEqual(caught.exception.details['scope'],'command_ack')
        self.assertGreaterEqual(caught.exception.details['command_wait_seconds'],12)
        self.assertLess(caught.exception.details['command_wait_seconds'],12.03)
        self.assertEqual(fake.publications,[b'\x01']);self.assertEqual(fake.ram[0xea03],1)
        self.assertEqual(len([e for e in events if e[0]=='native_command_go']),1)
        with self.assertRaisesRegex(ValueError,'already outstanding'):app.command(1,key=0x1c0d)
        self.assertEqual(fake.publications,[b'\x01'])

    def test_overall_timeout_is_retained_in_failed_application_evidence(self):
        class NeverRun(fixture.Fake):
            def request(self,method,route,data,kind):
                super().request(method,route,data,kind)
                if route=='runners:run_prg':self.ram[0xea00]=2
        app=self.app(seconds=10);fake=NeverRun()
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
            with self.assertRaises(r.NativeDeadlineError):app(fake,Path(directory))
            report=json.loads((Path(directory)/'application-result.json').read_text())
            self.assertEqual(report['status'],'failed');self.assertEqual(report['timeout']['scope'],'application')
            self.assertTrue((Path(directory)/'application-failure-before-reset.bin').exists())
            self.assertNotIn('helper_load',fake.events);self.assertEqual(fake.keys,[])

    def test_native_file_cli_forwards_explicit_cadence_and_budget_without_network(self):
        support=Path(r.__file__).parent
        spec=importlib.util.spec_from_file_location('private_observer_file_runner',support/'c64u_native_file_runner.py')
        runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
            directory=Path(directory)
            contents={'prg':fixture.PRG,'labels':b'labels','map':b'map','service':b'service',
                      'media':b'{}','staging':b'{}'}
            for name,body in contents.items():(directory/name).write_bytes(body)
            identity={'pins':[r.sha(contents[name]) for name in ['prg','labels','map']]}
            (directory/'identity').write_text(json.dumps(identity))
            args=['--recovery','native-file','--validate-only','--host','not-contacted',
                  '--output',str(ROOT/'agentworking/runs/mock-observer-validate'),
                  '--pal-clock-evidence','unused','--source','unused','--expected-prg-sha256',r.sha(fixture.PRG)]
            for name,option in [('prg','prg'),('labels','labels'),('map','map'),('service','service'),
                                ('media','media-manifest'),('staging','staging-manifest'),('identity','build-manifest')]:
                args.extend(['--'+option,str(directory/name)])
            for extra,expected in [([],{'seconds':180,'observation_interval':0.25}),
                                   (['--application-seconds','360','--observation-interval','2'],{'seconds':360,'observation_interval':2})]:
                with patch.object(runner.h,'base_prg',return_value=b'base'),patch.object(runner,'clock_evidence',return_value={}),\
                     patch.object(runner,'identities',return_value={}),patch.object(runner,'labels_from',return_value={}),\
                     patch.object(runner,'resident_from_map',return_value=[]),patch.object(runner.h,'SERVICE_SHA',r.sha(b'service')),\
                     patch.object(runner.h,'NativeFileClient') as client,patch.object(runner,'Application') as application,\
                     contextlib.redirect_stdout(io.StringIO()):
                    application.return_value.prg=fixture.PRG;application.return_value.base=0xea00
                    application.return_value.service_prg=b'service'
                    self.assertEqual(runner.main(args+extra),0)
                    for key,value in expected.items():self.assertEqual(application.call_args.kwargs[key],value)
                    client.assert_called_once()

    def test_cli_options_are_explicit_and_nonfinite_rejected_before_local_or_network_actions(self):
        support=Path(r.__file__).parent
        env={**os.environ,'PYTHONPATH':str(ROOT/'build_support')}
        wrapper="import runpy,sys; sys.path.insert(0,sys.argv[1]); import c64u_native_application; path=sys.argv.pop(2); sys.argv.pop(1); sys.argv[0]=path; runpy.run_path(path,run_name='__main__')"
        for filename in ['c64u_native_application.py','c64u_native_file_runner.py']:
            path=support/filename
            help_result=subprocess.run([sys.executable,'-c',wrapper,str(support),str(path),'--help'],env=env,capture_output=True,text=True)
            self.assertEqual(help_result.returncode,0,help_result.stderr)
            self.assertIn('--observation-interval',help_result.stdout);self.assertIn('--application-seconds',help_result.stdout)
            required=(['--host','not-contacted','--prg','absent','--labels','absent','--map','absent','--build-manifest','absent',
                       '--media-manifest','absent','--source','absent','--service','absent','--output','absent','--expected-prg-sha256','absent']
                      if filename=='c64u_native_application.py' else
                      ['--recovery','native-file','--host','not-contacted','--output','absent','--service','absent',
                       '--staging-manifest','absent','--pal-clock-evidence','absent'])
            for option,value in [('--observation-interval','nan'),('--application-seconds','inf'),('--application-seconds','601')]:
                failed=subprocess.run([sys.executable,'-c',wrapper,str(support),str(path),*required,option,value],env=env,capture_output=True,text=True)
                self.assertEqual(failed.returncode,2);self.assertIn('invalid',failed.stderr)
                self.assertNotIn('Traceback',failed.stderr)


if __name__=='__main__':unittest.main()
