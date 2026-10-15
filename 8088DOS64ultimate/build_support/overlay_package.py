#!/usr/bin/env python3
"""Package linked, fixed-address overlays into a temporary bitmap startup blob.

The resident PRG must end by 6000; padding plus five complete 2048-byte slots
are loaded at6000/6800/8000/8800/9000. Native bootstrap must commit these to immutable REU
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
    if identity not in (1, 2, 3, 4, 5):
        raise ValueError("unknown overlay identity")
    if not 1 <= len(payload) <= WINDOW_SIZE:
        raise ValueError("overlay payload must fit C900–CFFF and be nonempty")
    tag = {1:b"FILE",2:b"TEXT",3:b"KEYS",4:b"TIME",5:b"CGA "}[identity]
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
    import_size=symbols.get("__IMPORTCODE_SIZE__",0)
    cold_cursor=IMPORT_START+import_size
    for name in ("COLDINIT","COLDRODATA","UNITCOLD"):
        size=symbols.get("__"+name+"_SIZE__",0)
        if name=="UNITCOLD" and not size:
            continue
        if not size or symbols.get("__"+name+"_LOAD__")!=cold_cursor or symbols.get("__"+name+"_RUN__")!=cold_cursor:
            raise ValueError("cold BIOS/bootstrap/data segments must follow importer contiguously")
        cold_cursor+=size
    if cold_cursor!=IMPORT_START+len(cold):
        raise ValueError("cold linked output length differs from its segment total")
    expected = {"__IMPORT_START__": IMPORT_START, "__IMPORT_SIZE__": IMPORT_SIZE,
                "__IMPORT_FILEOFFS__": 0, "__IMPORT_LAST__": IMPORT_START + len(cold),
                "__IMPORTCODE_LOAD__": IMPORT_START, "__IMPORTCODE_RUN__": IMPORT_START,
                "__IMPORTCODE_SIZE__": import_size,
                "dos64_import_code_start": IMPORT_START,
                "dos64_import_code_end": IMPORT_START + import_size,
                "dos64_import_state_end": IMPORT_START + import_size}
    if not 1 <= len(cold) <= IMPORT_SIZE:
        raise ValueError("cold importer must be nonempty and fit 7000..7FFF")
    if any(symbols.get(k) != v for k, v in expected.items()):
        raise ValueError("cold importer differs from linked address/length/phase contract")
    if not IMPORT_START <= symbols.get("dos64_import_state_start", -1) < IMPORT_START + len(cold):
        raise ValueError("cold state must remain inside the discarded import image")
    return prg + cold + bytes(IMPORT_SIZE - len(cold))


def append_input(prg,payload,labels):
    symbols={name.lstrip("."):int(addr,16) for addr,name in re.findall(r"^al ([0-9A-Fa-f]+) (\S+)",labels,re.M)}
    expected={"__INPUT_START__":WINDOW,"__INPUT_SIZE__":WINDOW_SIZE,"__INPUT_FILEOFFS__":0,
              "__INPUT_LAST__":WINDOW+len(payload),"__INPUTCODE_LOAD__":WINDOW,
              "__INPUTCODE_RUN__":WINDOW,"__INPUTCODE_SIZE__":len(payload)}
    if prg[:2]!=b"\x01\x08" or len(prg)!=0x8000-0x801+2:
        raise ValueError("INPUT source requires complete cold7000..7FFF phase")
    if any(symbols.get(k)!=v for k,v in expected.items()):
        raise ValueError("INPUT linked payload address/length differs from its source phase")
    block=slot(payload,3)
    return prg+block,block


def append_variant(prg,payload,labels,identity,area,members,source):
    symbols={name.lstrip("."):int(addr,16) for addr,name in re.findall(r"^al ([0-9A-Fa-f]+) (\S+)",labels,re.M)}
    cursor=WINDOW
    for name in members:
        size=symbols.get("__"+name+"_SIZE__",0)
        if not size or symbols.get("__"+name+"_LOAD__")!=cursor or symbols.get("__"+name+"_RUN__")!=cursor:
            raise ValueError(area+" member placement differs from linked output")
        cursor+=size
    expected={"__"+area+"_START__":WINDOW,"__"+area+"_SIZE__":WINDOW_SIZE,"__"+area+"_FILEOFFS__":0,"__"+area+"_LAST__":cursor}
    if len(prg)!=source-0x801+2 or cursor-WINDOW!=len(payload) or any(symbols.get(k)!=v for k,v in expected.items()):
        raise ValueError(area+" source/length differs from linked output")
    block=slot(payload,identity)
    return prg+block,block

def validate_text(payload,labels):
    symbols={name.lstrip("."):int(addr,16) for addr,name in re.findall(r"^al ([0-9A-Fa-f]+) (\S+)",labels,re.M)}
    expected={"__RENDERCODE_RUN__":WINDOW,"__RENDERCODE_SIZE__":718,"__DISPLAYCODE_RUN__":WINDOW+718,"__DISPLAYCODE_SIZE__":245,"__RENDER_LAST__":WINDOW+963}
    if len(payload)!=963 or any(symbols.get(k)!=value for k,value in expected.items()):
        raise ValueError("TEXT payload must include canonical contiguous718-byte renderer+245-byte VIC setup")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--resident-prg", type=pathlib.Path, required=True)
    p.add_argument("--files", type=pathlib.Path, required=True)
    p.add_argument("--render", type=pathlib.Path, required=True)
    p.add_argument("--input",type=pathlib.Path,required=True)
    p.add_argument("--pit",type=pathlib.Path,required=True)
    p.add_argument("--gfx",type=pathlib.Path,required=True)
    p.add_argument("--import-code", type=pathlib.Path,required=True)
    p.add_argument("--labels", type=pathlib.Path)
    p.add_argument("--output-prg", type=pathlib.Path, required=True)
    p.add_argument("--output-assets", type=pathlib.Path, required=True)
    p.add_argument("--manifest", type=pathlib.Path)
    a = p.parse_args()
    if not a.labels or bool(a.import_code) != bool(a.labels):
        p.error("cold importer requires both linked code and labels")
    inputs = (a.resident_prg,a.files,a.render,a.import_code,a.labels,a.input,a.pit,a.gfx)
    outputs = (a.output_prg, a.output_assets) + ((a.manifest,) if a.manifest else ())
    resolved = [path.resolve() for path in inputs + outputs]
    if len(set(resolved)) != len(resolved):
        p.error("input/output paths must be distinct")
    raw = [path.read_bytes() for path in inputs]
    try:
        validate_text(raw[2],raw[4].decode())
        prg, assets = package(*raw[:3])
        if a.import_code:
            prg = append_import(prg,raw[3],raw[4].decode())
        prg,input_slot=append_input(prg,raw[5],raw[4].decode())
        assets+=input_slot
        prg,pit_slot=append_variant(prg,raw[6],raw[4].decode(),4,"PIT",("IRQMAIN","IRQDEVICE","PITCODE"),0x8800)
        prg,gfx_slot=append_variant(prg,raw[7],raw[4].decode(),5,"GFX",("GFXCODE",),0x9000)
        assets+=pit_slot+gfx_slot
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
                  "slot_size": SLOT_SIZE, "payload_lengths": [len(raw[1]),len(raw[2]),len(raw[5]),len(raw[6]),len(raw[7])],
                  "startup_sources": [0x6000,0x6800,0x8000,0x8800,0x9000],
                  "text_members": {"RENDERCODE":718,"DISPLAYCODE":245},
                  "fonts": {"narrow":{"start":0x4400,"bytes":1024,"executable":False,"sha256":hashlib.sha256(raw[0][0x4400-0x801+2:0x4800-0x801+2]).hexdigest()},"full":{"start":0x4800,"bytes":2048,"executable":False,"sha256":hashlib.sha256(raw[0][0x4800-0x801+2:0x5000-0x801+2]).hexdigest()}},
                  "input_source_ownership": "copied before any guest cache use; then first four cache frames",
                  "input_sha256": hashlib.sha256(raw[5]).hexdigest(),
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
