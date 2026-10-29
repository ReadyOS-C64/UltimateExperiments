"""Private coherent C15/C25/C31/R31 fit against an immutable released fixture."""
from pathlib import Path
import sys,json,zipfile,subprocess,shutil
ROOT=Path(__file__).resolve().parents[3]
def build(out,base):
 out.mkdir(parents=True,exist_ok=True);prod=out/'production';prod.mkdir(exist_ok=True)
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(prod)
 (prod/'tools').mkdir(exist_ok=True)
 for name in ['module_bindings.py','bindings.py','overlays.py']:shutil.copy2(ROOT/'tools'/name,prod/'tools'/name)
 (prod/'src/supermark/lexer.s').write_bytes(Path(__file__).with_name('lexer.s').read_bytes())
 for name in ['build-worker.py','build-stage.py']:shutil.copy2(ROOT/'src/render/geos/code-typing'/name,prod/'src/render/geos/code-typing'/name)
 stageguard=prod/'src/render/geos/code-typing/stage-guard.s';stageguard.write_text(stageguard.read_text().replace('STAMP=$5C80','STAMP=$5D00'))
 sys.path.insert(0,str(ROOT/'tools'));from bindings import verify
 d=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest'];(out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 def run(args):subprocess.run(list(map(str,args)),cwd=prod,check=True)
 result={}
 for name,cfg,modules in [('C15','lexical-c.cfg',[('entry','overlays/lexical.s',[]),('control','style/lexical-control.s',['-D','SE_STYLE_GRID=1']),('reader','style/reader-dispatch.s',[]),('lexer','supermark/lexer.s',['-D','SE_SM_CODE_ONLY=1'])]),('C25','geos-editor-semantic-lex.cfg',[('entry','render/geos/semantic-lex.s',[]),('lexer','supermark/lexer.s',[])])]:
  objects=[]
  for tag,path,defs in modules:
   obj=out/(name+'-'+tag+'.o');run(['ca65','-g','-I',out,'-I',prod/'src','-o',obj,*defs,prod/'src'/path]);objects.append(obj)
  aliases=out/(name+'-aliases.s');run([sys.executable,prod/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',aliases,*objects]);run(['ca65','-o',aliases.with_suffix('.o'),aliases]);run(['ld65','-C',prod/'cfg'/cfg,'-o',out/(name+'.bin'),'-Ln',out/(name+'.lbl'),*objects,aliases.with_suffix('.o')]);result[name]=len((out/(name+'.bin')).read_bytes())
 run([sys.executable,prod/'src/render/geos/code-typing/build-worker.py',out/'code-typing',base]);result['code-typing']=json.loads((out/'code-typing/worker-budget.json').read_text());(out/'fit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
if __name__=='__main__':build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
