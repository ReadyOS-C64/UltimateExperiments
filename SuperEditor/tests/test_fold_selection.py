"""Actual editor selected folded summaries across40/60/80; private CPU proof.
Default prepares only. --run freezes the parent-approved product; no sharedmake.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,ctypes as C,hashlib,json,sys
import test_fold_retention as retention
import test_fold_projection as projection
import test_fold_builder as builder
import test_grid_modes as grid
from test_folds import action_model
from redraw_model import native_text,Screen,verify_screen
ROOT=grid.ROOT

class Fixture(projection.Fixture):
 def reu(self):
  b=C.create_string_buffer(16*1024*1024);self.dll.gm_reu(self.m.handle,len(b),b);return b.raw
 def source(self,data):super().source(data,banks=2,physical=256)

def selected_marker(lo,hi,cr,after):return lo<hi and lo<after and cr<hi

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');parser.add_argument('--smoke',action='store_true');parser.add_argument('--fixture',type=Path);args=parser.parse_args()
 if not args.run:
  print('Prepared selected-fold-summary gate. Run --run --smoke after parent build-ready.');return
 out=ROOT/'build/fold-selection'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True);frozen,identity=retention.freeze(out,args.fixture)
 grid.cpu_editor.ROOT=grid.editor_fixture.ROOT=frozen;grid.cpu_editor.NAMES=grid.editor_fixture.NAMES=identity['names'];dll=grid.runner(out);frames=[];f=None
 def check(data,folds,anchor,caret,mark,tag):
  # These are the public persistent selection ABI fields; actual R1/C16 calls
  # se_selection_range themselves. No precomputed range or renderer is mocked.
  f.position(caret);f.put('se_sel_anchor',anchor);f.put('se_sel_mark',int(mark),1)
  canonical,reu,catalog=f.canonical(),f.reu(),f.catalog();metadata=f.metadata();top=f.get('se_v_top');f.render()
  wanted,anchors,ends,bits,seen=projection.expected(f,data,folds,top)
  actual=tuple(int.from_bytes(f.read(f.s['se_v_rows']+i*3,3),'little') for i in range(22))+(f.get('se_v_bottom'),)
  assert actual==anchors,(tag,'anchors',actual,anchors)
  assert tuple(int.from_bytes(f.read(f.s['se_ef_paint_ends']+i*3,3),'little') for i in range(22))==ends
  assert f.get('se_ef_fold_rows')==sum(x<<i for i,x in enumerate(bits)),(tag,'fold row bits')
  assert f.get('se_ef_valid',1) and f.metadata()==metadata==b''.join(x.bytes() for x in folds),(tag,'fold metadata changed')
  if f.get('se_mode',1):
   actualbits=f.read(0x6000,8000);actualattrs=f.read(0x4000,1000)
   assert actualbits==wanted[0],(tag,'bitmap',[(i,a,b) for i,(a,b) in enumerate(zip(actualbits,wanted[0])) if a!=b][:12])
   assert actualattrs==wanted[1],(tag,'attributes',[(i,a,b) for i,(a,b) in enumerate(zip(actualattrs,wanted[1])) if a!=b][:12])
  else:verify_screen(f.read(0x4000,1000),f.read(0xD800,1000),Screen(*wanted,anchors,seen),tag=tag)
  assert f.canonical()==canonical and f.merged()==data and f.catalog()==catalog and f.reu_safe(reu,tag)
  assert f.read(0xC600,1024)==f.shim and not any(f.get(n,1) for n in ['se_f_owner','se_doc_read_locks','se_fs_owned','se_e_job'])
  lo,hi=sorted((anchor,caret)) if mark else (0,0)
  markers=[dict(row=row,cr=end-1,after=anchors[row+1],selected=selected_marker(lo,hi,end-1,anchors[row+1])) for row,(end,bit) in enumerate(zip(ends,bits)) if bit]
  # Direct resident helper contract agrees with the independent interval
  # oracle on every row and leaves the shared phase completely untouched.
  phase=f.read(0x8D00,1152)
  for row,(end,bit) in enumerate(zip(ends,bits)):
   reg=f.call('se_ef_summary',row);selected=bool(bit and selected_marker(lo,hi,end-1,anchors[row+1]))
   assert reg.a==int(bool(bit)) and bool(reg.p&2)==(not bool(bit)) and bool(reg.p&1)==selected,(tag,'summary A/Z/C',row,reg.a,reg.p,bit,selected)
  assert f.read(0x8D00,1152)==phase,(tag,'summary helper touched phase')
  frames.append(dict(tag=tag,mode=f.get('se_mode',1),anchor=anchor,caret=caret,mark=bool(mark),markers=markers,source_bytes=len(data)));(out/'progress.json').write_text(json.dumps(frames,indent=2)+'\n')
 def load(data,mode,nested=False):
  f.source(data)
  if mode:f.command(96+mode)
  tree,_,_,error=builder.oracle(data);assert not error
  f.command(115);folds,_=action_model(tree,3,0,0,f.get('se_ef_motion',4),0)
  if nested:
   f.command(114);folds,_=action_model(folds,2,0,0,f.get('se_ef_motion',4),0)
  return folds
 try:
  f=Fixture(out,frozen,dll,True)
  basic=native_text('before\r:::region Detail\rhidden alpha\rhidden beta\r:::end\rafter\r')
  for mode in ([0] if args.smoke else [0,1,2]):
   folds=load(basic,mode);fold=folds[0];cr=fold.hidden-1
   # Tiny first gate isolates new behavior: no selected visible opener byte,
   # only the hidden tail is selected, ending at its next canonical anchor.
   check(basic,folds,fold.hidden+3,fold.end,True,f'{mode}-partial-hidden-only')
   if args.smoke:break
   variants=[('unmarked',fold.hidden+3,fold.end,False),('zero-mark',fold.end,fold.end,True),('full-hidden',fold.hidden,fold.end,True),('reverse-full',fold.end,fold.start,True),('end-exact-CR',cr,fold.start,True),('start-exact-foldend',fold.end,fold.end+3,True),('caret-marker-selected',fold.end,cr,True),('caret-marker-end-boundary',fold.start,cr,True)]
   for label,anchor,caret,mark in variants:check(basic,folds,anchor,caret,mark,f'{mode}-{label}')
   f.command(77)
   check(basic,folds,fold.hidden+3,fold.end,True,f'{mode}-nowrap-hidden-only')
   check(basic,folds,cr,fold.start,True,f'{mode}-nowrap-end-exact-CR')
   f.command(76)
   # A user-reachable hidden-only selection: F2 marks inside the expanded body,
   # collapse moves the caret to its summary, then public GOTO moves after it.
   f.source(basic)
   if mode:f.command(96+mode)
   body=fold.hidden+3;f.position(body);f.command(68);assert f.get('se_sel_anchor')==body
   f.command(113);tree,_,_,error=builder.oracle(basic);assert not error;actual,_=action_model(tree,1,0,body,f.get('se_ef_motion',4),body)
   line=basic[:fold.end].count(b'\r')+1;f.typed(native_text(f'goto {line}'));assert f.get('se_sel_mark',1) and f.get('se_sel_anchor')==body and f.get('se_hot_caret')==fold.end
   check(basic,actual,body,fold.end,True,f'{mode}-actual-F2-collapse-GOTO-hidden-selection')
   nested=native_text('# Parent\rintro\r:::region A\rfirst\r:::end\rmiddle\r:::region B\rsecond\r:::end\r# Tail\rend\r')
   folds=load(nested,mode,nested=True)
   for label,anchor,caret in [('nested-child-A',folds[1].hidden+1,folds[1].end),('nested-both-reverse',folds[2].end,folds[1].start)]:check(nested,folds,anchor,caret,True,f'{mode}-{label}')
   folds=load(nested,mode);check(nested,folds,folds[1].hidden+1,folds[0].end,True,f'{mode}-ancestor-represents-hidden-child')
   width=[40,60,80][mode]
   for n in [width-1,width,width+1]:
    data=native_text('before\r:::region ')+b'X'*(n-len(':::region '))+native_text('\rhidden\r:::end\rafter\r');folds=load(data,mode);fold=folds[0]
    check(data,folds,fold.hidden+1,fold.end,True,f'{mode}-opener{n}-hidden')
    check(data,folds,fold.hidden-1,fold.start,True,f'{mode}-opener{n}-end-CR')
   high=b'X'*65540+native_text('\r:::region High\rhidden high\r:::end\rafter\r');folds=load(high,mode);fold=folds[0];assert fold.start>65535
   check(high,folds,fold.hidden+1,fold.end,True,f'{mode}-above64KiB-hidden')
   check(high,folds,fold.end,fold.start,True,f'{mode}-above64KiB-reverse')
  result=dict(status='passed',identity=identity,frames=frames,checked_reu_bytes=16*1024*1024,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),oracle_sha256=hashlib.sha256((ROOT/'tests/test_fold_projection.py').read_bytes()).hexdigest(),scope='Actual R1/C11/C16/selection-range consumers and folded source metadata; exhaustive valid persistent selection ABI setups plus actual F2-collapse-GOTO flow. Complete CPU pixels/colors/anchors and source/history/REU/shim guards; no native/physical-key claim.')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 except BaseException as e:(out/'failure.json').write_text(json.dumps(dict(error=repr(e),frames=frames),indent=2)+'\n');raise
 finally:
  if f is not None:f.close()
if __name__=='__main__':main()
