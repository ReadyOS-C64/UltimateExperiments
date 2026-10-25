"""Originalactual73+256/allmode+history oracle, exactextra FEcert spans only."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_convergent_line as q
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',type=Path,default=q.DEFAULT);a=p.parse_args();out=ROOT/'build/geos-convergent-line-regression'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 original=q.c.outside_cache
 try:
  q.c.outside_cache=q.outside;r=q.hook.run(out,a.project.resolve(),False)
 finally:q.c.outside_cache=original
 r['private_wrapper_scope']='Originalactual73+256/all4mode/history/selection/copy/paste/menu/source oracle unchanged. Onlyadds precise22x64B outgoingsemanticcertificate records atFE0700+i0800 toexistingstrict16MiB mask. No pixel/source weakening.'
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('RESULT',r['status'],len(r['frames']))
