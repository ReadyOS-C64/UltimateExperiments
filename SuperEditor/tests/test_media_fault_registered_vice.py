"""Actual59 explicitly injected native File faults;8100/text8200.

These are debugger acknowledgement/catalog faults, not physical media errors.
Original named seams, source/history/rawdisk/VIC/REU/capability/retained-state
oracles are unchanged. Both-missing case intentionally retains failure state;
no cleanup success or hardware/power-loss/OS lifecycle claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import test_media_registered_vice as registered
media=registered.media;identity=registered.identity;ROOT=registered.ROOT;BASE=registered.BASE
CASES=('promotion-ack-injected','missing-c12-save','missing-both-read')

def run_one(base,case):
 assert case in CASES;seal=identity.authenticate(base);media.free_ports=registered.free_ports;registered.free_ports()
 e=media.freeze(base);result=media.execute(e,case);out=e/case
 assert result['actual_catalog_assets']==59 and result['injections'],'mustretainexplicitdebuggerprovenance'
 links=registered.hardlinks(out);result.update(fault_seal=seal,fault_wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),fault_case=case,hardlinks=links,visual_review='pending',physical_media_claim=False)
 (out/'registered-fault-result.json').write_text(json.dumps(result,indent=2)+'\n');print('REGISTERED_FAULT_PASS',case,out,result['screens'],'screens',flush=True)
 return dict(case=case,evidence=str(e.relative_to(ROOT)),screens=result['screens'],pixels=result['pixels'],attributes=result['attributes'],raw_disk_sha256=result['raw_disk_sha256'],injections=result['injections'],ports_released=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--case',choices=CASES,action='append');p.add_argument('--run',action='store_true');a=p.parse_args()
 if not a.run:print(__doc__);raise SystemExit(0)
 base=a.fixture.resolve();results=[]
 for case in a.case or CASES:results.append(run_one(base,case))
 out=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-media-fault-registered-gallery');out.mkdir()
 r=dict(status='PASS',seal=identity.authenticate(base),cases=results,screens=sum(v['screens']for v in results),pixels=sum(v['pixels']for v in results),attributes=sum(v['attributes']for v in results),scope=__doc__,visual_review='pending')
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('REGISTERED_FAULT_GALLERY',out,flush=True)
