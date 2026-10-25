"""Original37 heading cases against packaged bidirectional R28.

Only the now-supported corrective BACK expected path changes. Every pixel,
source, metadata, typed-DMA, whole-REU and opaque-entry barrier remains intact.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,inspect,json,zipfile
import test_geos_heading_transition as original

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();base=a.fixture.resolve()
 with zipfile.ZipFile(base/'product-sources.zip')as z:assert b'GEX_HEADING_BACK_CLASS=3'in z.read('src/render/geos/edit-cache.inc')
 source=inspect.getsource(original.run);old="data=raw;check('fallback-restores-heading',False)";new="data=raw;check('fallback-restores-heading',True)";assert source.count(old)==1
 out=original.ROOT/'build/geos-heading-forward-packaged'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 namespace=dict(vars(original));exec(compile(source.replace(old,new),str(Path(__file__))+'::supported-inverse-path','exec'),namespace)
 (out/'expected-path-change.json').write_text(json.dumps(dict(old=old,new=new,packaged_only=True,all_oracles_unchanged=True),indent=2)+'\n')
 namespace['run'](out,base,'candidate',False,True)

if __name__=='__main__':main()
