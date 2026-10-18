#!/usr/bin/env python3
import pathlib
import re
import sys
from typing import List, Optional


def symbol(text: str, name: str) -> Optional[int]:
    patterns = (
        rf"\b{name}\b\s+([0-9A-Fa-f]{{4,8}})",
        rf"\b{name}\b\s*=\s*\$?([0-9A-Fa-f]{{4,8}})",
        rf"\b([0-9A-Fa-f]{{4,8}})\s+\.?{name}\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1), 16)
    return None


def segment_end(text: str, name: str) -> Optional[int]:
    match = re.search(
        rf"^{re.escape(name)}\s+([0-9A-Fa-f]{{6,8}})\s+"
        rf"([0-9A-Fa-f]{{6,8}})\s+[0-9A-Fa-f]{{6,8}}",
        text,
        re.MULTILINE,
    )
    return int(match.group(2), 16) if match else None


def segment_start(text: str, name: str) -> Optional[int]:
    match = re.search(
        rf"^{re.escape(name)}\s+([0-9A-Fa-f]{{6,8}})\s+"
        rf"[0-9A-Fa-f]{{6,8}}\s+[0-9A-Fa-f]{{6,8}}",
        text,
        re.MULTILINE,
    )
    return int(match.group(1), 16) if match else None


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: verify_memory_map.py MAP [LABELS]", file=sys.stderr)
        return 2
    paths = [pathlib.Path(value) for value in sys.argv[1:]]
    text = "\n".join(path.read_text(errors="replace") for path in paths)
    required = {
        "__APP_START__": 0x0801,
        "__MAIN_START__": 0x0801,
        "__MAIN_SIZE__": 0x73FF,
        "__ENGINE_START__": 0x3100,
        "__WORK_START__": 0x5BA0,
        "__OVERLAY_START__": 0x7C00,
        "__ABI_START__": 0xC000,
        "_rsql_abi_table": 0xC000,
        "_rsql_checkpoint": 0xC01B,
        "_rsql_restore": 0xC01E,
        "_rsql_checkpoint_control": 0xCFFF,
    }
    failures: List[str] = []
    for name, expected in required.items():
        actual = symbol(text, name)
        if actual is None:
            failures.append(f"missing linker symbol {name}")
        elif actual != expected:
            failures.append(f"{name}=0x{actual:04X}, expected 0x{expected:04X}")

    work_start = symbol(text, "__WORK_START__")
    resident_ends = [segment_end(text, "ENGINE")]
    engine_last = max(value for value in resident_ends if value is not None)
    if (engine_last is not None and work_start is not None and
            engine_last >= work_start):
        failures.append(f"resident engine crosses into work RAM at 0x{engine_last:04X}")
    work_ends = [
        segment_end(text, name)
        for name in ("ENGINEDATA", "INIT", "ONCE", "BSS", "APPBSS")
    ]
    bss_last = max(
        value for value in work_ends
        if value is not None and work_start is not None and value >= work_start
    )
    if bss_last is not None and bss_last >= 0x7800:
        failures.append(f"work BSS crosses into the 1KB C stack at 0x{bss_last:04X}")
    client_ends = [
        segment_end(text, name)
        for name in
        ("STARTUP", "LOWCODE", "CODE", "RODATA", "DATA", "APPBSS",
         "SHELLBSS")
    ]
    client_last = max(
        value for value in client_ends
        if value is not None and work_start is not None and value < work_start
    )
    if client_last >= 0x3100:
        failures.append(f"client crosses into resident RAM at 0x{client_last:04X}")
    for name in (
        "OVERLAY0", "OVERLAY1", "OVERLAY2", "OVERLAY3",
        "OVERLAY4", "OVERLAY5", "OVERLAY6", "OVERLAY7",
        "OVERLAY8",
    ):
        start = segment_start(text, name)
        last = segment_end(text, name)
        if start != 0x7C00:
            failures.append(f"{name} starts at {start!r}, expected 0x7C00")
        if last is None or last >= 0xC000:
            failures.append(f"{name} crosses the shared window at {last!r}")
    abi_last = segment_end(text, "ABI")
    # $CFEF is a target-harness contract: Peddle marks BASIC-ROM FLOAT calls
    # there, while $CFF0-$CFF6 are the common test controls.  Catch an ABI
    # growth into the marker at link verification instead of allowing an
    # unrelated query to corrupt the FLOAT bridge state at runtime.
    if abi_last is not None and abi_last >= 0xCFEF:
        failures.append(
            f"ABI crosses into reserved BASIC FLOAT marker at 0x{abi_last:04X}"
        )
    control_last = segment_end(text, "CONTROL")
    if control_last is not None and control_last > 0xCFF6:
        failures.append(
            f"test controls cross reserved $CFF6 boundary at 0x{control_last:04X}"
        )
    control_tail_start = segment_start(text, "CONTROLTAIL")
    control_tail_last = segment_end(text, "CONTROLTAIL")
    if (control_tail_start is not None and control_tail_start < 0xCFF7):
        failures.append(
            f"control tail starts before $CFF7 at 0x{control_tail_start:04X}"
        )
    if control_tail_last is not None and control_tail_last > 0xCFFE:
        failures.append(
            f"control tail crosses reserved $CFFE boundary at 0x{control_tail_last:04X}"
        )
    control_flag_start = segment_start(text, "CONTROLFLAG")
    control_flag_last = segment_end(text, "CONTROLFLAG")
    if control_flag_start != 0xCFFF or control_flag_last != 0xCFFF:
        failures.append(
            "checkpoint handshake flag must occupy exactly $CFFF"
        )

    if failures:
        for failure in failures:
            print(f"memory-map error: {failure}", file=sys.stderr)
        return 1
    print(
        "memory map verified: client $0801-$30FF isolated; "
        "ABI ends before reserved $CFEF; controls stay within $CFF0-$CFFF"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
