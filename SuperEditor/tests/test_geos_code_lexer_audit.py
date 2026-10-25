"""Read-only attribution of an existing BASIC whole-word/substring color discrepancy."""
from pathlib import Path
import json,sys,importlib.util
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_code_typing as component
from supermark_model import lex

def run(out,base=component.BASE):
 out.mkdir(parents=True,exist_ok=True);spec=importlib.util.spec_from_file_location('gct_audit_build',ROOT/'src/render/geos/code-typing-candidate/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);payload,image,budget=b.build(out/'capsule',base)
 fold=component.fold;fold.geos.grid.editor_fixture.ROOT=fold.geos.grid.cpu_editor.ROOT=base;names=json.loads((base/'freeze.json').read_text())['names'];fold.geos.grid.editor_fixture.NAMES=fold.geos.grid.cpu_editor.NAMES=names
 dll=fold.geos.grid.runner(out);f=component.Fixture(out,base,dll,True);cases=[]
 try:
  f.source(b'A');f.m.load(f.s['se_overlay_header'],image[:36]);f.m.load(0x5000,image[36:]);assert not f.call('se_overlay_import').p&1
  for text in ['Second code row','SECOND CODE ROW','ON','SECOND','PRINT','PRINTX','XPRINT','aON','GO TO']:
   data=fold.geos.native_text(text);f.m.load(0x8200,data);f.m.load(0x8b40,bytes([len(data),16,0,1])+bytes(11));f.put('se_f_owner',4,1);f.m.write(f.s['se_overlay_frame'],0);r,n=f.fast_call(f.s['se_overlay_call'],a=31,x=0);assert r.a==0 and not r.p&1
   actual=f.read(0x8300,len(data));expected=bytearray([4]*len(data));spans=lex(data,1)
   for start,end,role in spans:expected[start:end]=bytes([role])*(end-start)
   cases.append(dict(text=text,native=list(data),actual_roles=list(actual),model_roles=list(expected),model_spans=spans,equal=actual==expected))
  result=dict(status='audited',cases=cases,scope='Actual unchanged pure lexer in sealed private capsule, no C24/C25/parser/source coordinator; host model comparison only.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));return result
 finally:f.close()
if __name__=='__main__':run(ROOT/'build/geos-code-typing-candidate/lexer-audit')
