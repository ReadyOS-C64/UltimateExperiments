"""Actual registered62 rebase CPU gate, with no capsule substitution/build.

The mature independent oracle/protocol suite is reused through explicit,
asserted host-only adaptations. The generated run function is saved alongside
its receipt. Product code and source/read/parser results are never replaced.
The historical batch gate masked the whole FE bank; this gate instead permits
only the authenticated source/GTF reservation [0,64)+[0200,EA88), preserving its
prefix hole and preview/body/glyph tail, plus the exact existing COW spans.
"""
from pathlib import Path
from datetime import datetime, timezone
from types import MappingProxyType
import argparse, binascii, hashlib, inspect, json, re, zipfile
import test_cache_edit_rebase_batch as suite
from bindings import verify
from d81_image import D81Image

ROOT = Path(__file__).resolve().parents[1]
FE_SPANS = ((0, 64), (0x200, 0xEA88))
STAGES = {'clex': 'code-typing/stage', 'code': 'code-typing/worker',
          'type': 'style-typing/stage', 'gtype': 'style-typing/worker'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def metadata(root, name):
    paths = [root / 'build/overlays' / name,
             root / 'build/cache-editor' / name,
             root / 'build/lexical' / name,
             root / 'build/cache-rebase' / name]
    if name in STAGES:
        paths.insert(0, root / 'build/geos-prod' / STAGES[name])
    image = (root / 'build/overlays' / (name + '.seo')).read_bytes()
    for p in paths:
        if all(p.with_suffix(e).exists() for e in ('.bin', '.lbl', '.map')):
            if p.with_suffix('.bin').read_bytes() == image[36:]:
                return p
    raise AssertionError((name, 'no source-matched raw/labels/map', paths))


def authenticate(fixture, project):
    """Read-only proof of the actual package/source/output cohort."""
    ident = json.loads((fixture / 'freeze.json').read_text())
    report = json.loads((fixture / 'build/editor-report.json').read_text())
    names = ident['names']
    assert len(names) == len(set(names)) == 62 and names[-2:] == ['parse', 'xform']
    seal = verify(fixture / 'build/editor.prg', fixture / 'build/editor.lbl')
    assert seal['resident_sha256'] == ident['prg_sha256'] == report['sha256']
    assert seal['digest'] == report['resident_binding']['digest']
    assert sha(fixture / 'build/supereditor.d81') == ident['disk_sha256']
    for name in ('editor.prg', 'editor.lbl', 'editor.map', 'editor-report.json'):
        assert (fixture / 'build' / name).read_bytes() == (project / 'build' / name).read_bytes(), name
    disk = D81Image((fixture / 'build/supereditor.d81').read_bytes())
    assert disk.read(b'SUPEREDITOR', kind=2).data == (fixture / 'build/editor.prg').read_bytes()
    pack = (fixture / 'build/geos-font-catalog/font-pack.bin').read_bytes()
    assert disk.read(b'GEOSFONTS', kind=1).data == pack
    assert pack == (project / 'build/geos-font-catalog/font-pack.bin').read_bytes()
    source_hashes = {}
    with zipfile.ZipFile(fixture / 'product-sources.zip') as z:
        for name, h in ident['sources'].items():
            data = z.read(name)
            assert hashlib.sha256(data).hexdigest() == h, ('frozen source hash', name)
            assert (project / name).read_bytes() == data, ('project differs from frozen source', name)
        contracts = {
            'src/render/geos/editor.inc': (b'GP_MAX_LINES=22', b'GP_SLOT_BASE=$0200', b'GP_SLOT_SIZE=$0800'),
            'src/render/geos/caret-cache.inc': (b'GCC_BITMAP=$B200', b'GCC_ATTRIBUTES=GCC_BITMAP+8000', b'GCC_END=GCC_ATTRIBUTES+1000'),
            'src/render/geos/edit-cache.inc': (b'GEX_OLD_HEADER=$D528', b'GEX_TAIL_END=$E568'),
            'src/render/geos/typing-font-cache.inc': (b'GTF_DATA=$E568', b'GTF_WIDTHS=$E9E8', b'GTF_META=$EA68'),
            'src/cache/edit-rebase-integration/api.inc': (b'S_BATCH=S+79', b'S_READER=BC_FRAME+173'),
        }
        for name, terms in contracts.items():
            data = z.read(name)
            assert all(t in data for t in terms), (name, 'unrecognized typed state contract')
            source_hashes[name] = hashlib.sha256(data).hexdigest()
    binding = bytes.fromhex(seal['digest'])
    pairs, outputs = [], {}
    for name in names:
        path = fixture / 'build/overlays' / (name + '.seo')
        image = path.read_bytes()
        assert sha(path) == ident['assets'][name]
        assert image == (project / 'build/overlays' / (name + '.seo')).read_bytes()
        assert image[:5] == b'SEO2\x02' and image[20:36] == image[36:52] == binding
        assert int.from_bytes(image[8:10], 'little') == len(image) - 36 <= 4096
        assert int.from_bytes(image[10:12], 'little') == 16
        assert binascii.crc_hqx(image[36:], 65535) == int.from_bytes(image[12:14], 'little')
        assert binascii.crc_hqx(image[:14] + image[16:36], 65535) == int.from_bytes(image[14:16], 'little')
        assert disk.read(name.upper().encode(), kind=1).data == image
        a, b = metadata(fixture, name), metadata(project, name)
        outputs[name] = {}
        for ext in ('.bin', '.lbl', '.map'):
            assert a.with_suffix(ext).read_bytes() == b.with_suffix(ext).read_bytes(), (name, ext)
            outputs[name][ext] = sha(a.with_suffix(ext))
        pairs.append(tuple(image[5:7]))
    assert len(set(pairs)) == 62 and pairs[-2:] == [(1, 41), (0, 34)]
    return dict(resident=ident['prg_sha256'], binding=seal['digest'], disk=ident['disk_sha256'],
                assets=62, source_contracts=source_hashes, actual_outputs=outputs,
                FE_spans=FE_SPANS, source_zip_sha256=sha(fixture / 'product-sources.zip'))


def fe_allowed(g, f, before, after):
    """Derive the physical FE bank only through the authenticated runtime API."""
    _, bank = f.raw_cache()  # checks handle, epoch, logical and physical owner FE
    want = bytearray(before)
    for a, b in FE_SPANS:
        lo, hi = bank * 65536 + a, bank * 65536 + b
        want[lo:hi] = after[lo:hi]
    return want


def adaptation(out):
    """Reuse protocol assertions; remove all host asset substitutions explicitly."""
    text = inspect.getsource(suite.run)
    replacements = [
        ("images={'parse':(VARIANT_DIR/'parse.seo').read_bytes()};g=", "g="),
        ("  for variant in (variant,):\n   f.assets=dict(original)\n   if variant=='candidate':f.assets.update(images)", "  for variant in (variant,):"),
        ("   f.assets=dict(original);f.assets.update(images)\n", ""),
        ("fe=f.raw_cache()[1];allowed[fe*65536:(fe+1)*65536]=after[fe*65536:(fe+1)*65536]", "allowed=fe_allowed(g,f,before_render,after)"),
        ("after=g.reu();allowed=bytearray(before);fe=f.raw_cache()[1];allowed[fe*65536:(fe+1)*65536]=after[fe*65536:(fe+1)*65536]", "after=g.reu();allowed=fe_allowed(g,f,before,after)"),
        ("scope='Private bounded4 C41 substitution; real cold62", "scope='Actual registered cold62, no capsule substitution; typed FE source/GTF only; real cold62"),
    ]
    # The refusal phrase contains the same whole-bank substring as the repeat
    # phrase. Apply its complete form first, then require every exact count.
    replacements[3:5] = replacements[3:5][::-1]
    for old, new in replacements:
        assert text.count(old) == 1, ('legacy protocol drift: review adaptation', old, text.count(old))
        text = text.replace(old, new)
    assert 'f.assets.update' not in text and 'images=' not in text
    assert 'fe*65536:(fe+1)*65536' not in text
    (out / 'registered-run.py').write_text(text)
    namespace = dict(suite.__dict__, fe_allowed=fe_allowed, __file__=str(Path(__file__).resolve()))
    exec(compile(text, str(out / 'registered-run.py'), 'exec'), namespace)
    return namespace


def run(out, fixture, project, cases=('repeat', 'small', 'high24')):
    out.mkdir(parents=True)
    seal = authenticate(fixture, project)
    (out / 'authentication.json').write_text(json.dumps(seal, indent=2) + '\n')
    (out / 'test_cache_rebase_registered.py').write_bytes(Path(__file__).read_bytes())
    (out / 'test_cache_edit_rebase_batch.py').write_bytes(Path(suite.__file__).read_bytes())
    namespace = adaptation(out)
    namespace['VARIANT_DIR'] = fixture / 'build/cache-rebase'
    original_gate = suite.ob.Gate
    cpu = suite.ob.geos.grid.cpu_editor
    old_startup = cpu.startup
    startup_receipts, typed_intervals = [], []

    def startup(m, s, assets, *args, **kwargs):
        before = bytes(m.read(0xC600 + i) for i in range(1024))
        names = old_startup(m, s, assets, *args, **kwargs)
        assert names == json.loads((fixture / 'freeze.json').read_text())['names']
        assert bytes(m.read(0xC600 + i) for i in range(1024)) == before
        for i, name in enumerate(names):
            logical = m.read(s['se_overlay_asset'] + i // 16)
            bank = m.read(s['se_reu_map'] + logical)
            assert m.read(s['se_reu_logical_owner'] + logical) == 2
            assert m.read(s['se_reu_physical_owner'] + bank) == 2
            image = assets[name]
            offset = (i % 16) * 4096
            raw = bytes(m.lib.zeropage_peddle_read_reu(m.handle, bank * 65536 + offset + j)
                        for j in range(len(image) - 36))
            assert raw == image[36:], ('actual startup asset', name)
        startup_receipts.append(dict(names=names, all62_payloads_exact=True, shim1024=True))
        return names

    class RegisteredGate(original_gate):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # This immutable transport dictionary contains only authenticated
            # actual packaged images; no test can append or substitute capsules.
            self.f.assets = MappingProxyType(dict(self.f.assets))
            original_render = self.f.render
            def render():
                before = self.audit_begin()
                self.dll.pb_arena_begin(True)  # authorize observed owned53 COW writes
                try:
                    result = original_render()
                    self.audit_end(before, 'registered62-render')
                    typed_intervals.append(dict(writes=int(self.dll.fr_writes())))
                    return result
                finally:
                    self.dll.fr_end()
                    self.dll.pb_arena_begin(False)
            self.f.render = render

    suite.ob.Gate, cpu.startup = RegisteredGate, startup
    results = {}
    try:
        for case in cases:
            length, repeats, protocols = {'repeat': (8000, 4, True),
                                         'small': (1000, 1, False),
                                         'high24': (66000, 2, False)}[case]
            target = out / case
            target.mkdir()
            namespace['run'](target, fixture, length, repeats, protocols, 'candidate')
            result = json.loads((target / 'result.json').read_text())
            assert result['passed'] and len(result['records']) == repeats
            if protocols:
                assert len(result['protocols']) == 30
            results[case] = dict(records=repeats, protocols=len(result['protocols']))
    finally:
        suite.ob.Gate, cpu.startup = original_gate, old_startup
    assert len(startup_receipts) == len(cases)
    result = dict(status='PASS', identity=seal, cases=results, startup=startup_receipts,
                  typed_DMA_intervals=len(typed_intervals), observed_checked_stashes=sum(x['writes'] for x in typed_intervals),
                  FE_policy='Only authenticated [0,64)+[0200,EA88); preserve64..1FF andEA88..FFFF. Other banks exact except precise COW/root/directory/journal spans.',
                  historical_scope_correction='Earlier batch/repeat gates allowed the whole FE bank; their precise-COW evidence did not prove the FE hole/tail. This registered gate is the first tightened repeat/fault/small/high24 proof.',
                  verifiers=dict(registered_sha256=sha(Path(__file__)), protocol_sha256=sha(Path(suite.__file__)), generated_sha256=sha(out/'registered-run.py')),
                  scope='Actual registered62 source/project/D81 and startup; no app build, capsule substitution, extra catalog imports, native or hardware. Existing host-only CPU observer compilation and ROM/font transport seams retained.')
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--project', type=Path, required=True)
    p.add_argument('--case', choices=('repeat', 'small', 'high24', 'all'), default='all')
    p.add_argument('--out', type=Path)
    args = p.parse_args()
    out = args.out or ROOT / 'build/cache-rebase-registered' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    print('RUN', out, flush=True)
    run(out.resolve(), args.fixture.resolve(), args.project.resolve(),
        ('repeat', 'small', 'high24') if args.case == 'all' else (args.case,))
