"""Extra bounded-selector refusal and actual-root recovery, private48 only."""
from pathlib import Path
from datetime import datetime,timezone
import json,shutil
import test_grid_caret_candidate_faults as faults
import test_geos_fold_editor as fold
import test_grid_modes as grid
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'build/grid-caret-xor/20261025T170500/fixture'
def run(out,base=BASE):
 transport=out/'transport';transport.mkdir();proof=faults.run(transport,base)
 identity=json.load(open(base/'freeze.json'));grid.editor_fixture.ROOT=grid.cpu_editor.ROOT=base;grid.editor_fixture.NAMES=grid.cpu_editor.NAMES=identity['names'];dll=fold.retention.runner(out);f=fold.Fixture(out,base,dll,True);cases=[]
 try:
  for width in (60,80):
   data=grid.native_text('Marked many words across this row\rSecond')
   f.source(data);f.command(97 if width==60 else 98);f.position(2);f.command(68);f.render();f.finish_style();f.command(33)
   canonical=f.canonical();reu=f.reu();phase=f.read(0x8d00,1152);bits=f.read(0x6000,8000);attrs=f.read(0x4000,1000)
   f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=33,x=1);assert r.a==2 and not r.p&1,(width,'wide-marked-delta-miss',r.a)
   assert f.canonical()==canonical and f.reu()==reu and f.read(0x8d00,1152)==phase and f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs and f.get('se_f_owner',1)==0
   f.render();f.finish_style();(wanted,ink),_,_,_=grid.expected(f,data);assert f.read(0x6000,8000)==wanted and f.read(0x4000,1000)==ink
   fold.geos.png(wanted,ink,out/f'{width}-wide-mark-full-fallback.png');item=dict(width=width,tag='marked-long-delta-before-pixel-miss-and-actual-full-fallback',miss_instructions=n,pixels=64000,attributes=1000);cases.append(item);print('PASS',item,flush=True)

  # Correct-CRC malformed header shape is rejected before any row fetch/paint.
  import binascii
  f.source(grid.native_text('Typed header source'));f.command(98);f.render();f.finish_style()
  def header(value=None):
   f.put('se_reu_logical',f.get('se_gc_handle',1),1);f.put('se_reu_offset',0x1500,2);f.put('se_reu_length',256,2);f.put('se_reu_c64',0x8880,2)
   if value is None:
    assert not f.call('se_reu_copy',1).p&1;return f.read(0x8880,256)
   f.m.load(0x8880,value);assert not f.call('se_reu_copy',0).p&1
  original=header()
  for tag,offset,value in [('seen-not-boolean',199,2),('row22',200,22),('column80',201,80)]:
   malformed=bytearray(original);malformed[offset]=value;malformed[254:]=binascii.crc_hqx(malformed[:254],65535).to_bytes(2,'little');header(malformed)
   canonical=f.canonical();reu=f.reu();phase=f.read(0x8d00,1152);bits=f.read(0x6000,8000);attrs=f.read(0x4000,1000);f.put('se_overlay_frame',1,1);r,n=f.fast_call(f.s['se_overlay_call'],a=33,x=1)
   assert r.a==2 and not r.p&1 and f.canonical()==canonical and f.reu()==reu and f.read(0x8d00,1152)==phase and f.read(0x6000,8000)==bits and f.read(0x4000,1000)==attrs,(tag,'typed-header readonlyrefusal')
   cases.append(dict(tag=tag,validCRC=True,instructions=n));print('PASS',cases[-1],flush=True);header(original)
  result=dict(status='passed',cases=cases,transport_cases=proof['cases'],scope=__doc__);(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:f.close()
if __name__=='__main__':
 out=ROOT/'build/grid-caret-xor-validation'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);print('RUN',out,flush=True);run(out)
