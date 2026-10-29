from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent;sys.path[:0]=[str(ROOT/'tools')]
from overlays import wrap
BASE=ROOT/'build/geos-incremental-editor/20261025T125409878419Z/fixture'
def command(*args):
 p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True);assert p.returncode==0,(p.stdout,p.stderr)
def build(out,base=BASE):
 out.mkdir(parents=True,exist_ok=True);inc=out/'includes';inc.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for n in z.namelist():
   if n.startswith('src/')and n.endswith(('.s','.inc')):
    p=inc/n[4:];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
  cfg=z.read('cfg/geos-editor-page.cfg')
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];images={};budgets={}
 for label in ['before','after']:
  p=out/label;p.mkdir();(p/'leaf.cfg').write_bytes(cfg);override=p/'includes/render/geos';override.mkdir(parents=True)
  if label=='after':
   for n in ['preview-cache.s','preview-cache.inc']:(override/n).write_bytes((D/n).read_bytes())
  command(sys.executable,'tools/overlay_api.py','--all-public','--symbols','text_ptr','screen_ptr','--report',base/'build/editor-report.json','--output',p/'editor-api.inc')
  command('ca65','-g','-I',p,'-I',p/'includes','-I',inc,'-o',p/'preview.o',inc/'render/geos/preview.s')
  command(sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',p/'bindings.s',p/'preview.o');command('ca65','-g','-o',p/'bindings.o',p/'bindings.s')
  command('ld65','-C',p/'leaf.cfg','-o',p/'preview.bin','-m',p/'preview.map','-Ln',p/'preview.lbl',p/'preview.o',p/'bindings.o')
  raw=(p/'preview.bin').read_bytes();budgets[label]=len(raw);images[label]=wrap(raw,1,27,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(report['resident_binding']['digest']));(p/'preview.seo').write_bytes(images[label])
  if label=='before':assert images[label]==(base/'build/overlays/geospreview.seo').read_bytes(),'strict baseline changed'
 (out/'budget.json').write_text(json.dumps(budgets,indent=2)+'\n');return images,budgets
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()if len(sys.argv)>2 else BASE)[1])
