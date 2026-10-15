"""Cold image importer has an exact temporary phase, never resident capacity."""
from pathlib import Path
import re
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "build_support"))
from verify_memory import verify
from overlay_package import append_import, append_input


class ImageImportContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map = Path("build/dos64-tests.map").read_text()
        cls.labels = Path("build/dos64-tests.labels").read_text()
        cls.prg = Path("build/dos64-tests.prg").read_bytes()
        cls.cold = Path("build/dos64-tests-resident.prg.import.bin").read_bytes()
        cls.payloads = {"FILECODE": Path("build/dos64-tests-resident.prg.files.bin").read_bytes(),
                        "RENDERCODE": Path("build/dos64-tests-resident.prg.render.bin").read_bytes(),
                        "INPUTCODE": Path("build/dos64-tests-resident.prg.input.bin").read_bytes()}

    def check(self, **changes):
        args = dict(map_text=self.map, labels_text=self.labels, prg=self.prg,
                    overlay_payloads=self.payloads, import_payload=self.cold)
        args.update(changes)
        return verify(**args)

    def symbol_change(self, name, value):
        changed = re.sub(r"^(al )([0-9A-F]+)( \."+name+r")$",
                         lambda m: m[1]+f"{value:06X}"+m[3], self.labels, flags=re.M)
        self.assertNotEqual(changed, self.labels)
        return changed

    def move(self, address):
        return re.sub(r"^(IMPORTCODE\s+)([0-9A-F]{6})(\s+)([0-9A-F]{6})",
                      lambda m: f"{m[1]}{address:06X}{m[3]}{address+len(self.cold)-1:06X}",
                      self.map, flags=re.M)

    def test_actual_cold_bytes_controlled_tail_and_distinct_lifetime(self):
        r = self.check()
        self.assertTrue(r["passed"], r["errors"])
        cold = r["load"]["cold_import"]
        self.assertEqual(cold["start"], 0x7000)
        self.assertEqual(cold["linked_bytes"], 1821)
        self.assertEqual(cold["state_bytes"], 26)
        self.assertTrue(cold["payload_checked"])
        self.assertEqual(r["load"]["prg_bytes"], 32769)
        self.assertEqual(self.prg[0x7000-0x801+2:0x7000-0x801+2+len(self.cold)], self.cold)
        self.assertEqual(self.prg[0x7000-0x801+2+len(self.cold):0x8000-0x801+2], bytes(4096-len(self.cold)))
        partial=append_import(self.prg[:0x7000-0x801+2],self.cold,self.labels)
        self.assertEqual(append_input(partial,self.payloads["INPUTCODE"],self.labels)[0],self.prg)

    def test_every_linked_cold_byte_difference_is_detected(self):
        for index in range(len(self.cold)):
            data = bytearray(self.prg)
            data[0x7000-0x801+2+index] ^= 1
            self.assertFalse(self.check(prg=data)["passed"], index)

    def test_truncated_extended_or_nonzero_cold_tail_rejected(self):
        for data in (self.prg[:-1], self.prg+b"\0", self.prg[:0x7000-0x801+2], self.prg[:-1]+b"\x01"):
            self.assertFalse(self.check(prg=data)["passed"])

    def test_short_long_or_changed_linked_output_rejected(self):
        for cold in (self.cold[:-1], self.cold+b"\0", bytes(len(self.cold))):
            self.assertFalse(self.check(import_payload=cold)["passed"])

    def test_phase_overlap_bounds_and_shifted_origin_rejected(self):
        for address in (0x3C00, 0x5000, 0x6000, 0x6800, 0x7001, 0x7FFF, 0x8000, 0xC900):
            self.assertFalse(self.check(map_text=self.move(address))["passed"], hex(address))

    def test_cold_state_cannot_escape_into_resident_or_other_phase(self):
        for address in (0x6000, 0x6FFF, 0x73A3, 0x8000, 0xEA00):
            self.assertFalse(self.check(labels_text=self.symbol_change("dos64_import_state_start", address))["passed"])

    def test_linker_output_identity_fields_are_required(self):
        for name in ("__IMPORT_START__", "__IMPORT_SIZE__", "__IMPORT_FILEOFFS__", "__IMPORT_LAST__",
                     "__IMPORTCODE_LOAD__", "__IMPORTCODE_RUN__", "__IMPORTCODE_SIZE__",
                     "dos64_import_code_start", "dos64_import_code_end", "dos64_import_state_end"):
            self.assertFalse(self.check(labels_text=self.symbol_change(name, 1))["passed"], name)

    def test_missing_import_or_overlay_phase_rejected(self):
        for name in ("IMPORTCODE", "FILECODE", "RENDERCODE"):
            changed = re.sub(r"^"+name+r"\s.*\n", "", self.map, flags=re.M)
            self.assertFalse(self.check(map_text=changed)["passed"])

    def test_packer_rejects_wrong_extent_length_and_linker_identity(self):
        base = self.prg[:0x7000-0x801+2]
        for prg, cold, labels in ((base[:-1], self.cold, self.labels), (base+b"\0", self.cold, self.labels),
                                  (base, b"", self.labels), (base, bytes(4097), self.labels),
                                  (base, self.cold[:-1], self.labels),
                                  (base, self.cold, self.symbol_change("__IMPORTCODE_RUN__", 0x6800))):
            with self.assertRaises(ValueError):
                append_import(prg, cold, labels)

    def test_runtime_native_boot_keeps_import_optional(self):
        # Loading extended bytes must not itself open any filesystem file.
        source = Path("src/boot.s").read_text()
        self.assertNotIn("jsr dos64_import_", source)


if __name__ == "__main__":
    unittest.main()
