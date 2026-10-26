"""Exact current59 binary stack graph, including genuine C33/R25 direct seam."""
from pathlib import Path
import importlib.util,json,shutil,sys,zipfile
ROOT=Path(__file__).resolve().parents[6];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_editor_registered_stack as registered

def run(out,base):
 out.mkdir(parents=True);project=out/'project';project.mkdir()
 with zipfile.ZipFile(base/'product-sources.zip')as z:z.extractall(project)
 # Only compiler inputs for the unchanged finite lexical dispatches are
 # rebuilt. Each resulting SEO must byte-match the frozen complete image.
 path=project/'src/cache/lexical/build.py';spec=importlib.util.spec_from_file_location('geometry_lexical_control',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.build(project/'build/lexical',base)
 for name in('edit','tail','lex','ical','ctrl'):assert(project/'build/lexical'/(name+'.seo')).read_bytes()==(base/'build/overlays'/(name+'.seo')).read_bytes(),name
 result=registered.run(out/'proof',base,project);return result
if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
