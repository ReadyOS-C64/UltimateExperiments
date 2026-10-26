"""Private immutable-fixture C26 gate+C39 and byte-only resident range probe."""
from pathlib import Path
import inspect,json,sys
ROOT=Path(__file__).resolve().parents[5]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_cache_inline_source4k as component

def build(out,base):
 out.mkdir(parents=True)
 control,_,inline_control,inline_candidate=component.source_images(out/'source',base)
 consumer=component.build_adapter(out/'consumer',base)
 report=json.loads((base/'build/editor-report.json').read_text());s=report['symbols']
 # The released component's tail aliases are deliberately explicit. They must
 # be the actual current resident state, not an old fixture's invented seam.
 for n,v in {'se_bc_arena':0x9fb5,'se_bc_ticket':0x9fba,'se_bc_incarnation':0x9fbe,'se_bc_flags':0x9fc2,'se_bc_head':0x9fc3,'se_bc_tail':0x9fc4,'se_bc_count':0x9fc5,'se_bc_ring':0x9d85}.items():assert s[n]==v,(n,s[n],v)
 return dict(control=inline_control,candidate=inline_candidate,consumer=consumer)
