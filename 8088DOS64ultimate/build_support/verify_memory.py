"""Check linked segments and stable entry/arena symbols against the host map."""
import json
from pathlib import Path
import re
import sys


def verify(map_text, labels_text):
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
              "RANGEBUFFER": (0xC000, 0xC0FF), "BSS": (0xE000, 0xE0FF), "PAGEMAP": (0xE100, 0xE8FF),
              "CACHEMETA": (0xE900, 0xEFFF)}
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
    return {"segments": segments, "errors": errors, "passed": not errors}


if __name__ == "__main__":
    report = verify(Path(sys.argv[1]).read_text(), Path(sys.argv[2]).read_text())
    Path(sys.argv[1]).with_suffix(".memory.json").write_text(json.dumps(report, indent=2)+"\n")
    if report["errors"]:
        raise SystemExit("\n".join(report["errors"]))
    print(f"Memory verified: {sys.argv[1]} ({sum(s['bytes'] for s in report['segments'])} linked bytes)")
