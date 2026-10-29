"""Bind operation-sized overlay objects to one verified resident image.

Internal exports take precedence. Remaining imports must resolve uniquely to
the sealed resident; the generated aliases occupy no runtime bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from bindings import link_symbols, verify

parser = argparse.ArgumentParser()
parser.add_argument('--report', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--require-export', action='append', default=[])
parser.add_argument('objects', nargs='+', type=Path)
args = parser.parse_args()
report = json.loads(args.report.read_text())
stem = args.report.name.removesuffix('-report.json')
identity = verify(args.report.with_name(stem + '.prg'),
                  args.report.with_name(stem + '.lbl'))
assert identity['digest'] == report['resident_binding']['digest']
assert identity['resident_sha256'] == report['sha256']


def names(kind, path):
    output = subprocess.run(['od65', '--dump-' + kind, str(path)],
                            capture_output=True, text=True, check=True).stdout
    return set(re.findall(r'Name:\s*"([^"\n]+)"', output))


imports, exports = set(), set()
import_sizes = {}
for path in args.objects:
    dump = subprocess.run(['od65', '--dump-imports', str(path)],
                          capture_output=True, text=True, check=True).stdout
    for size, name in re.findall(r'Address size:\s+0x([0-9A-Fa-f]+)[^\n]*\n\s+Name:\s*"([^"\n]+)"', dump):
        import_sizes.setdefault(name, set()).add(int(size, 16))
        imports.add(name)
    exports.update(names('exports', path))
assert set(args.require_export) <= exports, ('Missing internal exports', args.require_export)
symbols = link_symbols(args.report.with_name(stem + '.lbl'))
records = {}
lines = ['; Generated sealed resident aliases; no runtime bytes.']
for name in sorted(imports - exports):
    addresses = {value for candidate, value in symbols if candidate == name}
    assert len(addresses) == 1, ('Ambiguous or absent resident import', name, addresses)
    address = addresses.pop()
    assert not (0x0800 <= address < 0x1000 or 0xA000 <= address < 0xC000
                or 0xC600 <= address < 0xCA00), ('Unsafe resident alias', name, address)
    sizes = import_sizes[name]
    assert len(sizes) == 1, ('Conflicting resident import address sizes', name, sizes)
    size = sizes.pop()
    assert size in (1, 2), ('Unsupported import address size', name, size)
    assert size != 1 or address < 0x100, ('ZP import outside zero page', name, address)
    lines += [('.exportzp ' + name if size == 1 else '.export ' + name + ': absolute'),
              f'{name} = ${address:04X}']
    records[name] = address
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text('\n'.join(lines) + '\n')
args.output.with_suffix('.json').write_text(json.dumps(dict(
    schema=1, resident_sha256=report['sha256'], resident_binding=identity['digest'],
    imports=records, internal_exports=sorted(exports),
    object_sha256={str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in args.objects}), indent=2) + '\n')
print(f'Module bindings: {len(records)} resident aliases, {len(exports)} internal exports')
