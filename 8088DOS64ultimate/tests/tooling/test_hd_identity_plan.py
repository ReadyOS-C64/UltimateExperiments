from pathlib import Path
import sys,json,unittest,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build_support'))
from hd_identity_plan import plan
class ShadowIdentityPlan(unittest.TestCase):
 def test_uses_full_source_window_and_copied_run_address_excluding_vectors(self):
  p=Path('build/dos64');prg=p.with_suffix('.prg').read_bytes();memory=json.loads(p.with_suffix('.memory.json').read_text());record=plan(prg,p.with_suffix('.labels').read_text(),memory);s=record['shadow']
  self.assertEqual((s['source_start'],s['capture_run_start'],s['bytes']),(0xa000,0xf000,3584));self.assertEqual(s['expected_window_sha256'],hashlib.sha256(prg[0xa000-0x801+2:0xae00-0x801+2]).hexdigest());self.assertEqual(s['excluded_vectors'],{'start':0xfe00,'bytes':512});self.assertEqual(s['loaded_guard_required'],0xa5);self.assertEqual(s['normalizations'],[]);self.assertEqual(record['capture_required_bytes'],65536)
 def test_rejects_unverified_incomplete_or_changed_layout(self):
  p=Path('build/dos64');prg=p.with_suffix('.prg').read_bytes();labels=p.with_suffix('.labels').read_text();memory=json.loads(p.with_suffix('.memory.json').read_text());memory['passed']=False
  with self.assertRaises(ValueError):plan(prg,labels,memory)
  memory['passed']=True
  with self.assertRaises(ValueError):plan(prg[:-1],labels,memory)
  memory['load']['shadow']['source']=0x9800
  with self.assertRaises(ValueError):plan(prg,labels,memory)
if __name__=='__main__':unittest.main()
