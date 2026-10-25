"""Package the private48 CPU product; never touches shared products."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[5]
def build(out,base,tree):
 out.mkdir(parents=True,exist_ok=True);fixture=out/'fixture'
 if not fixture.exists():shutil.copytree(base,fixture)
 # Caller built C14 from the current span source against this private resident.
 shutil.copy2(tree/'build/overlays/styler.seo',fixture/'build/overlays/styler.seo')
 sys.path.insert(0,str(ROOT/'tools'));from d81_image import D81Image
 identity=json.loads((fixture/'freeze.json').read_text());names=identity['names'];assert len(names)==48 and names[-1]=='grid'
 assert len((fixture/'build/overlays/grid.seo').read_bytes())-36==3914
 assert len((fixture/'build/overlays/styler.seo').read_bytes())-36==4047
 archive=fixture/'product-sources.zip'
 with zipfile.ZipFile(archive)as z:c={n:z.read(n)for n in z.namelist()}
 c['src/style/plan.s']=(tree/'src/style/plan.s').read_bytes()
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
  for n,b in c.items():z.writestr(n,b)
 # Start afresh from the predecessor disk, then replace every sealed product.
 shutil.copy2(base/'build/supereditor.d81',fixture/'build/supereditor.d81')
 disk=fixture/'build/supereditor.d81';command=['c1541','-attach',str(disk),'-delete','supereditor','-write',str(fixture/'build/editor.prg'),'supereditor']
 for n in names:
  if n!='grid':command+=['-delete',n]
  command+=['-write',str(fixture/f'build/overlays/{n}.seo'),n+',s']
 p=subprocess.run(command,capture_output=True,text=True);(out/'package.log').write_text(p.stdout+p.stderr);assert not p.returncode,p.stdout+p.stderr
 parsed=D81Image(disk.read_bytes());assert parsed.read(b'SUPEREDITOR',kind=2).data==(fixture/'build/editor.prg').read_bytes()
 for n in names:assert parsed.read(n.upper().encode(),kind=1).data==(fixture/f'build/overlays/{n}.seo').read_bytes(),n
 identity['assets']={n:hashlib.sha256((fixture/f'build/overlays/{n}.seo').read_bytes()).hexdigest()for n in names};identity['disk_sha256']=hashlib.sha256(disk.read_bytes()).hexdigest();identity['product_sources_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest();identity['private_unpacked_48']=False;identity['private_packaged_48']=True;identity['c14_current_plan_sha256']=hashlib.sha256(c['src/style/plan.s']).hexdigest();identity['c33_payload']=3914
 (fixture/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n');print(fixture);print('PACKAGED48',identity['disk_sha256']);return fixture
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--base',type=Path,required=True);p.add_argument('--tree',type=Path,required=True);a=p.parse_args();build(a.out.resolve(),a.base.resolve(),a.tree.resolve())
