"""Run unchanged C23 navigation/fault oracles on the private local candidate.

The current candidate first recovers code space with fixed three-byte copies;
the local semantic-checkpoint consumer is deliberately not enabled yet.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, inspect, json, re, zipfile
import test_geos_navigation as original
import test_geos_navigation_editor as editor

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'src/render/geos/navigation-previous-candidate'
VARIANT = 'candidate'


def candidate_build(out, base):
    spec = importlib.util.spec_from_file_location('local_navigation_builder', D / 'build.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.build(out, base)
    dest = out / VARIANT
    labels = {name: int(address, 16) for address, name in re.findall(
        r'al ([0-9A-Fa-f]+) \.(\w+)', (dest / 'geosnav.lbl').read_text())}
    return (dest / 'geosnav.seo').read_bytes(), labels


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--focus', action='store_true')
    p.add_argument('--variant', choices=['control', 'candidate'], default='candidate')
    p.add_argument('--editor', action='store_true', help='Exercise the public root scheduler instead of the historical direct controller.')
    args = p.parse_args()
    VARIANT = args.variant
    out = ROOT / 'build/geos-navigation-previous-compatibility' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    with zipfile.ZipFile(out / 'verifier.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for path in (Path(__file__), Path(original.__file__), D / 'navigation.s', D / 'build.py'):
            z.write(path, path.relative_to(ROOT))
    if args.editor:
        image, _ = candidate_build(out / 'leaf', args.fixture.resolve())
        Base = editor.Fixture
        class Fixture(Base):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.assets['geosnav'] = image
            def remove(self, identity, slot):
                for i in range(self.s['se_overlay_capacity']):
                    if self.m.read(self.s['se_overlay_ids']+i)==identity and (self.m.read(self.s['image_slot']+i)&1)==slot:
                        self.m.write(self.s['se_overlay_ids']+i,0)
                        self.m.write(self.s['se_overlay_active']+slot,0)
                        return i
                raise AssertionError(('missing fault target', identity, slot))
        editor.Fixture = Fixture
        print('RUN', out, flush=True)
        with zipfile.ZipFile(args.fixture / 'product-sources.zip') as z:
            gcc = z.read('src/render/geos/caret-cache.inc')
            font = z.read('src/render/geos/typing-font-cache.inc')
        assert b'GCC_BITMAP=$B200' in gcc and b'GCC_END=GCC_ATTRIBUTES+1000' in gcc
        assert b'GTF_DATA=$E568' in font and b'GTF_META=$EA68' in font
        text = inspect.getsource(editor.run)
        old = 'allowed=[(start,start+64)]+[(start+0x200+i*0x800,start+0x200+(i+1)*0x800) for i in range(22)]'
        new = old + '+[(start+0xB200,start+0xD528),(start+0xE568,start+0xEA88)]'
        assert text.count(old) == 1
        namespace = dict(vars(editor))
        exec(compile(text.replace(old, new), str(Path(__file__)) + '::frozen-derived-cache-spans', 'exec'), namespace)
        (out / 'editor-adaptation.json').write_text(json.dumps(dict(old=old,new=new,
            scope='Exact existing literal caret-base and normal-font cache extents from frozen ABI; removed backup spans, remaining FE tail and foreign banks stay immutable.'), indent=2) + '\n')
        result = namespace['run'](out, args.fixture.resolve(), args.focus)
        result['candidate_status'] = 'V2 predecessor consumer; old packaged C24 must be refused through exact ABI witness'
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        raise SystemExit(0)
    # The historical harness appended duplicate module IDs under private
    # dictionary names. Current imports correctly refuse duplicates. Replace
    # the two existing catalog payloads, retaining every original oracle.
    text = inspect.getsource(original.run)
    changes = [("f.assets['geosnav-private'] = image", "f.assets['geosnav'] = image"),
               ("f.assets['semantic-private'] = semantic_image", "f.assets['geossema'] = semantic_image")]
    for old, new in changes:
        assert text.count(old) == 1
        text = text.replace(old, new)
    namespace = dict(vars(original), build=candidate_build)
    exec(compile(text, str(Path(__file__)) + '::current-catalog-keys', 'exec'), namespace)
    (out / 'adaptation.json').write_text(json.dumps(dict(
        original_sha256=hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest(),
        changes=changes, scope='Existing catalog payload selection only; no navigation, memory or failure oracle changed.'), indent=2) + '\n')
    print('RUN', out, flush=True)
    result = namespace['run'](out, args.fixture.resolve(), args.focus)
    result['candidate_status'] = 'V2 predecessor consumer; old packaged C24 must be refused through exact ABI witness'
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
