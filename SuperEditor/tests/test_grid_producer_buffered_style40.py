"""Existing source40 suite under the declared64catalog/managedbit policy only."""
from pathlib import Path
from datetime import datetime,timezone
import json,inspect,argparse,textwrap
import test_style_editor as original
from overlay_catalog_policy import catalog_identity
import font_fixture
ROOT=original.ROOT
original.Fixture.catalog=lambda self:catalog_identity(self.read(self.s['se_overlay_ids'],6*self.s['se_overlay_capacity']),self.s)
# Same fault target; publishedslotbit7 is verificationstate, notslotidentity.
method=original.Fixture.remove_asset
source=textwrap.dedent(inspect.getsource(method)).replace("self.m.read(self.s['image_slot']+i)==slot","(self.m.read(self.s['image_slot']+i)&1)==slot")
ns=dict(original.__dict__);exec(compile(source,__file__+':declaredslotidentity','exec'),ns);original.Fixture.remove_asset=ns['remove_asset']
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();out=ROOT/'build/grid-producer-buffered-style40'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);original.run(out,a.fixture);r=json.load(open(out/'result.json'));r['catalog_metadata_bytes']=384;r['catalog_policy']='Declared6-array64catalog, tools/overlay_catalog_policy.py; onlypublishedmanagedbit7 normalized.';(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
