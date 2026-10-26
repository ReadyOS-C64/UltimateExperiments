"""Private59 source-matched C45/R36/R37 batching/local-guard-fusion experiment."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools')]
from overlays import wrap
HERE=Path(__file__).resolve().parent

def build(out,base,batch=0,fused=False):
 out.mkdir(parents=True,exist_ok=True);source=out/'frozen-source';source.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for name in z.namelist():
   if name.startswith('src/')or name in('tools/module_bindings.py','tools/bindings.py'):z.extract(name,source)
 report=json.loads((base/'build/editor-report.json').read_text());symbols=report['symbols'];digest=report['resident_binding']['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 def command(*args):
  p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
  with(out/'build.log').open('a')as f:f.write(p.stdout+p.stderr)
  assert not p.returncode,(args,p.stdout,p.stderr)
 variants=[('edit',1,45,[(HERE/'gateway.s',(['LX_BATCH_STEPS='+str(batch)]if batch else[]))]),
  ('tail',0,36,[(source/'src/cache/lexical/resolver.s',[]),(source/'src/cache/arena/core.s',[]),(HERE/'arena-open.s',['BCA_READONLY_OPEN=1']),(HERE/'arena-page.s',[])]),
  ('lex',0,37,[(source/'src/cache/lexical/roles.s',[]),(source/'src/cache/arena/core.s',[]),(HERE/'arena-page.s',[])])]
 images={};labels={};budgets={}
 for tag,slot,id_,files in variants:
  d=out/tag;d.mkdir();objects=[]
  for i,(path,defs)in enumerate(files):
   if fused and path.name in('arena-open.s','arena-page.s'):defs=defs+['BCA_OUTER_VALIDATED=1']
   obj=d/(str(i)+'.o');command('ca65','-g','-I',out,'-I',source/'src',*[v for de in defs for v in('-D',de)],'-o',obj,path);objects.append(obj)
  command(sys.executable,source/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*objects)
  command('ca65','-g','-o',d/'aliases.o',d/'aliases.s')
  (d/'image.cfg').write_text('MEMORY {C:file=%%O,start=$%04X,size=$1000;} SEGMENTS {CODE:load=C,type=ro;RODATA:load=C,type=ro,optional=yes;}'%(0xb000 if slot else 0xa000))
  command('ld65','-C',d/'image.cfg','-o',out/(tag+'.bin'),'-Ln',out/(tag+'.lbl'),'-m',out/(tag+'.map'),*objects,d/'aliases.o')
  raw=(out/(tag+'.bin')).read_bytes();assert len(raw)<=4096
  image=wrap(raw,slot,id_,api=(symbols['se_overlay_call'],symbols['se_overlay_frame']),binding_digest=bytes.fromhex(digest))
  if not batch and not fused:assert image==(base/f'build/overlays/{tag}.seo').read_bytes(),tag+' default must be byte-identical'
  (out/(tag+'.seo')).write_bytes(image);images[tag]=image
  labels[tag]={name:int(a,16)for a,name in re.findall(r'al ([0-9A-Fa-f]+) \.(\w+)',(out/(tag+'.lbl')).read_text())}
  budgets[tag]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),slot=slot,id=id_)
 (out/'budget.json').write_text(json.dumps(dict(batch=batch,local_guard_fusion=fused,images=budgets),indent=2)+'\n')
 return images,labels,budgets

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--batch',type=int,default=0);p.add_argument('--fused',action='store_true');a=p.parse_args();print(build(a.out.resolve(),a.base.resolve(),a.batch,a.fused)[2])
