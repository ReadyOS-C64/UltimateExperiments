"""Private C21 routing + byte-proven resident routing, on frozen packed-cold54.

No production files, shared objects or packaged build is modified. The actual
CPU test applies the assembled one-byte resident branch-limit substitution only
after normal fixture source/import, retaining explicit input-binding provenance.
"""
from pathlib import Path
import sys,json,re,subprocess,importlib.util,hashlib
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'tools')]
from overlays import wrap

def labels(p):return {n:int(a,16)for a,n in re.findall(r'al ([0-9a-fA-F]+) \.(\w+)',p.read_text())}

def build(out,base):
 p=ROOT/'src/cache/splice-query-probe/build.py';s=importlib.util.spec_from_file_location('sq',p);sq=importlib.util.module_from_spec(s);s.loader.exec_module(sq)
 images=sq.build(out,base);api=out/'editor-api.inc';api.write_text('.import se_overlay_call,se_overlay_frame\n'+api.read_text());tree=out/'source';(out/'geossema-frozen.bin').write_bytes((base/'build/overlays/geossema.seo').read_bytes()[36:]);subprocess.run([sys.executable,str(tree/'tools/checkpoint_witness.py'),str(out/'geossema-frozen.bin'),str(out)],check=True);report=json.loads((base/'build/editor-report.json').read_text());symbols=report['symbols'];binding=report['resident_binding']['digest'];budget=json.loads((out/'budget.json').read_text());extra={}
 def run(args):subprocess.run(list(map(str,args)),check=True)
 def compile(tag,files,cfg):
  d=out/tag;d.mkdir();objects=[]
  for i,(path,defs)in enumerate(files):
   obj=d/(str(i)+'.o');run(['ca65','-g','-I',out,'-I',tree/'src',*[v for x in defs for v in('-D',x)],'-o',obj,path]);objects.append(obj)
  run([sys.executable,tree/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*objects]);run(['ca65','-o',d/'aliases.o',d/'aliases.s']);objects.append(d/'aliases.o')
  if not isinstance(cfg,Path):(d/'image.cfg').write_text(cfg);cfg=d/'image.cfg'
  run(['ld65','-C',cfg,'-o',d/'image.bin','-Ln',d/'image.lbl','-m',d/'image.map',*objects]);return d/'image.bin'
 page=tree/'src/render/geos/page.s';old=page.read_text();needle='@cold_query:\n    lda #35\n@query:';assert old.count(needle)==1
 cfg=tree/'cfg/geos-editor-page.cfg'
 before=compile('page-before',[(page,[]),(tree/'src/render/geos/cache.s',[])],cfg)
 assert before.read_bytes()==(base/'build/overlays/geospage.seo').read_bytes()[36:],'source-matched original C21'
 private=out/'page-routed.s';routed=old.replace(needle,'@cold_query:\n    lda #41\n@query:');old_init='    lda #0\n    sta GSEM_FRAME+GSEM_CP_VALID\n    lda #14\n    sta PS';assert routed.count(old_init)==1;routed=routed.replace(old_init,'    lda #2\n    sta GSEM_FRAME+GSEM_ERROR ;CP_VALID already proved zero above\n    lda #14\n    sta PS');private.write_text(routed)
 after=compile('page-routed',[(private,[]),(tree/'src/render/geos/cache.s',[])],cfg);raw=after.read_bytes();assert len(raw)<=4096
 images['geospage']=wrap(raw,1,21,api=(symbols['se_overlay_call'],symbols['se_overlay_frame']),binding_digest=bytes.fromhex(binding));(after.parent/'image.seo').write_bytes(images['geospage']);extra['page']=dict(bytes=len(raw),changes=[i for i,(a,b)in enumerate(zip(before.read_bytes(),raw))if a!=b])
 dispatch=tree/'src/render/geos/dispatch.s';old=dispatch.read_text();needle='    cmp #40\n    bcs ordinary_worker';assert old.count(needle)==1
 addr=symbols['se_geos_render'];rcfg=f'MEMORY {{ IMAGE:file=%O,start=${addr:04X},size=$1000; }} SEGMENTS {{ CODE:load=IMAGE,type=ro; }}'
 before=compile('dispatch-before',[(dispatch,[])],rcfg);prg=(base/'build/editor.prg').read_bytes();load=int.from_bytes(prg[:2],'little');start=addr-load+2
 assert before.read_bytes()==prg[start:start+len(before.read_bytes())],'source-matched original resident dispatch'
 private=out/'dispatch-routed.s';private.write_text(old.replace(needle,'    cmp #42\n    bcs ordinary_worker'));after=compile('dispatch-routed',[(private,[])],rcfg);a,b=before.read_bytes(),after.read_bytes();diff=[i for i,(x,y)in enumerate(zip(a,b))if x!=y];assert len(a)==len(b)and len(diff)==1 and a[diff[0]]==40 and b[diff[0]]==42
 patch=dict(address=addr+diff[0],old=40,new=42,original_dispatch_bytes=len(a),private_dispatch_bytes=len(b),source_matched=True,scope='single assembled runtime routing operand, not a registered/sealed production PRG')
 # Build the original cache jobs only for source-matched counter labels. Their
 # packaged images stay unchanged and are compared byte for byte.
 saved_path=list(sys.path);p=tree/'src/cache/editor/build.py';s=importlib.util.spec_from_file_location('cachelabels',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.ROOT=tree;m.build(out/'cache-labels',base);sys.path[:]=saved_path
 for tag in ('fold','sema','inln','page','line'):
  assert(out/'cache-labels'/(tag+'.seo')).read_bytes()==(base/'build/overlays'/(tag+'.seo')).read_bytes(),tag+' original asset'
 # Rebuild the source semantic worker solely to authenticate its parser PCs.
 for tag,cfg,files in [
 ('geossema','geos-editor-semantic.cfg',[('render/geos/semantic.s',[]),('supermark/block.s',[]),('render/geos/checkpoint/codec.s',['GSC_RESTORE_ONLY=1'])]),
 ('geoslex','geos-editor-semantic-lex.cfg',[('render/geos/semantic-lex.s',[]),('supermark/lexer.s',[])]),
 ('geosinln','geos-editor-inline.cfg',[('render/geos/inline.s',['SE_EDITOR_CACHED_INLINE_SOURCE=1','SE_EDITOR_INLINE_NAVIGATION=1','SE_EDITOR_NAV_TARGETED=1','BCQ_EDITOR_ACTIVE=1','BCQ_PAGE_REUSE=1']),('supermark/inline.s',[])])]:
  raw=compile(tag,[(tree/'src'/n,d)for n,d in files],tree/'cfg'/cfg)
  assert raw.read_bytes()==(base/'build/overlays'/(tag+'.seo')).read_bytes()[36:],tag+' exact parser counter image'
 (out/'integration.json').write_text(json.dumps(dict(base=str(base),binding=binding,input_sha256=report['sha256'],resident_routing_patch=patch,images=budget['images'],extra=extra,new_BSS=0,new_ZP=0,production_registration=False),indent=2)+'\n')
 return images,patch
if __name__=='__main__':build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
