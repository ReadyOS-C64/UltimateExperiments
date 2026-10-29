"""Packaged editor regression for minority ink in a shared hires color tile."""
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
    fonts = {n: (frozen / 'fonts' / n).read_bytes()
             for n in geos.GEOS_FONTS + ('native8.bin',)}
    f = geos.Fixture(out, frozen, dll, True)
    full = geos.Fixture(out, frozen, dll, True)

    def reu():
        data = C.create_string_buffer(16 * 1024 * 1024)
        dll.gm_reu(f.m.handle, len(data), data)
        return data.raw

    try:
        source = geos.native_text('Intro.\rjjj\r- .\rTail.')
        for editor in (f, full):
            editor.source(source)
            editor.command(99)
            editor.position(9)
            editor.render()
            assert editor.read(0x4000 + 160, 1) == b'\x16'
            editor.key(0x14)
        before = reu()
        canonical = f.canonical()
        f.render()
        full.m.write(0xCFE8, 0)  # Disarm GEC in comparison editor only.
        full.render()
        actual_source = f.merged()
        assert actual_source == source[:8] + source[9:] == full.merged()
        bitmap, attrs, _, _ = semantic.expected(f, actual_source, fonts)
        assert attrs[160] == 0x36
        assert f.read(0x6000, 8000) == bitmap == full.read(0x6000, 8000)
        assert f.read(0x4000, 1000) == attrs == full.read(0x4000, 1000)
        assert f.canonical() == canonical
        assert f.read(0xC600, 1024) == f.shim
        # The rendering transaction may update only its existing FE cache spans.
        after = reu()
        handle = f.get('se_gc_handle', 1)
        bank = f.m.read(f.s['se_reu_map'] + handle)
        assert handle and bank
        assert f.m.read(f.s['se_reu_logical_owner'] + handle) == 0xFE
        assert f.m.read(f.s['se_reu_physical_owner'] + bank) == 0xFE
        base = bank * 65536
        cursor = 0
        for start, end in [(base, base + 64),
                           (base + 0x200, base + 0xE568)]:
            assert after[cursor:start] == before[cursor:start]
            cursor = end
        assert after[cursor:] == before[cursor:]
        geos.png(bitmap, attrs, out / 'neighbor-color.png')
        result = dict(status='passed', identity=identity,
                      previous_attribute=0x16, expected_attribute=0x36,
                      pixels_checked=64000, attributes_checked=1000,
                      whole_REU_guard_bytes=len(before),
                      scope='Packaged public edit/render; forced full renderer '
                            'and independent source/font oracle. CPU only.')
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print('PASS', out, flush=True)
    finally:
        f.close()
        full.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', type=Path, required=True)
    args = parser.parse_args()
    out = ROOT / 'build/geos-neighbor-color' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    print('RUN', out, flush=True)
    run(out, args.fixture)
