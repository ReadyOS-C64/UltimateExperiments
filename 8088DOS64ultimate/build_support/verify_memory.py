"""Check linked segments and stable entry/arena symbols against the host map."""
import json
from pathlib import Path
import re
import sys


def verify(map_text, labels_text, prg=None):
    errors = []
    symbols = {name.lstrip("."): int(addr, 16) for addr, name in
               re.findall(r"^al ([0-9A-Fa-f]+) (\S+)", labels_text, re.M)}
    expected = {"__MAIN_START__": 0x0801, "__MAIN_SIZE__": 0x37FF,
                "__ZP_START__": 0x20, "__ZP_SIZE__": 0xC0,
                "__CONTROL_START__": 0xE000, "__CONTROL_SIZE__": 0x1000,
                "dos64_entry": 0x080D}
    for name, value in expected.items():
        if symbols.get(name) != value:
            errors.append(f"{name}: expected ${value:04X}, got {symbols.get(name)}")
    bounds = {"LOADADDR": (0, 1), "BASIC": (0x0801, 0x080C),
              "CODE": (0x080D, 0x3FFF), "RODATA": (0x080D, 0x3FFF),
              "TESTCODE": (0x080D, 0x3FFF), "ZEROPAGE": (0x20, 0xDF),
              "DEVICECODE": (0x5000, 0x5FFF),
              "UCIBUFFER": (0xC100, 0xC8FF),
              "RANGEBUFFER": (0xC000, 0xC0FF), "BSS": (0xE000, 0xE0FF), "PAGEMAP": (0xE100, 0xE8FF),
              "CACHEMETA": (0xE900, 0xE9FF), "DEVICESTATE": (0xEA00, 0xEEFF)}
    segments = []
    for name, first, last, size in re.findall(
            r"^(\w+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})", map_text, re.M):
        a, b, count = int(first, 16), int(last, 16), int(size, 16)
        segments.append({"name": name, "start": a, "end": b, "bytes": count})
        if name not in bounds or not (bounds[name][0] <= a <= b <= bounds[name][1]):
            errors.append(f"{name} outside owned range: ${a:04X}-${b:04X}")
        if b - a + 1 != count:
            errors.append(f"{name} has inconsistent size")
    if not segments:
        errors.append("No linker segments found")
    for index, seg in enumerate(segments):
        for other in segments[index+1:]:
            if max(seg['start'], other['start']) <= min(seg['end'], other['end']):
                errors.append(f"Overlapping segments {seg['name']} and {other['name']}")
    if 0x4000 // 0x4000 != 0x6000 // 0x4000 or 0x4800 % 0x800:
        errors.append("VIC bank/font alignment mismatch")
    # The extended runtime layout is one contiguous C64 PRG. Its intentional
    # zero padding is initialization, not additional executable allocation.
    runtime = "__DEVICE_START__" in symbols
    load = {"layout": "runtime" if runtime else "standalone", "start": 0x0801,
            "linked_file_bytes": sum(s["bytes"] for s in segments
                                     if s["name"] in ("BASIC", "CODE", "RODATA", "TESTCODE", "DEVICECODE")),
            "padding": [], "payload_checked": prg is not None}
    main_end = max((s["end"] + 1 for s in segments
                    if s["name"] in ("BASIC", "CODE", "RODATA", "TESTCODE")), default=0x0801)
    if runtime:
        area_expected = {"__MAIN_FILEOFFS__": 2, "__MAIN_LAST__": main_end,
                         "__INITVIDEO_START__": 0x4000, "__INITVIDEO_SIZE__": 0x1000,
                         "__INITVIDEO_FILEOFFS__": 0x3801, "__INITVIDEO_LAST__": 0x4000,
                         "__DEVICE_START__": 0x5000, "__DEVICE_SIZE__": 0x1000,
                         "__DEVICE_FILEOFFS__": 0x4801,
                         "__UCI_RAM_START__": 0xC100, "__UCI_RAM_SIZE__": 0x0800}
        device = [s for s in segments if s["name"] == "DEVICECODE"]
        device_end = device[0]["end"] + 1 if device else 0x5000
        area_expected["__DEVICE_LAST__"] = device_end
        if device:
            area_expected.update({"__DEVICECODE_LOAD__": device[0]["start"],
                                  "__DEVICECODE_RUN__": device[0]["start"],
                                  "__DEVICECODE_SIZE__": device[0]["bytes"]})
        for name, value in area_expected.items():
            if symbols.get(name) != value:
                errors.append(f"{name}: expected ${value:04X}, got {symbols.get(name)}")
        load["end_exclusive"] = device_end
        for name, first, last in (("unused_main", main_end, 0x4000),
                                  ("display_startup_zero", 0x4000, 0x5000)):
            if first < last:
                load["padding"].append({"name": name, "start": first,
                                        "end": last-1, "bytes": last-first,
                                        "file_offset": first-0x0801+2, "value": 0})
    else:
        load["end_exclusive"] = main_end
        if any(s["name"] in ("DEVICECODE", "UCIBUFFER") for s in segments):
            errors.append("Runtime-only segments require the contiguous runtime layout")
    load["padding_bytes"] = sum(p["bytes"] for p in load["padding"])
    load["payload_bytes"] = load["end_exclusive"] - load["start"]
    load["prg_bytes"] = load["payload_bytes"] + 2
    if prg is not None:
        if prg[:2] != b"\x01\x08":
            errors.append("PRG load address must be $0801")
        if len(prg) != load["prg_bytes"]:
            errors.append(f"PRG length: expected {load['prg_bytes']}, got {len(prg)}")
        for pad in load["padding"]:
            first = pad["file_offset"]
            data = prg[first:first+pad["bytes"]]
            if len(data) != pad["bytes"] or any(data):
                errors.append(f"PRG {pad['name']} is not complete zero initialization")
    return {"segments": segments, "load": load, "errors": errors, "passed": not errors}


if __name__ == "__main__":
    map_path = Path(sys.argv[1])
    prg_path = Path(sys.argv[3]) if len(sys.argv) > 3 else map_path.with_suffix(".prg")
    report = verify(map_path.read_text(), Path(sys.argv[2]).read_text(), prg_path.read_bytes())
    Path(sys.argv[1]).with_suffix(".memory.json").write_text(json.dumps(report, indent=2)+"\n")
    if report["errors"]:
        raise SystemExit("\n".join(report["errors"]))
    print(f"Memory verified: {sys.argv[1]} ({sum(s['bytes'] for s in report['segments'])} linked bytes, {report['load']['padding_bytes']} PRG padding bytes)")
