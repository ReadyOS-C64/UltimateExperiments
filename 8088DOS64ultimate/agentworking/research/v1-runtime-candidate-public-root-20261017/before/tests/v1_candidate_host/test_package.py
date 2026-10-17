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
        if cls.result['status'] != 'passed':
            raise RuntimeError('Run make v1-candidate first')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'build')
        self.p = Path(self.temp.name)
        # Native products and metadata are copies. No test edits a qualified run.
        coupled = json.loads((self.component_run / 'coupled/RESULT.json').read_text())
        local = self.p / 'coupled'
        shutil.copytree(Path(coupled['bundle']), local / 'bundle')
        for name in ['start/controller.labels', 'start/controller.map', 'main/build/dos64.labels']:
            target = local / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(coupled['run']) / name, target)
        coupled.update(run=str(local), bundle=str(local / 'bundle'))
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
        return b.assemble(self.c, self.s, self.g, self.p / name)

    def edit(self, path, callback):
        value = json.loads(path.read_text())
        callback(value)
        b.atomic_json(path, value)

    def test_complete_archive_contains_only_matched_native_assets_and_user_files(self):
        records, files = self.assemble()
        self.assertEqual(set(files), set(b.NATIVE) | {'BUILD.json', 'README.txt', 'DOS64.INI.example', 'SHA256SUMS'})
        self.assertFalse(any(n.endswith(('.IMG', '.CFG')) or n == 'START.PRG' for n in files))
        self.assertFalse(json.loads((self.p / 'package/BUILD.json').read_text())['V1_release_gates_closed'])
        self.assertNotIn(str(ROOT), (self.p / 'package/BUILD.json').read_text())
        self.assertNotIn(str(ROOT), (self.p / 'package/README.txt').read_text())
        b.archive(self.p / 'package', self.p / 'candidate.zip', files)
        b.verify(records)
        with zipfile.ZipFile(self.p / 'candidate.zip') as z:
            self.assertEqual(set(z.namelist()), set(files))
            self.assertTrue(all('/' not in n for n in z.namelist()))

    def test_each_of_nine_corrupted_native_products_is_rejected_before_packaging(self):
        paths, _ = b.component_inputs(self.c, self.s, self.g)
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
