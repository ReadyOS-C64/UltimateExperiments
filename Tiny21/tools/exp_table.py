"""Emit the fixed-point attention exponential lookup table for ca65."""
from tools.oracle import EXP_TABLE

for start in range(0, len(EXP_TABLE), 8):
    # The first entry is exactly 2^24 and takes a special path in assembly.
    print("    .faraddr " + ",".join(str(value & 0xffffff)
                                    for value in EXP_TABLE[start:start + 8]))
