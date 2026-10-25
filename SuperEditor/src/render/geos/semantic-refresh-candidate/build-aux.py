"""Existing C13 placement; immutable control bytes required, no newcatalogasset."""
from pathlib import Path
import json,sys,subprocess,zipfile,shutil
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify
from overlays import wrap

def build(out,base):
 out.mkdir(parents=True);src=out/'frozen-sources';src.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(src)
 shutil.copytree(D,src/'src/render/geos/semantic-refresh-candidate',dirs_exist_ok=True)
 s=json.loads((base/'build/editor-report.json').read_text())['symbols'];digest=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest']
 api='.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n';(out/'editor-api.inc').write_text(api);(out/'box').mkdir();(out/'box/editor-api.inc').write_text('\n'.join(n+'='+str(s[n])for n in ['tui_putc40','tui_color','tui_box_x','tui_box_y','tui_box_w','tui_box_h','box_rx','box_ry'])+'\n')
 def cmd(*a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True)
 result={}
 for name in ['control','helper']:
  d=out/name;d.mkdir();objects=[];sources=['src/overlays/aux.s','src/aux/layout-context.s','src/nav/invalidate.s','src/overlays/file-emergency.s','src/editor_file/dialog-draw.s','src/tui/box40.s']
  if name=='helper':
   entry=(src/sources[0]).read_text().replace('    cmp #A_LAYOUT_CONTEXT','    cmp #6\n    jeq se_gsr_refresh\n    cmp #A_LAYOUT_CONTEXT',1)+'\n.import se_gsr_refresh\n';(d/'entry.s').write_text(entry);sources[0]=str(d/'entry.s');sources+=['src/render/geos/semantic-refresh-candidate/rekey.s']
  for i,source in enumerate(sources):
   p=d/(str(i)+'.o');flags=['-D','SE_INDEX_IN_OVERLAY=1']if i==2else ['-D','EDITOR_OVERLAY=1']if i==5else ['-D','GSR_AUX=1']if i==6else[];includes=[out/'box']if i==5else[out];cmd('ca65','-g',*flags,*sum((['-I',p]for p in includes),[]),'-I',src/'src','-o',p,src/source);objects.append(p)
  cmd(sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*objects);cmd('ca65','-o',d/'aliases.o',d/'aliases.s');cmd('ld65','-C',src/'cfg/overlay-c.cfg','-o',d/'aux.bin','-Ln',d/'aux.lbl','-m',d/'aux.map',*objects,d/'aliases.o')
  raw=(d/'aux.bin').read_bytes();seo=wrap(raw,1,13,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(d/'aux.seo').write_bytes(seo)
  if name=='control':assert seo==(base/'build/overlays/aux.seo').read_bytes(),'AUXcontrol differs'
  result[name]=dict(bytes=len(raw),helper_bytes=len(raw)-2272)
 (out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
