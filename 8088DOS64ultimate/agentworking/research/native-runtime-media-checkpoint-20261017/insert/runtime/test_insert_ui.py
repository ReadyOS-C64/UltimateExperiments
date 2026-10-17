from pathlib import Path
import os,sys
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;os.environ['DOS64_MEDIA_TEST_ROLE']='runtime'
import unittest,json,time,zlib
from test_sequence_ui import enter,press,loop,keys,guard_C,BR,UI,BE,AC
from fixture_base import *
from test_insert_controller import configure_empty_B
from controller_fixture import initial
records=[]

class Tests(unittest.TestCase):
 def case(self,kind,target=1):
  m,old,f=initial(self,target=target,admit=False)
  try:
   if kind=='first_B':old=configure_empty_B(m,old)
   path=b'/sd/Incoming/GUI.IMG';image=fat(b'ACTUAL CIA INSERT\r\n')
   if kind!='missing':L.bulk_model_seed(m.m,path,image,len(image))
   enter(self,m);ctx=m.get('dos64_files_state_start',25);pos=L.save_model_position(m.m,target);high=m.get(128,96);old42=m.get('dos64_disk_reu_base',10)+m.get('dos64_disk_b_descriptor',32);before=L.bulk_model_commands(m.m)
   press(self,m,ord('b'));press(self,m,ord('i'));self.assertEqual(m.get(UI['_mu_result'],1),b'\3')
   for c in path:press(self,m,c)
   if kind=='first_B':press(self,m,13,1_600_000_000)
   else:
    press(self,m,13);self.assertEqual(m.get(UI['_mu_result'],1),b'\2');self.assertEqual(L.bulk_model_commands(m.m),before)
    if kind=='cancel':
     press(self,m,ord('c'));self.assertEqual(m.get(UI['_mu_result'],1),b'\1');self.assertEqual(L.bulk_model_commands(m.m),before);self.assertEqual(m.get('dos64_disk_reu_base',10)+m.get('dos64_disk_b_descriptor',32),old42);records.append({'CIA_path_confirm_cancel':True,'no_FILE_calls':True});return
    if kind=='save_first':
     press(self,m,ord('s'));self.assertEqual(m.get(UI['_mu_result'],1),b'\3');archive=b'/usb1/Owned/BEFORE.IMG'
     # Default readonlyB asks SaveAs with /sd/Media/ prefilled.
     for _ in range(len(b'/sd/Media/')):press(self,m,8)
     for c in archive:press(self,m,c)
     press(self,m,13,1_600_000_000)
     for _ in range(4):
      if m.g(UI['_mu_result'])!=4:break
      loop(self,m,1_600_000_000)
     self.assertEqual(m.bytes(archive,368640),f['working'])
    else:press(self,m,ord('d'),1_600_000_000)
   diag={'case':kind,'result':m.get(BE['br_last'],9).hex(),'native_diag':m.g('dos64_native_diag'),'UI':m.get(UI['_mu_result'],6).hex(),'intent':m.get(BE['br_intent'],5).hex()};(P/'LAST_INSERT_UI.json').write_text(json.dumps(diag,indent=2)+'\n')
   if kind=='missing':
    self.assertEqual(m.g(UI['_mu_result']),5,diag);self.assertEqual(m.g(BE['br_success']),0);self.assertEqual(m.get('dos64_disk_reu_base',10)+m.get('dos64_disk_b_descriptor',32),old42);self.assertEqual(m.bytes(b'/usb1/Owned/DOS64.CFG',576),old);self.assertEqual(m.g('dos64_floppy_stage_active'),0);press(self,m,13);self.assertEqual(m.g(UI['_mu_result']),1)
   else:
    self.assertEqual((m.g('dos64_native_diag'),m.g(BE['br_success']),m.g(BE['br_error'])),(8,1,0),diag);self.assertEqual(m.g(UI['_mu_result']),1);self.assertEqual(m.get(UI['_mu_view']+130,128),path.ljust(128,b'\0'));self.assertEqual(m.g(UI['_mu_view']+129),3);self.assertEqual(m.get(BE['br_intent']+2,2),b'\3\1')
    bank=int.from_bytes(m.get('dos64_disk_b_descriptor',3),'little');self.assertEqual(reu(m,bank,368640),image);new=m.bytes(b'/usb1/Owned/DOS64.CFG',576);self.assertEqual(new[264:392],path.ljust(128,b'\0'));self.assertEqual(int.from_bytes(new[532:536],'little'),zlib.crc32(image));self.assertEqual(m.g('dos64_floppy_stage_active'),0)
   guard_C(self,m,ctx,pos);self.assertEqual(m.get(128,96),high)
   # A real CIA Resume intent returns through the native broker.
   keys(m,bytes(8));loop(self,m);keys(m,bytes([0,0,2,0,0,0,0,0]));L.dos64_step(m.m);r=L.dos64_run(m.m,symbols['fixture_return'],5_000_000);self.assertEqual(r.status,0,(r.status,hex(r.regs.pc)));self.assertEqual(m.g('dos64_native_diag'),5);self.assertEqual(m.g('dos64_cache_limit'),32);guard_C(self,m,ctx,pos)
   records.append(diag|{'actual_CIA_private_intent_complete_Insert_and_Resume':True,'C_preserved':True,'save_first':kind=='save_first','scope':'synthetic media; no cold/DOS/physical'})
  finally:m.close()
 def test01_dirty_discard_Insert_and_Resume(self):self.case('discard')
 def test02_save_first_Insert_and_Resume(self):self.case('save_first')
 def test03_missing_keeps_old_then_Resume(self):self.case('missing')
 def test04_confirm_cancel_no_job(self):self.case('cancel')
 def test05_first_B_Ctarget2(self):self.case('first_B',2)

if __name__=='__main__':
 start=time.monotonic();r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));(P/'INSERT_UI_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'seconds':time.monotonic()-start,'records':records},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
