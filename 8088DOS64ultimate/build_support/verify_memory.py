"""Check linked segments and stable entry/arena symbols against the host map."""
import json
from pathlib import Path
import re
import sys
import struct


def verify(map_text, labels_text, prg=None, overlay_payloads=None):
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
              "FILECODE": (0xC900, 0xCFFF), "RENDERCODE": (0xC900, 0xCFFF),
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
            # Only these two separately emitted images may share a run window.
            exclusive_overlays = {seg["name"], other["name"]} == {"FILECODE", "RENDERCODE"}
            if not exclusive_overlays and max(seg['start'], other['start']) <= min(seg['end'], other['end']):
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
    overlays = {seg["name"]: seg for seg in segments
                if seg["name"] in ("FILECODE", "RENDERCODE")}
    load["overlays"] = []
    if overlays:
        if not runtime:
            errors.append("Overlays require the runtime layout")
        if len(overlays) != 2:
            errors.append("Both exclusive FILE and TEXT overlays are required")
        device_end = load["end_exclusive"]
        if device_end > 0x6000:
            errors.append("Resident payload overlaps startup overlay sources")
        if device_end < 0x6000:
            load["padding"].append({"name": "unused_device", "start": device_end,
                                    "end": 0x5FFF, "bytes": 0x6000-device_end,
                                    "file_offset": device_end-0x0801+2, "value": 0})
        load["resident_end_exclusive"] = device_end
        load["end_exclusive"] = 0x7000
        variants = (("FILECODE", "FILE", b"FILE"), ("RENDERCODE", "RENDER", b"TEXT"))
        for index, (segment_name, area_name, tag) in enumerate(variants):
            if segment_name not in overlays:
                continue
            seg = overlays[segment_name]
            fields = {f"__{area_name}_START__": 0xC900, f"__{area_name}_SIZE__": 0x700,
                      f"__{area_name}_FILEOFFS__": 0, f"__{area_name}_LAST__": seg["end"]+1,
                      f"__{segment_name}_LOAD__": 0xC900, f"__{segment_name}_RUN__": 0xC900,
                      f"__{segment_name}_SIZE__": seg["bytes"]}
            for name, value in fields.items():
                if symbols.get(name) != value:
                    errors.append(f"{name}: expected ${value:04X}, got {symbols.get(name)}")
            if seg["start"] != 0xC900:
                errors.append(f"{segment_name} must start at the exclusive execution window")
            if not 1 <= seg["bytes"] <= 0x700:
                errors.append(f"{segment_name} payload size must fit the exclusive window")
                continue
            source = 0x6000+index*0x800
            item = {"name": segment_name, "startup_source": source,
                    "reu_slot": 0x340000+index*0x800, "slot_bytes": 0x800,
                    "payload_bytes": seg["bytes"], "run": 0xC900,
                    "ownership": "startup sources released only after native bootstrap; FILE/TEXT execution exclusive"}
            load["overlays"].append(item)
            if prg is not None:
                offset = source-0x0801+2
                block = prg[offset:offset+0x800]
                expected_header = (b"D64O"+bytes((1, index+1)) +
                                   struct.pack("<HHH", seg["bytes"], 0xC900, 0)+tag)
                if len(block) != 0x800 or block[:16] != expected_header:
                    errors.append(f"{segment_name} startup slot has wrong header or length")
                elif any(block[16+seg["bytes"]:]):
                    errors.append(f"{segment_name} startup slot tail is not zero")
                if overlay_payloads is not None:
                    payload = overlay_payloads.get(segment_name)
                    if payload is None or len(payload) != seg["bytes"] or block[16:16+seg["bytes"]] != payload:
                        errors.append(f"{segment_name} startup payload differs from its linked output")
    elif overlay_payloads:
        errors.append("Overlay payloads provided without linked overlay segments")
    load["exclusive_overlay_window_bytes"] = 0x700 if overlays else 0
    load["max_linked_overlay_bytes"] = max((s["bytes"] for s in overlays.values()), default=0)
    load["overlay_source_bytes"] = sum(s["bytes"] for s in overlays.values())
    load["startup_overlay_bytes"] = len(load["overlays"])*0x800
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
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map", type=Path)
    parser.add_argument("labels", type=Path)
    parser.add_argument("prg", type=Path, nargs="?")
    parser.add_argument("--overlay-files", type=Path)
    parser.add_argument("--overlay-render", type=Path)
    args = parser.parse_args()
    map_path = args.map
    prg_path = args.prg or map_path.with_suffix(".prg")
    payloads = None
    if args.overlay_files or args.overlay_render:
        if not (args.overlay_files and args.overlay_render):
            parser.error("Both linked overlay payload files are required")
        payloads = {"FILECODE": args.overlay_files.read_bytes(),
                    "RENDERCODE": args.overlay_render.read_bytes()}
    report = verify(map_path.read_text(), args.labels.read_text(), prg_path.read_bytes(), payloads)
    map_path.with_suffix(".memory.json").write_text(json.dumps(report, indent=2)+"\n")
    if report["errors"]:
        raise SystemExit("\n".join(report["errors"]))
    print(f"Memory verified: {sys.argv[1]} ({sum(s['bytes'] for s in report['segments'])} linked bytes, {report['load']['padding_bytes']} PRG padding bytes)")
