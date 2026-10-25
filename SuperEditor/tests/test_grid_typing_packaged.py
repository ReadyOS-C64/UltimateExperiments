"""All released typing/refusal/mixed-pair oracles on unchanged packaged images."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, inspect, json, zipfile
import test_grid_typing_candidate as original

ROOT = Path(__file__).resolve().parents[1]


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--control', type=Path, required=True)
    args = p.parse_args()
    packaged = args.fixture.resolve()
    identity = json.loads((packaged / 'freeze.json').read_text())
    pair = {name: (packaged / 'build/overlays' / (name + '.seo')).read_bytes()
            for name in ['grid', 'geostail']}
    for name, image in pair.items():
        assert hashlib.sha256(image).hexdigest() == identity['assets'][name]
    assert len(pair['grid']) == 36+4096 and len(pair['geostail']) == 36+3586
    source = inspect.getsource(original.run)
    old = "frozen=out/'fixture';shutil.copytree(base,frozen)"
    new = "frozen=out/'fixture';shutil.copytree(PACKAGED,frozen)"
    assert source.count(old) == 1
    source = source.replace(old, new)
    old = "spec=importlib.util.spec_from_file_location('gridtypingbuild',ROOT/'src/render/grid/typing-candidate/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);seos,budget=b.build(out/'leaf',frozen)"
    new = "seos={};budget=dict(packaged=True,pair=PAIR)"
    assert source.count(old) == 1
    source = source.replace(old, new)
    namespace = dict(vars(original), PACKAGED=packaged,
                     PAIR={n:dict(payload=len(v)-36,sha256=hashlib.sha256(v).hexdigest()) for n,v in pair.items()})
    exec(compile(source, str(Path(__file__))+'::packaged-only-setup', 'exec'), namespace)
    out = ROOT / 'build/grid-typing-packaged' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    with zipfile.ZipFile(out / 'verifier.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for path in [Path(__file__), Path(original.__file__)]:
            z.write(path, path.relative_to(ROOT))
    print('RUN', out, flush=True)
    result = namespace['run'](out, args.control.resolve())
    result['packaged_fixture'] = str(packaged)
    result['setup_scope'] = 'Current immutable fixture, no private assembler or asset substitution; unchanged released positive/refusal/mixed-generation oracles and old control.'
    (out / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
