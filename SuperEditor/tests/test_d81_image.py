"""Independent raw-sector oracle boundaries and retained native D81 controls."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from d81_image import D81Error, D81Image, IMAGE_BYTES


def fixture(payload: bytes) -> bytearray:
    image = bytearray(IMAGE_BYTES)
    def put(track, sector, data):
        offset = ((track - 1) * 40 + sector) * 256
        image[offset:offset + len(data)] = data
    put(40, 0, bytes([40, 3]))
    directory = bytearray(256)
    directory[:2] = b'\x00\xff'
    directory[2:5] = bytes([0x81, 1, 0])
    directory[5:21] = b'EXACT'.ljust(16, b'\xa0')
    count = max(1, (len(payload) + 253) // 254)
    directory[30:32] = count.to_bytes(2, 'little')
    put(40, 3, directory)
    for index in range(count):
        chunk = payload[index * 254:(index + 1) * 254]
        block = bytearray([0xAC] * 256)
        block[:2] = bytes([1, index + 1]) if index + 1 < count else bytes([0, len(chunk) + 1])
        block[2:2 + len(chunk)] = chunk
        put(1, index, block)
    return image


class OracleTest(unittest.TestCase):
    def test_terminal_and_sector_boundaries(self):
        for length in [0, 1, 2, 253, 254, 255, 508, 509]:
            with self.subTest(length=length):
                payload = bytes((index * 71 + 19) & 255 for index in range(length))
                result = D81Image(fixture(payload)).read(b'EXACT', kind=1)
                self.assertEqual(result.data, payload)
                self.assertEqual(len(result.sectors), max(1, (length + 253) // 254))

    def test_one_nul_is_distinct_from_empty(self):
        self.assertEqual(D81Image(fixture(b'')).read(b'EXACT').data, b'')
        self.assertEqual(D81Image(fixture(b'\0')).read(b'EXACT').data, b'\0')

    def test_refuses_malformed_chains(self):
        for link in [b'\0\0', b'\1\0', b'\x51\0', b'\1\x28', b'\x28\x03']:
            with self.subTest(link=link):
                image = fixture(b'a')
                image[:2] = link
                with self.assertRaises(D81Error):
                    D81Image(image).read(b'EXACT')

    def test_refuses_wrong_name_type_open_and_block_count(self):
        disk = D81Image(fixture(b'data'))
        with self.assertRaises(D81Error): disk.read(b'exact')
        with self.assertRaises(D81Error): disk.read(b'EXACT', kind=2)
        at = ((40 - 1) * 40 + 3) * 256
        for offset, value in [(2, 1), (30, 2)]:
            image = fixture(b'data'); image[at + offset] = value
            with self.assertRaises(D81Error): D81Image(image).read(b'EXACT')

    def test_refuses_directory_loops_and_bad_geometry(self):
        at = ((40 - 1) * 40 + 3) * 256
        for link in [b'\x28\x03', b'\x27\x03', b'\x28\0']:
            image = fixture(b'data'); image[at:at + 2] = link
            with self.assertRaises(D81Error): D81Image(image).entries()
        with self.assertRaises(D81Error): D81Image(b'')

    def test_retained_native_empty_controls(self):
        # These bytes were written/read by the isolated real KERNAL probe.
        folder = ROOT / 'agentsworking/evidence/M4/20261024T200911775765Z-empty-seq'
        if not (folder / 'working.d81').exists():
            self.skipTest('Optional retained native evidence is local to the working session')
        disk = D81Image((folder / 'working.d81').read_bytes())
        self.assertEqual(disk.read(b'EMPTYFINAL', kind=1).data, b'')
        self.assertEqual(disk.read(b'IMPORTED', kind=1).data, b'')
        self.assertEqual(disk.read(b'NUL', kind=1).data, b'\0')
        self.assertEqual(disk.read(b'CONTROL', kind=1).data, bytes(range(64)))


if __name__ == '__main__':
    unittest.main()
