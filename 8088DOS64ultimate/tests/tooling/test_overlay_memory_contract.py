from pathlib import Path
import re, unittest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"build_support"))
from verify_memory import verify
BASE = Path('build')

class OverlayMemoryContract(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.map = (BASE / 'dos64-tests.map').read_text()
        cls.labels = (BASE / 'dos64-tests.labels').read_text()
        cls.prg = (BASE / 'dos64-tests.prg').read_bytes()
        cls.payloads = {'FILECODE': (BASE / 'dos64-tests-resident.prg.files.bin').read_bytes(), 'RENDERCODE': (BASE / 'dos64-tests-resident.prg.render.bin').read_bytes(), 'INPUTCODE': (BASE / 'dos64-tests-resident.prg.input.bin').read_bytes(), 'IRQMAIN': (BASE / 'dos64-tests-resident.prg.pit.bin').read_bytes(), 'GFXCODE': (BASE / 'dos64-tests-resident.prg.gfx.bin').read_bytes(), 'HDCODE': (BASE/'dos64-tests-resident.prg.hd.bin').read_bytes(),'DISKCODE':(BASE/'dos64-tests-resident.prg.disk.bin').read_bytes()}

    def check(self, map=None, labels=None, prg=None, payloads=None):
        return verify(self.map if map is None else map, self.labels if labels is None else labels, self.prg if prg is None else prg, self.payloads if payloads is None else payloads,(BASE/"dos64-tests-resident.prg.import.bin").read_bytes(),(BASE/"dos64-tests-resident.prg.hdb.bin").read_bytes(),(BASE/"dos64-tests-resident.prg.saver.bin").read_bytes())

    def test_real_exclusive_layout_and_packaged_outputs(self):
        r = self.check()
        self.assertTrue(r['passed'], r['errors'])
        self.assertEqual(r['load']['exclusive_overlay_window_bytes'], 1792)
        self.assertEqual(r['load']['overlay_source_bytes'],1464+1248+1182+1764+1303+1472+1475)
        self.assertEqual(r['load']['startup_overlay_bytes'],16384)
        self.assertEqual(r['load']['prg_bytes'],47105)

    def test_header_every_byte_fault_is_rejected(self):
        for start in (24576, 26624, 32768,34816,36864,38912,45056,47104):
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
        for address in (24575,26623,28671,32767,34815,36863,38911,40959,44543,45055,47103,49151):
            data = bytearray(self.prg)
            data[address - 2049 + 2] ^= 255
            self.assertFalse(self.check(prg=data)['passed'])

    def test_missing_one_overlay_fails(self):
        self.assertFalse(self.check(map=re.sub('^FILECODE\\s.*\\n', '', self.map, flags=re.M))['passed'])

    def test_overlay_run_start_must_be_exact(self):
        changed = re.sub('^(FILECODE\\s+)00C900(\\s+)00CEB7', '\\g<1>00C901\\g<2>00CEB8', self.map, flags=re.M)
        self.assertNotEqual(changed, self.map)
        self.assertFalse(self.check(map=changed)['passed'])

    def test_arbitrary_overlap_is_still_rejected(self):
        changed = self.map.replace('FILECODE              00C900  00CEB7  0005B8', 'FILECODE              00C100  00C6B7  0005B8')
        self.assertNotEqual(changed, self.map)
        self.assertFalse(self.check(map=changed)['passed'])

    def test_oversized_corrupt_segment_fails_without_crashing(self):
        changed = re.sub('^(FILECODE\\s+)00C900(\\s+)00CEB7(\\s+)0005B8', '\\g<1>00C900\\g<2>FFFFFF\\g<3>FF3700', self.map, flags=re.M)
        self.assertNotEqual(changed, self.map)
        self.assertFalse(self.check(map=changed)['passed'])

    def test_wrong_overlay_linker_file_offsets_and_sizes_fail(self):
        for symbol in ('__FILE_FILEOFFS__', '__RENDER_FILEOFFS__', '__FILECODE_SIZE__', '__RENDERCODE_RUN__','__INPUTCODE_RUN__'):
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
class ColdPhaseMemoryContract(unittest.TestCase):
    setUpClass=classmethod(OverlayMemoryContract.setUpClass.__func__)
    check=OverlayMemoryContract.check
    def test_loaded_guard_is_initialized_once(self):
        import re
        at=int(re.search(r"^al ([0-9A-F]+) \.dos64_cold_open$",self.labels,re.M)[1],16)
        for value in (0,1,0xff):
            data=bytearray(self.prg);data[at-0x801+2]=value
            self.assertFalse(self.check(prg=data)["passed"])
    def test_native_reload_guard_is_initialized_once(self):
        at=int(re.search(r"^al ([0-9A-F]+) \.n_started$",self.labels,re.M)[1],16)
        for value in (1,0xa5,0xff):
            data=bytearray(self.prg);data[at-0x801+2]=value
            self.assertFalse(self.check(prg=data)["passed"])
    def test_combined_cold_output_is_exact(self):
        cold=bytearray((BASE/"dos64-tests-resident.prg.import.bin").read_bytes());cold[1000]^=255
        self.assertFalse(verify(self.map,self.labels,self.prg,self.payloads,cold,(BASE/"dos64-tests-resident.prg.hdb.bin").read_bytes(),(BASE/"dos64-tests-resident.prg.saver.bin").read_bytes())["passed"])
    def test_cold_segment_order_must_be_contiguous(self):
        changed=re.sub(r"^(COLDINIT\s+)([0-9A-F]+)(\s+)([0-9A-F]+)",lambda m:m[1]+f"{int(m[2],16)+1:06X}"+m[3]+f"{int(m[4],16)+1:06X}",self.map,flags=re.M)
        self.assertNotEqual(changed,self.map);self.assertFalse(self.check(map=changed)["passed"])
if __name__ == '__main__':
    unittest.main(verbosity=2)
