"""Current actual59 reduced-REU/large-document gate; released capacity oracles.

Only registered catalog cardinality/tail are adapted initially. No capsule,
source, capacity, navigation, pixel, history, or REU guard is substituted.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,types
import test_cache_capacity_current as original
import test_grid_capture_index as index
ROOT=original.ROOT
BASE=index.FIXED

def run(out,base,physical=16):
 seal=index.authenticate(base)
 path=ROOT/'tests/test_cache_capacity_current.py';text=path.read_text()
 old="assert len(identity['names'])==54 and identity['names'][-1]=='line'"
 assert text.count(old)==1
 text=text.replace(old,"assert len(identity['names'])==59 and identity['names'][-1]=='ctrl'")
 module=types.ModuleType('registered_capacity_original');module.__file__=str(path)
 exec(compile(text,str(path),'exec'),module.__dict__)
 try:result=module.run(out,base,physical)
 finally:
  if out.exists():(out/'adapter.json').write_text(json.dumps(dict(scope=__doc__,seal=seal,original_source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),changes=['Exact59 names; final registered ctrl. No other original assertion modified.']),indent=2)+'\n')
 result['registered_adaptation']=dict(seal=seal,original_verifier_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--banks',type=int,choices=[16,32],default=16);a=p.parse_args();out=ROOT/'build/cache-capacity-registered'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.banks)
