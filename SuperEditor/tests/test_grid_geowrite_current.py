"""FullsameSP2oracles onprivateworker rebasedtoactualcurrentmodularproduction."""
from pathlib import Path
from datetime import datetime,timezone
import inspect,json
import test_grid_long_transaction_extended as original
import font_fixture # Pin existing immutable pack seam before privatebuild changes sys.path.
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'build/geos-incremental-editor/20261025T203233990688Z/fixture'
def run(out):
 src=inspect.getsource(original.run).replace("ROOT/'src/render/grid/long-prose-candidate/build-long.py'","ROOT/'src/render/grid/geowrite-reflow-candidate/build-current.py'").replace("old=(BASE/'build/overlays'","old=(OLD_BASE/'build/overlays'")
 ns=dict(original.__dict__,BASE=BASE,OLD_BASE=original.BASE);exec(compile(src,str(Path(__file__))+':sameguards','exec'),ns);r=ns['run'](out);r['candidate_scope']='PrivateR14pixelworker4091/C33batchedcaller;current203233 productionfixture,actualC14/R25byteidentical.';(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 out=ROOT/'build/grid-geowrite-current-proof'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
