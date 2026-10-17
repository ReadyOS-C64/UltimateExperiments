from pathlib import Path
import sys,os
W=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(W/('.absent-large-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import unittest,json,hashlib
from large_load_only import RegisteredLoadOnly
from bound_release import BoundRelease,Release16Protocol,NAMES
from protocol import Source
from stage_model import Clock,StageModel
from cold_session import native_contract
class Tests(unittest.TestCase):
 def fixture(self,leaf='SETUP.PRG'):
  c=Clock();raw=(W.parent/'STAGING_INVENTORY.json').read_bytes();release=BoundRelease(raw,hashlib.sha256(raw).hexdigest(),{n:(W.parent/'assets'/n).read_bytes()for n in NAMES});source=Source((W/'stager.prg').read_bytes(),(W/'stager.labels').read_text(),b'/usb1/DOS64_TEST/release16-load-model');assets=release.assets(source.home,b'1'*16)
  # Explicit host observation fixture, not a new actual-native receipt.
  p=Release16Protocol(None,source,clock=c);p.sequence=380;p.records=[{'op':0}for _ in range(379)];terminal=bytearray(65536);terminal[source.low:source.high]=source.body
  for a,v in source.port_words.items():terminal[a:a+2]=v.to_bytes(2,'little')
  for a in source.dynamic:terminal[a:a+2]=b'\xff\xff'
  r=memoryview(terminal)[0x2a0:0x2e0];r[:4]=b'AST1';r[4]=0xa5;r[6:8]=(380).to_bytes(2,'little');r[9]=3;r[32]=1;r[34]=9;p.records.append({'op':10,'result':bytes(r).hex()})
  # Source-backed conservative BASIC observer fields, no target mutation.
  ram=bytearray(65536);ram[0x801:0x801+len(assets[leaf])-2]=assets[leaf][2:];ram[0x288]=4;ram[0x289]=10;ram[0xd6]=5;ram[0xd3]=0;ram[0xd1:0xd3]=(0x400+200).to_bytes(2,'little');ram[0x400+160:0x400+200]=bytes([18,5,1,4,25,46])+b' '*34;ram[0x400+200:0x400+240]=b' '*40
  events=[];calls=[];fail=[None];reads=[0]
  def api(m,route,end):
   calls.append((m,route,end))
   if fail[0]is not None:raise fail[0]
   return {'errors':[]}
  def read(end):reads[0]+=1;ram[0xa0:0xa3]=reads[0].to_bytes(3,'big');return bytes(ram)
  g=RegisteredLoadOnly(p,release,assets,bytes(terminal),leaf,api=api,read_ram=read,record=events.append,clock=c,sleep=c.sleep)
  return g,c,ram,calls,events,fail,p,release,assets,terminal
 def test_both_large_product_roles_visible_only_noSYS(self):
  for leaf in ['SETUP.PRG','CONFIG.PRG']:
   g,c,ram,calls,events,fail,*_=self.fixture(leaf);r=g.run(600);self.assertFalse(r['hidden_preSYS_verified']);self.assertFalse(r['SYS_emitted']);self.assertTrue(r['paired_BASIC_READY']);self.assertEqual(sum('load_prg' in x[1]for x in calls),1);self.assertFalse(any('writemem'in x[1]or'run_prg?'in x[1]for x in calls))
 def test_ambiguousLOAD_exactfirst_no_second_request(self):
  g,c,ram,calls,events,fail,*_=self.fixture();e=ConnectionResetError(54,'reset');fail[0]=e
  with self.assertRaises(ConnectionResetError)as got:g.run(600)
  self.assertIs(got.exception,e)
  with self.assertRaises(ValueError):g.run(600)
  self.assertEqual(len(calls),1)
 def test_badvisible_source_refuses_withoutSYS(self):
  g,c,ram,calls,events,fail,*_=self.fixture();ram[0x900]^=1
  with self.assertRaises(ValueError):g.run(600)
  self.assertFalse(any('writemem'in x[1]for x in calls))
 def test_hidden_difference_never_claimed_verified(self):
  g,c,ram,calls,events,fail,*_=self.fixture();ram[0xa000]^=1;self.assertFalse(g.run(600)['hidden_preSYS_verified'])
 def test_unknown_stop_and_public_receipt_refused(self):
  g,c,ram,calls,events,fail,p,release,assets,terminal=self.fixture();terminal[0x2a0+31]=2
  with self.assertRaises(ValueError):RegisteredLoadOnly(p,release,assets,bytes(terminal),'SETUP.PRG',api=lambda *a:None,read_ram=lambda *a:None,record=lambda *a:None)
  with self.assertRaises(ValueError):RegisteredLoadOnly({'closed':True},release,assets,bytes(terminal),'SETUP.PRG',api=lambda *a:None,read_ram=lambda *a:None,record=lambda *a:None)
 def test_record_failure_precedes_LOAD(self):
  g,c,ram,calls,events,fail,*_=self.fixture();e=OSError('retention')
  def record(v):raise e
  g.record=record
  with self.assertRaises(OSError)as got:g.run(600)
  self.assertIs(got.exception,e);self.assertEqual(calls,[])
if __name__=='__main__':unittest.main(verbosity=2)
