import importlib.util
import pathlib
import struct
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("overlay_package", ROOT / "build_support/overlay_package.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class OverlayPackageTests(unittest.TestCase):
    def test_layout_constants_match_native_contract(self):
        source = (ROOT / "include/overlays.inc").read_text()
        for name, expected in (("OV_WINDOW", m.WINDOW), ("OV_WINDOW_SIZE", m.WINDOW_SIZE),
                               ("OV_SLOT_SIZE", m.SLOT_SIZE), ("OV_SOURCE", m.SOURCE),
                               ("OV_ASSETS", m.ASSETS), ("OV_HEADER", m.HEADER)):
            value = re.search(r"^" + name + r" = \$(\w+)$", source, re.M)
            self.assertIsNotNone(value, name)
            self.assertEqual(expected, int(value.group(1), 16), name)

    def test_exact_slots_identity_padding_and_payload(self):
        for identity in (1, 2, 3, 4, 5, 6, 7):
            for n in (1, 255, 256, 1088, 1792):
                payload = bytes(i % 251 for i in range(n))
                slot = m.slot(payload, identity)
                self.assertEqual(2048, len(slot))
                self.assertEqual(b"D64O" + bytes((1, identity)), slot[:6])
                self.assertEqual((n, 0xC900, 0), struct.unpack("<HHH", slot[6:12]))
                self.assertEqual({1:b"FILE",2:b"TEXT",3:b"KEYS",4:b"TIME",5:b"CGA ",6:b"HD  ",7:b"DSK "}[identity], slot[12:16])
                self.assertEqual(payload, slot[16:16+n])
                self.assertEqual(bytes(2032-n), slot[16+n:])

    def test_reject_empty_oversize_and_unknown(self):
        for payload, identity in ((b"", 1), (bytes(1793), 2), (b"x", 0), (b"x", 8), (b"x", 255)):
            with self.assertRaises(ValueError):
                m.slot(payload, identity)

    def test_contiguous_prg_places_source_exactly_without_mutating_resident(self):
        for end in (0x802, 0x5000, 0x6000):
            original = b"\x01\x08" + bytes((end-0x801))
            prg, assets = m.package(original, b"\x60", b"\xea\x60")
            self.assertEqual(original, prg[:len(original)])
            self.assertEqual(0x7000-0x801+2, len(prg))
            self.assertEqual(assets, prg[0x6000-0x801+2:])
            self.assertEqual(b"FILE", assets[12:16])
            self.assertEqual(b"TEXT", assets[2048+12:2048+16])

    def test_reject_wrong_load_truncated_and_resident_overlap(self):
        for prg in (b"", b"\x01\x08", b"\x00\x08\x60", b"\x01\x08"+bytes(0x6001-0x801)):
            with self.assertRaises(ValueError):
                m.package(prg, b"\x60", b"\x60")


if __name__ == "__main__":
    unittest.main()
