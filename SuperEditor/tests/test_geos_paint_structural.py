"""Public CR deletion and narrow live-packet edits on an authenticated fixture.

CPU modeled-ROM/source import, never a native or physical-key claim. No capsule,
GEC, collector, source-map or parser certificate substitution. Historical broken
fixtures must fail; --record-failures only keeps running the other cases and
still exits nonzero. All 16MiB are compared against exact checked DMA writes;
pending edit publications additionally may write only explicit typed-FE spans.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ctypes as C, hashlib, json, traceback, zipfile
import test_geos_editor as geos
import test_cache_hotpath_profile as hot
import test_cache_observer as observer
import test_plain_geos as plain

ROOT = geos.ROOT


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def authenticate(base):
    identity = json.loads((base / 'freeze.json').read_text())
    assert len(identity['names']) in (62, 63)
    assert sha((base / 'build/editor.prg').read_bytes()) == identity['prg_sha256']
    assert sha((base / 'build/supereditor.d81').read_bytes()) == identity['disk_sha256']
    for name, digest in identity['assets'].items():
        assert sha((base / f'build/overlays/{name}.seo').read_bytes()) == digest, name
    for name, digest in identity['fonts'].items():
        assert sha((base / 'fonts' / name).read_bytes()) == digest, name
    with zipfile.ZipFile(base / 'product-sources.zip') as z:
        for name, digest in identity['sources'].items():
            assert sha(z.read(name)) == digest, name
        abi = z.read('src/render/geos/editor.inc')
        for term in (b'GPR_USED=842', b'GP_CACHE_VERSION=3', b'GP_SLOT_BASE=$0200',
                     b'GP_SLOT_SIZE=$0800', b'GP_MAX_GLYPHS=161'):
            assert term in abi
        paint = 'paint' in identity['names']
        if paint:
            a = z.read('src/render/geos/paint-convergence/api.inc')
            for term in (b'CV_PACKET=$D568', b'CV_CERT=$DD68', b'CV_NEXT=$DE68', b'CV_SIZE=240'):
                assert term in a
    return identity, paint


def reu(f):
    b = C.create_string_buffer(16 * 1024 * 1024)
    f.dll.gm_reu(f.m.handle, len(b), b)
    return b.raw


def stable(f):
    fields = [('se_doc_meta', 15), ('se_doc_generation', 2), ('se_doc_length', 3),
              ('se_h_current', 4), ('se_h_saved', 4), ('se_h_end', 2),
              ('se_h_cursor', 2), ('se_h_counter', 4), ('se_clip_token', 5),
              ('se_clip_length', 3), ('se_sel_mark', 1), ('se_sel_anchor', 3)]
    return f.read(f.s['se_doc_roots'], 512) + b''.join(f.read(f.s[n], w) for n, w in fields)


def state(f):
    return dict(error=f.get('se_e_error', 1), caret=f.get('se_hot_caret'),
                top=f.get('se_v_top'), sequence=f.get('se_e_draw_sequence', 2),
                fast=f.m.read(0x9148), CV=f.read(0x9149, 47).hex(),
                GEC=f.read(0xcfe8, 20).hex(), debug=f.debug())


def audit_start(f):
    old = reu(f)
    fields = ('se_reu_copy', 'se_reu_logical', 'se_reu_offset', 'se_reu_length',
              'se_reu_map', 'se_reu_logical_owner', 'se_reu_physical_owner')
    f.dll.fr_begin(*(f.s[n] for n in fields))
    return old


def audit_end(f, old, *, pending, paint):
    f.dll.fr_end()
    assert not f.dll.fr_bad(), 'invalid/unexpected typed DMA stash'
    mask = C.create_string_buffer(len(old)); f.dll.fr_mask(mask)
    new = reu(f)
    assert all(a == b or permitted for a, b, permitted in zip(old, new, mask.raw)), \
        'whole16MiB write outside exact observed checked DMA spans'
    handle = f.get('se_gc_handle', 1); physical = f.m.read(f.s['se_reu_map'] + handle)
    assert handle and physical and f.get('se_gc_epoch', 2) == f.get('se_reu_epoch', 2)
    assert f.m.read(f.s['se_reu_logical_owner'] + handle) == 0xfe
    assert f.m.read(f.s['se_reu_physical_owner'] + physical) == 0xfe
    # No source/history/analysis-bank write is allowed during these pending
    # repaint intervals. Undo/Redo have independently checked exact typed DMA.
    spans = [(0, 64), (0x600, 0x680), (0xb200, 0xd568)]
    spans += [(0x200 + i * 0x800, 0x200 + i * 0x800 + 842) for i in range(22)]
    spans += [(0x700 + i * 0x800, 0x740 + i * 0x800) for i in range(22)]
    if paint:
        spans += [(0xd568, 0xd568 + 842), (0xdd68, 0xdd68 + 240), (0xde68, 0xde68 + 240)]
        spans += [(0x680 + i * 0x800, 0x680 + i * 0x800 + 842) for i in range(22) if i != 2]
    if pending:
        wanted = bytearray(old)
        for lo, hi in spans:
            a, b = physical * 65536 + lo, physical * 65536 + hi
            wanted[a:b] = new[a:b]
        assert wanted == new, 'pending edit changed REU outside explicit FE packet/chrome/proof spans'
    assert f.read(0xc600, 1024) == f.shim
    return dict(whole16MiB_checked_DMA=True, pending_FE_only=pending,
                typed_FE_physical=physical, changed_bytes=sum(a != b for a, b in zip(old, new)),
                old_sha256=sha(old), new_sha256=sha(new))


def run(out, base, cases, presets, record_failures=False):
    out.mkdir(parents=True, exist_ok=False)
    identity, paint = authenticate(base)
    geos.grid.editor_fixture.ROOT = geos.grid.cpu_editor.ROOT = base
    geos.grid.editor_fixture.NAMES = geos.grid.cpu_editor.NAMES = identity['names']
    dll = observer.runner(out)
    fonts = {n: (base / 'fonts' / n).read_bytes() for n in geos.GEOS_FONTS + ('native8.bin',)}
    results = []
    for case in cases:
        for preset in presets:
            tag = case + '-' + preset; dest = out / tag; dest.mkdir()
            f = geos.Fixture(out, base, dll, True); observations = []; active_audit = None
            data = geos.native_text('First source line.\rSecond source line.\rTail.' if case == 'cr-back'
                                    else '.' * 400 + '\rTail.')
            deleted = data.index(13) if case == 'cr-back' else 84
            wanted = data[:deleted] + data[deleted + 1:]
            caps = {'full': 3, 'markdown': 1}[preset]
            def pixels(source, label):
                bits, attrs, _ = plain.expected(f, source, fonts, caps)
                assert f.read(0x6000, 8000) == bits, (label, 'independent bitmap')
                assert f.read(0x4000, 1000) == attrs, (label, 'independent attributes')
                return sha(bits + attrs)
            try:
                f.source(data, physical=256); f.command(99); hot.drain(f)
                f.typed(geos.native_text('goto ' + ('2' if case == 'cr-back' else '1'))); hot.drain(f)
                if case == 'narrow-back':
                    for _ in range(85): f.key(0x1d)
                    hot.drain(f)
                f.typed(geos.native_text('syntax plain')); hot.drain(f)
                f.typed(geos.native_text('syntax ' + preset)); hot.drain(f)
                assert f.get('se_hot_caret') == deleted + 1
                pixels(data, 'before'); history0 = f.get('se_h_current', 4)
                clip = f.read(f.s['se_clip_token'], 5) + f.read(f.s['se_clip_length'], 3)
                catalog = f.catalog(); committed = stable(f); oldbits = f.read(0x6000, 8000)
                active_audit = audit_start(f)
                f.key(0x14)
                assert f.merged() == wanted and f.get('se_hot_pending', 1) == 1
                assert stable(f) == committed
                before_repaint = f.canonical()
                try: hot.drain(f)
                finally:
                    checks = audit_end(f, active_audit, pending=True, paint=paint); active_audit = None
                assert f.canonical() == before_repaint, 'painting mutated canonical/history/hotgap state'
                assert f.merged() == wanted and f.get('se_hot_caret') == deleted
                observations.append(dict(action='BACK', pixels=pixels(wanted, 'BACK'), state=state(f), guards=checks))
                for command, source, label in ((16, data, 'Undo'), (17, wanted, 'Redo')):
                    active_audit = audit_start(f)
                    try: f.command(command); hot.drain(f)
                    finally:
                        checks = audit_end(f, active_audit, pending=False, paint=paint); active_audit = None
                    assert f.merged() == source, (label, 'independent source')
                    if command == 16: assert f.get('se_h_current', 4) == history0
                    else: assert f.get('se_h_current', 4) != history0
                    assert f.read(f.s['se_clip_token'], 5) + f.read(f.s['se_clip_length'], 3) == clip
                    assert f.catalog() == catalog and not f.get('se_f_owner', 1) and not f.get('se_doc_read_locks', 1)
                    observations.append(dict(action=label, pixels=pixels(source, label), state=state(f), guards=checks))
                result = dict(case=tag, status='PASS', observations=observations)
            except BaseException as error:
                if active_audit is not None:
                    try: audit_end(f, active_audit, pending=False, paint=paint)
                    finally: active_audit = None
                (dest / 'failure-ram.bin').write_bytes(f.read(0, 0xd000))
                (dest / 'traceback.txt').write_text(traceback.format_exc())
                result = dict(case=tag, status='FAIL', exception=repr(error), state=state(f),
                              source_exact=f.merged() == wanted, observations=observations)
                if 'checks' in locals(): result['guards'] = checks
            finally: f.close()
            results.append(result); (dest / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            print(tag, result['status'], flush=True)
            if result['status'] == 'FAIL' and not record_failures: break
        if results[-1]['status'] == 'FAIL' and not record_failures: break
    result = dict(status='PASS' if all(c['status'] == 'PASS' for c in results) else 'FAIL',
                  fixture=str(base), identity=identity, cases=results,
                  scope=__doc__, no_capsule_or_authority_substitution=True)
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', required=True, type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--case', choices=('cr-back', 'narrow-back'), action='append')
    parser.add_argument('--preset', choices=('full', 'markdown'), action='append')
    parser.add_argument('--record-failures', action='store_true')
    args = parser.parse_args()
    out = args.out or ROOT / 'build/paint-integration-review' / ('structural-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    r = run(out, args.fixture.resolve(), args.case or ['cr-back', 'narrow-back'],
            args.preset or ['full', 'markdown'], args.record_failures)
    raise SystemExit(0 if r['status'] == 'PASS' else 1)
