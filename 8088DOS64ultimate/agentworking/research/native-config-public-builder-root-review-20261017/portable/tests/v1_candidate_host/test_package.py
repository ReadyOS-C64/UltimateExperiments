"""Packaging controls around real source-built native products, without device I/O."""
from pathlib import Path
import importlib.util
import json
import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.pycache_prefix = str(ROOT / 'build' / ('.absent-candidate-tests-' + str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
spec = importlib.util.spec_from_file_location('candidate_sut', ROOT / 'build_support/v1_candidate.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


class Candidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(os.environ.get('DOS64_CANDIDATE_RESULT', ROOT / 'build/v1-candidate/RESULT.json'))
        cls.result = json.loads(path.read_text())
        cls.component_run = Path(cls.result['run'])
        cls.runtime_media = cls.result.get('runtime_media', False)
        if cls.result['status'] != 'passed':
            raise RuntimeError('Run make v1-candidate first')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'build')
        self.p = Path(self.temp.name)
        # Native products and metadata are copies. No test edits a qualified run.
        coupled = json.loads((self.component_run / 'coupled/RESULT.json').read_text())
        local = self.p / 'coupled'
        shutil.copytree(Path(coupled['bundle']), local / 'bundle')
        for copied in (local / 'bundle').iterdir():
            copied.chmod(0o600)  # Only private test copies are made writable.
        # Copy metadata via its declared identities, independent of run layout.
        source_records = dict(coupled['source_inputs'])
        source_records.update(coupled.get('native_products', {}))
        for name, row in coupled.get('products', {}).items():
            source_records[str(Path(row['path'] if 'path' in row else name).resolve())] = {
                k: row[k] for k in ('sha256', 'bytes')}
        metadata = b.metadata_paths(coupled, source_records)
        for name, source in zip(['START.labels', 'START.map', 'DOS64.labels'], metadata):
            target = local / 'metadata' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            coupled['products'][name] = {'path': str(target), **b.digest(target)}
        coupled.update(run=str(local), bundle=str(local / 'bundle'))
        if self.runtime_media:
            self.runtime = self.p / 'runtime.json'
            shutil.copyfile(coupled['runtime_result'], self.runtime)
            coupled['runtime_result'] = str(self.runtime)
            coupled['runtime_result_identity'] = b.digest(self.runtime)
        self.c = self.p / 'coupled.json'
        b.atomic_json(self.c, coupled)
        setup = json.loads((self.component_run / 'setup/RESULT.json').read_text())
        build = self.p / 'setup/build'
        build.mkdir(parents=True)
        for name in setup['products']:
            (build / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(setup['work']) / 'build' / name, build / name)
        setup['work'] = str(build.parent)
        setup['release']['result_identity'] = b.digest(self.c)
        self.s = self.p / 'setup.json'
        b.atomic_json(self.s, setup)
        config = json.loads((self.component_run / 'config/RESULT.json').read_text())
        target = self.p / 'CONFIG.PRG'
        shutil.copyfile(config['products']['CONFIG.PRG']['path'], target)
        config['products']['CONFIG.PRG']['path'] = str(target)
        config['release']['result_identity'] = b.digest(self.c)
        self.g = self.p / 'config.json'
        b.atomic_json(self.g, config)

    def tearDown(self):
        self.temp.cleanup()

    def assemble(self, name='package'):
        return b.assemble(self.c, self.s, self.g, self.p / name, runtime_media=self.runtime_media)

    def edit(self, path, callback):
        value = json.loads(path.read_text())
        callback(value)
        b.atomic_json(path, value)

    def test_complete_archive_contains_only_matched_native_assets_and_user_files(self):
        records, files = self.assemble()
        self.assertEqual(set(files), set(b.RUNTIME_NATIVE if self.runtime_media else b.NATIVE) | {'BUILD.json', 'README.txt', 'DOS64.INI.example', 'SHA256SUMS'})
        self.assertFalse(any(n.endswith(('.IMG', '.CFG')) or n == 'START.PRG' for n in files))
        self.assertFalse(json.loads((self.p / 'package/BUILD.json').read_text())['V1_release_gates_closed'])
        self.assertNotIn(str(ROOT), (self.p / 'package/BUILD.json').read_text())
        self.assertNotIn(str(ROOT), (self.p / 'package/README.txt').read_text())
        b.archive(self.p / 'package', self.p / 'candidate.zip', files)
        b.verify(records)
        with zipfile.ZipFile(self.p / 'candidate.zip') as z:
            self.assertEqual(set(z.namelist()), set(files))
            self.assertTrue(all('/' not in n for n in z.namelist()))

    def test_each_corrupted_native_product_is_rejected_before_packaging(self):
        paths, _ = b.component_inputs(self.c, self.s, self.g, runtime_media=self.runtime_media)
        for name, path in paths.items():
            with self.subTest(name=name):
                original = path.read_bytes()
                path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
                try:
                    with self.assertRaises((RuntimeError, ValueError)):
                        self.assemble('out-' + name)
                    self.assertFalse((self.p / ('out-' + name)).exists())
                finally:
                    path.write_bytes(original)

    def test_missing_ini_overlay_is_rejected(self):
        (self.p / 'coupled/bundle/START.INO').unlink()
        with self.assertRaises((RuntimeError, FileNotFoundError)):
            self.assemble()

    def test_config_from_another_release_is_rejected(self):
        self.edit(self.g, lambda r: r['release']['assets']['DOS64.PRG'].update(sha256='0' * 64))
        with self.assertRaisesRegex(RuntimeError, 'different coupled release'):
            self.assemble()

    def test_unbound_setup_is_rejected(self):
        self.edit(self.s, lambda r: r.update(runtime_preflight=False, release=None))
        with self.assertRaisesRegex(RuntimeError, 'release-bound SETUP'):
            self.assemble()

    def test_setup_from_another_release_is_rejected(self):
        self.edit(self.s, lambda r: r['release']['assets']['DOS64.PRG'].update(sha256='0' * 64))
        with self.assertRaisesRegex(RuntimeError, 'SETUP was built for a different'):
            self.assemble()

    def test_stale_setup_receipt_pointer_is_rejected(self):
        self.edit(self.s, lambda r: r['release']['result_identity'].update(sha256='0' * 64))
        with self.assertRaisesRegex(RuntimeError, 'SETUP was built for a different'):
            self.assemble()

    def test_stale_config_receipt_pointer_is_rejected(self):
        self.edit(self.g, lambda r: r['release']['result_identity'].update(sha256='0' * 64))
        with self.assertRaisesRegex(RuntimeError, 'different coupled release'):
            self.assemble()

    def test_failed_component_cannot_be_packaged(self):
        for path in [self.c, self.s, self.g]:
            original = path.read_bytes()
            try:
                self.edit(path, lambda r: r.update(status='failed'))
                with self.assertRaisesRegex(RuntimeError, 'must have passed'):
                    self.assemble()
            finally:
                path.write_bytes(original)

    def test_components_with_conflicting_source_generations_are_rejected(self):
        coupled = json.loads(self.c.read_text())
        config = json.loads(self.g.read_text())
        shared = next(name for name in coupled['source_inputs'] if name in config['source_inputs'])
        self.edit(self.g, lambda r: r['source_inputs'][shared].update(sha256='0' * 64))
        with self.assertRaisesRegex(RuntimeError, 'Mixed source generations'):
            self.assemble()

    def test_existing_home_is_never_overwritten(self):
        home = self.p / 'package'
        home.mkdir()
        (home / 'C.IMG').write_bytes(b'owned user disk')
        with self.assertRaises(FileExistsError):
            self.assemble()
        self.assertEqual((home / 'C.IMG').read_bytes(), b'owned user disk')
        self.assertEqual([q.name for q in home.iterdir()], ['C.IMG'])

    def test_archive_detects_copy_change(self):
        _, files = self.assemble()
        (self.p / 'package/DOS64.PRG').write_bytes(b'changed after validation')
        with self.assertRaisesRegex(RuntimeError, 'archive bytes differ'):
            b.archive(self.p / 'package', self.p / 'candidate.zip', files)

    def test_runtime_requires_all_file_diagnostics_and_relocation_profiles(self):
        if not self.runtime_media:
            self.skipTest('runtime-media profile only')
        for key in ['trusted_boot_diagnostics','all_file_diagnostics','config_relocation']:
            original=self.g.read_bytes()
            try:
                self.edit(self.g,lambda r:r['memory'].update({key:False}))
                with self.assertRaisesRegex(RuntimeError,'CONFIG all-file diagnostics and relocation'):
                    self.assemble()
            finally:self.g.write_bytes(original)
        for key in ['terminal_payload_count','terminal_payload_run','terminal_load_only_source','terminal_tail_names_remain_readable','terminal_extra_ZP_bounded','C_stack_CD00_disjoint_helpers']:
            original=self.s.read_bytes()
            try:
                self.edit(self.s,lambda r:r['memory']['checks'].update({key:False}))
                with self.assertRaisesRegex(RuntimeError,'SETUP all-file diagnostics'):
                    self.assemble()
            finally:self.s.write_bytes(original)

    def test_runtime_dispatch_selects_new_profiles_default_dispatch_does_not(self):
        for enabled in [False,True]:
            commands=[]
            def command(argv,**kw):commands.append(argv)
            with patch.object(b.subprocess,'run',side_effect=command):
                with self.assertRaises(FileNotFoundError):b.build(self.p/('dispatch-'+str(enabled)),runtime_media=enabled)
            setup=next(row for row in commands if Path(row[2]).name=='setup_installer.py')
            config=next(row for row in commands if Path(row[2]).name=='config_generation.py')
            self.assertEqual('--all-file-diagnostics'in setup,enabled)
            self.assertEqual('--all-file-diagnostics'in config,enabled)
            self.assertEqual('--relocation'in config,enabled)

    def test_failed_build_preserves_previous_result_and_first_exception(self):
        out = self.p / 'output'
        out.mkdir()
        previous = b'{"status":"passed","old_candidate":true}\n'
        (out / 'RESULT.json').write_bytes(previous)
        first = RuntimeError('controlled compiler failure')
        with patch.object(b.subprocess, 'run', side_effect=first):
            with self.assertRaises(RuntimeError) as raised:
                b.build(out)
        self.assertIs(raised.exception, first)
        self.assertEqual((out / 'RESULT.json').read_bytes(), previous)
        runs = list(out.glob('run-*'))
        self.assertEqual(len(runs), 1)
        self.assertTrue((runs[0] / 'FAILURE.json').is_file())
        self.assertFalse((runs[0] / 'RESULT.json').exists())

    def test_declared_metadata_corruption_and_escape_rejected(self):
        coupled = json.loads(self.c.read_text())
        row = coupled['products']['START.labels']
        path = Path(row['path'])
        original = path.read_bytes()
        path.write_bytes(original + b'corrupt')
        with self.assertRaises(RuntimeError):
            self.assemble()
        path.write_bytes(original)
        self.edit(self.c, lambda r: r['products']['START.labels'].update(path=str(self.p / 'unowned.labels')))
        (self.p / 'unowned.labels').write_bytes(original)
        with self.assertRaisesRegex(RuntimeError, 'metadata'):
            self.assemble()

    def test_exact_bundle_inventory_rejects_extra_file(self):
        (self.p / 'coupled/bundle/UNEXPECTED.PRG').write_bytes(b'foreign')
        with self.assertRaisesRegex(RuntimeError, 'inventory'):
            self.assemble()

    def test_runtime_receipt_identity_and_enabled_format(self):
        if not self.runtime_media:
            self.skipTest('runtime-media profile only')
        self.edit(self.runtime, lambda r: r['flags'].update(DOS64_FLOPPY_FORMAT=0))
        with self.assertRaisesRegex(RuntimeError, 'stale runtime receipt'):
            self.assemble()
        self.edit(self.c, lambda r: r.update(runtime_result_identity=b.digest(self.runtime)))
        with self.assertRaisesRegex(RuntimeError, 'FORMAT'):
            self.assemble()

    def test_runtime_wrong_role_and_assets_rejected(self):
        if not self.runtime_media:
            self.skipTest('runtime-media profile only')
        original = self.runtime.read_bytes()
        for change, message in [
            (lambda r: r.update(role='unit'), 'actual runtime'),
            (lambda r: r['assets']['DOS64.MNU'].update(sha256='0'*64), 'different runtime'),
            (lambda r: r.update(MNU_REU_spans=[[0x3da000, 57344]]), 'layout'),
        ]:
            self.runtime.write_bytes(original)
            self.edit(self.runtime, change)
            self.edit(self.c, lambda r: r.update(runtime_result_identity=b.digest(self.runtime)))
            with self.assertRaisesRegex(RuntimeError, message):
                self.assemble()

    def test_runtime_diagnostic_profiles_required(self):
        if not self.runtime_media:
            self.skipTest('runtime-media profile only')
        original = self.s.read_bytes()
        self.edit(self.s, lambda r: r['memory']['checks'].update(file_helper_run=False))
        with self.assertRaisesRegex(RuntimeError, 'SETUP all-file diagnostics'):
            self.assemble()
        self.s.write_bytes(original)
        self.edit(self.g, lambda r: r['memory'].update(trusted_boot_diagnostics=False))
        with self.assertRaisesRegex(RuntimeError, 'CONFIG all-file diagnostics and relocation'):
            self.assemble()

    def test_archive_failure_and_report_failure_preserve_first_cause(self):
        out = self.p / 'failed-archive'
        out.mkdir()
        previous = b'{"status":"passed","old_candidate":true}\n'
        (out / 'RESULT.json').write_bytes(previous)
        first = KeyboardInterrupt('archive interrupted')
        def assembled(c, s, g, dest, **kwargs):
            dest.mkdir()
            (dest / 'x').write_bytes(b'asset')
            return {}, {'x': b.digest(dest / 'x')}
        with patch.object(b.subprocess, 'run'), patch.object(b, 'assemble', side_effect=assembled), patch.object(b, 'archive', side_effect=first), patch.object(b, 'atomic_json', side_effect=OSError('report failed')):
            with self.assertRaises(KeyboardInterrupt) as raised:
                b.build(out, runtime_media=self.runtime_media)
        self.assertIs(raised.exception, first)
        self.assertEqual((out / 'RESULT.json').read_bytes(), previous)

    def test_interrupt_during_result_publication_preserves_previous_pointer(self):
        out = self.p / 'publication'
        out.mkdir()
        previous = b'{"status":"passed","old_candidate":true}\n'
        (out / 'RESULT.json').write_bytes(previous)
        primary = KeyboardInterrupt('publication interrupted')
        real_atomic = b.atomic_json
        def controlled(path, value):
            if path == out / 'RESULT.json':
                raise primary
            real_atomic(path, value)
        def assembled(c, s, g, dest, **kwargs):
            dest.mkdir()
            (dest / 'x').write_bytes(b'asset')
            return {}, {'x': b.digest(dest / 'x')}
        with patch.object(b.subprocess, 'run'), patch.object(b, 'assemble', side_effect=assembled), patch.object(b, 'atomic_json', side_effect=controlled):
            with self.assertRaises(KeyboardInterrupt) as raised:
                b.build(out, runtime_media=self.runtime_media)
        self.assertIs(raised.exception, primary)
        self.assertEqual((out / 'RESULT.json').read_bytes(), previous)
        self.assertTrue(next(out.glob('run-*/FAILURE.json')).is_file())

    def test_runtime_build_plan_is_native_only_and_scrubs_environment(self):
        commands = []
        primary = RuntimeError('stop before assembly')
        def command(argv, **kwargs):
            commands.append((argv, kwargs['env']))
        with patch.dict(os.environ, {'PYTHONPATH':'untrusted', 'MAKEFLAGS':'--eval=bad', 'DOS64_CC65':'chosen-cc65'}), patch.object(b.subprocess, 'run', side_effect=command), patch.object(b, 'assemble', side_effect=primary):
            with self.assertRaises(RuntimeError) as raised:
                b.build(self.p / 'plan', runtime_media=True)
        self.assertIs(raised.exception, primary)
        self.assertEqual([Path(a[0][2]).name for a in commands], ['runtime_media.py', 'cold_start.py', 'setup_installer.py', 'config_generation.py'])
        self.assertIn('--floppy-format', commands[0][0])
        self.assertIn('--runtime-result', commands[1][0])
        for argv, env in commands:
            self.assertNotIn('PYTHONPATH', env)
            self.assertNotIn('MAKEFLAGS', env)
            self.assertEqual(env['DOS64_CC65'], 'chosen-cc65')
            self.assertNotIn('--test', argv)
        for flag in ['--cold-inventory','--start20k','--mnu56k','--startup-diagnostics','--file-diagnostics']:
            self.assertIn(flag, commands[2][0])
        self.assertNotIn('--file-diagnostics', commands[3][0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
