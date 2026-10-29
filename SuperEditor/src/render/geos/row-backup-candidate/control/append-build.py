"""Only private R28 delta; byte-identical frozen control required."""
from pathlib import Path
import json,re,sys,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[5];D=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify
from overlays import wrap

def build(out,base):
 out.mkdir(parents=True,exist_ok=True);src=out/'frozen-sources';src.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(src)
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols'];digest=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 def run(*a):subprocess.run(list(map(str,a)),cwd=ROOT,check=True)
 images={};budgets={}
 for variant in ['control','candidate']:
  d=out/variant;d.mkdir();objects=[];segments={}
  for name,source in [('edit-cache',D/'append-edit-cache.s'if variant=='candidate'else src/'src/render/geos/edit-cache.s'),('cache-warm',src/'src/render/geos/cache-warm.s')]:
   obj=d/(name+'.o');run('ca65','-g','-I',out,'-I',src/'src','-o',obj,source);objects.append(obj)
   t=subprocess.check_output(['od65','--dump-segments',str(obj)],text=True);segments[name]={n:int(v)for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',t,re.S)};assert not any(segments[name].get(k,0)for k in ['BSS','DATA','ZEROPAGE'])
  run(sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*objects);run('ca65','-g','-o',d/'aliases.o',d/'aliases.s');run('ld65','-C',src/'cfg/overlay-r.cfg','-o',d/'geosdelta.bin','-Ln',d/'geosdelta.lbl','-m',d/'geosdelta.map',*objects,d/'aliases.o')
  raw=(d/'geosdelta.bin').read_bytes();assert len(raw)<=4096
  images[variant]=wrap(raw,0,28,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(d/'geosdelta.seo').write_bytes(images[variant]);budgets[variant]=dict(R28=len(raw),segments=segments)
  if variant=='control':assert images[variant]==(base/'build/overlays/geosdelta.seo').read_bytes(),'ControlR28 differs from actualfreeze'
 (out/'budget.json').write_text(json.dumps(budgets,indent=2)+'\n');return images,budgets
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())[1])
