"""Compare the fixed-point reference with the original Tiny-2.1 C implementation."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from tools.oracle import Network, input_tokens

ROOT = Path(__file__).resolve().parents[1]


def compare(reference_dir, prompts_path):
    model = reference_dir / "TINY.BIN"
    network = Network(model.read_bytes())
    questions = prompts_path.read_text().splitlines()
    if not questions or any(not input_tokens(prompt) for prompt in questions):
        raise ValueError("supply nonempty questions")

    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    adapter = build / "float-trace"
    subprocess.run([os.environ.get("CC", "cc"), "-std=c90", "-O2", "-ffp-contract=off",
                    "-fno-fast-math", "-I", str(reference_dir), str(ROOT / "tests/float_trace.c"),
                    "-lm", "-o", str(adapter)], check=True)
    called = subprocess.run([str(adapter)], cwd=reference_dir, text=True,
                            input="\n".join(questions) + "\n", capture_output=True, check=True)
    lines = called.stdout.splitlines()
    if len(lines) != 2 * len(questions):
        raise RuntimeError("float trace has an unexpected number of records")

    results = []
    for index, prompt in enumerate(questions):
        golden, chosen = lines[2 * index:2 * index + 2]
        fixed = network.answer(prompt)
        tokens = input_tokens(prompt) + [1] + [ord(char) - 30 for char in golden]
        wanted = list(map(int, chosen.split()))
        if len(wanted) != len(tokens):
            raise RuntimeError(f"float trace token count does not match for {prompt!r}")
        network.reset()
        actual = []
        for token in tokens:
            scores = network.step(token)
            actual.append(max(range(97), key=scores.__getitem__))
        misses = [p for p, (x, y) in enumerate(zip(wanted, actual)) if x != y]
        results.append(dict(question=prompt, reference=golden, fixed=fixed,
                            positions=len(tokens), mismatches=misses))
    total = sum(row["positions"] for row in results)
    matches = total - sum(len(row["mismatches"]) for row in results)
    exact = sum(row["reference"] == row["fixed"] for row in results)
    return dict(questions=len(questions), exact_answers=exact, teacher_forced_positions=total,
                teacher_forced_matches=matches, answers=results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference_dir", type=Path)
    parser.add_argument("prompts", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.reference_dir.resolve(), args.prompts), indent=2))
