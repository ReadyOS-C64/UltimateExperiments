"""Actual styled GEOS root scheduler STOP/missing-worker recovery.

Frozen products, real bounded job11/12 services and independent semantic pixels.
No shared build or native/VIC claim. KERNAL/DOS are not invoked.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ctypes as C, hashlib, json, shutil, zipfile
import test_geos_editor as geos
import test_geos_semantic_editor as semantic

ROOT = geos.ROOT


def run(out, previous=None, smoke=False):
    frozen, identity = geos.freeze(out, previous)
    assert len(identity['names']) >= 31
    geos.grid.editor_fixture.ROOT = geos.grid.cpu_editor.ROOT = frozen
    geos.grid.editor_fixture.NAMES = geos.grid.cpu_editor.NAMES = identity['names']
    dll = geos.grid.runner(out)
    fonts = {n: (frozen/'fonts'/n).read_bytes() for n in geos.GEOS_FONTS+('native8.bin',)}
    data = semantic.FIXTURE
    cases, frames = [], []

    def reu(f):
        raw = C.create_string_buffer(16*1024*1024)
        dll.gm_reu(f.m.handle, len(raw), raw)
        return raw.raw

    def outside_cache(f, before, after, tag):
        _, bank = f.cache()
        start = bank*65536
        pos = 0
        # R27 base ends D528; current R28 transaction tail ends E568.
        # Presence is frozen by this fixture catalog; other bank tails stay exact.
        for a, b in ([(start, start+64)]+
                     [(start+0x200+i*0x800, start+0x200+(i+1)*0x800) for i in range(22)]+
                     [(start+0xB200,start+(0xEA88 if 'gfont' in f.assets else 0xE568 if 'geosdelta' in f.assets else 0xD528))]):
            assert after[pos:a] == before[pos:a], (tag, 'foreign/undeclared REU', pos, a)
            pos = b
        assert after[pos:] == before[pos:], (tag, 'REU tail')

    def exact(f, tag):
        canonical, catalog, before = f.canonical(), f.catalog(), reu(f)
        f.render()
        assert f.canonical() == canonical and f.catalog() == catalog
        assert f.merged() == data, (tag, 'source')
        bits, attrs, rows, _ = semantic.expected(f, data, fonts)
        assert f.read(0x6000, 8000) == bits, (tag, 'semantic bitmap')
        assert f.read(0x4000, 1000) == attrs, (tag, 'semantic attributes')
        assert f.read(0xC600, 1024) == f.shim
        assert not any(f.get(n, 1) for n in ('se_f_owner', 'se_fs_owned', 'se_doc_read_locks', 'se_e_job', 'se_e_draw_busy', 'se_e_error'))
        outside_cache(f, before, reu(f), tag)
        frames.append(dict(tag=tag, pixels=64000, source_bytes=len(data), rows=len(rows),
                           bitmap_sha256=hashlib.sha256(bits).hexdigest()))

    def pending(f, worker, nav=False):
        if nav:
            f.put('se_gc_width', 0, 1) #derived invalidation forces real cold navigation
            f.call('se_editor_command', 37)
            job = 12
        else:
            f.put('se_gc_width', 0, 1) #force producer, not cached repaint
            r = f.call('se_editor_render')
            assert not r.p & 1
            job = 11
        for step in range(100000):
            assert f.get('se_e_job', 1) == job, (worker, nav, 'job ended before target', f.debug())
            requested, operation = f.m.read(0x9135), f.m.read(0x9136)
            active = f.m.read(0x8B40) if worker == 22 else f.m.read(0x912D)
            if requested == worker and operation == 1 and active:
                assert f.get('se_f_owner', 1) == 4
                if worker != 22:
                    assert f.get('se_doc_read_locks', 1) == 1
                return step
            f.call('se_editor_service')
        raise AssertionError(('pending worker not reached', worker, nav))

    def remove(f, identity_, slot):
        idx = next(i for i in range(f.s['se_overlay_capacity'])
                   if f.m.read(f.s['se_overlay_ids']+i) == identity_
                   and f.m.read(f.s['image_slot']+i) == slot)
        f.m.write(f.s['se_overlay_ids']+idx, 0)
        f.m.write(f.s['se_overlay_active']+slot, 0)
        return idx

    matrix = [(worker, nav, action) for worker, nav in
              [(20, False), (24, False), (25, False), (22, False), (20, True), (24, True)]
              for action in ('STOP', 'missing-worker', 'missing-R14')
              if not (worker == 22 and action == 'missing-R14')]
    if smoke:
        matrix = [(25, False, 'STOP')]
    for serial, (worker, nav, action) in enumerate(matrix):
        f = geos.Fixture(out, frozen, dll, True)
        tag = f'{serial:02d}-job{12 if nav else 11}-C{worker}-{action}'
        try:
            f.source(data)
            f.command(99)
            # Poison caller storage the old zero-filled CPU fixture concealed.
            f.m.load(0x8B40, bytes([0xA5])*192)
            f.m.load(0x8300, bytes([0xFF])*160)
            exact(f, tag+'-initial')
            if nav:
                f.position(5)
            before = f.canonical()
            before_reu, before_catalog = reu(f), f.catalog()
            steps = pending(f, worker, nav)
            lease = f.get('se_doc_read_locks', 1)
            if action == 'STOP':
                f.queued(3)
                f.call('se_editor_service')
                assert f.get('se_e_error', 1) == 0
            else:
                identity_, slot = (14, 0) if action == 'missing-R14' else (worker, 1)
                idx = remove(f, identity_, slot)
                f.call('se_editor_service')
                assert f.get('se_e_error', 1) == 0x17, (tag, 'original admission error', f.get('se_e_error', 1))
                f.m.write(f.s['se_overlay_ids']+idx, identity_)
            assert not any(f.get(n, 1) for n in ('se_f_owner', 'se_doc_read_locks', 'se_fs_owned', 'se_e_job', 'se_e_draw_busy')), (tag, f.debug())
            assert f.read(0x8B40, 2) == b'\0\0' and f.m.read(0x912D) == 0
            assert f.canonical() == before and f.read(0xC600, 1024) == f.shim
            # A real harmless input acknowledges the error. Never host-edit
            # error state to make the subsequent public render appear healthy.
            if action != 'STOP':
                f.key(0x8B)
                f.key(0x8B)
            exact(f, tag+'-recovered')
            outside_cache(f, before_reu, reu(f), tag+'-entire-recovery')
            assert f.catalog() == before_catalog
            cases.append(dict(tag=tag, worker=worker, root_job=12 if nav else 11,
                              action=action, steps_to_pending=steps, owned_read_lease=lease))
            (out/'progress.json').write_text(json.dumps(cases, indent=2)+'\n')
        finally:
            f.close()
    result = dict(status='passed', identity=identity, cases=cases, frames=frames,
                  pixels_checked=len(frames)*64000, full_REU_guard_bytes=16*1024*1024,
                  scope='Actual frozen styled GEOS root job11/12 STOP/missing worker/R14 recovery and independent full pixels; no native/VIC/DOS claim.')
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    archive = ROOT/'agentsworking/evidence/M7'/(out.name+'-geos-semantic-recovery')
    archive.mkdir(parents=True)
    for name in ['result.json', 'progress.json']:
        shutil.copy2(out/name, archive/name)
    for name in ['product-sources.zip', 'freeze.json']:
        shutil.copy2(frozen/name, archive/name)
    shutil.copy2(Path(__file__), archive/Path(__file__).name)
    pointer = dict(status='passed', evidence=str(archive.relative_to(ROOT)),
                   prg_sha256=identity['prg_sha256'], disk_sha256=identity['disk_sha256'],
                   cases=len(cases), pixels_checked=result['pixels_checked'])
    (ROOT/'agentsworking/evidence/M7/geos-semantic-recovery-checkpoint.json').write_text(json.dumps(pointer, indent=2)+'\n')
    print(json.dumps(pointer, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    out = ROOT/'build/geos-semantic-recovery'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    print('RUN '+str(out), flush=True)
    run(out, args.fixture, args.smoke)
