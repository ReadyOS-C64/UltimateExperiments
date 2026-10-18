"""Example data disk: independently checked content and filesystem invariants."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'build_support'))
from example_disk import build, NAMES
from dos_disk_inspect import Volume


class ExampleDiskTests(unittest.TestCase):
    def test_deterministic_exact_allowlist_and_payloads(self):
        raw = build(ROOT / 'examples')
        self.assertEqual(raw, build(ROOT / 'examples'))
        self.assertEqual(len(raw), 360 * 1024)
        volume = Volume(raw)
        self.assertEqual(set(volume.payloads), set(NAMES))
        self.assertNotIn('IO.SYS', volume.payloads)
        self.assertNotIn('COMMAND.COM', volume.payloads)
        for name in NAMES:
            self.assertEqual(volume.payloads[name], (ROOT / 'examples' / name).read_bytes())

    def test_independent_parser_rejects_corrupt_fat_mirror(self):
        raw = bytearray(build(ROOT / 'examples'))
        raw[1536 + 3] ^= 1
        with self.assertRaisesRegex(ValueError, 'FAT size/copies'):
            Volume(raw)

    def test_committed_image_is_reproducible(self):
        self.assertEqual((ROOT / 'examples/EXAMPLES.IMG').read_bytes(), build(ROOT / 'examples'))


if __name__ == '__main__':
    unittest.main()
