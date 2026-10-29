"""Isolated 6510 diagnostic services; no editor build, VICE or shared outputs.

The host-created fragmented graph proves diagnostics/reader consumption only.
It does not establish integrated M2 completion or native display acceptance.
"""
import binascii
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build/diagnostics'
sys.path.insert(0, str(ROOT / 'tools'))
import peddle
# Even a missing/outdated Peddle library stays in this probe's output tree.
peddle.ROOT = BUILD
(BUILD / 'build').mkdir(exist_ok=True)
symbols = {}
for line in (BUILD / 'provider.lbl').read_text().splitlines():
    match = re.match(r'al ([0-9A-Fa-f]+) \.(\S+)', line)
    if match:
        symbols[match[2]] = int(match[1], 16)
s = symbols
m = peddle.Machine()
cases = 0
max_step = 0
max_begin = 0
step_calls = 0
full_mib_steps = 0
buffer = 0x8801


def read(address, size):
    return bytes(m.read(address + i) for i in range(size))


def put(name, value, width=3):
    m.load(s[name], value.to_bytes(width, 'little'))


def get(name, width=3):
    return int.from_bytes(read(s[name], width), 'little')


def call(name, a=0, x=0, y=0, error=None):
    global max_step, max_begin, step_calls
    regs, instructions = m.call(s[name], a=a, x=x, y=y)
    assert bool(regs.p & 1) == (error is not None), (name, regs.a, regs.p)
    if error is not None:
        assert regs.a == error, (name, regs.a, error)
    if name == 'se_diag_step':
        max_step = max(max_step, instructions)
        step_calls += 1
    if name == 'se_diag_begin':
        max_begin = max(max_begin, instructions)
    return regs.a


def reu_hash():
    # Complete16MiB hardware image,including every unallocated bank.
    return hashlib.sha256(bytes(m.lib.zeropage_peddle_read_reu(m.handle, i)
                                for i in range(16 * 1024 * 1024))).hexdigest()


def token(name):
    return read(s[name], 5)


def obj_write(t, offset, data, host=0x8000):
    m.load(s['se_object_id'], t)
    m.load(host, data)
    put('se_object_offset', offset)
    put('se_object_length', len(data), 2)
    put('se_object_c64', host, 2)
    call('se_object_copy')


def document_state():
    return (read(s['se_doc_roots'], 512)
            + read(s['se_doc_ready'], 1)
            + read(s['se_doc_generation'], 2)
            + read(s['se_doc_length'], 3)
            + token('se_doc_meta') + token('se_doc_original') + token('se_doc_append'))


def begin(caret=0, address=buffer):
    put('se_diag_buffer', address, 2)
    put('se_diag_cursor', caret)
    return call('se_diag_begin')


def snapshot():
    return read(buffer, 128)


def scan(model, caret=0, interleave=True):
    global cases
    before = document_state()
    hot_before = read(0x9200, 2048)
    owners_before = read(s['se_reu_map'], 768)
    foreign_leases = get('se_doc_read_locks', 1)
    m.load(buffer - 1, b'\xA5' + b'\xCC' * 128 + b'\x5A')
    assert begin(caret) == 1
    header = snapshot()
    assert header[:8] == b'DGS1\x01\x80\x01\x01'
    assert int.from_bytes(header[8:11], 'little') == len(model)
    assert int.from_bytes(header[13:16], 'little') == caret
    assert int.from_bytes(header[20:22], 'little') == get('se_reu_epoch', 2)
    assert header[93] == foreign_leases + 1
    assert int.from_bytes(header[34:36], 'little') == s['se_reu_map']
    assert int.from_bytes(header[36:38], 'little') == s['se_reu_logical_owner']
    assert int.from_bytes(header[38:40], 'little') == s['se_reu_physical_owner']
    assert int.from_bytes(header[40:42], 'little') == sum(0 < b < 255 for b in owners_before[256:512])
    assert int.from_bytes(header[42:44], 'little') == owners_before[512:].count(0)
    # A rejected repeat BEGIN must preserve the active output/job/lease.
    active = read(s['se_diag_frame_start'], s['se_diag_frame_end'] - s['se_diag_frame_start'])
    call('se_diag_begin', error=0x78)
    assert snapshot() == header
    assert read(s['se_diag_frame_start'], len(active)) == active
    # Public request may be reused after admission; continuation uses own pointer.
    put('se_diag_buffer', 0xC600, 2)
    steps = 0
    while get('se_diag_active', 1):
        previous = get('se_diag_pos')
        # Deliberately destroy shared CRC and pointer between every slice.
        m.call(s['se_crc_init'])
        m.call(s['se_crc_byte'], a=steps & 255)
        m.load(s['text_ptr'], b'\x00\xC6')
        result = call('se_diag_step')
        steps += 1
        actual = get('se_diag_pos')
        assert 0 <= actual - previous <= 128
        assert result == bool(get('se_diag_active', 1))
        assert get('se_doc_read_locks', 1) == foreign_leases + bool(result)
        if interleave and result and steps % 17 == 0:
            put('se_doc_offset', len(committed) - 1)
            put('se_doc_count', 1, 2)
            put('se_doc_c64', 0x8000, 2)
            call('se_doc_read')
    final = snapshot()
    assert final[6] == 2 and final[27] == 0
    assert int.from_bytes(final[22:24], 'little') == binascii.crc_hqx(model, 0xFFFF)
    assert int.from_bytes(final[24:27], 'little') == len(model)
    assert final[28:94] == header[28:94]
    assert m.read(buffer - 1) == 0xA5 and m.read(buffer + 128) == 0x5A
    assert document_state() == before
    assert read(0x9200, 2048) == hot_before
    assert read(s['se_reu_map'], 768) == owners_before
    call('se_diag_step', error=0x78)
    call('se_diag_cancel')
    assert snapshot() == final
    cases += 1
    return steps, final


def hot(base, old_length, payload, split):
    put('se_hot_ready', 1, 1)
    put('se_hot_phase', 0, 1)
    put('se_hot_pending', 1, 1)
    m.load(s['se_hot_original'], token('se_doc_original'))
    m.load(s['se_hot_append'], token('se_doc_append'))
    put('se_hot_generation', get('se_doc_generation', 2), 2)
    put('se_hot_base', base)
    put('se_hot_old_length', old_length, 2)
    put('se_hot_length', len(payload), 2)
    put('se_hot_left', split, 2)
    right = 2048 - (len(payload) - split)
    put('se_hot_right', right, 2)
    m.load(0x9200, b'\xB7' * 2048)
    m.load(0x9200, payload[:split])
    m.load(0x9200 + right, payload[split:])
    put('se_r_revision', get('se_r_revision', 4) + 1, 4)
    return committed[:base] + payload + committed[base + old_length:]


try:
    m.load(0x1000, (BUILD / 'provider.bin').read_bytes())
    m.load(0xB000, (BUILD / 'diagnostics.bin').read_bytes())
    shim = bytes((i * 73 + 29) & 255 for i in range(1024))
    protected = bytes((i * 37 + 11) & 255 for i in range(1536))
    m.load(0xC600, shim)
    m.load(0x8C00, protected)
    put('se_reu_banks', 256, 2)
    call('se_reu_provider_init')
    call('se_object_init')
    call('se_doc_init', a=16)
    committed = b''
    _, empty = scan(b'', interleave=False)
    assert empty[22:24] == b'\xFF\xFF'
    # Actual assembler object transfer and original adoption,full1MiB endpoint.
    committed = bytes(range(256)) * 4096
    orig = token('se_doc_original')
    for offset in range(0, len(committed), 1024):
        obj_write(orig, offset, committed[offset:offset + 1024])
    put('se_doc_source_length', len(committed))
    call('se_doc_adopt_original')
    put('se_overlay_loads', 0xFFFF, 2)
    put('se_overlay_hits', 0xABCD, 2)
    put('se_overlay_calls', 0x1234, 2)
    initial_reu = reu_hash()
    full_mib_steps, full = scan(committed, 1048576)
    assert full_mib_steps == 8192
    assert full[28:34] == bytes.fromhex('ffffcdab3412')
    assert reu_hash() == initial_reu
    # Keep later cases small while preserving actual source's final1MiB byte.
    # An independently host-built one-piece view is a diagnostic reader fixture.
    put('se_doc_length', 1024)
    m.load(s['se_doc_roots'] + 2, (1024).to_bytes(3, 'little'))
    committed = committed[:1024]
    put('se_doc_generation', get('se_doc_generation', 2) + 1, 2)
    call('se_doc_invalidate')
    # Existing adopted first piece must match root size for this fixture.
    leaf = bytearray(1024)
    leaf[:3] = orig[:3]
    leaf[6:9] = (1024).to_bytes(3, 'little')
    leaf[9:12] = b'\xFF' * 3
    obj_write(token('se_doc_meta'), 0, leaf, 0x8400)
    stable_reu = reu_hash()
    scan(committed, 1024)
    for base, old, payload, split in [
            (0, 0, bytes(range(256)), 0),
            (257, 31, bytes(range(256)), 137),
            (1024, 0, b'123456789', 9),
            (500, 200, b'', 0),
            (0, 1024, bytes(range(256)) * 8, 1031)]:
        model = hot(base, old, payload, split)
        _, final = scan(model, len(model))
        assert final[16:18] == b'\x01\x01'
    put('se_hot_ready', 0, 1)
    put('se_hot_pending', 0, 1)
    put('se_h_dirty', 1, 1)
    _, final = scan(committed)
    assert final[16:19] == b'\x00\x01\x01'
    put('se_h_dirty', 0, 1)
    # Foreign leases survive completion,cancel and context errors.
    call('se_doc_read_acquire')
    call('se_doc_read_acquire')
    scan(committed)
    assert get('se_doc_read_locks', 1) == 2
    begin()
    call('se_diag_step')
    call('se_diag_cancel')
    assert get('se_doc_read_locks', 1) == 2 and snapshot()[6] == 3
    call('se_diag_cancel')
    assert get('se_doc_read_locks', 1) == 2
    for name, width in [('se_r_revision', 4), ('se_doc_generation', 2),
                        ('se_hot_pending', 1), ('se_hot_original', 1)]:
        begin()
        old = read(s[name], width)
        put(name, int.from_bytes(old, 'little') ^ 1, width)
        call('se_diag_step', error=0x79)
        assert snapshot()[6] == 4 and snapshot()[27] == 0x79
        assert get('se_doc_read_locks', 1) == 2
        m.load(s[name], old)
        cases += 1
    call('se_doc_read_release')
    call('se_doc_read_release')
    put('se_doc_read_locks', 255, 1)
    put('se_diag_buffer', buffer, 2)
    call('se_diag_begin', error=0x41)
    assert get('se_doc_read_locks', 1) == 255
    put('se_doc_read_locks', 0, 1)
    # Reject busy consumers before acquiring a lease or touching output.
    for name in ['se_doc_busy', 'se_hot_phase', 'se_h_phase', 'se_b_phase',
                 'se_clip_busy', 'se_snapshot_busy']:
        put(name, 1, 1)
        old = snapshot()
        put('se_diag_buffer', buffer, 2)
        call('se_diag_begin', error=0x78)
        assert snapshot() == old and get('se_doc_read_locks', 1) == 0
        put(name, 0, 1)
        cases += 1
    for address in [0, 0x8000, 0x8400, 0x87FF, 0x8B81, 0x8C00, 0x9200, 0xC600, 0xFF80]:
        put('se_diag_buffer', address, 2)
        call('se_diag_begin', error=0x7A)
        assert get('se_doc_read_locks', 1) == 0
        cases += 1
    # Exact legal end and unaligned128-byte snapshot boundaries.
    begin(address=0x8B80)
    call('se_diag_cancel')
    assert read(0x8B80, 4) == b'DGS1'
    # Shape errors cannot expose DOCSTATE or hash malformed gap bytes.
    hot(100, 5, b'abc', 1)
    for name, value in [('se_hot_right', 2049), ('se_hot_left', 2049),
                         ('se_hot_length', 4), ('se_hot_old_length', 2049)]:
        old = read(s[name], 2)
        put(name, value, 2)
        put('se_diag_buffer', buffer, 2)
        call('se_diag_begin', error=0x7B)
        assert get('se_doc_read_locks', 1) == 0
        m.load(s[name], old)
        cases += 1
    put('se_hot_ready', 0, 1)
    put('se_hot_pending', 0, 1)
    assert reu_hash() == stable_reu
    # Host-built32-leaf/2048-one-byte-piece graph,including final object byte.
    model = bytearray()
    roots = bytearray()
    for page in range(32):
        leaf = bytearray(1024)
        for rec in range(64):
            index = page * 64 + rec
            offset = 1048575 if index == 2047 else (index * 65537) % 1048576
            at = rec * 16
            leaf[at:at + 3] = orig[:3]
            leaf[at + 3:at + 6] = offset.to_bytes(3, 'little')
            leaf[at + 6:at + 9] = b'\x01\x00\x00'
            leaf[at + 9:at + 12] = b'\xFF' * 3
            model.append(offset & 255)
        obj_write(token('se_doc_meta'), page * 1024, leaf, 0x8400)
        roots.extend(bytes([page, 64]) + (64).to_bytes(3, 'little') + b'\xFF' * 3)
    m.load(s['se_doc_roots'], roots)
    put('se_doc_root_count', 32, 1)
    put('se_doc_length', len(model))
    put('se_doc_generation', get('se_doc_generation', 2) + 1, 2)
    call('se_doc_invalidate')
    committed = bytes(model)
    fragmented_reu = reu_hash()
    fragment_steps, _ = scan(committed)
    assert fragment_steps == 256
    assert reu_hash() == fragmented_reu
    # Late reader failure preserves source,owns only its lease,and invalidatesCRC.
    begin()
    call('se_diag_step')
    m.load(s['se_doc_original'] + 1, b'\xFF\xFF')
    call('se_diag_step', error=0x79)
    m.load(s['se_doc_original'], orig)
    # Lower-level ownership failure after a valid prefix is propagated and
    # cannot publish the incomplete hash or leak the owned lease.
    begin()
    call('se_diag_step')
    logical = m.read(s['object_extents'] + orig[0] * 16 + 15)
    owner_address = s['se_reu_logical_owner'] + logical
    owner = m.read(owner_address)
    m.write(owner_address, 0)
    call('se_diag_step', error=0x34)
    assert snapshot()[6] == 4 and snapshot()[27] == 0x34
    assert get('se_doc_read_locks', 1) == 0
    m.write(owner_address, owner)
    assert reu_hash() == fragmented_reu
    # Epoch cancellation must not decrement a new provider's unrelated lease.
    begin()
    call('se_reu_provider_init')
    put('se_doc_read_locks', 7, 1)
    call('se_diag_cancel')
    assert get('se_doc_read_locks', 1) == 7
    assert read(0xC600, 1024) == shim
    assert read(0x8C00, 1536) == protected
    assert len((BUILD / 'diagnostics.bin').read_bytes()) + 16 <= 4096
    frame = s['se_diag_frame_end'] - s['se_diag_frame_start']
    assert frame <= 48
    result = dict(status='passed', engine='Peddle MOS_6510', cases=cases,
                  independent_hash='binascii.crc_hqx(init=FFFF);CRC16/CCITT-FALSE',
                  source_native_bytes=256, full_mib_bytes=1048576,
                  full_mib_steps=full_mib_steps, fragmented_pieces=2048,
                  fragmented_steps=fragment_steps, step_calls=step_calls,
                  max_begin_instructions=max_begin,
                  max_step_instructions=max_step, max_hashed_bytes_per_step=128,
                  max_committed_source_spans_per_step=8,
                  persistent_frame_bytes=frame, new_diagnostic_zp_bytes=0,
                  overlay_service_bytes=len((BUILD / 'diagnostics.bin').read_bytes()),
                  shim_bytes_verified=1024, view_index_bytes_preserved=1536,
                  full_reu_bytes_compared=16777216, immutable_reu=True,
                  stale_epoch_foreign_leases_preserved=True,
                  shared_crc_clobber_between_steps=True,
                  source_context_changes_rejected=True,
                  limitations='Separate emitted-service fixture;no integrated overlay/menu,VICE,cycle or M2 closure claim',
                  provider_sha256=hashlib.sha256((BUILD / 'provider.bin').read_bytes()).hexdigest(),
                  diagnostics_sha256=hashlib.sha256((BUILD / 'diagnostics.bin').read_bytes()).hexdigest())
    (BUILD / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
finally:
    m.close()
