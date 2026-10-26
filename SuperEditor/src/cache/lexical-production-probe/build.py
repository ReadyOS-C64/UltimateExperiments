"""Private production-ID milestones; frozen inputs, no shared build."""
from pathlib import Path
import hashlib,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'tests')]
from test_cache_lexical import command,labels

def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def build(out,base):
 out.mkdir(parents=True)
 previous=ROOT/'src/cache/lexical-adaptive-probe/build.py'
 assert hashlib.sha256(previous.read_bytes()).hexdigest()=='91b40193bee09dea23d43d1c19384f4c880c76e9fd982085edf0ea086c71dfba'
 binaries,linked,result=module('sealed_adaptive',previous).build(out/'adaptive',base)
 tree=out/'adaptive/profiles/tree';report=base/'build/editor-report.json';digest=json.load(open(report))['resident_binding']['digest']
 for tag,mask in [('inline-control',False),('inline-lexcap',True)]:
  d=out/tag;d.mkdir();objects=[]
  names=['source-entry','source-seed','query','source','records','source-core','source-page']
  for n in names:
   text=(tree/'src/cache/inline'/(n+'.s')).read_text()
   if mask and n=='source-seed':
    old=' lda BCQP_CACHE+3\n cmp #1';assert text.count(old)==1
    text=text.replace(old,' lda BCQP_CACHE+3\n and #$7F\n cmp #1')
   src=d/(n+'.s');src.write_text(text);obj=d/(n+'.o');command(['ca65','-g','-D','BCQ_EDITOR_ACTIVE=1','-D','BCQ_SELECTOR_OWNS_OWNER=1','-I',out/'adaptive/profiles','-I',tree/'src','-o',obj,src]);objects.append(obj)
  command(['python3',ROOT/'tools/module_bindings.py','--report',report,'--output',d/'aliases.s',*objects]);command(['ca65','-o',d/'aliases.o',d/'aliases.s'])
  (d/'image.cfg').write_text('MEMORY {C:file=%O,start=$B000,size=$1000;} SEGMENTS {CODE:load=C,type=ro;RODATA:load=C,type=ro;}')
  command(['ld65','-C',d/'image.cfg','-o',d/'image.bin','-Ln',d/'image.lbl','-m',d/'image.map',*objects,d/'aliases.o'])
  raw=(d/'image.bin').read_bytes();assert len(raw)<=4096
  if not mask:assert raw==(base/'build/overlays/line.seo').read_bytes()[36:],'C39 control not exact'
  binaries[tag]=raw;linked[tag]=labels(d/'image.lbl');result[tag]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 # Actual packaged C26 is reassembled only to authenticate parser-entry PCs.
 d=out/'c26-control';d.mkdir();objects=[]
 (d/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 for n,p,defs in [('entry','render/geos/inline.s',['SE_EDITOR_CACHED_INLINE_SOURCE=1','SE_EDITOR_INLINE_NAVIGATION=1','SE_EDITOR_NAV_TARGETED=1','BCQ_EDITOR_ACTIVE=1','BCQ_PAGE_REUSE=1']),('parser','supermark/inline.s',[])]:
  obj=d/(n+'.o');command(['ca65','-g','-I',d,'-I',tree/'src',*[x for flag in defs for x in ('-D',flag)],'-o',obj,tree/'src'/p]);objects.append(obj)
 command(['python3',ROOT/'tools/module_bindings.py','--report',report,'--output',d/'aliases.s',*objects]);command(['ca65','-o',d/'aliases.o',d/'aliases.s'])
 (d/'image.cfg').write_text('MEMORY {C:file=%O,start=$B000,size=$1000;P:file="",start=$8D00,size=$1E0;} SEGMENTS {GEOS_INLINE:load=C,type=ro;SM_INLINE:load=C,type=ro;SM_STATE:load=P,type=bss,define=yes;}')
 command(['ld65','-C',d/'image.cfg','-o',d/'image.bin','-Ln',d/'image.lbl','-m',d/'image.map',*objects,d/'aliases.o'])
 raw=(d/'image.bin').read_bytes();assert raw==(base/'build/overlays/geosinln.seo').read_bytes()[36:],'C26 control not exact'
 linked['c26']=labels(d/'image.lbl');result['c26-control']=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 (out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');return binaries,linked,result
