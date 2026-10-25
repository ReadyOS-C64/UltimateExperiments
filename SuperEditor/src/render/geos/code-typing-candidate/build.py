"""Private exact-role/native8 capsule and measured missing-transaction budget."""
from pathlib import Path
import sys,json,subprocess,re
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from overlays import wrap
from bindings import verify

def build(out,base):
 out.mkdir(parents=True,exist_ok=True);s=json.loads((base/'build/editor-report.json').read_text())['symbols'];d=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest'];(out/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+d[i:i+2]for i in range(0,32,2))+'\n.endmacro\n');objects=[];segments={}
 def run(args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
 for name,flags in [('entry',[]),('guard',[]),('lex-paint',[]),('lexer',['-D','SE_SM_CODE_ONLY=1']),('lexer-state',['-D','SE_SM_STATE_ONLY=1'])]:
  p=out/(name+'.o');run(['ca65','-g','-I',out,'-I','src','-o',p,*flags,ROOT/'src/render/geos/code-typing-candidate'/('lexer.s'if name=='lexer-state'else name+'.s')]);objects.append(p);text=subprocess.check_output(['od65','--dump-segments',str(p)],text=True);segments[name]={n:int(v)for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',text,re.S)};assert not any(segments[name].get(n,0)for n in ['BSS','DATA','ZEROPAGE'])
 run([sys.executable,'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/'aliases.s',*objects]);run(['ca65','-o',out/'aliases.o',out/'aliases.s']);run(['ld65','-C','src/render/geos/code-typing-candidate/capsule.cfg','-o',out/'capsule.bin','-Ln',out/'capsule.lbl','-m',out/'capsule.map',*objects,out/'aliases.o']);payload=(out/'capsule.bin').read_bytes();image=wrap(payload,0,31,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(d));(out/'capsule.seo').write_bytes(image);result=dict(payload_bytes=len(payload),segments=segments,new_BSS=0,new_ZP=0,missing='typed transport, trusted code-language/row admission, real canonical packet update, FEbase/cache/prefix transaction, status/publication',with_released_typed_transport=len(payload)+317,with_transport_and_released_status=len(payload)+317+228);(out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');return payload,image,result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())[2])
