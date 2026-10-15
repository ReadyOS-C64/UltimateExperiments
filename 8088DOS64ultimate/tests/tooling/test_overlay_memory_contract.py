from pathlib import Path
import re, unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'build_support'))
from verify_memory import verify
BASE = Path('build')

class OverlayMemoryContract(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.map = (BASE / 'dos64-tests.map').read_text()
        cls.labels = (BASE / 'dos64-tests.labels').read_text()
        cls.prg = (BASE / 'dos64-tests.prg').read_bytes()
        cls.payloads = {'FILECODE': (BASE / 'dos64-tests-resident.prg.files.bin').read_bytes(), 'RENDERCODE': (BASE / 'dos64-tests-resident.prg.render.bin').read_bytes()}

    def check(self, map=None, labels=None, prg=None, payloads=None):
        return verify(self.map if map is None else map, self.labels if labels is None else labels, self.prg if prg is None else prg, self.payloads if payloads is None else payloads)

    def test_real_exclusive_layout_and_packaged_outputs(self):
        r = self.check()
        self.assertTrue(r['passed'], r['errors'])
        self.assertEqual(r['load']['exclusive_overlay_window_bytes'], 1792)
        self.assertEqual(r['load']['overlay_source_bytes'], 1994)
        self.assertEqual(r['load']['startup_overlay_bytes'], 4096)
        self.assertEqual(r['load']['prg_bytes'], 26625)

    def test_header_every_byte_fault_is_rejected(self):
        for start in (24576, 26624):
            for i in range(16):
                data = bytearray(self.prg)
                data[start - 2049 + 2 + i] ^= 255
                self.assertFalse(self.check(prg=data)['passed'])

    def test_linked_payload_identity_is_required(self):
        for name in self.payloads:
            data = self.payloads.copy()
            raw = bytearray(data[name])
            raw[len(raw) // 2] ^= 255
            data[name] = raw
            self.assertFalse(self.check(payloads=data)['passed'])

    def test_slot_tail_and_device_gap_must_be_zero(self):
        for address in (24575, 26623, 28671):
            data = bytearray(self.prg)
            data[address - 2049 + 2] ^= 255
            self.assertFalse(self.check(prg=data)['passed'])

    def test_missing_one_overlay_fails(self):
        self.assertFalse(self.check(map=re.sub('^FILECODE\\s.*\\n', '', self.map, flags=re.M))['passed'])

    def test_overlay_run_start_must_be_exact(self):
        changed = re.sub('^(FILECODE\\s+)00C900(\\s+)00CD3F', '\\g<1>00C901\\g<2>00CD40', self.map, flags=re.M)
        self.assertNotEqual(changed, self.map)
        self.assertFalse(self.check(map=changed)['passed'])

    def test_arbitrary_overlap_is_still_rejected(self):
        changed = self.map.replace('FILECODE              00C900  00CD3F  000440', 'FILECODE              00C100  00C53F  000440')
        self.assertNotEqual(changed, self.map)
        self.assertFalse(self.check(map=changed)['passed'])

    def test_oversized_corrupt_segment_fails_without_crashing(self):
        changed = re.sub('^(FILECODE\\s+)00C900(\\s+)00CD3F(\\s+)000440', '\\g<1>00C900\\g<2>FFFFFF\\g<3>FF3700', self.map, flags=re.M)
        self.assertNotEqual(changed, self.map)
        self.assertFalse(self.check(map=changed)['passed'])

    def test_wrong_overlay_linker_file_offsets_and_sizes_fail(self):
        for symbol in ('__FILE_FILEOFFS__', '__RENDER_FILEOFFS__', '__FILECODE_SIZE__', '__RENDERCODE_RUN__'):
            changed = re.sub('^(al )([0-9A-F]+)( \\.' + symbol + ')$', lambda m: m[1] + f'{int(m[2], 16) + 1:06X}' + m[3], self.labels, flags=re.M)
            self.assertNotEqual(changed, self.labels)
            self.assertFalse(self.check(labels=changed)['passed'])

    def test_prg_header_and_full_startup_extent_are_required(self):
        for data in (b'\x00`' + self.prg[2:], self.prg[:-1], self.prg + b'\x00'):
            self.assertFalse(self.check(prg=data)['passed'])

    def test_missing_linked_payload_pair_fails(self):
        self.assertFalse(self.check(payloads={'FILECODE': self.payloads['FILECODE']})['passed'])

    def test_standalone_hardware_helper_remains_accepted(self):
        base = Path('build/dos64-range-probe')
        r = verify(base.with_suffix('.map').read_text(), base.with_suffix('.labels').read_text(), base.with_suffix('.prg').read_bytes())
        self.assertTrue(r['passed'], r['errors'])
        self.assertEqual(r['load']['startup_overlay_bytes'], 0)
if __name__ == '__main__':
    unittest.main(verbosity=2)
