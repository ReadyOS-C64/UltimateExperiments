"""Actual C6+readonlycertifier private build; production source is untouched."""
from pathlib import Path
import subprocess,sys,json,zipfile,re,shutil
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from overlays import wrap
from bindings import verify

def build(out,base):
 out.mkdir(parents=True,exist_ok=True);prod=out/'production';prod.mkdir(exist_ok=True)
 with zipfile.ZipFile(base/'product-sources.zip') as z:
  for n in z.namelist():
   if n.startswith(('src/','assets/')) and not n.endswith('/'):
    q=prod/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(z.read(n))
 dest=prod/'src/render/geos/style-typing-candidate';dest.mkdir(parents=True,exist_ok=True)
 shutil.copy2(ROOT/'src/render/geos/style-typing-candidate/certify-styles.s',dest/'certify.s')
 shutil.copy2(prod/'src/render/geos/typing/transfer.s',dest/'transfer.s')
 def run(args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
 run([sys.executable,'tools/overlay_api.py','--report',base/'build/editor-report.json','--output',out/'editor-api.inc','--all-public','--symbols','object_owner','object_banks','object_size_lo','object_size_mid','object_size_hi','tui_putc40','tui_color','tui_box_x','tui_box_y','tui_box_w','tui_box_h','box_rx','box_ry','text_ptr','screen_ptr'])
 src=(prod/'src/overlays/hot-window.s').read_text();assert src.count('    jsr se_gtt_certify')==1;(out/'hot-window-candidate.s').write_text(src);objects=[];segments={}
 for name,source,flags in [('window',out/'hot-window-candidate.s',['-D','EDITOR_BINDINGS=1']),('certify',dest/'certify.s',[]),('transfer',dest/'transfer.s',[])]:
  p=out/(name+'.o');run(['ca65','-g','-I',out,'-I',prod/'src','-o',p,*flags,source]);objects.append(p);t=subprocess.check_output(['od65','--dump-segments',str(p)],text=True);segments[name]={n:int(v) for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',t,re.S)};assert all(segments[name].get(n,0)==0 for n in ['BSS','DATA','ZEROPAGE'])
 run([sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects]);run(['ca65','-g','-o',out/'aliases.o',out/'aliases.s']);run(['ld65','-C','cfg/overlay-c.cfg','-o',out/'window.bin','-Ln',out/'window.lbl','-m',out/'window.map',*objects,out/'aliases.o']);payload=(out/'window.bin').read_bytes();s=json.loads((base/'build/editor-report.json').read_text())['symbols'];d=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest'];image=wrap(payload,1,6,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(out/'window.seo').write_bytes(image);(out/'build.json').write_text(json.dumps(dict(payload_bytes=len(payload),segments=segments,new_BSS=0,new_ZP=0),indent=2)+'\n');return payload,image
if __name__=='__main__':
 p,i=build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve());print('C6',len(p))
