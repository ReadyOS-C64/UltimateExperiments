"""Actual resident source-retreat carry edges, registers unspecified by its API."""
from datetime import datetime,timezone
from pathlib import Path
import json,random
import test_geos_editor as geos
ROOT=geos.ROOT
if __name__=='__main__':
 out=ROOT/'build/view-source-arithmetic'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True)
 frozen,identity=geos.freeze(out)
 geos.grid.editor_fixture.ROOT=geos.grid.cpu_editor.ROOT=frozen
 geos.grid.editor_fixture.NAMES=geos.grid.cpu_editor.NAMES=identity['names']
 dll=geos.grid.runner(out);f=geos.Fixture(out,frozen,dll,True)
 try:
  rng=random.Random(6510);cases=[0,1,255,256,257,65535,65536,65537,0xfffffe,0xffffff]+[rng.randrange(0x1000000)for _ in range(1024)]
  for position in cases:
   f.put('se_v_pos',position);before=f.read(0,65536);f.call('se_view_retreat');after=f.read(0,65536)
   assert f.get('se_v_pos')==(position-1)&0xffffff
   expected=bytearray(before);expected[0x100:0x200]=after[0x100:0x200];a=f.s['se_v_pos'];expected[a:a+3]=after[a:a+3];assert after==expected
  result=dict(status='passed',identity=identity,cases=len(cases),wholeRAM=65536,scope='Actual resident24bit retreat; wholeRAM except3-byte position and hardwarestack, no A/P preservation contract.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',len(cases),flush=True)
 finally:f.close()
