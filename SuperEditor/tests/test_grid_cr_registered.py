"""Real cold60/D81 CR transaction; no post-startup extra-image import seam."""
from pathlib import Path
import argparse
import binascii
import hashlib
import json
import test_grid_cr_suffix as public
import test_grid_cr_suffix_faults as faults
import test_grid_cr_suffix_unchanged as unchanged
from d81_image import D81Image


def authenticate(base):
    identity = json.loads((base/'freeze.json').read_text())
    names = identity['names']
    assert len(names) == len(set(names)) == 60 and names[-1] == 'row'
    report = json.loads((base/'build/editor-report.json').read_text())
    digest = bytes.fromhex(report['resident_binding']['digest'])
    disk = D81Image((base/'build/supereditor.d81').read_bytes())
    prg = (base/'build/editor.prg').read_bytes()
    assert hashlib.sha256(prg).hexdigest() == identity['prg_sha256'] == report['sha256']
    assert hashlib.sha256((base/'build/supereditor.d81').read_bytes()).hexdigest() == identity['disk_sha256']
    assert disk.read(b'SUPEREDITOR', kind=2).data == prg
    pairs = []
    for name in names:
        image = (base/f'build/overlays/{name}.seo').read_bytes()
        assert hashlib.sha256(image).hexdigest() == identity['assets'][name]
        assert image[20:36] == image[36:52] == digest
        assert binascii.crc_hqx(image[36:], 65535) == int.from_bytes(image[12:14], 'little')
        assert binascii.crc_hqx(image[:14]+image[16:36], 65535) == int.from_bytes(image[14:16], 'little')
        assert disk.read(name.upper().encode(), kind=1).data == image
        pairs.append(tuple(image[5:7]))
    assert len(set(pairs)) == 60 and pairs[-1] == (0, 29)
    assert (1, 29) in pairs, 'C29 lifecycle must remain registered'
    return dict(resident=report['sha256'], binding=digest.hex(), assets=60,
                D81=identity['disk_sha256'], R29=identity['assets']['row'])


def run(out, base, groups):
    out.mkdir(parents=True)
    identity = authenticate(base)
    old = public.make_gate

    def cold_gate(target, fixture, control=False):
        assert not control
        # Gate executes the frozen resident's genuine startup loop. Its ROM
        # transport seam checks every decoded filename and all60 actual imports.
        # Unlike the private prototype, no image is imported after startup.
        return public.observer.Gate(target, fixture)

    public.make_gate = cold_gate
    try:
        results = {}
        for name, fn in (('public', public.run), ('faults', faults.run),
                         ('unchanged', unchanged.run)):
            if name in groups:
                results[name] = fn(out/name, base)
        result = dict(status='PASS', identity=identity, groups=results,
                      scope=__doc__, extra_import_after_startup=False)
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        return result
    finally:
        public.make_gate = old


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--groups', default='public,faults,unchanged')
    a = p.parse_args()
    run(a.out.resolve(), a.fixture.resolve(), a.groups.split(','))
