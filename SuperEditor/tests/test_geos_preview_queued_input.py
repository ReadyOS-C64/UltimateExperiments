"""Public queued preview input preserves completed-page navigation dependencies.

CPU modeled ROM/source transport, actual resident idle/service/input ring. No
job, page result, parser state or authority is seeded. Native timing is separate.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json

import test_cache_observer as observer
import test_cache_hotpath_profile as hot
import test_plain_geos as plain
from geos_preview_model import Face, FontCatalog, profiles, render, with_chrome

ROOT = observer.ROOT
SOURCE = plain.SOURCE + observer.geos.native_text(
    'Ordinary continuing words for another viewport.\r' * 42 + 'Last.\r')


def run(fixture, out):
    out.mkdir(parents=True)
    (out / 'verifier.py').write_bytes(Path(__file__).read_bytes())
    gate = observer.Gate(out, fixture)
    f = gate.f
    fonts = {name: (gate.frozen / 'fonts' / name).read_bytes()
             for name in observer.geos.GEOS_FONTS + ('native8.bin',)}
    # The pinned session defaults use only these two genuine frozen font faces.
    # Refuse another default configuration instead of borrowing live build data.
    faces = {(0, 0, 9): Face(fonts['bsw9-original.bin'], native=fonts['native8.bin']),
             (0, 1, 8): Face(native=fonts['native8.bin'])}
    catalog = FontCatalog.__new__(FontCatalog)
    catalog.native, catalog.faces = fonts['native8.bin'], faces
    cases = []

    def setup():
        f.source(SOURCE, physical=256)
        f.typed(observer.geos.native_text('syntax full'))
        f.command(99)
        hot.drain(f)
        assert all((p.origin, p.family, p.point) in faces
                   for p in profiles(f.read(f.s['se_editor_settings'], 64)))

    def pending_preview(command=102):
        f.call('se_editor_command', command)
        for _ in range(20000):
            if f.get('se_e_job', 1) == 11 and f.m.read(0x9135) == 27:
                return
            f.tick()
        raise AssertionError(('actual preview boundary missing', f.debug()))

    def drain_queue():
        for ticks in range(40000):
            f.tick()
            if (f.get('se_input_head', 1) == f.get('se_input_tail', 1)
                    and hot.quiet(f)):
                return ticks + 1
        raise AssertionError(('preview input starved', f.debug()))

    def pixels(tag, preview=True):
        assert f.merged() == SOURCE
        assert f.read(0xC600, 1024) == f.shim
        assert not any(f.get(n, 1) for n in
            ('se_e_job', 'se_e_error', 'se_f_owner', 'se_doc_read_locks', 'se_e_draw_busy'))
        if preview:
            assert f.get('se_e_ui', 1) == 4 and f.get('se_r_presentation', 1) == 1
            expected = render(SOURCE, f.read(f.s['se_editor_settings'], 64),
                              catalog=catalog, top=f.get('se_v_top'))
            matrix, colors, popup = observer.geos.grid.logical_ui(f, SOURCE)
            assert popup is None
            bitmap, attrs = with_chrome(expected.bitmap, expected.attrs,
                                        matrix, colors, catalog.native)
        else:
            bitmap, attrs, _ = plain.expected(f, SOURCE, fonts, 3)
        assert f.read(0x6000, 8000) == bitmap, (tag, 'independent bitmap')
        assert f.read(0x4000, 1000) == attrs, (tag, 'independent attributes')
        return hashlib.sha256(bitmap + attrs).hexdigest()

    try:
        setup()
        f.command(102)
        hot.drain(f)
        appearance = f.read(f.s['se_editor_settings'], 64)
        first = render(SOURCE, appearance, catalog=catalog, top=f.get('se_v_top'))
        second = render(SOURCE, appearance, catalog=catalog, top=first.bottom)
        # The second F5 arrives only AFTER the first starts actual job11. This
        # distinguishes cancellation regression from two events prequeued before
        # any redraw, which is a separate older input-coalescing limitation.
        f.queued(0x87)
        f.tick()
        for _ in range(20000):
            if f.get('se_e_job', 1) == 11 and f.m.read(0x9135) == 27:
                break
            f.tick()
        else:
            raise AssertionError('first F5 did not start actual preview')
        assert f.get('se_v_top') == first.bottom
        canonical, images = f.canonical(), f.catalog()
        before = gate.audit_begin()
        f.queued(0x87)
        ticks = drain_queue()
        gate.audit_end(before, 'pending-next-page')
        assert f.canonical() == canonical and f.catalog() == images
        assert f.get('se_v_top') == second.bottom, (
            'second F5 reused an unfinished page bottom', f.get('se_v_top'), second.bottom)
        cases.append(dict(tag='pending-next-page', expected_top=second.bottom,
                          ticks=ticks, pixels=pixels('pending-next-page')))

        for tag, key in (('ignored-ordinary', observer.Q), ('F1-menu', 0x85)):
            setup()
            pending_preview()
            canonical, images = f.canonical(), f.catalog()
            before = gate.audit_begin()
            tail = f.get('se_input_tail', 1)
            f.queued(key)
            f.call('se_editor_service')
            assert f.get('se_e_job', 1) == 11, (tag, 'preview canceled')
            assert f.get('se_input_tail', 1) == tail
            ticks = drain_queue()
            if key == 0x85:
                assert f.get('se_e_ui', 1) == 1
                f.queued(3)
                f.tick()
                hot.drain(f)
            gate.audit_end(before, tag)
            assert f.canonical() == canonical and f.catalog() == images
            cases.append(dict(tag=tag, ticks=ticks, pixels=pixels(tag)))

        setup()
        pending_preview()
        for _ in range(7):
            f.call('se_editor_service')
        canonical, images = f.canonical(), f.catalog()
        before = gate.audit_begin()
        f.queued(3)
        f.call('se_editor_service')
        assert not any(f.get(n, 1) for n in
            ('se_e_job', 'se_f_owner', 'se_doc_read_locks', 'se_e_draw_busy'))
        assert f.get('se_input_head', 1) == f.get('se_input_tail', 1)
        assert f.get('se_e_ui', 1) == 4
        # Existing STOP service contract aborts current work. A subsequent STOP
        # is delivered to the idle preview UI and returns to editable source.
        f.queued(3)
        f.tick()
        hot.drain(f)
        gate.audit_end(before, 'STOP-abort-and-source-recovery')
        assert f.get('se_e_ui', 1) == 0 and f.get('se_r_presentation', 1) == 0
        assert f.canonical() == canonical and f.catalog() == images
        cases.append(dict(tag='STOP-abort-and-source-recovery',
                          pixels=pixels('STOP-abort-and-source-recovery', False)))
        result = dict(status='PASS', fixture=str(fixture), identity=gate.identity,
                      cases=cases, exact_checked_DMA_whole16MiB_intervals=gate.exact_dma_intervals,
                      scope=__doc__)
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        return result
    finally:
        f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    out = args.out or ROOT / 'build/geos-preview-queued-input' / datetime.now(
        timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    result = run(args.fixture.resolve(), out.resolve())
    print(json.dumps(dict(status=result['status'], cases=len(result['cases']), out=str(out))))
