"""Verify VICE evidence independently of the target success mailbox."""
import hashlib
import json


def verify_capture(run, project):
    """Reject stale/partial evidence and compare captured memory independently."""
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest["plan_id"] != "dos64_reu_integrity" or manifest["status"] != "success":
        raise ValueError("Expected a successful dos64_reu_integrity run")
    if len(manifest["steps"]) != 5 or any(s["status"] != "ok" for s in manifest["steps"]):
        raise ValueError("Missing or failed VICE probe step")
    restored = (run / "stages/dump/restored_data.bin").read_bytes()
    expected = bytes((i & 255) ^ 0xa7 for i in range(4096))
    if restored != expected:
        mismatch = next((i for i, (a,b) in enumerate(zip(restored,expected)) if a != b), None)
        raise ValueError(f"Restored data mismatch: bytes={len(restored)}, first={mismatch}")
    mailbox = (run / "stages/dump/mailbox.bin").read_bytes()
    if len(mailbox) != 8 or mailbox[0] != 1 or mailbox[1] != 0xa5 or mailbox[4] != 0:
        raise ValueError(f"Invalid captured mailbox: {mailbox.hex()}")
    # Associate this result with executable bytes, even when checking an old run.
    ram = (run / "dumps/mem_end_of_run.bin").read_bytes()
    prg = (project / "build/dos64-reu-probe.prg").read_bytes()
    start = int.from_bytes(prg[:2], "little")
    if len(ram) != 65536 or len(prg) < 3 or ram[start:start+len(prg)-2] != prg[2:]:
        raise ValueError("Captured executable does not match the current probe PRG")
    return {
        "schema": 1, "run_id": manifest["run_id"], "status": "passed",
        "finished_utc": manifest["finished_utc"],
        "raw_run": str(run.relative_to(project)),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "probe_prg_sha256": hashlib.sha256(prg).hexdigest(),
        "captured_executable_identical": True,
        "restored_bytes": len(restored), "pattern": "low_byte(index) XOR A7",
        "restored_sha256": hashlib.sha256(restored).hexdigest(),
        "mailbox_hex": mailbox.hex(), "all_steps_passed": True,
        "configuration": {"reu_kib": 16384, "warp": True, "headless": True},
        "limitations": ["Functional 4 KiB roundtrip below the 4 MiB baseline",
                        "Harness uses 16 MiB REU; not physical capacity validation",
                        "No C64U firmware or 64 MHz timing evidence"],
    }

