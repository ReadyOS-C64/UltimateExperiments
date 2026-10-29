"""Private twoleaf SPLICE prototype, exclusively frozen source/resident imports."""
from pathlib import Path
import sys,subprocess,json,zipfile,shutil
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'tools')]
from overlays import wrap

def build(out,base):
 out.mkdir(parents=True);source=out/'source';source.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(source)
 shutil.copytree(ROOT/'src/cache/splice-probe',source/'src/cache/splice-probe')
 r=json.loads((base/'build/editor-report.json').read_text());b=r['resident_binding']['digest'];s=r['symbols']
 (out/'editor-api.inc').write_text('.macro OVL_BINDING\n.byte '+','.join('$'+b[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 images={};budgets={}
 for tag,slot,ident,files in [('splice',1,40,[('cache/splice-probe/worker.s',[]),('supermark/block.s',['SE_SM_CODE_ONLY=1']),('supermark/block.s',['SE_SM_STATE_ONLY=1'])]),('spliceio',0,34,[('cache/splice-probe/transport.s',[])]+[(f'cache/arena/{n}.s',['BCA_READONLY_OPEN=1'])for n in('core','open','page')])]:
  d=out/tag;d.mkdir();oo=[]
  for i,(name,defs)in enumerate(files):
   obj=d/(str(i)+'.o');subprocess.run(['ca65','-g','-I',str(out),'-I',str(source/'src'),*[v for x in defs for v in('-D',x)],'-o',str(obj),str(source/'src'/name)],check=True);oo.append(obj)
  subprocess.run([sys.executable,str(ROOT/'tools/module_bindings.py'),'--report',str(base/'build/editor-report.json'),'--output',str(d/'aliases.s'),*map(str,oo)],check=True);subprocess.run(['ca65','-o',str(d/'aliases.o'),str(d/'aliases.s')],check=True);oo.append(d/'aliases.o')
  extra='SM_BLOCK:load=IMAGE,type=ro; SM_STATE:load=P,type=bss;'if slot else ''
  cfg=f'MEMORY {{ IMAGE:file=%O,start=${0xB000 if slot else 0xA000:04X},size=$1000; P:file="",start=$8D5E,size=79; }} SEGMENTS {{ CODE:load=IMAGE,type=ro; RODATA:load=IMAGE,type=ro; {extra} }}';(d/'image.cfg').write_text(cfg)
  subprocess.run(['ld65','-C',str(d/'image.cfg'),'-o',str(d/'image.bin'),'-Ln',str(d/'image.lbl'),'-m',str(d/'image.map'),*map(str,oo)],check=True);raw=(d/'image.bin').read_bytes();assert len(raw)<=4096
  image=wrap(raw,slot,ident,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(b));(d/'image.seo').write_bytes(image);images[tag]=image;budgets[tag]=dict(bytes=len(raw),free=4096-len(raw),slot=slot,id=ident)
 (out/'budget.json').write_text(json.dumps(dict(images=budgets,new_BSS=0,new_ZP=0,borrowed_parser79='BC_FRAME+94, existingowner4union'),indent=2)+'\n');return images
if __name__=='__main__':build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
