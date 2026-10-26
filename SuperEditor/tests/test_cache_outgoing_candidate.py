"""Private actual C21+C35+R19 cachedcarry bridge; no canonical edits/builds."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
from overlays import wrap
from d81_image import D81Image
import test_geos_incremental_editor as gate
BASE=ROOT/'build/cache-editor-product/20261026T001942640938Z/fixture'
FIT=ROOT/'build/cache-outgoing-fit/20261026T004107457274Z'
SHA=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()

def package(out,base=BASE,fit=FIT):
 f=out/'fixture';shutil.copytree(base,f);r=json.loads((f/'build/editor-report.json').read_text());s=r['symbols'];digest=bytes.fromhex(r['resident_binding']['digest']);identity=json.loads((f/'freeze.json').read_text())
 assert (fit/'control.bin').read_bytes()==(base/'build/overlays/rangeio.seo').read_bytes()[36:]
 assets={}
 for name,raw in [('rangeio','candidate.bin'),('geospage','page.bin'),('inln','query.bin')]:
  prior=(base/'build/overlays'/(name+'.seo')).read_bytes();image=wrap((fit/raw).read_bytes(),prior[5],prior[6],api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=digest)
  dest=f/'build/overlays'/(name+'.seo');dest.write_bytes(image);identity['assets'][name]=SHA(dest);assets[name]=dict(bytes=len(image)-36,sha256=SHA(dest))
  call=subprocess.run(['c1541','-attach',str(f/'build/supereditor.d81'),'-delete',name,'-write',str(dest),name+',s'],capture_output=True,text=True);assert not call.returncode,call.stdout+call.stderr
 disk=D81Image((f/'build/supereditor.d81').read_bytes())
 for name in identity['names']:assert disk.read(name.upper().encode(),kind=1).data==(f/'build/overlays'/(name+'.seo')).read_bytes()
 identity['disk_sha256']=SHA(f/'build/supereditor.d81');(f/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 overrides={
  'src/render/geos/page.s':ROOT/'src/render/geos/cache-outgoing-candidate/page.s',
  'src/render/geos/checkpoint/outgoing.s':ROOT/'src/render/geos/cache-outgoing-candidate/outgoing.s',
  'src/render/geos/cache-outgoing-candidate/cache-outgoing.inc':ROOT/'src/render/geos/cache-outgoing-candidate/cache-outgoing.inc',
  **{str(q.relative_to(ROOT)):q for q in (ROOT/'src/cache/query').glob('*') if q.is_file()},
 }
 original=f/'product-sources.zip';old=f/'product-sources-before.zip';original.rename(old)
 with zipfile.ZipFile(old)as z,zipfile.ZipFile(original,'w',zipfile.ZIP_DEFLATED)as dest:
  for n in z.namelist():
   if n not in overrides:dest.writestr(n,z.read(n))
  for n,q in overrides.items():dest.write(q,n)
 result=dict(base=str(base),fixture=str(f),assets=assets,disk_sha256=identity['disk_sha256'],scope='Three actual sealedimage replacements; originalresident unchanged. PAGE_REUSE sourceprofile consumes verifiedCR proof, explicitcarrytype2 publishes64B, neverCP79.')
 (out/'package.json').write_text(json.dumps(result,indent=2)+'\n');return f

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package-only',action='store_true');p.add_argument('--fixture',type=Path);a=p.parse_args();out=ROOT/'build/cache-outgoing-editor'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);f=a.fixture or package(out)
 if not a.package_only:
  run=out/'public15';run.mkdir();gate.run(run,f)
if __name__=='__main__':main()
