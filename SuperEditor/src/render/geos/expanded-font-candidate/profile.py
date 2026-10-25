"""Exact current R21 decoder PC attribution, private isolated CPU seam."""
from pathlib import Path
from datetime import datetime,timezone
import sys,re,json
ROOT=Path(__file__).resolve().parents[4];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_geos_strip_raster_candidate as build
import test_geos_literal_profile as profile
BASE=ROOT/'build/geos-incremental-editor/20261025T174216345896Z/fixture'
out=ROOT/'build/geos-expanded-font'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
src,s,labels,raw,image,modules=build.build(out/'link',BASE,'control');f=profile.Fixture(out,BASE,src,s,labels,raw)
cheap=[(int(a,16),n)for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.(\S+)',(out/'link/geosrow.lbl').read_text())]
def local(name,lo,hi):return next(a for a,n in cheap if n==name and lo<=a<hi)
header=local('@header',labels['se_geos_measure'],labels['se_geos_glyph']);bsw=local('@bsw',labels['next_row'],labels['styles'])
bins={'font_header8':(header,header+15),'packed_index_and_pointer':(labels['packed'],labels['prepare_masks']),'packed_row_read_align_mask':(bsw,labels['styles']),'measure_all':(labels['se_geos_measure'],labels['se_geos_glyph']),'glyph_all':(labels['se_geos_glyph'],0xAB21),'styles_inverse_store_advance':(labels['styles'],0xAB21),'row_byte_composite':(labels['byte_row'],labels['validate']),'row_glyph_loop':(labels['next_glyph'],labels['run_done']),'row_address_helpers':(labels['pixel_address'],labels['byte_row']),'tile_election':(labels['resolve'],labels['complete']),'row_validation':(labels['validate'],labels['resolve'])}
cases=[]
try:
 for tag,runs in [('prose',[profile.rec(b'Wim. gjpqy Mixed UPPER/lower')]),('dense',[profile.rec(b'Wim. gjpqy '*9,style=3,role=7)]),('selected',[profile.rec(b'Wim. gjpqy '*9,style=3,role=7,flag=6)]),('two-runs',[profile.rec(b'gjpqy Previous line',y=-8,style=2,role=3),profile.rec(b'Next logical line',y=1,style=1,flag=2,role=8)]),('native',[profile.rec(bytes([0x5c,0x5e,0x7f,0xa1,0xff])*10,style=3,role=2)])]:
  used,counts,_=f.check(runs);row=dict(tag=tag,instructions=used,glyph_calls=counts[labels['se_geos_glyph']],bins={n:sum(counts[a:b])for n,(a,b)in bins.items()});cases.append(row);print(row,flush=True)
 result=dict(status='passed',identity=str(BASE),bins={n:[hex(a),hex(b)]for n,(a,b)in bins.items()},cases=cases,scope='Byte-identical current R21, actual entry/independent wholepixels/attrs/maps/votes/fullRAM+16MiB; instruction attribution, not cycles. Bins overlap explicitly (header inside measure, packed inside glyph).');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
finally:f.close()
