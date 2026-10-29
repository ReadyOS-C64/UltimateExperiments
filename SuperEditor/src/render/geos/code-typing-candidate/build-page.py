"""Private C21 publisher: actual C24 language stamped into reserved prefix30/31."""
from pathlib import Path
import sys,subprocess,json,zipfile
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify
from overlays import wrap
def build(out,base):
 out.mkdir(parents=True,exist_ok=True);prod=out/'production';prod.mkdir(exist_ok=True)
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for n in z.namelist():
   if n.startswith(('src/','assets/','cfg/'))and not n.endswith('/'):
    p=prod/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
 p=prod/'src/render/geos/page.s';text=p.read_text();text=text.replace('prepare_line:\n','prepare_line:\n    lda GSEM_FRAME+GSEM_LANG\n    sta GP_RECORD+30\n    eor #$FF\n    sta GP_RECORD+31\n',1);p.write_text(text)
 d=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest'];s=json.loads((base/'build/editor-report.json').read_text())['symbols'];(out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 def run(a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True)
 objects=[]
 for name in ['page','cache']:
  obj=out/(name+'.o');run(['ca65','-g','-I',out,'-I',prod/'src','-o',obj,prod/'src/render/geos'/(name+'.s')]);objects.append(obj)
 run([sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects]);run(['ca65','-o',out/'aliases.o',out/'aliases.s']);run(['ld65','-C',prod/'cfg/geos-editor-page.cfg','-o',out/'page.bin','-Ln',out/'page.lbl',*objects,out/'aliases.o'])
 payload=(out/'page.bin').read_bytes();image=wrap(payload,1,21,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(out/'page.seo').write_bytes(image);return image
