"""Attribute actual Peddle instruction cycles to linked assembly modules."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from tools.model import LAYOUTS
from tools.peddle import BUILD, Machine
from tools.run_peddle import Target


def module_cycles(profile, map_text):
    modules, segments, _ = map_text.split("\n\n", maxsplit=2)
    code_base = int(re.search(r"^CODE\s+([\dA-F]+)", segments, re.MULTILINE)[1], 16)
    result = {}
    for name, offset, size in re.findall(
            r"^([\w.]+):\n\s+CODE\s+Offs=([\dA-F]+)\s+Size=([\dA-F]+)", modules, re.MULTILINE):
        first = code_base + int(offset, 16)
        result[name] = sum(profile[first:first + int(size, 16)])
    if sum(result.values()) != sum(profile):
        raise ValueError("some instruction cycles lie outside the linked modules")
    return dict(sorted(result.items(), key=lambda item: item[1], reverse=True))


def profile(checkpoint, core_dir, question, layout):
    machine = Machine(core_dir)
    try:
        target = Target(machine, checkpoint, layout)
        histogram = machine.cycle_profile()
        report = target.answer(question, verify=checkpoint)
        cycles = module_cycles(histogram, (core_dir / "core.map").read_text())
        if sum(cycles.values()) != report["prefill"]["cpu_cycles"] + report["decode"]["cpu_cycles"]:
            raise ValueError("module profile does not sum to measured question cycles")
        return {**report, "module_cpu_cycles": cycles, "model_sha256": target.image_sha256,
                "core_sha256": hashlib.sha256((core_dir / "core.bin").read_bytes()).hexdigest()}
    finally:
        machine.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("question")
    parser.add_argument("--core-dir", type=Path, default=BUILD)
    parser.add_argument("--layout", choices=LAYOUTS, default="canonical")
    args = parser.parse_args()
    print(json.dumps(profile(args.checkpoint.read_bytes(), args.core_dir, args.question, args.layout), indent=2))
