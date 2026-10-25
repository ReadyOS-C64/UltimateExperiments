"""Bind separately linked diagnostic micromodules to one sealed resident.

Existing C11 absolute exports resolve first. This zero-byte alias object binds
only remaining imports and forbids cold,overlay and reserved-shim addresses.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from bindings import verify,link_symbols

p=argparse.ArgumentParser()
p.add_argument('--report',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('objects',nargs='+',type=Path)
a=p.parse_args()
r=json.loads(a.report.read_text());stem=a.report.name.removesuffix('-report.json')
v=verify(a.report.with_name(stem+'.prg'),a.report.with_name(stem+'.lbl'))
assert v['digest']==r['resident_binding']['digest'] and v['resident_sha256']==r['sha256']
def names(kind,obj):
    result=subprocess.run(['od65','--dump-'+kind,str(obj)],capture_output=True,text=True,check=True)
    return set(re.findall(r'Name:\s*"([^"\n]+)"',result.stdout))
imports=set();exports=set()
for obj in a.objects:
    imports.update(names('imports',obj));exports.update(names('exports',obj))
assert {'se_diag_begin','se_diag_step','se_diag_context','se_diag_shape'}<=exports
pairs=link_symbols(a.report.with_name(stem+'.lbl'));records={}
lines=['; Generated exact resident imports; no runtime bytes.']
for name in sorted(imports-exports):
    addresses={address for candidate,address in pairs if candidate==name}
    assert len(addresses)==1,(name,addresses)
    address=addresses.pop()
    assert not (0x800<=address<0x1000 or 0xA000<=address<0xC000 or 0xC600<=address<0xCA00),(name,address)
    lines.extend([('.exportzp ' if address<0x100 else '.export ')+name,f'{name} = ${address:04X}'])
    records[name]=address
a.output.write_text('\n'.join(lines)+'\n')
a.output.with_suffix('.json').write_text(json.dumps(dict(schema=1,resident_sha256=r['sha256'],resident_binding=v['digest'],imports=records,internal_exports=sorted(exports),object_sha256={str(obj):hashlib.sha256(obj.read_bytes()).hexdigest() for obj in a.objects}),indent=2)+'\n')
print(f'Diagnostic linked imports: {len(records)}; zero-byte aliases')
