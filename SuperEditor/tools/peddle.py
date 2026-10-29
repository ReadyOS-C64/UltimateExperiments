"""Small ctypes adapter to the existing ZeroPage/Peddle CPU test wrapper.

Peddle is used for instruction-level assembly tests, never video/keyboard proof.
The external MIT-licensed source stays in zig64; build products are local.
"""
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VENDOR = Path(os.environ.get('PEDDLE_ROOT', str(ROOT.parent.parent/'zig64/third_party/peddle')))


class Registers(C.Structure):
    _fields_ = [('pc', C.c_uint16), ('pc0', C.c_uint16),
                ('sp', C.c_uint8), ('a', C.c_uint8), ('x', C.c_uint8),
                ('y', C.c_uint8), ('p', C.c_uint8),
                ('cycles', C.c_uint64), ('instructions', C.c_uint64)]


def library():
    sources = [VENDOR/'zeropage_peddle.cpp'] + [VENDOR/'Peddle'/f for f in
        ['Peddle.cpp', 'PeddleDebugger.cpp', 'PeddleDisassembler.cpp', 'StrWriter.cpp']]
    files = sources + list((VENDOR/'Peddle').glob('*.h')) + [VENDOR/'zeropage_peddle.h']
    fingerprint = hashlib.sha256(b''.join(p.read_bytes() for p in sorted(files))).hexdigest()
    extension = '.dylib' if sys.platform == 'darwin' else '.so'
    output = ROOT/f'build/libse_peddle{extension}'
    stamp = ROOT/'build/peddle-source.json'
    if not output.exists() or not stamp.exists() or json.loads(stamp.read_text())['sha256'] != fingerprint:
        command = ['clang++', '-std=c++20', '-O2', '-dynamiclib' if sys.platform == 'darwin' else '-shared',
                   '-fPIC', '-Wno-unused-parameter', '-Wno-unused-variable',
                   '-I'+str(VENDOR), '-I'+str(VENDOR/'Peddle'), *map(str, sources), '-o', str(output)]
        subprocess.run(command, check=True, capture_output=True, text=True)
        stamp.write_text(json.dumps(dict(sha256=fingerprint, source=str(VENDOR), command=command), indent=2)+'\n')
    lib = C.CDLL(str(output))
    lib.zeropage_peddle_create.restype = C.c_void_p
    for name in ['destroy', 'reset', 'clear_memory', 'step_instruction']:
        getattr(lib, 'zeropage_peddle_'+name).argtypes = [C.c_void_p]
    for name in ['set_pc', 'set_sp', 'set_a', 'set_x', 'set_y', 'set_p']:
        getattr(lib, 'zeropage_peddle_'+name).argtypes = [C.c_void_p, C.c_uint16]
    lib.zeropage_peddle_load.argtypes = [C.c_void_p, C.c_uint16, C.c_void_p, C.c_size_t]
    lib.zeropage_peddle_read.argtypes = [C.c_void_p, C.c_uint16]
    lib.zeropage_peddle_read.restype = C.c_uint8
    lib.zeropage_peddle_read_reu.argtypes = [C.c_void_p, C.c_uint32]
    lib.zeropage_peddle_read_reu.restype = C.c_uint8
    lib.zeropage_peddle_write.argtypes = [C.c_void_p, C.c_uint16, C.c_uint8]
    lib.zeropage_peddle_regs.argtypes = [C.c_void_p]
    lib.zeropage_peddle_regs.restype = Registers
    return lib


class Machine:
    def __init__(self):
        self.lib = library()
        self.handle = self.lib.zeropage_peddle_create()
        assert self.handle

    def close(self):
        if self.handle:
            self.lib.zeropage_peddle_destroy(self.handle)
            self.handle = None

    def load(self, address, data):
        data = bytes(data)  # accept immutable and mutable byte buffers
        self.lib.zeropage_peddle_load(self.handle, address, data, len(data))

    def read(self, address):
        return self.lib.zeropage_peddle_read(self.handle, address)

    def write(self, address, value):
        self.lib.zeropage_peddle_write(self.handle, address, value)

    def regs(self):
        return self.lib.zeropage_peddle_regs(self.handle)

    def call(self, address, a=0, x=0, y=0, limit=1_000_000):
        for name, value in [('a', a), ('x', x), ('y', y), ('p', 0x24), ('sp', 0xFD), ('pc', address)]:
            getattr(self.lib, 'zeropage_peddle_set_'+name)(self.handle, value)
        self.write(0x01FE, 0xFE)
        self.write(0x01FF, 0x02)
        initial = self.regs().instructions
        for _ in range(limit):
            if self.regs().pc == 0x02FF:
                return self.regs(), self.regs().instructions-initial
            self.lib.zeropage_peddle_step_instruction(self.handle)
        raise AssertionError(f'CPU routine did not return: PC=${self.regs().pc:04x}')
