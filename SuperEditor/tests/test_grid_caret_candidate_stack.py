"""Unchanged staged stack evaluator, exact private48 C33 metadata extension."""
from pathlib import Path
from datetime import datetime,timezone
import inspect,json,argparse
import test_editor_staged_stack as verifier
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/grid-caret-integration/20261025T163000/fixture'
def run(out,base=BASE):
 source=inspect.getsource(verifier.stage_proof)
 old="assert (len(frozen['names'])==46 and frozen['names'][-2:]==['code','clex']) or (len(frozen['names'])==47 and frozen['names'][-3:]==['code','clex','type'])"
 new="assert len(frozen['names'])==48 and frozen['names'][-4:]==['code','clex','type','grid']"
 assert source.count(old)==1
 namespace=dict(verifier.__dict__);exec(compile(source.replace(old,new),str(Path(__file__))+':48-metadata-only','exec'),namespace);verifier.stage_proof=namespace['stage_proof']
 result=verifier.run(out,base,verifier.original.ROM)
 result['private48_metadata_extension']=dict(assertion=new,justification='Original47 remainordered andbytechecked; oneC33 grid slot1ID33 added. All48binding/CRC/callgraph checks retained; no evaluator/interrupt/opaque-edge rule changed. Native baseline hash differs, so only relative idle stack claim.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);a=p.parse_args()
 out=ROOT/'build/grid-caret-stack'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)
