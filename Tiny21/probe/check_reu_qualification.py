"""Verify the cold REU qualification, including restoration with aliased banks."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import random

from probe.check_local import load_native
from probe.physical import decode_reu_qualification
from tools.peddle import Machine


def check(bundle):
    manifest = json.loads((bundle / "bundle.json").read_text())
    mailbox = manifest["reu_qualification_mailbox"]
    machine = Machine()
    try:
        load_native(machine, bundle)
        machine.preload(random.Random(6510).randbytes(len(machine.reu)))
        model = (bundle / "MODEL.BIN").read_bytes()
        machine.preload(model)
        digest = sha256(machine.reu).hexdigest()
        stats = machine.run("qualify_reu")
        assert not stats[4] & 1, stats
        assert stats[2:4] == (208, 3328), stats
        result = decode_reu_qualification(bytes(machine.ram[mailbox:mailbox + 10]))
        assert sha256(machine.reu).hexdigest() == digest
        print(json.dumps({**result, "dma_calls": stats[2], "dma_bytes": stats[3],
                          "cpu_cycles": stats[1], "whole_reu_sha256": digest}), flush=True)

        for physical in (8 << 20, 512 << 10):
            machine.set_reu_capacity(physical)
            stats = machine.run("qualify_reu")
            assert stats[4] & 1, stats
            receipt = bytes(machine.ram[mailbox:mailbox + 10])
            assert receipt == b"T64R" + bytes((4, 0, 34, 0, 34, 0)), receipt.hex()
            assert sha256(machine.reu).hexdigest() == digest
            print(f"Rejected {physical >> 10} KiB aliased backing and restored all bytes.", flush=True)
        machine.set_reu_capacity(len(machine.reu))
        machine.put("reu_banks", 32)
        assert not machine.run("model_open")[4] & 1
    finally:
        machine.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    check(parser.parse_args().bundle)
