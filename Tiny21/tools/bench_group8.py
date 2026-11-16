"""Measure exact group-four and group-eight raw dots on real projection rows."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import struct

from tools.model import decode, mask_row, mask_row_group8
from tools.oracle import Network, dense_input, input_tokens
from tools.peddle import BUILD, Machine

COLUMNS = 96
ROW_BUFFER = 0xCC00


def prepare(machine, vector, group):
    machine.put("dot_columns", len(vector))
    for name, shift in (("activation_lo", 0), ("activation_hi", 8)):
        address = machine.symbols[name]
        machine.ram[address:address + len(vector)] = bytes((v >> shift) & 255 for v in vector)
    return machine.run(f"group{group}_prepare")[1]


def dot(machine, weights, group):
    packed = mask_row_group8(weights) if group == 8 else mask_row(weights)
    machine.ram[ROW_BUFFER:ROW_BUFFER + COLUMNS] = packed
    machine.put("dot_weights", ROW_BUFFER, 2)
    cycles = machine.run(f"group{group}_dot")[1]
    return machine.get("dot_result", 4, signed=True), cycles


def trace_vectors(checkpoint, matrix_names):
    network = Network(checkpoint)
    vectors = {}
    position = 0

    def capture(name, values):
        if position in (0, 8, 17) and name in matrix_names:
            vectors[position, name] = dense_input(values)[0]
        return network.matrices[name].apply(values)

    network.project = capture
    prompt = input_tokens("what is 7 times 8") + [1]
    for position, token in enumerate(prompt):
        network.step(token, logits=position == len(prompt) - 1)
    return vectors


def measure(checkpoint, candidate):
    matrices, _ = decode(checkpoint)
    names = {name for name, matrix in matrices.items()
             if "." in name and matrix.cols == COLUMNS}
    vectors = trace_vectors(checkpoint, names)
    machine = Machine(candidate)
    rng = random.Random(6510)
    extremes = [
        ([-32768] * COLUMNS, [-128] * COLUMNS),
        ([32767] * COLUMNS, [127] * COLUMNS),
        ([-32768, 32767, -1, 1] * 24, [-128, 127, -1, 1] * 24),
        ([0] * 95 + [-32768], [-128] * COLUMNS),
        ([0] * COLUMNS, [-128] * COLUMNS),
    ]
    for _ in range(16):
        extremes.append(([rng.randrange(-32768, 32768) for _ in range(COLUMNS)],
                         [rng.randrange(-128, 128) for _ in range(COLUMNS)]))
    rows = []
    try:
        for vector, weights in extremes:
            expected = sum(x * w for x, w in zip(vector, weights, strict=True))
            for group in (4, 8):
                prepare(machine, vector, group)
                assert dot(machine, weights, group)[0] == expected

        for (position, name), vector in sorted(vectors.items()):
            weights = [struct.unpack("<96b", raw) for raw in matrices[name].weights]
            record = dict(position=position, matrix=name, rows=len(weights))
            expected = [sum(x * w for x, w in zip(vector, row, strict=True)) for row in weights]
            for group in (4, 8):
                build_cycles = prepare(machine, vector, group)
                if name.endswith((".k", ".v")):
                    query_name = name[:-1] + "q"
                    assert vectors[position, query_name] == vector
                    build_cycles = 0
                measured = [dot(machine, row, group) for row in weights]
                assert [value for value, _ in measured] == expected, (position, name, group)
                record[f"group{group}"] = dict(prepare_cycles=build_cycles,
                                                dot_cycles=sum(cycles for _, cycles in measured))
            rows.append(record)
    finally:
        machine.close()
    return dict(checkpoint_sha256=hashlib.sha256(checkpoint).hexdigest(),
                core_sha256=hashlib.sha256((candidate / "core.bin").read_bytes()).hexdigest(),
                exact_extrema_and_random_cases=len(extremes),
                columns=COLUMNS, packed_bytes_per_row=COLUMNS, projections=rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--candidate", type=Path, default=BUILD / "group8-bench")
    args = parser.parse_args()
    print(json.dumps(measure(args.checkpoint.read_bytes(), args.candidate), indent=2))
