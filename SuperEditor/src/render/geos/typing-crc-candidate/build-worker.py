"""Private actual complete R30 link. No shared product outputs."""
from pathlib import Path
import subprocess,sys,json,re
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify
from overlays import wrap

def build(out,base):
 out.mkdir(parents=True,exist_ok=True);d=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest'];s=json.loads((base/'build/editor-report.json').read_text())['symbols'];(out/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2] for i in range(0,32,2))+'\n.endmacro\n');objects=[];segments={}
 def run(args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
 for name,source in [('worker','worker'),('guard','guard'),('patch','patch-buffered'),('status','status-normal'),('raster','status-raster'),('cache','transfer')]:
  p=out/(name+'.o');run(['ca65','-g','-I',out,'-I','src','-o',p,ROOT/'src/render/geos/typing-crc-candidate'/(source+'.s')]);objects.append(p);t=subprocess.check_output(['od65','--dump-segments',str(p)],text=True);segments[name]={n:int(v) for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',t,re.S)};assert all(segments[name].get(n,0)==0 for n in ['BSS','DATA','ZEROPAGE'])
 run([sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects]);run(['ca65','-g','-o',out/'aliases.o',out/'aliases.s']);run(['ld65','-C','cfg/overlay-r.cfg','-o',out/'worker.bin','-Ln',out/'worker.lbl','-m',out/'worker.map',*objects,out/'aliases.o']);payload=(out/'worker.bin').read_bytes();image=wrap(payload,0,30,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(out/'worker.seo').write_bytes(image);ls={p[2].lstrip('.'):int(p[1],16) for line in (out/'worker.lbl').read_text().splitlines() if (p:=line.split()) and p[0]=='al'};(out/'build.json').write_text(json.dumps(dict(payload_bytes=len(payload),segments=segments,new_BSS=0,new_ZP=0),indent=2)+'\n');return ls,payload,image
if __name__=='__main__':print(len(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())[1]))
