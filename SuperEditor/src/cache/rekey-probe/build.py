"""Private C38 REKEY bridge; frozen resident/helpers, no shared build writes."""
from pathlib import Path
import sys,json,re,subprocess,zipfile,shutil
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tools'))
from overlays import wrap

def build(out,base):
 out.mkdir(parents=True);src=out/'source';src.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(src)
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];binding=report['resident_binding']['digest'];(out/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+binding[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 # Only this new namespace supplies candidate code; existing core/open are frozen.
 shutil.copytree(ROOT/'src/cache/rekey-probe',src/'src/cache/rekey-probe');objects=[];sizes={}
 for n,p in [('rekey',src/'src/cache/rekey-probe/rekey.s'),('core',src/'src/cache/arena/core.s'),('open',src/'src/cache/arena/open.s')]:
  obj=out/(n+'.o');subprocess.run(['ca65','-g','-D','BCA_READONLY_OPEN=1','-I',str(out),'-I',str(src/'src'),'-o',str(obj),str(p)],check=True);objects.append(obj);sizes[n]={k:int(v)for k,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',subprocess.check_output(['od65','--dump-segments',str(obj)],text=True),re.S)}
 subprocess.run([sys.executable,str(ROOT/'tools/module_bindings.py'),'--report',str(base/'build/editor-report.json'),'--output',str(out/'aliases.s'),*map(str,objects)],check=True);subprocess.run(['ca65','-o',str(out/'aliases.o'),str(out/'aliases.s')],check=True);objects.append(out/'aliases.o')
 (out/'image.cfg').write_text('MEMORY { IMAGE:file=%O,start=$B000,size=$1000; } SEGMENTS { CODE:load=IMAGE,type=ro; RODATA:load=IMAGE,type=ro; }')
 subprocess.run(['ld65','-C',str(out/'image.cfg'),'-o',str(out/'rekey.bin'),'-Ln',str(out/'rekey.lbl'),'-m',str(out/'rekey.map'),*map(str,objects)],check=True)
 raw=(out/'rekey.bin').read_bytes();assert len(raw)<=4096;(out/'rekey.seo').write_bytes(wrap(raw,1,38,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(binding)));d=dict(payload=len(raw),free=4096-len(raw),segments=sizes,new_BSS=0,new_ZP=0);(out/'budget.json').write_text(json.dumps(d,indent=2)+'\n');return d
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
