"""Exercise the standard transport loops of the actual native link in Peddle."""
import argparse
import json
from pathlib import Path

from tools.peddle import Machine


def check_standard(bundle):
    manifest = json.loads((bundle / "bundle.json").read_text())
    if manifest["transport_mode"] != "reu":
        raise ValueError("this fixture models the standard REU port only")
    machine = Machine()
    try:
        labels = (bundle / "probe.lbl").read_text()
        machine.symbols = {name[1:]: int(addr, 16)
                           for _, addr, name in map(str.split, labels.splitlines())}
        prg = (bundle / "PROBE.PRG").read_bytes()
        load = int.from_bytes(prg[:2], "little")
        machine.ram[load:load + len(prg) - 2] = prg[2:]
        src = machine.symbols["__PROBE_LOAD__"]
        dst = machine.symbols["__PROBE_RUN__"]
        size = machine.symbols["__PROBE_SIZE__"]
        machine.ram[dst:dst + size] = machine.ram[src:src + size]
        sample = (bundle / "sample.bin").read_bytes()
        far = manifest["sample_offset"]
        assert machine.run("seed")[4] & 1 == 0
        assert bytes(machine.reu[far:far + len(sample)]) == sample
        for lane, transfers in enumerate((1, 16, 4096, 0)):
            machine.put("lane", lane)
            machine.run("poison")
            assert machine.run("verify")[4] & 1
            stats = machine.run("copy_lane", instruction_limit=1_000_000)
            assert stats[4] & 1 == 0 and stats[2] == transfers
            assert stats[3] == (len(sample) if transfers else 0)
            assert machine.run("verify")[4] & 1 == 0
        print("Native-linked transport loops check all 4 KiB in Peddle at 1/16/4096/0 DMA operations.")
    finally:
        machine.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    check_standard(args.bundle)
