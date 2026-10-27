"""Actual62 stack CFG with the replacement R21 bounded row-job assembly.

Only the old raster reassembly bridge changes. Every graph, unknown-edge
refusal, staged-code proof and IRQ/NMI bound remains the released analyzer's.
No shared build or product substitution. Relative stack scope only.
"""
from pathlib import Path
import argparse
import binascii
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'tools')]
import test_cache_rebase_registered_stack as registered
import test_geos_strip_raster_candidate as raster
from overlays import wrap


def row_job_build(out, base, variant):
    assert variant == 'control', 'this adapter never substitutes a candidate'
    out.mkdir(parents=True)
    source = out / 'frozen-sources'
    source.mkdir()
    modules = ['render/geos/row-job', 'render/geos/row-job-loans',
               'render/geos/literal-byte/measure', 'render/geos/literal-byte/glyph',
               'render/geos/literal-byte/assets']
    exact = {'cfg/geos-editor-row.cfg', 'tools/module_bindings.py',
             'tools/bindings.py'} | {'src/' + n + '.s' for n in modules}
    with zipfile.ZipFile(base / 'product-sources.zip') as archive:
        for name in archive.namelist():
            if name in exact or name.startswith('src/') and name.endswith('.inc'):
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(name))
    fonts = source / 'assets/fonts/generated'
    fonts.mkdir(parents=True)
    for name in ('bsw9-original.bin', 'bsw9-widths.bin'):
        shutil.copyfile(base / 'fonts' / name, fonts / name)
    report = json.loads((base / 'build/editor-report.json').read_text())
    symbols = report['symbols']
    binding = report['resident_binding']['digest']
    (out / 'editor-api.inc').write_text(
        '.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '
        + ','.join('$' + binding[i:i + 2] for i in range(0, 32, 2))
        + '\n.endmacro\n')

    def command(*args):
        subprocess.run(list(map(str, args)), cwd=source, check=True)

    objects = []
    for name in modules:
        obj = out / (name.replace('/', '-') + '.o')
        command('ca65', '-g', '-I', out, '-I', source / 'src', '-o', obj,
                source / ('src/' + name + '.s'))
        objects.append(obj)
    command(sys.executable, source / 'tools/module_bindings.py', '--report',
            base / 'build/editor-report.json', '--output', out / 'aliases.s', *objects)
    command('ca65', '-g', '-o', out / 'aliases.o', out / 'aliases.s')
    command('ld65', '-C', source / 'cfg/geos-editor-row.cfg', '-o', out / 'geosrow.bin',
            '-Ln', out / 'geosrow.lbl', '-m', out / 'geosrow.map',
            *objects, out / 'aliases.o')
    raw = (out / 'geosrow.bin').read_bytes()
    labels = {name: int(address, 16) for address, name in re.findall(
        r'al ([0-9A-Fa-f]+) \.(\w+)', (out / 'geosrow.lbl').read_text())}
    assert labels['se_logical_row_job'] == labels['entry'] == 0xA010
    assert labels['se_geos_packed'] == 0xABF3 and labels['se_geos_widths'] == 0xAEDB
    assert len(raw) <= 4096 and raw[:16] == bytes.fromhex(binding)
    image = wrap(raw, 0, 21, api=(symbols['se_overlay_call'], symbols['se_overlay_frame']),
                 binding_digest=bytes.fromhex(binding))
    assert image == (base / 'build/overlays/geosrow.seo').read_bytes(), (
        'new R21 source/object order/cfg does not byte-match sealed actual image')
    (out / 'geosrow.seo').write_bytes(image)
    (out / 'row-job-proof.json').write_text(json.dumps(dict(
        status='byte-identical', entry=labels['entry'], modules=modules,
        raw_bytes=len(raw), raw_sha256=hashlib.sha256(raw).hexdigest(),
        raw_crc16=binascii.crc_hqx(raw, 65535),
        image_sha256=hashlib.sha256(image).hexdigest(),
        source_zip_sha256=hashlib.sha256((base / 'product-sources.zip').read_bytes()).hexdigest(),
        scope=__doc__), indent=2) + '\n')
    return source, symbols, labels, raw, image, {}


def run(out, fixture, project):
    identity = json.loads((fixture / 'freeze.json').read_text())
    assert len(identity['names']) == 62
    old = raster.build
    raster.build = row_job_build
    try:
        result = registered.run(out, fixture, project)
    finally:
        raster.build = old
    fg = result['foreground']
    row = next(item for item in fg['results'] if item['name'] == 'R:geosrow')
    proof = json.loads((out / 'raster-phase-reassembly/row-job-proof.json').read_text())
    assert row['status'] == 'bounded' and row['root'] == proof['entry']
    assert not row['faults']
    fg['row_job_reassembly'] = proof
    result['row_job_scope'] = __doc__
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--project', type=Path, default=ROOT)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print('RUN', args.out, flush=True)
    result = run(args.out.resolve(), args.fixture.resolve(), args.project.resolve())
    fg = result['foreground']
    print(json.dumps(dict(status=result['status'], foreground=fg['foreground_beyond_entry_idle'],
                          IRQ_NMI=fg['one_IRQ_NMI'], relative_combined=fg['relative_combined'],
                          assets=fg['assets'])), flush=True)
