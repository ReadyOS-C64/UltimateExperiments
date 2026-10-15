import importlib.util
from pathlib import Path
import unittest
import copy
import sys
import tempfile

PATH = Path(__file__).resolve().parents[2] / 'build_support/clock_probe_verify.py'
SPEC = importlib.util.spec_from_file_location('clock_probe_verify', PATH)
v = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v)


def capture(delta=None, start=0xfff00000):
    if delta is None:
        delta = v.EXPECTED_TICKS
    prg = b'\x01\x08\xea\x4c\x0d\x08'
    ram = bytearray(65536)
    ram[0x801:0x805] = prg[2:]
    ram[0xe000:0xe008] = b'\x01\xa5\0\0\0\0\0\0'
    r = bytearray(40)
    r[:8] = b'DCK1\x01\xa5\0\x01'
    for offset, n, size in ((8, 100, 2), (10, 100, 2), (12, 311, 2),
                            (14, start, 4), (18, (start + delta) & 0xffffffff, 4),
                            (22, delta, 4), (32, 1, 2), (34, 2, 2)):
        r[offset:offset+size] = n.to_bytes(size, 'little')
    r[29] = 5
    ram[0x6000:0x6028] = r
    return ram, prg


class ClockProbeVerifierTests(unittest.TestCase):
    def test_valid_modulo_wrap_and_interval(self):
        ram, prg = capture()
        result = v.verify_capture(ram, prg, 0xe000)
        self.assertLess(result['end_ticks'], result['start_ticks'])
        self.assertEqual(result['delta_ticks'], 1965600)

    def test_endpoint_tolerance_is_inclusive_and_next_tick_rejected(self):
        for side in (-1, 1):
            ram, prg = capture(v.EXPECTED_TICKS + side*v.TOLERANCE_TICKS)
            v.verify_capture(ram, prg, 0xe000)
            ram, prg = capture(v.EXPECTED_TICKS + side*(v.TOLERANCE_TICKS+1))
            with self.assertRaises(ValueError):
                v.verify_capture(ram, prg, 0xe000)

    def test_pass_marker_does_not_accept_bad_delta_or_lost_frame(self):
        for delta in (0, 1, 65536, v.EXPECTED_TICKS + 19656, v.EXPECTED_TICKS * 16):
            ram, prg = capture(delta)
            with self.assertRaises(ValueError):
                v.verify_capture(ram, prg, 0xe000)

    def test_every_published_field_has_negative_guard(self):
        for offset, bad in ((0, 0), (4, 2), (5, 1), (6, 1), (7, 0),
                            (8, 99), (10, 99), (12, 54), (13, 0),
                            (22, 1), (26, 255), (28, 1), (29, 4),
                            (30, 1), (31, 1), (32, 16), (33, 1),
                            (34, 16), (35, 1), (36, 1), (39, 1)):
            ram, prg = capture()
            ram[0x6000+offset] = bad
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                v.verify_capture(ram, prg, 0xe000)

    def test_retry_metadata_requires_only_reload_sample_error(self):
        ram, prg = capture()
        ram[0x601a] = 127
        ram[0x601c] = 4
        v.verify_capture(ram, prg, 0xe000)
        for bad in (0, 1, 2, 3, 0xfe):
            ram[0x601c] = bad
            with self.assertRaises(ValueError):
                v.verify_capture(ram, prg, 0xe000)

    def test_mailbox_entire_state_and_prg_bytes_are_independent(self):
        for address in list(range(0xe000, 0xe008)) + [0x801, 0x804]:
            ram, prg = capture()
            ram[address] ^= 1
            with self.subTest(address=address), self.assertRaises(ValueError):
                v.verify_capture(ram, prg, 0xe000)

    def test_truncation_header_length_and_mailbox_bounds(self):
        ram, prg = capture()
        for badram, badprg, mailbox in ((ram[:-1], prg, 0xe000),
                                        (ram+b'\0', prg, 0xe000),
                                        (ram, b'\0\x08x', 0xe000),
                                        (ram, b'\x01\x08'+bytes(0x5800), 0xe000),
                                        (ram, prg, -1), (ram, prg, 65529)):
            with self.assertRaises(ValueError):
                v.verify_capture(badram, badprg, mailbox)

    def test_failure_inspection_never_accepts_and_rejects_truncated_ram(self):
        ram, prg = capture()
        result = v.inspect_capture(ram, prg, 0xe000)
        self.assertFalse(result['accepted'])
        self.assertEqual(result['kind'], 'diagnostic-only')
        self.assertTrue(result['captured_executable_matches'])
        with self.assertRaises(ValueError):
            v.inspect_capture(ram[:-1], prg, 0xe000)

    def test_three_distinct_speed_captures_and_ratio(self):
        _, prg = capture()
        entries = [(speed, capture(v.EXPECTED_TICKS + offset)[0])
                   for speed, offset in ((1, -v.TOLERANCE_TICKS), (16, 0), (64, v.TOLERANCE_TICKS))]
        result = v.verify_matrix(entries, prg, 0xe000)
        self.assertEqual(result['cross_speed_spread_ticks'], 2*v.TOLERANCE_TICKS)
        self.assertLessEqual(result['maximum_to_minimum_delta_ratio'],
                             result['maximum_ratio_from_bounds'])
        for bad in (entries[:-1], entries + entries[:1],
                    [(1, entries[0][1]), (16, entries[1][1]), (16, entries[2][1])]):
            with self.assertRaises(ValueError):
                v.verify_matrix(bad, prg, 0xe000)


# Workflow mocks only; no physical launch or network call occurs in these tests.
sys.path.insert(0, str(PATH.parent))
import c64u_clock_probe as runner


class FakeClient:
    def __init__(self, bad=None):
        self.turbo = {'Turbo Control': 'Off', 'CPU Speed': '64'}
        self.original = copy.deepcopy(self.turbo)
        self.bad = bad
        self.runs = 0
        self.reset = False
        self.resume = False
        self.applied = []
        self.failure_read_before_reset = False
    def get(self, route):
        if route == 'info':
            return {'firmware_version': 'mock'}
        if route.endswith('/Turbo%20Control'):
            return {'U64 Specific Settings': {'Turbo Control': {'values': ['Off', 'Manual']}}}
        if route.endswith('/CPU%20Speed'):
            return {'U64 Specific Settings': {'CPU Speed': {'values': [' 1', '16', '64']}}}
        if route == 'configs/U64%20Specific%20Settings':
            return {'U64 Specific Settings': copy.deepcopy(self.turbo)}
        if route == 'configs/C64%20and%20Cartridge%20Settings':
            return {'C64 and Cartridge Settings': {'video': 'PAL'}}
        if route == 'drives':
            image = 'changed' if self.bad == 'postreset' and self.reset else 'original'
            return {'drives': [{'A': {'image': image, 'last_error': ''}}]}
        raise AssertionError(route)
    def configs(self, value):
        self.turbo.update(value['U64 Specific Settings'])
        self.applied.append(copy.deepcopy(value))
        if self.bad == 'config' and len(self.applied) == 1:
            raise RuntimeError('configuration partially applied')
    def put(self, route):
        if route == 'machine:reset':
            self.reset = True
            if self.bad == 'reset':
                raise RuntimeError('reset failed')
        if route == 'machine:resume':
            self.resume = True
    def run(self, prg, mailbox):
        self.runs += 1
        if self.bad in ('launch', 'native', 'capture'):
            raise RuntimeError('target or launch failed after partial write')
    def read(self, address, length):
        assert address == 0 and length == 65536
        ram, _ = capture()
        if self.runs and not self.reset:
            self.failure_read_before_reset = True
        if self.bad == 'capture' and self.runs:
            raise RuntimeError('failure capture read also failed')
        if self.bad == 'native' and self.runs:
            ram[0xe001] = 0xe1
            ram[0xe004] = 3
            ram[0x6005] = 0xe1
            ram[0x6006] = 3
            ram[0x601c] = 0xfe
            ram[0x601d] = 2
        if self.bad == 'delta' and self.runs:
            ram[0x6016] ^= 1
        if self.bad == 'prg' and self.runs:
            ram[0x801] ^= 1
        return bytes(ram)


class ClockProbeRunnerTests(unittest.TestCase):
    def project(self, directory):
        project = Path(directory)/'project'
        (project/'build').mkdir(parents=True)
        _, prg = capture()
        (project/'build/dos64-clock-probe.prg').write_bytes(prg)
        (project/'build/dos64-clock-probe.map').write_text('workflow mock linker map')
        (project/'build/dos64-clock-probe.labels').write_text(
            'al 00E000 .dos64_mailbox\nal 00080D .dos64_entry\n'
            'al 006000 .dos64_host_clock_probe_record\n')
        return project
    def test_three_speed_matrix_exact_padded_option_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            project = self.project(directory)
            client = FakeClient()
            result = runner.run_matrix(client, project, Path(directory)/'run')
            self.assertEqual(result['status'], 'passed')
            self.assertEqual([v['mhz_setting'] for v in result['speeds']], [1, 16, 64])
            self.assertEqual(client.applied[0]['U64 Specific Settings']['CPU Speed'], ' 1')
            self.assertEqual(client.turbo, client.original)
            self.assertTrue(result['configuration_restored'])
            self.assertTrue(result['reset_resumed'])
            self.assertTrue(client.reset and client.resume)
    def test_launch_capture_and_reset_faults_never_forge_pass(self):
        for bad in ('launch', 'delta', 'prg', 'reset', 'postreset'):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as directory:
                project = self.project(directory)
                client = FakeClient(bad)
                result = runner.run_matrix(client, project, Path(directory)/'run')
                self.assertEqual(result['status'], 'failed')
                self.assertTrue(client.reset)
                self.assertEqual(client.turbo, client.original)
                self.assertTrue(client.resume)
    def test_configuration_failure_restores_and_resumes_without_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            project = self.project(directory)
            client = FakeClient('config')
            result = runner.run_matrix(client, project, Path(directory)/'run')
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(client.runs, 0)
            self.assertEqual(client.turbo, client.original)
            self.assertTrue(client.resume)
            self.assertFalse(client.reset)
    def test_native_fail_preserves_mailbox_record_and_full_ram_before_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            project = self.project(directory)
            client = FakeClient('native')
            out = Path(directory)/'run'
            result = runner.run_matrix(client, project, out)
            self.assertEqual(result['status'], 'failed')
            self.assertTrue(client.failure_read_before_reset)
            self.assertTrue(client.reset and client.resume)
            evidence = result['failure_capture']
            self.assertEqual(evidence['kind'], 'diagnostic-only')
            self.assertFalse(evidence['accepted'])
            self.assertEqual(evidence['mailbox_hex'], '01e1000003000000')
            self.assertEqual(evidence['error'], 3)
            self.assertEqual(evidence['last_clock_error'], 0xfe)
            self.assertEqual(evidence['phase'], 2)
            self.assertTrue(evidence['captured_executable_matches'])
            self.assertEqual(len((out/'ram-failed-1.bin').read_bytes()), 65536)
            self.assertEqual((out/'mailbox-failed-1.bin').read_bytes(),
                             bytes.fromhex('01e1000003000000'))
            self.assertEqual(len((out/'record-failed-1.bin').read_bytes()), 40)
    def test_failed_diagnostic_capture_still_restores_resets_and_resumes(self):
        with tempfile.TemporaryDirectory() as directory:
            project = self.project(directory)
            client = FakeClient('capture')
            result = runner.run_matrix(client, project, Path(directory)/'run')
            self.assertEqual(result['status'], 'failed')
            self.assertIn('capture_error', result['failure_capture'])
            self.assertTrue(client.reset and client.resume)
            self.assertTrue(result['configuration_restored'])
            self.assertTrue(result['reset_resumed'])

    def test_nonempty_directory_and_bad_prg_rejected_before_hardware(self):
        with tempfile.TemporaryDirectory() as directory:
            project = self.project(directory)
            out = Path(directory)/'run'
            out.mkdir()
            (out/'existing').write_text('preserve')
            client = FakeClient()
            with self.assertRaises(ValueError):
                runner.run_matrix(client, project, out)
            self.assertEqual(client.applied, [])
            (project/'build/dos64-clock-probe.prg').write_bytes(b'bad')
            with self.assertRaises(ValueError):
                runner.run_matrix(client, project, Path(directory)/'another')
            self.assertEqual(client.applied, [])


if __name__ == '__main__':
    unittest.main()
