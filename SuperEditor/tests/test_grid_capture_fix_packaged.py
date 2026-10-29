"""Unchanged 78-frame CR-bit/pixel oracles on the packaged corrected C33."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, inspect, json
import test_grid_capture_fix as original

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--control', type=Path, required=True)
    args = p.parse_args()
    source = inspect.getsource(original.run)
    old = "frozen=out/'fixture';shutil.copytree(base,frozen);spec=importlib.util.spec_from_file_location('capturebuild',ROOT/'src/render/grid/capture-fix-candidate/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);seos,budget=b.build(out/'leaf',frozen);identity=json.load(open(frozen/'freeze.json'))"
    new = "frozen=out/'fixture';shutil.copytree(PACKAGED,frozen);identity=json.load(open(frozen/'freeze.json'));seos={n:(frozen/'build/overlays'/(n+'.seo')).read_bytes()for n in ['grid','geostail']};budget=dict(packaged=True)"
    assert source.count(old) == 1
    namespace = dict(vars(original), PACKAGED=args.fixture.resolve())
    exec(compile(source.replace(old, new), str(Path(__file__))+'::packaged-setup-only', 'exec'), namespace)
    out = ROOT / 'build/grid-capture-packaged' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    for name in ['grid', 'geostail']:
        image = (args.fixture / 'build/overlays' / (name+'.seo')).read_bytes()
        assert hashlib.sha256(image).hexdigest() == json.loads((args.fixture/'freeze.json').read_text())['assets'][name]
    print('RUN', out, flush=True)
    result = namespace['run'](out, args.control.resolve())
    result['packaged_fixture'] = str(args.fixture)
    result['control_scope'] = ('Same-build forced-full reference; historical old_capture_defects field records reference CR maps, not a newly reproduced historical defect.' if args.control.resolve() == args.fixture.resolve() else 'Separate control fixture; historical capture bytes retained.')
    result['setup_scope'] = 'No private assembler or different product image; unchanged independent trueCR/allpixel/reference/source/history/shim oracles.'
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
