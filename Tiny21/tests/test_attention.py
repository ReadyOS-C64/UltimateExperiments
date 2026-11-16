import random
import unittest

from tools.oracle import Q, exp_delta
from tools.peddle import Machine


class AttentionTest(unittest.TestCase):
    def test_all_lut_knots_interpolation_and_cutoff(self):
        m = Machine()
        self.addCleanup(m.close)
        rng = random.Random(24)
        deltas = [index * 1024 + sub for index in range(1024)
                  for sub in (0, 1, 512, 1023)]
        deltas.extend(rng.randrange(16 * Q) for _ in range(250))
        deltas.extend((16 * Q, 16 * Q + 1, 1 << 24, (1 << 32) - 1))
        for delta in deltas:
            m.put("exp_delta_q16", delta, 4)
            m.run("attention_exp")
            self.assertEqual(m.get("exp_value_q24", 4), exp_delta(delta), delta)

    def test_four_head_attention_streams_only_live_cache(self):
        import struct

        from tools.oracle import Network

        m = Machine()
        self.addCleanup(m.close)
        rng = random.Random(197)
        m.put("reu_banks", 32)
        for count in (2, 17, 32, 40, 41, 80, 81, 128):
            with self.subTest(count=count):
                layer = count % 4
                keys, values = [], []
                base = 0x80000 + 0x8000 * layer
                for pos in range(count):
                    k = [rng.randrange(-127, 128) for _ in range(96)]
                    v = [rng.randrange(-127, 128) for _ in range(96)]
                    kpeak = rng.randrange(300_000) if pos % 5 else 0
                    vpeak = rng.randrange(300_000) if pos % 7 else 0
                    keys.append((k, kpeak))
                    values.append((v, vpeak))
                    struct.pack_into("<I96bI96b", m.reu, base + 200 * pos,
                                     kpeak, *k, vpeak, *v)
                # Uniform first head; realistic and extreme score deltas
                # on the other heads.
                query = ([0] * 24 + [rng.randrange(-150_000, 150_000) for _ in range(48)]
                         + [rng.randrange(-2**31, 2**31) for _ in range(24)])
                struct.pack_into("<96i", m.ram, m.symbols["query"], *query)
                m.put("layer_id", layer)
                m.put("token_pos", count - 1)
                stats = m.run("cache_attention", instruction_limit=60_000_000)
                blocks = (count + 39) // 40
                tail = min(count, 40)
                self.assertEqual((stats[4] & 1, stats[2], stats[3]),
                                 (0, 2 * blocks - 1, 200 * (2 * count - tail)))
                reference = Network.__new__(Network)
                reference.keys = {layer: keys}
                reference.values = {layer: values}
                expected = reference.attend(layer, query)
                actual = struct.unpack_from("<96i", m.ram, m.symbols["attention"])
                self.assertEqual(actual, tuple(expected))
                print(f"attention {count:3} positions: {stats[1]:,} CPU cycles, "
                      f"{stats[2]} DMA calls, {stats[3]:,} bytes")
