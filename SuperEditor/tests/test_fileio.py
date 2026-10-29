"""CPU-level boundary and failure tests; native 1581 semantics remain a gate."""
import hashlib
import json
from pathlib import Path
import random
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from fileio_fixture import FileIOFixture

checks = []
def check(name):
    checks.append(name)

f = FileIOFixture()
try:
    # Exhaustive one-byte filename domain, command-injection protection, both
    # devices and exact16 bound. Validation must never call ROM.
    rejected = set(b'"*,/:=?') | set(range(32)) | set(range(127, 161)) | {32}
    for b in range(256):
        f.name(bytes([b])); before = len(f.trace)
        f.call('se_io_validate', error=0x90 if b in rejected else None)
        assert len(f.trace) == before
    for data in [b'', b' '*16, b'x'*17, b'0:file', b'@a,b', b'a\rb']:
        f.name(data); f.call('se_io_validate', error=0x90)
    for dev in [0, 7, 10, 255]:
        f.set('se_io_device', dev); f.name(b'test')
        f.call('se_io_open_read', error=0x90)
        assert not f.channels
    for size in range(1,17):
        for position in range(size):
            f.name(b'A'*position+b'\xA0'+b'Z'*(size-position-1));before=len(f.trace)
            f.call('se_io_validate',error=0x90)
            assert len(f.trace)==before
    f.set('se_io_device', 9); f.name(b'Name\xc1\xda\xa1'*2)
    f.call('se_io_validate'); f.set('se_io_device', 8)
    check('exhaustive filename/device validation')

    rng = random.Random(1581)
    for size in [1, 2, 15, 16, 255, 256, 257, 511, 512, 1025, 65537]:
        data = rng.randbytes(size)
        f.name(b'mixed\xc1\xdA')
        f.fs.clear()
        f.call('se_io_create_write')
        assert f.read('se_io_mode') == b'\x02'
        pos = 0
        while pos < size:
            n = min(size-pos, rng.choice([1, 17, 127, 256]))
            f.m.load(0x8000, data[pos:pos+n]); f.set('se_io_count', n & 255)
            f.call('se_io_write_chunk')
            assert int.from_bytes(f.read('se_io_done', 2), 'little') == n
            assert f.selected_out is None
            pos += n
        f.call('se_io_close'); assert not f.channels
        assert bytes(f.fs[b'mixed\xc1\xda']) == data
        f.call('se_io_open_read')
        actual = bytearray()
        while not f.read('se_io_eof')[0]:
            f.set('se_io_count', rng.choice([1, 17, 127, 0]))
            f.call('se_io_read_chunk')
            n = int.from_bytes(f.read('se_io_done', 2), 'little')
            actual.extend(f.read(0x8000, n))
            assert f.selected_in is None
        assert actual == data
        f.call('se_io_read_chunk'); assert f.read('se_io_done', 2) == b'\0\0'
        f.call('se_io_close'); assert not f.channels
    check('binary streams1..65537 bytes, final EOI, page/chunk boundaries')

    f.name(b'absent'); f.call('se_io_open_read', error=0x93)
    assert f.read('se_io_dos_code') == b'\x3e' and not f.channels
    f.fs[b'existing'] = b'keep'; f.name(b'existing')
    f.call('se_io_create_write', error=0x93)
    assert f.fs[b'existing'] == b'keep' and not f.channels
    for rom in [0xFFC0, 0xFFC6, 0xFFC9, 0xFFCF, 0xFFD2]:
        f.fs[b'test'] = b'abc'; f.name(b'test')
        if rom in (0xFFC0,):
            f.inject[rom] = 128
            f.call('se_io_open_read', error=0x92)
        elif rom in (0xFFC6, 0xFFCF):
            f.call('se_io_open_read'); f.inject[rom] = 128
            f.set('se_io_count', 3); f.call('se_io_read_chunk', error=0x92)
        else:
            f.name(b'output'); f.fs.pop(b'output', None)
            f.call('se_io_create_write'); f.inject[rom] = 128
            f.set('se_io_count', 3); f.call('se_io_write_chunk', error=0x92)
        assert not f.channels and f.selected_in is None and f.selected_out is None
        assert f.read('se_io_mode') == b'\0'
    check('missing/existing files and OPEN/CHKIN/CHKOUT/CHRIN/CHROUT cleanup')

    # Directory line pointers are hostile input and never memory destinations.
    def listing(rows):
        data = bytearray(b'\x01\x08')
        for blocks, text in rows:
            data.extend(b'\xff\xff'+blocks.to_bytes(2, 'little')+text+b'\0')
        return bytes(data+b'\0\0')
    f.directory = listing([(0, b'\x12"DISK NAME" ID 3D'),
                           (2, b' "HELLO" SEQ'), (9, b' "CODE" PRG'),
                           (1, b' "\xc1\xda" *SEQ<'), (500, b'BLOCKS FREE.')])
    f.call('se_io_directory_open'); found = []
    for _ in range(3):
        f.call('se_io_directory_next')
        n = f.read('se_io_dir_len')[0]
        if n:
            found.append((f.read('se_io_dir_name', n),
                          int.from_bytes(f.read('se_io_dir_blocks', 2), 'little'),
                          f.read('se_io_dir_flags')[0]))
    assert found == [(b'HELLO', 2, 0), (b'\xc1\xda', 1, 3)], found
    assert f.read('se_io_eof')[0]
    f.call('se_io_close'); assert not f.channels
    f.directory = listing([])
    f.call('se_io_directory_open'); f.call('se_io_directory_next')
    assert f.read('se_io_dir_len') == b'\0' and f.read('se_io_eof')[0]
    f.call('se_io_close')
    native_name = bytes(range(0xC1, 0xCF))+b'  '
    f.directory = listing([(257,b'     "'+native_name+b'"     SEQ   '),
                           (4,b'"'+b'a'*17+b'" SEQ')])
    f.call('se_io_directory_open'); f.call('se_io_directory_next')
    assert f.read('se_io_dir_name',16) == native_name
    assert f.read('se_io_dir_blocks',2) == b'\x01\x01'
    f.call('se_io_directory_next'); assert f.read('se_io_dir_len') == b'\0'
    f.call('se_io_close')
    for malformed in [b'\x01', b'\x01\x08\x01\x01\x00\x00unterminated']:
        f.directory = malformed
        if len(malformed) == 1:
            f.call('se_io_directory_open', error=0x94)
        else:
            f.call('se_io_directory_open'); f.call('se_io_directory_next',error=0x94)
        assert not f.channels
    f.directory = listing([(1, b'x'*83)])
    f.call('se_io_directory_open'); f.call('se_io_directory_next', error=0x95)
    assert not f.channels
    f.directory = listing([(i, b'"ignore" PRG') for i in range(65)] + [(1,b'"ok" SEQ')])
    f.call('se_io_directory_open')
    f.call('se_io_directory_next', error=0x95)
    assert f.read('se_io_mode') == b'\x03' and 5 in f.channels
    f.call('se_io_directory_next', error=0x95)
    f.call('se_io_directory_next')
    assert f.read('se_io_dir_name', 2) == b'ok'
    f.call('se_io_abort'); assert not f.channels
    check('bounded binary directory, SEQ filter, splat/lock,32-line yield, malformed limit')

    f.fs = {b'target': b'old', b'occupied': b'unrelated'}
    f.name(b'occupied'); f.call('se_io_create_temp', error=0x93)
    f.call('se_io_scratch_owned', error=0x96)
    assert f.fs[b'occupied'] == b'unrelated'
    f.name(b'se000001t'); f.call('se_io_create_temp')
    f.m.load(0x8000, b'new\0\r\x93'); f.set('se_io_count', 6)
    f.call('se_io_write_chunk'); f.call('se_io_close')
    assert f.read('se_io_owned_temp') == b'\x01'
    f.name(b'target'); f.name(b'occupied', other=True)
    f.call('se_io_make_backup', error=0x93)
    assert f.read('se_io_owned_backup') == b'\0'
    f.name(b'se000001b', other=True); f.call('se_io_make_backup')
    assert f.fs[b'se000001b'] == b'old' and b'target' not in f.fs
    f.name(b'se000001t'); f.name(b'target', other=True); f.call('se_io_rename')
    assert f.read('se_io_owned_temp') == b'\0'
    assert f.fs[b'target'] == b'new\0\r\x93'
    f.name(b'occupied') # scratch ignores arbitrary input and uses stored capability
    f.call('se_io_scratch_owned', a=1)
    assert f.read('se_io_owned_backup') == b'\0'
    assert b'se000001b' not in f.fs and f.fs[b'occupied'] == b'unrelated'
    f.call('se_io_scratch_owned', a=1, error=0x96)
    f.name(b'empty'); f.call('se_io_create_temp')
    f.call('se_io_close',error=0x98)
    assert f.read('se_io_owned_temp')==b'\x01'
    f.call('se_io_scratch_owned');assert b'empty' not in f.fs
    f.name(b'se000002t'); f.call('se_io_create_temp'); f.call('se_io_abort')
    f.name(b'occupied'); f.call('se_io_scratch_owned')
    assert b'se000002t' not in f.fs and f.fs[b'occupied'] == b'unrelated'
    check('collision-safe temp/backup capabilities, exact rename, owned-only scratch')

    for response, error in [(b'99, TEST,00,00\r',0x93), (b'x0, INVALID\r',0x94),
                            (b'00xBAD\r',0x94), (b'00,'+b'x'*150,0x95)]:
        f.dos = response; f.call('se_io_status', error=error)
        assert 6 not in f.channels and f.selected_in is None
    check('DOS diagnostics, malformed/truncated display, bounded status drain')
    result = dict(pass_=True, checks=checks,
                  provider_sha256=hashlib.sha256((ROOT/'build/fileio/provider.bin').read_bytes()).hexdigest(),
                  bytes=(ROOT/'build/fileio/provider.bin').stat().st_size,
                  bss_end=f.s['__BSS_RUN__']+f.s['__BSS_SIZE__'],
                  rom_calls=len(f.trace), scope='emitted CPU with modeled ROM/DOS boundary; no native IEC proof')
    (ROOT/'build/fileio/result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
finally:
    f.close()
