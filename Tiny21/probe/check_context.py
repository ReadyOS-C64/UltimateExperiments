"""Run the linked context-boundary probe in Peddle with a fresh REU cache."""
import argparse
import json
from pathlib import Path

from probe.check_local import load_native, seed_pal_clock
from tools.peddle import Machine
from tools.run_peddle import STEP_LIMIT


def check(bundle):
    manifest = json.loads((bundle / "bundle.json").read_bytes())
    if not manifest.get("context_test"):
        raise ValueError("build the bundle with --context-test")
    model = (bundle / "MODEL.BIN").read_bytes()
    machine = Machine()
    try:
        load_native(machine, bundle)
        seed_pal_clock(machine)
        machine.preload(model)
        machine.put("reu_banks", 32)
        assert not machine.run("model_open")[4] & 1
        sentinels = [0x80000 + layer * 0x8000 + 128 * 200 for layer in range(4)]
        for address in sentinels:
            machine.reu[address] = 0x5a

        for index, (question, answer) in enumerate(zip(
                manifest["questions"], manifest["expected_answers"], strict=True)):
            machine.put("question_id", index)
            stats = machine.run("run_question", instruction_limit=128 * STEP_LIMIT)
            assert not stats[4] & 1, (index, stats)
            start = manifest["answer_records"][index]
            record = bytes(machine.ram[start:start + 138])
            assert record[:2] == bytes((0xa5, len(answer)))
            assert record[10:10 + len(answer)] == answer.encode("ascii")
            positions = len(question) + 1 + len(answer)
            assert machine.get("token_pos", 1) == positions
            if index == 0:
                assert positions == record[137] == 128
            assert all(machine.reu[address] == 0x5a for address in sentinels)
            assert bytes(machine.reu[:len(model)]) == model
            print(json.dumps(dict(question=question, answer=answer, context_positions=positions,
                                  cpu_cycles=stats[1], dma_calls=stats[2], dma_bytes=stats[3],
                                  next_token_rejected=index == 0)), flush=True)
    finally:
        machine.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    check(parser.parse_args().bundle)
