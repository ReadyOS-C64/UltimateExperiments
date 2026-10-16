"""Terminal-owned coherent range probe; preserve every touched REU envelope.

Launch only with exclusive hardware access through the approved Terminal workflow.
PRGs are uploaded to volatile RAM; this runner never writes hardware files or UCI.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

from c64u_probe import Client as BaseClient, drive_media, sha, speed_option

ENVELOPES = ((0x07FC00, 2048), (0x34FF00, 1536), (0x35FF00, 1536))
SNAPSHOT_SIZE = sum(length for _, length in ENVELOPES)
HOST_SNAPSHOT = 0x6000


def restore_image(base, backup):
    end = 0x0801 + len(base) - 2
    if len(base) < 3 or base[:2] != b"\x01\x08":
        raise ValueError("Unexpected restore PRG header")
    if len(backup) != SNAPSHOT_SIZE or end > 0x4000:
        raise ValueError("Invalid range snapshot or restore executable size")
    # Include padding and the entire snapshot in the uploaded owned PRG. Reading
    # the payload from old C64 host RAM after run_prg would lose recovery bytes.
    return base + bytes(HOST_SNAPSHOT - end) + backup


def validate_mailbox(mailbox):
    if len(mailbox) != 8 or mailbox[0] != 1 or mailbox[1] != 0xA5 or mailbox[4] != 0:
        raise ValueError(f"Native range mailbox failed: {mailbox.hex()}")


def expected_output():
    return bytes((i & 255) ^ (i >> 8) ^ 0xA7 ^ (0x5A if i % 256 == 0 else 0)
                 for i in range(1536))


def validate_probe(data, mailbox):
    validate_mailbox(mailbox)
    if data != expected_output():
        raise ValueError("Physical range readback does not match all 1536 bytes")


class Client(BaseClient):
    def run(self, prg, mailbox_address, executable_length=None):
        self.put("machine:pause")
        self.request("POST", f"machine:writemem?address={mailbox_address + 1:X}",
                     b"\0", "application/octet-stream")
        self.request("POST", "runners:run_prg", prg, "application/octet-stream")
        self.put("machine:resume")
        deadline = time.monotonic() + 12
        # HTTP/device responses provide pacing; completion is elapsed bounded.
        while time.monotonic() < deadline:
            mailbox = self.read(mailbox_address, 8)
            if mailbox[1] in (0xA5, 0xE1):
                return mailbox
        raise TimeoutError("Native range helper did not complete within 12 seconds")


def labels(path):
    result = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[0] == "al":
            result[fields[2].lstrip(".")] = int(fields[1], 16)
    mailbox = result["dos64_mailbox"]
    if not 0 <= mailbox <= 65528:
        raise ValueError("Invalid linked mailbox address")
    return mailbox


def run_matrix(client, project, out):
    """One 64 MHz manual-setting run (name retained for harness compatibility)."""
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError("Range evidence directory must be new and empty")

    def save(name, value):
        path = out / name
        if isinstance(value, bytes):
            path.write_bytes(value)
        else:
            path.write_text(json.dumps(value, indent=2) + "\n")

    report = {"schema": 1, "status": "running", "pid": os.getpid(), "speeds": [],
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "reu_restored": False, "configuration_restored": False,
              "reset_resumed": False, "reu_recovery_required": False,
              "envelopes": [{"reu_start": address, "length": length} for address, length in ENVELOPES],
              "limitations": ["Integrity at manual 64 MHz setting; no calibrated CPU/DMA timing",
                              "C64 RAM capture is recovery evidence; prior program execution is not resumed",
                              "REU volatile registers are not an execution snapshot",
                              "No UCI or persistent hardware file writes; PRGs upload to volatile RAM"]}
    save("pid.json", {"pid": os.getpid()})

    def progress(stage):
        report["stage"] = stage
        save("progress.json", report)

    def run_verified(prg, mailbox, name, executable_length=None):
        result = client.run(prg, mailbox, executable_length)
        save(name + "-mailbox.bin", result)
        validate_mailbox(result)
        payload = prg[2:] if executable_length is None else prg[2:2 + executable_length]
        capture = client.read(0x0801, len(payload))
        save(name + "-executable.bin", capture)
        if capture != payload:
            raise ValueError(f"{name}: captured executable differs from uploaded PRG")
        return result

    backup = None
    turbo = machine = drives = None
    ran_program = False
    try:
        progress("validate owned artifacts")
        artifacts = {}
        mailboxes = {}
        for kind in ("backup", "restore", "probe"):
            stem = "dos64-range-" + kind
            prg = (project / "build" / (stem + ".prg")).read_bytes()
            if len(prg) < 3 or prg[:2] != b"\x01\x08" or 0x0801 + len(prg) - 2 > 0x4000:
                raise ValueError(f"Invalid {kind} PRG header/range")
            artifacts[kind] = prg
            mailboxes[kind] = labels(project / "build" / (stem + ".labels"))
            save(stem + ".prg", prg)
            save(stem + ".labels", (project / "build" / (stem + ".labels")).read_bytes())
        restore_image(artifacts["restore"], bytes(SNAPSHOT_SIZE))
        report["artifacts"] = {key + "_prg_sha256": sha(value) for key, value in artifacts.items()}
        report["mailbox_addresses"] = mailboxes
        report["source_sha256"] = {}
        for name in ("src/boot.s", "src/cpu_state.s", "src/reu.s", "src/memory.s",
                     "src/address.s", "src/range.s", "src/range_probe.s", "src/range_snapshot.s",
                     "include/abi.inc", "include/reu.inc", "include/memory.inc", "include/range.inc",
                     "cfg/dos64.cfg", "build_support/c64u_probe.py", "build_support/c64u_range_probe.py"):
            path = project / name
            if path.is_file():
                report["source_sha256"][name] = sha(path.read_bytes())
        manifest = project / "build/manifest.json"
        if manifest.is_file():
            save("build-manifest.json", manifest.read_bytes())
            report["build_manifest_sha256"] = sha(manifest.read_bytes())
        progress("inventory")
        report["device"] = client.get("info")
        save("info.json", report["device"])
        turbo = client.get("configs/U64%20Specific%20Settings")["U64 Specific Settings"]
        machine = client.get("configs/C64%20and%20Cartridge%20Settings")
        drives = client.get("drives")
        save("turbo-before.json", turbo)
        save("machine-before.json", machine)
        save("drives-before.json", drives)
        controls = client.get("configs/U64%20Specific%20Settings/Turbo%20Control")["U64 Specific Settings"]["Turbo Control"]["values"]
        speeds = client.get("configs/U64%20Specific%20Settings/CPU%20Speed")["U64 Specific Settings"]["CPU Speed"]["values"]
        report["firmware_options"] = {"turbo": controls, "speed": speeds}
        if "Manual" not in controls:
            raise ValueError("Firmware does not offer Manual turbo control")
        option = speed_option(speeds, 64)
        settings = machine["C64 and Cartridge Settings"]
        size = settings["REU Size"].split()
        if settings["RAM Expansion Unit"] != "Enabled" or len(size) != 2 or size[1] != "MB" or int(size[0]) < 4:
            raise ValueError("Already enabled REU of at least 4 MiB is required")
        progress("RAM recovery capture")
        client.put("machine:pause")
        save("ram-before.bin", client.read(0, 65536))
        progress("backup all REU envelopes")
        ran_program = True
        run_verified(artifacts["backup"], mailboxes["backup"], "backup-before")
        backup = client.read(HOST_SNAPSHOT, SNAPSHOT_SIZE)
        if len(backup) != SNAPSHOT_SIZE:
            backup = None
            raise ValueError("Incomplete REU backup; probe is prohibited")
        save("reu-before.bin", backup)
        report["reu_before_sha256"] = sha(backup)
        progress("range probe manual 64 MHz")
        client.configs({"U64 Specific Settings": {"Turbo Control": "Manual", "CPU Speed": option}})
        active = client.get("configs/U64%20Specific%20Settings")["U64 Specific Settings"]
        if active["Turbo Control"] != "Manual" or active["CPU Speed"] != option:
            raise ValueError("Requested exact manual turbo setting was not applied")
        report["reu_recovery_required"] = True  # Launch may partly execute before a failed HTTP response.
        result = run_verified(artifacts["probe"], mailboxes["probe"], "probe-64")
        data = client.read(HOST_SNAPSHOT, 1536)
        save("readback-64.bin", data)
        validate_probe(data, result)
        save("ram-64.bin", client.read(0, 65536))
        report["speeds"].append({"mhz_setting": 64, "firmware_speed_value": option,
                                 "turbo_control": "Manual", "result": "pass",
                                 "readback_sha256": sha(data), "mailbox_hex": result.hex()})
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = repr(exc)
    finally:
        if backup is not None:
            progress("restore and freshly verify all REU envelopes")
            restoration = restore_image(artifacts["restore"], backup)
            save("restore-owned.prg", restoration)
            for attempt in range(1, 4):
                try:
                    run_verified(restoration, mailboxes["restore"], f"restore-{attempt}", len(artifacts["restore"]) - 2)
                    run_verified(artifacts["backup"], mailboxes["backup"], f"backup-after-{attempt}")
                    restored = client.read(HOST_SNAPSHOT, SNAPSHOT_SIZE)
                    save(f"reu-after-{attempt}.bin", restored)
                    if restored != backup:
                        raise ValueError("Restored REU differs from saved complete 5120-byte snapshot")
                    report["reu_restored"] = True
                    report["restore_attempts"] = attempt
                    report["reu_after_sha256"] = sha(restored)
                    save("reu-after.bin", restored)
                    break
                except Exception as exc:
                    report.setdefault("restore_errors", []).append(repr(exc))
            if not report["reu_restored"]:
                report["status"] = "failed"
        if turbo is not None:
            progress("restore prior settings")
            try:
                client.configs({"U64 Specific Settings": {"Turbo Control": turbo["Turbo Control"], "CPU Speed": turbo["CPU Speed"]}})
            except Exception as exc:
                report["status"] = "failed"
                report["configuration_restore_error"] = repr(exc)
        if ran_program:
            try:
                client.put("machine:reset")
            except Exception as exc:
                report["status"] = "failed"
                report["reset_error"] = repr(exc)
        if turbo is not None:
            try:
                client.put("machine:resume")
                report["reset_resumed"] = ran_program and "reset_error" not in report
            except Exception as exc:
                report["status"] = "failed"
                report["resume_error"] = repr(exc)
        if turbo is not None and machine is not None and drives is not None:
            try:
                after = client.get("configs/U64%20Specific%20Settings")["U64 Specific Settings"]
                machine_after = client.get("configs/C64%20and%20Cartridge%20Settings")
                drives_after = client.get("drives")
                save("turbo-after.json", after)
                save("machine-after.json", machine_after)
                save("drives-after.json", drives_after)
                if after != turbo or machine_after != machine or drive_media(drives_after) != drive_media(drives):
                    raise ValueError("Prior turbo/machine/media configuration differs after reset/resume")
                if "configuration_restore_error" not in report:
                    report["configuration_restored"] = True
            except Exception as exc:
                report["status"] = "failed"
                report["configuration_verification_error"] = repr(exc)
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        progress("finished")
        save("result.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    report = run_matrix(Client(args.host), project, args.output.resolve())
    print(json.dumps({key: report[key] for key in ("status", "speeds", "reu_restored", "configuration_restored", "reset_resumed")}))
    raise SystemExit(report["status"] != "passed")
