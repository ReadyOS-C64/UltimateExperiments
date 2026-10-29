"""Independent16-bank CPU stress on the sealed private C19 fixture.
Uses the released workload/strict typedDMA and capacity expectations unchanged.
No storedfold/far phase in this reduced profile; preview and all4modes remain.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json
import test_retention_grammar_stress as stress
ROOT=stress.ROOT
BASE=ROOT/'build/retention-grammar/20261026T200015684677Z/link/fixture'
def run(out,base,rounds=96):
 r=stress.run(out,base,16,rounds)
 assert r['status']=='passed' and r['physical_banks']==16 and r['rounds']==rounds
 assert r['checkpoint_max_allocated_banks']<=15 and r['checkpoint_max_objects']<=8
 assert len(r['events'])==rounds+1 and r['events'][-1]['turn']=='repeated32'
 assert all(not c['tag'].startswith('above64KiB')for c in r['checks'])
 r['reduced_qualification']=dict(physical_banks=16,usable_banks=15,modeled_mutation_history_operations=sum(3 for e in r['events']if e['delta']),fullpixel_frames=len(r['pixel_checks']),canonical_history_checkpoints=len(r['checks']),no_stored_fold_or_far_claim=True,monitor_limit='Raw STA peaks include source-reset initialization and are not a physical16-bank allocation highwater. Checkpoint peaks only are qualified.',scope=__doc__)
 (out/'result-qualified.json').write_text(json.dumps(r,indent=2)+'\n');print('REDUCED16_PASS',out,json.dumps(r['reduced_qualification']),flush=True);return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--rounds',type=int,default=96);a=p.parse_args();out=ROOT/'build/retention-grammar16'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture,a.rounds)
