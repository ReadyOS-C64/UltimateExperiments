"""Private conservative early-wrap refusal; never a new fast-admission proof."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,inspect,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_heading_body_candidate as body
import test_geos_row_backup_candidate as backup
D=ROOT/'src/render/geos/wrap-refusal-candidate';BASE=ROOT/'build/geos-row-backup/20261025T172445081632Z/fixture'

def run(out,base,variant='candidate',smoke=False,packaged=False):
 if packaged:
  with zipfile.ZipFile(base/'product-sources.zip')as z:assert b'GEX_EARLY_WRAP=1' in z.read('src/render/geos/edit-cache.inc')
  assert variant=='candidate'
 text=inspect.getsource(body.run)
 old="after[0xd528:0xd568]==old[:64], 'admitted then actualVERIFY rejected wrap before dirtypaint'"
 new="after[0xd528:0xd568]==(old[0xd528:0xd568]if EARLY else old[:64]), 'exact earlyrefusal/noheaderwrites versus oldVERIFYrefusal'"
 assert text.count(old)==1
 ns=dict(vars(body));ns.update(D=D if variant=='candidate'else D/'control',Fixture=backup.PoisonFixture,EARLY=variant=='candidate')
 exec(compile(text.replace(old,new),str(Path(__file__))+'::early-header-contract','exec'),ns)
 result=ns['run'](out,base,'candidate',smoke=smoke,diverse=True,append=True,packaged=packaged)
 result['variant']=variant;result['backup_poison']=list(backup.observations)
 result['early_refusal_contract']=dict(old=old,new=new,scope='Only expected absence of old-header backup on proven earlyrefusal; allsource/pixel/forcedfull/metadata/16MiB assertions unchanged.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--variant',choices=['control','candidate'],default='candidate');p.add_argument('--smoke',action='store_true');p.add_argument('--packaged',action='store_true');a=p.parse_args();out=ROOT/'build/geos-wrap-refusal'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 with zipfile.ZipFile(out/'verifier.zip','w',zipfile.ZIP_DEFLATED)as z:
  for p in [Path(__file__),ROOT/'tests/test_geos_heading_body_candidate.py',ROOT/'tests/test_geos_row_backup_candidate.py',*D.glob('*')]:
   if p.is_file():z.write(p,p.relative_to(ROOT))
 run(out,a.fixture.resolve(),a.variant,a.smoke,a.packaged)
