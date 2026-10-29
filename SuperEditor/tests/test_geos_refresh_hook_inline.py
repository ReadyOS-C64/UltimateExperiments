"""Existing independent inline19 oracle with stricter current16MiB write spans."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,inspect,json
import test_geos_semantic_editor as original
import test_geos_semantic_consumer as c
ROOT=Path(__file__).resolve().parents[1]

def run(out,fixture):
 source=inspect.getsource(original.run);start=source.index('        for a,b in ([(start,start+64)]+');end=source.index('        assert f.read(0xC600',start);source=source[:start]+'        c.outside_cache(f,reu,tag)\n'+source[end:];namespace=dict(original.__dict__,c=c);exec(compile(source,__file__+':exact-spans','exec'),namespace)
 saved=original.geos.Fixture;original.geos.Fixture=c.Fixture
 try:r=namespace['run'](out,fixture,inline_case=True)
 finally:original.geos.Fixture=saved
 r['private_verifier_scope']='Originalinline19source/pixels/attrs/anchors/nav/menu/edit oracle unchanged; Fixture dumps16MiB; exact declaredcurrentcache/CPspans replace oldreservedwholepacket/backupmask. No product substitution/hostAUXcall.';r['wrapper_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();out=ROOT/'build/geos-refresh-hook-inline'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);r=run(out,a.fixture.resolve());print('RESULT',r['status'],'frames',len(r['frames']))
