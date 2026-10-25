"""Released wide-inline and ASM defect oracles on coherent packaged images."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, inspect, json, shutil
import test_geos_inline161_candidate as wide
import test_asm_word_editor_candidate as asm

ROOT = Path(__file__).resolve().parents[1]

def run(out, fixture, control, suite):
    if suite in ('capacity', 'wide'):
        target = out / 'gate'
        target.mkdir()
        result = (wide.public if suite == 'capacity' else wide.wide)(target, fixture)
    else:
        source = inspect.getsource(asm.run)
        start = source.index(' out.mkdir(')
        end = source.index(' dll=')
        setup = " out.mkdir(parents=True,exist_ok=True);frozen=out/'fixture';shutil.copytree(PACKAGED,frozen);old=((base/'build/overlays/geoslex.seo').read_bytes(),{});image=(frozen/'build/overlays/geoslex.seo').read_bytes();identity=json.loads((frozen/'freeze.json').read_text())\n"
        namespace = dict(vars(asm), PACKAGED=fixture)
        exec(compile(source[:start] + setup + source[end:], str(Path(__file__)) + '::packaged-setup', 'exec'), namespace)
        result = namespace['run'](out / 'gate', control)
    result['packaged_fixture'] = str(fixture)
    result['setup_scope'] = 'No assembler or overlay substitution. Original independent pixels, attributes, source, pending, lease and memory guards retained.'
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--control', type=Path, required=True)
    p.add_argument('--suite', choices=['capacity', 'wide', 'asm'], required=True)
    a = p.parse_args()
    out = ROOT / 'build/geos-hardening-packaged' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + a.suite)
    out.mkdir(parents=True)
    print('RUN', out, flush=True)
    run(out, a.fixture.resolve(), a.control.resolve(), a.suite)
