"""Unchanged SP2 fullsource/pixel/ownership tests on batchedR14candidate."""
from pathlib import Path
from datetime import datetime,timezone
import inspect,json
import test_grid_long_transaction_extended as original
ROOT=Path(__file__).resolve().parents[1]
def run(out):
 source=inspect.getsource(original.run);old="ROOT/'src/render/grid/long-prose-candidate/build-long.py'";assert source.count(old)==1;source=source.replace(old,"ROOT/'src/render/grid/geowrite-reflow-candidate/build.py'")
 # The baselinefixture alreadycontainsSP2; oldpublisherfaults stilluseactual
 # original193429 metadata, notanidenticalunchangedcandidateC14.
 source=source.replace("old=(BASE/'build/overlays'", "old=(OLD_BASE/'build/overlays'")
 ns=dict(original.__dict__,BASE=ROOT/'agentsworking/evidence/M8/20261025T201720331556Z-grid-long-prose/fixture',OLD_BASE=original.BASE);exec(compile(source,str(Path(__file__))+':same-oracles','exec'),ns);r=ns['run'](out);r['candidate_scope']='Sameadmissionandpixeloracle; newR14strictpixelworker7,batchpixelsbeforeR25packetcommit.';(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 out=ROOT/'build/grid-geowrite-transaction'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
