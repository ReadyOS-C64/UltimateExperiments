"""Sealed C41/R34 production profiles; content-aware no-op publication."""
from pathlib import Path
import argparse,binascii,hashlib,json,os,re,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from overlays import wrap
from bindings import verify

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write_changed(p,data):
 if p.exists()and p.read_bytes()==data:return
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp');tmp.write_bytes(data);os.replace(tmp,p)
def inputs(base):
 paths={p for folder in ('src/cache/edit-rebase-integration','src/cache/arena','src/supermark')for p in(ROOT/folder).glob('*')if p.is_file()and p.suffix in('.s','.inc','.py')}
 paths.update(ROOT/'tools'/n for n in('module_bindings.py','bindings.py','overlays.py'))
 pending=list(paths)
 while pending:
  p=pending.pop()
  for n in re.findall(r'^\s*\.include\s+"([^"]+)"',p.read_text(),re.M|re.I):
   if n=='editor-api.inc':continue
   q=next((x.resolve()for x in(p.parent/n,ROOT/'src'/n)if x.is_file()),None)
   if q is None:raise ValueError(('unresolved include',p,n))
   if q not in paths:paths.add(q);pending.append(q)
 return dict(sources={str(p.relative_to(ROOT)):sha(p)for p in sorted(paths)},resident={n:sha(base/'build'/n)for n in('editor.prg','editor.lbl','editor-report.json')},toolchain={n:subprocess.check_output([n,'-V'],stderr=subprocess.STDOUT,text=True).strip()for n in('ca65','ld65','od65')})
def build(out,base):
 out.mkdir(parents=True,exist_ok=True);report=json.loads((base/'build/editor-report.json').read_text());seal=verify(base/'build/editor.prg',base/'build/editor.lbl');assert seal['digest']==report['resident_binding']['digest'] and seal['resident_sha256']==report['sha256']
 before=inputs(base);manifest=out/'content.json';artifacts=[tag+suffix for tag in('parse','xform')for suffix in('.seo','.bin','.lbl','.map')]+['budget.json']
 def valid_outputs():
  budget=json.loads((out/'budget.json').read_text());assert budget['binding']==seal['digest'] and budget['resident_sha256']==report['sha256']
  for tag,slot,ident in (('parse',1,41),('xform',0,34)):
   raw=(out/(tag+'.bin')).read_bytes();image=(out/(tag+'.seo')).read_bytes();item=budget['images'][tag]
   assert 16<len(raw)<=4096 and raw[:16]==bytes.fromhex(seal['digest'])
   assert image[:5]==b'SEO2\x02' and image[5:8]==bytes((slot,ident,0)) and image[36:]==raw and image[20:36]==raw[:16]
   assert image[16:20]==report['symbols']['se_overlay_call'].to_bytes(2,'little')+report['symbols']['se_overlay_frame'].to_bytes(2,'little')
   assert int.from_bytes(image[8:10],'little')==len(raw) and int.from_bytes(image[10:12],'little')==16
   assert binascii.crc_hqx(raw,65535)==int.from_bytes(image[12:14],'little') and binascii.crc_hqx(image[:14]+image[16:36],65535)==int.from_bytes(image[14:16],'little')
   assert item['bytes']==len(raw) and item['sha256']==hashlib.sha256(raw).hexdigest() and (item['slot'],item['id'])==(slot,ident)
 if manifest.exists():
  try:
   old=json.loads(manifest.read_text());assert old['schema']==1 and isinstance(old['artifacts'],dict) and isinstance(old['inputs'],dict)
   valid_outputs()
   if old['inputs']==before and all((out/n).exists()and sha(out/n)==old['artifacts'].get(n)for n in artifacts):return dict(rebuilt=False,binding=seal['digest'])
  except (ValueError,KeyError,TypeError,OSError,AssertionError):
   # Retain exact bad metadata for diagnosis; a failed compilation below leaves
   # both the previous published artifacts and original manifest untouched.
   data=manifest.read_bytes();write_changed(out/('rejected-content.'+hashlib.sha256(data).hexdigest()+'.json'),data)
 binding=seal['digest'];s=report['symbols'];budgets={}
 with tempfile.TemporaryDirectory(prefix='rebase-',dir=out)as tmp:
  temp=Path(tmp);(temp/'editor-api.inc').write_text('.global se_overlay_call,se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+binding[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
  for tag,slot,ident,files in [('parse',1,41,[('cache/edit-rebase-integration/worker.s',[]),('supermark/block.s',['SE_SM_CODE_ONLY=1']),('supermark/block.s',['SE_SM_STATE_ONLY=1'])]),('xform',0,34,[('cache/edit-rebase-integration/transport.s',[])]+[(f'cache/arena/{n}.s',['BCA_READONLY_OPEN=1'])for n in('core','open','page')])]:
   d=temp/tag;d.mkdir();objects=[]
   for i,(name,defs)in enumerate(files):
    obj=d/(str(i)+'.o');subprocess.run(['ca65','-g','-I',str(temp),'-I',str(ROOT/'src'),*[v for x in defs for v in('-D',x)],'-o',str(obj),str(ROOT/'src'/name)],check=True);objects.append(obj)
   subprocess.run([sys.executable,str(ROOT/'tools/module_bindings.py'),'--report',str(base/'build/editor-report.json'),'--output',str(d/'aliases.s'),*map(str,objects)],check=True)
   subprocess.run(['ca65','-o',str(d/'aliases.o'),str(d/'aliases.s')],check=True);objects.append(d/'aliases.o')
   extra='SM_BLOCK:load=IMAGE,type=ro; SM_STATE:load=P,type=bss;'if slot else ''
   (d/'image.cfg').write_text(f'MEMORY {{ IMAGE:file=%O,start=${0xB000 if slot else 0xA000:04X},size=$1000; P:file="",start=$8D5E,size=79; }} SEGMENTS {{ CODE:load=IMAGE,type=ro; RODATA:load=IMAGE,type=ro; {extra} }}')
   subprocess.run(['ld65','-C',str(d/'image.cfg'),'-o',str(temp/(tag+'.bin')),'-Ln',str(temp/(tag+'.lbl')),'-m',str(temp/(tag+'.map')),*map(str,objects)],check=True)
   raw=(temp/(tag+'.bin')).read_bytes();assert len(raw)<=4096 and raw[:16]==bytes.fromhex(binding)
   (temp/(tag+'.seo')).write_bytes(wrap(raw,slot,ident,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(binding)))
   budgets[tag]=dict(bytes=len(raw),free=4096-len(raw),slot=slot,id=ident,sha256=hashlib.sha256(raw).hexdigest())
  (temp/'budget.json').write_text(json.dumps(dict(binding=binding,resident_sha256=report['sha256'],images=budgets,new_BSS=0,new_ZP=0),indent=2)+'\n')
  assert inputs(base)==before,'source/resident changed during rebase build'
  saved={n:(out/n).read_bytes()if(out/n).exists()else None for n in artifacts+['content.json','jobs.stamp']}
  try:
   for n in artifacts:write_changed(out/n,(temp/n).read_bytes())
   valid_outputs()
   write_changed(manifest,(json.dumps(dict(schema=1,inputs=before,artifacts={n:sha(out/n)for n in artifacts}),indent=2,sort_keys=True)+'\n').encode())
   write_changed(out/'jobs.stamp',(json.dumps(before,sort_keys=True)+'\n').encode())
  except BaseException:
   for n,data in saved.items():
    if data is None:(out/n).unlink(missing_ok=True)
    else:write_changed(out/n,data)
   raise
 return dict(rebuilt=True,binding=binding,images=budgets)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--base',type=Path,default=ROOT);a=p.parse_args();print(json.dumps(build(a.out.resolve(),a.base.resolve()),sort_keys=True))
