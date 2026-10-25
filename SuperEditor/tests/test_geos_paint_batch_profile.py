"""Matched forcedfresh TOP0 attribution for the private bounded painter batch."""
from pathlib import Path
from datetime import datetime,timezone
from types import SimpleNamespace
import argparse,json
import test_geos_page_cost_profile as profile
import test_geos_paint_batch_candidate as batch
ROOT=batch.ROOT
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--variant',choices=['control','candidate'],default='candidate');a=p.parse_args()
 out=ROOT/'build/geos-paint-batch-profile'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+a.variant);out.mkdir(parents=True);print('RUN',out,flush=True)
 frozen=batch.install(out,batch.BASE,a.variant)
 profile.packet=SimpleNamespace(build=lambda where,base,variant:batch.build(where,base,a.variant))
 gate=out/'gate';gate.mkdir();result=profile.run(gate,frozen);result['variant']=a.variant;(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
