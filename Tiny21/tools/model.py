"""Convert the pinned TNY2 checkpoint to a compact REU image.

The canonical layout keeps the original row weights. The experimental group4
layout repacks selected dense rows into bitplane masks at the same size.
The group8 candidate uses wider masks for Q/K/V and F1. All layouts
use Q0.24 row scales, Q4.12 RMS gains and the same tiled directory.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct

MODEL_SHA = "4b603237070ad9084433537bf8d6c7470d0fc583e6a4f1f03c00cd17264e7095"
TILE_ROWS = 16
HEADER_SIZE = 4096
LAYOUTS = {"canonical": 1, "group4": 2, "group8": 3}


@dataclass
class Matrix:
    rows: int
    cols: int
    weights: list[bytes]
    scales: list[float]


def decode(data):
    if len(data) < 12 or struct.unpack_from("<4s4H", data) != (b"TNY2", 96, 4, 4, 256):
        raise ValueError("expected TNY2 checkpoint with D96/L4/H4/HID256")
    cursor = 12
    matrices = {}
    gains = {}

    def take(size):
        nonlocal cursor
        end = cursor + size
        if end > len(data):
            raise ValueError(f"checkpoint truncated at byte {cursor}")
        result = data[cursor:end]
        cursor = end
        return result

    def matrix(name, rows, cols):
        scales, weights = [], []
        for _ in range(rows):
            scale, = struct.unpack("<f", take(4))
            if not math.isfinite(scale) or not 0 < scale < 1:
                raise ValueError(f"invalid row scale in {name}")
            scales.append(scale)
            weights.append(take(cols))
        matrices[name] = Matrix(rows, cols, weights, scales)

    def gain(name):
        values = struct.unpack("<96f", take(384))
        if not all(math.isfinite(v) and -8 <= v < 8 for v in values):
            raise ValueError(f"invalid gain in {name}")
        gains[name] = values

    matrix("embedding", 97, 96)
    matrix("position", 128, 96)
    for layer in range(4):
        gain(f"{layer}.g1")
        for projection in ("q", "k", "v", "o"):
            matrix(f"{layer}.{projection}", 96, 96)
        gain(f"{layer}.g2")
        matrix(f"{layer}.f1", 256, 96)
        matrix(f"{layer}.f2", 96, 256)
    gain("final")
    if cursor != len(data):
        raise ValueError(f"unexpected bytes after checkpoint at byte {cursor}")
    return matrices, gains


def mask_row(row):
    """Convert weight bytes to four high-to-low packed bitplane runs."""
    if len(row) % 4:
        raise ValueError("packed bitplane rows require complete four-weight groups")
    packed = bytearray()
    for bit in (6, 4, 2, 0):
        for first in range(0, len(row), 4):
            pair = 0
            for lane, weight in enumerate(row[first:first + 4]):
                pair |= ((weight >> bit) & 1) << lane
                pair |= ((weight >> (bit + 1)) & 1) << (lane + 4)
            packed.append(pair)
    return packed


def mask_row_group8(row):
    """Convert 96 signed-weight bytes to eight successive bitplanes."""
    if len(row) != 96:
        raise ValueError("group-eight rows require 96 weights")
    return bytes(
        sum(((weight >> bit) & 1) << lane
            for lane, weight in enumerate(row[start:start + 8]))
        for bit in range(7, -1, -1)
        for start in range(0, len(row), 8)
    )


def image(data, layout="canonical"):
    if layout not in LAYOUTS:
        raise ValueError(f"unknown matrix layout {layout!r}")
    version = LAYOUTS[layout]
    matrices, gains = decode(data)
    digest = hashlib.sha256(data).hexdigest()
    if digest != MODEL_SHA:
        raise ValueError(f"unexpected checkpoint SHA-256: {digest}")
    payload = bytearray(HEADER_SIZE)
    directory = {}
    entries = []
    for name, matrix in matrices.items():
        projection = name.rsplit(".", 1)[-1]
        transform = None
        if version >= 2 and projection in ("q", "k", "v", "o", "f1"):
            transform = mask_row
            if version == 3 and projection != "o":
                transform = mask_row_group8
        start = len(payload)
        for first in range(0, matrix.rows, TILE_ROWS):
            stop = first + TILE_ROWS
            weights = matrix.weights[first:stop]
            payload.extend(b"".join(map(transform, weights) if transform else weights))
            for scale in matrix.scales[first:stop]:
                payload.extend(round(scale * (1 << 24)).to_bytes(3, "little"))
        directory[name] = dict(offset=start, rows=matrix.rows, columns=matrix.cols)
        entries.append((start, matrix.rows, matrix.cols))
    gain_base = len(payload)
    for name, values in gains.items():
        directory[name] = dict(offset=len(payload), count=len(values))
        payload.extend(struct.pack("<96h", *(round(v * 4096) for v in values)))
    struct.pack_into("<4sBBBBHHII32s", payload, 0, b"T64M", version, 96, 4, 4,
                     256, len(entries), len(payload), gain_base, bytes.fromhex(digest))
    for index, entry in enumerate(entries):
        struct.pack_into("<IHH", payload, 64 + 8 * index, *entry)
    manifest = dict(model_sha256=digest, image_sha256=hashlib.sha256(payload).hexdigest(),
                    format_version=version, tile_rows=TILE_ROWS, bytes=len(payload), regions=directory)
    return payload, manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--layout", choices=LAYOUTS, default="canonical")
    args = parser.parse_args()
    payload, manifest = image(args.checkpoint.read_bytes(), args.layout)
    args.output.write_bytes(payload)
    args.output.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n")
