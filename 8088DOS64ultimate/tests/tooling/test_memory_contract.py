"""Negative gates prove a misplaced linker segment cannot silently pass."""
from pathlib import Path
import sys
import re
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/"build_support"))
from verify_memory import verify


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

    def test_changed_entry_point_fails(self):
        changed = self.labels.replace("00080D .dos64_entry", "00080E .dos64_entry")
        self.assertFalse(verify(self.map, changed)["passed"])

    def test_missing_segment_list_fails(self):
        self.assertFalse(verify("", self.labels)["passed"])


if __name__ == "__main__":
    unittest.main()
