from pathlib import Path
import urllib.request,json,os
from readyfs_build_report import segments,OVERLAY_MAP
root=Path(__file__).resolve().parent.parent
out=Path(os.environ['READYFS_DEMO_INSPECT_OUT']);out.mkdir(parents=True,exist_ok=True)
binary=(root/'artifacts/readyfs/readyfs-overlay.prg').read_bytes();load=int.from_bytes(binary[:2],'little');report={}
for name,segment in segments(OVERLAY_MAP).items():
 if name not in ('CODE','RODATA'):continue
 differences=[]
 for address in range(segment['start'],segment['end']+1,1024):
  size=min(1024,segment['end']+1-address)
  with urllib.request.urlopen(f'http://10.0.0.79/v1/machine:readmem?address={address:X}&length={size}',timeout=15) as response:actual=response.read()
  expected=binary[2+address-load:2+address-load+size]
  if len(actual)!=len(expected):differences.append({'address':address,'actual_length':len(actual),'expected_length':len(expected)})
  else:
   differences.extend({'address':address+i,'expected':a,'actual':b} for i,(a,b) in enumerate(zip(expected,actual)) if a!=b)
 report[name]=differences
(out/'resident-differences.json').write_text(json.dumps(report,indent=2));print({key:len(value) for key,value in report.items()},flush=True)
