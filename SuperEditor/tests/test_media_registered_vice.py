"""Fixed59 native media qualification, three real conditions;8100/text8200.

Read-only imports preserve original protocol/source/history/rawdisk/VIC/REU
oracles. No ACK/status/catalog injection is used in these three cases. Actual
file staging can write/free leaves; this does not assert all unownedREU bytes
unchanged or add any blanket53 allowance. No hardware/power-loss claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,socket,subprocess,zipfile
import test_combined_media_vice as media
import test_grid_capture_index as identity
ROOT=media.ROOT
BASE=ROOT/'build/capture-lexical-integrated/20261026T190219265642Z/fixture'
CASES=('missing-device','write-protected','disk-full')

def free_ports():
 for port in (8100,*range(8200,8240)):
  with socket.socket()as sock:
   sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
   try:sock.bind(('127.0.0.1',port))
   except OSError as exc:raise AssertionError(f'owned port{port} busy; no process killed')from exc

def hardlinks(out):
 reply=json.loads((out/'run-plan.stdout.txt').read_text(encoding='utf-8-sig'));assert reply['Status']=='success'
 runtime=Path(reply['RunDir']).resolve();assert runtime.name.startswith('vice_auto_')
 process=subprocess.run(['ps','-Ao','command'],capture_output=True,text=True,check=True).stdout
 assert str(runtime/'dumps/vice_reu_working.img')not in process,'closedownedVICErequired'
 known={};records=[]
 for folder in (out,runtime):
  for p in sorted(folder.rglob('*')):
   if not p.is_file() or p.stat().st_size!=16777216:continue
   digest=hashlib.sha256(p.read_bytes()).hexdigest()
   if digest not in known:known[digest]=p;continue
   peer=known[digest]
   if p.stat().st_ino==peer.stat().st_ino:continue
   temp=p.with_name(p.name+'.owned-link');os.link(peer,temp);os.replace(temp,p)
   assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
   records.append(dict(path=str(p),peer=str(peer),sha256=digest,bytes=16777216))
 result=dict(closed_owned_only=True,runtime=str(runtime),links=records,bytes_avoided=16777216*len(records))
 (out/'registered-hardlinks.json').write_text(json.dumps(result,indent=2)+'\n');return result

def run_one(base,case):
 assert case in CASES;seal=identity.authenticate(base);media.free_ports=free_ports;free_ports()
 e=media.freeze(base);result=media.execute(e,case);out=e/case
 assert result['actual_catalog_assets']==59 and not result['injections'],'realmediaonly/noACKsubstitution'
 links=hardlinks(out);result.update(registered_seal=seal,registered_wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),registered_case=case,hardlinks=links,visual_review='pending')
 (out/'registered-result.json').write_text(json.dumps(result,indent=2)+'\n');print('REGISTERED_MEDIA_PASS',case,out,result['screens'],'screens',flush=True)
 return dict(case=case,evidence=str(e.relative_to(ROOT)),screens=result['screens'],pixels=result['pixels'],attributes=result['attributes'],raw_disk_sha256=result['raw_disk_sha256'],injections=[],ports_released=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--case',choices=CASES,action='append');p.add_argument('--run',action='store_true');a=p.parse_args()
 if not a.run:print(__doc__);raise SystemExit(0)
 base=a.fixture.resolve();results=[]
 for case in a.case or CASES:results.append(run_one(base,case))
 out=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-media-registered-gallery');out.mkdir()
 result=dict(status='PASS',seal=identity.authenticate(base),cases=results,screens=sum(c['screens']for c in results),pixels=sum(c['pixels']for c in results),attributes=sum(c['attributes']for c in results),scope=__doc__,visual_review='pending')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('REGISTERED_MEDIA_GALLERY',out,flush=True)
