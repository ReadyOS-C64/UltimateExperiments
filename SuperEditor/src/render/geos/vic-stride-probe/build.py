"""Private two-asset rebuild from pinned source ZIP; no shared outputs."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,zipfile
D=Path(__file__).resolve().parent

def build(out,base,variant):
 out=out.resolve();base=base.resolve();out.mkdir(parents=True);project=out/'project';project.mkdir();frozen=out/'fixture';shutil.copytree(base,frozen)
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for n in z.namelist():
   if n.startswith('src/')and(n.endswith('.inc')or n.startswith('src/render/geos/style-typing/')or n in ['src/render/geos/typing/'+x+'.s'for x in ('transfer','status-normal','status-raster')])or n in ('tools/overlays.py','tools/bindings.py','tools/module_bindings.py'):
    p=project/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
  assert z.read('src/render/geos/style-typing/wide.s')==(D/'wide-before.s').read_bytes()
 font=project/'assets/fonts/generated/bsw9-widths.bin';font.parent.mkdir(parents=True);shutil.copy2(base/'fonts/bsw9-widths.bin',font)
 shutil.copy2(D/('wide-before.s'if variant=='before'else'wide.s'),project/'src/render/geos/style-typing/wide.s')
 p=project/'src/render/geos/style-typing/build.py';spec=importlib.util.spec_from_file_location('warm_shift_'+variant,p);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);images,budget=b.build(out/'assets',frozen)
 ident=json.loads((frozen/'freeze.json').read_text());changed=[]
 for tag,name in [('stage','type'),('worker','gtype')]:
  p=frozen/'build/overlays'/f'{name}.seo';old=p.read_bytes();data=images[tag]
  if variant=='before':assert data==old,(name,'original source-rebuilt payload differs')
  p.write_bytes(data);ident['assets'][name]=hashlib.sha256(data).hexdigest()
  if data!=old:changed.append(name)
  dest=frozen/'build/geos-prod/style-typing';dest.mkdir(parents=True,exist_ok=True)
  for ext in('.bin','.lbl','.map'):shutil.copy2(out/'assets'/(tag+ext),dest/(tag+ext))
 if variant=='after':assert changed==['type','gtype'],changed
 ident['private_variant']=dict(name='vic-stride8',variant=variant,changes=changed,packaging='CPU catalog substitutions only; original D81 retained, no native/package claim')
 (frozen/'freeze.json').write_text(json.dumps(ident,indent=2)+'\n');(out/'budget.json').write_text(json.dumps(budget,indent=2)+'\n');return frozen,budget
