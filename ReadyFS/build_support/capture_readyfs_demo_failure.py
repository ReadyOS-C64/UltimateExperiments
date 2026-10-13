from pathlib import Path
import urllib.request,json,time,subprocess
ROOT=Path(__file__).resolve().parent.parent
out=ROOT/'logs/readyfs_c64u/demo-failure-state-20261009-0706';out.mkdir(exist_ok=True)
api='http://10.0.0.79/v1'
def request(p,method='GET',data=None):
 with urllib.request.urlopen(urllib.request.Request(api+p,method=method,data=data,headers={'Content-Type':'application/json'} if data else {}),timeout=20) as r:return r.read()
saved=json.loads(request('/configs/U64%20Specific%20Settings'))['U64 Specific Settings'];restore={'U64 Specific Settings':{k:saved[k] for k in ('Turbo Control','CPU Speed')}}
(out/'restore-speed.json').write_text(json.dumps(restore))
try:
 request('/configs','POST',json.dumps({'U64 Specific Settings':{'Turbo Control':'Off','CPU Speed':' 1'}}).encode());time.sleep(1)
 for address,size in [(0,512),(0x400,1000),(0xb500,256),(0xb600,4096),(0x800,0xae00)]:
  (out/f'memory-{address:04x}.bin').write_bytes(request(f'/machine:readmem?address={address:X}&length={size}'))
 subprocess.run(['python3',str(ROOT/'build_support/decode_c64_screen.py'),str(out/'memory-0400.bin'),'--output',str(out/'screen.txt')],check=True)
finally:request('/configs','POST',json.dumps(restore).encode())
print(out,flush=True)
