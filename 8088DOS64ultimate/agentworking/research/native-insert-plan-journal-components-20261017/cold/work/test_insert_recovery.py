"""Actual START/JG/RFW recovery of native PLAN-produced Insert journals.

Synthetic media and caller receipt; this does not execute the Insert controller
or DOS. The journals and CFG files are outputs of the real linked PLAN worker.
"""
from pathlib import Path
import json,time,unittest,zlib
from test_recovery_ui import Cold,G,L,SYMS
P=Path(__file__).resolve().parent
records=[]

def resign_cfg(b):
 b=bytearray(b);b[572:576]=zlib.crc32(b[:572]).to_bytes(4,'little');return bytes(b)

def resign_journal(b):
 b=bytearray(b);b[1280:1284]=zlib.crc32(b[:1280]).to_bytes(4,'little');return bytes(b)

class Tests(unittest.TestCase):
 def tearDown(self):
  if hasattr(self,'f'):self.f.close()
 def positive(self,case):
  f=self.f=Cold('insert-'+case)
  f.prompt();ports=tuple(L.dos64_peek(f.m,i)for i in [0,1]);f.confirm()
  f.advance(0xa000)
  self.assertEqual(bytes(L.dos64_peek(f.m,0xa000+i)for i in range(len(f.worker))),f.worker)
  f.cpu_guard(allow_install=True);L.dos64_clear_writes(f.m)
  r=f.advance(G['_jg_dispatch'])
  self.assertEqual(r.regs.a,0);self.assertEqual(L.dos64_peek(f.m,G['_jg_initialized']),0)
  self.assertEqual(bytes(L.dos64_peek(f.m,0x6000+i)for i in range(len(f.gate))),f.gate)
  j=f.original['DOS64.JRN']
  self.assertEqual(f.file('DOS64.CFG'),j[704:1280]);self.assertEqual(f.file('S0001.OLD'),j[128:704]);self.assertEqual(f.file('S0001.JRN'),j)
  for n in ['DOS64.JRN','DOS64.NEW','DOS64.OLD']:self.assertIsNone(f.file(n))
  self.assertEqual(f.file('SAVE0001.IMG'),f.original['SAVE0001.IMG']);self.assertEqual(L.bulk_model_open(f.m,1),0)
  f.advance('trampoline_start')
  self.assertEqual(f.read('_lc_result',3),b'\5\0\0');self.assertEqual(f.read('sp',2),b'\xff\xcf')
  for at in [0x3ff005,0x3ff505]:self.assertEqual(f.reu(at,1),b'\xa5')
  self.assertEqual(bytes(L.dos64_peek(f.m,0x6000+i)for i in range(len(f.asset))),f.asset)
  self.assertEqual(f.reu(0x380000,368640),f.before[0x380000:0x3da000]);self.assertEqual(f.reu(0x3f4000,0x4000),f.before[0x3f4000:0x3f8000])
  self.assertEqual(tuple(L.dos64_peek(f.m,i)for i in [0,1]),ports);self.assertEqual(L.bulk_model_open(f.m,1),0)
  f.cpu_guard()
  records.append({'case':case,'actual_SYS_JG_CIA_RFW_fresh_NONE_INO_handoff':True,'native_PLAN_output':True,'old_presence':j[128+525],'new_presence':j[704+525],'image_crc':int.from_bytes(j[54:58],'little'),'known_closed':True,'full_third_floppy_and_reserve_preserved':True,'scope':'synthetic caller receipt/media; no full Insert or DOS/physical claim'})
 def test01_first_B(self):self.positive('first_B')
 def test02_first_B_zero_CRC(self):self.positive('first_B_zero')
 def test03_ejected_A(self):self.positive('ejected_A')
 def test04_ejected_B(self):self.positive('ejected_B')
 def test05_existing_mounted_journal(self):self.positive('mounted_B')
 def negative(self,which):
  f=self.f=Cold('insert-first_B_zero'if which=='zero_crc_corruption'else'insert-first_B')
  j=bytearray(f.original['DOS64.JRN']);new=bytearray(j[704:1280])
  if which=='unrelated_C_path':new[392:520]=b'/usb1/Owned/OTHER.IMG'.ljust(128,b'\0')
  elif which=='missing_new_B':
   new[524]&=~2;new[525]&=~2;new[264:392]=bytes(128);new[532:536]=bytes(4)
  elif which=='null_previously_configured_B':
   old=bytearray(j[128:704]);old[525]|=2;old[264:392]=b'/sd/Media/B.IMG'.ljust(128,b'\0');old[532:536]=(0x12345678).to_bytes(4,'little');old=resign_cfg(old);j[128:704]=old;f.seedfile('DOS64.CFG',old)
  else:
   b=bytearray(f.original['SAVE0001.IMG']);b[-1]^=1;f.seedfile('SAVE0001.IMG',bytes(b))
  new=resign_cfg(new);j[704:1280]=new;j=resign_journal(j);f.seedfile('DOS64.JRN',j);f.seedfile('DOS64.NEW',new)
  before={n:f.file(n)for n in f.original};f.run(SYMS['sf_entry_idle'],1_300_000_000)
  self.assertEqual(L.dos64_peek(f.m,SYMS['_sf_status']),3);self.assertEqual(f.read('_lc_result',1),b'\3')
  self.assertEqual(L.dos64_peek(f.m,G['_jg_state_observed']),3);self.assertEqual(L.dos64_peek(f.m,G['_jg_error_observed']),4 if which=='zero_crc_corruption'else 2)
  for n,b in before.items():self.assertEqual(f.file(n),b)
  for n in ['S0001.OLD','S0001.JRN']:self.assertIsNone(f.file(n))
  for at in [0x3da005,0x3ff005,0x3ff505]:self.assertEqual(f.reu(at,1),b'\0')
  self.assertEqual(L.bulk_model_open(f.m,1),0);self.assertEqual(bytes(L.dos64_peek(f.m,0xa000+i)for i in range(32)),bytes(32))
  records.append({'negative':which,'actual_SYS_JG_refusal':True,'no_RFW_entry_or_persistent_mutation':True,'known_closed':True})
 def test06_forbidden_unrelated_change(self):self.negative('unrelated_C_path')
 def test07_new_selected_must_be_present(self):self.negative('missing_new_B')
 def test08_null_descriptor_not_previously_configured(self):self.negative('null_previously_configured_B')
 def test09_zero_CRC_is_verified(self):self.negative('zero_crc_corruption')

if __name__=='__main__':
 start=time.monotonic();r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 (P/'INSERT_RECOVERY_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'seconds':time.monotonic()-start,'records':records},indent=2)+'\n')
 raise SystemExit(not r.wasSuccessful())
