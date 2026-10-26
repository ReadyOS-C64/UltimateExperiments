"""Actual packaged PAL physical-row geometry and real-CR fallback A/B.

Full-default59 products use public IRQ syntax-Plain setup and ROM File/Open.
Source/history/pixels/attributes/catalog/shim checks reuse the released native
typing evaluator; the stopwatch uses its disclosed PC/SP/input-entry seam.
"""
from pathlib import Path
import argparse,inspect,json,textwrap
import test_grid_raw_typing_vice as native
import test_normal_row80_vice as row
from closed_runtime_copy import run_with_closed_links
ROOT=native.ROOT
BASE=ROOT/'build/lexical-batch-current/20261026T194420618867Z/fixture'

class Plan(row.Plan):
 pass

def scenario(e,geometry):
 report=json.loads((e/'editor-report.json').read_text());assert report['symbols']['se_presentation_default']==3
 # Return is a body edit here. Only this setup precondition differs from the
 # released command-acceptance stopwatch; all scheduler/capture guards remain.
 source=inspect.getsource(native.timing.Plan.measure);assert source.count('ui if key!=13 else 2')==1
 source=textwrap.dedent(source.replace('ui if key!=13 else 2','ui'));ns=dict(vars(native.timing));exec(compile(source,str(e/'body-return-measure.py'),'exec'),ns);Plan.measure=ns['measure'];(e/'body-return-measure.py').write_text(source)
 n=Plan(e,report,1,0);n.cost_profile=True;n.boot();n.typed('public_plain','syntax plain');n.memory('actual_plain','se_render_caps',0)
 for width,mode in((60,1),(80,2)):
  data=native.fixture(width);wrapped=data.index(b'\r')+1;edge=data.index(b'\r',wrapped)+1;n.open('open_raw'+str(width),('RAW'+str(width)).encode());n.mode_to(mode)
  for tag,at,key in(('new-wrap',edge+5,81),('insert-CR',5,13)):
   ident=str(width)+'-'+tag;line=data[:at].count(b'\r')+1;column=at-(data.rfind(b'\r',0,at)+1);n.typed(ident+'-goto','goto '+str(line))
   if column:n.send(ident+'-column',b'\x1d'*column)
   n.memory(ident+'-at','se_hot_caret',at,3);changed=data[:at]+bytes((key,))+data[at:];branch=2 if geometry and tag=='new-wrap'else None
   n.measure(ident+'-insert',changed,mode,key=key,category='geometry-'+tag);n.measurements[-1].update(caps=0,branch=branch,expected_caret=at+1)
   n.measure(ident+'-back',data,mode,key=20,category='geometry-delete-'+tag);n.measurements[-1].update(caps=0,branch=branch,expected_caret=at)
 return n

def run(source,geometry):
 original=(native.Plan,native.scenario,native.caret.free_ports,native.capacity.run_owned_plan);native.Plan=Plan;native.scenario=lambda e:scenario(e,geometry);native.caret.free_ports=row.free_ports
 native.capacity.run_owned_plan=lambda plan,out,timeout=900:run_with_closed_links(original[3],plan,out,timeout)
 try:return native.execute(source=source,require_fast=geometry)
 finally:native.Plan,native.scenario,native.caret.free_ports,native.capacity.run_owned_plan=original

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,default=BASE);p.add_argument('--geometry',action='store_true');a=p.parse_args();run(a.fixture.resolve(),a.geometry)
