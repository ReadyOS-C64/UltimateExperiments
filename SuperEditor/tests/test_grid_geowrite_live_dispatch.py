"""Unchanged SP2 40+37 oracles on private C14 event skip, live-candidate producer and pixelworker."""
from pathlib import Path
from datetime import datetime,timezone
import inspect,json
import test_grid_long_transaction_extended as original
import font_fixture
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'build/geos-incremental-editor/20261025T203233990688Z/fixture'
def run(out):
 src=inspect.getsource(original.run).replace("ROOT/'src/render/grid/long-prose-candidate/build-long.py'","ROOT/'src/render/grid/geowrite-reflow-candidate/build-live-dispatch.py'").replace("old=(BASE/'build/overlays'","old=(OLD_BASE/'build/overlays'")
 ns=dict(original.__dict__,BASE=BASE,OLD_BASE=original.BASE);exec(compile(src,str(Path(__file__))+':sameguards','exec'),ns);r=ns['run'](out);r['candidate_scope']='Private R14 pixelworker plus phase-owned negative/positive approval latch. Live clean paragraph still checks full typedFE/source/key/anchors on each scan; rejected or absent prose no repeated record authentication. Final publication still fullguard.';(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 out=ROOT/'build/grid-geowrite-live-dispatch-proof'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
