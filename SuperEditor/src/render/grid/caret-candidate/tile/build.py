from pathlib import Path
import importlib.util,sys,json
ROOT=Path(__file__).resolve().parents[5];BASE=ROOT/'build/grid-caret-integration/20261025T163000/fixture'
def build(out,base=BASE):
 d=out/'source';d.mkdir(parents=True)
 source=ROOT/'build/grid-caret-integration/20261025T163000/tree/src/render/grid/caret-candidate'
 for n in ['api.inc','build.py']: (d/n).write_bytes((source/n).read_bytes())
 s=(source/'caret.s').read_text();a=s.index(' lda #0\n ldx #67\n',s.index('paint_row:'));b=s.index(' bcs @return\n jsr row_request',a)
 s=s[:a]+' jsr paint_cells\n'+s[b:];s+='\n.segment "CODE"\n'+(ROOT/'src/render/grid/caret-candidate/tile/paint.s').read_text();(d/'caret.s').write_text(s)
 spec=importlib.util.spec_from_file_location('tilebuilder',d/'build.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.ROOT=ROOT;m.D=d;return m.build(out/'linked',base)
if __name__=='__main__':print(build(Path(sys.argv[1]))[2])
