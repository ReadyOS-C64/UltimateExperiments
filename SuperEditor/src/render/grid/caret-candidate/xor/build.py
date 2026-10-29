from pathlib import Path
import importlib.util,sys,json,shutil,hashlib,zipfile
ROOT=Path(__file__).resolve().parents[5];BASE=ROOT/'build/grid-caret-integration/20261025T163000/fixture'
def build(out,base=BASE):
 d=out/'source';d.mkdir(parents=True)
 source=ROOT/'build/grid-caret-integration/20261025T163000/tree/src/render/grid/caret-candidate'
 for n in ['api.inc','build.py']: (d/n).write_bytes((source/n).read_bytes())
 s=(source/'caret.s').read_text();a=s.index(' lda #0\n ldx #67\n',s.index('paint_row:'));b=s.index(' bcs @return\n jsr row_request',a)
 s=s[:a]+' jsr xor_changes\n'+s[b:]
 old=''' lda H+N_SEEN
 sta OLDSEEN'''
 new=''' lda H+N_SEEN
 cmp #2
 jcs miss
 sta OLDSEEN
 tax
 beq @old_hidden
 lda H+N_ROW
 cmp #22
 jcs miss
 lda H+N_COL
 cmp W
 jcs miss
@old_hidden:'''
 assert s.count(old)==1;s=s.replace(old,new)
 s=s.replace('@prepared:\n jsr se_selection_range','@prepared:\n lda #0\n sta CHANGE\n sta CHANGE+1\n jsr se_selection_range')
 old=''' lda (text_ptr),y
 and #1
 sta BCOL'''
 new=''' lda (text_ptr),y
 pha
 and #6
 beq :+
 lda #1
: sta WAS
 pla
 and #1
 sta BCOL'''
 assert s.count(old)==1;s=s.replace(old,new)
 old='''@store:
 ldy COL
 lda BCOL
 sta (text_ptr),y'''
 new='''@store:
 lda BCOL
 and #6
 beq :+
 lda #1
: cmp WAS
 beq @unchanged
 ldx #0
 lda PTR
 cmp #<P
 beq :+
 inx
: ldy CHANGE,x
 cpy #2
 jcs invalid ;optional fast path, never paint a wider marked delta
 lda COL
 cpx #0
 bne @second
 sta CELLA,y
 jmp @changed
@second:
 sta CELLB,y
@changed:
 inc CHANGE,x
@unchanged:
 ldy COL
 lda BCOL
 sta (text_ptr),y'''
 assert s.count(old)==1;s=s.replace(old,new)
 s+='\n.segment "CODE"\n'+(ROOT/'src/render/grid/caret-candidate/xor/paint.s').read_text();(d/'caret.s').write_text(s)
 spec=importlib.util.spec_from_file_location('xorbuilder',d/'build.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.ROOT=ROOT;m.D=d;seo,labels,budget=m.build(out/'linked',base)
 frozen=out/'fixture';shutil.copytree(base,frozen);identity=json.load(open(frozen/'freeze.json'));(frozen/'build/overlays/grid.seo').write_bytes(seo);identity['assets']['grid']=hashlib.sha256(seo).hexdigest();identity['xor_selector_delta']=True;(frozen/'freeze.json').write_text(json.dumps(identity,indent=2)+'\n')
 archive=frozen/'product-sources.zip'
 with zipfile.ZipFile(archive) as z:contents={n:z.read(n) for n in z.namelist()}
 contents['src/render/grid/caret-candidate/caret.s']=s.encode()
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for n,data in contents.items():z.writestr(n,data)
 (out/'budget.json').write_text(json.dumps(budget,indent=2)+'\n');return frozen,budget
if __name__=='__main__':print(build(Path(sys.argv[1]))[1])
