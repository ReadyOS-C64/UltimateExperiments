"""Resolve an engine overlay's real imports to the sealed resident contract.

State aliases disambiguate private names (e.g. emit.pending vs code.pending).
Functions exported by the engine resolve inside its own image, never back
through resident entry trampolines. The generated object exports no bytes.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from bindings import verify,link_symbols
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--report',type=Path,default=ROOT/'build/editor-report.json');p.add_argument('--output',type=Path,default=ROOT/'build/engine-bindings.s');p.add_argument('objects',nargs='+',type=Path);a=p.parse_args()
r=json.loads(a.report.read_text());stem=a.report.name.removesuffix('-report.json')
v=verify(a.report.with_name(stem+'.prg'),a.report.with_name(stem+'.lbl'));assert v['digest']==r['resident_binding']['digest'] and v['resident_sha256']==r['sha256']
def names(kind,obj):
 run=subprocess.run(['od65','--dump-'+kind,str(obj)],capture_output=True,text=True,check=True)
 return set(re.findall(r'Name:\s*"([^"\n]+)"',run.stdout))
imports=set();exports=set()
for obj in a.objects:imports.update(names('imports',obj));exports.update(names('exports',obj))
moved={'se_doc_splice_begin','se_doc_splice_local_begin','se_doc_splice_feed','se_doc_splice_step','se_doc_splice_refs_begin','se_doc_splice_local_refs_begin'}
assert moved<=exports and 'se_doc_splice_cancel' not in exports
state_names={}
for frame in (ROOT/'src/document/frames').glob('*.inc'):
 for alias,name in re.findall(r'^(se_engine_\w+) = (\w+)$',frame.read_text(),re.M):state_names.setdefault(name,[]).append(alias)
pairs=link_symbols(a.report.with_name(stem+'.lbl'));records={};lines=['; Generated exact resident imports; no runtime bytes.']
for name in sorted(imports-exports):
 aliases=state_names.get(name,[])
 assert len(aliases)<=1,(name,aliases)
 key=aliases[0] if aliases else name
 addresses={value for candidate,value in pairs if candidate==key}
 assert len(addresses)==1,(name,key,addresses)
 address=addresses.pop()
 assert not 0x800<=address<0x1000 and not 0xA000<=address<0xC000,(name,'unsafe code/buffer binding')
 if aliases:assert address<0x100 or 0x9A00<=address<0x9E00,(key,address)
 directive='.exportzp' if address<0x100 else '.export'
 lines.extend([f'{directive} {name}',f'{name} = ${address:04X}'])
 records[name]=dict(address=address,resident_symbol=key,state_alias=bool(aliases))
assert not moved & records.keys()
a.output.write_text('\n'.join(lines)+'\n')
a.output.with_suffix('.json').write_text(json.dumps(dict(schema=1,resident_sha256=r['sha256'],resident_binding=v['digest'],imports=records,engine_exports=sorted(exports),object_sha256={str(obj):hashlib.sha256(obj.read_bytes()).hexdigest() for obj in a.objects}),indent=2)+'\n')
print(f'Engine linked imports: {len(records)}; internal exports: {len(exports)}')
