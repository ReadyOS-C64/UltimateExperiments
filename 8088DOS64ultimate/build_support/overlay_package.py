#!/usr/bin/env python3
"""Package linked, fixed-address overlays into a temporary bitmap startup blob.

The resident PRG must end by 6000; padding plus the two complete 2048-byte slots
are loaded at 6000–6FFF. Native bootstrap must commit these to immutable REU
before VIC bitmap use. Payloads run at C900 and are mutually exclusive. This
packer does not relocate code, change state allocation, or replace native DMA.
"""
import argparse
import hashlib
import json
import pathlib
import struct

WINDOW = 0xC900
WINDOW_SIZE = 0x700
SLOT_SIZE = 0x800
SOURCE = 0x6000
ASSETS = 0x340000
HEADER = 16


def slot(payload, identity):
    if identity not in (1, 2):
        raise ValueError("unknown overlay identity")
    if not 1 <= len(payload) <= WINDOW_SIZE:
        raise ValueError("overlay payload must fit C900–CFFF and be nonempty")
    tag = b"FILE" if identity == 1 else b"TEXT"
    header = b"D64O" + bytes((1, identity)) + struct.pack("<HHH", len(payload), WINDOW, 0) + tag
    return header + payload + bytes(SLOT_SIZE - HEADER - len(payload))


def package(resident, files, render):
    if len(resident) < 3:
        raise ValueError("invalid resident PRG")
    start = struct.unpack("<H", resident[:2])[0]
    end = start + len(resident) - 2
    if start != 0x801 or end > SOURCE:
        raise ValueError("resident PRG must load at 0801 and end before startup blob")
    assets = slot(files, 1) + slot(render, 2)
    prg = resident + bytes(SOURCE - end) + assets
    return prg, assets


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--resident-prg", type=pathlib.Path, required=True)
    p.add_argument("--files", type=pathlib.Path, required=True)
    p.add_argument("--render", type=pathlib.Path, required=True)
    p.add_argument("--output-prg", type=pathlib.Path, required=True)
    p.add_argument("--output-assets", type=pathlib.Path, required=True)
    p.add_argument("--manifest", type=pathlib.Path)
    a = p.parse_args()
    inputs = (a.resident_prg, a.files, a.render)
    outputs = (a.output_prg, a.output_assets) + ((a.manifest,) if a.manifest else ())
    resolved = [path.resolve() for path in inputs + outputs]
    if len(set(resolved)) != len(resolved):
        p.error("input/output paths must be distinct")
    raw = [path.read_bytes() for path in inputs]
    try:
        prg, assets = package(*raw)
    except ValueError as e:
        p.error(str(e))
    # Compute and validate all results before opening outputs. Build outputs are
    # disposable; no existing source/reference file is rewritten.
    a.output_prg.write_bytes(prg)
    a.output_assets.write_bytes(assets)
    if a.manifest:
        record = {"version": 1,
                  "inputs": {str(path): hashlib.sha256(data).hexdigest()
                             for path, data in zip(inputs, raw)},
                  "window": WINDOW, "window_size": WINDOW_SIZE,
                  "startup_source": SOURCE, "reu_assets": ASSETS,
                  "slot_size": SLOT_SIZE, "payload_lengths": [len(x) for x in raw[1:]],
                  "sha256": {"files": hashlib.sha256(raw[1]).hexdigest(),
                             "render": hashlib.sha256(raw[2]).hexdigest(),
                             "startup_assets": hashlib.sha256(assets).hexdigest(),
                             "packaged_prg": hashlib.sha256(prg).hexdigest()},
                  "contract": "startup bytes released only after native bootstrap; immutable REU payload trust, no native CRC"}
        a.manifest.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
