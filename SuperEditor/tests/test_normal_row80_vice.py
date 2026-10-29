"""Private R16 normal-row PAL A/B after public syntax-Plain setup.

Actual current59 Full-default products; no cold-Plain/unverified-dependency claim.
Released native typing evaluator/source/pixel/attribute/shim checks are unchanged.
Stopwatch retains its explicit instruction-entry PC/SP/public-input seam.
"""
from pathlib import Path
import argparse,json,socket
import test_grid_raw_typing_vice as native
ROOT=native.ROOT
BASE=ROOT/'build/capture-lexical-integrated/20261026T190219265642Z/fixture'
CANDIDATE=ROOT/'build/normal-row80-unrolled2/fixture'
PORT=8500

class Plan(native.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=PORT;p['global_defaults']['monitor_port_span']=1;return p

def free_ports():
 for port in(PORT,*range(PORT+100,PORT+140)):
  with socket.socket()as sock:
   sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sock.bind(('127.0.0.1',port))

def scenario(e):
 report=json.loads((e/'editor-report.json').read_text());assert report['symbols']['se_presentation_default']==3
 n=Plan(e,report,1,0);n.cost_profile=True;n.boot();n.typed('public_plain','syntax plain');n.memory('actual_plain','se_render_caps',0)
 width=80;data=native.fixture(width);wrapped=data.index(b'\r')+1;n.open('open_raw80',b'RAW80');n.mode_to(2)
 for tag,at,key,branch in(('short-space',5,32,1),('wrapped-quote',wrapped+width+5,34,2)):
  ident='80-'+tag;line=data[:at].count(b'\r')+1;column=at-(data.rfind(b'\r',0,at)+1)
  n.typed(ident+'-goto','goto '+str(line))
  if column:n.send(ident+'-column',b'\x1d'*column)
  n.memory(ident+'-at','se_hot_caret',at,3);changed=data[:at]+bytes((key,))+data[at:]
  n.measure(ident+'-insert',changed,2,key=key,category='normal-row-'+tag);n.measurements[-1].update(caps=0,branch=branch,expected_caret=at+1)
  n.measure(ident+'-back',data,2,key=20,category='normal-row-delete-'+tag);n.measurements[-1].update(caps=0,branch=branch,expected_caret=at)
 return n

def run(source):
 original=(native.Plan,native.scenario,native.caret.free_ports)
 native.Plan=Plan;native.scenario=scenario;native.caret.free_ports=free_ports
 try:return native.execute(source=source,require_fast=True)
 finally:native.Plan,native.scenario,native.caret.free_ports=original

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--candidate',action='store_true');p.add_argument('--source',type=Path);a=p.parse_args();run(a.source.resolve()if a.source else CANDIDATE if a.candidate else BASE)
