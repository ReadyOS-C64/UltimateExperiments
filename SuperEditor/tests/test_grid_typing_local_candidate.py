"""Private C33-owned native status: all original typing/refusal contracts."""
from pathlib import Path
from datetime import datetime,timezone
import inspect,json,hashlib,shutil,importlib.util
import test_grid_typing_candidate as original
ROOT=original.ROOT
BASE=ROOT/'build/geos-incremental-editor/20261025T171440790321Z/fixture'
def run(out,base=BASE):
 source=inspect.getsource(original.run);old="ROOT/'src/render/grid/typing-candidate/build.py'";assert source.count(old)==1
 namespace=dict(original.__dict__);exec(compile(source.replace(old,"ROOT/'src/render/grid/typing-candidate/build-local.py'"),str(Path(__file__))+':builder-only', 'exec'),namespace)
 result=namespace['run'](out,base);result['variant']='C33-owned native font, exact backend-CRC plus managed-verified backing; no R16 execution for XOR-only caret';(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 out=ROOT/'build/grid-typing-local'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
