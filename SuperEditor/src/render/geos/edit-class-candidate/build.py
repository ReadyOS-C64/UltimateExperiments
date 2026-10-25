"""Build private R28/C21 replacements from immutable production dependencies."""
from pathlib import Path
import sys,subprocess,json,re,zipfile,shutil
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify
from overlays import wrap

def build(out,base):
 out.mkdir(parents=True,exist_ok=True);prod=out/'production';prod.mkdir(exist_ok=True)
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for n in z.namelist():
   if n.startswith(('src/','assets/','cfg/'))and not n.endswith('/'):
    p=prod/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
 dst=prod/'src/render/geos/edit-class-candidate';dst.mkdir(exist_ok=True)
 for p in (ROOT/'src/render/geos/edit-class-candidate').glob('*'):
  if p.is_file():shutil.copy2(p,dst/p.name)
 d=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest'];s=json.loads((base/'build/editor-report.json').read_text())['symbols'];(out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 def run(args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
 result={}
 for tag,slot,ident,source,cfg,flags in [('page',1,21,'page.s','cfg/geos-editor-page.cfg',[]),('delta',0,28,'edit-cache.s','cfg/overlay-r.cfg',['-D','SE_GP_CACHE_WARM_ONLY=1'])]:
  objects=[];segs={}
  for name,path,defs in [(tag,dst/source,[]),('cache-'+tag,prod/'src/render/geos/cache.s',flags)]:
   p=out/(name+'.o');run(['ca65','-g','-I',out,'-I',prod/'src','-o',p,*defs,path]);objects.append(p);t=subprocess.check_output(['od65','--dump-segments',str(p)],text=True);segs[name]={n:int(v)for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',t,re.S)};assert all(segs[name].get(n,0)==0 for n in ['BSS','DATA','ZEROPAGE'])
  run([sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(tag+'-aliases.s'),*objects]);run(['ca65','-g','-o',out/(tag+'-aliases.o'),out/(tag+'-aliases.s')]);run(['ld65','-C',prod/cfg,'-o',out/(tag+'.bin'),'-Ln',out/(tag+'.lbl'),'-m',out/(tag+'.map'),*objects,out/(tag+'-aliases.o')]);payload=(out/(tag+'.bin')).read_bytes();image=wrap(payload,slot,ident,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(out/(tag+'.seo')).write_bytes(image);result[tag]=dict(bytes=len(payload),segments=segs)
 (out/'build.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
