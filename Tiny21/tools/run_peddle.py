"""Run complete Tiny-2.1 inference on the assembled core using Peddle."""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import struct
from time import perf_counter

from tools.model import LAYOUTS, image
from tools.oracle import Network, input_tokens
from tools.peddle import BUILD, Machine

CPU_HZ = 64_000_000
STEP_LIMIT = 175_000_000


@dataclass
class Timing:
    cycles: int = 0
    transfers: int = 0
    bytes: int = 0
    peak_stack_bytes: int = 0

    def add(self, stats, stack_bytes):
        _, cycles, transfers, size, flags, _ = stats
        if flags & 1:
            raise RuntimeError("target routine reported failure")
        self.cycles += cycles
        self.transfers += transfers
        self.bytes += size
        self.peak_stack_bytes = max(self.peak_stack_bytes, stack_bytes)

    def report(self):
        return dict(cpu_cycles=self.cycles, dma_calls=self.transfers, dma_bytes=self.bytes,
                    peak_stack_bytes=self.peak_stack_bytes,
                    ideal_64mhz_cpu_seconds=self.cycles / CPU_HZ)


class Target:
    def __init__(self, machine, checkpoint, layout="canonical"):
        self.machine = machine
        payload, manifest = image(checkpoint, layout)
        payload = bytes(payload)
        start = perf_counter()
        machine.preload(payload)
        self.preload_seconds = perf_counter() - start
        self.image_sha256 = manifest["image_sha256"]
        self.model_length = len(payload)
        machine.put("reu_banks", 32)
        self.admission = Timing()
        self.execute(self.admission, "model_open")

    def execute(self, timing, label, accumulator=0, *, x=0, instruction_limit=2_000_000):
        m = self.machine
        timing.add(m.run(label, accumulator, x=x, instruction_limit=instruction_limit,
                         model_length=self.model_length), m.stack_bytes)

    def answer(self, question, verify=None):
        m = self.machine
        prefill = Timing()
        decode = Timing()
        trace = []
        prompt = input_tokens(question)

        def consume(token, logits, timing):
            self.execute(timing, "model_ingest", token, x=int(logits), instruction_limit=STEP_LIMIT)
            if verify is not None:
                scores = (struct.unpack_from("<97i", m.ram, m.symbols["logits"]) if logits else None)
                trace.append((token, scores))

        start = perf_counter()
        self.execute(prefill, "model_reset")
        for token in prompt:
            consume(token, False, prefill)
        consume(1, True, prefill)
        self.execute(prefill, "model_choose")
        token = m.accumulator
        first_decision = perf_counter() - start

        answer = []
        while token > 1 and m.get("token_pos", 1) < 128:
            answer.append(chr(token + 30))
            consume(token, True, decode)
            if m.get("token_pos", 1) < 128:
                self.execute(decode, "model_choose")
                token = m.accumulator
        elapsed = perf_counter() - start
        stop = "context" if m.get("token_pos", 1) == 128 else "eos"
        if verify is not None:
            reference = Network(verify)
            for position, (token_id, scores) in enumerate(trace):
                expected = reference.step(token_id, logits=scores is not None)
                if scores is not None and scores != tuple(expected):
                    raise AssertionError(f"target logits differ from the reference at position {position}")
            if "".join(answer) != reference.answer(question):
                raise AssertionError("target greedy answer differs from the reference")

        return dict(question=question, answer="".join(answer), stop=stop,
                    prefill_tokens=len(prompt) + 1, emitted_characters=len(answer),
                    host_first_decision_seconds=first_decision,
                    host_elapsed_seconds=elapsed,
                    prefill=prefill.report(), decode=decode.report(),
                    ideal_64mhz_decode_characters_per_second=(
                        CPU_HZ * len(answer) / decode.cycles if decode.cycles else None))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("question", nargs="+")
    parser.add_argument("--verify", action="store_true", help="compare results with the integer reference")
    parser.add_argument("--core-dir", type=Path, default=BUILD, help="directory with linked core and labels")
    parser.add_argument("--layout", choices=LAYOUTS, default="canonical")
    args = parser.parse_args()
    checkpoint = args.checkpoint.read_bytes()
    machine = Machine(args.core_dir)
    try:
        target = Target(machine, checkpoint, args.layout)
        print(json.dumps(dict(host_reu_preload_seconds=target.preload_seconds,
                              image_sha256=target.image_sha256,
                              admission=target.admission.report())), flush=True)
        for question in args.question:
            print(json.dumps(target.answer(question, verify=checkpoint if args.verify else None)),
                  flush=True)
    finally:
        machine.close()
