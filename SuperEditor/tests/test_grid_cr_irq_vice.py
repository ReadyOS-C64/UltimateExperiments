"""Real IRQ Return/Undo/Redo/BACK on actual registered cold60 in60/80.

Only File/Open and native input queue/IRQ transport; no PC/SP/source substitution.
Own binary8100/text8200..8239. Complete inherited source/history/settings/fonts/
all60 catalog/shim/independent VIC oracle and byte-identical read-only D81.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,socket
import test_grid_terminal_registered_vice as terminal
from test_grid_cr_registered import authenticate

ROOT=terminal.ROOT
SOURCE=terminal.SOURCE
NAME=terminal.NAME

class Plan(terminal.Plan):
 def plan(self):
  p=super().plan();p['global_defaults']['monitor_port_start']=8100
  p['global_defaults']['monitor_port_span']=1
  assert not p['global_defaults'].get('kill_stale',False)
  return p

def free_ports():
 for port in (8100,*range(8200,8240)):
  with socket.socket()as s:
   s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('127.0.0.1',port))

def freeze(fixture):
 seal=authenticate(fixture)
 e=terminal.engine.folds.freeze(fixture,seal['resident'],seal['D81'])
 target=ROOT/'agentsworking/evidence/M8'/e.name.replace('geos-fold-native','grid-cr-irq-native')
 shutil.move(e,target);e=target
 (e/'term.bin').write_bytes(SOURCE)
 p=terminal.subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'term.bin'),'term,s'],capture_output=True)
 (e/'term-package.log').write_bytes(p.stdout+p.stderr);assert not p.returncode
 assert terminal.D81Image((e/'working.d81').read_bytes()).read(NAME,kind=1).data==SOURCE
 shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')
 (e/'irq-seal.json').write_text(json.dumps(dict(identity=seal,ports=[8100,8200,8239],scope=__doc__),indent=2)+'\n')
 return e

def scenario(e):
 n=Plan(e,json.loads((e/'editor-report.json').read_text()),'gallery')
 n.boot();n.typed('public_plain','syntax plain');n.memory('actual_plain','se_render_caps',0)
 at=SOURCE.index(b'\r');changed=SOURCE[:at]+b'\r'+SOURCE[at:]
 for mode in (1,2):
  tag=str(mode);n.open('open_'+tag,NAME);n.switch('mode_'+tag,mode)
  n.typed('goto_'+tag,'goto 1');n.typed('end_'+tag,'end')
  n.memory('terminal_position_'+tag,'se_hot_caret',at,3)
  n.send('actual_return_'+tag,b'\r');n.send('flush_left_'+tag,b'\x9d')
  n.shot('split-'+tag,changed,mode,caret=at,node=2,current=NAME)
  n.send('actual_undo_'+tag,b'\x1a');n.shot('undo-'+tag,SOURCE,mode,caret=at,current=NAME)
  n.send('actual_redo_'+tag,b'\x19');n.shot('redo-'+tag,changed,mode,caret=at+1,node=2,current=NAME)
  n.send('immediate_back_merge_'+tag,b'\x14');n.shot('merge-'+tag,SOURCE,mode,caret=at,pending=1,node=2,current=NAME)
  # Commit/Undo the pending merge, then Undo the original Return via public
  # input. Reopening the next width must begin from saved history node1.
  n.send('cleanup_undo_merge_'+tag,b'\x1a')
  n.send('cleanup_undo_split_'+tag,b'\x1a')
  n.memory('cleanup_saved_node_'+tag,'se_h_current',1,4)
  n.memory('cleanup_clean_'+tag,'se_h_dirty',0)
 return n

def run(fixture):
 old=(terminal.ports.free_ports,terminal.freeze,terminal.scenario,terminal.evaluate)
 terminal.ports.free_ports=free_ports;terminal.freeze=freeze;terminal.scenario=scenario;terminal.evaluate=evaluate
 # terminal.run uses its own evaluator symbol; keep its original captured here
 # so the wrapper adds scope/count without recursively replacing that function.
 try:return terminal.run(fixture)
 finally:terminal.ports.free_ports,terminal.freeze,terminal.scenario,terminal.evaluate=old

ORIGINAL_EVALUATE=terminal.evaluate

def evaluate(e):
 result=ORIGINAL_EVALUATE(e);result['scope']=__doc__;assert len(result['frames'])==8
 (e/'gallery/irq-result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path);p.add_argument('--verify',type=Path);a=p.parse_args()
 if a.verify:evaluate(a.verify.resolve())
 else:assert a.fixture;run(a.fixture.resolve())
