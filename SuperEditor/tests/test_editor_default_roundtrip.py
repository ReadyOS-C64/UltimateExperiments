"""Build genuine Full→Plain→Full defaults and retain a cold-Plain D81 fixture.

Run only while owning the shared build. Restores the actual host configuration
and rebuilds in finally; no runtime preset, binding or capsule is substituted.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, subprocess, sys, zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'tools')]
import test_geos_editor as geos
import cpu_editor
from d81_image import D81Image


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity():
    report = json.loads((ROOT / 'build/editor-report.json').read_text())
    digest = bytes.fromhex(report['resident_binding']['digest'])
    disk = D81Image((ROOT / 'build/supereditor.d81').read_bytes())
    assert disk.read(b'SUPEREDITOR', kind=2).data == (ROOT / 'build/editor.prg').read_bytes()
    assets = {}
    for name in cpu_editor.NAMES:
        image = (ROOT / 'build/overlays' / (name + '.seo')).read_bytes()
        assert image[20:36] == image[36:52] == digest, ('actual binding', name)
        assert disk.read(name.upper().encode(), kind=1).data == image, ('actual D81', name)
        assets[name] = hashlib.sha256(image).hexdigest()
    assert disk.read(b'GEOSFONTS', kind=1).data == (ROOT / 'build/geos-font-catalog/font-pack.bin').read_bytes()
    return dict(resident=sha(ROOT / 'build/editor.prg'), binding=digest.hex(),
                assets=assets, disk=sha(ROOT / 'build/supereditor.d81'),
                default=report['symbols']['se_presentation_default'])


def run():
    out = ROOT / 'build/editor-default-roundtrip' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    config = ROOT / 'config/editor-defaults.toml'
    original = config.read_bytes()
    assert original.count(b'source_preset = "full"') == 1
    baseline = identity()
    assert baseline['default'] == 3
    print('RUN', out, flush=True)

    def build(name):
        with (out / name).open('wb') as log:
            subprocess.run(['make', '-j1', 'editor', 'disk'], cwd=ROOT,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        return identity()

    try:
        config.write_bytes(original.replace(b'source_preset = "full"', b'source_preset = "plain"'))
        plain = build('plain-build.log')
        assert plain['default'] == 0 and plain['binding'] != baseline['binding']
        frozen, sealed = geos.freeze(out)
        (frozen / 'actual-host-defaults.toml').write_bytes(config.read_bytes())
        with zipfile.ZipFile(frozen / 'product-sources.zip', 'a', zipfile.ZIP_DEFLATED) as archive:
            archive.write(config, 'config/editor-defaults.toml')
        result = dict(status='plain-frozen', baseline=baseline, plain=plain,
                      fixture=str(frozen), actual_host_config_only=True)
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print('COLDPLAIN', frozen, plain['resident'], flush=True)
    finally:
        config.write_bytes(original)
        restored = build('full-restore.log')
        assert restored == baseline, ('Full restore differs', restored, baseline)
        print('FULL_RESTORED', restored['resident'], 'all', len(restored['assets']), 'assets and actual D81 exact', flush=True)
    result['status'] = 'PASS'
    result['restored'] = restored
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    run()
