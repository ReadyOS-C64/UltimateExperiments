"""Private full-product lexical capsules. Executed inside copied project only."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify
from overlays import wrap
def build(out,base):
 out.mkdir(parents=True,exist_ok=True);report=json.load(open(base/'build/editor-report.json'));symbols=report['symbols'];digest=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest'];assert digest==report['resident_binding']['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 def run(args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
 budgets={}
 for tag,slot,id_,files in [
 ('edit',1,45,[('cache/lexical/gateway.s',[])]),
 ('tail',0,36,[('cache/lexical/resolver.s',[]),*[(f'cache/arena/{n}.s',['BCA_READONLY_OPEN=1'])for n in('core','open','page')]]),
 ('lex',0,37,[('cache/lexical/roles.s',[]),('cache/arena/core.s',[]),('cache/arena/page.s',[])]),
 ('ical',1,47,[('cache/lexical/worker.s',[]),('supermark/lexer.s',['SE_SM_CODE_ONLY=1']),('supermark/lexer.s',['SE_SM_STATE_ONLY=1'])]),
 ('ctrl',1,49,[('cache/lexical/linker.s',[]),*[(f'cache/arena/{n}.s',['BCA_READONLY_OPEN=1'])for n in('core','open','page')]])]:
  d=out/tag;d.mkdir(exist_ok=True);objects=[]
  for i,(source,defs)in enumerate(files):
   obj=d/(str(i)+'.o');run(['ca65','-g','-I',out,'-I',ROOT/'src',*[v for de in defs for v in('-D',de)],'-o',obj,ROOT/'src'/source]);objects.append(obj)
  run([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*objects]);run(['ca65','-o',d/'aliases.o',d/'aliases.s']);objects.append(d/'aliases.o')
  cfg='MEMORY {C:file=%%O,start=$%04X,size=$1000;P:file="",start=$8D5E,size=60;} SEGMENTS {'%(0xB000 if slot else 0xA000)
  cfg+=('LX_CODE:load=C,type=ro;SM_LEXER:load=C,type=ro;SM_STATE:load=P,type=bss;'if tag=='ical'else'CODE:load=C,type=ro;RODATA:load=C,type=ro,optional=yes;')+'}'
  (d/'image.cfg').write_text(cfg);run(['ld65','-C',d/'image.cfg','-o',out/(tag+'.bin'),'-Ln',out/(tag+'.lbl'),'-m',out/(tag+'.map'),*objects]);raw=(out/(tag+'.bin')).read_bytes();assert len(raw)<=4096
  (out/(tag+'.seo')).write_bytes(wrap(raw,slot,id_,api=(symbols['se_overlay_call'],symbols['se_overlay_frame']),binding_digest=bytes.fromhex(digest)));budgets[tag]=dict(slot=slot,id=id_,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 (out/'budget.json').write_text(json.dumps(dict(binding=digest,images=budgets),indent=2)+'\n')
if __name__=='__main__':build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
