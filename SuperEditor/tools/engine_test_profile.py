"""Run existing independent models against either old resident or real R2 engine.

--editor-engine selects the actual production link and matching sidecars. Test
vectors/assertions stay identical; results get separate names and asset hashes.
"""
import hashlib,json,sys
from pathlib import Path
from overlays import HEADER
ROOT=Path(__file__).resolve().parents[1]
class Profile:
 def __init__(self,stem,suite):
  self.engine='--editor-engine' in sys.argv
  self.stem='editor' if self.engine else stem;self.suite=suite
  self.report=json.loads((ROOT/f'build/{self.stem}-report.json').read_text())
  self.image=(ROOT/f'build/{self.stem}.prg').read_bytes()
  self.result_path=ROOT/'build'/f'{"engine-" if self.engine else ""}{suite}-test-result.json'
  self.images={};self.files={}
 def assets(self,names):
  mapping={'hedit':'eedit','hplay':'eplay','hwin':'window','wedit':'eedit','wplay':'eplay'}
  self.files={n:mapping.get(n,n) if self.engine else n for n in names}
  if self.engine:
   self.files['engine']='engine'
   # Selected-reference capture is a separately sealed R19 in current editor.
   # Historical editor/probe reports retain their original resident reader.
   if 'se_engine_range_range_token' in self.report['symbols']:
    self.files['rangeio']='rangeio'
  self.images={n:(ROOT/f'build/overlays/{filename}.seo').read_bytes() for n,filename in self.files.items()}
  return self.images
 def import_engine(self,m,s):
  if not self.engine:return
  if not self.images:self.assets([])
  result,_=m.call(s['se_overlay_init']);assert not result.p&1,hex(result.a)
  for image in self.images.values():
   m.load(s['se_overlay_header'],image[:HEADER]);m.load(0x5000,image[HEADER:]);result,_=m.call(s['se_overlay_import']);assert not result.p&1,hex(result.a)
 @property
 def identity(self):
  if not self.engine:return {}
  return dict(secondary_engine_overlay=True,resident_binding=self.report['resident_binding']['digest'],
   asset_files=self.files,overlay_sha256={n:hashlib.sha256(image).hexdigest() for n,image in self.images.items()})
