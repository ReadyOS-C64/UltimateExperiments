from pathlib import Path
import sys,json,subprocess,re,importlib.util
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from overlays import wrap
from bindings import verify
def build(out,base):
 out.mkdir(parents=True,exist_ok=True)
 spec=importlib.util.spec_from_file_location('gct_stage',Path(__file__).with_name('build-stage.py'));st=importlib.util.module_from_spec(spec);spec.loader.exec_module(st);stage=st.build(out,base)
 d=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest'];s=json.loads((base/'build/editor-report.json').read_text())['symbols'];(out/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2]for i in range(0,32,2))+'\n.endmacro\n');objects=[];segments={}
 def run(args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
 for name,source in [('worker','code-typing-candidate/worker'),('guard','code-typing-candidate/guard'),('admit','code-typing-candidate/admit'),('stage-guard','code-typing-candidate/stage-guard'),('transport','code-typing-candidate/transport'),('status-normal','typing/status-normal'),('status-raster','typing/status-raster')]:
  p=out/(name+'.o');run(['ca65','-g','-I',out,'-I','src','-o',p,ROOT/'src/render/geos'/(source+'.s')]);objects.append(p);dump=subprocess.check_output(['od65','--dump-segments',str(p)],text=True);segments[name]={n:int(v)for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',dump,re.S)}
 run([sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'worker-aliases.s',*objects]);run(['ca65','-o',out/'worker-aliases.o',out/'worker-aliases.s']);run(['ld65','-C','src/render/geos/code-typing-candidate/capsule.cfg','-o',out/'worker.bin','-Ln',out/'worker.lbl','-m',out/'worker.map',*objects,out/'worker-aliases.o'])
 p=(out/'worker.bin').read_bytes();image=wrap(p,0,31,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(out/'worker.seo').write_bytes(image);result=dict(payload_bytes=len(p),segments=segments,stage=stage,newBSS=0,newZP=0);(out/'worker-budget.json').write_text(json.dumps(result,indent=2)+'\n');return p,image,result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())[2])
