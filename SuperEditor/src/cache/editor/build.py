"""Build sealed cache jobs against the actual resident ABI, with no new RAM."""
from pathlib import Path
import json,re,subprocess,sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify
from overlays import wrap

def build(out,base):
 out.mkdir(parents=True,exist_ok=True)
 report=json.loads((base/'build/editor-report.json').read_text())
 symbols=report['symbols'];digest=verify(base/'build/editor.prg',base/'build/editor.lbl')['digest']
 assert digest==report['resident_binding']['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 seam=['se_bc_arena','se_bc_ticket','se_bc_incarnation','se_bc_flags','se_bc_head','se_bc_tail','se_bc_count','se_bc_ring']
 (out/'state.s').write_text('\n'.join(f'.export {n}: absolute\n{n}=${symbols[n]:04X}'for n in seam)+'\n')
 def run(args):subprocess.run(list(map(str,args)),cwd=ROOT,check=True)
 budgets={}
 for tag,slot,ident,files in [
  ('fold',0,33,[(f'cache/arena/{n}.s',['BCA_WRITER_PROFILE=1'])for n in ('entry','core','open','control','writer')]),
  ('sema',1,34,[('cache/editor/entry.s',[]),('cache/semantic/worker.s',['BSC_SELECTOR_OWNS_OWNER=1','BSC_AUTO_OWNS_CANCEL=1']),('cache/semantic/state.s',[]),('supermark/block.s',['SE_SM_CODE_ONLY=1']),('supermark/inline.s',['SE_SM_CODE_ONLY=1'])]),
  ('inln',1,35,[(f'cache/query/{n}.s',['BCQ_EDITOR_ACTIVE=1','BCQ_CLASSIFY=1','BCQ_SELECTOR_OWNS_OWNER=1','BCQ_PAGE_REUSE=1','BCQ_FORWARD_SEED=1'])for n in ('classify-entry','query','source','records')]+[(f'cache/arena/{n}.s',['BCA_READONLY_OPEN=1'])for n in ('core','open','page')]),
  ('page',1,37,[(f'cache/query/{n}.s',['BCQ_EDITOR_ACTIVE=1','BCQ_CLASSIFY=1','BCQ_SELECTOR_OWNS_OWNER=1','BCQ_PAGE_REUSE=1','BCQ_FORWARD_SEED=1','BCQ_FORWARD_QUERY=1'])for n in ('fast-entry','query','source','records')]+[(f'cache/arena/{n}.s',['BCA_READONLY_OPEN=1'])for n in ('core','page')])]:
  folder=out/tag;folder.mkdir(exist_ok=True);objects=[];segments={}
  for i,(name,defs)in enumerate(files+[('STATE',[])]):
   path=out/'state.s'if name=='STATE'else ROOT/'src'/name
   obj=folder/(str(i)+'.o')
   run(['ca65','-g','-I',out,'-I',ROOT/'src',*[v for d in defs for v in ('-D',d)],'-o',obj,path])
   sizes=subprocess.check_output(['od65','--dump-segments',str(obj)],text=True)
   segments[name]={n:int(v)for n,v in re.findall(r'Name:\s+"([^"]+)".*?Size:\s+(\d+)',sizes,re.S)}
   assert not any(segments[name].get(n,0)for n in ('BSS','ZEROPAGE'))
   objects.append(obj)
  run([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',folder/'aliases.s',*objects])
  run(['ca65','-o',folder/'aliases.o',folder/'aliases.s']);objects.append(folder/'aliases.o')
  cfg='MEMORY { IMAGE:file=%%O,start=$%04X,size=$1000; '%(0xB000 if slot else 0xA000)
  if tag=='sema':
   cfg+='P:file="",start=$8D5E,size=79; } SEGMENTS { BSC_CODE:load=IMAGE,type=ro; SM_BLOCK:load=IMAGE,type=ro; SM_INLINE:load=IMAGE,type=ro; BSC_PARSER:load=P,type=bss; }'
  else:cfg+='} SEGMENTS { CODE:load=IMAGE,type=ro; RODATA:load=IMAGE,type=ro; }'
  (folder/'image.cfg').write_text(cfg)
  run(['ld65','-C',folder/'image.cfg','-o',out/(tag+'.bin'),'-Ln',out/(tag+'.lbl'),'-m',out/(tag+'.map'),*objects])
  raw=(out/(tag+'.bin')).read_bytes();assert len(raw)<=4096
  (out/(tag+'.seo')).write_bytes(wrap(raw,slot,ident,api=(symbols['se_overlay_call'],symbols['se_overlay_frame']),binding_digest=bytes.fromhex(digest)))
  budgets[tag]=dict(bytes=len(raw),free=4096-len(raw),segments=segments)
 result=dict(binding=digest,resident_sha256=report['sha256'],new_BSS=0,new_ZP=0,images=budgets)
 (out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':print(json.dumps(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()),indent=2))
