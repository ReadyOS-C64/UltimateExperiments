"""Assemble only the prospective boundary bridge, never claim runtime geometry."""
from pathlib import Path
import hashlib,importlib.util,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[5]
BASE=ROOT/'build/capture-index-fixed/20261026T183928480377Z/fixture'
def build(out):
 out.mkdir(parents=True);tree=out/'tree';tree.mkdir()
 with zipfile.ZipFile(BASE/'product-sources.zip')as z:z.extractall(tree)
 p=tree/'src/render/grid/caret/build.py';spec=importlib.util.spec_from_file_location('geometry_c33',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.build(out/'control',BASE)
 assert (out/'control/grid.seo').read_bytes()==(BASE/'build/overlays/grid.seo').read_bytes()
 c=tree/'src/render/grid/caret/caret.s';s=c.read_text()
 # Current frozen source already contains BOTH refusal-before-phase and
 # sparse-index revocation. Never pay for the geometry bridge by undoing them.
 assert s.index(' lda se_e_redraw',s.index('capture:\n'))<s.index(' jsr capture_tables',s.index('capture:\n'))
 assert ' lda #0\n sta se_i_ready\n sta se_i_count\n sta se_n_cache_count\n ldx #0' in s
 # New helper only. Existing six/seven vectors, font ABI and helper unchanged.
 s+='\n.segment "CODE"\ngeometry:\n sta se_overlay_frame\n lda #24\n ldx #0\n jmp se_overlay_call\n'
 c.write_text(s)
 p=tree/'src/render/grid/paragraph/controller.inc';s=p.read_text()
 s=s.replace('long_try:\n','RG_GEOM=$8DFF\nlong_try:\n lda #0\n sta RG_GEOM\n')
 assert s.count('jcs @bad1 ;no newly introduced physical row')==1;s=s.replace('jcs @bad1 ;no newly introduced physical row','jcs @geometry_boundary ;new boundary is admitted only by new R24')
 assert s.count(' jeq @bad1 ;no removal of an existing physical row')==1;s=s.replace(' jeq @bad1 ;no removal of an existing physical row',' jeq @geometry_boundary\n jmp @packet\n@geometry_boundary:\n lda se_render_caps\n jne @bad1\n lda #5\n jsr geometry\n jcs @bad1')
 # A5/plan/source/NC PREPARE must succeed before the first existing mutation.
 assert s.count('@worker_ready:\n')==1;s=s.replace('@worker_ready:\n','@worker_ready:\n lda RG_GEOM\n beq :+\n lda #3\n jsr geometry\n jcs miss\n:\n')
 assert s.count('@paint_done:\n')==1;s=s.replace('@paint_done:\n','@paint_done:\n lda RG_GEOM\n beq :+\n lda #4\n jsr geometry\n jcs miss\n:\n')
 p.write_text(s);image,labels,budget=m.build(out/'candidate',BASE)
 assert (out/'candidate/geostail.seo').read_bytes()==(BASE/'build/overlays/geostail.seo').read_bytes(),'R25 changed'
 result=dict(status='budget-only',scope='C33 prospective hooks only; R24 complete geometry body not implemented or invoked.',budget=budget,fixedfont=labels['local_native8'],map=(out/'candidate/grid.map').read_text().split('Segment list:')[1].split('Exports list by name:')[0].strip());(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve()))
