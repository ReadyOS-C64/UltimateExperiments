"""Current59 older read-cancel/H_SAVED boundaries, native8100/text8200.

Cancel-read uses real IRQSTOP after actual packet. H_SAVED cases explicitly
inject C12 loss; pending9 additionally forces wrapper ordering before the normal
pump consumesE8. Unchanged legacy boundary/source/history/device/name/disk oracles.
No physical-failure/powerloss/OS/hardware claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json
import test_media_registered_vice as registered
media=registered.media;identity=registered.identity;ROOT=registered.ROOT;BASE=registered.BASE
CASES=('cancel-read','missing-c12-saved-ack9','missing-c12-savepoint-pending9')

def run_one(base,case):
 assert case in CASES;seal=identity.authenticate(base);media.free_ports=registered.free_ports;registered.free_ports()
 e=media.freeze(base);result=media.execute(e,case);out=e/case
 assert result['actual_catalog_assets']==59
 if case=='cancel-read':assert not result['injections']
 else:assert result['injections'] and (out/'working9.d81').exists()
 links=registered.hardlinks(out);result.update(boundary_seal=seal,boundary_wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),boundary_case=case,hardlinks=links,visual_review='pending',forced_ordering=case=='missing-c12-savepoint-pending9')
 (out/'registered-boundary-result.json').write_text(json.dumps(result,indent=2)+'\n');print('REGISTERED_BOUNDARY_PASS',case,out,result['screens'],'screens',flush=True)
 return dict(case=case,evidence=str(e.relative_to(ROOT)),screens=result['screens'],pixels=result['pixels'],attributes=result['attributes'],raw_disk_sha256=result['raw_disk_sha256'],injections=result['injections'],ports_released=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--case',choices=CASES,action='append');p.add_argument('--run',action='store_true');a=p.parse_args()
 if not a.run:print(__doc__);raise SystemExit(0)
 base=a.fixture.resolve();results=[]
 for case in a.case or CASES:results.append(run_one(base,case))
 out=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-media-boundary-registered-gallery');out.mkdir()
 r=dict(status='PASS',seal=identity.authenticate(base),cases=results,screens=sum(v['screens']for v in results),pixels=sum(v['pixels']for v in results),attributes=sum(v['attributes']for v in results),scope=__doc__,visual_review='pending')
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('REGISTERED_BOUNDARY_GALLERY',out,flush=True)
