from pathlib import Path
import binascii,json,re,sys,subprocess,zipfile,shutil
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify
from overlays import wrap

def build(out,base):
 out.mkdir(parents=True);src=out/'frozen-sources';src.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(src)
 shutil.copytree(D,src/'src/render/geos/semantic-refresh-candidate',dirs_exist_ok=True)
 s=json.loads((base/'build/editor-report.json').read_text())['symbols'];digest=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 def cmd(*a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True)
 result={}
 for name in ['control','helper']:
  d=out/name;d.mkdir();objects=[];sources=['src/overlays/source-view.s','src/fold/source-context.s','src/fold/source-read.s']
  if name=='helper':
   entry=(src/sources[0]).read_text().replace('    cmp #2','    cmp #6\n    beq refresh\n    cmp #2',1)+'\n.import se_gsr_refresh\nrefresh:jmp se_gsr_refresh\n';(d/'entry.s').write_text(entry);sources[0]=str(d/'entry.s');sources+=['src/render/geos/semantic-refresh-candidate/rekey.s']
  for i,source in enumerate(sources):
   p=d/(str(i)+'.o');cmd('ca65','-g','-I',out,'-I',src/'src','-o',p,src/source);objects.append(p)
  cmd(sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*objects);cmd('ca65','-o',d/'aliases.o',d/'aliases.s');cmd('ld65','-C',src/'cfg/source-r.cfg','-o',d/'viewsource.bin','-Ln',d/'viewsource.lbl','-m',d/'viewsource.map',*objects,d/'aliases.o')
  raw=(d/'viewsource.bin').read_bytes();seo=wrap(raw,0,14,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(d/'viewsource.seo').write_bytes(seo)
  if name=='control':assert seo==(base/'build/overlays/viewsource.seo').read_bytes(),'R14control differs'
  result[name]=dict(bytes=len(raw),helper_bytes=len(raw)-2331)
 (out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
