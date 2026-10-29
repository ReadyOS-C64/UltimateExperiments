"""Released C33/R25 pair: unchanged broad caret/root/primitive/fault gates."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib,shutil,zipfile
import test_grid_caret_candidate_integration as broad
import test_grid_caret_candidate_xor_validation as faults
import test_grid_caret_candidate_xor as primitive
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/grid-typing-native/20261025T180126291505Z/fixture'
def run(out,base):
 result={}
 # Exact published XOR source remains unchanged in the actual sealed candidate.
 released=(ROOT/'src/render/grid/typing-candidate/released/caret.s').read_text();original=(ROOT/'src/render/grid/caret-candidate/xor/paint.s').read_text();assert released[released.index('xor_changes:'):released.index('type_try:')].split('\n.segment "CODE"')[0].strip()==original[original.index('xor_changes:'):].strip()
 for name,module in [('broad',broad),('faults',faults),('primitive',primitive)]:
  target=out/name;target.mkdir();print('GATE',name,flush=True)
  result[name]=module.run(target)if name=='primitive'else module.run(target,base)
 (out/'result.json').write_text(json.dumps(dict(status='passed',fixture=str(base),gates=result),indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/grid-typing-regression'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)
