from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P.parent/'.absent-relocation-import');assert not Path(sys.pycache_prefix).exists()
import unittest,ctypes as C,struct,zlib,json
from config_fixture import F,L,cfg,REPORT
from test_config_ui import UI
class Moved(UI):
 def __init__(self,old=b'/Home',selected=b'/Moved installation',paths=None,**kw):
  super().__init__(**kw);self.selected=selected;self.old=old
  self.directory(b'/',[(16,selected[1:]),(16,b'Release'),(16,b'New launch')]);self.directory(selected,[])
  b=bytearray(cfg(old))
  if paths is None:paths=[old+b'/A.IMG',old+b'/B.IMG',old+b'/C.IMG']
  for at,p in zip([136,264,392],paths):b[at:at+128]=p.ljust(128,b'\0')
  struct.pack_into('<I',b,572,zlib.crc32(b[:572]));self.original=bytes(b)
  L.bulk_model_seed(self.f.m,selected+b'/DOS64.CFG',self.original,576)
 def moved(self):
  assert self.begin()==1;assert self.ready()==2;self.key(0,1);return self.key(0,4)
 def accept(self):return self.key(3,1)
 def ri(self):
  f=self.f;f.write('_ri_query_home',self.selected.ljust(128,b'\0'));f.write('_ri_query_session',f.read('_ri_result',8)[6:8]);assert f.call('_ri_get')==1;return f.read('_ri_receipt',710)
class Relocation(unittest.TestCase):
 def make(self,**kw):u=Moved(**kw);self.addCleanup(u.close);return u
 def test_explicit_CIA_confirm_native_derive_and_original_unchanged(self):
  u=self.make();f=u.f;self.assertEqual(u.moved(),8);self.assertEqual(f.call('_ri_state'),4);self.assertEqual(f.call('_ri_get'),0);self.assertEqual(f.call('_cg_get'),0);before=f.commands()
  self.assertEqual(u.key(0,1),8)
  f.write('_ri_receipt',bytes([0x55])*710);f.write('_ri_result',b'\2'+bytes(7));f.write('_cg_result',b'\6'+bytes(6)+b'\xa5')
  self.assertEqual(f.call('_ri_get'),0);self.assertEqual(f.call('_cg_get'),0)
  self.assertEqual(u.accept(),4);b=u.ri()[134:];want=bytearray(u.original)
  for at,p in [(8,u.selected),(136,u.selected+b'/A.IMG'),(264,u.selected+b'/B.IMG'),(392,u.selected+b'/C.IMG')]:want[at:at+128]=p.ljust(128,b'\0')
  struct.pack_into('<I',want,572,zlib.crc32(want[:572]));self.assertEqual(b,bytes(want));self.assertEqual(f.commands(),before);self.assertEqual(f.call('_ri_confirm'),0)
  out=C.create_string_buffer(576);self.assertEqual(L.bulk_model_read(f.m,u.selected+b'/DOS64.CFG',out,576),1);self.assertEqual(out.raw,u.original)
  self.assertEqual([L.bulk_model_open(f.m,t)for t in [1,2]],[0,0]);REPORT['derived']={'old':u.old.decode(),'selected':u.selected.decode(),'original_identity':zlib.crc32(u.original[:572]),'derived_identity':zlib.crc32(b[:572])}
 def test_case_fold_component_boundary_and_external_path(self):
  paths=[b'/hOmE/disks/A.IMG',b'/Home archive/B.IMG',b'/Shared/C.IMG'];u=self.make(paths=paths);self.assertEqual(u.moved(),8);self.assertEqual(u.accept(),4);b=u.ri()[134:]
  for at,w in zip([136,264,392],[u.selected+b'/disks/A.IMG',paths[1],paths[2]]):self.assertEqual(b[at:at+128].split(b'\0')[0],w)
 def test_decline_STOP_has_no_derive_or_media_or_publication(self):
  u=self.make();self.assertEqual(u.moved(),8);before=u.f.commands();self.assertEqual(u.key(7,7),7);self.assertEqual(u.f.call('_cg_error'),5);self.assertEqual(u.f.call('_ri_state'),3);self.assertEqual(u.f.call('_ri_confirm'),0);self.assertEqual(u.f.call('_ri_get'),0);self.assertEqual(u.f.commands(),before);self.assertEqual(u.f.call('_cg_closed_quiet'),1)
 def test_clock_fault_cannot_be_laundered_through_public_pending(self):
  u=self.make();self.assertEqual(u.moved(),8);before=u.f.commands();L.dos64_cia_clock_step(u.f.m,0x40000);u.poll();self.assertEqual(u.state,7);self.assertEqual(u.f.call('_ri_error'),7);u.f.write('_ri_result',b'\4'+bytes(7));self.assertEqual(u.f.call('_ri_confirm'),0);self.assertEqual(u.f.commands(),before)
 def test_overflow_fails_before_any_media_or_write(self):
  u=self.make(selected=b'/'+b'L'*100,paths=[b'/Home/'+b'A'*40,b'/Home/B.IMG',b'/Home/C.IMG']);self.assertEqual(u.moved(),8);before=u.f.commands();self.assertEqual(u.accept(),7);self.assertEqual(u.f.call('_ri_error'),4);self.assertEqual(u.f.commands(),before);self.assertEqual(u.f.call('_ri_get'),0)
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Relocation));(P.parent/'RELOCATION_TEST_REPORT.json').write_text(json.dumps({'tests':r.testsRun,'passed':r.wasSuccessful(),'native':REPORT},indent=2)+'\n');sys.exit(not r.wasSuccessful())
