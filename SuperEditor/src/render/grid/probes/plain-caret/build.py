"""Private frozen pair build; only C33 dependency scan placement changes."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[5]

def build(out,base):
 out.mkdir(parents=True);tree=out/'tree'
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(tree)
 p=tree/'src/render/grid/caret/build.py';spec=importlib.util.spec_from_file_location('plain_caret_builder',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.build(out/'control',base)
 for name in ('grid','geostail'):assert(out/'control'/(name+'.seo')).read_bytes()==(base/'build/overlays'/(name+'.seo')).read_bytes(),(name,'control reassembly')
 target=tree/'src/render/grid/caret/caret.s';old=target.read_text();new=old
 needle=' jsr authenticate_helper\n jcs miss\n';assert new.count(needle)==1;new=new.replace(needle,'',1)
 needle=':\n jsr admit\n jcs miss\n lda OP\n';assert new.count(needle)==1;new=new.replace(needle,':\n jsr authenticate_helper\n jcs miss\n jsr admit\n jcs miss\n lda OP\n')
 needle='authenticate_helper:\n ldy #2\n@image:\n';assert new.count(needle)==1
 new=new.replace(needle,'authenticate_helper:\n ldy #0\n beq authenticate_dependencies\nauthenticate_paragraph:\n ldy #2\nauthenticate_dependencies:\n@image:\n')
 needle='type_try:\n';assert new.count(needle)==1;new=new.replace(needle,'type_try:\n jsr authenticate_paragraph\n jcs miss\n')
 target.write_text(new);(out/'caret-original.s').write_text(old);(out/'caret-candidate.s').write_text(new)
 m.build(out/'candidate',base)
 assert(out/'candidate/geostail.seo').read_bytes()==(out/'control/geostail.seo').read_bytes(),'R25 must remain exact'
 frozen=out/'fixture';shutil.copytree(base,frozen);image=(out/'candidate/grid.seo').read_bytes();(frozen/'build/overlays/grid.seo').write_bytes(image)
 identity=json.load(open(frozen/'freeze.json'));identity['assets']['grid']=hashlib.sha256(image).hexdigest();identity['private_change']='OnlyC33caret/capture dependency selection; R25exact/controlpair exact first.';(frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 proof=dict(status='built',baseline=str(base),control_pair_byte_identical=True,R25_byte_identical=True,C33_sha256=identity['assets']['grid'],source_diff='Moved initial authentication after existing typed-revision branch; capture/caretLDY0, type_trystrictLDY2 sharedscan.',newBSS=0,newZP=0)
 for name in ('control','candidate'):
  proof[name]=(out/name/'grid.map').read_text().split('Segment list:')[1].split('Exports list by name:')[0].strip()
 (out/'build.json').write_text(json.dumps(proof,indent=2)+'\n');return frozen,proof
