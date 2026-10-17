from pathlib import Path
import json,hashlib,os
root=Path(__file__).resolve().parents[3];p=root/'agentworking/scratch/native-copy20m-splitread-purpose-20261017';h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert h(p/'MANIFEST.json')=='b1221d91e0b3cfdf744514be8f2d12654112143961777c29af9b164af5fef285'
m=json.loads((p/'MANIFEST.json').read_text());rows=m['files']
for n,r in rows.items():
 f=p/n;assert h(f)==r['sha256']and f.stat().st_size==r['bytes'],n
w=p/'work';launch=json.loads((w/'LAUNCH_MANIFEST.json').read_text());assert h(w/'LAUNCH_MANIFEST.json')=='4e40209b42433eb5114149497fad9a42555e82f30abe6ba6006cccb8c31ce8eb'
for n,v in launch['files'].items():assert h(Path(n))==v,n
closed=json.loads((p/'closed-local/INPUTS_BEFORE.json').read_text());assert closed==json.loads((p/'closed-local/INPUTS_AFTER.json').read_text())
for n,r in json.loads((p/'closed-local/SOURCE_COPIES.json').read_text()).items():assert h(Path(n))==r['sha256']and h(Path(r['copy']))==r['sha256']
assert h(root/'agentworking/ACTIVE_HARDWARE_SESSION.json')=='230c88094f48b9a3d61f91f1f808639d038f8e1f93ded381a2d2efd767b5c102'
for pid in (28233,28240):
 try:os.kill(pid,0)
 except ProcessLookupError:pass
 else:raise AssertionError(pid)
print('Verified',len(rows),'parent pins;',len(launch['files']),'launch originals+copies; ACTIVE and absent PIDs exact')
