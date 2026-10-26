"""Registered NR input-template typing check in60/80-column Plain modes.

The released native typing/source/pixel/catalog/shim and parser-bypass oracles
are unchanged. Timing retains its explicit public-input PC/SP stopwatch seam.
Owns8500/text8600..8639; only the closed output copy uses verified hardlinks.
"""
from pathlib import Path
import argparse,json
import test_grid_raw_typing_vice as native
import test_normal_row80_vice as ports
from closed_runtime_copy import run_with_closed_links

class Plan(ports.Plan):
 pass

def scenario(e):
 report=json.loads((e/'editor-report.json').read_text())
 assert report['symbols']['se_presentation_default']==3
 n=Plan(e,report,1,0);n.cost_profile=True;n.boot()
 n.typed('public_plain','syntax plain');n.memory('actual_plain','se_render_caps',0)
 for width,mode in ((60,1),(80,2)):
  data=native.fixture(width);at=5
  n.open('open_'+str(width),('RAW'+str(width)).encode());n.mode_to(mode)
  n.typed('goto_'+str(width),'goto 1');n.send('column_'+str(width),b'\x1d'*at)
  n.memory('caret_'+str(width),'se_hot_caret',at,3)
  changed=data[:at]+b' '+data[at:]
  for tag,key,text,caret in [('insert',32,changed,at+1),('back',20,data,at)]:
   n.measure(str(width)+'-short-'+tag,text,mode,key=key,category='NR-input-template')
   n.measurements[-1].update(caps=0,branch=1,expected_caret=caret)
 return n

def run(fixture):
 identity=json.loads((fixture/'freeze.json').read_text())
 assert identity['assets']['grid']=='fb3e6a86c658bb5bc345167403e4b9137a94a47d12faefeae26e8a84ed629c3b'
 original=(native.Plan,native.scenario,native.caret.free_ports,native.capacity.run_owned_plan)
 native.Plan=Plan;native.scenario=scenario;native.caret.free_ports=ports.free_ports
 native.capacity.run_owned_plan=lambda plan,out,timeout=900:run_with_closed_links(original[3],plan,out,timeout)
 try:return native.execute(source=fixture,require_fast=True)
 finally:native.Plan,native.scenario,native.caret.free_ports,native.capacity.run_owned_plan=original

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();run(a.fixture.resolve())
