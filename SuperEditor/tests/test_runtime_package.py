"""Real c1541 runtime packaging, no diagnostic dependencies, no-op and rollback."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, json, shutil, subprocess, sys, zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from d81_image import D81Image


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(fixture, out):
    out.mkdir(parents=True)
    project = out / 'project'
    project.mkdir()
    with zipfile.ZipFile(fixture / 'product-sources.zip') as z:
        z.extractall(project)
    for name in ('package.py', 'cache_job_build.py'):
        shutil.copyfile(ROOT / 'tools' / name, project / 'tools' / name)
    (project / 'build/overlays').mkdir(parents=True)
    for name in ('editor.prg', 'editor.lbl', 'editor-report.json', 'supereditor.d81'):
        shutil.copyfile(fixture / 'build' / name, project / 'build' / name)
    identity = json.loads((fixture / 'freeze.json').read_text())
    for name in identity['names']:
        shutil.copyfile(fixture / f'build/overlays/{name}.seo', project / f'build/overlays/{name}.seo')
    fonts = project / 'build/geos-font-catalog/font-pack.bin'
    fonts.parent.mkdir()
    shutil.copyfile(fixture / 'build/geos-font-catalog/font-pack.bin', fonts)
    spec = importlib.util.spec_from_file_location('runtime_package_guard', project / 'tools/cache_job_build.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    # No probe program, malformed SEO or probe report is supplied.
    assert not (project / 'build/overlay-probe-report.json').exists()
    dev = project / 'build/supereditor.d81'
    dev_before = dev.read_bytes(), dev.stat().st_mtime_ns
    result = guard.ensure_disk(project, runtime=True)
    assert result['packaged'] and result['editor_capsules'] == len(identity['names'])
    disk = project / 'build/supereditor-runtime.d81'
    manifest = project / 'build/runtime-disk-manifest.json'
    proof = project / 'build/runtime-disk-content.json'
    expected = {b'SUPEREDITOR', b'GEOSFONTS', *(n.upper().encode() for n in identity['names'])}

    def verify():
        image = D81Image(disk.read_bytes())
        assert {e.name for e in image.entries()} == expected
        for rel, native in guard.package_inputs(project, True)['members']:
            name = native.split(',')[0].upper().encode()
            assert image.read(name, kind=1 if native.endswith(',s') else 2).data == (project / rel).read_bytes()
        assert (dev.read_bytes(), dev.stat().st_mtime_ns) == dev_before
        return image

    image = verify()
    trap = out / 'never-c1541'
    trap.write_text('#!/bin/sh\nexit 97\n')
    trap.chmod(0o755)
    def snapshot():
        return {str(p.relative_to(project)): (sha(p), p.stat().st_mtime_ns)
                for p in (project / 'build').rglob('*') if p.is_file()}
    before = snapshot()
    assert not guard.ensure_disk(project, str(trap), True)['packaged']
    assert before == snapshot(), 'runtime no-op changed product bytes/mtime'

    # A previous real disk member can be intentionally removed by a new profile.
    retired = project / 'build/retired.seq'
    retired.write_bytes(b'old diagnostic data')
    def old_medium():
        r = subprocess.run(['c1541', '-attach', str(disk), '-write', str(retired), 'retired,s'], capture_output=True)
        assert r.returncode == 0
        m = json.loads(manifest.read_text())
        m['command'][-1:-1] = ['-write', str(retired), 'retired,s']
        m['sha256'] = sha(disk)
        manifest.write_text(json.dumps(m, indent=2) + '\n')
        assert D81Image(disk.read_bytes()).read(b'RETIRED', kind=1).data == retired.read_bytes()
    old_medium()
    assert guard.ensure_disk(project, runtime=True)['packaged']
    verify()
    assert retired.read_bytes() == b'old diagnostic data'

    # Retiring a member does not permit concurrent changes to its input bytes.
    old_medium()
    prior = {p: p.read_bytes() for p in (disk, manifest, proof)}
    wrapper = out / 'change-retired-c1541'
    actual = shutil.which('c1541')
    wrapper.write_text('#!' + sys.executable + '\nimport os,sys\nfrom pathlib import Path\n'
                       + 'Path(' + repr(str(retired)) + ').write_bytes(b"concurrent change")\n'
                       + 'os.execv(' + repr(actual) + ',[' + repr(actual) + ',*sys.argv[1:]])\n')
    wrapper.chmod(0o755)
    try:
        guard.ensure_disk(project, str(wrapper), True)
    except RuntimeError as error:
        assert 'input changed during packaging: build/retired.seq' in str(error)
    else:
        raise AssertionError('concurrent retired-input change accepted')
    assert all(p.read_bytes() == data for p, data in prior.items()), 'failed publication changed prior medium/proof'
    retired.write_bytes(b'old diagnostic data')
    assert guard.ensure_disk(project, runtime=True)['packaged']
    verify()

    # A real external packager failure must preserve the existing runtime image.
    prior = {p: p.read_bytes() for p in (disk, manifest, proof)}
    font_bytes = fonts.read_bytes()
    fonts.write_bytes(font_bytes[:-1] + bytes([font_bytes[-1] ^ 1]))
    try:
        guard.ensure_disk(project, str(trap), True)
    except subprocess.CalledProcessError:
        pass
    else:
        raise AssertionError('failed c1541 accepted')
    assert all(p.read_bytes() == data for p, data in prior.items())
    fonts.write_bytes(font_bytes)
    assert not guard.ensure_disk(project, str(trap), True)['packaged']
    verify()
    report = dict(status='PASS', scope=__doc__, fixture=str(fixture),
                  editor_images=len(identity['names']), runtime_files=len(expected),
                  diagnostic_dependencies=0, runtime_disk_sha256=sha(disk),
                  dev_disk_untouched=True, all_runtime_members_exact=True,
                  no_op_bytes_and_mtimes=True, intentional_member_removal=True,
                  concurrent_retired_input_refuses_and_rolls_back=True,
                  failed_packager_preserves_disk_manifest_proof=True,
                  development_file_blocks=sum(e.blocks for e in D81Image(dev.read_bytes()).entries()),
                  runtime_file_blocks=sum(e.blocks for e in image.entries()))
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    out = args.out or ROOT / 'build/runtime-package' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run(args.fixture.resolve(), out.resolve())
