"""Private optimized lexical classification + authenticated forward-proof profile."""
from pathlib import Path
import binascii,hashlib,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'tests')]
from test_cache_lexical import command,labels

def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def build(out,base):
 out.mkdir(parents=True)
 # Released adapter supplies unchanged gateway/resolver/strict fallback only.
 old=module('released_lexical_adapter',ROOT/'src/cache/lexical-editor-probe/build.py')
 assert hashlib.sha256((ROOT/'src/cache/lexical-editor-probe/build.py').read_bytes()).hexdigest()=='a3f020aa79d7a4c3397c23aeb17a26128aeb3abd5c0d8350ded778d2856d1e0f'
 binaries,linked,result=old.build(out/'released',base)
 budget=module('adaptive_budget',Path(__file__).with_name('budget.py'));br=budget.build(out/'profiles',base)
 for name,tag in [('query','lex35-compact'),('forward','lex37-compact')]:
  d=out/'profiles'/tag;binaries[name]=(d/'image.bin').read_bytes();linked[name]=labels(d/'image.lbl');result[name]=br[tag];assert len(binaries[name])<=4096
 tree=out/'profiles/tree';report=base/'build/editor-report.json';digest=json.load(open(report))['resident_binding']['digest']
 # Coupled C21 changes only the low-kind mask at capture; no forged CP79.
 for tag,adaptive in [('page-control',False),('page-adaptive',True)]:
  d=out/tag;d.mkdir();inc=d/'cache/query';inc.mkdir(parents=True)
  source=(tree/'src/cache/query/proof.inc').read_text()
  if adaptive:
   old=' lda BQ_CACHE+3\n cmp #1';assert source.count(old)==1
   source=source.replace(old,' lda BQ_CACHE+3\n and #$7F\n cmp #1')
  (inc/'proof.inc').write_text(source)
  (d/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
  raw=(base/'build/overlays/geossema.seo').read_bytes()[36:]
  (d/'consumer-witness.inc').write_text('GSC_SEED_SIZE='+str(len(raw))+'\nGSC_SEED_CRC='+str(binascii.crc_hqx(raw,65535))+'\n')
  objects=[]
  for n in ('page','cache'):
   obj=d/(n+'.o');command(['ca65','-g','-I',d,'-I',tree/'src','-o',obj,tree/'src/render/geos'/(n+'.s')]);objects.append(obj)
  command(['python3',ROOT/'tools/module_bindings.py','--report',report,'--output',d/'aliases.s',*objects]);command(['ca65','-o',d/'aliases.o',d/'aliases.s'])
  # Frozen cfg is not needed for these three explicit segments.
  (d/'image.cfg').write_text('MEMORY {C:file=%O,start=$B000,size=$1000;} SEGMENTS {GEOS_PAGE:load=C,type=ro;CODE:load=C,type=ro;RODATA:load=C,type=ro,optional=yes;}')
  command(['ld65','-C',d/'image.cfg','-o',d/'image.bin','-Ln',d/'image.lbl','-m',d/'image.map',*objects,d/'aliases.o'])
  raw=(d/'image.bin').read_bytes();assert len(raw)<=4096
  if not adaptive:assert raw==(base/'build/overlays/geospage.seo').read_bytes()[36:],'page control not exact'
  else:binaries['page']=raw;linked['page']=labels(d/'image.lbl');result['page']=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 result['policy']='Private proof kind1/base or81/lex; CRC85 covers tag. Legacy kind and tagged kind both explicitly validated. Only baseline1/ABI0 or lexical5/ABI1 roots admitted; mapped3/7 refuse.'
 (out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');print('ADAPTIVE_BUDGET',result,flush=True);return binaries,linked,result
