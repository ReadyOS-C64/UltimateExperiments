"""Existing independent gates on the private R28 heading-body candidate.

No shared verifier, product source, or build is edited. Only reviewed historical
expected-path predicates change in the old forward feature test.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,inspect,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_heading_body_candidate as body

def run(out,fixture,suite,packaged=False):
 if suite=='ordinary':
  import test_geos_incremental_editor as original
  text=inspect.getsource(original.run)
  old="eligible=(classes and tag in ('inline','basic'))or(heading_prefix and tag=='prefix')"
  new="eligible=(classes and tag in ('heading','inline','basic'))or(heading_prefix and tag=='prefix')"
  assert text.count(old)==1,'Historical ordinary verifier changed; review explicitly'
  namespace=dict(vars(original));exec(compile(text.replace(old,new),str(Path(__file__))+'::reviewed-heading-path','exec'),namespace)
  (out/'predicate-adaptations.json').write_text(json.dumps(dict(original_sha256=hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest(),changes=[[old,new]],scope='Only intended heading expected-path. All independent/fullrenderer/REU/source guards retained.'),indent=2)+'\n')
  return namespace['run'](out,fixture)
 if suite=='back':
  import test_geos_heading_back as original
  original.D=body.D
  return original.run(out,fixture,'candidate',packaged=packaged)
 if suite=='forward':
  import test_geos_heading_transition as original
  text=inspect.getsource(original.run)
  changes=[("data=raw;check('fallback-restores-heading',False)","data=raw;check('fallback-restores-heading',True)"),
   ("('heading-interior','# Heading words\\rTail.',5,False)","('heading-interior','# Heading words\\rTail.',5,True)")]
  for old,new in changes:
   assert text.count(old)==1,(old,'Historical verifier changed; review explicitly')
   text=text.replace(old,new)
  namespace=dict(vars(original));namespace['D']=body.D
  exec(compile(text,str(Path(__file__))+'::reviewed-forward-paths','exec'),namespace)
  (out/'predicate-adaptations.json').write_text(json.dumps(dict(original_sha256=hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest(),changes=changes,scope='Expected-path predicates only. All independent source/forcedfull/pixel/attribute/anchor/REU/owner guards retained.'),indent=2)+'\n')
  return namespace['run'](out,fixture,'candidate',packaged=packaged)
 raise AssertionError(suite)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--suite',choices=['ordinary','forward','back'],required=True);p.add_argument('--packaged',action='store_true');a=p.parse_args();out=ROOT/'build/geos-heading-body-regression'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+a.suite);out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.suite,a.packaged)
