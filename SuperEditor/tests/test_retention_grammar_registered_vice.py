"""Native incomplete-region recovery on the combined registered59 product.

The existing real-input scenario and pixel/history/whole-REU evaluator remain
unchanged. This wrapper authenticates the additional production render/lexical
changes against their committed fixture and owns8500/text8600..8639.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,socket
import test_retention_grammar_vice as native
from test_grid_geometry_current import authenticate

ROOT=native.ROOT
BASE=ROOT/'build/geometry-committed/20261026T202241625056Z/fixture'

class Plan(native.Plan):
 def plan(self):
  result=super().plan()
  result['global_defaults']['monitor_port_start']=8500
  return result

def free_ports():
 for port in (8500,*range(8600,8640)):
  with socket.socket()as s:
   s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
   s.bind(('127.0.0.1',port))

def freeze(fixture,baseline):
 seal=authenticate(baseline)
 old=json.loads((baseline/'freeze.json').read_text())
 current=json.loads((fixture/'freeze.json').read_text())
 assert current['names']==old['names'] and current['prg_sha256']==old['prg_sha256']
 assert {n for n in old['assets']if old['assets'][n]!=current['assets'][n]}=={'foldctl'}
 assert current['assets']['foldctl']==native.C19
 assert (fixture/'build/overlays/foldctl.bin').read_bytes()==(fixture/'build/overlays/foldctl.seo').read_bytes()[36:]
 assert {n for n in old['sources']if old['sources'][n]!=current['sources'][n]}=={'src/editor_fold/coordinator.s'}
 assert hashlib.sha256((fixture/'build/supereditor.d81').read_bytes()).hexdigest()==current['disk_sha256']
 # The original freezer checks these exact identities and freezes every actual
 # registered image/font. Only the policy for its initial baseline is replaced.
 original=native.grammar.BASE
 native.grammar.BASE=baseline
 try:e=native.freeze(fixture)
 finally:native.grammar.BASE=original
 target=e.with_name(e.name.replace('retention-grammar-native','retention-grammar-registered-native'))
 shutil.move(e,target)
 (target/'registered-seal.json').write_text(json.dumps(dict(baseline=seal,candidate=current['disk_sha256'],scope=__doc__),indent=2)+'\n')
 return target

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--fixture',type=Path)
 p.add_argument('--baseline',type=Path,default=BASE)
 p.add_argument('--verify',type=Path)
 a=p.parse_args()
 native.Plan=Plan
 native.free_ports=free_ports
 if a.verify:native.evaluate(a.verify.resolve())
 else:
  assert a.fixture
  free_ports()
  e=freeze(a.fixture.resolve(),a.baseline.resolve())
  print('REGISTERED_NATIVE',e,flush=True)
  native.execute(e)
