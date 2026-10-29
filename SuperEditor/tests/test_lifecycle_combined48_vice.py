"""Combined48 immutable lifecycle native gate; private8500/text8600.

Unchanged released body-memo/current/original lifecycle engines and oracles.
No production edits, shared build, physicalRESTORE, externalprovider or OS claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil
import test_lifecycle_body_memo_vice as body
ROOT=body.ROOT
FIXTURE=ROOT/'build/geos-incremental-editor/20261025T171440790321Z/fixture'
PRG='b33cc41e68e32b620222c49a62f8e8a42dfc0e7e2e487e76b9004c1eca1692d9'
DISK='da5f2235a1102a1ad5d370385ffece04cc01c1ff5addb7256538eab3e6961727'


def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--fixture',type=Path,default=FIXTURE);p.add_argument('--mode',choices=['all','40','80','literal','preview'],default='all');a=p.parse_args()
 if not a.run:print('Prepared only; --run actualfourmode native24 plusSaveAs/reopen, owned8500/text8600.');return
 fixture=a.fixture.resolve();raw=(fixture/'freeze.json').read_bytes();identity=json.loads(raw);assert len(identity['names'])==48 and identity['prg_sha256']==PRG and identity['disk_sha256']==DISK
 scenarios={'40':(0,False),'80':(2,False),'literal':(3,False),'preview':(3,True)};cases=[]
 for label,(mode,preview)in scenarios.items():
  if a.mode not in('all',label):continue
  assert (fixture/'freeze.json').read_bytes()==raw
  entry=body.run_one(fixture,mode,preview);assert entry['prg_sha256']==PRG and entry['disk_sha256']==DISK
  result=json.loads((ROOT/entry['evidence']/'current-result.json').read_text());assert result['catalog_assets']==48
  cases.append(entry)
 out=ROOT/'agentsworking/evidence/M8'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-combined48-lifecycle-native');out.mkdir();result=dict(status='passed',fixture=str(fixture),identity=identity,cases=cases,frames=sum(x['frames']for x in cases),native_pixels=sum(x['native_pixels']for x in cases),scope=__doc__,visual_review='pending',source_sha256={str(Path(m.__file__).relative_to(ROOT)):hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()for m in [body,body.current,body.current.lifecycle]})
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');shutil.copy2(Path(__file__),out/Path(__file__).name);print('COMBINED48_LIFECYCLE_PASS',out,flush=True)
if __name__=='__main__':main()
