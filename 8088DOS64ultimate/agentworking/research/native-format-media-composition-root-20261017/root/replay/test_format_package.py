from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;assert Path.cwd()==P
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-format-host');assert not Path(sys.pycache_prefix).exists()
import unittest,importlib.util,struct,zlib,json,tempfile
W=P/'runtime/work';B=W/'build'
def module(n,p):s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
pack=module('actual_pack',W/'build_support/overlay_package.py');mem=module('actual_map',W/'build_support/verify_memory.py')
labels=(B/'dos64.labels').read_text();maptext=(B/'dos64.map').read_text();prg=(B/'dos64.prg').read_bytes()
payloads={k:(B/('dos64-resident.prg.'+v+'.bin')).read_bytes()for k,v in [('FILECODE','files'),('RENDERCODE','render'),('INPUTCODE','input'),('IRQMAIN','pit'),('GFXCODE','gfx'),('HDCODE','hd'),('DISKCODE','disk')]}
cold=(B/'dos64-resident.prg.import.bin').read_bytes();shadow=(B/'dos64-resident.prg.hdb.bin').read_bytes();saver=(B/'dos64-resident.prg.saver.bin').read_bytes();fmt=(B/'dos64-resident.prg.format.bin').read_bytes()
def verify(data=prg,l=labels,p=fmt):return mem.verify(maptext,l,data,payloads,cold,shadow,saver,p)
class Test(unittest.TestCase):
 def test_exact_actual_runtime_schema_and_package(self):
  r=verify();self.assertTrue(r['passed'],r['errors']);self.assertEqual(r['load']['format']['padding'],26);self.assertEqual(len(pack.slot(fmt,8)),2048)
 def test_ninth_managed_selector_header_and_unknown_ID(self):
  b=pack.slot(fmt,8);self.assertEqual(b[:6],b'D64O\1\10');self.assertEqual(b[12:16],b'FMT ')
  for n in [0,9,255]:
   with self.assertRaises(ValueError):pack.slot(fmt,n)
 def test_format_bad_placement_and_wrong_length(self):
  for l in [labels.replace('al 00C900 .__FORMATCODE_RUN__','al 00C901 .__FORMATCODE_RUN__'),labels.replace('al 0002AF .__FORMATCODE_SIZE__','al 0002AE .__FORMATCODE_SIZE__')]:
   self.assertNotEqual(l,labels)
   with self.assertRaises(ValueError):pack.validate_variant(fmt,l,'FORMAT',('FORMATCODE',))
 def test_TEXT_canonical_prefix_and_checker_count(self):
  render=payloads['RENDERCODE'];pack.validate_text(render,labels)
  for body in [render[:-1],render+bytes(1),render[:1248]]:
   with self.assertRaises(ValueError):pack.validate_text(body,labels)
 def test_nested_header_body_padding_and_independent_expected_CRC(self):
  meta=json.loads((B/'dos64-overlay-package.json').read_text())['format'];start=0x9000-0x801+2+meta['nested_slot_offset'];crc=meta['resident_crc_address']-0x801+2
  for at in [start,start+16,0x9800-0x801+1,crc]:
   b=bytearray(prg);b[at]^=1;r=verify(bytes(b));self.assertFalse(r['passed'],hex(at))
 def test_missing_linked_payload_or_checker_binds_pair(self):
  self.assertFalse(verify(p=None)['passed']);l=labels.replace('al 00009E .__FORMATCHECKCODE_SIZE__','al 00009F .__FORMATCHECKCODE_SIZE__');self.assertNotEqual(l,labels);self.assertFalse(verify(l=l)['passed'])
if __name__=='__main__':
 r=unittest.main(exit=False,verbosity=2).result;(P/'FORMAT_HOST_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun},indent=2)+'\n');sys.exit(not r.wasSuccessful())
