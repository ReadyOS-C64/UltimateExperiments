from pathlib import Path
import sys,os
sys.dont_write_bytecode=True;sys.pycache_prefix=str(Path.cwd()/('.absent-sequential-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import unittest,json,hashlib
from test_online_save import Machine,L,symbols,A,HD
P=Path.cwd();receipts=[]
class Sequential(unittest.TestCase):
 def scenario(self,mid):
  m=Machine()
  try:
   before=m.get('dos64_files_state_start',25);m.call('dos64_native_tick',2000000)
   if mid:
    for i in range(5000):
     if m.g('dos64_export_phase')==3:break
     m.call('dos64_native_tick',200000)
    self.assertEqual(m.g('dos64_export_phase'),3)
   m.p(symbols['dos64_native_diag']+3,9)
   for i in range(5000):
    if not m.g('sav_borrowed'):break
    m.call('dos64_native_tick',200000)
   self.assertEqual(m.g('sav_borrowed'),0);self.assertEqual(m.g('dos64_native_diag'),5);self.assertEqual(m.g('dos64_export_cancel'),1);self.assertEqual(m.get('dos64_files_state_start',25),before)
   second=b'/usb1/Owned/SECOND-MID.IMG'if mid else b'/usb1/Owned/SECOND-EARLY.IMG';m.path=second;m.p('dos64_export_path_len',len(second)+1);m.put('dos64_export_path',second+b'\0');m.p(symbols['dos64_native_diag']+3,7);m.call('dos64_native_tick',2000000)
   admitted=m.g('sav_borrowed');self.assertEqual(admitted,1)
   for i in range(250000):
    if not m.g('sav_borrowed'):break
    m.call('dos64_native_tick',200000)
   receipt={'first_cancel':'mid-write'if mid else'safety-close','second_admitted':admitted,'second_polls':i,'second_ack':m.g(symbols['dos64_native_diag']+4),'second_stage':m.g('dos64_native_diag'),'cancel':m.g('dos64_export_cancel'),'verified':m.g('dos64_export_verified'),'size':L.bulk_model_size(m.m,second),'context_pending':m.g('sav_context_pending'),'C_online':m.g('hdb_online'),'C_handle_open':L.bulk_model_open(m.m,2),'C_position':L.save_model_position(m.m,2),'C_context_equal':m.get('dos64_files_state_start',25)==before,'wire_commands':L.bulk_model_commands(m.m)};receipts.append(receipt)
   self.assertEqual(receipt['second_ack'],0xa5);self.assertEqual(receipt['verified'],1);self.assertEqual(receipt['size'],len(A));self.assertEqual(m.bytes(second,len(A)),A);self.assertEqual(m.bytes(b'/usb1/Owned/C.IMG',len(HD)),HD);self.assertTrue(receipt['C_context_equal']);self.assertEqual(receipt['C_position'],12345)
  finally:m.close()
 def test_01_safety_close_cancel_then_fresh_save(self):self.scenario(False)
 def test_02_mid_write_cancel_then_fresh_save(self):self.scenario(True)
 def test_03_new_cancel_after_second_admission_is_preserved(self):
  m=Machine()
  try:
   before=m.get('dos64_files_state_start',25)
   for name in [b'/usb1/Owned/FIRST-CANCEL.IMG',b'/usb1/Owned/SECOND-CANCEL.IMG']:
    m.path=name;m.p('dos64_export_path_len',len(name)+1);m.put('dos64_export_path',name+b'\0');m.p(symbols['dos64_native_diag']+3,7);m.call('dos64_native_tick',2000000);self.assertEqual(m.g('dos64_export_cancel'),0);m.p(symbols['dos64_native_diag']+3,9)
    for count in range(1000):
     if not m.g('sav_borrowed'):break
     m.call('dos64_native_tick',200000)
    self.assertEqual(m.g('dos64_export_cancel'),1);self.assertEqual(m.g(symbols['dos64_native_diag']+4),0xe1);self.assertEqual(L.bulk_model_size(m.m,name),0xffffffff);self.assertEqual(m.get('dos64_files_state_start',25),before)
   name=b'/usb1/Owned/THIRD-SUCCESS.IMG';m.path=name;m.p('dos64_export_path_len',len(name)+1);m.put('dos64_export_path',name+b'\0');m.p(symbols['dos64_native_diag']+3,7);m.call('dos64_native_tick',2000000);self.assertEqual(m.g('dos64_export_cancel'),0)
   for count in range(250000):
    if not m.g('sav_borrowed'):break
    m.call('dos64_native_tick',200000)
   self.assertEqual(m.g(symbols['dos64_native_diag']+4),0xa5);self.assertEqual(m.bytes(name,len(A)),A);self.assertEqual(m.get('dos64_files_state_start',25),before);self.assertEqual(L.save_model_position(m.m,2),12345);receipts.append({'case':'second-live-cancel-kept-third-success','polls':count,'verified':1,'C_context_equal':True})
  finally:m.close()
 def test_04_rejected_new_owner_does_not_clear_previous_cancel(self):
  m=Machine()
  try:
   m.call('dos64_native_tick',2000000);m.p(symbols['dos64_native_diag']+3,9)
   for count in range(1000):
    if not m.g('sav_borrowed'):break
    m.call('dos64_native_tick',200000)
   self.assertEqual(m.g('dos64_export_cancel'),1);before=m.get('dos64_files_state_start',25);commands=L.bulk_model_commands(m.m);m.p('hdc_target',1);m.p(symbols['dos64_native_diag']+3,7);m.call('dos64_native_tick',2000000);self.assertEqual(m.g('sav_borrowed'),0);self.assertEqual(m.g('dos64_export_cancel'),1);self.assertEqual(L.bulk_model_commands(m.m),commands);self.assertEqual(m.get('dos64_files_state_start',25),before);receipts.append({'case':'rejected-owner-keeps-old-cancel','no_new_wire':True,'cancel':1})
  finally:m.close()
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Sequential));(P/'SEQUENTIAL_RESULT.json').write_text(json.dumps({'successful':r.wasSuccessful(),'tests':r.testsRun,'receipts':receipts},indent=2)+'\n');sys.exit(not r.wasSuccessful())
