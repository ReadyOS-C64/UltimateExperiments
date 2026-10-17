"""Only the native model ABI needed by the actual-runtime FORMAT assertions."""
import ctypes as C
from pathlib import Path

L = C.CDLL(str(Path(__file__).resolve().parent / 'model/format-peddle.dylib'))
ptr = C.c_void_p
class Regs(C.Structure):
    _fields_ = [('pc', C.c_uint16), ('sp', C.c_uint8), ('a', C.c_uint8),
                ('x', C.c_uint8), ('y', C.c_uint8), ('p', C.c_uint8),
                ('cycles', C.c_uint64), ('instructions', C.c_uint64)]
class Result(C.Structure):
    _fields_ = [('regs', Regs), ('status', C.c_uint), ('stack', C.c_uint8)]
for name, ret, args in [
    ('dos64_create', ptr, []), ('dos64_destroy', None, [ptr]),
    ('dos64_load', None, [ptr, C.c_uint16, ptr, C.c_size_t]),
    ('dos64_poke', None, [ptr, C.c_uint16, C.c_uint8]),
    ('dos64_peek', C.c_uint8, [ptr, C.c_uint16]),
    ('dos64_set_regs', None, [ptr, Regs]),
    ('dos64_run', Result, [ptr, C.c_uint16, C.c_uint64]),
    ('dos64_enable_reu', None, [ptr]),
    ('bulk_reu_seed', None, [ptr, C.c_uint32, ptr, C.c_uint32]),
    ('dos64_reu_read', C.c_uint8, [ptr, C.c_uint32, ptr, C.c_size_t]),
    ('dos64_reu_fail_after', None, [ptr, C.c_uint64, C.c_uint32]),
]:
    f = getattr(L, name)
    f.restype, f.argtypes = ret, args
