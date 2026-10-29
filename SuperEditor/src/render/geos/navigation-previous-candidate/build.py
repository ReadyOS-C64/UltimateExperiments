"""Private C23 local-navigation work; never modifies shared build outputs."""
from pathlib import Path
import binascii, importlib.util, json, subprocess, sys, zipfile

ROOT = Path(__file__).resolve().parents[4]
D = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
from bindings import verify
from overlays import wrap


def build(out, base):
    out.mkdir(parents=True)
    src = out / 'frozen-sources'
    src.mkdir()
    with zipfile.ZipFile(base / 'product-sources.zip') as z:
        z.extractall(src)
    # Explicit private input: this is the separately qualified C24 op3 ABI,
    # not an assumption about whatever prototype was in an older source ZIP.
    protocol = ROOT / 'src/render/geos/semantic-previous-candidate/codec.inc'
    target = src / protocol.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(protocol.read_bytes())
    spec = importlib.util.spec_from_file_location('local_seed_builder', protocol.parent / 'build.py')
    semantic = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(semantic)
    semantic.build(out / 'semantic', base)
    seed = (out / 'semantic/seed/geossema.seo').read_bytes()[36:]
    (out / 'seed-witness.inc').write_text('SEED_SIZE=' + str(len(seed)) +
        '\nSEED_CRC=' + str(binascii.crc_hqx(seed, 65535)) + '\n')
    report = json.loads((base / 'build/editor-report.json').read_text())
    digest = verify(base / 'build/editor.prg', base / 'build/editor.lbl')['digest']
    (out / 'editor-api.inc').write_text(
        '.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte ' +
        ','.join('$' + digest[i:i+2] for i in range(0, 32, 2)) + '\n.endmacro\n')
    result = {}
    def cmd(*args):
        subprocess.run(list(map(str, args)), cwd=ROOT, check=True)
    for variant in ('control', 'candidate'):
        dest = out / variant
        dest.mkdir()
        source = src / 'src/render/geos/navigation.s' if variant == 'control' else D / 'navigation.s'
        objects = []
        for i, path in enumerate((source, src / 'src/render/geos/cache.s')):
            obj = dest / (str(i) + '.o')
            cmd('ca65', '-g', '-D', 'EDITOR_OVERLAY=1', '-I', out, '-I', src / 'src', '-o', obj, path)
            objects.append(obj)
        cmd(sys.executable, ROOT / 'tools/module_bindings.py', '--report', base / 'build/editor-report.json',
            '--output', dest / 'aliases.s', *objects)
        cmd('ca65', '-o', dest / 'aliases.o', dest / 'aliases.s')
        cmd('ld65', '-C', src / 'cfg/geos-editor-navigation.cfg', '-o', dest / 'geosnav.bin',
            '-Ln', dest / 'geosnav.lbl', '-m', dest / 'geosnav.map', *objects, dest / 'aliases.o')
        raw = (dest / 'geosnav.bin').read_bytes()
        image = wrap(raw, 1, 23,
            api=(report['symbols']['se_overlay_call'], report['symbols']['se_overlay_frame']),
            binding_digest=bytes.fromhex(digest))
        (dest / 'geosnav.seo').write_bytes(image)
        if variant == 'control':
            assert image == (base / 'build/overlays/geosnav.seo').read_bytes(), 'control must reproduce the frozen C23'
        result[variant] = dict(payload_bytes=len(raw), spare_bytes=4096-len(raw))
    (out / 'budget.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    print(build(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()))
