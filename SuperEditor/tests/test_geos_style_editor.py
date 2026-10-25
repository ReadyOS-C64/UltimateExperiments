"""Packaged public styled typing versus full renderer and source/font oracle."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import ctypes as C
import json
import test_geos_semantic_editor as semantic

geos = semantic.geos
ROOT = geos.ROOT


def run(out, previous):
    frozen, identity = geos.freeze(out, previous)
    geos.grid.editor_fixture.ROOT = geos.grid.cpu_editor.ROOT = frozen
    geos.grid.editor_fixture.NAMES = geos.grid.cpu_editor.NAMES = identity['names']
    dll = geos.grid.runner(out)
    f = geos.Fixture(out, frozen, dll, True)
    full = geos.Fixture(out, frozen, dll, True)
    fonts = {n: (frozen / 'fonts' / n).read_bytes()
             for n in geos.GEOS_FONTS + ('native8.bin',)}
    frames = []

    def reu():
        data = C.create_string_buffer(16 * 1024 * 1024)
        dll.gm_reu(f.m.handle, len(data), data)
        return data.raw

    def check(tag, worker=30, window=0x42):
        before = reu()
        canonical = f.canonical()
        instructions = f.total_instructions
        loads = f.get('se_overlay_loads', 2)
        f.render()
        used = f.total_instructions - instructions
        full.m.write(0xCFE8, 0)
        full.m.write(0xCF90, 0)
        full.render()
        active = f.get('se_overlay_active', 1)
        assert active and f.m.read(f.s['se_overlay_ids'] + active - 1) == worker
        assert f.m.read(0xCBD5) == window
        assert f.get('se_f_owner', 1) == 0 and f.m.read(0xCF90) == 1
        source = f.merged()
        assert source == full.merged() and f.canonical() == canonical
        bitmap, attrs, _, _ = semantic.expected(f, source, fonts)
        assert f.read(0x6000, 8000) == bitmap == full.read(0x6000, 8000), tag
        assert f.read(0x4000, 1000) == attrs == full.read(0x4000, 1000), tag
        assert f.read(0xC600, 1024) == f.shim
        handle = f.get('se_gc_handle', 1)
        bank = f.m.read(f.s['se_reu_map'] + handle)
        assert handle and bank
        assert f.m.read(f.s['se_reu_logical_owner'] + handle) == 0xFE
        assert f.m.read(f.s['se_reu_physical_owner'] + bank) == 0xFE
        after = reu()
        base = bank * 65536
        cursor = 0
        for start, end in [(base, base + 64),
                           (base + 0x200, base + 0xE568)]:
            assert after[cursor:start] == before[cursor:start], (tag, cursor, start)
            cursor = end
        assert after[cursor:] == before[cursor:]
        geos.png(bitmap, attrs, out / (tag + '.png'))
        row = dict(tag=tag, instructions=used,
                   loads=(f.get('se_overlay_loads', 2) - loads) & 65535)
        frames.append(row)
        print('PASS', row, flush=True)

    try:
        for style, delimiter in [('plain', ''), ('bold', '**'),
                                 ('italic', '*'), ('combined', '***')]:
            source = geos.native_text('Alpha ' + delimiter + 'interiorwords' +
                                      delimiter + ' omega.\rSecond plain row\rTail.')
            for editor in (f, full):
                editor.source(source)
                editor.command(99)
                editor.position(source.index(geos.native_text('interiorwords')) + 2)
                editor.render()
            events = [('insert', geos.native_text('X')[0]), ('backspace', 0x14)]
            if style == 'combined':
                events += [('insert-W', geos.native_text('W')[0]),
                           ('insert-M', geos.native_text('M')[0]),
                           ('delete-M', 0x14), ('delete-W', 0x14)]
            for name, key in events:
                for editor in (f, full):
                    editor.key(key)
                check(style + '-' + name)
            assert f.merged() == source
        # Both executable borrowers use $5000. Real public navigation and edits
        # must replace their namespace, then recover the other without stale code.
        source = geos.native_text('Alpha **interiorwords** omega.\rSecond plain row\r'
                                  'Third plain row\r:::basic\r10 PRINT "HELLO"\r:::\rTail.')
        for editor in (f, full):
            editor.source(source)
            editor.command(99)
        for turn, word in enumerate(['interiorwords', 'HELLO', 'interiorwords']):
            position = source.index(geos.native_text(word)) + 2
            line = source[:position].count(b'\r') + 1
            column = position - (source.rfind(b'\r', 0, position) + 1)
            for editor in (f, full):
                # GOTO performs the supported pending-edit flush. W_LOAD alone
                # correctly refuses replacing a still-pending hot window.
                editor.typed(geos.native_text('goto ' + str(line)))
                for _ in range(column):
                    editor.key(0x1D)
                assert editor.get('se_hot_caret') == position
                editor.render()
            worker, window = (31, 0x41) if word == 'HELLO' else (30, 0x42)
            for name, key in [('insert', geos.native_text('Q')[0]), ('delete', 0x14)]:
                for editor in (f, full):
                    editor.key(key)
                check(f'namespace-{turn}-{name}', worker, window)
            assert f.merged() == source
        result = dict(status='passed', identity=identity, frames=frames,
                      pixels_checked=len(frames) * 64000,
                      attributes_checked=len(frames) * 1000,
                      whole_REU_guard_bytes=16 * 1024 * 1024,
                      scope='Actual packaged key/render path, no injected '
                            'images or row packets. Forced actual full renderer '
                            'and independent source/font oracle; CPU only.')
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    finally:
        f.close()
        full.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', type=Path, required=True)
    args = parser.parse_args()
    out = ROOT / 'build/geos-style-editor' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    print('RUN', out, flush=True)
    run(out, args.fixture)
