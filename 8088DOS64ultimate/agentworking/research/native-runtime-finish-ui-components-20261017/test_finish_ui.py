"""Actual selected runtime/CIA routing; synthetic disk fixtures, no cold/DOS/hardware claim."""
from test_ui_saveas import *
FN=labels('finish/finish.labels');records=[]
class FinishUI(unittest.TestCase):
 def start(self,target=1):
  m,old,f=initial(self,target=target,admit=False)
  try:
   L.dos64_graphics_color_enable(m.m);body=(P/'MODAL.MNU').read_bytes()
   for a,b in [(0x3da000,body[:0x6000]),(0x3f0000,body[0x6000:])]:L.bulk_reu_seed(m.m,a,b,len(b))
   load(m,'broker/broker.prg');ret=symbols['fixture_return']-1;m.p(0x1ff,ret>>8);m.p(0x1fe,ret&255)
   high=bytes((i*11+17)&255 for i in range(96));m.put(128,high);keys(m,bytes(8));L.dos64_set_regs(m.m,Regs(BR['modal_entry'],0xfd,0x71,0x82,0x93,0x24,0,0));r=L.dos64_run(m.m,BR['modal_wait'],5000000);self.assertEqual((r.status,r.regs.pc),(2,BR['modal_wait']))
   return m,old,f,high
  except BaseException:m.close();raise
 def confirm(self,m):
  press(self,m,ord('f'));self.assertEqual(m.g(UI['_mu_result']),2)
  press(self,m,ord('d'));self.assertEqual(m.g(UI['_mu_result']),7)
 def enter(self,m,until,budget=10000000):
  keys(m,bytes(8));loop(self,m);keys(m,bytes([2,0,0,0,0,0,0,0]));L.dos64_step(m.m);return L.dos64_run(m.m,until,budget)
 def success(self,target):
  m,old,f,high=self.start(target)
  try:
   self.confirm(m);before=reu(m,0,4194304);n=L.bulk_model_commands(m.m);r=self.enter(m,BR['modal_safe_idle']);d={'status':r.status,'pc':hex(r.regs.pc),'ui':m.get(UI['_mu_result'],6).hex(),'error':m.g(BE['br_error']),'safe':m.g(BE['br_safe']),'stage':m.g('dos64_native_diag')};(P/'LAST_FINISH_UI.json').write_text(json.dumps(d,indent=2)+'\n')
   self.assertEqual((r.status,r.regs.pc),(2,BR['modal_safe_idle']),d);self.assertEqual(m.g(UI['_mu_result']),6,d);self.assertEqual(m.g(BE['br_safe']),1);self.assertEqual(m.g(BE['br_resume']),0);self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(m.g('hdb_online'),0);self.assertEqual(L.bulk_model_open(m.m,target),0);self.assertEqual(L.bulk_model_commands(m.m)-n,1);self.assertEqual([L.bulk_model_command(m.m,n,k)for k in range(2)],[target,3]);self.assertEqual(reu(m,0,4194304),before);self.assertEqual(m.get(128,96),high);self.assertEqual(m.bytes(b'/usb1/Owned/C.IMG',len(HD)),HD);self.assertEqual(m.g(symbols['dos64_disk_dirty']+1),1)
   keys(m,bytes([0,0,2,0,0,0,0,0]));r=L.dos64_run(m.m,0x0300,100000);self.assertEqual(r.status,3);self.assertEqual(m.g(UI['_mu_result']),6);self.assertEqual(L.bulk_model_commands(m.m)-n,1);self.assertEqual(m.g('dos64_native_diag'),0xe1)
   records.append(d|{'target':target,'one_known_CLOSE':True,'terminal_safe_park':True,'all4MiB_exact':True,'high96_exact':True,'no_guest_Resume':True})
  finally:m.close()
 def test01_Ctarget1_safe(self):self.success(1)
 def test02_Ctarget2_safe(self):self.success(2)
 def test03_cancel_before_close(self):
  for key in [ord('c'),27]:
   m,old,f,high=self.start()
   try:
    self.confirm(m);n=L.bulk_model_commands(m.m);press(self,m,key);self.assertEqual(m.g(UI['_mu_result']),1);self.assertEqual(L.bulk_model_commands(m.m),n);self.assertEqual(L.bulk_model_open(m.m,1),1);self.assertEqual(m.g('dos64_native_diag'),8);self.assertEqual(m.g(BE['br_safe']),0)
    keys(m,bytes(8));loop(self,m);keys(m,bytes([0,0,2,0,0,0,0,0]));L.dos64_step(m.m);r=L.dos64_run(m.m,0x0300,5000000);self.assertEqual(r.status,0);self.assertEqual(m.g('dos64_native_diag'),5);records.append({'cancel_key':key,'no_CLOSE':True,'Resume_retained':True})
   finally:m.close()
 def test04_finish_source_CRC_refusal(self):
  m,old,f,high=self.start()
  try:
   self.confirm(m);a=0x3f3800;b=reu(m,a,1);L.bulk_reu_seed(m.m,a,bytes([b[0]^1]),1);n=L.bulk_model_commands(m.m);r=self.enter(m,0x0300);self.assertEqual(r.status,0);self.assertEqual(L.bulk_model_commands(m.m),n);self.assertEqual(L.bulk_model_open(m.m,1),1);self.assertEqual(m.g(BE['br_safe']),0);self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(m.get(0x400,35),b'DISK CONTROL FAILED. KEEP POWER ON.');records.append({'Finish_CRC_refusal_before_FILE':True,'native_fallback':True})
  finally:m.close()
 def test05_unknown_CLOSE_never_safe_or_retry(self):
  m,old,f,high=self.start()
  try:
   self.confirm(m);L.save_model_fail_close(m.m,1);n=L.bulk_model_commands(m.m);r=self.enter(m,BR['modal_wait']);self.assertEqual((r.status,r.regs.pc),(2,BR['modal_wait']));self.assertEqual(m.g(UI['_mu_result']),5);self.assertEqual(m.g(BE['br_error']),4);self.assertEqual(m.g(BE['br_safe']),0);self.assertEqual(L.bulk_model_commands(m.m)-n,1);self.assertEqual(L.bulk_model_open(m.m,1),1);self.assertEqual(m.g('dos64_native_diag'),0xe1)
   # The next broker poll observes the permanent fence; no second CLOSE.
   keys(m,bytes(8));L.dos64_step(m.m);r=L.dos64_run(m.m,0x0300,5000000);self.assertEqual(r.status,0);self.assertEqual(L.bulk_model_commands(m.m)-n,1);self.assertEqual(m.g(UI['_mu_result']),5);records.append({'unknown_CLOSE':True,'one_attempt':True,'no_safe':True,'Resume_fenced':True})
  finally:m.close()
 def test07_retained_UI_code_corruption_no_SAFE_execution(self):
  m,old,f,high=self.start()
  try:
   self.confirm(m);n=L.bulk_model_commands(m.m);r=self.enter(m,BE['finish_present']);self.assertEqual((r.status,r.regs.pc),(2,BE['finish_present']));self.assertEqual(L.bulk_model_open(m.m,1),0);m.p(0x8000,m.g(0x8000)^1);r=L.dos64_run(m.m,0x0300,5000000);self.assertEqual(r.status,0);self.assertEqual(m.g(BR['ui_ready']),0);self.assertEqual(m.g(BE['br_safe']),0);self.assertEqual(m.get(0x400,35),b'DISK CONTROL FAILED. KEEP POWER ON.');self.assertEqual(L.bulk_model_commands(m.m)-n,1);records.append({'retained_UI_CRC_refusal':True,'known_CLOSED_but_no_SAFE_screen':True,'no_incomplete_execution':True})
  finally:m.close()
 def test08_STOP_after_acceptance_no_SAFE(self):
  m,old,f,high=self.start()
  try:
   self.confirm(m);n=L.bulk_model_commands(m.m);r=self.enter(m,BE['finish_wait']);self.assertEqual((r.status,r.regs.pc),(2,BE['finish_wait']));keys(m,bytes(7)+b'\x80');r=L.dos64_run(m.m,BR['modal_wait'],10000000);self.assertEqual((r.status,r.regs.pc),(2,BR['modal_wait']));self.assertEqual(m.g(UI['_mu_result']),5);self.assertEqual(m.g(BE['br_safe']),0);self.assertEqual(m.g(BE['br_error']),7);self.assertEqual(L.bulk_model_commands(m.m),n);self.assertEqual(L.bulk_model_open(m.m,1),1);self.assertEqual(m.g('dos64_native_diag'),0xe1);records.append({'CIA_STOP_after_acceptance':True,'no_FILE_or_SAFE':True,'Resume_fenced':True})
  finally:m.close()
 def test06_public_SAFE_reply_is_not_private_intent(self):
  m,old,f,high=self.start()
  try:
   n=L.bulk_model_commands(m.m);m.put(UI['_mu_event'],b'\1\0\7\1\2'+bytes(128));m.p(UI['_mu_reply_safe'],1);m.put(UI['_mu_reply_ticket'],b'\1\0');m.p(UI['_mu_reply_error'],0);r=m.call('bridge_entry',5000000);self.assertTrue(r.regs.p&1);self.assertEqual(L.bulk_model_commands(m.m),n);self.assertEqual(m.g(BE['br_safe']),0);self.assertEqual(L.bulk_model_open(m.m,1),1);self.assertEqual(m.g(UI['_mu_result']),1);records.append({'forged_public_SAFE_and_event_denied':True,'no_FILE':True})
  finally:m.close()
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FinishUI));(P/'FINISH_UI_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'records':records,'scope':'actual runtime native/CIA/Finish; synthetic mounted media; no cold boot, guest DOS or physical qualification'},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
