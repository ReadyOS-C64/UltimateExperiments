"""Private pixel worker plus fail-closed live-candidate producer."""
from pathlib import Path
import importlib.util,sys
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('privatecurrent',D/'build-current.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def build(out,base=m.BASE):return m.build(out,base,D/'producer-live.s')
if __name__=='__main__':print(build(Path(sys.argv[1]).resolve())[1])
