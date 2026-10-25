"""Independent actual block classifications and fail-closed optional-producer latch."""
from pathlib import Path
from datetime import datetime,timezone
import json,binascii
import test_geos_fold_editor as fold,test_grid_modes as grid
from supermark_model import blocks
import font_fixture
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/grid-geowrite-live-dispatch-proof/20261025T205155421158Z/fixture'
def run(out,base):
 ident=json.load(open(base/'freeze.json'));grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=base;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=ident['names'];dll=fold.retention.runner(out);f=fold.Fixture(out,base,dll,True);cases=[];faults=[]
 def cert():
  h=f.get('se_gc_handle',1);bank=f.m.read(f.s['se_reu_map']+h);return f.reu()[bank*65536+0x1600:bank*65536+0x1680],bank
 def verify(tag,data):
  q,bank=cert();assert q[:4]==b'SP\2\xa5'and binascii.crc_hqx(q[:126],65535)==int.from_bytes(q[126:],'little');rows=f.read(f.s['se_v_rows'],66)+f.read(f.s['se_v_bottom'],3);assert q[42:111]==rows and q[4:37]==f.read(f.s['se_st_descriptor'],33);expected=0;events=blocks(data)
  for i in range(22):
   p=int.from_bytes(rows[3*i:3*i+3],'little');e=next((e for e in events if e['start']<=p<e['end']),None)
   if e and e['kind']==0:
    line=data[e['start']:e['end']]
    if 65<=line[0]&127<=90 and not any(v in line for v in b'*@\\'):expected|=1<<i
  assert int.from_bytes(q[111:114],'little')==expected,(tag,q.hex(),hex(expected));want,attrs=grid.expected(f,data)[0];assert f.read(0x6000,8000)==want and f.read(0x4000,1000)==attrs and f.merged()==data and f.read(0xc600,1024)==f.shim;cases.append(dict(tag=tag,rows=expected))
 try:
  for width in (60,80):
   for tag,text in [('literal','Alpha '+('word '*100)+'ends.\rTail.'),('closed',':::basic\r10 PRINT 1\r:::\r:::asm\rlda #1\r:::\rAlpha '+('word '*100)+'ends.\rTail.'),('late-marker','Alpha '+('word '*60)+'*'+('word '*40)+'ends.\rTail.'),('late-escape','Alpha '+('word '*60)+'\\'+('word '*40)+'ends.\rTail.'),('matched-inline','Alpha '+('word '*60)+'**bold**'+('word '*40)+'ends.\rTail.'),('nonalpha-first','#A '+('word '*100)+'ends.\rTail.'),('multiple','Alpha '+('word '*30)+'\rBeta '+('word '*40)+'\rGamma '+('word '*30)+'ends.\rTail.')]:
    data=grid.native_text(text);at=data.find(grid.native_text('word'))+2*width+1;f.source(data);f.command(97 if width==60 else 98);f.position(at);f.render();f.finish_style();verify(str(width)+'-'+tag,data)
  # Actual owned C14 job reaches its live prose scan. A transient typedFE
  # fault during a real R14 source READ must preserve the successful source
  # transport, disarm optional authority, and never approve a partial record.
  data=grid.native_text('Alpha '+('word '*500)+'\rTail.');f.source(data);f.command(98);f.position(22);f.render();f.finish_style();f.key(32);f.begin_style()
  for _ in range(10000):
   if f.get('se_f_owner',1)==2 and f.get('st_phase',1)==4 and f.m.read(0x89c3)==1:break
   f.tick()
  else:raise AssertionError(('no live scan',f.debug(),f.m.read(0x89c3)))
  q,bank=cert();before=f.canonical();allreu=f.reu();f.m.write(f.s['se_reu_physical_owner']+bank,253);f.put('se_overlay_frame',2,1);r,n=f.fast_call(f.s['se_overlay_call'],a=14,x=0);f.m.write(f.s['se_reu_physical_owner']+bank,254);assert not r.p&1 and r.a==0 and f.m.read(0x89c3)==128 and f.canonical()==before and f.reu()==allreu;f.finish_style();q,_=cert();assert q[3]!=165 and f.get('se_st_valid',1)==1;faults.append(dict(tag='transientFEphysical-afteractualprose-start',instructions=n))
  # The next genuine BEGIN must recover without reusing the failed lease/job.
  f.put('se_st_valid',0,1);f.put('se_st_request',1,1);f.put('se_gc_valid',0,1);f.render();f.finish_style();verify('fresh-BEGIN-recovers',f.merged())
  for owner in (0,1,3,4):
   for op in (3,4,5):
    f.put('se_f_owner',owner,1);phase=f.read(0x8880,0x900);canonical=f.canonical();reu=f.reu();f.put('se_overlay_frame',op,1);r,n=f.fast_call(f.s['se_overlay_call'],a=14,x=0);assert r.a==2 and r.p&1 and f.read(0x8880,0x900)==phase and f.canonical()==canonical and f.reu()==reu;faults.append(dict(owner=owner,op=op))
  f.put('se_f_owner',0,1);result=dict(status='passed',cases=cases,faults=faults,scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 except BaseException:(out/'failure-ram.bin').write_bytes(f.read(0,65536));(out/'failure-reu.bin').write_bytes(f.reu());raise
 finally:f.close()
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();out=ROOT/'build/grid-producer-live-authority'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out,a.fixture)
