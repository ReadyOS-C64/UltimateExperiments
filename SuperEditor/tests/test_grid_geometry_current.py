"""Actual packaged59 combined R16/LEX/row-geometry qualification, CPU only.

Reuses the released source/pixel/packet/provider/whole-REU and stack oracles.
The qualified empty-suffix kernel extends only FIRST22/COUNT0/direction-1.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,binascii,hashlib,importlib.util,json,shutil,sys
import test_grid_row_geometry_extend as extension
from d81_image import D81Image
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'src/render/grid/probes/row-geometry/full'
BASE=ROOT/'build/lexical-batch-current/20261026T194420618867Z/fixture'

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def authenticate(base):
 identity=json.loads((base/'freeze.json').read_text());report=json.loads((base/'build/editor-report.json').read_text());names=identity['names'];digest=bytes.fromhex(report['resident_binding']['digest']);disk=(base/'build/supereditor.d81').read_bytes();d=D81Image(disk)
 assert len(names)==59 and names[-5:]==['edit','tail','lex','ical','ctrl']
 assert hashlib.sha256(disk).hexdigest()==identity['disk_sha256']
 prg=(base/'build/editor.prg').read_bytes();assert hashlib.sha256(prg).hexdigest()==identity['prg_sha256']==report['sha256'];assert d.read(b'SUPEREDITOR',kind=2).data==prg
 for name in names:
  image=(base/f'build/overlays/{name}.seo').read_bytes();assert hashlib.sha256(image).hexdigest()==identity['assets'][name]
  assert image[:4]==b'SEO2'and image[20:36]==image[36:52]==digest
  assert len(image)-36==int.from_bytes(image[8:10],'little')and binascii.crc_hqx(image[36:],65535)==int.from_bytes(image[12:14],'little')
  assert d.read(name.upper().encode(),kind=1).data==image
 assert identity['assets']['geosfold']=='96f07240efb9d49a23840fa4e1c657b5551f910a98aac1da846a8774cf2122b6','qualified FIRST23 R24'
 return dict(resident=identity['prg_sha256'],binding=digest.hex(),D81=identity['disk_sha256'],assets=59)

def run(out,base,baseline):
 seal=authenticate(base);out.mkdir(parents=True)
 # The released fault helper resolves its sibling R25 labels by directory.
 # Supply only exact labels from these same packaged payloads, without
 # changing the immutable fixture or reading mutable canonical build files.
 labels=out/'labels';(labels/'r24').mkdir(parents=True);(labels/'c33').mkdir()
 for name,target in(('geosfold',labels/'r24/leaf.lbl'),('geostail',labels/'c33/geostail.lbl')):
  assert(base/f'build/overlays/{name}.bin').read_bytes()==(base/f'build/overlays/{name}.seo').read_bytes()[36:]
  shutil.copyfile(base/f'build/overlays/{name}.lbl',target)
 public=load('registered_geometry_public',D/'public.py').run(out/'public',base)
 faults=load('registered_geometry_faults',D/'faults.py').run(out/'faults',base,labels/'r24/leaf.lbl')
 compatibility=load('registered_geometry_compatibility',D/'compatibility.py').run(out/'compatibility',baseline,base)
 edges=extension.public(out/'empty-suffix',base)
 kernel=extension.kernel(out/'kernel',base,base/'build/overlays/geosfold.lbl')
 regressions=load('registered_geometry_regressions',D/'regressions.py').run(out/'regressions',base)
 stack=load('registered_geometry_stack',D/'stack.py').run(out/'stack',base)
 result=dict(status='PASS',scope=__doc__,seal=seal,public=public,faults=faults,compatibility=compatibility,edges=edges,kernel=kernel,regressions=regressions,stack=stack)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('REGISTERED_GEOMETRY_PASS',out,flush=True);return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--baseline',type=Path,default=BASE);a=p.parse_args();out=ROOT/'build/geometry-registered'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');print('RUN',out,flush=True);run(out,a.fixture.resolve(),a.baseline.resolve())
