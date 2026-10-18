"""Negative contracts for new linked variants and disposable unit helpers."""
from pathlib import Path
import re,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build_support'))
from verify_memory import verify
class FiveOverlayContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.mp=Path('build/dos64-tests.map').read_text();cls.labels=Path('build/dos64-tests.labels').read_text();cls.prg=Path('build/dos64-tests.prg').read_bytes()
 def check(self,mp=None,labels=None):return verify(self.mp if mp is None else mp,self.labels if labels is None else labels,self.prg,shadow_payload=Path("build/dos64-tests-resident.prg.hdb.bin").read_bytes())
 def change(self,name):
  changed=re.sub(r'^(al )([0-9A-F]+)( \.'+name+r')$',lambda m:m[1]+f'{int(m[2],16)+1:06X}'+m[3],self.labels,flags=re.M)
  self.assertNotEqual(changed,self.labels);return changed
 def test_each_pit_member_is_required(self):
  for name in ('IRQMAIN','IRQDEVICE','PITCODE'):
   changed=re.sub('^'+name+r'\s.*\n','',self.mp,flags=re.M);self.assertNotEqual(changed,self.mp);self.assertFalse(self.check(mp=changed)['passed'])
 def test_each_variant_member_metadata_is_exact(self):
  for member in ('IRQMAIN','IRQDEVICE','PITCODE','GFXCODE','UNITCOLD'):
   for suffix in ('LOAD','RUN','SIZE'):self.assertFalse(self.check(labels=self.change('__'+member+'_'+suffix+'__'))['passed'])
 def test_unit_return_cannot_move_into_disposable_region(self):
  changed=re.sub(r'^(al )[0-9A-F]+( \.fixture_return)$',r'\g<1>007E00\g<2>',self.labels,flags=re.M)
  self.assertNotEqual(changed,self.labels);self.assertFalse(self.check(labels=changed)['passed'])
 def test_pit_and_gfx_window_metadata_is_required(self):
  for area in ('PIT','GFX'):
   for suffix in ('START','SIZE','FILEOFFS','LAST'):self.assertFalse(self.check(labels=self.change('__'+area+'_'+suffix+'__'))['passed'])
if __name__=='__main__':unittest.main()
