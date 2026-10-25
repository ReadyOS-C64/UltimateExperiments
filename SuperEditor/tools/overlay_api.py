"""Export requested resident ABI addresses and an inseparable payload seal."""
import argparse
import json
from pathlib import Path
from bindings import verify,link_symbols
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--report',type=Path,default=root/'build/overlay-probe-report.json');p.add_argument('--output',type=Path,default=root/'build/overlay-api.inc');p.add_argument('--symbols',nargs='+',default=['se_overlay_call','se_overlay_frame']);p.add_argument('--all-public',action='store_true');a=p.parse_args()
r=json.loads(a.report.read_text());stem=a.report.name.removesuffix('-report.json')
binding=verify(a.report.with_name(stem+'.prg'),a.report.with_name(stem+'.lbl'))
assert binding['digest']==r['resident_binding']['digest'] and binding['resident_sha256']==r['sha256']
names=set(a.symbols)
cold=[(part['start'],part['end']) for part in r['segments'] if part['name']=='COLD']
# BOOT padding may hold cold-only buffers as absolute symbols (editor0F00).
# They have no COLD segment record but are still outside a warm snapshot.
cold.append((0x0800,0x0FFF))
def warm(name):return not any(start<=r['symbols'][name]<=end for start,end in cold)
if a.all_public:names.update(n for n in r['symbols'] if n.startswith('se_') and warm(n))
assert all(warm(n) for n in names), 'cold-only code/buffer bindings cannot be imported by command modules'
pairs=link_symbols(a.report.with_name(stem+'.lbl'))
for name in names:
    assert len({address for candidate,address in pairs if candidate==name})==1, f'ambiguous binding {name}'
addresses=''.join(f'{name} = ${r["symbols"][name]:04X}\n' for name in sorted(names))
bytes_literal=','.join(f'${b:02X}' for b in bytes.fromhex(binding['digest']))
a.output.write_text('; Generated for this complete resident build only.\n'+addresses+'\n.macro OVL_BINDING\n    .byte '+bytes_literal+'\n.endmacro\n')
