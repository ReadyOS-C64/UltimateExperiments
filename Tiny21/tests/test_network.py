from pathlib import Path
import struct
import unittest

from tools.model import image
from tools.oracle import Network, cache_vector
from tools.peddle import Machine

MODEL = Path(__file__).resolve().parents[1] / "reference" / "TINY.BIN"


@unittest.skipUnless(MODEL.exists(), "supply the pinned reference/TINY.BIN")
class NetworkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checkpoint = MODEL.read_bytes()
        cls.image, cls.manifest = image(cls.checkpoint)

    def setUp(self):
        self.m = Machine()
        self.addCleanup(self.m.close)
        self.m.preload(self.image)
        self.m.put("reu_banks", 32)

    def read_vector(self, name):
        return struct.unpack_from("<96i", self.m.ram, self.m.symbols[name])

    def test_model_open_rejects_wrong_geometry_and_offsets(self):
        m = self.m
        self.assertFalse(m.run("model_open")[4] & 1)
        m.put("reu_banks", 1)
        self.assertEqual(m.run("model_open")[4] & 1, 1)
        m.put("reu_banks", 32)
        m.put("token_id", 1)
        m.put("token_pos", 0)
        for index in (0, 7, 12, 20, 64, 72 + 6):
            original = m.reu[index]
            m.reu[index] ^= 1
            self.assertTrue(m.run("model_open")[4] & 1)
            self.assertTrue(m.run("model_embed")[4] & 1)
            m.reu[index] = original

    def test_first_token_layer_front_in_assembly(self):
        m = self.m
        self.assertFalse(m.run("model_open")[4] & 1)
        token = ord("w") - 30
        m.put("token_id", token)
        m.put("token_pos", 0)
        self.assertFalse(m.run("model_embed")[4] & 1)
        trace = {}
        Network(self.checkpoint).step(token, logits=False, trace=trace)
        self.assertEqual(self.read_vector("residual"), tuple(trace["embedding"]))
        m.put("layer_id", 0)
        _, cycles, calls, size, flags, _ = m.run("layer_front", instruction_limit=5_000_000)
        self.assertFalse(flags & 1)
        self.assertEqual((calls, size), (19, 192 + 3 * 96 * 99))
        for name, tensor in (("normalized", "norm1"), ("query", "q"), ("key", "k"), ("value", "v")):
            self.assertEqual(self.read_vector(name), tuple(trace["0." + tensor]))
        print(f"first token layer 0 norm + Q/K/V: {cycles:,} CPU cycles, {calls} DMA calls, {size:,} bytes")
        _, cycles, calls, size, flags, _ = m.run("cache_store")
        self.assertFalse(flags & 1)
        self.assertEqual((calls, size), (1, 200))
        self.assertEqual(bytes(m.reu[0x80000:0x800c8]),
                         self.record(trace["0.k"]) + self.record(trace["0.v"]))
        print(f"first token layer 0 quantized KV write: {cycles:,} CPU cycles")
        # Exercise the full target tail in isolation before the attention
        # kernel is available. Only this boundary is a reference fixture.
        struct.pack_into("<96i", m.ram, m.symbols["attention"], *trace["0.attention"])
        _, cycles, calls, size, flags, _ = m.run("layer_tail", instruction_limit=10_000_000)
        self.assertFalse(flags & 1)
        self.assertEqual((calls, size), (29, 192 + 96 * 99 + 256 * 99 + 96 * 259))
        self.assertEqual(self.read_vector("normalized"), tuple(trace["0.norm2"]))
        self.assertEqual(self.read_vector("projected"), tuple(trace["0.f2"]))
        self.assertEqual(self.read_vector("residual"), tuple(trace["0.residual"]))
        got_hidden = struct.unpack_from("<256i", m.ram, m.symbols["hidden"])
        self.assertEqual(got_hidden, tuple(trace["0.relu"]))
        print(f"first token layer 0 O + FFN with reference attention: {cycles:,} CPU cycles")


    def test_full_target_first_token_matches_all_logits(self):
        m = self.m
        self.assertFalse(m.run("model_open")[4] & 1)
        for text in ("w", "7"):
            with self.subTest(text=text):
                token = ord(text) - 30
                m.put("token_id", token)
                net = Network(self.checkpoint)
                trace = {}
                expected = net.step(token, trace=trace)
                _, cycles, calls, size, flags, _ = m.run("model_first_token",
                                                          instruction_limit=50_000_000)
                self.assertFalse(flags & 1)
                actual = struct.unpack_from("<97i", m.ram, m.symbols["logits"])
                self.assertEqual(actual, tuple(expected))
                self.assertEqual(self.read_vector("residual"), tuple(trace["3.residual"]))
                for layer in range(4):
                    offset = 0x80000 + layer * 0x8000
                    self.assertEqual(bytes(m.reu[offset:offset + 200]),
                                     self.record(trace[f"{layer}.k"]) +
                                     self.record(trace[f"{layer}.v"]))
                print(f"full position-zero token {text!r}: {cycles:,} CPU cycles, "
                      f"{calls} DMA calls, {size:,} bytes")

    def test_real_multi_token_ingest_logits_and_argmax(self):
        m = self.m
        self.assertFalse(m.run("model_open")[4] & 1)
        m.run("model_reset")
        self.assertTrue(m.run("model_choose")[4] & 1)
        reference = Network(self.checkpoint)
        base = m.symbols["logits"]
        for position, text in enumerate("wha"):
            token = ord(text) - 30
            want = position != 0
            trace = {}
            expected = reference.step(token, logits=want, trace=trace)
            stats = m.run("model_ingest", token, x=want, instruction_limit=80_000_000)
            self.assertFalse(stats[4] & 1)
            self.assertEqual(m.get("token_pos", 1), position + 1)
            self.assertEqual(self.read_vector("attention"), tuple(trace["3.attention"]))
            flags = m.run("model_choose")[4]
            self.assertEqual(flags & 1, int(not want))
            if want:
                self.assertEqual(m.accumulator, max(range(97), key=expected.__getitem__))
                self.assertEqual(struct.unpack_from("<97i", m.ram, base), tuple(expected))
        m.run("model_reset")
        self.assertEqual(m.get("token_pos", 1), 0)
        self.assertTrue(m.run("model_choose")[4] & 1)
        m.put("token_pos", 128)
        stats = m.run("model_ingest", 2)
        self.assertEqual((stats[4] & 1, stats[2], m.get("token_pos", 1)), (1, 0, 128))

    def test_final_context_step_uses_all_128_positions(self):
        m = self.m
        self.assertFalse(m.run("model_open")[4] & 1)
        tokens = [ord(char) - 30 for char in ("what comes after 199? " * 6)[:128]]
        reference = Network(self.checkpoint)
        for token in tokens[:127]:
            reference.step(token, logits=False)
        for layer in range(4):
            base = 0x80000 + layer * 0x8000
            for position, ((key, key_peak), (value, value_peak)) in enumerate(
                    zip(reference.keys[layer], reference.values[layer])):
                struct.pack_into("<I96bI96b", m.reu, base + 200 * position,
                                 key_peak, *key, value_peak, *value)
            m.reu[base + 128 * 200] = 0x5a
        m.put("token_pos", 127)
        expected = reference.step(tokens[-1])
        stats = m.run("model_ingest", tokens[-1], x=1, instruction_limit=175_000_000,
                      model_length=len(self.image))
        stack_bytes = m.stack_bytes
        self.assertFalse(stats[4] & 1)
        self.assertEqual(m.get("token_pos", 1), 128)
        self.assertEqual(struct.unpack_from("<97i", m.ram, m.symbols["logits"]), tuple(expected))
        for layer in range(4):
            base = 0x80000 + layer * 0x8000
            self.assertEqual(m.reu[base + 128 * 200], 0x5a)
        overflow = m.run("model_ingest", 2)
        self.assertTrue(overflow[4] & 1)
        self.assertEqual(overflow[2], 0)
        print(f"full position-127 token: {stats[1]:,} CPU cycles, "
              f"{stats[2]} DMA calls, {stats[3]:,} bytes, {stack_bytes} stack bytes")

    @staticmethod
    def record(values):
        vector, peak = cache_vector(values)
        return struct.pack("<I96b", peak, *vector)

    def test_cache_at_distinct_layers_and_final_position(self):
        m = self.m
        keys = [-(2**31), 2**31 - 1, 32768, -32768] * 24
        values = [0] * 96
        for name, vector in (("key", keys), ("value", values)):
            struct.pack_into("<96i", m.ram, m.symbols[name], *vector)
        for layer, position in ((0, 0), (1, 127), (2, 64), (3, 127)):
            with self.subTest(layer=layer, position=position):
                offset = 0x80000 + layer * 0x8000 + position * 200
                m.reu[offset - 1] = 0x44
                m.reu[offset + 200] = 0x77
                m.put("layer_id", layer)
                m.put("token_pos", position)
                stats = m.run("cache_store")
                self.assertEqual((stats[4] & 1, stats[2], stats[3]), (0, 1, 200))
                self.assertEqual(bytes(m.reu[offset - 1:offset + 201]),
                                 b"D" + self.record(keys) + self.record(values) + b"w")
        m.put("token_pos", 128)
        stats = m.run("cache_store")
        self.assertEqual((stats[4] & 1, stats[2]), (1, 0))
