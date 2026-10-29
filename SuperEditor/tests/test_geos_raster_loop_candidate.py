"""Private per-glyph horizontal raster hoist; exact renderer remains fallback."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json
import test_geos_strip_raster_candidate as build
import test_geos_literal_byte_candidate as proof
ROOT=build.ROOT;D=ROOT/'src/render/geos/raster-loop-candidate';BASE=ROOT/'build/geos-incremental-editor/20261025T180626648789Z/fixture'
def prepare(out,base,variant):
 old=build.D;build.D=D
 try:src,s,ls,raw,image,mods=build.build(out/'link',base,variant)
 finally:build.D=old
 return out/'link',src,s,ls,raw,image,mods
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--suite',choices=['fit','component','inline','fold','incremental'],default='fit');p.add_argument('--variant',choices=['candidate','control'],default='candidate');a=p.parse_args();out=ROOT/'build/geos-raster-loop'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);proof.prepare=prepare;proof.PRIVATE=D
 if a.suite=='fit':
  _,_,_,_,raw,image,mods=prepare(out,BASE,a.variant);print('FIT',len(raw),mods,flush=True)
 elif a.suite=='component':proof.component(out,BASE,a.variant)
 else:proof.public_gate(out,BASE,a.variant,a.suite)
