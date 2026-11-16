"""Run a hybrid question benchmark with every dense projection in assembly.

The host integer oracle still executes normalization, attention, embeddings
and token selection. CPU cycles cover assembly projections only.
"""
import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import struct
from time import perf_counter

from tools.model import image
from tools.oracle import Network, dense_input, input_tokens
from tools.peddle import Machine


@dataclass
class Totals:
    cycles: int = 0
    dma_calls: int = 0
    dma_bytes: int = 0

    def add(self, stats):
        _, cycles, calls, size, flags, _ = stats
        if flags & 1:
            raise RuntimeError("assembly projection rejected the operation")
        self.cycles += cycles
        self.dma_calls += calls
        self.dma_bytes += size

    def report(self, steps):
        cpu_seconds = self.cycles / 64_000_000
        scenarios = {}
        for bandwidth in (1, 4, 16):
            modeled = cpu_seconds + self.dma_bytes / (bandwidth * 1024**2)
            scenarios[str(bandwidth)] = {
                "projection_seconds": modeled,
                "projection_steps_per_second": steps / modeled if modeled else None,
            }
        return {**asdict(self), "steps": steps, "ideal_64mhz_cpu_seconds": cpu_seconds,
                "cpu_only_steps_per_second": steps / cpu_seconds if cpu_seconds else None,
                "hypothetical_dma_mib_per_second": scenarios}


class AssemblyProjections:
    def __init__(self, machine, checkpoint):
        self.machine = machine
        payload, self.manifest = image(checkpoint)
        payload = bytes(payload)
        start = perf_counter()
        machine.preload(payload)
        self.preload_seconds = perf_counter() - start
        self.totals = Totals()
        machine.put("reu_banks", 32)

    def __call__(self, name, values):
        m = self.machine
        descriptor = self.manifest["regions"][name]
        inputs, shift = dense_input(values)
        m.prepare(inputs)
        self.totals.cycles += m.last_stats[1]
        m.put("scale_shift", shift)
        m.put("reu_addr", descriptor["offset"], 3)
        address = m.symbols["matrix_dots"]
        result = []
        remaining = descriptor["rows"]
        while remaining:
            rows = min(16, remaining)
            m.put("matrix_rows", rows)
            self.totals.add(m.run("matrix_project"))
            result.extend(struct.unpack_from(f"<{rows}i", m.ram, address))
            remaining -= rows
        return result


def benchmark(checkpoint, question):
    machine = Machine()
    try:
        projections = AssemblyProjections(machine, checkpoint)
        network = Network(checkpoint, project=projections)
        prompt = input_tokens(question)
        start = perf_counter()
        for token in prompt:
            network.step(token, logits=False)
        scores = network.step(1)
        first_logits_wall = perf_counter() - start
        prefill = projections.totals.report(len(prompt) + 1)
        projections.totals = Totals()
        output = []
        while network.position < 128:
            token = max(range(97), key=scores.__getitem__)
            if token <= 1:
                break
            output.append(chr(token + 30))
            scores = network.step(token)
        wall = perf_counter() - start
        answer = "".join(output)
        expected = Network(checkpoint).answer(question)
        if answer != expected:
            raise RuntimeError(f"assembly projection answer {answer!r} differs from {expected!r}")
        return dict(question=question, answer=answer, host_wall_seconds=wall,
                    host_first_logits_seconds=first_logits_wall,
                    host_reu_preload_seconds=projections.preload_seconds,
                    model_image_bytes=projections.manifest["bytes"],
                    prefill=prefill, decode=projections.totals.report(len(output)),
                    scope="Peddle assembly dense projections and DMA, with host oracle orchestration")
    finally:
        machine.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("question", nargs="+")
    args = parser.parse_args()
    checkpoint = args.checkpoint.read_bytes()
    for question in args.question:
        print(json.dumps(benchmark(checkpoint, question)), flush=True)
