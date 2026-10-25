"""Actual editor GEOS dirty-workspace, STOP and pre-DOS modal regressions.

Private frozen products only; no shared build or native/VIC claim. The File
case pauses immediately after real C12 modal construction, before servicing
its directory request. It tests rendering/phase ownership, not DOS behavior.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import ctypes as C
import hashlib
import json
import shutil

import test_geos_editor as geos

ROOT = geos.ROOT


def run(out, previous=None):
    frozen, identity = geos.freeze(out, previous)
    geos.grid.editor_fixture.ROOT = geos.grid.cpu_editor.ROOT = frozen
    geos.grid.editor_fixture.NAMES = geos.grid.cpu_editor.NAMES = identity['names']
    dll = geos.grid.runner(out)
    fonts = {n: (frozen/'fonts'/n).read_bytes()
             for n in geos.GEOS_FONTS + ('native8.bin',)}
    cases = []

    def reu(f):
        result = C.create_string_buffer(16*1024*1024)
        dll.gm_reu(f.m.handle, len(result), result)
        return result.raw

    def exact(f, data, tag):
        canonical, catalog = f.canonical(), f.catalog()
        before = reu(f)
        f.render()
        assert f.canonical() == canonical and f.catalog() == catalog, tag
        assert f.merged() == data, (tag, 'canonical/pending source')
        bits, attrs, lines = geos.expected(f, data, fonts)
        assert f.read(0x6000, 8000) == bits, (tag, 'all bitmap bytes')
        assert f.read(0x4000, 1000) == attrs, (tag, 'all tile attributes')
        cache, physical = f.cache()
        after = reu(f)
        start = physical*65536
        assert before[:start] == after[:start] and before[start+65536:] == after[start+65536:], (tag, 'foreign REU')
        assert cache[0] == 1 and cache[1] == len(lines), (tag, 'published page')
        for i, line in enumerate(lines):
            record = cache[0x200+i*0x800:0x220+i*0x800]
            assert tuple(int.from_bytes(record[p:p+3], 'little') for p in (0, 3, 6)) == (line.start, line.end, line.next), (tag, 'anchors', i)
        assert f.read(0xC600, 1024) == f.shim, (tag, 'shim')
        assert not any(f.get(n, 1) for n in ('se_f_owner', 'se_doc_read_locks', 'se_fs_owned', 'se_e_error')), (tag, f.debug())
        cases.append(dict(tag=tag, source_bytes=len(data), lines=len(lines),
                          pixels=64000, bitmap_sha256=hashlib.sha256(bits).hexdigest()))

    def stop(f, tag):
        canonical = f.canonical()
        f.queued(3)
        f.call('se_editor_service')
        assert not any(f.get(n, 1) for n in ('se_f_owner', 'se_doc_read_locks', 'se_fs_owned', 'se_e_job', 'se_e_draw_busy')), (tag, f.debug())
        assert f.read(0x8B40, 2) == b'\0\0', (tag, 'abandoned painter')
        assert f.canonical() == canonical, (tag, 'STOP changed source/history')

    f = geos.Fixture(out, frozen, dll, True)
    try:
        data = geos.TINY
        f.source(data)
        # These are caller workspace, not initialized BSS. Nonzero native RAM
        # must not masquerade as a live painter or invalid source styles.
        f.m.load(0x8B40, b'\xA5\x5A')
        f.m.load(0x8300, bytes([0xFF])*160)
        f.command(99)
        exact(f, data, 'dirty-first-entry')

        f.key(geos.native_text('Q')[0])
        data = geos.native_text('Q')+data
        r = f.call('se_editor_render')
        assert not r.p & 1
        for _ in range(10000):
            if f.m.read(0x912D):
                break
            f.call('se_editor_service')
        else:
            raise AssertionError('source context never acquired')
        assert f.get('se_doc_read_locks', 1)
        stop(f, 'source-STOP')
        exact(f, data, 'after-source-STOP-pending')

        f.call('se_editor_render')
        for _ in range(10000):
            if f.m.read(0x8B40):
                break
            f.call('se_editor_service')
        else:
            raise AssertionError('C22 painter never acquired')
        stop(f, 'paint-STOP')
        exact(f, data, 'after-paint-STOP-pending')

        # Open flushes pending input normally. Settle that ordinary flush, then
        # stop before the queued directory request reaches any KERNAL channel.
        f.put('se_e_key', 15, 1)
        f.put('se_e_mods', 4, 1)
        f.call('se_editor_input')
        for _ in range(10000):
            if f.get('se_f_owner', 1) == 1:
                break
            f.call('se_editor_service')
        else:
            raise AssertionError('real File modal not claimed')
        assert f.get('se_e_ui', 1) == 3 and f.get('se_f_request', 1)
        f.put('se_e_job', 0, 1)  # isolated pre-DOS rendering seam, not DOS execution
        f.hold_file_transport = True
        for tag, help_flag in [('File-modal', False), ('File-help-paint', True)]:
            if help_flag:
                # Directory work is deliberately unserviced, so F6 correctly
                # refuses BUSY. Seed only the display flag for a second pure
                # modal paint case; no claim of executing that UI transition.
                f.put('se_f_ui_help', 1, 1)
            phase, canonical, before = f.read(0x8D00, 1152), f.canonical(), reu(f)
            f.render()
            bits, attrs, _ = geos.expected(f, data, fonts)
            assert f.read(0x6000, 8000) == bits and f.read(0x4000, 1000) == attrs, (tag, 'popup pixels')
            assert f.read(0x8D00, 1152) == phase, (tag, 'File union changed')
            assert f.canonical() == canonical and reu(f) == before, (tag, 'source/REU')
            assert f.get('se_f_owner', 1) == 1 and f.get('se_e_ui', 1) == 3
            assert not f.get('se_e_error', 1) and f.read(0xC600, 1024) == f.shim
            cases.append(dict(tag=tag, pixels=64000, phase_bytes_preserved=1152,
                              source_bytes=len(data), DOS_calls=0))
    finally:
        f.close()

    for tag, data in [('empty', b''), ('single-CR', b'\r'),
                      ('trailing-CR', geos.native_text('A\r')),
                      ('long-word', geos.native_text('W'*400)),
                      ('long-spaces', b' '*320), ('native-byte-range', bytes(range(256)))]:
        f = geos.Fixture(out, frozen, dll, True)
        try:
            f.source(data)
            f.command(99)
            exact(f, data, tag)
        finally:
            f.close()
    result = dict(status='passed', identity=identity, cases=cases,
                  pixels_checked=sum(c['pixels'] for c in cases), whole_REU_bytes=16*1024*1024,
                  scope='Actual CPU/root GEOS dirty workspace, source/painter STOP recovery, tiny/long canonical anchors, and pre-DOS File modal phase-safe pixels; no native/VIC/DOS claim.')
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    archive = ROOT/'agentsworking/evidence/M7'/(out.name+'-geos-recovery')
    archive.mkdir(parents=True)
    for name in ['result.json']:
        shutil.copy2(out/name, archive/name)
    shutil.copy2(Path(__file__), archive/Path(__file__).name)
    shutil.copy2(frozen/'product-sources.zip', archive/'product-sources.zip')
    pointer = dict(status='passed', evidence=str(archive.relative_to(ROOT)),
                   prg_sha256=identity['prg_sha256'], cases=len(cases),
                   pixels_checked=result['pixels_checked'])
    (ROOT/'agentsworking/evidence/M7/geos-recovery-checkpoint.json').write_text(json.dumps(pointer, indent=2)+'\n')
    print(json.dumps(pointer, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--fixture', type=Path)
    args = parser.parse_args()
    if args.run:
        out = ROOT/'build/geos-recovery'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        out.mkdir(parents=True)
        print('RUN '+str(out), flush=True)
        run(out, args.fixture)
    else:
        print('Prepared; --run executes frozen actual CPU GEOS recovery checks.')
