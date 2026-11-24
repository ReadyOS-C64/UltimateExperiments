"""Reusable Peddle session with direct block access to model REU and RAM."""

import ctypes as C
from pathlib import Path

BUILD = Path(__file__).resolve().parents[1] / "build"


class Machine:
    lib = C.CDLL(str(BUILD / "peddle.so"))
    lib.tiny_new.restype = C.c_void_p
    lib.tiny_free.argtypes = (C.c_void_p,)
    lib.tiny_ram.argtypes = lib.tiny_reu.argtypes = (C.c_void_p,)
    lib.tiny_ram.restype = C.POINTER(C.c_ubyte * 65536)
    lib.tiny_reu.restype = C.POINTER(C.c_ubyte * (16 << 20))
    lib.tiny_set_reu_capacity.argtypes = (C.c_void_p, C.c_uint)
    lib.tiny_set_reu_capacity.restype = None
    lib.tiny_enable_group4_workspace.argtypes = (C.c_void_p,)
    lib.tiny_enable_group4_workspace.restype = None
    lib.tiny_enable_group8_dma.argtypes = (C.c_void_p,)
    lib.tiny_enable_group8_dma.restype = None
    lib.tiny_set_workspace.argtypes = (C.c_void_p, C.c_uint, C.c_uint, C.c_uint)
    lib.tiny_set_workspace.restype = None
    lib.tiny_keyboard.argtypes = (C.c_void_p,)
    lib.tiny_keyboard.restype = C.POINTER(C.c_ubyte * 8)
    lib.tiny_enable_cycle_profile.argtypes = (C.c_void_p,)
    lib.tiny_enable_cycle_profile.restype = C.POINTER(C.c_uint64 * 65536)
    lib.tiny_run.argtypes = (C.c_void_p, C.c_uint16, C.c_uint64,
                            C.POINTER(C.c_uint64), C.c_uint8, C.c_uint8, C.c_uint32, C.c_uint32)
    def __init__(self, core_dir=BUILD):
        self.symbols = {name[1:]: int(addr, 16)
                        for _, addr, name in map(str.split, (core_dir / "core.lbl").read_text().splitlines())}
        self.ptr = self.lib.tiny_new()
        if "group4_dot" in self.symbols:
            self.lib.tiny_enable_group4_workspace(self.ptr)
        if "reu_group8_read" in self.symbols:
            self.lib.tiny_enable_group8_dma(self.ptr)
        self.lib.tiny_set_workspace(self.ptr, self.symbols.get("__WORK_START__", 0x5000),
                                    self.symbols.get("__SCORES_RUN__", 0),
                                    self.symbols.get("__SCORES_SIZE__", 0))
        self.ram = self.lib.tiny_ram(self.ptr).contents
        self.reu = self.lib.tiny_reu(self.ptr).contents
        code = (core_dir / "core.bin").read_bytes()
        self.ram[0x1000:0x1000 + len(code)] = code

    def preload(self, payload, offset=0):
        """Copy contiguous model bytes into the host device backing store."""
        if offset < 0 or offset + len(payload) > len(self.reu):
            raise ValueError("preload exceeds the modeled REU")
        C.memmove(C.addressof(self.reu) + offset, bytes(payload), len(payload))

    def close(self):
        self.lib.tiny_free(self.ptr)

    def set_reu_capacity(self, size):
        """Model physical address aliasing with a smaller REU."""
        if not (1 << 19) <= size <= len(self.reu) or size & (size - 1):
            raise ValueError("REU capacity must be a power of two from 512 KiB through 16 MiB")
        self.lib.tiny_set_reu_capacity(self.ptr, size)

    def keyboard_matrix(self):
        """Enable modeled CIA1 matrix reads and expose eight active-low columns."""
        return self.lib.tiny_keyboard(self.ptr).contents

    def cycle_profile(self):
        """Start a fresh per-instruction-address CPU cycle profile."""
        return self.lib.tiny_enable_cycle_profile(self.ptr).contents

    def put(self, name, value, size=1):
        addr = self.symbols[name]
        self.ram[addr:addr + size] = value.to_bytes(size, "little")

    def get(self, name, size, signed=False):
        addr = self.symbols[name]
        return int.from_bytes(bytes(self.ram[addr:addr + size]), "little", signed=signed)

    def run(self, label, accumulator=0, *, instruction_limit=2_000_000, x=0,
            model_length=0, model_base=0):
        if not 0 <= model_length <= 0x80000 or model_base not in (0, 0x100000):
            raise ValueError("guard model length exceeds the owned model region")
        stats = (C.c_uint64 * 9)()
        status = self.lib.tiny_run(self.ptr, self.symbols[label], instruction_limit, stats,
                                   accumulator, x, model_length, model_base)
        if status:
            error = {1: "instruction budget", 2: "unsupported REU command",
                     3: "unowned CPU write", 4: "stack guard",
                     5: "unowned CPU DMA", 6: "unowned REU DMA"}[status]
            raise AssertionError(f"{label}: {error}, address=${stats[8]:06x}, PC=${stats[5]:04x}")
        self.accumulator = stats[6]
        self.stack_bytes = stats[7] if model_length else None
        return tuple(stats[:6])

    def transfer(self, far, address, size, direction=1, banks=32):
        self.put("reu_addr", far, 3)
        self.put("reu_ram", address, 2)
        self.put("reu_size", size, 2)
        self.put("reu_direction", direction)
        self.put("reu_banks", banks)
        return self.run("reu_transfer")

    def prepare(self, inputs):
        for label, shift in [("activation_lo", 0), ("activation_hi", 8)]:
            addr = self.symbols[label]
            self.ram[addr:addr + len(inputs)] = bytes((v >> shift) & 255 for v in inputs)
        self.put("dot_columns", len(inputs) & 255)
        self.last_stats = self.run("dot_prepare")

