"""Independent raw-byte acceptance for the CIA2/VIC PAL calibration probe.

PAL constants are pinned from VICE's own machine header:
https://raw.githubusercontent.com/VICE-Team/svn-mirror/ec23deb9a4ce708f6122d3a8be3356b8d52c1ff2/vice/src/c64/c64.h
SHA256 b1bc8fe494539a930b6442a1a59cc95610a8fc4523bc8b1ad99d1c7411cf1e68
Lines 35-38 specify 985248 phi2/s, 63 phi2/line, 312 lines/frame.
The probe only measures raw phi2/frame; this verifier does not infer MHz or
microseconds from CPU instructions, REST elapsed duration, or a PASS marker.
"""
import argparse
import hashlib
import json
from pathlib import Path

RECORD_ADDRESS = 0x6000
RECORD_SIZE = 40
FRAMES = 100
PAL_LINES = 312
PAL_TICKS_PER_LINE = 63
EXPECTED_TICKS = FRAMES * PAL_LINES * PAL_TICKS_PER_LINE
# Every endpoint attempt checks a stable post-read raster <16. Its CIA sample
# precedes that check, after the observed frame boundary. Assuming ordinary
# PAL monotonic raster progression, each endpoint lies in [0,1008) phi2 after
# its boundary. Subtracting two endpoints gives error strictly below 1008.
# A conservative inclusive bound of 1008 rejects frame loss (19656 ticks).
ENDPOINT_LINES = 16
TOLERANCE_TICKS = ENDPOINT_LINES * PAL_TICKS_PER_LINE


def sha(data):
    return hashlib.sha256(data).hexdigest()


def labels_from(path):
    labels = {}
    for line in Path(path).read_text().splitlines():
        bits = line.split()
        if len(bits) == 3 and bits[0] == "al":
            labels[bits[2].lstrip(".")] = int(bits[1], 16)
    return labels


def inspect_capture(ram, prg, mailbox_address):
    """Decode raw failure evidence only; this NEVER declares acceptance."""
    if len(ram) != 65536 or not 0 <= mailbox_address <= 65528:
        raise ValueError("Failure inspection needs full RAM and valid mailbox")
    r = ram[RECORD_ADDRESS:RECORD_ADDRESS + RECORD_SIZE]
    def word(offset):
        return int.from_bytes(r[offset:offset + 2], "little")
    def long(offset):
        return int.from_bytes(r[offset:offset + 4], "little")
    end = 0x801 + len(prg) - 2
    return {"kind": "diagnostic-only", "accepted": False,
            "mailbox_hex": ram[mailbox_address:mailbox_address + 8].hex(),
            "record_hex": r.hex(), "record_magic_hex": r[:4].hex(),
            "record_version": r[4], "record_status": r[5], "error": r[6],
            "profile": r[7], "frames": word(8), "target_frames": word(10),
            "maximum_raster": word(12), "start_ticks": long(14),
            "end_ticks": long(18), "delta_ticks": long(22),
            "clock_retries": word(26), "last_clock_error": r[28],
            "phase": r[29], "start_postread_raster": word(32),
            "end_postread_raster": word(34),
            "captured_executable_matches": (prg[:2] == b"\x01\x08" and
                0x801 < end <= RECORD_ADDRESS and ram[0x801:end] == prg[2:]),
            "ram_sha256": sha(ram), "record_sha256": sha(r),
            "prg_sha256": sha(prg)}


def verify_capture(ram, prg, mailbox_address):
    if len(ram) != 65536:
        raise ValueError("Capture must contain exactly 65536 RAM bytes")
    if len(prg) < 3 or prg[:2] != b"\x01\x08":
        raise ValueError("Expected 0801 PRG header")
    end = 0x801 + len(prg) - 2
    if end > 0x6000:
        raise ValueError("Executable overlaps evidence record")
    if ram[0x801:end] != prg[2:]:
        raise ValueError("Captured executable differs from uploaded PRG")
    if not 0 <= mailbox_address <= 65528:
        raise ValueError("Mailbox outside RAM")
    mailbox = ram[mailbox_address:mailbox_address + 8]
    if mailbox != b"\x01\xa5\0\0\0\0\0\0":
        raise ValueError("Mailbox is not the complete successful probe state")
    r = ram[RECORD_ADDRESS:RECORD_ADDRESS + RECORD_SIZE]
    def word(offset):
        return int.from_bytes(r[offset:offset + 2], "little")
    def long(offset):
        return int.from_bytes(r[offset:offset + 4], "little")
    if r[:4] != b"DCK1" or r[4:8] != b"\x01\xa5\0\x01":
        raise ValueError("Probe record magic/version/status/error/PAL profile rejected")
    if word(8) != FRAMES or word(10) != FRAMES:
        raise ValueError("Probe did not observe the requested 100 full frames")
    if word(12) != PAL_LINES - 1:
        raise ValueError("PAL physical raster height was not observed")
    if r[29] != 5 or r[30:32] != bytes(2) or r[36:40] != bytes(4):
        raise ValueError("Incomplete phase or nonzero reserved bytes")
    if not word(32) < ENDPOINT_LINES or not word(34) < ENDPOINT_LINES:
        raise ValueError("Endpoint was sampled outside bounded first-sixteen-line window")
    retries = word(26)
    if retries > 254 or r[28] != (4 if retries else 0):
        raise ValueError("Clock retry/status metadata inconsistent with successful reads")
    start, end_ticks, delta = long(14), long(18), long(22)
    if delta != ((end_ticks - start) & 0xffffffff):
        raise ValueError("Recorded delta differs from independent modulo subtraction")
    if abs(delta - EXPECTED_TICKS) > TOLERANCE_TICKS:
        raise ValueError("CIA ticks do not match 100 PAL frames within endpoint tolerance")
    return {"profile": "PAL-312x63", "frames": FRAMES, "start_ticks": start,
            "end_ticks": end_ticks, "delta_ticks": delta,
            "expected_ticks": EXPECTED_TICKS, "error_ticks": delta - EXPECTED_TICKS,
            "tolerance_ticks": TOLERANCE_TICKS, "clock_retries": retries,
            "start_postread_raster": word(32), "end_postread_raster": word(34),
            "record_hex": r.hex(), "record_sha256": sha(r),
            "ram_sha256": sha(ram), "prg_sha256": sha(prg),
            "mailbox_hex": mailbox.hex(),
            "limitations": ["Raw CIA phi2 ticks against VIC PAL frames, not turbo CPU cycles",
                            "No prior CIA timer/NMI execution-state restoration",
                            "No XT throughput or UCI asynchronous protocol acceptance"]}


def verify_matrix(captures, prg, mailbox_address):
    """captures is iterable of (requested manual MHz setting, full raw RAM)."""
    entries = list(captures)
    if len(entries) != 3 or {speed for speed, _ in entries} != {1, 16, 64}:
        raise ValueError("Require exactly one capture at each manual 1/16/64 setting")
    results = [{"mhz_setting": speed, **verify_capture(ram, prg, mailbox_address)}
               for speed, ram in entries]
    deltas = [r["delta_ticks"] for r in results]
    spread = max(deltas) - min(deltas)
    if spread > 2 * TOLERANCE_TICKS:
        raise ValueError("Cross-speed CIA/VIC delta spread exceeds endpoint bounds")
    return {"status": "passed", "speeds": results,
            "cross_speed_spread_ticks": spread,
            "maximum_to_minimum_delta_ratio": max(deltas) / min(deltas),
            "maximum_ratio_from_bounds": (EXPECTED_TICKS + TOLERANCE_TICKS) /
                                         (EXPECTED_TICKS - TOLERANCE_TICKS)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prg", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--ram", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify_capture(args.ram.read_bytes(), args.prg.read_bytes(),
                            labels_from(args.labels)["dos64_mailbox"])
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end="")
