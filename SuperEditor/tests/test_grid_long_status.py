"""Actual final C33 linear26glyph status vs verified128lookup compact formatter."""
from pathlib import Path
from datetime import datetime,timezone
import json
import test_geos_fold_editor as fold,test_grid_modes as grid
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'build/grid-long-transaction-extended/20261025T200745478455Z/fixture';LEAF=BASE.parent/'leaf'
def labels(p):return{z[2].lstrip('.'):int(z[1],16)for line in p.read_text().splitlines()if(z:=line.split())and z[0]=='al'}
def run(out):
 ident=json.load(open(BASE/'freeze.json'));grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=BASE;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=ident['names'];dll=fold.retention.runner(out);f=fold.Fixture(out,BASE,dll,True);g=fold.Fixture(out,BASE,dll,True);l=labels(LEAF/'grid.lbl');c=labels(LEAF/'compact/grid.lbl');cases=[]
 try:
  for nibble in range(16):
   for pending,dirty in((0,0),(0,1),(1,0),(1,1)):
    for reverse in(0,128):
     caret=int(hex(nibble)[2:]*6,16)
     for x in(f,g):
      x.m.load(0x43c0,bytes([0x16])*40);x.m.load(0x7e00,bytes(320));x.m.load(0xdbc0,bytes([1])*40);x.put('se_hot_caret',caret);x.put('se_hot_pending',pending,1);x.put('se_h_dirty',dirty,1);x.put('se_ink_reverse',reverse,1)
     f.m.load(0xb000,(LEAF/'grid.bin').read_bytes());g.m.load(0xb000,(LEAF/'compact/grid.bin').read_bytes());r,n=f.fast_call(l['status']);q,old=g.fast_call(c['status']);assert not r.p&1 and not q.p&1;assert f.read(0x7e00,320)==g.read(0x7e00,320)and f.read(0x43c0,40)==g.read(0x43c0,40),(nibble,pending,dirty,reverse);assert f.read(0xc600,1024)==f.shim;cases.append(dict(nibble=nibble,pending=pending,dirty=dirty,reverse=reverse,instructions=n,old=old))
  result=dict(status='passed',cases=cases,scope='Finalactual26-entry linearlookup vspreviouslyverified128lookup,allhex/state/inverse combinations.');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',len(cases));return result
 finally:f.close();g.close()
if __name__=='__main__':
 out=ROOT/'build/grid-long-status'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);run(out)
