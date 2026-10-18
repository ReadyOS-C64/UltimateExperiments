#!/usr/bin/env python3
"""Build a tiny C64 PRG that copies Char ROM bank-1 glyph A to $6000."""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    # BASIC: 10 SYS2061, followed by a machine-code probe at $080D.
    basic = bytes((
        0x0B, 0x08, 0x0A, 0x00, 0x9E, 0x32, 0x30, 0x36, 0x31,
        0x00, 0x00, 0x00,
    ))
    code = bytes((
        0x78,             # SEI
        0xA5, 0x01,       # LDA $01
        0x48,             # PHA
        0xA9, 0x33,       # LDA #$33 (character ROM visible at $D000)
        0x85, 0x01,       # STA $01
        0xA2, 0x07,       # LDX #7
        0xBD, 0x08, 0xD8, # loop: LDA $D808,X (bank 1, screen code 1/A)
        0x9D, 0x00, 0x60, # STA $6000,X
        0xCA,             # DEX
        0x10, 0xF7,       # BPL loop
        0x68,             # PLA
        0x85, 0x01,       # STA $01
        0x58,             # CLI
        0x60,             # RTS
    ))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(b"\x01\x08" + basic + code)
    print(args.output)


if __name__ == "__main__":
    main()
