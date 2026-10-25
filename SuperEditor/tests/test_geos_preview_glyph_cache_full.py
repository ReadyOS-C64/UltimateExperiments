"""Reuse unchanged79480+4096 packed/native oracle with declared4160B cacheextent."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,sys,importlib.util,shutil,json
import test_geos_preview_glyph_cache as cache
reference=cache.reference;old=cache.old;ROOT=cache.ROOT;ORIGINAL=old.build
BUILD_SCRIPT='build-cache.py'
class Masked(cache.Fixture):
 def __init__(self,*a):
  self.cache_bank=None;super().__init__(*a);self.cache_bank=self.m.read(self.s['se_reu_map']+self.get('se_gc_handle',1))
 def glyph(self,*a,**kw):kw.pop('ink',None);return super().glyph(*a,**kw)
 def reu(self):
  raw=super().reu()
  if self.cache_bank is not None:
   p=self.cache_bank*65536+0xeb69;raw=raw[:p]+bytes(4160)+raw[p+4160:]
  return raw

def build(out,frozen,candidate,source_dir=None):
 if not candidate:return cache.build_control(out,frozen)
 spec=importlib.util.spec_from_file_location('glyph_cache_build',cache.D/BUILD_SCRIPT);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 old.build=ORIGINAL
 try:result=m.build(out,frozen)
 finally:old.build=build
 for ext in('bin','lbl'):shutil.copy2(out/('cache.'+ext),out/('r23.'+ext))
 return old.symbols(out/'r23.lbl'),result['bytes']
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=cache.BASE);x=p.parse_args();out=ROOT/'build/geos-preview-glyph-cache-full'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 old.build=build;reference.Fixture=Masked
 r=reference.run(out,x.fixture.resolve(),False);r['scope']='Exactexisting79480+4096oracle with completecacheenabled, all64KiBRAM guard + actualwhole16MiB exceptexplicit4160B derivedcache incapturedownedFEbank. No generic/source/nativeclaim.';(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
