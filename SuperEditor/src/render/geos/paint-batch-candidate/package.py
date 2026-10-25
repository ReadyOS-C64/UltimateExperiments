"""Create private, fully byte-compared48-asset candidate disk/fixture."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib,zipfile,subprocess
ROOT=Path(__file__).resolve().parents[4];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_paint_batch_candidate as test
from d81_image import D81Image
out=ROOT/'build/geos-paint-batch-native-input'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
f=test.install(out,test.BASE,'candidate');source=ROOT/'src/render/geos/paint-batch-candidate/page-paint.s';old=(f/'product-sources.zip').read_bytes();import io
with zipfile.ZipFile(io.BytesIO(old))as z,zipfile.ZipFile(f/'product-sources.zip','w',zipfile.ZIP_DEFLATED)as w:
 for n in z.namelist():w.writestr(n,source.read_bytes()if n=='src/render/geos/page-paint.s'else z.read(n))
disk=f/'build/supereditor.d81';p=subprocess.run(['c1541','-attach',str(disk),'-delete','geospaint','-write',str(f/'build/overlays/geospaint.seo'),'geospaint,s'],capture_output=True,text=True);(out/'package.log').write_text(p.stdout+p.stderr);assert not p.returncode
image=D81Image(disk.read_bytes());meta=json.loads((f/'freeze.json').read_text());assert len(meta['names'])==48
for name in meta['names']:assert image.read(name.upper().encode(),kind=1).data==(f/'build/overlays'/(name+'.seo')).read_bytes(),name
assert image.read(b'SUPEREDITOR',kind=2).data==(f/'build/editor.prg').read_bytes()
meta['disk_sha256']=hashlib.sha256(disk.read_bytes()).hexdigest();meta['sources']['src/render/geos/page-paint.s']=hashlib.sha256(source.read_bytes()).hexdigest();(f/'freeze.json').write_text(json.dumps(meta,indent=2)+'\n');print(f)
