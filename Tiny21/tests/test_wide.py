import math
import random
import unittest

from tools.peddle import Machine


class WideTest(unittest.TestCase):
    def test_wide_target_primitives(self):
        m = Machine()
        self.addCleanup(m.close)
        limit = (1 << 96) - 1
        rng = random.Random(6502)
        operands = [(0, 1), (1, 2), (2, 3), (7, 2), (limit, 1),
                    (limit, 1 << 95), (limit, limit), (limit - 1, limit),
                    (0x100, 0x130077), (0x00c0ffee, 0x01000680)]
        for _ in range(120):
            operands.append((rng.getrandbits(rng.randrange(1, 97)),
                             rng.getrandbits(rng.randrange(1, 97)) or 1))
        for a, b in operands:
            with self.subTest(a=a, b=b):
                m.put("wide_a", a, 12)
                m.put("wide_b", b, 12)
                m.run("wide_multiply")
                self.assertEqual(m.get("wide_product", 12), a * b & limit)
                m.run("wide_mul_byte")
                self.assertEqual(m.get("wide_product", 12), a * (b & 255) & limit)
                self.assertFalse(m.run("wide_divide")[4] & 1)
                self.assertEqual(m.get("wide_a", 12), a // b)
                self.assertEqual(m.get("wide_remainder", 12), a % b)
                m.put("wide_a", a, 12)
                self.assertFalse(m.run("wide_round_divide")[4] & 1)
                self.assertEqual(m.get("wide_a", 12), (a + b // 2) // b)
                m.put("wide_a", a, 12)
                m.run("wide_sqrt")
                self.assertEqual(m.get("wide_root", 12), math.isqrt(a))
        m.put("wide_b", 0, 12)
        self.assertTrue(m.run("wide_divide")[4] & 1)

    def test_score_division_at_rounding_boundaries_and_full_width(self):
        m = Machine()
        self.addCleanup(m.close)
        denominator = 127 << 40
        limit = (1 << 96) - 1
        rng = random.Random(127)
        numerators = [0, 1, limit, limit - 1]
        for quotient in (0, 1, 255, 256, (limit // denominator) - 1):
            for offset in (-1, 0, 1):
                numerators.append(quotient * denominator + denominator // 2 + offset)
        numerators.extend(rng.getrandbits(96) for _ in range(128))
        for n in numerators:
            m.put("wide_a", n, 12)
            m.run("wide_round_divide_score")
            self.assertEqual(m.get("wide_a", 12), (n + denominator // 2) // denominator, n)

    def test_bounded_byte_product_ignores_upper_operand_and_preserves_upper_result(self):
        m = Machine()
        self.addCleanup(m.close)
        rng = random.Random(0x6502)
        for width in (1, 4, 7, 11, 12):
            result_width = min(width + 1, 12)
            input_mask = (1 << (8 * width)) - 1
            result_mask = (1 << (8 * result_width)) - 1
            sentinel = int.from_bytes(b"\xa5" * 12, "little")
            for a, b in [(0, 0xff), (input_mask, 0xff), (input_mask, 0)] + [
                    (rng.getrandbits(96), rng.getrandbits(96)) for _ in range(40)]:
                m.put("wide_a", a, 12)
                m.put("wide_b", b, 12)
                m.put("wide_product", sentinel, 12)
                m.run("wide_mul_byte_limited", x=width)
                expected = ((a & input_mask) * (b & 0xff)) & result_mask
                self.assertEqual(m.get("wide_product", 12), expected | (sentinel & ~result_mask))
                self.assertEqual((m.get("wide_a", 12), m.get("wide_b", 12)), (a, b))

    def test_stream_division_at_divisor_width_boundaries(self):
        m = Machine()
        self.addCleanup(m.close)
        rng = random.Random(0x6502)
        for width in range(1, 9):
            top = 1 << (8 * width - 1)
            for b in (top >> 7, top - 1, top, top + 1, 2 * top - 1):
                for a in (0, b - 1, b, b + b // 2, (1 << 96) - 1,
                          rng.getrandbits(96)):
                    with self.subTest(a=a, b=b):
                        m.put("wide_a", a, 12)
                        m.put("wide_b", b, 12)
                        self.assertFalse(m.run("wide_divide")[4] & 1)
                        self.assertEqual((m.get("wide_a", 12), m.get("wide_remainder", 12)),
                                         divmod(a, b))
                        self.assertEqual(m.get("wide_b", 12), b)
                        m.put("wide_a", a, 12)
                        self.assertFalse(m.run("wide_round_divide")[4] & 1)
                        self.assertEqual(m.get("wide_a", 12), (a + b // 2) // b)
