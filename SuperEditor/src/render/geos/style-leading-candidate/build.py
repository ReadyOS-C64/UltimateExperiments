"""Private C6 admission delta; exact original must reassemble first."""
from pathlib import Path
import json,re,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify
from overlays import wrap,HEADER

def build(out,base):
 out.mkdir(parents=True,exist_ok=True);src=out/'frozen-sources';src.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(src)
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];d=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest']
 def run(*a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True)
 run(sys.executable,ROOT/'tools/overlay_api.py','--report',base/'build/editor-report.json','--output',out/'editor-api.inc','--all-public','--symbols','object_owner','object_banks','object_size_lo','object_size_mid','object_size_hi','tui_putc40','tui_color','tui_box_x','tui_box_y','tui_box_w','tui_box_h','box_rx','box_ry','text_ptr','screen_ptr')
 images={};budgets={}
 for variant in ['control','candidate']:
  dest=out/variant;dest.mkdir();objs=[];segments={}
  for n,source,flags in [('window',src/'src/overlays/hot-window.s',['-D','EDITOR_BINDINGS=1']),('certify',D/'certify.s'if variant=='candidate'else src/'src/render/geos/typing/certify.s',[]),('transfer',src/'src/render/geos/typing/transfer.s',[])]:
   obj=dest/(n+'.o');run('ca65','-g','-I',out,'-I',src/'src','-o',obj,*flags,source);objs.append(obj);t=subprocess.check_output(['od65','--dump-segments',str(obj)],text=True);segments[n]={n:int(v)for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',t,re.S)};assert not any(segments[n].get(k,0)for k in ['DATA','BSS','ZEROPAGE'])
  run(sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',dest/'aliases.s',*objs);run('ca65','-g','-o',dest/'aliases.o',dest/'aliases.s');run('ld65','-C',src/'cfg/overlay-c.cfg','-o',dest/'window.bin','-Ln',dest/'window.lbl','-m',dest/'window.map',*objs,dest/'aliases.o')
  payload=(dest/'window.bin').read_bytes();assert len(payload)<=4096
  images[variant]=wrap(payload,1,6,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(dest/'window.seo').write_bytes(images[variant]);budgets[variant]=dict(C6=len(payload),segments=segments)
  if variant=='control':assert images[variant]==(base/'build/overlays/window.seo').read_bytes(),'OriginalC6 differs from packaged freeze'
 (out/'budget.json').write_text(json.dumps(budgets,indent=2)+'\n');return images,budgets
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())[1])
