"""Production runner option/default/reporting tests without device contact."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'build_support'))
import c64u_native_display_runner as r


class Tests(unittest.TestCase):
    def args(self,root):
        result=['--host','example.invalid','--output',str(root/'agentworking/runs/fresh')]
        for name in ('prg','labels','map','build-manifest','mode-proof','mode-proof-sha256','proposal-manifest','media-manifest','source','expected-prg-sha256','service','restore-prg','staging-manifest','pal-clock-evidence'):
            result+=['--'+name,'unused']
        return result
    def test_default_and_explicit_options_are_kept_and_shadow_pair_forwarded(self):
        for explicit in (False,True):
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);captured=[]
                def validate(args):
                    captured.append(args)
                    return SimpleNamespace(prg=b'p',service_prg=b's',seconds=args.application_seconds,observation_interval=args.observation_interval),object(),b'b',{}, {}, {}, {}
                args=self.args(root)+['--validate-only']
                if explicit:args+=['--observation-interval','2.0','--application-seconds','360','--shadow-package','package.json','--shadow-memory','memory.json']
                with patch.object(r,'PROJECT',root),patch.object(r,'validate_inputs',side_effect=validate),patch.object(r,'run_with_recovery',side_effect=AssertionError('Network workflow forbidden')),contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(r.main(args),0)
                value=captured[0]
                self.assertEqual(value.observation_interval,2.0 if explicit else 0.25)
                self.assertEqual(value.application_seconds,360 if explicit else 180)
                self.assertEqual(value.shadow_package,'package.json' if explicit else None)
                self.assertEqual(value.shadow_memory,'memory.json' if explicit else None)
    def test_nonfinite_or_out_of_range_options_rejected_before_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name,values in [('--observation-interval',['0.24','2.01','nan','inf']),('--application-seconds',['9','601','nan','inf'])]:
                for value in values:
                    with patch.object(r,'validate_inputs',side_effect=AssertionError('Should reject before validation')),contextlib.redirect_stderr(io.StringIO()):
                        with self.assertRaises(SystemExit):r.main(self.args(root)+[name,value])
    def test_native_file_report_explains_owned_ftp_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'agentworking/runs/fresh'
            app=SimpleNamespace(prg=b'p',service_prg=b's',seconds=180,observation_interval=0.25)
            def workflow(*args,**kw):
                out.mkdir(parents=True)
                return {'status':'passed','reu_restored':True,'configuration_restored':True,'reset_resumed':True,'limitations':['No persistent media or UCI writes; REST is development control only','first4MiB scope']}
            with patch.object(r,'PROJECT',root),patch.object(r,'validate_inputs',return_value=(app,object(),b'b',{}, {}, {}, {})),patch.object(r,'run_with_recovery',side_effect=workflow),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(r.main(self.args(root)),0)
            result=json.loads((out/'result.json').read_text())
            self.assertNotIn('No persistent media or UCI writes; REST is development control only',result['limitations'])
            self.assertIn('FTP creates only new owned backup/PRG files; native UCI opens its backup read-only',result['limitations'])
            self.assertIn('first4MiB scope',result['limitations'])

if __name__=='__main__':unittest.main()
