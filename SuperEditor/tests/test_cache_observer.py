"""Actual hot RAM observer + R32 fault gate, on an immutable product fixture.

No private producer substitution, shared make or native claim. The host arms
the optional observer explicitly; it does not claim a semantic baseline exists.
Expected tuples/CRC come from canonical byte operations, never emitted code.
R2/universal publication and arena draining are deliberately separate gates.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import binascii
import ctypes as C
import hashlib
import json
import subprocess
import sys

import test_geos_editor as geos
import test_presentation_bypass as bypass

ROOT = geos.ROOT
DATA = geos.native_text('Ordinary source text.\rSecond source row.\r')
Q = geos.native_text('Q')[0]
WORKERS = ('styler', 'lexical', 'foldparse', 'foldfinish', 'foldctl',
           'geossema', 'geoslex', 'geosinln')
W_LOAD, W_STEP, W_INSERT, W_BACK, W_DELETE = range(1, 6)
W_LEFT, W_RIGHT, W_FLUSH, W_CANCEL = range(6, 10)


def integer(raw, at, width):
    return int.from_bytes(raw[at:at + width], 'little')


def event(ticket, revision, generation, position, deleted, inserted, *, kind=1,
          next_generation=None, next_revision=None):
    """Independent ABI1 event encoder; CRC16/CCITT-FALSE, marker excluded."""
    raw = bytearray(32)
    raw[0] = 0xA5
    raw[1] = kind
    for at, width, value in ((4, 4, ticket), (8, 4, revision),
                             (12, 4, revision + (kind == 1) if next_revision is None
                              else next_revision),
                             (16, 3, position), (19, 3, deleted),
                             (22, 3, inserted), (25, 2, generation),
                             (27, 2, generation if next_generation is None
                              else next_generation)):
        raw[at:at + width] = value.to_bytes(width, 'little')
    raw[29:31] = binascii.crc_hqx(raw[1:29] + raw[31:32], 0xFFFF).to_bytes(2, 'little')
    return bytes(raw)


def runner(out):
    """Existing CPU + read-only PC/DMA observer; no execution interception."""
    original = bypass.runner(out)
    path = out / 'runner.cpp'
    text = path.read_text()
    # Match the shared owner predicate prefix; the parser gate may append its
    # independently controlled typed53 initial-allocation exception.
    old = '(lo!=0x46 && lo!=0xfe'
    assert text.count(old) == 1
    # Universal source transactions may legitimately stash metadata3,
    # source/append4, clipboard5 and journal6. Record exact checked DMA spans, never mask
    # those entire banks; independently verify all committed source bytes.
    text = text.replace(old, '(lo!=3 && lo!=4 && lo!=5 && lo!=6 && lo!=0x46 && lo!=0xfe')
    needle = 'static void step(ZeroPagePeddle*m){auto r=zeropage_peddle_regs(m);'
    assert text.count(needle) == 1
    observer = r'''
static uint16_t ob_base=0,ob_bad=0,ob_pc=0,ob_address=0;
extern "C" void ob_ring(uint16_t base){ob_base=base;ob_bad=ob_pc=ob_address=0;}
extern "C" uint16_t ob_ring_get(unsigned n){return n==0?ob_bad:n==1?ob_pc:ob_address;}
static void ob_step(ZeroPagePeddle*m,uint16_t pc,uint8_t x,uint8_t y){if(!ob_base)return;
 auto op=zeropage_peddle_read(m,pc);if(op!=0xb9 && op!=0x99 && op!=0xbd && op!=0x9d)return;
 uint16_t base=zeropage_peddle_read(m,pc+1)|(zeropage_peddle_read(m,pc+2)<<8);
 if(base<ob_base || base>=ob_base+96)return;uint16_t a=base+((op==0xb9 || op==0x99)?y:x);
 if(a>=ob_base && a<ob_base+96)return;if(!ob_bad){ob_pc=pc;ob_address=a;}ob_bad++;}
'''
    text = text.replace(needle, observer + needle + 'ob_step(m,r.pc,r.x,r.y);')
    path.write_text(text)
    ext = '.dylib' if sys.platform == 'darwin' else '.so'
    target = out / ('observer-runner' + ext)
    subprocess.run(['clang++', '-std=c++20', '-O2',
        '-dynamiclib' if sys.platform == 'darwin' else '-shared', '-fPIC',
        '-I' + str(geos.grid.VENDOR), str(path),
        str(ROOT / ('build/libse_peddle' + ext)), '-o', str(target)], check=True)
    dll = C.CDLL(str(target))
    for name in ('gm_rom', 'gm_rom_count', 'gm_profile', 'gm_metric', 'gm_run',
                 'gm_idle', 'gm_read', 'gm_reu', 'fr_begin', 'fr_end', 'fr_mask',
                 'fr_bad', 'fr_writes', 'pb_config', 'pb_begin', 'pb_end',
                 'pb_get', 'pb_fault_get'):
        oldfn, newfn = getattr(original, name), getattr(dll, name)
        newfn.argtypes, newfn.restype = oldfn.argtypes, oldfn.restype
    dll.ob_ring.argtypes = [C.c_uint16]
    dll.ob_ring_get.argtypes = [C.c_uint]
    dll.ob_ring_get.restype = C.c_uint16
    return dll


class Gate:
    def __init__(self, out, fixture):
        self.out = out
        self.frozen, self.identity = geos.freeze(out, fixture)
        names = self.identity['names']
        assert len(names) >= 49 and 'hotcold' in names
        geos.grid.editor_fixture.ROOT = geos.grid.cpu_editor.ROOT = self.frozen
        geos.grid.editor_fixture.NAMES = geos.grid.cpu_editor.NAMES = names
        self.dll = runner(out)
        self.f = geos.Fixture(out, self.frozen, self.dll, True)
        for name in ('se_bc_arena', 'se_bc_ticket', 'se_bc_incarnation',
                     'se_bc_flags', 'se_bc_head', 'se_bc_tail', 'se_bc_count',
                     'se_bc_ring'):
            assert name in self.f.s, ('missing actual observer export', name)
        targets = [(n, 0xB010, 2, names.index(n) + 1) for n in WORKERS]
        self.targets = targets
        self.dll.pb_config(self.f.s['se_overlay_active'], len(targets),
            (C.c_uint16 * len(targets))(*(v[1] for v in targets)),
            (C.c_uint8 * len(targets))(*(v[2] for v in targets)),
            (C.c_uint8 * len(targets))(*(v[3] for v in targets)),
            (C.c_uint8 * (16 * len(targets)))())
        self.cases = []
        self.whole_reu_intervals = 0
        self.exact_dma_intervals = 0
        self.known = []

    def reu(self):
        b = C.create_string_buffer(16 * 1024 * 1024)
        self.dll.gm_reu(self.f.m.handle, len(b), b)
        return b.raw

    def queue(self):
        f = self.f
        return f.read(f.s['se_bc_arena'], 17), f.read(f.s['se_bc_ring'], 96)

    def stable(self):
        """Committed source/history/clipboard, excluding reader/request scratch."""
        f = self.f
        names = [('se_doc_meta', 15), ('se_doc_generation', 2),
                 ('se_doc_length', 3), ('se_h_current', 4), ('se_h_saved', 4),
                 ('se_h_end', 2), ('se_h_cursor', 2), ('se_h_counter', 4),
                 ('se_h_open_group', 1), ('se_h_fault', 1), ('se_clip_token', 5),
                 ('se_clip_length', 3), ('se_sel_mark', 1), ('se_sel_anchor', 3)]
        return f.read(f.s['se_doc_roots'], 512) + b''.join(
            f.read(f.s[n], w) for n, w in names)

    def guards(self, before, tag, *, unchanged=None):
        f = self.f
        assert self.reu() == before, (tag, 'whole16MiB changed')
        self.whole_reu_intervals += 1
        assert f.read(0xC600, 1024) == f.shim, (tag, 'ReadyOS shim')
        if unchanged is not None:
            assert self.stable() == unchanged, (tag, 'committed/history/clipboard changed')

    def hot(self, command, *, error=None):
        r = self.f.call('se_hot_call', command)
        assert bool(r.p & 1) == (error is not None), (command, hex(r.a), error)
        if error is not None:
            assert r.a == error, (command, hex(r.a), hex(error))
        return r

    def call(self, name, a=0, error=None):
        r = self.f.call(name, a)
        assert bool(r.p & 1) == (error is not None), (name, hex(r.a), error)
        if error is not None:
            assert r.a == error, (name, hex(r.a), hex(error))
        return r

    def audit_begin(self):
        names = ('se_reu_copy', 'se_reu_logical', 'se_reu_offset', 'se_reu_length',
                 'se_reu_map', 'se_reu_logical_owner', 'se_reu_physical_owner')
        before = self.reu()
        self.dll.fr_begin(*(self.f.s[n] for n in names))
        return before

    def audit_end(self, before, tag):
        self.dll.fr_end()
        assert not self.dll.fr_bad(), (tag, 'invalid/unexpected typed DMA stash')
        mask = C.create_string_buffer(len(before))
        self.dll.fr_mask(mask)
        after, allowed = self.reu(), mask.raw
        wanted = bytearray(before)
        start = allowed.find(b'\1')
        while start >= 0:
            end = allowed.find(b'\0', start)
            if end < 0:
                end = len(allowed)
            wanted[start:end] = after[start:end]
            start = allowed.find(b'\1', end)
        assert after == wanted, (tag, 'REU changed outside exact observed checked DMA spans')
        self.exact_dma_intervals += 1
        assert self.f.read(0xC600, 1024) == self.f.shim

    def consume(self):
        """Explicit test consumer acknowledgment, not an arena-drain claim."""
        f = self.f
        assert not f.get('se_bc_flags', 1) & 4
        f.put('se_bc_tail', f.get('se_bc_head', 1), 1)
        f.put('se_bc_count', 0, 1)

    def latest(self, head, expected, tag):
        f = self.f
        actual = f.read(f.s['se_bc_ring'] + head * 32, 32)
        assert actual == expected, (tag, actual.hex(), expected.hex())
        assert f.get('se_bc_head', 1) == (head + 1) % 3
        assert f.get('se_bc_count', 1) == 1
        assert f.get('se_bc_flags', 1) == 1

    def setup(self, position=5, armed=True, data=DATA):
        f = self.f
        f.source(data)
        f.typed(geos.native_text('syntax plain'))
        assert f.get('se_render_caps', 1) == 0
        f.position(position)
        # Warm C6 deliberately, then sample to distinguish per-key producer
        # work from a legal first image admission.
        if position:
            self.hot(W_LEFT)
            self.hot(W_RIGHT)
        f.m.load(f.s['se_bc_arena'], bytes(17))
        f.m.load(f.s['se_bc_ring'], bytes([0xA7]) * 96)
        if armed:
            result, _ = f.fast_call(f.s['se_object_create'], a=0x53, x=1)
            assert not result.p & 1, ('actual optional typed53 allocation', result.a)
            token = f.read(f.s['se_object_id'], 5)
            assert f.m.read(f.s['object_owner'] + token[0]) == 0x53
            f.m.load(f.s['se_bc_arena'], token)
        f.put('se_bc_incarnation', 1, 4)
        f.put('se_bc_flags', int(armed), 1)
        assert f.merged() == data

    def sampled(self, fn):
        self.dll.pb_begin()
        before = self.f.get('se_reu_dma_calls', 2)
        try:
            fn()
        finally:
            self.dll.pb_end()
        counts = {v[0]: self.dll.pb_get(i) for i, v in enumerate(self.targets)}
        return (self.f.get('se_reu_dma_calls', 2) - before) & 0xFFFF, counts

    def remove(self, name):
        f = self.f
        image = f.assets[name]
        # Catalog memo bit7 is not a physical C/R slot bit.
        slot, identity = image[5], image[6]
        candidates = [i for i in range(f.s['se_overlay_capacity'])
            if f.m.read(f.s['se_overlay_ids'] + i) == identity
            and f.m.read(f.s['image_slot'] + i) & 1 == slot]
        assert len(candidates) == 1, (name, slot, identity, candidates)
        at = candidates[0]
        f.m.write(f.s['se_overlay_ids'] + at, 0)
        f.m.write(f.s['se_overlay_active'] + slot, 0)
        return at, identity

    def restore(self, saved):
        at, identity = saved
        self.f.m.write(self.f.s['se_overlay_ids'] + at, identity)

    def record(self, tag, **fields):
        self.cases.append(dict(tag=tag, **fields))
        (self.out / 'progress.json').write_text(json.dumps(self.cases, indent=2) + '\n')

    def local_edits(self):
        f = self.f
        self.setup()
        wanted = DATA
        gen = f.get('se_doc_generation', 2)
        revision = f.get('se_r_revision', 4)
        stable, reu = self.stable(), self.reu()
        operations = [('insert', lambda: f.key(Q), 5, 0, bytes([Q])),
                      ('backspace', lambda: f.key(0x14), 5, 1, b''),
                      ('delete', lambda: f.command(4), 5, 1, b'')]
        for index, (tag, fn, p, d, inserted) in enumerate(operations):
            dma, parsers = self.sampled(fn)
            wanted = wanted[:p] + inserted + wanted[p + d:]
            assert f.merged() == wanted, (tag, 'actual canonical+gap bytes')
            assert not dma and not any(parsers.values()), (tag, dma, parsers)
            expected = event(index + 1, revision + index, gen, p, d, len(inserted))
            assert f.read(f.s['se_bc_ring'] + index * 32, 32) == expected, (
                tag, 'event', f.read(f.s['se_bc_ring'] + index * 32, 32).hex(), expected.hex())
            assert f.get('se_bc_count', 1) == index + 1
            assert f.get('se_bc_head', 1) == (index + 1) % 3
            assert f.get('se_bc_ticket', 4) == index + 1
            assert f.get('se_bc_flags', 1) == 1
            self.guards(reu, tag, unchanged=stable)
            self.record(tag, event=expected.hex(), dma_calls=dma, parser_entries=parsers)
        before = self.queue()
        dma, parsers = self.sampled(lambda: (self.hot(W_LEFT), self.hot(W_RIGHT)))
        assert self.queue() == before and f.merged() == wanted
        assert not dma and not any(parsers.values())
        self.guards(reu, 'movement-no-event', unchanged=stable)
        self.record('movement-no-event', dma_calls=dma)
        ring = self.queue()[1]
        f.key(Q)
        wanted = wanted[:5] + bytes([Q]) + wanted[5:]
        assert f.merged() == wanted
        assert f.get('se_bc_flags', 1) == 2 and f.get('se_bc_count', 1) == 3
        assert self.queue()[1] == ring, 'overflow overwrote unread event'
        self.guards(reu, 'fourth-edit-continues-LOST', unchanged=stable)
        self.record('fourth-edit-continues-LOST', ticket=f.get('se_bc_ticket', 4),
                    complete_ticket_chain=False)
        print('FIRST PASS: three real pending edits, exact events/CRC, movement0 and fourth-edit LOST; whole16MiB unchanged', flush=True)

    def disarmed_and_refusals(self):
        f = self.f
        self.setup(armed=False)
        before, reu, stable = self.queue(), self.reu(), self.stable()
        dma, parsers = self.sampled(lambda: f.key(Q))
        assert self.queue() == before and not dma and not any(parsers.values())
        assert f.merged() == DATA[:5] + bytes([Q]) + DATA[5:]
        self.guards(reu, 'disarmed-Plain', unchanged=stable)
        self.record('disarmed-Plain-no-observer-write/DMA/parser', dma_calls=dma, parser_entries=parsers)
        for p, command in ((0, W_BACK), (len(DATA), W_DELETE)):
            self.setup(p)
            before, reu, canonical = self.queue(), self.reu(), f.canonical()
            self.hot(command, error=0x72)
            assert self.queue() == before and f.canonical() == canonical
            self.guards(reu, 'boundary-refusal')
            self.record('boundary-refusal', position=p, command=command)
        for name, value in (('se_bc_head', 3), ('se_bc_tail', 255), ('se_bc_count', 4)):
            self.setup()
            f.put(name, value, 1)
            ring, reu, stable = self.queue()[1], self.reu(), self.stable()
            # The lower neighbor is live HOT scratch (through9D84), so an
            # accepted edit legitimately changes it. The upper unused tail
            # must remain exact; malformed unsigned indices would hit it.
            lo, hi = f.s['se_bc_ring'], f.s['se_bc_ring'] + 96
            assert lo == f.s['se_hot_state_end']
            neighbor = f.read(hi, 16)
            f.key(Q)
            assert f.merged() == DATA[:5] + bytes([Q]) + DATA[5:]
            assert f.get('se_bc_flags', 1) == 2 and self.queue()[1] == ring
            assert f.read(hi, 16) == neighbor
            self.guards(reu, 'malformed-queue', unchanged=stable)
            self.record('malformed-queue-LOST-no-index', field=name, value=value)

        self.setup()
        f.put('se_bc_ticket', 0xFFFFFFFE, 4)
        revision, generation = f.get('se_r_revision', 4), f.get('se_doc_generation', 2)
        reu, stable = self.reu(), self.stable()
        f.key(Q)
        assert f.read(f.s['se_bc_ring'], 32) == event(
            0xFFFFFFFF, revision, generation, 5, 0, 1)
        first = f.read(f.s['se_bc_ring'], 32)
        f.key(0x14)
        assert f.merged() == DATA
        assert f.get('se_bc_flags', 1) == 2 and f.get('se_bc_count', 1) == 1
        assert f.read(f.s['se_bc_ring'], 32) == first
        assert f.m.read(f.s['se_bc_ring'] + 32) == 0
        self.guards(reu, 'ticket-wrap-LOST', unchanged=stable)
        self.record('ticket-wrap-LOST-before-reusing-ticket', wrapped=f.get('se_bc_ticket', 4))

    def cold_faults(self):
        f = self.f
        self.setup(armed=False)
        saved = self.remove('hotcold')
        canonical, stable, reu, queue = f.canonical(), self.stable(), self.reu(), self.queue()
        f.put('se_hot_position', 6)
        self.hot(W_LOAD, error=0x17)
        assert f.canonical() == canonical and self.queue() == queue
        self.guards(reu, 'missing-R32-LOAD', unchanged=stable)
        self.restore(saved)
        self.record('missing-R32-LOAD-before-body')

        # One legitimate foreign read lease must survive cancellation of the
        # window loader's separately acquired lease.
        for foreign in (False, True):
            self.setup(armed=False)
            if foreign:
                assert not f.call('se_doc_read_acquire').p & 1
            f.put('se_hot_position', 6)
            assert self.hot(W_LOAD).a == 1
            assert f.get('se_hot_owned', 1) == 1
            assert f.get('se_doc_read_locks', 1) == 1 + foreign
            saved = self.remove('hotcold')
            stable, reu, queue = self.stable(), self.reu(), self.queue()
            self.hot(W_STEP, error=0x17)
            assert not f.get('se_hot_owned', 1) and not f.get('se_hot_phase', 1)
            assert not f.get('se_hot_ready', 1)
            assert f.get('se_doc_read_locks', 1) == int(foreign)
            assert self.queue() == queue
            self.guards(reu, 'missing-R32-STEP', unchanged=stable)
            self.restore(saved)
            if foreign:
                assert not f.call('se_doc_read_release').p & 1
            self.record('missing-R32-STEP-owned-cleanup', foreign_lease=foreign)

        self.setup(armed=False)
        f.key(Q)
        saved = self.remove('hotcold')
        canonical, stable, reu, queue = f.canonical(), self.stable(), self.reu(), self.queue()
        self.hot(W_FLUSH, error=0x17)
        assert f.canonical() == canonical and f.merged() == DATA[:5] + bytes([Q]) + DATA[5:]
        assert self.queue() == queue and not f.get('se_hot_phase', 1)
        self.guards(reu, 'missing-R32-PREPARE', unchanged=stable)
        self.restore(saved)
        self.record('missing-R32-PREPARE-preserves-pending')

        self.setup(armed=False)
        f.put('se_hot_position', 6)
        self.hot(W_LOAD)
        # Explicit stale token-epoch injection models an old continuation. It
        # does not pretend a complete provider reset was performed by typing.
        address = f.s['se_hot_original'] + 3
        f.m.write(address, f.m.read(address) ^ 0x80)
        reu, stable = self.reu(), self.stable()
        self.hot(W_CANCEL)
        assert not f.get('se_hot_owned', 1) and not f.get('se_hot_phase', 1)
        assert f.get('se_doc_read_locks', 1) == 1, 'stale epoch released a current lease'
        self.guards(reu, 'epoch-forget-CANCEL', unchanged=stable)
        assert not f.call('se_doc_read_release').p & 1
        self.record('epoch-forget-CANCEL', injection='hot token epoch byte; current doc lease preserved')

    def high_position(self):
        f = self.f
        data = b'a' * 65535 + geos.native_text('\rhello world\r')
        self.setup(position=65536, data=data)
        gen, revision = f.get('se_doc_generation', 2), f.get('se_r_revision', 4)
        reu, stable = self.reu(), self.stable()
        for i, (tag, fn, deleted, inserted, wanted) in enumerate((
                ('high24-insert', lambda: f.key(Q), 0, 1,
                 data[:65536] + bytes([Q]) + data[65536:]),
                ('high24-backspace', lambda: f.key(0x14), 1, 0, data))):
            fn()
            expected = event(i + 1, revision + i, gen, 65536, deleted, inserted)
            assert f.read(f.s['se_bc_ring'] + i * 32, 32) == expected
            assert f.merged() == wanted
            self.guards(reu, tag, unchanged=stable)
            self.record(tag, source_length=len(wanted), event=expected.hex())

    def packet_fault(self):
        f = self.f
        self.setup(armed=False)
        f.key(Q)
        wanted = DATA[:5] + bytes([Q]) + DATA[5:]
        assert self.hot(W_FLUSH).a == 1
        for step in range(1000):
            if f.get('se_h_phase', 1) == 4 and f.get('se_hot_feed_left', 2):
                break
            self.hot(W_STEP)
        else:
            raise AssertionError('did not reach actual H_FEEDING')
        saved = self.remove('eedit')
        source, reu = f.document(), self.reu()
        self.hot(W_STEP, error=0x17)
        retained = dict(hot_phase=f.get('se_hot_phase', 1),
                        history_phase=f.get('se_h_phase', 1),
                        doc_busy=f.get('se_doc_busy', 1),
                        locks=f.get('se_doc_read_locks', 1))
        assert f.merged() == wanted and f.document() == source
        self.guards(reu, 'missing-fast-C4-PACKET')
        if retained['hot_phase']:
            assert retained['hot_phase'] == 2 and retained['history_phase'] == 4
            self.known.append(dict(tag='fast-C4-packet-error-does-not-auto-cancel', **retained))
        self.restore(saved)
        assert not retained['hot_phase'], ('current fast C4 packet must auto-cancel', retained)
        self.hot(W_CANCEL)
        assert not f.get('se_hot_phase', 1) and not f.get('se_h_phase', 1)
        assert not f.get('se_doc_busy', 1) and not f.get('se_doc_read_locks', 1)
        assert f.merged() == wanted and f.document() == DATA
        self.record('missing-fast-C4-PACKET-explicit-cancel-recovery', observed=retained,
                    automatic_cleanup=not bool(retained['hot_phase']))

    def flush(self, *, inspect=None):
        assert self.hot(W_FLUSH).a in (0, 1)
        if inspect:
            inspect()
        for step in range(1000):
            if not self.f.get('se_hot_phase', 1):
                return step
            self.hot(W_STEP)
        raise AssertionError('hot flush did not finish')

    def rekeys(self):
        f = self.f
        self.setup()
        f.key(Q)
        revision, generation = f.get('se_r_revision', 4), f.get('se_doc_generation', 2)
        wanted = DATA[:5] + bytes([Q]) + DATA[5:]
        def reserved():
            assert f.get('se_bc_flags', 1) == 5 and f.get('se_bc_count', 1) == 1
            assert f.get('se_bc_ticket', 4) == 1
            raw = f.read(f.s['se_bc_ring'] + 32, 32)
            assert raw[0] == 0 and raw[1] == 2
            assert integer(raw, 16, 3) == 5 and integer(raw, 19, 3) == 0
            assert integer(raw, 22, 3) == 1
        before = self.audit_begin()
        self.flush(inspect=reserved)
        self.audit_end(before, 'nonzero-REKEY')
        expected = event(1, revision, generation, 5, 0, 1, kind=2,
                         next_generation=generation + 1, next_revision=revision)
        assert f.read(f.s['se_bc_ring'] + 32, 32) == expected
        assert f.get('se_bc_count', 1) == 2 and f.get('se_bc_ticket', 4) == 1
        assert f.get('se_bc_flags', 1) == 1
        assert f.document() == wanted and f.merged() == wanted
        assert not f.get('se_hot_pending', 1)
        self.record('nonzero-flush-one-REKEY-no-extra-ticket', event=expected.hex())
        queue, reu = self.queue(), self.reu()
        self.flush()
        assert self.queue() == queue
        self.guards(reu, 'repeated-empty-flush')
        self.record('repeated-empty-flush-no-event')

        self.setup()
        f.key(Q)
        f.key(0x14)
        assert f.merged() == DATA and f.get('se_hot_pending', 1)
        revision, generation = f.get('se_r_revision', 4), f.get('se_doc_generation', 2)
        before = self.audit_begin()
        self.flush()
        self.audit_end(before, 'zero-delta-REKEY')
        expected = event(2, revision, generation, 5, 0, 0, kind=2,
                         next_generation=generation, next_revision=revision)
        assert f.read(f.s['se_bc_ring'] + 64, 32) == expected
        assert f.get('se_bc_ticket', 4) == 2 and f.get('se_bc_count', 1) == 3
        assert f.get('se_doc_generation', 2) == generation and f.document() == DATA
        self.record('net-zero-flush-W_COMMIT-REKEY-gen-unchanged', event=expected.hex())

        self.setup()
        f.key(Q)
        assert self.hot(W_FLUSH).a == 1
        self.hot(W_CANCEL)
        assert f.get('se_bc_flags', 1) == 5
        assert f.get('se_bc_count', 1) == 1 and f.get('se_bc_ticket', 4) == 1
        assert f.m.read(f.s['se_bc_ring'] + 32) == 0
        reu, stable = self.reu(), self.stable()
        f.key(Q)
        assert f.get('se_bc_flags', 1) == 2
        assert f.get('se_bc_count', 1) == 1
        assert f.merged() == DATA[:5] + bytes([Q, Q]) + DATA[5:]
        self.guards(reu, 'abandoned-REKEY-next-edit', unchanged=stable)
        self.record('abandoned-REKEY-next-edit-LOST-no-false-publish')

    def request(self, p, d, n):
        for name, value in (('se_doc_edit_position', p), ('se_doc_edit_delete', d),
                            ('se_doc_edit_insert', n)):
            self.f.put(name, value)

    def feed(self, data):
        f = self.f
        for at in range(0, len(data), 128):
            part = data[at:at + 128]
            f.m.load(0x8000, part)
            f.put('se_doc_c64', 0x8000, 2)
            f.put('se_doc_count', len(part), 2)
            self.call('se_doc_splice_feed')

    def apply(self):
        for _ in range(2000):
            r = self.call('se_doc_splice_step')
            if r.a == 0:
                assert not self.f.get('se_doc_busy', 1)
                return
            assert r.a == 1
        raise AssertionError('R2 splice did not finish')

    def byte_splices(self):
        f = self.f
        for name, p, d, inserted, data in (
            ('byte-replace', 7, 3, geos.native_text('xyz'), DATA),
            ('high24-delete-cross-FFFF', 65535, 2, b'', b'a' * 65535 + b'bc tail\r')):
            self.setup(data=data)
            self.hot(10)  # actual W_CLOSE: no pending window; canonical==visible
            head = f.get('se_bc_head', 1)
            revision, generation = f.get('se_r_revision', 4), f.get('se_doc_generation', 2)
            self.request(p, d, len(inserted))
            queue = self.queue()
            before = self.audit_begin()
            assert self.call('se_doc_splice_begin').a == 1
            assert self.queue() == queue, 'BEGIN prematurely published event'
            self.feed(inserted)
            assert self.queue() == queue, 'FEED prematurely published event'
            # The actual transaction must be authoritative, not request scratch.
            self.request(0x123456, 0x654321, 0x010203)
            self.apply()
            self.audit_end(before, name)
            expected = event(1, revision, generation, p, d, len(inserted),
                             next_revision=revision, next_generation=generation + 1)
            self.latest(head, expected, name)
            assert f.document() == data[:p] + inserted + data[p + d:]
            self.record(name, event=expected.hex(), public_request_clobbered=True)

        for mode in ('admission-fail', 'cancel-before-feed', 'missing-feed-retry', 'zero-noop'):
            self.setup()
            self.hot(10)
            queue, source = self.queue(), f.document()
            before = self.audit_begin()
            if mode == 'admission-fail':
                self.request(len(DATA), 1, 0)
                self.call('se_doc_splice_begin', error=0x32)
            elif mode == 'zero-noop':
                self.request(5, 0, 0)
                assert self.call('se_doc_splice_begin').a == 0
            else:
                self.request(5, 0, 3)
                assert self.call('se_doc_splice_begin').a == 1
                if mode == 'missing-feed-retry':
                    self.call('se_doc_splice_step', error=0x45)
                self.call('se_doc_splice_cancel')
            self.audit_end(before, mode)
            assert self.queue() == queue and f.document() == source
            self.record(mode + '-no-event')

        self.setup()
        f.key(Q)
        self.consume()
        self.request(1, 1, 0)
        before = self.audit_begin()
        self.call('se_doc_splice_begin')
        self.apply()
        self.audit_end(before, 'unproved-pending-generic-splice')
        assert f.get('se_bc_flags', 1) == 2 and not f.get('se_bc_count', 1)
        assert f.document() == DATA[:1] + DATA[2:]
        self.record('unproved-pending-generic-splice-LOST',
                    scope='Direct source API intentionally invalidates unrelated pending source proof; no merged-window reuse claim')

    def reference_splice(self):
        f = self.f
        self.setup()
        self.hot(10)
        # A real type6 immutable reference object, pointing into actual original.
        r, _ = f.fast_call(f.s['se_object_create'], a=6, x=1)
        assert not r.p & 1
        token = f.read(f.s['se_object_id'], 5)
        packed = f.read(f.s['se_doc_original'], 3) + (2).to_bytes(3, 'little') + (4).to_bytes(3, 'little')
        f.m.load(0x8000, packed)
        f.put('se_object_offset', 0)
        f.put('se_object_length', 9, 2)
        f.put('se_object_c64', 0x8000, 2)
        self.call('se_object_copy')
        f.put('se_object_offset', 9)
        self.call('se_object_resize')
        f.m.load(f.s['se_doc_refs_token'], token)
        f.put('se_doc_refs_offset', 0)
        f.put('se_doc_refs_pieces', 1, 2)
        self.request(8, 2, 4)
        revision, generation = f.get('se_r_revision', 4), f.get('se_doc_generation', 2)
        head, queue = f.get('se_bc_head', 1), self.queue()
        before = self.audit_begin()
        assert self.call('se_doc_splice_refs_begin').a == 1
        assert self.queue() == queue
        self.apply()
        self.audit_end(before, 'reference-splice')
        expected = event(1, revision, generation, 8, 2, 4,
                         next_revision=revision, next_generation=generation + 1)
        self.latest(head, expected, 'reference-splice')
        assert f.document() == DATA[:8] + DATA[2:6] + DATA[10:]
        self.record('reference-splice-one-event', event=expected.hex())

    def history_events(self):
        f = self.f
        self.setup()
        f.key(Q)
        before = self.audit_begin()
        self.flush()
        self.audit_end(before, 'history-seed-flush')
        self.consume()
        for command, tag, deleted, inserted, wanted in (
                (16, 'undo', 1, 0, DATA),
                (17, 'redo', 0, 1, DATA[:5] + bytes([Q]) + DATA[5:])):
            revision, generation = f.get('se_r_revision', 4), f.get('se_doc_generation', 2)
            ticket, head = f.get('se_bc_ticket', 4), f.get('se_bc_head', 1)
            before = self.audit_begin()
            f.command(command)
            self.audit_end(before, tag)
            expected = event(ticket + 1, revision, generation, 5, deleted, inserted,
                             next_revision=revision, next_generation=generation + 1)
            self.latest(head, expected, tag)
            assert f.document() == wanted and f.merged() == wanted
            self.record(tag + '-one-R2-SPLICE-no-C5-duplicate', event=expected.hex())
            self.consume()

    def history_context(self):
        f = self.f
        self.setup()
        f.key(Q)
        before = self.audit_begin()
        self.flush()
        self.audit_end(before, 'context-seed')
        queue, source, reu = self.queue(), f.document(), self.reu()
        self.call('se_history_call', 1)
        assert self.queue() == queue
        self.guards(reu, 'same-H_INIT')
        self.record('same-H_INIT-idempotent')
        incarnation = f.get('se_bc_incarnation', 4)
        token = f.read(f.s['se_bc_arena'], 5)
        # Explicit old history-context identity injection forces the real
        # H_INIT new_context path, without faking a document publication/OPEN.
        f.m.write(f.s['se_h_original'] + 1, f.m.read(f.s['se_h_original'] + 1) ^ 0x80)
        reu = self.reu()
        self.call('se_history_call', 1)
        assert f.get('se_bc_flags', 1) == 2
        assert all(f.get(n, 1) == 0 for n in ('se_bc_head', 'se_bc_tail', 'se_bc_count'))
        assert f.get('se_bc_ticket', 4) == 0 and f.get('se_bc_incarnation', 4) == incarnation + 1
        assert f.read(f.s['se_bc_arena'], 5) == token and f.document() == source
        self.guards(reu, 'new-H_INIT')
        self.record('new-H_INIT-repairs-context-disarms-LOST',
                    seam='injected old history identity; actual H_INIT; no OPEN claim')

    def selected_edits(self):
        f = self.f
        def select():
            f.command(68)
            for _ in range(4):
                f.command(2)
            assert f.get('se_hot_caret') == 9 and f.get('se_sel_anchor') == 5
        self.setup()
        select()
        head = f.get('se_bc_head', 1)
        revision, generation = f.get('se_r_revision', 4), f.get('se_doc_generation', 2)
        before = self.audit_begin()
        f.key(Q)
        self.audit_end(before, 'selected-replace')
        expected = event(1, revision, generation, 5, 4, 1,
                         next_revision=revision, next_generation=generation + 1)
        self.latest(head, expected, 'selected-replace')
        assert f.merged() == DATA[:5] + bytes([Q]) + DATA[9:]
        self.record('selected-replace-one-generic-C4-SPLICE', event=expected.hex())

        self.setup()
        select()
        queue = self.queue()
        before = self.audit_begin()
        f.command(69)
        self.audit_end(before, 'COPY')
        assert self.queue() == queue and f.document() == DATA
        assert f.get('se_clip_length') == 4
        self.record('COPY-no-source-event')
        for command, tag, deleted, inserted, wanted in (
                (70, 'CUT', 4, 0, DATA[:5] + DATA[9:]),
                (71, 'PASTE', 0, 4, DATA)):
            head, ticket = f.get('se_bc_head', 1), f.get('se_bc_ticket', 4)
            revision, generation = f.get('se_r_revision', 4), f.get('se_doc_generation', 2)
            before = self.audit_begin()
            f.command(command)
            self.audit_end(before, tag)
            expected = event(ticket + 1, revision, generation, 5, deleted, inserted,
                             next_revision=revision, next_generation=generation + 1)
            self.latest(head, expected, tag)
            assert f.document() == wanted and f.merged() == wanted
            self.record(tag + '-one-generic-C4-SPLICE', event=expected.hex())
            self.consume()

    def head_faults(self):
        f = self.f
        for zero in (True, False):
            self.setup()
            f.key(Q)
            if zero:
                f.key(0x14)
            assert self.hot(0x80).a == 1  # actual W_PREPARE only, before H_BEGIN
            assert f.get('se_bc_flags', 1) == 5
            if not zero:
                assert self.call('se_history_call', 2).a == 1
            f.put('se_bc_head', 3, 1)  # continuation corruption after PREPARE
            before = self.audit_begin()
            self.dll.ob_ring(f.s['se_bc_ring'])
            try:
                if zero:
                    # W_COMMIT is an internal C6 operation, not an admitted
                    # competing se_hot_call command during phase2. Invoke its
                    # real overlay entry like the resident dispatcher does.
                    f.put('se_overlay_frame', 0x82, 1)
                    r, _ = f.fast_call(f.s['se_overlay_call'], a=6, x=1)
                    assert not r.p & 1, ('internal zero-delta W_COMMIT', r.a)
                else:
                    for step in range(1000):
                        if not f.get('se_hot_phase', 1):
                            break
                        self.hot(W_STEP)
                    else:
                        raise AssertionError('corrupt-intent flush did not finish')
            finally:
                bad = [self.dll.ob_ring_get(i) for i in range(3)]
                self.dll.ob_ring(0)
                self.audit_end(before, 'mutated-head')
            detail = dict(tag='mutated-head-after-PREPARE', zero_delta=zero,
                          out_of_bounds_accesses=bad[0], first_pc=hex(bad[1]),
                          first_address=hex(bad[2]), flags=f.get('se_bc_flags', 1))
            (self.out / 'head-fault.json').write_text(json.dumps(detail, indent=2) + '\n')
            assert bad[0] == 0, detail
            assert f.get('se_bc_flags', 1) == 2
            assert f.document() == (DATA if zero else DATA[:5] + bytes([Q]) + DATA[5:])
            self.record(**{k: v for k, v in detail.items() if k != 'tag'}, tag=detail['tag'])

    def finish(self):
        result = dict(status='passed', identity=self.identity, cases=self.cases,
            known_behavior=self.known, whole16MiB_unchanged_intervals=self.whole_reu_intervals,
            exact_checked_dma_intervals=self.exact_dma_intervals,
            payload_bytes={name: len(self.f.assets[name]) - 36
                           for name in ('window', 'hotcold', 'engine', 'eedit')},
            verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            crc='CRC16/CCITT-FALSE; bytes1..28 + reserved31, little-endian29..30',
            scope='Actual hot/R2 byte/reference/history SPLICE + trusted REKEY and R32/C4 fault paths. Explicit host ARMED + queue-consumer acknowledgment seams; no semantic baseline/arena drain/OPEN/native/pixel claim.')
        (self.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', action='store_true')
    p.add_argument('--fixture', type=Path)
    p.add_argument('--smoke', action='store_true')
    p.add_argument('--head-faults', action='store_true')
    a = p.parse_args()
    if not a.run:
        print('Prepared actual observer gate; wait for coherent49 build then --run [--fixture immutable].')
        return
    out = ROOT / 'build/cache-observer' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    print('RUN', out, flush=True)
    gate = None
    try:
        gate = Gate(out, a.fixture)
        if a.head_faults:
            gate.head_faults()
        else:
            gate.local_edits()
        if not a.smoke and not a.head_faults:
            gate.disarmed_and_refusals()
            gate.high_position()
            gate.cold_faults()
            gate.packet_fault()
            gate.rekeys()
            gate.byte_splices()
            gate.reference_splice()
            gate.history_events()
            gate.selected_edits()
            gate.history_context()
            gate.head_faults()
        result = gate.finish()
        print(json.dumps(dict(status=result['status'], cases=len(result['cases']),
            known_behavior=result['known_behavior'], result=str(out / 'result.json')), indent=2))
    finally:
        if gate:
            gate.f.close()


if __name__ == '__main__':
    main()
