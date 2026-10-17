"""Provider provenance controls; native execution has separate integration tests."""
from pathlib import Path
import importlib.util
import sys, tempfile, unittest

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('config_release_inputs', ROOT / 'build_support/config_generation.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
LEGACY = {'START.labels': 'start/controller.labels', 'START.map': 'start/controller.map',
          'DOS64.labels': 'main/build/dos64.labels'}

class Inputs(unittest.TestCase):
    def setUp(self):
        (ROOT / 'build').mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix='config-inputs-', dir=ROOT / 'build')
        self.run = Path(self.tmp.name); self.rows = {}
        for name in LEGACY:
            p = self.run / 'products' / name; p.parent.mkdir(exist_ok=True)
            p.write_bytes(('fixture ' + name).encode())
            self.rows[name] = {'path': str(p), **m.digest(p)}
        self.j = {'run': str(self.run), 'products': self.rows, 'source_inputs': {}}

    def tearDown(self): self.tmp.cleanup()

    def test_named_and_recorded_legacy_layouts_are_accepted(self):
        self.assertEqual(m.release_metadata_paths(self.j), [Path(r['path']) for r in self.rows.values()])
        legacy = {'run': str(self.run), 'products': {}, 'source_inputs': {}}
        expected = []
        for name, relative in LEGACY.items():
            p = self.run / relative; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(name.encode()); legacy['products'][str(p)] = m.digest(p); expected.append(p)
        self.assertEqual(m.release_metadata_paths(legacy), expected)
        self.assertEqual(set(m.release_records(legacy)), set(map(str, expected)))

    def test_each_corrupted_metadata_file_is_refused(self):
        for row in self.rows.values():
            p = Path(row['path']); old = p.read_bytes(); p.write_bytes(old + b'bad')
            try:
                with self.assertRaises(RuntimeError): m.release_metadata_paths(self.j)
                with self.assertRaises(RuntimeError): m.release_records(self.j)
            finally: p.write_bytes(old)

    def test_valid_hash_outside_owned_run_is_not_metadata_authority(self):
        # The file exists and hashes correctly; ownership still must be checked.
        self.j['run'] = str(self.run / 'other-run')
        with self.assertRaisesRegex(RuntimeError, 'Unbound'): m.release_metadata_paths(self.j)

    def test_unrecorded_legacy_metadata_is_refused(self):
        for name, relative in LEGACY.items():
            p = self.run / relative; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(name.encode())
        self.j['products'] = {}
        with self.assertRaisesRegex(RuntimeError, 'Unbound'): m.release_metadata_paths(self.j)

    def test_unused_declared_product_corruption_is_refused(self):
        p = self.run / 'unused'; p.write_bytes(b'original')
        self.rows['unused'] = {'path': str(p), **m.digest(p)}
        p.write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError, 'product changed'): m.release_records(self.j)

    def test_changed_provider_source_and_generated_product_are_refused(self):
        for section in ['source_inputs', 'native_products']:
            p = self.run / section; p.write_bytes(b'before')
            self.j[section] = {str(p): m.digest(p)}; p.write_bytes(b'after')
            with self.assertRaises(RuntimeError): m.release_records(self.j)
            self.j[section] = {}

if __name__ == '__main__': unittest.main(verbosity=2)
