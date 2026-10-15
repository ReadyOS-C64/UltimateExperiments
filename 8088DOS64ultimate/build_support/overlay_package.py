#!/usr/bin/env python3
"""Package linked, fixed-address overlays into a temporary bitmap startup blob.

The resident PRG must end by 6000; padding plus the two complete 2048-byte slots
are loaded at 6000–6FFF. Native bootstrap must commit these to immutable REU
before VIC bitmap use. Payloads run at C900 and are mutually exclusive. This
packer does not relocate code, change state allocation, or replace native DMA.
An optional independently linked cold importer occupies7000–7FFF only during
startup; exact linked bytes precede a controlled zero tail. Bitmap ownership
discards both its code and state.
"""
import argparse
import hashlib
import json
import pathlib
import struct
import re

WINDOW = 0xC900
WINDOW_SIZE = 0x700
SLOT_SIZE = 0x800
SOURCE = 0x6000
ASSETS = 0x340000
HEADER = 16
IMPORT_START = 0x7000
IMPORT_SIZE = 0x1000


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


def append_import(prg, cold, labels):
    """Append exact linked cold bytes, then explicit zero tail through 7FFF."""
    if prg[:2] != b"\x01\x08" or len(prg) != IMPORT_START - 0x801 + 2:
        raise ValueError("cold importer requires complete 0801..6FFF overlay phase")
    symbols = {name.lstrip("."): int(addr, 16) for addr, name in
               re.findall(r"^al ([0-9A-Fa-f]+) (\S+)", labels, re.M)}
    expected = {"__IMPORT_START__": IMPORT_START, "__IMPORT_SIZE__": IMPORT_SIZE,
                "__IMPORT_FILEOFFS__": 0, "__IMPORT_LAST__": IMPORT_START + len(cold),
                "__IMPORTCODE_LOAD__": IMPORT_START, "__IMPORTCODE_RUN__": IMPORT_START,
                "__IMPORTCODE_SIZE__": len(cold),
                "dos64_import_code_start": IMPORT_START,
                "dos64_import_code_end": IMPORT_START + len(cold),
                "dos64_import_state_end": IMPORT_START + len(cold)}
    if not 1 <= len(cold) <= IMPORT_SIZE:
        raise ValueError("cold importer must be nonempty and fit 7000..7FFF")
    if any(symbols.get(k) != v for k, v in expected.items()):
        raise ValueError("cold importer differs from linked address/length/phase contract")
    if not IMPORT_START <= symbols.get("dos64_import_state_start", -1) < IMPORT_START + len(cold):
        raise ValueError("cold state must remain inside the discarded import image")
    return prg + cold + bytes(IMPORT_SIZE - len(cold))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--resident-prg", type=pathlib.Path, required=True)
    p.add_argument("--files", type=pathlib.Path, required=True)
    p.add_argument("--render", type=pathlib.Path, required=True)
    p.add_argument("--import-code", type=pathlib.Path)
    p.add_argument("--labels", type=pathlib.Path)
    p.add_argument("--output-prg", type=pathlib.Path, required=True)
    p.add_argument("--output-assets", type=pathlib.Path, required=True)
    p.add_argument("--manifest", type=pathlib.Path)
    a = p.parse_args()
    if bool(a.import_code) != bool(a.labels):
        p.error("cold importer requires both linked code and labels")
    inputs = (a.resident_prg, a.files, a.render) + ((a.import_code, a.labels) if a.import_code else ())
    outputs = (a.output_prg, a.output_assets) + ((a.manifest,) if a.manifest else ())
    resolved = [path.resolve() for path in inputs + outputs]
    if len(set(resolved)) != len(resolved):
        p.error("input/output paths must be distinct")
    raw = [path.read_bytes() for path in inputs]
    try:
        prg, assets = package(*raw[:3])
        if a.import_code:
            prg = append_import(prg, raw[3], raw[4].decode())
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
                  "slot_size": SLOT_SIZE, "payload_lengths": [len(x) for x in raw[1:3]],
                  "cold_import": ({"start": IMPORT_START, "window_bytes": IMPORT_SIZE,
                                   "linked_bytes": len(raw[3]), "tail_zero_bytes": IMPORT_SIZE-len(raw[3]),
                                   "sha256": hashlib.sha256(raw[3]).hexdigest(),
                                   "ownership": "startup-only; code and state discarded before bitmap ownership"}
                                  if a.import_code else None),
                  "sha256": {"files": hashlib.sha256(raw[1]).hexdigest(),
                             "render": hashlib.sha256(raw[2]).hexdigest(),
                             "startup_assets": hashlib.sha256(assets).hexdigest(),
                             "packaged_prg": hashlib.sha256(prg).hexdigest()},
                  "contract": "startup bytes released only after native bootstrap; immutable REU payload trust, no native CRC"}
        a.manifest.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
