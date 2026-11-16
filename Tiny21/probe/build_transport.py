"""Build a transport-only Ultimate PROBE.PRG with a pinned 4 KiB sample."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zlib

from probe.build import ROOT, SOURCE, RUN_PATH, digest

SAMPLE_OFFSET = 0x2000
SAMPLE_SIZE = 0x1000
METHODS_REU = ["reu-4096-dma", "reu-256-dma", "reu-byte-dma", "cpu-ram-unrolled"]
METHODS_GEO = ["georam-window-unrolled", "cpu-ram-unrolled"]


def build(out, remote, mode):
    if not RUN_PATH.fullmatch(remote):
        raise ValueError("remote directory must be /USBn/TINY64-<unique run ID>")
    out.mkdir(parents=True, exist_ok=True)
    data = (ROOT / "build/model.reu").read_bytes()
    sample = data[SAMPLE_OFFSET:SAMPLE_OFFSET + SAMPLE_SIZE]
    if len(sample) != SAMPLE_SIZE:
        raise ValueError("canonical model has no complete transport sample")
    (out / "sample.bin").write_bytes(sample)
    identifying_bytes = hashlib.sha256(remote.encode("ascii")).digest()
    palette = (1, 3, 6, 7, 13, 14)
    marker = [palette[value % len(palette)] for value in identifying_bytes[:12]]
    nonce = int.from_bytes(identifying_bytes[-2:], "little")
    (out / "transport.inc").write_text(
        f"TRANSPORT_GEO = {int(mode == 'georam')}\n"
        f"RUN_NONCE = ${nonce:04x}\n"
        f".define RUN_MARKER {','.join(map(str, marker))}\n")
    objects = [(ROOT / "build/reu.o")]
    for stem in ("boot", "clock", "transport"):
        obj = out / f"{stem}.o"
        subprocess.run(["ca65", "-I", str(out), "-g", "-o", str(obj),
                        str(SOURCE / f"{stem}.s")], cwd=out, check=True)
        objects.append(obj)
    prg = out / "PROBE.PRG"
    labels = out / "probe.lbl"
    subprocess.run(["ld65", "-C", str(SOURCE / "ultimate.cfg"), "-m", str(out / "probe.map"),
                    "-Ln", str(labels), "-o", str(prg), *map(str, objects)], check=True)
    symbols = {name.lstrip("."): int(address, 16)
               for kind, address, name in (line.split() for line in labels.read_text().splitlines())
               if kind == "al"}
    raw = prg.read_bytes()
    start = int.from_bytes(raw[:2], "little")
    end = start + len(raw) - 2
    if (start != 0x801 or symbols["probe_start"] != 0x80d
            or symbols["__PROBE_LOAD__"] != 0x5000
            or symbols["__PROBE_LOAD__"] + symbols["__PROBE_SIZE__"] != end
            or symbols["__PROBE_RUN__"] != 0xa000 or symbols["sample"] & 255
            or raw[-len(sample):] != sample):
        raise ValueError("invalid transport PRG layout")
    manifest = {
        "remote_path": remote,
        "transport_mode": mode,
        "prg_sha256": digest(prg),
        "sample_sha256": hashlib.sha256(sample).hexdigest(),
        "sample_crc32": f"{zlib.crc32(sample):08x}",
        "sample_offset": SAMPLE_OFFSET,
        "sample_bytes": SAMPLE_SIZE,
        "sweeps": 8,
        "methods": METHODS_GEO if mode == "georam" else METHODS_REU,
        "mailbox": 0xca00,
        "nonce": nonce,
        "video_colors": marker,
        "load_range": [start, end - 1],
    }
    (out / "bundle.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--out", required=True, type=Path)
    cli.add_argument("--remote", required=True)
    cli.add_argument("--mode", required=True, choices=["reu", "georam"])
    args = cli.parse_args()
    print(json.dumps(build(args.out.resolve(), args.remote, args.mode), indent=2))
