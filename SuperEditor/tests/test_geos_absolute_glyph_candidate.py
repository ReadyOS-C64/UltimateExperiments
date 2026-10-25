"""Private fixed-frame R21 glyph specialization; public and component guards unchanged."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json
import test_geos_strip_raster_candidate as builder
import test_geos_literal_byte_candidate as proof
ROOT=builder.ROOT
D=ROOT/'src/render/geos/absolute-glyph-candidate'
BASE=ROOT/'build/geos-incremental-editor/20261025T194101943594Z/fixture'

def prepare(out,base,variant):
    saved=builder.D;builder.D=D
    try:src,s,labels,raw,image,modules=builder.build(out/'link',base,variant)
    finally:builder.D=saved
    return out/'link',src,s,labels,raw,image,modules

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--suite',choices=['fit','component','inline','fold','incremental'],default='fit');p.add_argument('--variant',choices=['candidate','control'],default='candidate');p.add_argument('--base',type=Path,default=BASE);a=p.parse_args()
    out=ROOT/'build/geos-absolute-glyph'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+a.suite+'-'+a.variant);out.mkdir(parents=True)
    print('RUN',out,flush=True);proof.prepare=prepare;proof.PRIVATE=D
    if a.suite=='fit':
        _,_,_,_,raw,image,mods=prepare(out,a.base.resolve(),a.variant)
        print('FIT',len(raw),mods,flush=True)
    elif a.suite=='component':proof.component(out,a.base.resolve(),a.variant)
    else:proof.public_gate(out,a.base.resolve(),a.variant,a.suite)
