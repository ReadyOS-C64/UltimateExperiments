from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-coldentry-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import unittest
from cold_entry import ColdEntry
class Tests(unittest.TestCase):
 def lane(self):
  b=(P.parent/'predecessor-terminal-RAM.bin').read_bytes();return ColdEntry((P.parent/'ACTIVE-predecessor.json').read_bytes(),b,(P.parent/'predecessor-stream.prg').read_bytes()),b
 def test_exact_retained_owned_stream_only(self):
  a,b=self.lane();self.assertEqual(a.admit(b)['cold_entry'],'EXACT_OWNED_FAILED_READONLY_STREAM')
 def test_mutated_code_header_nonce_and_unknown_MAIN_refused(self):
  a,b=self.lane()
  for i in [0x801,0x1000,0x3e08,0x3e18,0x3e30]:
   c=bytearray(b);c[i]^=1
   with self.assertRaises(ValueError):a.admit(bytes(c))
  with self.assertRaises(ValueError):a.admit(bytes(65536))
 def test_historical_predecessor_cannot_be_substituted(self):
  a,b=self.lane()
  with self.assertRaises(ValueError):ColdEntry((P.parent/'ACTIVE-predecessor.json').read_bytes()+b' ',b,(P.parent/'predecessor-stream.prg').read_bytes())
if __name__=='__main__':unittest.main(verbosity=2)
