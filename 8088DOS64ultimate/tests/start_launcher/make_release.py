"""Release-bound descriptor; rejects legacy images without native handoff ABI."""
import argparse
import struct
import zlib
from pathlib import Path


def descriptor(prg: bytes, labels: str) -> bytes:
    symbols = {}
    for line in labels.splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[0] == 'al':
            key, value = fields[2].lstrip('.'), int(fields[1], 16)
            if key not in {'dos64_native_start','dos64_native_loop','dos64_native_idle',
                           'dos64_native_nmi','dos64_native_config','dos64_native_config_end',
                           'hdc_config','hdc_config_end','dos64_loader_required'}:
                continue  # private and overlay-local symbols can repeat
            if key in symbols and symbols[key] != value:
                raise ValueError('conflicting symbol: '+key)
            symbols[key] = value
    def symbol(name):
        if name not in symbols:
            raise ValueError('missing native handoff ABI symbol: '+name)
        return symbols[name]
    if not 2 <= len(prg) <= 0xb801 or prg[:2] != b'\x01\x08':
        raise ValueError('invalid main PRG load range')
    def offset(name, length, low, high):
        addr = symbol(name)
        at = addr-0x0801+2
        if not low <= addr or addr+length > high or not 2 <= at <= len(prg)-length:
            raise ValueError('invalid symbol range: '+name)
        return at
    entries = [symbol('dos64_native_'+n) for n in ('start','loop','idle')]
    if any(not 0x0801 <= a < min(0x4000,0x0801+len(prg)-2) for a in entries):
        raise ValueError('entry outside resident MAIN')
    nmi = symbol('dos64_native_nmi')
    if nmi != 0x5882 or nmi-0x0801+2 >= len(prg) or prg[nmi-0x0801+2] != 0x40:
        raise ValueError('ABI1 requires resident RTI at5882')
    n = offset('dos64_native_config',142,0x7000,0x8000)
    h = offset('hdc_config',140,0x7000,0x8000)
    f = offset('dos64_loader_required',1,0x0801,0x4000)
    if symbol('dos64_native_config_end')-symbol('dos64_native_config') != 142 or \
       symbol('hdc_config_end')-symbol('hdc_config') != 140:
        raise ValueError('configuration ABI size changed')
    spans = [(n,n+142),(h,h+140),(f,f+1)]
    if any(a < d and c < b for i,(a,b) in enumerate(spans) for c,d in spans[i+1:]):
        raise ValueError('overlapping patch spans')
    if f in [a-0x0801+2 for a in entries] or prg[f] != 0 or \
       prg[n:n+5] != b'D64N\0' or prg[h:h+5] != b'D64H\0':
        raise ValueError('main is not an unconfigured native template')
    out = bytearray(64)
    struct.pack_into('<4sBBHIIHHHHHHIII',out,0,b'D64L',1,1,64,len(prg),
                     zlib.crc32(prg),0x0801,len(prg)-2,*entries,nmi,n,h,f)
    struct.pack_into('<IIHBBHH',out,40,0x3e0000,0x3ff000,576,32,0x40,142,140)
    struct.pack_into('<I',out,60,zlib.crc32(out[:60]))
    return bytes(out)


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--prg',type=Path,required=True)
    p.add_argument('--labels',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    # No partial/stale descriptor is written on rejected inputs.
    data=descriptor(a.prg.read_bytes(),a.labels.read_text())
    a.output.write_bytes(data)
