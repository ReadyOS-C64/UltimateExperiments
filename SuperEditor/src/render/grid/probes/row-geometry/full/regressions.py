"""Unmodified released Full/Plain edit and original R24 fold consumers."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[6];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import test_grid_raw_boundary as boundary
import test_cache_visual_regressions as visual
def run(out,fixture):
 out.mkdir(parents=True)
 edits=boundary.native_sequence(out/'edits',fixture)
 folds=visual.run(out/'folds',fixture,'fold')
 result=dict(status='PASS',edit_frames=len(edits),fold_frames=len(folds['frames']),scope='Existing complete independent raster/source/packet/checked-DMA tests, invoked unchanged; CPU fixture seams, no native claim.')
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
