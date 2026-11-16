from pathlib import Path
import random
import struct
import unittest

from tools.model import decode, image
from tools.oracle import round_div
from tools.peddle import Machine

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "reference" / "TINY.BIN"


class CoreTest(unittest.TestCase):
    def setUp(self):
        self.m = Machine()
        self.addCleanup(self.m.close)

    def test_reu_boundaries_and_guards(self):
        m = self.m
        for border in (0x080000, 0x100000, 0xf80000):
            with self.subTest(border=hex(border)):
                far = border - 17
                data = bytes((n * 29 + 11) & 255 for n in range(61))
                m.reu[far - 1:far + 62] = b"?" + data + b"!"
                m.reu[far - 0x80000 + 17:far - 0x80000 + 61] = b"X" * 44
                m.ram[0x7fff] = 0x5a
                m.ram[0x803d] = 0x5a
                _, _, calls, moved, status, _ = m.transfer(far, 0x8000, 61)
                self.assertEqual((calls, moved, status & 1), (2, 61, 0))
                self.assertEqual(bytes(m.ram[0x8000:0x803d]), data)
                self.assertEqual((m.ram[0x7fff], m.ram[0x803d]), (0x5a, 0x5a))
                m.ram[0x8000:0x803d] = data[::-1]
                _, _, calls, moved, status, _ = m.transfer(far, 0x8000, 61, 0)
                self.assertEqual((calls, moved, status & 1), (2, 61, 0))
                self.assertEqual(bytes(m.reu[far - 1:far + 62]), b"?" + data[::-1] + b"!")
        m.reu[0xffffff] = 127
        self.assertEqual(m.transfer(0xffffff, 0x9fff, 1)[2:4], (1, 1))
        self.assertEqual(m.ram[0x9fff], 127)

    def test_reu_rejects_invalid_spans_before_dma(self):
        for case in ((0xffffff, 0x8000, 2), (0, 0x9fff, 2), (0, 0xdf00, 1),
                     (0, 0x7fff, 4), (0, 0x8000, 0xffff),
                     (0x7ffff, 0x8000, 2, 1, 1), (0, 0x8000, 1, 2)):
            with self.subTest(case=case):
                _, _, calls, moved, status, _ = self.m.transfer(*case)
                self.assertEqual((calls, moved, status & 1), (0, 0, 1))
        stats = self.m.transfer(0xffffff, 0x8000, 0)
        self.assertEqual((stats[2], stats[3], stats[4] & 1), (0, 0, 0))

    def test_all_unsigned_byte_products(self):
        for left in range(256):
            for right in range(256):
                self.m.put("mul_rhs", right)
                self.m.run("mul8_unsigned", left)
                self.assertEqual(self.m.get("mul_result", 2), left * right, (left, right))

    def test_signed_dot_at_extrema_and_random(self):
        rng = random.Random(23)
        for count in (24, 96, 256):
            for vector, weights in [
                    ([0] * count, [-128] * count),
                    ([0] * (count - 1) + [-32768], [127] * count),
                    ([-32768] * count, [-128] * count),
                    ([-32768] * count, [127] * count),
                    ([0, 12, -255, -256] * (count // 4), [127] * count),
                    ([rng.randrange(-32768, 32768) for _ in range(count)],
                     [rng.randrange(-128, 128) for _ in range(count)])]:
                self.m.prepare(vector)
                self.m.ram[0x8000:0x8000 + count] = bytes(w & 255 for w in weights)
                self.m.put("dot_weights", 0x8000, 2)
                self.m.run("dot_w8a16")
                self.assertEqual(self.m.get("dot_result", 4, signed=True),
                                 sum(x * w for x, w in zip(vector, weights)))

    def test_q24_scale_rounding_and_overflow(self):
        rng = random.Random(831)
        cases = [(1, 0x800000, 0), (-1, 0x800000, 0),
                 (-2**31, 1, 24), (2**31 - 1, 1, 24),
                 (-2**31, 2, 24), (2**31 - 1, 2, 24), (0, 1, 25)]
        # At every right shift, test both signs and the neighbors of a tie.
        # For shifts of 8, 16 and 24 bits the tie bit is in the discarded byte.
        for bits in range(1, 25):
            half = 1 << (bits - 1)
            cases.extend((sign * (3 * half + offset), 1, 24 - bits)
                         for offset in (-1, 0, 1) for sign in (-1, 1))
        cases += [(rng.randrange(-2**31, 2**31), rng.randrange(1 << 24),
                   rng.randrange(25)) for _ in range(256)]
        for dot, factor, shift in cases:
            self.m.put("dot_result", dot & 0xffffffff, 4)
            self.m.put("scale_factor", factor, 3)
            self.m.put("scale_shift", shift)
            expected = round_div((dot * factor) << shift, 1 << 24)
            carry = self.m.run("scale_dot")[4] & 1
            if shift > 24 or not -2**31 <= expected < 2**31:
                self.assertEqual(carry, 1)
            else:
                self.assertEqual(carry, 0)
                self.assertEqual(self.m.get("scale_value", 4, signed=True), expected)

    @unittest.skipUnless(MODEL.exists(), "supply the pinned reference/TINY.BIN")
    def test_token_and_position_embedding_tiles(self):
        data = MODEL.read_bytes()
        matrices, _ = decode(data)
        payload, manifest = image(data)
        self.m.preload(payload)
        self.m.put("reu_banks", 32)
        for name, indices in (("embedding", (0, 15, 16, 65, 96)),
                              ("position", (0, 15, 16, 64, 127))):
            matrix = matrices[name]
            self.m.put("embedding_rows", matrix.rows)
            for index in indices:
                self.m.put("reu_addr", manifest["regions"][name]["offset"], 3)
                self.m.put("embedding_index", index)
                stats = self.m.run("embedding_row")
                self.assertEqual(stats[4] & 1, 0)
                self.assertEqual(stats[2], 1)
                address = self.m.symbols["embedding_result"]
                actual = struct.unpack_from("<96i", self.m.ram, address)
                scale = round(matrix.scales[index] * (1 << 24))
                expected = tuple(round_div(weight * scale, 256)
                                 for weight in struct.unpack("<96b", matrix.weights[index]))
                self.assertEqual(actual, expected)
            self.m.put("embedding_index", matrix.rows)
            stats = self.m.run("embedding_row")
            self.assertEqual((stats[2], stats[4] & 1), (0, 1))

    @unittest.skipUnless(MODEL.exists(), "supply the pinned reference/TINY.BIN")
    def test_real_checkpoint_loaded_directly_and_consumed_by_assembly(self):
        data = MODEL.read_bytes()
        matrices, _ = decode(data)
        payload, manifest = image(data)
        self.m.preload(payload)
        self.m.put("reu_banks", 32)
        for name in ("embedding", "0.q", "0.f1", "0.f2"):
            with self.subTest(matrix=name):
                matrix = matrices[name]
                values = [(-1)**i * (i * 99 + 19) for i in range(matrix.cols)]
                self.m.prepare(values)
                offset = manifest["regions"][name]["offset"]
                self.m.put("reu_addr", offset, 3)
                cycles = moved = 0
                self.m.put("scale_shift", 2)
                for first in range(0, matrix.rows, 16):
                    weight_rows = matrix.weights[first:first + 16]
                    rows = len(weight_rows)
                    self.m.put("matrix_rows", rows)
                    _, clocks, _, size, status, _ = self.m.run("matrix_project")
                    self.assertFalse(status & 1)
                    cycles += clocks
                    moved += size
                    addr = self.m.symbols["matrix_dots"]
                    actual = struct.unpack(f"<{rows}i", bytes(self.m.ram[addr:addr + 4 * rows]))
                    expected = tuple(sum(x * w for x, w in zip(values, struct.unpack(
                        f"<{matrix.cols}b", weights))) for weights in weight_rows)
                    scaled = tuple(round_div(dot * round(scale * (1 << 24)), 1 << 22)
                                   for dot, scale in zip(expected, matrix.scales[first:first + 16]))
                    self.assertEqual(actual, scaled)
                self.assertEqual(moved, matrix.rows * (matrix.cols + 3))
                print(f"{name}: {matrix.rows}x{matrix.cols}, {cycles:,} CPU cycles, {moved:,} DMA bytes")


if __name__ == "__main__":
    unittest.main()
