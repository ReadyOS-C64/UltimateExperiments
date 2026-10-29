from pathlib import Path
import sys,json,subprocess,re,hashlib
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify
from overlays import wrap

def build(out,base):
 out.mkdir(parents=True,exist_ok=True);s=json.loads((base/'build/editor-report.json').read_text())['symbols'];seal=verify(base/'build/editor.prg',base/'build/editor.lbl');digest=seal['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 objs=[];segments={}
 for name,path in [('caret',D/'caret.s'),('status',ROOT/'src/render/geos/typing/status-normal.s')]:
  o=out/(name+'.o');subprocess.run(['ca65','-g','-I',out,'-I',D,'-I',ROOT/'src','-o',o,path],check=True);objs.append(o)
  text=subprocess.check_output(['od65','--dump-segments',o],text=True);segments[name]={n:int(v)for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',text,re.S)}
  assert not any(segments[name].get(n,0)for n in('BSS','ZEROPAGE','DATA'))
 subprocess.run([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objs],check=True)
 a=out/'aliases.o';subprocess.run(['ca65','-o',a,out/'aliases.s'],check=True);objs.append(a)
 cfg=out/'leaf.cfg';cfg.write_text('MEMORY {IMAGE:file=%O,start=$B000,size=$1000,type=ro;} SEGMENTS {CODE:load=IMAGE,type=ro;RODATA:load=IMAGE,type=ro;}')
 subprocess.run(['ld65','-C',cfg,'-o',out/'candidate.bin','-Ln',out/'candidate.lbl','-m',out/'candidate.map',*objs],check=True)
 raw=(out/'candidate.bin').read_bytes();seo=wrap(raw,1,33,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/'gridcaret.seo').write_bytes(seo)
 symbols={p[2].lstrip('.'):int(p[1],16)for l in(out/'candidate.lbl').read_text().splitlines()if len(p:=l.split())==3 and p[0]=='al'}
 result=dict(payload=len(raw),segments=segments,newBSS=0,newZP=0,sha256=hashlib.sha256(seo).hexdigest(),resident=seal['resident_sha256']);(out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');return seo,symbols,result
if __name__=='__main__':print(build(Path(sys.argv[1]),Path(sys.argv[2]))[2])
