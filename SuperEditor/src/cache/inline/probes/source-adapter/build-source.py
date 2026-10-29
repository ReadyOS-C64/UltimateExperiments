from pathlib import Path
import sys,json,zipfile,subprocess,hashlib
sys.path[:0]=['tests','tools']
import test_cache_inline as q
from overlays import wrap

def build_source(out,base):
 out.mkdir();tree=out/'tree';tree.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for name in z.namelist():
   if name.startswith('src/')and not name.endswith('/'):
    p=tree/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
 report=base/'build/editor-report.json';r=json.loads(report.read_text());s=r['symbols'];digest=r['resident_binding']['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 def link(tag):
  d=out/tag;d.mkdir();objs=[]
  for n in('source-line','line','measure','assets'):
   o=d/(n+'.o');q.command('ca65','-g','-I',out,'-I',tree/'src','-D','SE_EDITOR_GEOS_INLINE=1','-o',o,tree/'src/render/geos'/(n+'.s'));objs.append(o)
  q.command(sys.executable,'tools/module_bindings.py','--report',report,'--output',d/'aliases.s',*objs);q.command('ca65','-o',d/'aliases.o',d/'aliases.s');objs.append(d/'aliases.o')
  (d/'image.cfg').write_text('MEMORY { IMAGE:file=%O,start=$B000,size=$1000; } SEGMENTS { GEOS_SOURCE:load=IMAGE,type=ro; CODE:load=IMAGE,type=ro; RODATA:load=IMAGE,type=ro; }')
  q.command('ld65','-C',d/'image.cfg','-o',d/'image.bin','-Ln',d/'image.lbl',*objs);raw=(d/'image.bin').read_bytes();return raw
 control=link('control');expected=(base/'build/overlays/geosline.seo').read_bytes()[36:];assert control==expected,('C20identity',len(control),len(expected),hashlib.sha256(control).hexdigest(),hashlib.sha256(expected).hexdigest())
 p=tree/'src/render/geos/source-inline.s';t=p.read_text();old='    lda #26\n    sta $9135\n    lda #3 ;SOURCE_BEGIN';new='    lda #39\n    sta $9135\n    lda #0 ;CACHE_BEGIN';assert old in t;t=t.replace(old,new,1);p.write_text(t)
 raw=link('candidate');delta=[i for i,(a,b)in enumerate(zip(raw,control))if a!=b];assert len(delta)==2
 image=wrap(raw,1,20,api=(s['se_overlay_call'],s['se_overlay_frame']),binding_digest=bytes.fromhex(digest));(out/'candidate/image.seo').write_bytes(image);print('C20',len(raw),'delta',delta,flush=True);return image
if __name__=='__main__':
 try:build_source(Path('build/cache-inline-c20-fit'),q.classify.BASE)
 except subprocess.CalledProcessError as e:print(e.stderr);raise
