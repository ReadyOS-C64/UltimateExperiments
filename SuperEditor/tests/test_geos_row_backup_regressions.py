"""Unchanged public15 and historical class2/3 probes on private no-backup R28."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_row_backup_candidate as candidate

def run(out,fixture,suite):
 if suite=='ordinary':
  import test_geos_incremental_editor as original
  # Current canonical verifier recognizes GEX_HEADING_BODY_CLASS=4. No expected
  # path, pixel, source, owner or REU assertion is altered.
  return original.run(out,fixture)
 import test_geos_heading_body_candidate_regressions as historical
 historical.body.D=candidate.D
 return historical.run(out,fixture,suite,packaged=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--suite',choices=['ordinary','forward','back'],required=True);a=p.parse_args();out=ROOT/'build/geos-row-backup-regression'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+a.suite);out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.suite)
