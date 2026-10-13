#!/usr/bin/env python3
"""Execute the runner's real cleanup branch with hardware calls replaced by spies."""
import ast
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from readyfs_sd2iec_baseline import Baseline

ROOT=Path(os.environ.get('READYFS_CLEANUP_TEST_SOURCE',Path(__file__).parent))
TREE=ast.parse((ROOT/'run_readyfs_c64u_demo_v3.py').read_text())
RUN=next(n for n in TREE.body if isinstance(n,ast.Try) and n.finalbody)
START=next(i for i,n in enumerate(RUN.finalbody) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='restored' for t in n.targets))
END=next(i for i,n in enumerate(RUN.finalbody[START:],START) if isinstance(n,ast.If) and 'rc == 0' in ast.unparse(n.test))
CLEANUP=compile(ast.Module(body=RUN.finalbody[START:END],type_ignores=[]),'<actual runner cleanup>','exec')
SPEC=importlib.util.spec_from_file_location('tested_image_hardware',ROOT/'readyfs_sd2iec_image_hardware.py')
MODULE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MODULE)

class CleanupTests(unittest.TestCase):
    def test_busy_wait_or_suite_defers_all_hardware_restoration(self):
        for wait,suite_idle in [(True,True),(False,False),(True,False)]:
            with self.subTest(wait=wait,suite_idle=suite_idle):
                suite=SimpleNamespace(idle=suite_idle,restore=Mock())
                api=Mock();process=SimpleNamespace(run=Mock());event=Mock()
                context=dict(hardware_wait_unresolved=wait,extra_baseline=suite,
                    event=event,api=api,subprocess=process,saved={'speed':64},mounted=True)
                exec(CLEANUP,context)
                self.assertFalse(context['restored'])
                suite.restore.assert_not_called();api.assert_not_called();process.run.assert_not_called()
                self.assertEqual(event.call_args.kwargs['result'],'UNCONFIRMED')

    def test_launch_timeout_is_already_marked_unresolved(self):
        index=next(i for i,n in enumerate(RUN.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='response' for t in n.targets))
        code=compile(ast.Module(body=RUN.body[index-1:index+1],type_ignores=[]),'<actual launch>','exec')
        context=dict(hardware_wait_unresolved=False,binary=b'PRG',api=Mock(side_effect=TimeoutError('launch')))
        with self.assertRaises(TimeoutError):exec(code,context)
        self.assertTrue(context['hardware_wait_unresolved'])

    def test_shared_command_refuses_keys_after_unresolved_wait(self):
        fn=next(n for n in TREE.body if isinstance(n,ast.FunctionDef) and n.name=='command')
        keys=Mock();context=dict(hardware_wait_unresolved=True,keys=keys)
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<actual shared command>','exec'),context)
        with self.assertRaisesRegex(AssertionError,'not returned'):context['command']('CLEAR')
        keys.assert_not_called()

    def test_idle_suite_gets_restored(self):
        suite=SimpleNamespace(idle=True,restore=Mock())
        context=dict(hardware_wait_unresolved=False,extra_baseline=suite,event=Mock(),saved=None,mounted=False)
        exec(CLEANUP,context)
        self.assertTrue(context['restored']);suite.restore.assert_called_once_with()

    def test_native_state_failure_is_not_reported_as_restored(self):
        suite=SimpleNamespace(idle=True,restore=Mock(side_effect=RuntimeError('uncertain SD state')))
        api=Mock();process=SimpleNamespace(run=Mock())
        context=dict(hardware_wait_unresolved=False,extra_baseline=suite,event=Mock(),saved={'speed':64},mounted=True,api=api,subprocess=process)
        exec(CLEANUP,context)
        self.assertFalse(context['restored']);api.assert_not_called();process.run.assert_not_called()

    def test_image_requires_idle_config_and_fat_proof_before_recovery_prg(self):
        for idle,config,mounted,fat in [(False,True,False,True),(True,False,False,True),(True,True,True,True),(True,True,False,False)]:
            suite=MODULE.NativeImage.__new__(MODULE.NativeImage)
            suite.idle=idle;suite.config_restored=config;suite.maybe_mounted=mounted;suite.fat_verified=fat
            with patch.object(Baseline,'restore') as inherited:
                with self.assertRaises(AssertionError):suite.restore()
                inherited.assert_not_called()
        suite.idle=True;suite.config_restored=True;suite.maybe_mounted=False;suite.fat_verified=True
        with patch.object(Baseline,'restore') as inherited:
            suite.restore();inherited.assert_called_once_with()

    def test_clear_timeout_keeps_each_native_command_wrapper_busy(self):
        for filename in ('readyfs_sd2iec_image_hardware.py','readyfs_sd2iec_image_matrix.py'):
            tree=ast.parse((ROOT/filename).read_text())
            fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='command')
            fn.body=[n for n in fn.body if not isinstance(n,ast.Nonlocal)]
            suite=SimpleNamespace(idle=True)
            clear=Mock(side_effect=RuntimeError('CLEAR wait unresolved'))
            context=dict(self=suite,c={'command':clear},sequence=0)
            exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'<actual command wrapper>','exec'),context)
            with self.assertRaisesRegex(RuntimeError,'CLEAR wait'):context['command']('IEC 10: CONFIG')
            self.assertFalse(suite.idle)
            with self.assertRaises(AssertionError):context['command']('IEC 10: CONFIG')
            clear.assert_called_once_with('CLEAR',pause=1)

    def test_extension_and_hiding_restore_attempts_are_independent(self):
        tree=ast.parse((ROOT/'readyfs_sd2iec_image_hardware.py').read_text())
        run=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='run')
        upload=next(n for n in run.body if isinstance(n,ast.Try))
        final=compile(ast.Module(body=upload.finalbody,type_ignores=[]),'<actual configuration cleanup>','exec')
        for failed in ('IEC 10: EXTENSIONS 1','IEC 10: HIDE-EXTENSIONS off'):
            calls=[];suite=SimpleNamespace(idle=True,config_restored=False)
            def command(text,needle):
                calls.append(text)
                if text==failed:raise RuntimeError('simulated assertion failure')
                return '03,E01-:*+:I00:R,10,00'
            context=dict(self=suite,command=command,extension=1,hidden='-',original='03,E01-:*+:I00:R,10,00',c={'event':Mock()})
            with self.assertRaisesRegex(RuntimeError,'restoration'):exec(final,context)
            self.assertEqual(calls,['IEC 10: EXTENSIONS 1','IEC 10: HIDE-EXTENSIONS off','IEC 10: CONFIG'])
            self.assertTrue(suite.config_restored)
        suite=SimpleNamespace(idle=False,config_restored=False);command=Mock()
        context=dict(self=suite,command=command,extension=1,hidden='-',original='03,E01-',c={'event':Mock()})
        exec(final,context);command.assert_not_called();self.assertFalse(suite.config_restored)

if __name__=='__main__':unittest.main()
