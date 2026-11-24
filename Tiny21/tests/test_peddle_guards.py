import unittest

from tools.peddle import BUILD, Machine


class PeddleGuardTest(unittest.TestCase):
    def setUp(self):
        self.machine = Machine()
        self.addCleanup(self.machine.close)

    def run_fixture(self, code):
        # Host fixture only. The bytes execute as normal 6510 instructions.
        m = self.machine
        m.ram[0x0300:0x0300 + len(code)] = code
        m.symbols = {**m.symbols, "fixture": 0x0300}
        return m.run("fixture", model_length=0x1000)

    def test_unowned_cpu_write_cannot_mutate_memory(self):
        m = self.machine
        before = m.ram[0x1000]
        # LDA #$55; STA $1000; RTS.
        with self.assertRaisesRegex(AssertionError, r"unowned CPU write, address=\$001000"):
            self.run_fixture(bytes.fromhex("a955 8d0010 60"))
        self.assertEqual(m.ram[0x1000], before)
        # The same write in the work arena is legitimate.
        work = m.symbols["__WORK_START__"]
        self.run_fixture(bytes.fromhex("a955 8d") + work.to_bytes(2, "little") + b"\x60")
        self.assertEqual(m.ram[work], 0x55)

    def test_stack_high_water_balanced_return_and_guard(self):
        # Three PHA / PLA pairs nested on top of the two return bytes.
        self.run_fixture(bytes.fromhex("48 48 48 68 68 68 60"))
        self.assertEqual(self.machine.stack_bytes, 5)
        with self.assertRaisesRegex(AssertionError, "stack guard"):
            self.run_fixture(bytes([0x48] * 63 + [0x60]))

    def test_reu_dma_to_model_or_unowned_scratch_is_rejected(self):
        m = self.machine
        m.put("reu_banks", 32)
        m.put("reu_size", 1, 2)
        m.put("reu_ram", 0x8000, 2)
        m.put("reu_addr", 0, 3)
        m.put("reu_direction", 0)
        m.ram[0x8000] = 0x55
        before = m.reu[0]
        with self.assertRaisesRegex(AssertionError, r"unowned REU DMA, address=\$000000"):
            m.run("reu_transfer", model_length=0x1000)
        self.assertEqual(m.reu[0], before)
        m.put("reu_addr", 0x1000, 3)
        m.put("reu_direction", 1)
        with self.assertRaisesRegex(AssertionError, r"unowned REU DMA, address=\$001000"):
            m.run("reu_transfer", model_length=0x1000)
        m.put("reu_addr", 0x80000, 3)
        m.put("reu_direction", 0)
        self.assertFalse(m.run("reu_transfer", model_length=0x1000)[4] & 1)
        self.assertEqual(m.reu[0x80000], 0x55)

    def test_dma_guard_checks_device_writes_that_bypass_cpu_bus(self):
        # Set C64 address to $0400, transfer length 1, and command $91.
        # This bypasses the target's own transfer routine.
        with self.assertRaisesRegex(AssertionError, r"unowned CPU DMA, address=\$000400"):
            self.run_fixture(bytes.fromhex(
                "a900 8d02df a904 8d03df a901 8d07df a900 8d08df a991 8d01df 60"
            ))


@unittest.skipUnless((BUILD / "group8/core.bin").exists(), "build the group-eight candidate")
class GroupEightGuardTest(unittest.TestCase):
    def setUp(self):
        self.machine = Machine(BUILD / "group8")
        self.addCleanup(self.machine.close)
        self.machine.put("reu_banks", 32)

    def transfer(self, label, far, cpu, size, read=1):
        m = self.machine
        m.put("reu_addr", far, 3)
        m.put("reu_ram", cpu, 2)
        m.put("reu_size", size, 2)
        m.put("reu_direction", read)
        return m.run(label, model_length=380995)

    def test_projection_window_checks_both_spans_and_direction(self):
        m = self.machine
        label = "reu_group8_read"
        m.reu[380994] = 0xa5
        self.assertEqual(self.transfer(label, 380994, 0xcaff, 1)[2:4], (1, 1))
        self.assertEqual(m.ram[0xcaff], 0xa5)
        for far, cpu, size, read in ((0, 0xc3ff, 2, 1), (0, 0xcaff, 2, 1),
                                     (380994, 0xc400, 2, 1), (0, 0xc400, 1, 0),
                                     (0x80000, 0xc400, 1, 1)):
            with self.subTest(far=far, cpu=cpu, size=size, read=read):
                result = self.transfer(label, far, cpu, size, read)
                self.assertEqual(result[2:4], (0, 0))
                self.assertTrue(result[4] & 1)
        self.assertTrue(self.transfer("reu_transfer", 0, 0xc400, 1)[4] & 1)

    def test_normal_transfer_invalidates_only_the_overlapping_table(self):
        m = self.machine
        m.put("group4_ready", 2)
        self.transfer("reu_group8_read", 0, 0xc400, 1)
        self.assertEqual(m.get("group4_ready", 1), 2)
        self.transfer("reu_transfer", 0, 0x8000, 0)
        self.assertEqual(m.get("group4_ready", 1), 2)
        self.transfer("reu_transfer", 0, 0x8000, 1)
        self.assertEqual(m.get("group4_ready", 1), 0)
        m.put("group4_ready", 1)
        self.transfer("reu_transfer", 0, 0x8000, 1)
        self.assertEqual(m.get("group4_ready", 1), 1)
