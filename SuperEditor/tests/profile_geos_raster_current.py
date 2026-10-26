"""Private actual full-page raster self/callsite profile; no product mutations."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
import profile_cache_lookup53 as profile
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--dataset',choices=['251','422'],default='422');a=p.parse_args();out=ROOT/'build/geos-raster-probe'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);profile.run(out,a.fixture,'hint-raster-self',a.dataset)
