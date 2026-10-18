#!/usr/bin/env python3
"""Create or verify the disposable blank TAP used by ReadyFS tape tests."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


MAGIC = b"C64-TAPE-RAW"
HEADER_BYTES = 20
BLANK_PULSE = b"\x00\xa0\x86\x01"  # v1 extended pulse: 100000 cycles


def blank_tap() -> bytes:
    return (MAGIC + bytes((1, 0, 0, 0)) +
            struct.pack("<I", len(BLANK_PULSE)) + BLANK_PULSE)


def verify(path: Path, require_data: bool) -> int:
    data = path.read_bytes()
    if len(data) < HEADER_BYTES or data[:12] != MAGIC:
        raise SystemExit("ReadyFS TAP fixture: invalid header")
    payload_bytes = struct.unpack_from("<I", data, 16)[0]
    if payload_bytes != len(data) - HEADER_BYTES:
        raise SystemExit(
            "ReadyFS TAP fixture: header length does not match payload")
    if require_data and payload_bytes <= len(BLANK_PULSE):
        raise SystemExit("ReadyFS TAP fixture: recording stayed empty")
    print(f"ReadyFS TAP fixture: PASS ({payload_bytes} recorded bytes)")
    return payload_bytes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--require-data", action="store_true")
    args = parser.parse_args()
    if args.create:
        args.path.parent.mkdir(parents=True, exist_ok=True)
        args.path.write_bytes(blank_tap())
    verify(args.path, args.require_data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
