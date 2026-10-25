"""geoWrite-inspired prefix reuse plus fixed4/5px byteblit, independent840oracle."""
from pathlib import Path
from datetime import datetime,timezone
import json
import test_grid_wrapped_shift as original
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
 out=ROOT/'build/grid-geowrite-shift'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);original.D=ROOT/'src/render/grid/geowrite-reflow-candidate';r=original.run(out);baseline=json.load(open(ROOT/'agentsworking/evidence/M8/20261025T201720331556Z-grid-long-prose/primitive-result.json'));r['baseline']=baseline['instructions'];r['mean_instruction_reduction']=1-r['instructions']['mean']/baseline['instructions']['mean'];(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('A/B',r['mean_instruction_reduction'])
