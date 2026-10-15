"""Negative gates prove a misplaced linker segment cannot silently pass."""
from pathlib import Path
import sys
import re
import unittest
import subprocess
import tempfile
import os
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/"build_support"))
from verify_memory import verify


def move_segment(map_text, name, first):
    return re.sub(r"^("+name+r"\s+)([0-9A-F]{6})(\s+)([0-9A-F]{6})",
                  lambda m: f"{m[1]}{first:06X}{m[3]}{first+int(m[4],16)-int(m[2],16):06X}",
                  map_text, flags=re.M)


class MemoryContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map = Path("build/dos64.map").read_text()
        cls.labels = Path("build/dos64.labels").read_text()

    def test_linked_artifact_fits(self):
        self.assertTrue(verify(self.map, self.labels)["passed"])

    def test_code_moved_into_guest_cache_fails(self):
        changed = re.sub(r"^(CODE\s+)([0-9A-F]{6})(\s+)([0-9A-F]{6})",
                         lambda m: f"{m[1]}{int(m[2],16)+0x7800:06X}{m[3]}{int(m[4],16)+0x7800:06X}",
                         self.map, flags=re.M)
        self.assertNotEqual(changed, self.map)
        self.assertFalse(verify(changed, self.labels)["passed"])

    def test_range_staging_cannot_move_into_VIC_bitmap(self):
        changed = re.sub(r"^(RANGEBUFFER\s+)([0-9A-F]{6})(\s+)([0-9A-F]{6})",
                         lambda m: f"{m[1]}006000{m[3]}0060FF",
                         self.map, flags=re.M)
        self.assertNotEqual(changed, self.map)
        self.assertFalse(verify(changed, self.labels)["passed"])

    def test_changed_entry_point_fails(self):
        changed = self.labels.replace("00080D .dos64_entry", "00080E .dos64_entry")
        self.assertFalse(verify(self.map, changed)["passed"])

    def test_device_state_cannot_take_vector_reservation(self):
        changed = re.sub(r"^(DEVICESTATE\s+)([0-9A-F]{6})(\s+)([0-9A-F]{6})",
                         lambda m: f"{m[1]}00EF00{m[3]}00EF{int(m[4],16)-int(m[2],16):02X}",
                         self.map, flags=re.M)
        self.assertNotEqual(changed, self.map)
        self.assertFalse(verify(changed, self.labels)["passed"])

    def test_frame_metadata_cannot_expand_into_devices(self):
        changed = re.sub(r"^(CACHEMETA\s+)([0-9A-F]{6})(\s+)([0-9A-F]{6})",
                         lambda m: f"{m[1]}00EA00{m[3]}00EABF", self.map, flags=re.M)
        self.assertNotEqual(changed, self.map)
        self.assertFalse(verify(changed, self.labels)["passed"])

    def test_missing_segment_list_fails(self):
        self.assertFalse(verify("", self.labels)["passed"])


class ContiguousRuntimeContract(unittest.TestCase):
    """An independent tiny assembled PRG proves loader placement and fill bytes."""
    @classmethod
    def setUpClass(cls):
        scratch = Path("agentworking/scratch")
        scratch.mkdir(parents=True, exist_ok=True)
        cls.scratch = tempfile.TemporaryDirectory(prefix="layout-contract-", dir=scratch)
        cls.addClassCleanup(cls.scratch.cleanup)
        base = Path(cls.scratch.name)
        source = base / "fixture.s"
        source.write_text('.export dos64_entry\n.segment "LOADADDR"\n.word $0801\n'
                          '.segment "BASIC"\n.res 12, $11\n.segment "CODE"\n'
                          'dos64_entry: .byte $60, $AB\n.segment "DEVICECODE"\n'
                          '.byte $A9, $42, $60\n.segment "UCIBUFFER"\n.res $800\n')
        obj = base / "fixture.o"
        subprocess.run([os.environ.get("DOS64_CA65", "ca65"), "-o", str(obj), str(source)], check=True)
        cls.base = base / "fixture"
        subprocess.run([os.environ.get("DOS64_LD65", "ld65"), "-C", "cfg/dos64-runtime.cfg",
                        "-o", str(cls.base.with_suffix(".prg")), "-m", str(cls.base.with_suffix(".map")),
                        "-Ln", str(cls.base.with_suffix(".labels")), str(obj)], check=True)
        cls.map = cls.base.with_suffix(".map").read_text()
        cls.labels = cls.base.with_suffix(".labels").read_text()
        cls.prg = cls.base.with_suffix(".prg").read_bytes()

    def test_real_loader_bytes_and_padding_accounting(self):
        report = verify(self.map, self.labels, self.prg)
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(self.prg[:2], b"\x01\x08")
        self.assertEqual(self.prg[14:16], b"\x60\xab")  # host $080D
        self.assertEqual(self.prg[0x4801:], b"\xa9\x42\x60")  # host $5000
        self.assertEqual(report["load"]["linked_file_bytes"], 17)
        self.assertEqual(report["load"]["padding_bytes"], 18417)
        self.assertEqual(report["load"]["prg_bytes"], 18436)
        self.assertEqual(sum(s["bytes"] for s in report["segments"]), 2067)
        self.assertEqual(report["load"]["padding"][1]["bytes"], 4096)

    def test_each_zero_initialization_area_rejects_nonzero_data(self):
        for offset in (16, 0x3800, 0x3801, 0x4800):
            with self.subTest(offset=offset):
                changed = bytearray(self.prg)
                changed[offset] = 1
                self.assertFalse(verify(self.map, self.labels, changed)["passed"])

    def test_header_and_truncated_or_extended_prgs_fail(self):
        for changed in (b"\x00\x50"+self.prg[2:], self.prg[:-1], self.prg+b"\x00"):
            self.assertFalse(verify(self.map, self.labels, changed)["passed"])

    def test_main_code_cannot_use_device_window(self):
        self.assertFalse(verify(move_segment(self.map, "CODE", 0x5000), self.labels, self.prg)["passed"])

    def test_device_code_cannot_use_bitmap_or_display_initialization(self):
        for address in (0x4000, 0x6000):
            self.assertFalse(verify(move_segment(self.map, "DEVICECODE", address), self.labels, self.prg)["passed"])

    def test_device_window_end_is_enforced(self):
        self.assertFalse(verify(move_segment(self.map, "DEVICECODE", 0x5FFF), self.labels, self.prg)["passed"])

    def test_wrong_linker_file_offsets_and_load_address_fail(self):
        for symbol, old, new in (("__DEVICE_FILEOFFS__", "004801", "003801"),
                                 ("__INITVIDEO_FILEOFFS__", "003801", "000002"),
                                 ("__DEVICECODE_LOAD__", "005000", "005001")):
            changed = self.labels.replace(f"{old} .{symbol}", f"{new} .{symbol}")
            self.assertNotEqual(changed, self.labels)
            self.assertFalse(verify(self.map, changed, self.prg)["passed"])

    def test_uci_buffer_cannot_take_bounce_or_extra_resident_ram(self):
        for address in (0xC000, 0xC900):
            self.assertFalse(verify(move_segment(self.map, "UCIBUFFER", address), self.labels, self.prg)["passed"])

    def test_runtime_only_segments_require_runtime_linker_markers(self):
        changed = re.sub(r"^al [0-9A-F]+ \.__DEVICE_START__\n", "", self.labels, flags=re.M)
        self.assertNotEqual(changed, self.labels)
        self.assertFalse(verify(self.map, changed, self.prg)["passed"])

    def test_standalone_cfg_remains_short_and_unpadded(self):
        source = Path(self.scratch.name) / "standalone.s"
        source.write_text('.export dos64_entry\n.segment "LOADADDR"\n.word $0801\n'
                          '.segment "BASIC"\n.res 12, $11\n.segment "CODE"\n'
                          'dos64_entry: .byte $60, $AB\n')
        obj = source.with_suffix(".o")
        subprocess.run([os.environ.get("DOS64_CA65", "ca65"), "-o", str(obj), str(source)], check=True)
        subprocess.run([os.environ.get("DOS64_LD65", "ld65"), "-C", "cfg/dos64.cfg",
                        "-o", str(source.with_suffix(".prg")), "-m", str(source.with_suffix(".map")),
                        "-Ln", str(source.with_suffix(".labels")), str(obj)], check=True)
        prg = source.with_suffix(".prg").read_bytes()
        report = verify(source.with_suffix(".map").read_text(), source.with_suffix(".labels").read_text(), prg)
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(len(prg), 16)
        self.assertEqual(report["load"]["padding_bytes"], 0)
        self.assertEqual(report["load"]["layout"], "standalone")


if __name__ == "__main__":
    unittest.main()
