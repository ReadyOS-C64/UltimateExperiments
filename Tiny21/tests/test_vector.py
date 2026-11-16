from pathlib import Path
import random
import struct
import unittest

from tools.model import image
from tools.oracle import Network, dense_input, normalize
from tools.peddle import Machine

MODEL = Path(__file__).resolve().parents[1] / "reference" / "TINY.BIN"
INPUT = 0xa000
OUTPUT = 0xa400
GAINS = 0xa800


class VectorTest(unittest.TestCase):
    def setUp(self):
        self.m = Machine()
        self.addCleanup(self.m.close)
        self.m.put("vector_source", INPUT, 2)
        self.m.put("vector_dest", OUTPUT, 2)
        self.m.put("vector_gains", GAINS, 2)

    def load_vector(self, values):
        struct.pack_into(f"<{len(values)}i", self.m.ram, INPUT, *values)
        self.m.put("vector_count", len(values) & 255)

    def test_target_add_and_dense_pack(self):
        m = self.m
        rng = random.Random(76)
        cases = [[0], [32767, -32767], [65534, -65534], [65535, -65535],
                 [-2**31, 2**31 - 1], [rng.randrange(-1_000_000, 1_000_000)
                                      for _ in range(256)]]
        for values in cases:
            with self.subTest(peak=max(map(abs, values))):
                self.load_vector(values)
                m.run("vector_pack")
                expected, shift = dense_input(values)
                self.assertEqual(m.get("scale_shift", 1), shift)
                lo = m.symbols["activation_lo"]
                hi = m.symbols["activation_hi"]
                got = [m.ram[lo + i] + 256 * (m.ram[hi + i] - (256 if m.ram[hi + i] >= 128 else 0))
                       for i in range(len(values))]
                self.assertEqual(got, expected)
        values = [1, 255, 65535, -1, -65535] * 19 + [257]
        offsets = [-v - 2 for v in values]
        self.load_vector(values)
        struct.pack_into("<96i", m.ram, OUTPUT, *offsets)
        m.run("vector_add")
        self.assertEqual(struct.unpack_from("<96i", m.ram, OUTPUT), (-2,) * 96)

    def check_norm(self, values, gains, dest=OUTPUT):
        m = self.m
        self.load_vector(values)
        m.put("vector_dest", dest, 2)
        struct.pack_into("<96h", m.ram, GAINS, *gains)
        stats = m.run("vector_norm")
        self.assertFalse(stats[4] & 1)
        actual = struct.unpack_from("<96i", m.ram, dest)
        self.assertEqual(actual, tuple(normalize(values, gains)))
        return stats[1]

    def test_target_norm_signed_inputs_gains_and_energy_extrema(self):
        rng = random.Random(0x6510)
        gains = [rng.randrange(-32768, 32768) for _ in range(96)]
        self.check_norm([0] * 96, gains)
        self.check_norm([15, -11, 2] * 32, gains, INPUT)
        self.check_norm([rng.randrange(-2**31, 2**31) for _ in range(96)], gains)
        self.check_norm([-(2**31)] * 96, [-32768, -256, -1, 0] * 24)

    @unittest.skipUnless(MODEL.exists(), "supply the pinned reference/TINY.BIN")
    def test_target_first_real_embedding_residual_and_norm(self):
        m = self.m
        checkpoint = MODEL.read_bytes()
        payload, manifest = image(checkpoint)
        m.preload(payload)
        m.put("reu_banks", 32)
        token = ord("w") - 30
        trace = {}
        network = Network(checkpoint)
        network.step(token, logits=False, trace=trace)
        for name, index in (("embedding", token), ("position", 0)):
            region = manifest["regions"][name]
            m.put("reu_addr", region["offset"], 3)
            m.put("embedding_index", index)
            m.put("embedding_rows", region["rows"])
            self.assertFalse(m.run("embedding_row")[4] & 1)
            start = m.symbols["embedding_result"]
            if name == "embedding":
                m.ram[INPUT:INPUT + 384] = m.ram[start:start + 384]
            else:
                m.put("vector_source", start, 2)
                m.put("vector_dest", INPUT, 2)
                m.put("vector_count", 96)
                m.run("vector_add")
        residual = struct.unpack_from("<96i", m.ram, INPUT)
        self.assertEqual(residual, tuple(trace["embedding"]))
        m.put("vector_source", INPUT, 2)
        cycles = self.check_norm(residual, network.gains["0.g1"])
        self.assertEqual(struct.unpack_from("<96i", m.ram, OUTPUT), tuple(trace["0.norm1"]))
        print(f"first layer-0 RMSNorm: {cycles:,} CPU cycles")
