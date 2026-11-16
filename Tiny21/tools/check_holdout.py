"""Replay a verified target holdout on a candidate build in parallel Peddle sessions."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

from tools.model import LAYOUTS
from tools.peddle import BUILD


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def assign_batches(baseline, workers):
    costs = [sum(q[phase]["cpu_cycles"] for phase in ("prefill", "decode")) for q in baseline]
    batches = [[] for _ in range(workers)]
    loads = [0] * workers
    for index in sorted(range(len(costs)), key=costs.__getitem__, reverse=True):
        worker = min(range(workers), key=loads.__getitem__)
        batches[worker].append(index)
        loads[worker] += costs[index]
    return batches


def run(args):
    baseline = json.loads(args.baseline.read_bytes())["questions"]
    prompts = args.prompts.read_text().splitlines()
    if not prompts or args.jobs < 1 or prompts != [row["question"] for row in baseline]:
        raise ValueError("check the worker count and use the same ordered prompts as the verified baseline")
    core_hash = digest(args.core_dir / "core.bin")
    model_hash = digest(args.model_image)
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "pid").write_text(f"{os.getpid()}\n")
    batches = assign_batches(baseline, min(args.jobs, len(prompts)))
    (args.out / "shards.json").write_text(json.dumps(batches) + "\n")
    (args.out / "identity.json").write_text(
        json.dumps(dict(core_sha256=core_hash, model_sha256=model_hash, layout=args.layout), indent=2) + "\n")

    def worker(entry):
        number, batch = entry
        stem = args.out / f"shard-{number}"
        with stem.with_suffix(".jsonl").open("w") as records, stem.with_suffix(".stderr").open("w") as errors:
            result = subprocess.run([sys.executable, "-m", "tools.run_peddle",
                                     "--core-dir", str(args.core_dir), "--layout", args.layout,
                                     "--verify", "--", str(args.checkpoint), *[prompts[i] for i in batch]],
                                    stdout=records, stderr=errors)
        stem.with_suffix(".status").write_text(f"{result.returncode}\n")
        print(f"{stem.name}: {result.returncode}", flush=True)
        return result.returncode

    with ThreadPoolExecutor(max_workers=len(batches)) as pool:
        if any(list(pool.map(worker, enumerate(batches, start=1)))):
            raise RuntimeError(f"one or more Peddle workers failed in {args.out}")

    results = [None] * len(prompts)
    for number, batch in enumerate(batches, start=1):
        stem = args.out / f"shard-{number}"
        admission, *rows = map(json.loads, stem.with_suffix(".jsonl").read_text().splitlines())
        if admission["image_sha256"] != model_hash:
            raise ValueError(f"worker {number} loaded the wrong model")
        for index, row in zip(batch, rows, strict=True):
            previous = baseline[index]
            if any(row[field] != previous[field] for field in ("question", "answer", "stop")):
                raise ValueError(f"answer or stop condition changed at prompt {index + 1}")
            if any(row[phase][field] != previous[phase][field]
                   for phase in ("prefill", "decode") for field in ("dma_calls", "dma_bytes")):
                raise ValueError(f"DMA changed at prompt {index + 1}")
            results[index] = row
    if (core_hash, model_hash) != (digest(args.core_dir / "core.bin"), digest(args.model_image)):
        raise ValueError("candidate artifacts changed while running the holdout")
    receipt = dict(core_sha256=core_hash, model_sha256=model_hash,
                   verified_questions=len(results), questions=results)
    (args.out / "verified.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"Verified {len(results)} exact answers and logits with unchanged DMA.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--core-dir", type=Path, default=BUILD)
    parser.add_argument("--layout", choices=LAYOUTS, default="canonical")
    parser.add_argument("--model-image", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--prompts", type=Path, default=Path("tests/fixtures/holdout.txt"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=4)
    run(parser.parse_args())
