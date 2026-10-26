"""Private exact4094 control and optional compact C35 empty-INLINE hint."""
from pathlib import Path
import json,zipfile,sys,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[5];HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'tools')]
from overlays import wrap

def build(out,base):
 out.mkdir(parents=True);tree=out/'tree';tree.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for name in z.namelist():
   if name.startswith('src/')and not name.endswith('/'):
    p=tree/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
 report=base/'build/editor-report.json';r=json.loads(report.read_text());s=r['symbols'];digest=r['resident_binding']['digest'];(out/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 def command(*args):return subprocess.run(list(map(str,args)),cwd=ROOT,check=True,text=True,capture_output=True)
 def link(tag,entry,hint=False):
  folder=out/tag;folder.mkdir();objects=[]
  for group,names in [('query',('classify-entry','query','source','records')),('arena',('core','open','page'))]:
   for name in names:
    defs=['BCQ_EDITOR_ACTIVE=1','BCQ_CLASSIFY=1','BCQ_SELECTOR_OWNS_OWNER=1','BCQ_PAGE_REUSE=1','BCQ_FORWARD_SEED=1','BCQ_COMMITTED_IDENTITY=1']if group=='query'else['BCA_READONLY_OPEN=1']
    if hint:defs+=['BCQ_EMPTY_INLINE_HINT=1']
    path=entry if name=='classify-entry'else tree/'src/cache'/group/(name+'.s');obj=folder/(group+'-'+name+'.o');command('ca65','-g','-I',out,'-I',tree/'src',*[v for d in defs for v in ('-D',d)],'-o',obj,path);objects.append(obj)
  command(sys.executable,ROOT/'tools/module_bindings.py','--report',report,'--output',folder/'aliases.s',*objects);command('ca65','-o',folder/'aliases.o',folder/'aliases.s');objects.append(folder/'aliases.o')
  (folder/'image.cfg').write_text('MEMORY {C:file=%O,start=$B000,size=$1000;} SEGMENTS {CODE:load=C,type=ro;RODATA:load=C,type=ro;}');command('ld65','-C',folder/'image.cfg','-o',folder/'image.bin','-Ln',folder/'image.lbl','-m',folder/'image.map',*objects);raw=(folder/'image.bin').read_bytes();assert len(raw)<=4096
  image=wrap(raw,1,35,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(folder/'inln.seo').write_bytes(image);return image
 control=link('control',tree/'src/cache/query/classify-entry.s');assert control==(base/'build/overlays/inln.seo').read_bytes(),'packaged C35 control mismatch'
 default=link('flag-off',HERE/'classify-entry.s');assert default==control,'flag-off changed C35'
 hint=link('hint',HERE/'classify-entry.s',True)
 result={'default_bytes':len(control)-36,'hint_bytes':len(hint)-36,'default_sha256':hashlib.sha256(control[36:]).hexdigest(),'hint_sha256':hashlib.sha256(hint[36:]).hexdigest(),'binding':digest,'no_BSS_ZP':True};(out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True);return result

if __name__=='__main__':
 try:build(Path(sys.argv[1]),Path(sys.argv[2]))
 except subprocess.CalledProcessError as e:print(e.stderr,flush=True);raise
