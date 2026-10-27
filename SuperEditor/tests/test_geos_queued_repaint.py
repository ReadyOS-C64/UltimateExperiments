"""Queued input during real GEOS jobs: latency, cleanup and final independent pixels.

The CPU fixture models ROM/source transport; queued events use the public ring
producer seam, not physical keys. Actual se_idle/service/input code executes.
No job, source lease, parser certificate or result is seeded by this test.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json
import test_cache_observer as observer
import test_cache_hotpath_profile as hot
import test_plain_geos as plain

ROOT = observer.ROOT


def run(base, out):
    out.mkdir(parents=True)
    (out / 'verifier.py').write_bytes(Path(__file__).read_bytes())
    identity = json.loads((base / 'freeze.json').read_text())
    assert len(identity['names']) == 62
    g = observer.Gate(out, base)
    f = g.f
    fonts = {n: (base / 'fonts' / n).read_bytes()
             for n in observer.geos.GEOS_FONTS + ('native8.bin',)}
    data = plain.SOURCE + observer.geos.native_text(
        'Long continuing words make several real viewports. ' * 32 + '\rLast.\r')
    cases = []

    def pixels(source, caps, tag):
        bitmap, attrs, _ = plain.expected(f, source, fonts, caps)
        assert f.read(0x6000, 8000) == bitmap, (tag, 'independent bitmap')
        assert f.read(0x4000, 1000) == attrs, (tag, 'independent color cells')
        observer.geos.png(bitmap, attrs, out / (tag + '.png'))
        return hashlib.sha256(bitmap + attrs).hexdigest()

    try:
        for preset, caps in [('plain', 0), ('markdown', 1), ('full', 3)]:
            for worker in (20, 22):
                tag = preset + '-worker' + str(worker)
                f.source(data, physical=256)
                f.typed(observer.geos.native_text('syntax ' + preset))
                f.command(99)
                hot.drain(f)
                pixels(data, caps, tag + '-before')
                # Leave this viewport through real navigation, then return.
                # An unchanged same-mode command may correctly hit the caret
                # cache and is not a reliable way to require layout work.
                f.command(35)
                hot.drain(f)
                f.call('se_editor_command', 34)
                for _ in range(20000):
                    if (f.get('se_e_job', 1) == 11
                            and f.m.read(0x9135) == worker
                            and not f.get('se_bc_flags', 1) & 8):
                        break
                    f.tick()
                else:
                    raise AssertionError((tag, 'real worker boundary missing', f.debug()))
                assert f.get('se_f_owner', 1) == 4
                canonical, catalog = f.canonical(), f.catalog()
                sequence = f.get('se_e_draw_sequence', 2)
                f.queued(observer.geos.native_text('Q')[0])
                tail = f.get('se_input_tail', 1)
                before = g.audit_begin()
                start = f.total_instructions
                f.call('se_editor_service')
                service_used = f.total_instructions - start
                g.audit_end(before, tag + '-cancel-service')
                # Both old and new controls retain the queue in service. The
                # next real idle iteration applies it once cancellation wins.
                assert f.get('se_input_tail', 1) == tail
                assert f.canonical() == canonical and f.catalog() == catalog
                canceled = f.get('se_e_job', 1) == 0
                if canceled:
                    assert not any(f.get(n, 1) for n in
                                   ('se_f_owner', 'se_doc_read_locks', 'se_e_draw_busy'))
                    assert f.read(0x912c, 2) == bytes(2)
                    assert f.get('se_e_draw_sequence', 2) == sequence
                for ticks in range(20000):
                    f.tick()
                    if f.get('se_input_tail', 1) != tail:
                        break
                else:
                    raise AssertionError((tag, 'queued key starved'))
                apply_used = f.total_instructions - start
                wanted = observer.geos.native_text('Q') + data
                assert f.merged() == wanted and f.get('se_hot_caret') == 1
                # A burst arrives before the next frame, preserving ordering.
                burst = observer.geos.native_text('abcdef0123456789')
                for byte in burst:
                    f.queued(byte)
                for _ in burst:
                    f.tick()
                assert f.get('se_input_head', 1) == f.get('se_input_tail', 1)
                wanted = observer.geos.native_text('Q') + burst + data
                assert f.merged() == wanted and f.get('se_hot_caret') == 17
                hot.drain(f)
                final = pixels(wanted, caps, tag + '-final')
                f.command(16)
                hot.drain(f)
                assert f.merged() == data
                pixels(data, caps, tag + '-undo')
                f.command(17)
                hot.drain(f)
                assert f.merged() == wanted
                pixels(wanted, caps, tag + '-redo')
                row = dict(tag=tag, canceled_before_next_slice=canceled,
                           service_instructions=service_used,
                           queued_key_apply_instructions=apply_used,
                           idle_ticks_before_apply=ticks + 1,
                           burst_events=len(burst), pixels=final)
                cases.append(row)
                (out / 'progress.json').write_text(json.dumps(cases, indent=2) + '\n')
                print(tag, row, flush=True)
        # Queued ordinary input must not abandon a still-running position
        # command. It belongs at the requested destination, not the old caret.
        for preset, caps in [('plain', 0), ('full', 3)]:
            f.source(data, physical=256)
            f.typed(observer.geos.native_text('syntax ' + preset))
            f.command(99)
            hot.drain(f)
            f.call('se_editor_command', 35)
            for _ in range(20000):
                if f.get('se_e_job', 1) == 12:
                    break
                f.tick()
            else:
                raise AssertionError('real proportional position job missing')
            f.queued(observer.geos.native_text('Q')[0])
            tail = f.get('se_input_tail', 1)
            navigation_steps = 0
            for _ in range(20000):
                if f.get('se_e_job', 1) != 12:
                    break
                f.call('se_editor_service')
                navigation_steps += 1
                assert f.get('se_input_tail', 1) == tail
            else:
                raise AssertionError('position command starved')
            for _ in range(20000):
                f.tick()
                if f.get('se_input_tail', 1) != tail:
                    break
            else:
                raise AssertionError('input after position command starved')
            wanted = data + observer.geos.native_text('Q')
            assert f.merged() == wanted and f.get('se_hot_caret') == len(wanted)
            hot.drain(f)
            cases.append(dict(tag='navigation-order-' + preset, public_job12_steps=navigation_steps,
                              pixels=pixels(wanted, caps, 'navigation-order-' + preset)))
        for event in ('STOP', 'NMI'):
            f.source(data, physical=256)
            f.typed(observer.geos.native_text('syntax plain'))
            f.command(99)
            hot.drain(f)
            f.command(35)
            hot.drain(f)
            f.call('se_editor_command', 34)
            for _ in range(20000):
                if f.get('se_e_job', 1) == 11 and f.m.read(0x9135) == 22:
                    break
                f.tick()
            else:
                raise AssertionError('real paint boundary missing for ' + event)
            if event == 'STOP':
                f.queued(3)
            else:
                f.put('se_input_nmi_pending', 1, 1)  # external NMI-event seam
            before = g.audit_begin()
            f.call('se_editor_service')
            g.audit_end(before, event)
            assert not any(f.get(n, 1) for n in ('se_e_job', 'se_f_owner', 'se_doc_read_locks'))
            if event == 'STOP' and f.get('se_input_head', 1) != f.get('se_input_tail', 1):
                f.tick()
            assert f.merged() == data and not f.get('se_input_nmi_pending', 1)
            f.key(0x8c)  # actual mode cycle proves the abandoned page can be left
            hot.drain(f)
            assert f.get('se_mode', 1) == 0 and f.merged() == data
            matrix, colors, _ = observer.geos.grid.logical_ui(f, data)
            assert f.read(0x4000, 1000) == matrix and f.read(0xd800, 1000) == colors
            cases.append(dict(tag=event, cleanup=True, source40_recovery=True))
        result = dict(status='PASS', cases=cases, fixture=str(base),
                      resident_sha256=identity['prg_sha256'], scope=__doc__)
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        return result
    finally:
        f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    out = args.out or ROOT / 'build/queued-repaint' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run(args.fixture.resolve(), out.resolve())
