"""Private strict-C25 admission; C45 owns its sequential continuation."""
from pathlib import Path
import hashlib,importlib.util,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'tests')]
from test_cache_lexical import command,labels

def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def build(out,base):
 out.mkdir(parents=True)
 adaptive=module('sealed_adaptive_builder',ROOT/'src/cache/lexical-adaptive-probe/build.py')
 binaries,linked,result=adaptive.build(out/'adaptive',base)
 tree=out/'adaptive/profiles/tree';report=base/'build/editor-report.json';digest=json.load(open(report))['resident_binding']['digest']
 with zipfile.ZipFile(base/'product-sources.zip')as z:
  strict=z.read('src/render/geos/semantic-lex.s').decode();lexer=z.read('src/supermark/lexer.s')
 old=' lda se_overlay_frame\n jeq begin\n';assert strict.count(old)==1
 strict=strict.replace(old,' lda se_overlay_frame\n jeq choose\n cmp #3\n jeq begin\n',1)
 old='begin:\n';assert strict.count(old)==1
 strict=strict.replace(old,'''choose:
 ; Only real root job11 can own a child C continuation. Generic direct C25
 ; callers retain their exact strict BEGIN/STEP protocol.
 lda se_e_job
 cmp #11
 bne begin
 lda se_render_caps
 cmp #3
 bne begin
 ; Advisory only: actual gateway still authenticates the root/CR and source.
 lda se_bc_flags
 and #32
 beq begin
 lda $8BA8
 cmp #$81
 bne begin
 sec
 lda F+GSEM_END
 sbc F+GSEM_BODY
 lda F+GSEM_END+1
 sbc F+GSEM_BODY+1
 bne @long
 lda F+GSEM_END+2
 sbc F+GSEM_BODY+2
 beq begin
@long:
 lda #45
 sta $9135
 lda #0
 sta $9136
 lda #1
 clc
 rts
begin:
''',1)
 # COPY24 loop fusion: disjoint source/destination, carry retained, A/X/NZ
 # dead before subsequent source/range operations. No input/count field mixed.
 old=' COPY24 se_fs_length,GLEX_LENGTH';assert strict.count(old)==1
 strict=strict.replace(old,' ldx #2\n@copy_length:lda se_fs_length,x\n sta GLEX_LENGTH,x\n dex\n bpl @copy_length',1)
 old=' COPY24 F+GSEM_QUERY,GLEX_QUERY\n COPY24 F+GSEM_BODY,GLEX_BODY\n COPY24 F+GSEM_END,GLEX_END';assert strict.count(old)==1
 strict=strict.replace(old,' ldx #2\n@copy:lda F+GSEM_QUERY,x\n sta GLEX_QUERY,x\n lda F+GSEM_BODY,x\n sta GLEX_BODY,x\n lda F+GSEM_END,x\n sta GLEX_END,x\n dex\n bpl @copy',1)
 strict=strict.replace('.import se_f_owner,','.import se_bc_flags,se_e_job,se_f_owner,',1)
 gateway=(ROOT/'src/cache/lexical-editor-probe/gateway.s').read_text()
 assert hashlib.sha256(gateway.encode()).hexdigest()=='18de44c59ccb0606b4ac6e5204e4b093f53fa65b585b9d9117de081d86b718a4'
 old=' lda #0\n sta $9136\n lda #39\n sta $9135';assert gateway.count(old)==1
 gateway=gateway.replace(old,' lda #3\n sta $9136\n lda #25\n sta $9135',1)
 old='pending:\n lda #25';assert gateway.count(old)==1;gateway=gateway.replace(old,'pending:\n lda #45',1)
 # Completion explicitly hands to actual C21/C27 with A1. Thus it works even
 # with the frozen resident's worker range ending40; no resident RAM patch.
 # The existing include already imports job/presentation. Its ordinary tail
 # is changed ONLY in this private C45 include, after all successful cleanup.
 handoff=(tree/'src/render/geos/preview-handoff.inc').read_text();old='@ordinary:\n lda #0\n clc\n rts';assert handoff.count(old)==1
 handoff=handoff.replace(old,'@ordinary:\n lda #21\n sta $9135\n lda #1\n sta $9136\n clc\n rts',1)
 for tag,sources,segs in [('strict', [('strict',strict,[]),('lexer',lexer.decode(),['SE_SM_CODE_ONLY=1']),('state',lexer.decode(),['SE_SM_STATE_ONLY=1'])],['GEOS_SEMANTIC_LEX','SM_LEXER','SM_STATE']),('gateway',[('gateway',gateway,[])],['CODE'])]:
  d=out/tag;d.mkdir();inc=d/'render/geos';inc.mkdir(parents=True);(inc/'preview-handoff.inc').write_text(handoff if tag=='gateway'else(tree/'src/render/geos/preview-handoff.inc').read_text())
  (d/'editor-api.inc').write_text('.import se_overlay_frame,se_overlay_call\n.macro OVL_BINDING\n.byte '+','.join('$'+digest[i:i+2]for i in range(0,32,2))+'\n.endmacro\n')
  objects=[]
  for n,text,defs in sources:
   source=d/(n+'.s');source.write_text(text);obj=d/(n+'.o');command(['ca65','-g','-I',d,'-I',tree/'src','-I',ROOT/'src',*[v for de in defs for v in ['-D',de]],'-o',obj,source]);objects.append(obj)
  command(['python3',ROOT/'tools/module_bindings.py','--report',report,'--output',d/'aliases.s',*objects]);command(['ca65','-o',d/'aliases.o',d/'aliases.s'])
  cfg='MEMORY {C:file=%O,start=$B000,size=$1000;S:file="",start=$8D00,size=60;} SEGMENTS {'+''.join(n+':load='+('S,type=bss;'if n=='SM_STATE'else'C,type=ro;')for n in segs)+'}'
  (d/'image.cfg').write_text(cfg);command(['ld65','-C',d/'image.cfg','-o',d/'image.bin','-Ln',d/'image.lbl','-m',d/'image.map',*objects,d/'aliases.o'])
  raw=(d/'image.bin').read_bytes();assert len(raw)<=4096
  binaries[tag]=raw;linked[tag]=labels(d/'image.lbl');result[tag]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 (out/'budget.json').write_text(json.dumps(result,indent=2)+'\n');print('ADMISSION_BUDGET',result,flush=True);return binaries,linked,result
