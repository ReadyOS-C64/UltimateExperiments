"""Private probes only. No canonicalbuild; released source identities required."""
from pathlib import Path
import hashlib,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'tests')]
from test_cache_lexical import command,labels
D=Path(__file__).parent

def build(out,base):
 out.mkdir(parents=True);report=json.load(open(base/'build/editor-report.json'));binding=report['resident_binding']['digest']
 (out/'editor-api.inc').write_text('.import se_overlay_call,se_overlay_frame\n.macro OVL_BINDING\n.byte '+','.join('$'+binding[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
 source=ROOT/'src/cache/lexical-link-probe/entry.s';assert hashlib.sha256(source.read_bytes()).hexdigest()=='e44397419d282fde4773d4a78ad46d9e091ebb0aaae6df56afaaff6c830c3258'
 text=source.read_text().replace(' jeq begin\n',' jeq bca_bad\n',1);a=text.index('begin:\n');b=text.index('cancel:\n',a)
 text=text[:a]+'''resolve:
 lda LL_STATE
 jne bca_bad
 lda LX_LIVE
 cmp #1
 jne bca_bad
 lda #1
 sta LL_MODE
 CP se_bc_arena,LX_AUTH,13
 lda #0
 sta BCA_PHASE
 sta BCA_PROOF
 jsr se_bc_arena_open
 jcs fail
 cmp #1
 jne fail
 lda #1
 sta LL_STATE
 jmp bca_pending
'''+text[b:]
 (out/'resolver.s').write_text(text)
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for n in ('core','open','page'):(out/(n+'.s')).write_bytes(z.read('src/cache/arena/'+n+'.s'))
  (out/'fallback.s').write_bytes(z.read('src/render/geos/semantic-lex.s'))
  (out/'lexer.s').write_bytes(z.read('src/supermark/lexer.s'))
  path=out/'fallback-include/render/geos';path.mkdir(parents=True)
  original=z.read('src/render/geos/semantic-lex.inc').decode();assert original.count('GLEX_ID=25')==1;(path/'semantic-lex.inc').write_text(original.replace('GLEX_ID=25','GLEX_ID=39'))
 # Strict private semantic reader supports lexical-tagged roots without
 # claiming legacy CP79 or PAGE_REUSE proof. No classification is fabricated.
 query_dir=out/'query-source';query_dir.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  for name in ('classify-entry','query','source','records'):(query_dir/(name+'.s')).write_bytes(z.read('src/cache/query/'+name+'.s'))
 q=(query_dir/'query.s').read_text();oldroot=' lda BC_IO+31\n cmp #1\n jne bq_corrupt';assert q.count(oldroot)==1
 q=q.replace(oldroot,''' lda BC_IO+31
 cmp #1
 beq @lex_base
 cmp #5
 jne bq_corrupt
 lda BC_IO+98
 cmp #1
 jne bq_corrupt
 sta BQ_LEX_CERT
 jmp @lex_admitted
@lex_base:
 lda BC_IO+98
 jne bq_corrupt
 sta BQ_LEX_CERT
@lex_admitted:''',1).replace(' ora BC_IO+98\n','',1);(query_dir/'query.s').write_text(q)
 q=(query_dir/'records.s').read_text();oldflag=' lda BQ_CR+2\n and #$F0\n jne bq_corrupt';assert q.count(oldflag)==1
 q=q.replace(oldflag,''' lda BQ_CR+2
 and #$E0
 jne bq_corrupt
 lda BQ_CR+2
 and #$10
 beq @lex_record_admitted
 lda BQ_LEX_CERT
 cmp #1
 jne bq_corrupt
@lex_record_admitted:''',1);(query_dir/'records.s').write_text(q)
 query_defs=['BCQ_CLASSIFY=1','BCQ_EDITOR_ACTIVE=1','BCQ_SELECTOR_OWNS_OWNER=1','BCQ_EMPTY_INLINE_HINT=1','BCA_READONLY_OPEN=1']
 profiles={
  'gateway':([('gateway',D/'gateway.s',[])],'$B000',{'CODE'}),
  'query':([*[(n,query_dir/(n+'.s'),query_defs)for n in ('classify-entry','query','source','records')],*[(n,out/(n+'.s'),query_defs)for n in ('core','open','page')]],'$B000',{'CODE','RODATA'}),
  'resolver':([('resolver',out/'resolver.s',[]),*[(n,out/(n+'.s'),['BCA_READONLY_OPEN=1'])for n in ('core','open','page')]],'$A000',{'CODE','RODATA'}),
  'fallback':([('fallback',out/'fallback.s',[]),('lexer',out/'lexer.s',['SE_SM_CODE_ONLY=1']),('state',out/'lexer.s',['SE_SM_STATE_ONLY=1'])],'$B000',{'GEOS_SEMANTIC_LEX','SM_LEXER','SM_STATE'})}
 results={};binaries={};linked={}
 for profile,(sources,addr,segs)in profiles.items():
  dest=out/profile;dest.mkdir();objs=[]
  for name,source,defs in sources:
   obj=dest/(name+'.o');inc=[out/'fallback-include']if profile=='fallback' else[]
   command(['ca65','-g',*[x for d in inc+[out,ROOT/'src']for x in ['-I',d]],*[x for d in defs for x in ['-D',d]],'-o',obj,source]);objs.append(obj)
  command(['python3','tools/module_bindings.py','--report',base/'build/editor-report.json','--output',dest/'aliases.s',*objs]);command(['ca65','-o',dest/'aliases.o',dest/'aliases.s'])
  cfg='MEMORY {C:file=%O,start='+addr+',size=$1000;S:file="",start=$8D00,size=60;} SEGMENTS {'
  cfg+=''.join(n+':load='+('S,type=bss;'if n=='SM_STATE' else'C,type=ro;')for n in sorted(segs))+'}'
  (dest/'image.cfg').write_text(cfg);command(['ld65','-C',dest/'image.cfg','-o',dest/'image.bin','-Ln',dest/'image.lbl','-m',dest/'image.map',*objs,dest/'aliases.o'])
  raw=(dest/'image.bin').read_bytes();assert raw[:16]==bytes.fromhex(binding)and len(raw)<=4096
  binaries[profile]=raw;linked[profile]=labels(dest/'image.lbl');results[profile]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 original=(base/'build/overlays/geoslex.seo').read_bytes()[36:];different=[(i,a,b)for i,(a,b)in enumerate(zip(original,binaries['fallback']))if a!=b];assert len(original)==len(binaries['fallback']) and len(different)==1 and different[0][1:]==(25,39),different;results['fallback']['request_id_only_difference']=different
 print('ADAPTER_BUDGET',results,flush=True);(out/'budget.json').write_text(json.dumps(results,indent=2)+'\n');return binaries,linked,results
