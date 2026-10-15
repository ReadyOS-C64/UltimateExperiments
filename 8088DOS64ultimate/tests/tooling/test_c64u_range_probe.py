"""Physical orchestration faults with an independent fake; target DMA uses Peddle."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "build_support"))
from c64u_range_probe import (Client, SNAPSHOT_SIZE, expected_output, restore_image,
                             run_matrix, validate_probe)
from c64u_probe import speed_option

PASS = bytes([1, 0xA5, 0, 0, 0, 0, 0, 0])
FAIL = bytes([1, 0xE1, 0, 0, 4, 0, 0, 0])


class FakeClient:
    def __init__(self, project, fault=None):
        self.prgs = {kind: (project / "build" / ("dos64-range-" + kind + ".prg")).read_bytes()
                     for kind in ("backup", "restore", "probe")}
        # Three distinct nonzero regions prevent an empty/default snapshot passing.
        self.original = bytes((i * 29 + (i // 1536) * 71) % 255 + 1 for i in range(SNAPSHOT_SIZE))
        self.reu = self.original
        self.ram = bytearray(65536)
        self.turbo = {"Turbo Control": "C64U Turbo Registers", "CPU Speed": "64", "Other": "unchanged"}
        self.machine = {"C64 and Cartridge Settings": {"RAM Expansion Unit": "Enabled", "REU Size": "16 MB"}, "errors": []}
        self.drives = {"drives": [{"a": {"image_file": "unchanged.d81", "enabled": True, "last_error": ""}}], "errors": []}
        self.fault = fault
        self.actions = []
        self.probes = 0
        self.restores = 0

    def get(self, route):
        if route == "info":
            return {"product": "owned mock", "firmware": "test"}
        if route.endswith("/Turbo%20Control"):
            return {"U64 Specific Settings": {"Turbo Control": {"values": ["Off", "Manual", "C64U Turbo Registers"]}}}
        if route.endswith("/CPU%20Speed"):
            return {"U64 Specific Settings": {"CPU Speed": {"values": [" 1", "16", " 64"]}}}
        if route == "configs/U64%20Specific%20Settings":
            return {"U64 Specific Settings": copy.deepcopy(self.turbo)}
        if route == "configs/C64%20and%20Cartridge%20Settings":
            return copy.deepcopy(self.machine)
        if route == "drives":
            return copy.deepcopy(self.drives)
        raise AssertionError(route)

    def put(self, route):
        self.actions.append(route)
        if route == "machine:reset":
            self.drives["drives"][0]["a"]["last_error"] = "reset transient"
            if self.fault == "post_reset_settings":
                self.turbo["Other"] = "changed"

    def configs(self, value):
        settings = value["U64 Specific Settings"]
        self.actions.append(("configs", copy.deepcopy(settings)))
        if settings["Turbo Control"] == "Manual":
            if settings["CPU Speed"] != " 64":
                raise AssertionError("Firmware requires the exact padded advertised speed")
            if self.fault == "configuration":
                raise RuntimeError("Synthetic speed selection failure")
        self.turbo.update(settings)

    def read(self, address, length):
        self.actions.append(("read", address, length))
        return bytes(self.ram[address:address + length])

    def run(self, prg, mailbox, executable_length=None):
        self.actions.append("run")
        # Upload copies the complete image, including restore padding/payload.
        self.ram[0x0801:0x0801 + len(prg) - 2] = prg[2:]
        if prg == self.prgs["backup"]:
            self.ram[0x6000:0x7400] = self.reu
            if self.fault == "backup":
                return FAIL
        elif prg == self.prgs["probe"]:
            self.probes += 1
            self.reu = bytes((value ^ 0x91) for value in self.reu)
            output = bytearray(expected_output())
            if self.fault == "output":
                output[-1] ^= 1
            self.ram[0x6000:0x6600] = output
            if self.fault == "transfer":
                raise RuntimeError("Synthetic failed launch response after REU mutation")
            if self.fault == "mailbox":
                return FAIL
            if self.fault == "identity":
                self.ram[0x0801] ^= 1
        else:
            self.restores += 1
            payload = prg[2 + 0x6000 - 0x0801:]
            if len(payload) != SNAPSHOT_SIZE:
                raise AssertionError("Restore upload lacks complete embedded payload")
            if self.fault == "partial_restore" or (self.fault == "retry_restore" and self.restores == 1):
                self.reu = payload[:17] + self.reu[17:]
                return FAIL
            self.reu = payload
        return PASS


class RangeHardwareWorkflow(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[2] / "agentworking" / "scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="range-workflow-", dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "project"
        (self.project / "build").mkdir(parents=True)
        for number, kind in enumerate(("backup", "restore", "probe")):
            stem = self.project / "build" / ("dos64-range-" + kind)
            stem.with_suffix(".prg").write_bytes(b"\x01\x08\x4c\x0d\x08" + bytes([number]))
            stem.with_suffix(".labels").write_text("al 00E020 .dos64_mailbox\n")
        self.out = Path(self.temp.name) / "evidence"

    def run_fault(self, fault=None):
        client = FakeClient(self.project, fault)
        report = run_matrix(client, self.project, self.out)
        return client, report

    def test_restore_embeds_exact_5120_bytes_after_padding(self):
        base = b"\x01\x08\x4c\x0d\x08"
        snapshot = bytes(range(256)) * 20
        image = restore_image(base, snapshot)
        self.assertEqual(image[:len(base)], base)
        self.assertEqual(image[2 + 0x6000 - 0x0801:], snapshot)
        self.assertEqual(len(image), 2 + 0x7400 - 0x0801)
        for invalid in (snapshot[:-1], snapshot + b"\0"):
            with self.assertRaises(ValueError):
                restore_image(base, invalid)
        with self.assertRaises(ValueError):
            restore_image(b"\x00\x08x", snapshot)
        with self.assertRaises(ValueError):
            restore_image(b"\x01\x08" + bytes(0x4000), snapshot)

    def test_complete_output_and_mailbox_both_required(self):
        validate_probe(expected_output(), PASS)
        for data in (expected_output()[:-1], expected_output()[:-1] + b"\0", bytes(1536)):
            with self.assertRaises(ValueError):
                validate_probe(data, PASS)
        for mailbox in (FAIL, PASS[:-1], b"\0" + PASS[1:]):
            with self.assertRaises(ValueError):
                validate_probe(expected_output(), mailbox)
        self.assertEqual(speed_option([" 1", "16", " 64"], 64), " 64")

    def test_success_one_manual_64_run_and_verified_full_recovery(self):
        client, report = self.run_fault()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(client.probes, 1)
        self.assertEqual(client.restores, 1)
        self.assertEqual(client.reu, client.original)
        self.assertTrue(report["reu_restored"])
        self.assertTrue(report["configuration_restored"])
        self.assertTrue(report["reset_resumed"])
        self.assertEqual(report["speeds"][0]["firmware_speed_value"], " 64")
        self.assertEqual(client.turbo["Turbo Control"], "C64U Turbo Registers")
        self.assertEqual((self.out / "reu-before.bin").read_bytes(), (self.out / "reu-after.bin").read_bytes())
        self.assertEqual(len((self.out / "reu-after.bin").read_bytes()), SNAPSHOT_SIZE)
        self.assertEqual(len((self.out / "readback-64.bin").read_bytes()), 1536)
        self.assertTrue((self.out / "probe-64-executable.bin").exists())

    def test_configuration_failure_still_restores_and_resumes(self):
        client, report = self.run_fault("configuration")
        self.assertEqual(report["status"], "failed")
        self.assertEqual(client.probes, 0)
        self.assertEqual(client.reu, client.original)
        self.assertTrue(report["reu_restored"] and report["configuration_restored"] and report["reset_resumed"])

    def test_failed_transfer_response_after_mutation_still_recovers(self):
        client, report = self.run_fault("transfer")
        self.assertEqual(report["status"], "failed")
        self.assertTrue(report["reu_recovery_required"])
        self.assertTrue(report["reu_restored"] and report["configuration_restored"])
        self.assertEqual(client.reu, client.original)

    def test_corrupted_output_mailbox_and_identity_cannot_pass(self):
        for fault in ("output", "mailbox", "identity"):
            with self.subTest(fault=fault):
                self.out = Path(self.temp.name) / fault
                client, report = self.run_fault(fault)
                self.assertEqual(report["status"], "failed")
                self.assertTrue(report["reu_restored"] and report["configuration_restored"])
                self.assertEqual(client.reu, client.original)
                self.assertEqual(report["speeds"], [])

    def test_partial_restore_never_claims_recovery_or_success(self):
        client, report = self.run_fault("partial_restore")
        self.assertEqual(report["status"], "failed")
        self.assertFalse(report["reu_restored"])
        self.assertNotEqual(client.reu, client.original)
        self.assertEqual(client.restores, 3)
        self.assertEqual(len(report["restore_errors"]), 3)
        self.assertNotIn("reu_after_sha256", report)
        self.assertTrue(report["configuration_restored"] and report["reset_resumed"])

    def test_partial_restore_full_retry_works_from_embedded_payload(self):
        client, report = self.run_fault("retry_restore")
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["reu_restored"])
        self.assertEqual(report["restore_attempts"], 2)
        self.assertEqual(client.reu, client.original)

    def test_backup_failure_never_launches_probe_or_claims_recovery(self):
        client, report = self.run_fault("backup")
        self.assertEqual(report["status"], "failed")
        self.assertEqual(client.probes, 0)
        self.assertEqual(client.restores, 0)
        self.assertFalse(report["reu_restored"] or report["reu_recovery_required"])
        self.assertTrue(report["configuration_restored"] and report["reset_resumed"])

    def test_configuration_verified_after_reset(self):
        client, report = self.run_fault("post_reset_settings")
        self.assertEqual(report["status"], "failed")
        self.assertFalse(report["configuration_restored"])
        self.assertIn("configuration_verification_error", report)
        self.assertTrue(report["reu_restored"])

    def test_existing_output_directory_is_never_overwritten(self):
        self.out.mkdir()
        (self.out / "owned-evidence").write_text("retain")
        client = FakeClient(self.project)
        with self.assertRaises(ValueError):
            run_matrix(client, self.project, self.out)
        self.assertEqual(client.actions, [])
        self.assertEqual((self.out / "owned-evidence").read_text(), "retain")
