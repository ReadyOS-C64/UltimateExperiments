"""Compare the exact packed group-four kernel with the shipping projection."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import struct

from tools.model import TILE_ROWS, decode, image, mask_row
from tools.oracle import Network, dense_input, input_tokens
from tools.peddle import BUILD, Machine


def masked_image(payload, regions, matrices):
    result = bytearray(payload)
    for name in ("embedding", *(name for name in matrices if "." in name)):
        matrix = matrices[name]
        offset = regions[name]["offset"]
        for first in range(0, matrix.rows, TILE_ROWS):
            rows = matrix.weights[first:first + TILE_ROWS]
            for row in rows:
                result[offset:offset + matrix.cols] = mask_row(row)
                offset += matrix.cols
            offset += 3 * len(rows)
    return result


def activate(machine, values, routine):
    for name, shift in (("activation_lo", 0), ("activation_hi", 8)):
        address = machine.symbols[name]
        machine.ram[address:address + len(values)] = bytes((v >> shift) & 255 for v in values)
    machine.put("dot_columns", len(values) & 255)
    _, cycles, _, _, status, _ = machine.run(routine)
    if routine == "group4_prepare":
        assert not status & 1
    return cycles


def exact_dots(machine):
    rng = random.Random(6510)
    for count in (4, 24, 96, 256):
        extrema = [-32768] * count
        cases = [
            ([0] * count, [-128] * count),
            ([0] * (count - 1) + [-32768], [-128] * count),
            (extrema, [-128] * count),
            (extrema, [127] * count),
            ([-32768, 32767, -1, 1] * (count // 4), [-128, 127, -1, 1] * (count // 4)),
        ]
        for _ in range(16):
            cases.append(([rng.randrange(-32768, 32768) for _ in range(count)],
                          [rng.randrange(-128, 128) for _ in range(count)]))
        for vector, weights in cases:
            activate(machine, vector, "group4_prepare")
            machine.ram[0x8000:0x8000 + count] = mask_row(weights)
            machine.put("dot_weights", 0x8000, 2)
            machine.run("group4_dot")
            assert machine.get("dot_result", 4, signed=True) == sum(
                x * w for x, w in zip(vector, weights, strict=True)), (count, vector, weights)


def project(machine, region, shift):
    machine.put("reu_addr", region["offset"], 3)
    machine.put("scale_shift", shift)
    done = []
    totals = dict(project_cycles=0, dma_calls=0, dma_bytes=0)
    address = machine.symbols["matrix_dots"]
    for first in range(0, region["rows"], TILE_ROWS):
        count = min(region["rows"] - first, TILE_ROWS)
        machine.put("matrix_rows", count)
        _, cycles, calls, size, status, _ = machine.run("matrix_project")
        assert not status & 1
        done.extend(struct.unpack_from(f"<{count}i", machine.ram, address))
        totals["project_cycles"] += cycles
        totals["dma_calls"] += calls
        totals["dma_bytes"] += size
    return done, totals


def run(checkpoint, candidate_dir):
    original, manifest = image(checkpoint)
    matrices, _ = decode(checkpoint)
    regions = manifest["regions"]
    packed = masked_image(original, regions, matrices)
    baseline = Machine()
    candidate = Machine(candidate_dir)
    rows = []
    try:
        exact_dots(candidate)
        baseline.preload(original)
        candidate.preload(packed)
        baseline.put("reu_banks", 32)
        candidate.put("reu_banks", 32)
        network = Network(checkpoint)
        position = 0

        def compare(name, values):
            expected = network.matrices[name].apply(values)
            if position not in (0, 8, 17):
                return expected
            activation, shift = dense_input(values)
            row = dict(position=position, matrix=name, zero_activation_count=activation.count(0),
                       columns=len(activation), rows=regions[name]["rows"])
            for label, machine, routine in (("baseline", baseline, "dot_prepare"),
                                            ("group4", candidate, "group4_prepare")):
                # Q/K/V share the exact same prepared vector in the native core.
                preparation = 0 if name.endswith((".k", ".v")) else activate(machine, activation, routine)
                result, totals = project(machine, regions[name], shift)
                assert expected == result, (label, name, position)
                row[label] = dict(prepare_cycles=preparation, **totals)
            for counter in ("dma_calls", "dma_bytes"):
                assert row["baseline"][counter] == row["group4"][counter]
            rows.append(row)
            return expected

        network.project = compare
        for position, token in enumerate(input_tokens("what is 7 times 8") + [1]):
            network.step(token, logits=position == 17)
        return dict(checkpoint_sha256=manifest["model_sha256"],
                    baseline_core_sha256=hashlib.sha256((BUILD / "core.bin").read_bytes()).hexdigest(),
                    candidate_core_sha256=hashlib.sha256((candidate_dir / "core.bin").read_bytes()).hexdigest(),
                    model_image_sha256=manifest["image_sha256"],
                    experimental_weight_image_sha256=hashlib.sha256(packed).hexdigest(),
                    exact_dot_cases=84, projections=rows)
    finally:
        baseline.close()
        candidate.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--candidate-dir", type=Path, default=BUILD / "group4-matrix")
    args = parser.parse_args()
    print(json.dumps(run(args.checkpoint.read_bytes(), args.candidate_dir), indent=2))
