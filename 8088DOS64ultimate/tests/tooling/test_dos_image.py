import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "build_support"))
from dos_image import Fat12Image, ImageError, canonical_json, clone_and_extract

SCRATCH = PROJECT / "agentworking" / "scratch"
SCRATCH.mkdir(parents=True, exist_ok=True)


def fat_set(image, cluster, value, copy=None):
    """Fixture writer using three-byte pairs, independently of reader indexing."""
    spf = struct.unpack_from("<H", image, 22)[0]
    copies = range(image[16]) if copy is None else (copy,)
    for number in copies:
        base = 512 + number * spf * 512 + (cluster // 2) * 3
        if cluster & 1:
            image[base + 1] = (image[base + 1] & 15) | ((value & 15) << 4)
            image[base + 2] = value >> 4
        else:
            image[base] = value & 255
            image[base + 1] = (image[base + 1] & 240) | (value >> 8)


def fixture(total=14, spf=1, start=2):
    image = bytearray(total * 512)
    image[:3] = b"\xeb\x3c\x90"
    image[3:11] = b"DOS64TST"
    struct.pack_into("<HBHBHHBHHHI", image, 11, 512, 1, 1, 2, 16, total, 0xf0, spf, 7 if total == 14 else 50, 2, 0)
    image[510:512] = b"\x55\xaa"
    for copy in range(2):
        image[(1 + copy * spf) * 512:(1 + copy * spf) * 512 + 3] = b"\xf0\xff\xff"
    root = (1 + 2 * spf) * 512
    image[root:root + 11] = b"FILE    BIN"
    image[root + 11] = 0x20
    struct.pack_into("<HI", image, root + 26, start, 1025)
    for cluster, next_cluster in ((start, start + 1), (start + 1, start + 2), (start + 2, 0xfff)):
        fat_set(image, cluster, next_cluster)
    data_lba = 2 + 2 * spf
    for n in range(3):
        position = (data_lba + start - 2 + n) * 512
        image[position:position + 512] = bytes([0x41 + n]) * 512
    return image


class DosImageTests(unittest.TestCase):
    def assertImageError(self, code, function, *args):
        with self.assertRaises(ImageError) as caught:
            function(*args)
        self.assertEqual(code, caught.exception.code)

    def test_actual_images_and_all_file_hashes_match_preexisting_inventory(self):
        record = json.loads((PROJECT / "tests/fixtures/dos33-inventory.json").read_text())
        for original in record["images"]:
            with self.subTest(original["path"]):
                data = (PROJECT / original["path"]).read_bytes()
                self.assertEqual(original["sha256"], hashlib.sha256(data).hexdigest())
                image = Fat12Image(data)
                manifest = image.manifest()
                self.assertEqual((5, 12, 720), (image.root_lba, image.data_lba, image.total_sectors))
                for entry in original["root_files"]:
                    if "sha256" in entry:
                        content = image.read_file(entry["name"])
                        self.assertEqual(entry["size"], len(content))
                        self.assertEqual(entry["sha256"], hashlib.sha256(content).hexdigest())
                self.assertEqual(canonical_json(manifest), canonical_json(image.manifest()))
                self.assertEqual(data, image.data)

    def test_all_supplied_chs_addresses_roundtrip_and_bounds(self):
        source = sorted((PROJECT / "reference").glob("*1 of 3.img"))[0]
        image = Fat12Image.from_path(source)
        for lba in range(720):
            self.assertEqual(lba, image.chs_to_lba(*image.lba_to_chs(lba)))
        self.assertEqual((0, 0, 6), image.lba_to_chs(5))
        self.assertEqual((39, 1, 9), image.lba_to_chs(719))
        for chs in ((-1, 0, 1), (40, 0, 1), (0, 2, 1), (0, 0, 0), (0, 0, 10)):
            self.assertImageError("chs_bounds", image.chs_to_lba, *chs)
        for lba in (-1, 720):
            self.assertImageError("lba_bounds", image.lba_to_chs, lba)
        for lba, count in ((-1, 1), (719, 2), (0, 0), (0, -1)):
            self.assertImageError("sector_range", image.read_sectors, lba, count)
        self.assertEqual(1024, len(image.read_sectors(0, 2)))

    def test_even_odd_fat_entries_and_cross_sector_packed_entry(self):
        data = fixture()
        image = Fat12Image(data)
        self.assertEqual((3, 4, 0xfff), tuple(image.fat_entry(c) for c in (2, 3, 4)))
        self.assertEqual(b"A" * 512 + b"B" * 512 + b"C", image.read_file("file.bin"))
        self.assertEqual((2, 3, 4), image.cluster_chain(image.find("FILE.BIN")))
        # Cluster341 has its packed FAT bytes across a 512-byte boundary.
        large = Fat12Image(fixture(total=1000, spf=3, start=341))
        self.assertEqual((342, 343, 0xfff), tuple(large.fat_entry(c) for c in (341, 342, 343)))
        self.assertEqual(image.read_file("FILE.BIN"), large.read_file("FILE.BIN"))
        self.assertImageError("fat_index", image.fat_entry, -1)
        self.assertImageError("fat_index", image.fat_entry, 4095)

    def test_input_is_immutable_snapshot(self):
        data = fixture()
        image = Fat12Image(data)
        data[:] = b"\x00" * len(data)
        self.assertEqual(1025, len(image.read_file("FILE.BIN")))

    def test_bpb_signature_size_layout_and_fat_capacity_rejected(self):
        self.assertImageError("short_boot_sector", Fat12Image, b"x" * 511)
        base = fixture()
        mutations = (("boot_signature", 510, b"\x00\x00"),
                     ("sector_size", 11, struct.pack("<H", 1024)),
                     ("cluster_size", 13, b"\x03"),
                     ("layout_fields", 14, b"\x00\x00"),
                     ("layout_fields", 16, b"\x00"),
                     ("layout_fields", 17, b"\x00\x00"),
                     ("layout_fields", 22, b"\x00\x00"),
                     ("chs_geometry", 24, b"\x00\x00"),
                     ("chs_geometry", 26, b"\x01\x01"),
                     ("media_descriptor", 21, b"\x01"),
                     ("conflicting_sector_counts", 32, struct.pack("<I", 14)),
                     ("layout_bounds", 17, struct.pack("<H", 65535)))
        for code, offset, value in mutations:
            data = bytearray(base)
            data[offset:offset + len(value)] = value
            with self.subTest(code=code, offset=offset):
                self.assertImageError(code, Fat12Image, data)
        self.assertImageError("image_length", Fat12Image, base[:-1])
        self.assertImageError("image_length", Fat12Image, base + b"\x00")
        large = fixture(total=1000, spf=3)
        struct.pack_into("<H", large, 22, 1)
        self.assertImageError("fat_capacity", Fat12Image, large)
        too_large = fixture(total=5000, spf=16)
        self.assertImageError("not_fat12", Fat12Image, too_large)

    def test_total32_bpb_and_single_fat_volume(self):
        data = fixture()
        struct.pack_into("<H", data, 19, 0)
        struct.pack_into("<I", data, 32, 14)
        self.assertEqual(14, Fat12Image(data).total_sectors)
        # Remove the second FAT sector and update the exact volume count.
        data = fixture()
        del data[1024:1536]
        data[16] = 1
        struct.pack_into("<H", data, 19, 13)
        image = Fat12Image(data)
        self.assertEqual((2, 3), (image.root_lba, image.data_lba))
        self.assertEqual(b"A" * 512 + b"B" * 512 + b"C", image.read_file("FILE.BIN"))

    def test_mirror_and_fat_header_disagreement(self):
        data = fixture()
        fat_set(data, 2, 7, copy=1)
        self.assertImageError("fat_mismatch", Fat12Image, data)
        for cluster, value in ((0, 0xff8), (1, 0xff7)):
            data = fixture()
            fat_set(data, cluster, value)
            self.assertImageError("fat_header", Fat12Image, data)

    def test_bad_reserved_free_cycle_short_and_long_chains(self):
        for value, code in ((0, "reserved_or_free_cluster"), (1, "reserved_or_free_cluster"),
                            (0xff0, "reserved_or_free_cluster"), (0xff6, "reserved_or_free_cluster"),
                            (0xff7, "bad_cluster"), (0xff8, "short_chain"),
                            (2, "cluster_cycle"), (100, "cluster_bounds")):
            data = fixture()
            fat_set(data, 2, value)
            image = Fat12Image(data)
            with self.subTest(value=value):
                self.assertImageError(code, image.read_file, "FILE.BIN")
        data = fixture()
        fat_set(data, 3, 2)
        self.assertImageError("cluster_cycle", Fat12Image(data).read_file, "FILE.BIN")
        data = fixture()
        fat_set(data, 4, 5)
        self.assertImageError("long_chain", Fat12Image(data).read_file, "FILE.BIN")
        # Terminal FAT errors are checked even after all declared bytes exist.
        data = fixture()
        fat_set(data, 4, 0xff7)
        self.assertImageError("bad_cluster", Fat12Image(data).read_file, "FILE.BIN")

    def test_empty_files_invalid_first_cluster_and_impossible_size(self):
        root = 3 * 512
        data = fixture()
        struct.pack_into("<HI", data, root + 26, 0, 0)
        self.assertEqual(b"", Fat12Image(data).read_file("FILE.BIN"))
        struct.pack_into("<HI", data, root + 26, 2, 0)
        self.assertImageError("empty_file_cluster", Fat12Image(data).read_file, "FILE.BIN")
        for cluster in (0, 1, 12, 0xff0, 0xffff):
            data = fixture()
            struct.pack_into("<H", data, root + 26, cluster)
            self.assertImageError("cluster_bounds", Fat12Image(data).read_file, "FILE.BIN")
        data = fixture()
        struct.pack_into("<I", data, root + 28, 0xffffffff)
        self.assertImageError("file_size_bounds", Fat12Image(data).read_file, "FILE.BIN")

    def test_root_duplicates_skips_deleted_long_names_and_rejects_truncation(self):
        data = fixture()
        root = 3 * 512
        data[root + 32:root + 64] = data[root:root + 32]
        self.assertImageError("duplicate_name", Fat12Image, data)
        data[root + 32] = 0xe5
        data[root + 64:root + 96] = data[root:root + 32]
        data[root + 64 + 11] = 0x0f
        self.assertEqual(1, len(Fat12Image(data).entries))
        self.assertImageError("image_length", Fat12Image, data[:root + 31])
        data = fixture()
        data[root + 11] = 0x10
        self.assertImageError("not_regular_file", Fat12Image(data).read_file, "FILE.BIN")
        data[root + 11] = 0x80
        self.assertImageError("directory_attributes", Fat12Image, data)
        data = fixture()
        data[root:root + 8] = b"../BAD  "
        self.assertImageError("directory_name", Fat12Image, data)
        with self.assertRaises(FileNotFoundError):
            Fat12Image(fixture()).read_file("MISSING.SYS")

    def test_volume_label_does_not_hide_same_named_regular_file(self):
        data = fixture()
        root = 3 * 512
        data[root + 32:root + 64] = data[root:root + 32]
        data[root + 11] = 8
        struct.pack_into("<HI", data, root + 26, 0, 0)
        image = Fat12Image(data)
        self.assertEqual(2, len(image.entries))
        self.assertEqual(1025, len(image.read_file("FILE.BIN")))

    def test_safe_clone_extract_never_changes_source_or_overwrites_destinations(self):
        source = sorted((PROJECT / "reference").glob("*1 of 3.img"))[0]
        before = source.read_bytes()
        with tempfile.TemporaryDirectory(prefix="dos-image-test-", dir=SCRATCH) as temp:
            root = Path(temp)
            output = root / "owned"
            report = clone_and_extract(source, output, ["COMMAND.COM", "IO.SYS", "MSDOS.SYS"])
            self.assertEqual(before, (output / "disk.img").read_bytes())
            self.assertEqual(report, json.loads((output / "manifest.json").read_text()))
            for item in report["extracted"]:
                data = (output / item["name"]).read_bytes()
                self.assertEqual(item["sha256"], hashlib.sha256(data).hexdigest())
            (output / "sentinel").write_bytes(b"keep")
            with self.assertRaises(FileExistsError):
                clone_and_extract(source, output)
            self.assertEqual(b"keep", (output / "sentinel").read_bytes())
            with self.assertRaises(FileNotFoundError):
                clone_and_extract(source, root / "missing-file", ["NOFILE.SYS"])
            self.assertFalse((root / "missing-file").exists())
            self.assertImageError("duplicate_extraction", clone_and_extract, source, root / "duplicate", ["IO.SYS", "io.sys"])
            (root / "link").symlink_to(output, target_is_directory=True)
            with self.assertRaises(FileExistsError):
                clone_and_extract(source, root / "link")
        self.assertEqual(before, source.read_bytes())

    def test_extraction_rejects_reserved_output_name_before_creating_directory(self):
        data = fixture()
        data[1536:1547] = b"DISK    IMG"
        with tempfile.TemporaryDirectory(prefix="dos-image-name-", dir=SCRATCH) as temp:
            root = Path(temp)
            source = root / "input.img"
            source.write_bytes(data)
            self.assertImageError("unsafe_output_name", clone_and_extract, source, root / "owned", ["DISK.IMG"])
            self.assertFalse((root / "owned").exists())
            self.assertEqual(bytes(data), source.read_bytes())

    def test_inspect_cli_is_deterministic_json_without_source_writes(self):
        source = sorted((PROJECT / "reference").glob("*1 of 3.img"))[0]
        command = [sys.executable, str(PROJECT / "build_support/dos_image.py"), "inspect", str(source)]
        first = subprocess.check_output(command)
        self.assertEqual(first, subprocess.check_output(command))
        self.assertEqual(368640, json.loads(first)["bytes"])


if __name__ == "__main__":
    unittest.main()
