"""Private raw short-row typing pair; all inputs frozen, no shared build."""
from pathlib import Path
import hashlib,importlib.util,json,shutil
ROOT=Path(__file__).resolve().parents[5]
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def patch(text,old,new):
 assert text.count(old)==1,old;return text.replace(old,new)
def build(out,base):
 out.mkdir(parents=True);p=load(ROOT/'src/render/grid/probes/plain-caret/build.py','released_caret');caret_fixture,previous=p.build(out/'caret-release',base)
 tree=out/'caret-release/tree';d=tree/'src/render/grid/caret';c=(d/'caret.s').read_text();h=(d/'helper.s').read_text();a=(d/'api.inc').read_text()
 c=patch(c,'type_try:\n jsr authenticate_paragraph\n','type_try:\n ldy #2\n lda se_render_caps\n bne :+\n ldy #0\n: jsr authenticate_dependencies\n')
 c=patch(c,' lda #14\n jsr helper\n jcs long_try\n',' lda #14\n jsr helper\n bcc @prepared\n lda se_render_caps\n jeq miss\n jmp long_try\n@prepared:\n')
 a=patch(a,'N_CRC=254','N_CAPS=253 ;exact presentation policy, CRC-covered and compared in every consumer\nN_CRC=254')
 h=patch(h,' jsr field\n jcs invalid\n.endmacro',' jsr field\n bcc :+\n rts\n:\n.endmacro')
 h=patch(h,' FIELD se_gc_valid,N_VALID,3\n FIELD se_gc_previous_ui,N_PREVUI,1\n FIELD se_gc_current_ui,N_CURUI,1\n',' .assert se_gc_previous_ui=se_gc_valid+3,lderror,"GC fields adjacency"\n .assert se_gc_current_ui=se_gc_valid+4,lderror,"GC fields adjacency"\n FIELD se_gc_valid,N_VALID,5\n FIELD se_render_caps,N_CAPS,1\n')
 h=patch(h,' FIELD se_sel_mark,N_MARK,1\n FIELD se_sel_anchor,N_ANCHOR,3\n',' .assert se_sel_anchor=se_sel_mark+1,lderror,"selection fields adjacency"\n FIELD se_sel_mark,N_MARK,4\n')
 h=patch(h,' FIELD se_ef_token,N_TOKEN,5\n FIELD se_ef_count,N_COUNT,2\n',' .assert se_ef_count=se_ef_token+5,lderror,"fold fields adjacency"\n FIELD se_ef_token,N_TOKEN,7\n')
 h=patch(h,' FIELD se_ef_fold_rows,N_BITS,3\n FIELD se_ef_projection_generation,N_PROJECTION,2\n',' .assert se_ef_projection_generation=se_ef_fold_rows+3,lderror,"projection fields adjacency"\n FIELD se_ef_fold_rows,N_BITS,5\n')
 h=patch(h,'type_long_prepare:\n lda #2\n','type_long_prepare:\n lda se_render_caps\n jeq invalid\n lda #2\n')
 h=patch(h,' lda se_st_valid\n cmp #1\n jne invalid\n lda se_st_request\n jne invalid\n',' lda se_render_caps\n beq @raw_style\n lda se_st_valid\n cmp #1\n jne invalid\n lda se_st_request\n jne invalid\n@raw_style:\n')
 h=patch(h,' jsr sc_check\n jcs invalid\n',' lda se_render_caps\n beq :+\n jsr sc_check\n jcs invalid\n:\n')
 h=patch(h,' cpx TLEN\n bcs @oldnext\n lda B,x\n',' cpx TLEN\n bcs @oldnext\n lda se_render_caps\n beq @oldnext\n lda B,x\n')
 h=patch(h,' jsr sc_rekey\n jcs invalid\n',' lda se_render_caps\n beq :+\n jsr sc_rekey\n jcs invalid\n:\n')
 h=patch(h,' sta TLEN\n clc\n adc #1\n cmp W\n jcs invalid\n',' sta TLEN\n lda se_render_caps\n beq @raw_length\n lda TLEN\n clc\n adc #1\n jmp @check_length\n@raw_length:\n lda TLEN\n clc\n adc SIGN\n@check_length:\n cmp W\n jcs invalid\n')
 # Raw bytes have no grammar: geometry and exact byte delta are the authority.
 h=patch(h,' lda EDIT\n jeq invalid\n cmp TLEN\n jcs invalid\n',' lda se_render_caps\n beq @raw_edit\n lda EDIT\n jeq invalid\n cmp TLEN\n jcs invalid\n jmp @edit_ok\n@raw_edit:\n lda EDIT\n cmp TLEN\n bcc @edit_ok\n bne @edit_bad\n lda SIGN\n cmp #1\n beq @edit_ok\n@edit_bad:\n jmp invalid\n@edit_ok:\n')
 h=patch(h,' lda B\n jsr alpha\n jcs invalid\n',' lda se_render_caps\n beq :+\n lda B\n jsr alpha\n jcs invalid\n:\n')
 # All three pure short-row alpha/alnum calls retain original Full behavior.
 # In raw mode only CR is excluded: it changes row ownership/geometry.
 h=patch(h,'alpha:\n and #$7F\n','raw_char:\n ldx se_render_caps\n bne alnum\n cmp #13\n beq type_bad\n clc\n rts\nalpha:\n and #$7F\n')
 before,after=h.split('raw_char:',1)
 before=before.replace(' jsr alnum\n',' jsr raw_char\n')
 h=before+'raw_char:'+after
 # No synthetic semantic descriptor/checkpoint is published in raw mode.
 h=patch(h,' sta se_l_revision,x\n sta se_st_descriptor+17,x\n',' sta se_l_revision,x\n lda se_render_caps\n beq :+\n lda se_r_revision,x\n sta se_st_descriptor+17,x\n:\n')
 h=patch(h,' lda se_v_length,x\n sta se_st_descriptor+21,x\n',' lda se_render_caps\n beq :+\n lda se_v_length,x\n sta se_st_descriptor+21,x\n:\n')
 (d/'caret.s').write_text(c);(d/'helper.s').write_text(h);(d/'api.inc').write_text(a)
 m=load(d/'build.py','raw_pair_build');m.build(out/'candidate',base)
 frozen=out/'fixture';shutil.copytree(base,frozen);identity=json.loads((frozen/'freeze.json').read_text())
 for name in ('grid','geostail'):
  image=(out/'candidate'/(name+'.seo')).read_bytes();(frozen/'build/overlays'/(name+'.seo')).write_bytes(image);identity['assets'][name]=hashlib.sha256(image).hexdigest()
 identity['private_change']='Raw short-row Plain typing and CRC-bound exact render_caps; strict semantic path preserved.';(frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 result=dict(status='built',baseline=str(base),original_pair_byte_identical=True,caret_release=str(caret_fixture),newBSS=0,newZP=0,assets={name:identity['assets'][name]for name in ('grid','geostail')})
 for name in ('grid','geostail'):result[name]=(out/'candidate'/(name+'.map')).read_text().split('Segment list:')[1].split('Exports list by name:')[0].strip()
 (out/'build.json').write_text(json.dumps(result,indent=2)+'\n');return frozen,result
if __name__=='__main__':
 import sys
 print(build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())[1])
