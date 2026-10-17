from pathlib import Path
import json,hashlib,shutil,subprocess
P=Path(__file__).parent;S=P/'project';R=P/'closed-final';ROOT=P.parents[2]
def ident(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
j=json.loads((R/'RESULT.json').read_text());assert j['status']=='PASSED_PRIVATE_OPTIONAL_8088_TF_COMPONENT'
for file in ['INPUTS_BEFORE.json','INPUTS_AFTER.json']:
 data=json.loads((R/file).read_text())
 for n,v in data.items():assert ident(Path(n))==v,n
assert json.loads((R/'INPUTS_BEFORE.json').read_text())==json.loads((R/'INPUTS_AFTER.json').read_text())
for n,v in json.loads((R/'PRODUCTS_AFTER.json').read_text()).items():assert ident(Path(n))==v,n
# Record only reviewed differences from public native/test sources.
files=[]
for p in sorted(S.rglob('*')):
 if not p.is_file()or any(n in {'build','.zig-cache','zig-out','__pycache__'}for n in p.relative_to(S).parts)or p.suffix=='.pyc':continue
 n=str(p.relative_to(S));base=ROOT/n
 if not base.is_file()or ident(base)!=ident(p):files.append(n)
assert len(files)==21,files
portable=P/'portable';portable.mkdir(exist_ok=False)
for n in files:
 q=portable/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(S/n,q)
(P/'PORTABLE_SOURCE.json').write_text(json.dumps({n:ident(portable/n)for n in files},indent=2)+'\n')
memory=json.loads((S/'build/dos64.memory.json').read_text());unit=json.loads((S/'build/dos64-tests.memory.json').read_text())
(P/'LAYOUT.json').write_text(json.dumps({'runtime':memory,'UNIT':unit},indent=2)+'\n')
versions={}
for n,c in [('zig',['/Users/karlprosserpp/dev/c64projects/zeropage-tooling/bin/zig','version']),('ca65',['ca65','--version']),('ld65',['ld65','--version']),('make',['make','--version'])]:
 q=subprocess.run(c,capture_output=True,check=True,text=True);versions[n]=(q.stdout+q.stderr).strip()
(P/'TOOL_VERSIONS.json').write_text(json.dumps(versions,indent=2)+'\n')
# Parent seal deliberately excludes generated native binaries/cache/whole SDK copies.
# Its closed ledgers pin all actual inputs/products, including external resources.
selected=['REPRO_RESULT.json','REPRO_INPUTS_BEFORE.json','REPRO_INPUTS_AFTER.json','BASELINE_COPIES_VERIFIED.json','SOURCE_COPIES_BEFORE.json','PRIVATE_MODIFICATIONS.json','PORTABLE_SOURCE.json','LAYOUT.json','TOOL_VERSIONS.json','probe.py','prepare.py','modify_private.py','integrate_private.py','update_trace_fixtures.py','package_controls.py','profile_switch.py','close_cpu.py','seal_private.py']
selected += [str(p.relative_to(P))for p in portable.rglob('*')if p.is_file()]
for folder in ['closed-final','closed','package-controls','profile-switch-v2','profile-switch']:
 for p in (P/folder).iterdir():
  if p.is_file()and p.suffix in('.json','.stdout','.stderr','.py'):selected.append(str(p.relative_to(P)))
selected += [p.name for p in P.iterdir()if p.is_file()and p.suffix in('.stdout','.stderr')]
(P/'SEAL_INPUTS.json').write_text(json.dumps(sorted(set(selected)),indent=2)+'\n')
print(json.dumps({'inputs':j['inputs'],'products':j['products'],'runtime':j['runtime'],'UNIT':j['UNIT'],'commands':j['commands'],'portable':len(files),'seal_candidates':len(set(selected))},indent=2))
