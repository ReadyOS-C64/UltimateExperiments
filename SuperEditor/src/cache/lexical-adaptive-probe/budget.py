"""Private budget experiment. Frozen sources only; no canonical outputs."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[3]

def run(*args):
 p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout

def build(out,base):
 out.mkdir(parents=True);tree=out/'tree';tree.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for n in z.namelist():
   if n.startswith('src/')and not n.endswith('/'):
    p=tree/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
 r=json.load(open(base/'build/editor-report.json'));digest=r['resident_binding']['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 defs=['BCQ_EDITOR_ACTIVE=1','BCQ_CLASSIFY=1','BCQ_SELECTOR_OWNS_OWNER=1','BCQ_PAGE_REUSE=1','BCQ_FORWARD_SEED=1','BCQ_COMMITTED_IDENTITY=1','BCQ_EMPTY_INLINE_HINT=1']
 result={}
 for tag,forward,adaptive in [('original35',False,False),('original37',True,False),('lex35-measure',False,True),('lex37-measure',True,True),('lex35-compact',False,True),('lex37-compact',True,True)]:
  d=out/tag;d.mkdir();inc=d/'cache/query';inc.mkdir(parents=True)
  for n in ('api.inc','proof-api.inc','proof.inc'): (inc/n).write_bytes((tree/'src/cache/query'/n).read_bytes())
  sources={n:(tree/'src/cache/query'/(n+'.s')).read_text() for n in ('classify-entry','fast-entry','query','source','records')}
  if adaptive:
   old=' lda BC_IO+31\n cmp #1\n jne bq_corrupt'
   new=''' lda BC_IO+31
 and #$FB
 cmp #1
 jne bq_corrupt
 lda BC_IO+31
 lsr a
 lsr a
 sta BQ_LEX_CERT
 cmp BC_IO+98
 jne bq_corrupt'''
   assert sources['query'].count(old)==1
   sources['query']=sources['query'].replace(old,new).replace(' ora BC_IO+98\n','',1)
   old=' lda BQ_CR+2\n and #$F0\n jne bq_corrupt'
   new=''' lda BQ_CR+2
 and #$E0
 jne bq_corrupt
 lda BQ_CR+2
 and #$10
 beq @lex_ok
 lda BQ_LEX_CERT
 jeq bq_corrupt
@lex_ok:'''
   assert sources['records'].count(old)==1;sources['records']=sources['records'].replace(old,new)
   # The tagged kind byte is covered by existing CRC85. Its low7 remain kind1;
   # bit7 authenticates lexical-root capability. Capture/restore changes are
   # measured in this profile only, never assumed compatible with old C21.
   p=(inc/'proof.inc').read_text()
   p=p.replace(' lda BCQP_CACHE+3\n cmp #1',' lda BCQP_CACHE+3\n and #$7F\n cmp #1')
   p=p.replace(' lda BQ_CACHE+3\n cmp #1',' lda BQ_CACHE+3\n and #$7F\n cmp #1')
   marker=' lda #$A5\n sta BCA_PROOF'
   assert p.count(marker)==1
   p=p.replace(marker,''' lda BCQP_CACHE+3
 asl a
 lda #0
 rol a
 sta BQ_LEX_CERT
 lda #1
 sta BQ_CACHE+3
'''+marker)
   p=p.replace(' bne @miss',' jne @miss',2)
   (inc/'proof.inc').write_text(p)
   marker='publish:\n';assert sources['classify-entry'].count(marker)==1
   sources['classify-entry']=sources['classify-entry'].replace(marker,'''publish:
 lda BQ_LEX_CERT
 beq :+
 lda #$81
 sta BQ_CACHE+3
:
''')
   sources['fast-entry']=sources['fast-entry'].replace('publish:\n','publish:\n lda BQ_LEX_CERT\n beq :+\n lda #$81\n sta BQ_CACHE+3\n:\n',1)
  names=['fast-entry'if forward else'classify-entry','query','source','records']
  objs=[]
  for group,ns in [('query',names),('arena',['core','page']if forward else['core','open','page'])]:
   for n in ns:
    p=d/(group+'-'+n+'.s');text=sources[n]if group=='query'else(tree/'src/cache/arena'/(n+'.s')).read_text()
    if tag.endswith('-compact') and group=='arena'and n=='open':
     a=text.index('bca_root_check:\n');tail=text[a:];count=tail.count(' jne bca_corrupt')+tail.count(' jcs bca_corrupt')
     tail=tail.replace(' jne bca_corrupt',' bne @root_bad').replace(' jcs bca_corrupt',' bcs @root_bad').replace('.segment "RODATA"','@root_bad:jmp bca_corrupt\n.segment "RODATA"')
     text=text[:a]+tail
    if tag.endswith('-compact')and group=='query'and n=='query':
     old=' CP BC_IO+32,BQ_SOURCE,59\n CP BC_IO+91,BQ_LENGTH,3'
     assert text.count(old)==1;text=text.replace(old,' CP BC_IO+32,BQ_SOURCE,62')
     old=' .endif\n@return:rts\nse_bc_query_cancel:'
     assert text.count(old)==1;text=text.replace(old,' .endif\nse_bc_query_cancel:')
    if tag.endswith('-compact')and group=='query'and n=='records':
     a=text.index('read_record:\n');b=text.index('\n',text.index('@lex_ok:',a))+1
     part=text[a:b].replace(' jne bq_corrupt',' bne @record_bad').replace(' jeq bq_corrupt',' beq @record_bad')
     text=text[:a]+part+' jmp @record_good\n@record_bad:jmp bq_corrupt\n@record_good:\n'+text[b:]
    p.write_text(text)
    obj=p.with_suffix('.o');flags=defs+(['BCQ_FORWARD_QUERY=1']if forward else[])if group=='query'else['BCA_READONLY_OPEN=1']
    run('ca65','-g','-I',d,'-I',out,'-I',tree/'src',*[v for f in flags for v in ('-D',f)],'-o',obj,p);objs.append(obj)
  run('python3',ROOT/'tools/module_bindings.py','--report',base/'build/editor-report.json','--output',d/'aliases.s',*objs)
  run('ca65','-o',d/'aliases.o',d/'aliases.s');objs.append(d/'aliases.o')
  # Deliberately oversized *measurement* region: never packaged/imported.
  (d/'image.cfg').write_text('MEMORY {C:file=%O,start=$B000,size=$2000;} SEGMENTS {CODE:load=C,type=ro;RODATA:load=C,type=ro;}')
  run('ld65','-C',d/'image.cfg','-o',d/'image.bin','-Ln',d/'image.lbl','-m',d/'image.map',*objs)
  raw=(d/'image.bin').read_bytes();control=base/'build/overlays'/('page.seo'if forward else'inln.seo')
  if not adaptive:assert raw==control.read_bytes()[36:],tag+' control is not exact packaged image'
  result[tag]=dict(bytes=len(raw),free=4096-len(raw),sha256=hashlib.sha256(raw).hexdigest(),deployable_size=len(raw)<=4096)
 (out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result
if __name__=='__main__':build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
