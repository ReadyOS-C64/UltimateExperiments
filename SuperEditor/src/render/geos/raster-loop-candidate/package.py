"""Private coherent48-asset R21 raster-loop fixture. No shared writes."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib,zipfile,subprocess,shutil,io
ROOT=Path(__file__).resolve().parents[4];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_raster_loop_candidate as test
from d81_image import D81Image
out=ROOT/'build/geos-raster-loop-native-input'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);_,_,_,_,raw,image,mods=test.prepare(out,test.BASE,'candidate');f=out/'fixture';shutil.copytree(test.BASE,f);(f/'build/overlays/geosrow.seo').write_bytes(image)
old=(f/'product-sources.zip').read_bytes();changes={'src/render/geos/literal-byte/'+n+'.s':(test.D/(n+'.s')).read_bytes()for n in ['row','glyph','measure','assets']}
with zipfile.ZipFile(io.BytesIO(old))as z,zipfile.ZipFile(f/'product-sources.zip','w',zipfile.ZIP_DEFLATED)as w:
 for n in z.namelist():w.writestr(n,changes.get(n,z.read(n)))
disk=f/'build/supereditor.d81';p=subprocess.run(['c1541','-attach',str(disk),'-delete','geosrow','-write',str(f/'build/overlays/geosrow.seo'),'geosrow,s'],capture_output=True,text=True);(out/'package.log').write_text(p.stdout+p.stderr);assert not p.returncode
im=D81Image(disk.read_bytes());meta=json.loads((f/'freeze.json').read_text());assert len(meta['names'])==48
for name in meta['names']:assert im.read(name.upper().encode(),kind=1).data==(f/'build/overlays'/(name+'.seo')).read_bytes(),name
assert im.read(b'SUPEREDITOR',kind=2).data==(f/'build/editor.prg').read_bytes();meta['assets']['geosrow']=hashlib.sha256(image).hexdigest();meta['disk_sha256']=hashlib.sha256(disk.read_bytes()).hexdigest()
for n,b in changes.items():meta['sources'][n]=hashlib.sha256(b).hexdigest()
meta['private_R21_raster_loop']=dict(payload=len(raw),newstate=0,newBSS=0,newZP=0);(f/'freeze.json').write_text(json.dumps(meta,indent=2)+'\n');(out/'link.json').write_text(json.dumps(dict(payload=len(raw),sha256=hashlib.sha256(image).hexdigest(),segments=mods),indent=2)+'\n');print(f)
