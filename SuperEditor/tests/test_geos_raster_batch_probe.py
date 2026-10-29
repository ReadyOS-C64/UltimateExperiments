"""Private resolver tile-range batching; no production or shared build edits."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib
import test_geos_strip_raster_candidate as build
import test_geos_literal_byte_candidate as proof
ROOT=build.ROOT;D=ROOT/'src/render/geos/raster-batch-probe';BASE=ROOT/'build/cache-editor-product/20261026T021924007962Z/fixture'
def prepare(out,base,variant):
 old=build.D;build.D=D
 try:src,s,ls,raw,image,mods=build.build(out/'link',base,variant)
 finally:build.D=old
 return out/'link',src,s,ls,raw,image,mods
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=BASE);p.add_argument('--suite',choices=['fit','component','incremental','public'],default='fit');p.add_argument('--variant',choices=['candidate','control'],default='candidate');a=p.parse_args();out=ROOT/'build/geos-raster-batch'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);proof.prepare=prepare;proof.PRIVATE=D
 if a.suite=='fit':
  _,_,_,_,raw,image,mods=prepare(out,a.base,a.variant);result=dict(status='fits',payload=len(raw),sha256=hashlib.sha256(image).hexdigest(),modules=mods);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
 elif a.suite=='component':proof.component(out,a.base,a.variant)
 elif a.suite=='public':
  import test_geos_raster_public_probe as public
  public.candidate.prepare=prepare;public.run(out,a.base)
 else:proof.public_gate(out,a.base,a.variant,a.suite)
