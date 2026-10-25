"""SP2 literal-paragraph authority prototype; no long-row consumer yet."""
from pathlib import Path
import sys,json,subprocess,hashlib,shutil
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'));from overlays import wrap
BASE=ROOT/'build/grid-prose-authority/20261025T190208381544Z/fixture'
LEAF=ROOT/'build/grid-prose-authority/20261025T190208381544Z/leaf'
def build(out,base=BASE):
 out.mkdir(parents=True,exist_ok=True);project=out/'project';shutil.copytree(LEAF/'project',project);s=json.load(open(base/'build/editor-report.json'))['symbols'];digest=json.load(open(base/'build/editor-report.json'))['resident_binding']['digest'];header='.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n'
 for n in['editor-api.inc','style-api.inc']:(out/n).write_text(header)
 # Previous paragraph is finalized by the next visible EVENT or FINISH;
 # no per-prefix-line C14 callback or additional C14 bytes.
 plan=project/'src/style/plan.s'
 reader=project/'src/style/reader-dispatch.s'
 entry=project/'src/overlays/source-view.s';text=entry.read_text();text=text.replace('.import se_sc_begin,se_sc_event,se_sc_finish','.import se_sc_begin,se_sc_event,se_sc_finish,se_sc_close,se_sc_scan');text=text.replace('read:jmp se_fs_read','read:jsr se_fs_read\n bcs :+\n jmp se_sc_scan\n: rts');entry.write_text(text);products={};budget={}
 for name,items,cfg,slot,ident in [('styler',[(project/'src/style'/n,defs)for n,defs in [('entry.s',[]),('plan.s',['SE_STYLE_LEXICAL=1','SE_STYLE_GRID=1']),('editor-control.s',[]),('reader-dispatch.s',[])]]+[(project/'src/supermark'/n,['SE_SM_CODE_ONLY=1'])for n in ['block.s','inline.s']],(LEAF/'styler.cfg').read_text(),1,14),('viewsource',[(entry,[]),(project/'src/fold/source-context.s',[]),(project/'src/fold/source-read.s',[]),(D/'producer2.s',[])],(LEAF/'viewsource.cfg').read_text(),0,14)]:
  objs=[]
  for j,(path,defs)in enumerate(items):
   o=out/(name+str(j)+'.o');cmd=['ca65','-g','-I',out,'-I',D,'-I',project/'src']
   for flag in defs:cmd+=['-D',flag]
   subprocess.run([*cmd,'-o',o,path],check=True);objs.append(o)
  subprocess.run([sys.executable,ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',out/(name+'-aliases.s'),*objs],check=True);subprocess.run(['ca65','-o',out/(name+'-aliases.o'),out/(name+'-aliases.s')],check=True);(out/(name+'.cfg')).write_text(cfg);subprocess.run(['ld65','-C',out/(name+'.cfg'),'-o',out/(name+'.bin'),'-Ln',out/(name+'.lbl'),'-m',out/(name+'.map'),*objs,out/(name+'-aliases.o')],check=True);raw=(out/(name+'.bin')).read_bytes();seo=wrap(raw,slot,ident,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/(name+'.seo')).write_bytes(seo);products[name]=seo;budget[name]=dict(payload=len(raw),sha256=hashlib.sha256(seo).hexdigest())
 (out/'budget.json').write_text(json.dumps(budget,indent=2)+'\n');return products,budget
if __name__=='__main__':print(build(Path(sys.argv[1]),Path(sys.argv[2])if len(sys.argv)>2 else BASE)[1])
