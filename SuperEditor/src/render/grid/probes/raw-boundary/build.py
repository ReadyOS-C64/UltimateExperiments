"""Private boundary correction; sealed wrapped release remains immutable."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[5]
RELEASE=ROOT/'agentsworking/evidence/M8/20261026T074830577823Z-grid-raw-wrapped'
def build(out):
 out.mkdir(parents=True);base=RELEASE/'fixture';tree=out/'tree';tree.mkdir()
 with zipfile.ZipFile(RELEASE/'release/generated-sources.zip')as z:z.extractall(tree)
 d=tree/'src/render/grid/caret';spec=importlib.util.spec_from_file_location('boundary_pair',d/'build.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.build(out/'control',base)
 for n in('grid','geostail'):assert(out/'control'/(n+'.seo')).read_bytes()==(base/'build/overlays'/(n+'.seo')).read_bytes(),n+' control differs'
 p=d/'helper.s';s=p.read_text();old='@raw_length:\n lda TLEN\n clc\n adc SIGN\n';new='@raw_length:\n lda TLEN\n cmp W\n jcs invalid ;old full-width row may have a separate CR/EOF continuation\n clc\n adc SIGN\n';assert s.count(old)==1;p.write_text(s.replace(old,new))
 m.build(out/'candidate',base);fixture=out/'fixture';shutil.copytree(base,fixture);ident=json.loads((fixture/'freeze.json').read_text())
 for n in('grid','geostail'):
  image=(out/'candidate'/(n+'.seo')).read_bytes();(fixture/'build/overlays'/(n+'.seo')).write_bytes(image);ident['assets'][n]=hashlib.sha256(image).hexdigest()
 ident['private_change']='Raw short path requires old row length below width before applying signed edit; full-width deletion uses checked long/fallback path.';(fixture/'freeze.json').write_text(json.dumps(ident,indent=2)+'\n')
 result=dict(status='built',base=str(base),control_byte_identical=True,changed=['geostail','grid'],newBSS=0,newZP=0,assets={n:ident['assets'][n]for n in('grid','geostail','viewsource')})
 for n in('grid','geostail'):result[n]=(out/'candidate'/(n+'.map')).read_text().split('Segment list:')[1].split('Exports list by name:')[0].strip()
 (out/'build.json').write_text(json.dumps(result,indent=2)+'\n');return fixture,result
if __name__=='__main__':
 import sys
 print(build(Path(sys.argv[1]).resolve())[1])
