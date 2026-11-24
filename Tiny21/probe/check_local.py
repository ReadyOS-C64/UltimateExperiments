"""Exercise native-linked CRC and screen clock formatting under Peddle."""
import argparse
import ctypes as C
import os
import subprocess
from pathlib import Path
import struct
import zlib

from tools.peddle import Machine


def check_uci(bundle, symbols, program, expected_size, *, slot=0):
    root = Path(__file__).resolve().parent.parent
    source = root / "third_party/peddle/Peddle"
    dylib = bundle / "uci-fixture.so"
    env = dict(os.environ)
    env.setdefault("DEVELOPER_DIR", "/Library/Developer/CommandLineTools")
    subprocess.run(["c++", "-std=c++20", "-O2", "-shared", "-fPIC",
                    "-I" + str(source), "-o", str(dylib),
                    str(root / "probe/uci_fixture.cpp"),
                    *(str(path) for path in sorted(source.glob("*.cpp")))],
                   env=env, check=True)
    fixture = C.CDLL(str(dylib.resolve()))
    fixture.test_uci.argtypes = (C.c_char_p, C.c_uint, *([C.c_uint16] * 5),
                                C.c_uint, C.c_uint, C.c_uint, C.POINTER(C.c_uint8))
    for mode, expected in ((0, (0, 4, 48, 48, 4, 1, 1)),
                           (1, (1, 2, 48, 48, 3, 0, 1)),
                           (2, (1, 3, 48, 50, 4, 1, 1))):
        result = (C.c_uint8 * 7)()
        status = fixture.test_uci(
            program, len(program), *(symbols[name] for name in
                                    ("clock_start", "load_model_file", "dos_stage", "dos_status")),
            symbols.get("requested_model", 0), slot, expected_size, mode, result)
        assert status == 0 and tuple(result) == expected, (mode, status, tuple(result))
    print("Native UCI passed async multi-block reply, size mismatch, and LOAD_REU failure/close.")
    fixture.test_turbo.argtypes = (C.c_char_p, C.c_uint, *([C.c_uint16] * 4),
                                  C.c_uint, C.POINTER(C.c_uint32))
    for mode, readback, rejected in ((0, 0x8f, 0), (3, 0x8f, 1), (4, 0xff, 1)):
        result = (C.c_uint32 * 4)()
        status = fixture.test_turbo(
            program, len(program), *(symbols[name] for name in
                                    ("clock_start", "turbo_start", "turbo_restore", "turbo_sample")),
            mode, result)
        assert status == 0 and tuple(result[:2]) == (rejected, readback), tuple(result)
        assert result[3] == (0xff if mode == 4 else 1), tuple(result)
    print("Modeled turbo control accepts 64 MHz, rejects 48 MHz and disabled register, and restores setting.")


def load_native(machine, bundle):
    labels = bundle / "probe.lbl"
    machine.symbols = {name[1:]: int(addr, 16)
                       for _, addr, name in map(str.split, labels.read_text().splitlines())}
    prg = (bundle / "PROBE.PRG").read_bytes()
    addr, = struct.unpack_from("<H", prg)
    machine.ram[addr:addr + len(prg) - 2] = prg[2:]
    src = machine.symbols["__PROBE_LOAD__"]
    dst = machine.symbols["__PROBE_RUN__"]
    length = machine.symbols["__PROBE_SIZE__"]
    machine.ram[dst:dst + length] = machine.ram[src:src + length]
    bss = machine.symbols["__PROBEBSS_RUN__"]
    bss_size = machine.symbols["__PROBEBSS_SIZE__"]
    machine.ram[bss:bss + bss_size] = bytes(bss_size)
    return bytes(machine.ram[dst:dst + length])


def seed_pal_clock(machine):
    """Install a static coherent CIA2 sample for Peddle control-flow tests."""
    machine.ram[0xdd04:0xdd08] = [0, 0x12, 0xff, 0xff]
    machine.ram[0xdd0e:0xdd10] = [1, 0x41]
    machine.put("clock_rate", 985248, 4)


def check(bundle):
    machine = Machine()
    try:
        program = load_native(machine, bundle)
        data = (bundle / "MODEL.BIN").read_bytes()
        machine.preload(data)
        machine.put("reu_banks", 32)
        stats = machine.run("verify_model_image", instruction_limit=12_000_000)
        assert stats[4] & 1 == 0 and stats[3] == len(data), stats
        assert machine.get("model_crc", 4) == zlib.crc32(data)
        assert machine.run("model_open")[4] & 1 == 0
        stats = machine.run("check_resident_model", instruction_limit=12_000_000)
        assert stats[4] & 1 == 0 and stats[3] == len(data) + 272, stats
        machine.reu[0] ^= 1
        stats = machine.run("check_resident_model")
        assert stats[4] & 1 and stats[3] == 272, stats
        machine.reu[0] ^= 1

        machine.reu[-1] = 4  # unowned scratch remains outside the hash
        machine.reu[len(data) - 1] ^= 0x80
        stats = machine.run("check_resident_model", instruction_limit=12_000_000)
        assert stats[4] & 1 and stats[3] == len(data) + 272, stats
        machine.reu[len(data) - 1] ^= 0x80

        for rate in (985248, 1022727):
            machine.put("clock_rate", rate, 4)
            for ticks, expected in (
                (0, b"000.000S"), (rate + rate * 13 // 16, b"001.812S"),
                (123 * rate + (rate + 1) // 2, b"123.500S")
            ):
                machine.put("clock_elapsed", ticks, 4)
                machine.ram[0xf0:0xf2] = [0, 4]
                machine.run("format_time")
                assert bytes(machine.ram[0x400:0x408]) == expected, (rate, ticks, expected)
        print(f"Native-linked CRC and corruption detection, model admission, and PAL/NTSC rendering passed "
              f"({len(data):,} DMA bytes, {stats[2]} CRC DMA transfers).")
        check_uci(bundle, machine.symbols, program, len(data))
    finally:
        machine.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    check(args.bundle)
