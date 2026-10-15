"""Ensure acceptance fails on corrupted/stale/partial VICE evidence."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/"build_support"))
from vice_capture import verify_capture


class ViceCapture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.run = self.project/"logs/owned-run"
        (self.run/"stages/dump").mkdir(parents=True)
        (self.run/"dumps").mkdir()
        (self.project/"build").mkdir()
        self.manifest = {"plan_id": "dos64_reu_integrity", "status": "success",
                         "steps": [{"status":"ok"} for _ in range(5)],
                         "run_id": "owned-run", "finished_utc": "fixture"}
        self.write_manifest()
        # Construct the inverse permutation rather than use the verifier's loop.
        page = bytearray(256)
        for value in range(256):
            page[value ^ 0xa7] = value
        (self.run/"stages/dump/restored_data.bin").write_bytes(page*16)
        (self.run/"stages/dump/mailbox.bin").write_bytes(bytes([1,0xa5,0,0,0,0,0,0]))
        (self.project/"build/dos64-reu-probe.prg").write_bytes(bytes([1,8,0x4c,1,8]))
        ram=bytearray(65536);ram[0x801:0x804]=bytes([0x4c,1,8])
        (self.run/"dumps/mem_end_of_run.bin").write_bytes(ram)

    def write_manifest(self):
        (self.run/"manifest.json").write_text(json.dumps(self.manifest),encoding="utf-8-sig")

    def test_valid_capture(self):
        self.assertEqual(verify_capture(self.run,self.project)["restored_bytes"],4096)

    def test_pass_mailbox_does_not_hide_data_corruption(self):
        path=self.run/"stages/dump/restored_data.bin"
        data=bytearray(path.read_bytes());data[777]^=1;path.write_bytes(data)
        with self.assertRaisesRegex(ValueError,"first=777"):
            verify_capture(self.run,self.project)

    def test_failed_mailbox_rejected(self):
        (self.run/"stages/dump/mailbox.bin").write_bytes(bytes([1,0xe1,0,0,3,0,0,0]))
        with self.assertRaisesRegex(ValueError,"mailbox"):
            verify_capture(self.run,self.project)

    def test_stale_executable_rejected(self):
        (self.project/"build/dos64-reu-probe.prg").write_bytes(bytes([1,8,0xea]))
        with self.assertRaisesRegex(ValueError,"executable"):
            verify_capture(self.run,self.project)

    def test_partial_run_rejected(self):
        self.manifest["steps"].pop();self.write_manifest()
        with self.assertRaisesRegex(ValueError,"step"):
            verify_capture(self.run,self.project)

    def test_cache_capture_uses_its_own_length_pattern_and_executable(self):
        self.manifest["plan_id"]="dos64_cache_integrity";self.write_manifest()
        prg=self.project/"build/dos64-reu-probe.prg"
        (self.project/"build/dos64-cache-probe.prg").write_bytes(prg.read_bytes())
        data=bytearray(1536)
        for page in range(6):
            for value in range(256):
                data[page*256+(value ^ page ^ 0xa7)]=value
        (self.run/"stages/dump/restored_data.bin").write_bytes(data)
        self.assertEqual(verify_capture(self.run,self.project,"cache")["restored_bytes"],1536)
        with self.assertRaisesRegex(ValueError,"successful"):
            verify_capture(self.run,self.project,"reu")
