"""Controlled current54 cache lifecycle on a parent-released immutable fixture.

Reuses the original evaluator unchanged: observer17/ring96, checked type53,
managed invalidation, exact warm extents, source/history, actual VIC and disk.
Fresh trusted bootstrap/same process provider only; no ReadyOS, physical RESTORE
or saved-stack continuation claim. Own8300/text8400..8439, never kill anotherPID.
"""
from pathlib import Path
import argparse,hashlib,inspect,json
import test_lifecycle_cache_current as prior
ROOT=prior.ROOT
BASE=ROOT/'build/cache-editor-product/20261026T035310363807Z/fixture'


def prepare(base):
 names=json.loads((base/'freeze.json').read_text())['names'];assert len(names)==54 and len(set(names))==54
 # The old immutable preparation function has one hardcoded provenance field.
 # Rebind only that metadata expression and unique destination name. Its
 # build, packaged-image identity, bootstrap and scenario code are untouched.
 source=inspect.getsource(prior.prepare);assert source.count('catalog=53,')==1
 source=source.replace('catalog=53,',"catalog=len(json.loads((base/'freeze.json').read_text())['names']),")
 assert source.count("'-lifecycle-cache-current-native'")==1
 source=source.replace("'-lifecycle-cache-current-native'","'-lifecycle-cache-current54-native'")
 ns=dict(vars(prior),__file__=__file__);exec(compile(source,'prepare-current54.py','exec'),ns)
 e,n,plan=ns['prepare'](base);(e/'prepare-current54.py').write_text(source)
 identity=json.loads((e/'freeze.json').read_text());assert identity['catalog']==names
 q=json.loads((e/'qualification.json').read_text());assert q['catalog']==54
 q.update(ordered_catalog=names,original_wrapper_sha256=hashlib.sha256(Path(prior.__file__).read_bytes()).hexdigest(),new_wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),metadata_adaptation='Only53literal→actual immutable catalog count; all original evaluator assertions retained.')
 (e/'qualification.json').write_text(json.dumps(q,indent=2)+'\n');return e,n,plan


def evaluate(e):
 result=prior.evaluate(e);q=json.loads((e/'qualification.json').read_text());assert q['catalog']==54
 result.update(actual_catalog_assets=54,actual_ordered_catalog=q['ordered_catalog'],current54_scope=__doc__,current54_wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 # Original asserts already require a freshly authenticated baseline and a
 # changed capability/incarnation after actualFile/Open. Keep that strict
 # behavior with C12's earlier checked optional-cache retirement.
 assert result['reopened_fresh_baseline']['token']!=result['typed53arena']['token']
 (e/'current54-result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--run',action='store_true');p.add_argument('--verify',type=Path);a=p.parse_args()
 if a.verify:print(json.dumps(evaluate(a.verify.resolve()),indent=2));return
 assert a.run,'explicit --run required';e,n,plan=prepare(a.fixture.resolve());print('CURRENT54_LIFECYCLE_NATIVE',e,len(n.steps),'steps',flush=True)
 project=prior.life.native.live.grid.synchronous_project(n.out);prior.vice_plan.PROJECT=project;prior.life.component.command('dotnet','build',project,'--nologo');prior.vice_plan.run_plan(plan,n.out)
 result=evaluate(e);prior.free_ports();result['owned_ports_released']=True;(e/'current54-result.json').write_text(json.dumps(result,indent=2)+'\n');print('CURRENT54_LIFECYCLE_PASS',e,result['native_pixels'],flush=True)
if __name__=='__main__':main()
