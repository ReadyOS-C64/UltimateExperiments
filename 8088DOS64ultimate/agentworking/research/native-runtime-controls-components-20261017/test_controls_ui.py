from test_finish_ui import *
records=[]
class Controls(unittest.TestCase):
 def start(self,target=1):
  m,old,f,high=FinishUI.start(self,target);f['HDB']=m.get('hdb_state_start',symbols['hdb_state_end']-symbols['hdb_state_start']);f['nativeSP']=L.dos64_get_regs(m.m).sp;return m,old,f,high
 def exact_C(self,m,f,position,high,before,check_reu=True):
  self.assertEqual(m.get('dos64_files_state_start',25),f['C']);self.assertEqual(m.get('hd_state_start',symbols['hd_state_end']-symbols['hd_state_start']),f['HD']);self.assertEqual(L.save_model_position(m.m,m.target),position);self.assertEqual(m.get('hdb_state_start',symbols['hdb_state_end']-symbols['hdb_state_start']),f['HDB']);self.assertEqual(m.get(128,96),high)
  if check_reu:self.assertEqual(reu(m,0,4194304),before)
 def request(self,m,op,drive=0,flags=0):
  q=bytearray(27);q[0]=op;q[1]=drive;q[2]=flags;q[4]=4;off=drive*4;q[15:19]=m.get(symbols['dos64_disk_mount_generation']+off,4);q[19:23]=m.get(symbols['dos64_disk_content_generation']+off,4);m.put('dos64_floppy_request',q)
 def core(self,m):return m.call('dos64_overlay_floppy_control',3000000)
 def test01_CIA_WriteProtect_toggle_A_B_preserves_dirty_and_C(self):
  for target,drive in [(1,0),(2,1)]:
   m,old,f,high=self.start(target)
   try:
    press(self,m,ord('b'if drive else'a'));before=reu(m,0,4194304);position=L.save_model_position(m.m,target);n=L.bulk_model_commands(m.m);meta=m.get('dos64_disk_b_descriptor',32);initial=m.g(symbols['dos64_disk_readonly']+drive);mount=m.get('dos64_disk_mount_generation',16);binding=m.get('dos64_disk_binding',8)
    for want in [initial^1,initial]:
     press(self,m,ord('w'));self.assertEqual(m.g(UI['_mu_result']),1);self.assertEqual(m.g(BE['br_success']),1);self.assertEqual(m.g(symbols['dos64_disk_readonly']+drive),want);self.assertEqual(m.g(symbols['dos64_disk_dirty']+1),1);self.assertEqual(m.g(UI['_mu_view']+129*drive)&2,want*2)
    self.assertEqual(m.get('dos64_disk_b_descriptor',32),meta);self.assertEqual(m.get('dos64_disk_mount_generation',16),mount);self.assertEqual(m.get('dos64_disk_binding',8),binding);self.exact_C(m,f,position,high,before);self.assertEqual(L.bulk_model_commands(m.m),n);records.append({'target':target,'drive':drive,'CIA_protect_toggle':True,'dirty_unchanged':True,'C_context_and_all4MiB_exact':True,'no_FILE':True})
   finally:m.close()
 def test02_CIA_dirty_Eject_cancel_then_discard_retains_startup_binding(self):
  m,old,f,high=self.start()
  try:
   press(self,m,ord('b'));before=reu(m,0,4194304);position=L.save_model_position(m.m,1);n=L.bulk_model_commands(m.m);meta=m.get('dos64_disk_b_descriptor',32);bindings=m.get('dos64_disk_binding',8);generation=int.from_bytes(m.get(symbols['dos64_disk_mount_generation']+4,4),'little')
   press(self,m,ord('e'));self.assertEqual(m.g(UI['_mu_result']),2);press(self,m,ord('c'));self.assertEqual(m.g(UI['_mu_result']),1);self.assertEqual(m.get('dos64_disk_b_descriptor',32),meta)
   press(self,m,ord('e'));press(self,m,ord('d'));self.assertEqual(m.g(UI['_mu_result']),1);self.assertEqual(m.g(BE['br_success']),1);self.assertEqual(m.g(symbols['dos64_disk_b_descriptor']+9),0);self.assertEqual(m.g(symbols['dos64_disk_dirty']+1),0);self.assertEqual(int.from_bytes(m.get(symbols['dos64_disk_mount_generation']+4,4),'little'),generation+1);self.assertEqual(m.get('dos64_disk_binding',8),bindings);self.assertEqual(m.g(UI['_mu_view']+129)&1,0);self.assertEqual(reu(m,0x3ff020,576),old);self.assertEqual(m.bytes(b'/usb1/Owned/DOS64.CFG',576),old);self.exact_C(m,f,position,high,before);self.assertEqual(L.bulk_model_commands(m.m),n);records.append({'dirty_Eject_cancel_then_discard':True,'empty_B':True,'startup_CFG_binding_retained':True,'C_context_and_all4MiB_exact':True,'no_FILE':True})
  finally:m.close()
 def test03_Eject_B_then_SaveAs_A_remains_durable(self):
  m,old,f,high=self.start()
  try:
   press(self,m,ord('b'));press(self,m,ord('e'));press(self,m,ord('d'));self.assertEqual(m.g(symbols['dos64_disk_b_descriptor']+9),0);press(self,m,ord('a'));press(self,m,ord('n'))
   for i in range(len(b'/usb1/Media/')):press(self,m,8)
   path=b'/usb1/Owned/AFTER.IMG'
   for c in path:press(self,m,c)
   press(self,m,13,1400000000);self.assertEqual(m.g(BE['br_success']),1);self.assertEqual(m.g(BE['br_error']),0);self.assertEqual(m.g(UI['_mu_result']),1);self.assertEqual(m.g('dos64_native_diag'),8);self.assertEqual(m.g(symbols['dos64_disk_b_descriptor']+9),0);self.assertEqual(m.bytes(path,368640),A);cfg_now=m.bytes(b'/usb1/Owned/DOS64.CFG',576);self.assertEqual(cfg_now[136:264],path.ljust(128,b'\0'));self.assertEqual(cfg_now[264:392],old[264:392]);self.assertEqual(cfg_now[532:536],old[532:536]);self.assertEqual(m.bytes(b'/usb1/Owned/C.IMG',len(HD)),HD);records.append({'CIA_Eject_B_then_A_SaveAs':True,'CFG_durable':True,'B_remains_empty':True,'C_image_exact':True})
  finally:m.close()
 def save_before_eject(self,collision=False):
  m,old,f,high=self.start()
  try:
   path=b'/usb1/Owned/BSAVED.IMG'
   if collision:L.bulk_model_seed(m.m,path,b'EXISTING',8)
   press(self,m,ord('b'));press(self,m,ord('e'));self.assertEqual(m.g(UI['_mu_result']),2);press(self,m,ord('s'));self.assertEqual(m.g(UI['_mu_result']),3)
   for i in range(len(b'/sd/Media/')):press(self,m,8)
   for c in path:press(self,m,c)
   press(self,m,13,1400000000)
   if collision:
    self.assertEqual(m.g(UI['_mu_result']),5);self.assertEqual(m.g(symbols['dos64_disk_b_descriptor']+9),1);self.assertEqual(m.g(symbols['dos64_disk_dirty']+1),1);self.assertEqual(m.bytes(path,8),b'EXISTING');self.assertEqual(m.bytes(b'/usb1/Owned/DOS64.CFG',576),old);records.append({'Save_before_Eject_collision':True,'Eject_cancelled':True,'old_working_B_retained':True});return
   if m.g(UI['_mu_result'])==4:keys(m,bytes(8));loop(self,m,10000000)
   self.assertEqual(m.g(UI['_mu_result']),1);self.assertEqual(m.g(symbols['dos64_disk_b_descriptor']+9),0);self.assertEqual(m.bytes(path,368640),NEW_B);new=m.bytes(b'/usb1/Owned/DOS64.CFG',576);self.assertEqual(new[264:392],path.ljust(128,b'\0'));self.assertEqual(m.get(symbols['dos64_disk_binding']+4,4),new[532:536]);self.assertEqual(m.bytes(b'/sd/Media/B.IMG',368640),OLD_B);self.assertEqual(m.bytes(b'/usb1/Owned/C.IMG',len(HD)),HD);records.append({'Save_before_Eject_success':True,'new_B_durable_before_Eject':True,'startup_binding_retained':True,'C_originals_exact':True})
  finally:m.close()
 def test09_CIA_Save_first_then_Eject(self):self.save_before_eject()
 def test10_CIA_failed_Save_first_cancels_Eject(self):self.save_before_eject(True)
 def test11_CIA_clean_A_Eject_Ctarget2(self):
  m,old,f,high=self.start(2)
  try:
   before=reu(m,0,4194304);position=L.save_model_position(m.m,2);n=L.bulk_model_commands(m.m);other=m.get('dos64_disk_b_descriptor',32);press(self,m,ord('e'));self.assertEqual(m.g(UI['_mu_result']),1);self.assertEqual(m.g(BE['br_success']),1);self.assertEqual(m.g('dos64_disk_loaded'),0);self.assertEqual(m.get('dos64_disk_b_descriptor',32)[:10],other[:10]);self.assertEqual(m.g(symbols['dos64_disk_dirty']+1),1);self.exact_C(m,f,position,high,before);self.assertEqual(L.bulk_model_commands(m.m),n);records.append({'CIA_clean_A_Eject_C2':True,'dirty_other_B_preserved':True,'C_context_all4MiB_exact':True,'no_FILE':True})
  finally:m.close()
 def test12_core_modal_guards_before_any_media_operation(self):
  for which in ['cache','target','E1','unknownop']:
   m,old,f,high=self.start()
   try:
    self.request(m,1 if which=='cache'else 7 if which=='unknownop'else 6);meta=m.get('dos64_disk_b_descriptor',32);before=reu(m,0,4194304);n=L.bulk_model_commands(m.m)
    if which=='cache':m.p('dos64_cache_limit',1)
    elif which=='target':m.p('hdc_target',2)
    elif which=='E1':m.p('dos64_native_diag',0xe1)
    self.assertTrue(self.core(m).regs.p&1);self.assertEqual(m.g('dos64_floppy_status'),7);self.assertEqual(m.get('dos64_disk_b_descriptor',32),meta);self.assertEqual(reu(m,0,4194304),before);self.assertEqual(L.bulk_model_commands(m.m),n)
   finally:m.close()
  records.append({'modal_cache_Ctarget_E1_unknownop_guards':True,'no_FILE_or_media_change':True})
 def test04_core_stage8_PREPARE_COMMIT_rotates_and_preserves_other_image(self):
  m,old,f,high=self.start()
  try:
   n=L.bulk_model_commands(m.m);before=reu(m,0,4194304);position=L.save_model_position(m.m,1);self.request(m,1,0,1);binding=b'\x12\x34\x56\x78';m.put(symbols['dos64_floppy_request']+23,binding);self.assertFalse(self.core(m).regs.p&1);q=m.get('dos64_floppy_request',27);self.assertEqual(q[5:8],b'\0\0\x18');candidate=fat(b'NEW INCOMING\r\n');L.bulk_reu_seed(m.m,0x180000,candidate,len(candidate));m.p('dos64_floppy_request',2);m.p(symbols['dos64_floppy_request']+3,0xa5);self.assertFalse(self.core(m).regs.p&1);self.assertEqual(m.get('dos64_disk_reu_base',3),b'\0\0\x18');self.assertEqual(m.g('dos64_disk_readonly'),1);self.assertEqual(m.get('dos64_disk_binding',4),binding);self.assertEqual(m.g('dos64_floppy_stage_active'),0);self.assertEqual(reu(m,0x100000,368640),before[0x100000:0x15a000]);self.assertEqual(reu(m,0x380000,368640),before[0x380000:0x3da000]);self.exact_C(m,f,position,high,before,False);after=reu(m,0,4194304);self.assertEqual(after[:0x180000],before[:0x180000]);self.assertEqual(after[0x1da000:],before[0x1da000:]);self.assertEqual(L.bulk_model_commands(m.m),n);records.append({'stage8_PREPARE_COMMIT':True,'returned_free18_arena':True,'old_A_and_B_bytes_exact':True,'binding_captured_before_PREPARE':True,'C_context_exact':True})
  finally:m.close()
 def test05_core_bad_incoming_geometry_keeps_old_mount_then_CANCEL(self):
  m,old,f,high=self.start()
  try:
   oldmeta=m.get('dos64_disk_reu_base',10);self.request(m,1);self.assertFalse(self.core(m).regs.p&1);bad=bytearray(A);bad[11]^=1;L.bulk_reu_seed(m.m,0x180000,bytes(bad),len(bad));m.p('dos64_floppy_request',2);m.p(symbols['dos64_floppy_request']+3,0xa5);self.assertTrue(self.core(m).regs.p&1);self.assertEqual(m.g('dos64_floppy_status'),6);self.assertEqual(m.get('dos64_disk_reu_base',10),oldmeta);self.assertEqual(m.g('dos64_floppy_stage_active'),0xa5);m.p('dos64_floppy_request',3);self.assertFalse(self.core(m).regs.p&1);self.assertEqual(m.g('dos64_floppy_stage_active'),0);self.assertEqual(m.get('dos64_disk_reu_base',10),oldmeta);records.append({'bad_BPBincoming_keeps_old_mount':True,'stage8_CANCEL':True})
  finally:m.close()
 def test06_core_stale_snapshot_and_invalid_policy_refuse(self):
  for op,flags,stale,expected in [(4,1,False,1),(6,2,False,1),(4,2,True,4),(6,1,True,4),(4,0,False,3)]:
   m,old,f,high=self.start()
   try:
    before=reu(m,0,4194304);meta=m.get('dos64_disk_b_descriptor',32);self.request(m,op,1,flags)
    if stale:m.p(symbols['dos64_floppy_request']+15,m.g(symbols['dos64_floppy_request']+15)^1)
    self.assertTrue(self.core(m).regs.p&1);self.assertEqual(m.g('dos64_floppy_status'),expected);self.assertEqual(m.get('dos64_disk_b_descriptor',32),meta);self.assertEqual(reu(m,0,4194304),before)
   finally:m.close()
  records.append({'invalid_flags_stale_snapshot_no_discard':True,'all_refused_without_media_changes':True})
 def test07_CIA_STOP_before_native_control_preserves_media(self):
  m,old,f,high=self.start()
  try:
   n=L.bulk_model_commands(m.m);meta=m.get('dos64_disk_b_descriptor',32);keys(m,bytes(8));loop(self,m);key=normal.index(ord('w'));b=bytearray(8);b[key//8]|=1<<(key%8);keys(m,b);L.dos64_step(m.m);r=L.dos64_run(m.m,BE['control_intent'],5000000);self.assertEqual((r.status,r.regs.pc),(2,BE['control_intent']));keys(m,bytes(7)+b'\x80');r=L.dos64_run(m.m,BR['modal_wait'],5000000);self.assertEqual((r.status,r.regs.pc),(2,BR['modal_wait']));self.assertEqual(m.g(UI['_mu_result']),5);self.assertEqual(m.g(BE['br_error']),8);self.assertEqual(m.g(BE['br_resume']),1);self.assertEqual(m.get('dos64_disk_b_descriptor',32),meta);self.assertEqual(L.bulk_model_commands(m.m),n);records.append({'physical_STOP_before_control':True,'no_change':True,'Resume_retained':True})
  finally:m.close()
 def test08_C_context_or_busy_UCI_blocks_before_control(self):
  for which in ['Ctarget','UCIbusy']:
   m,old,f,high=self.start()
   try:
    n=L.bulk_model_commands(m.m);meta=m.get('dos64_disk_b_descriptor',32);keys(m,bytes(8));loop(self,m);key=normal.index(ord('w'));b=bytearray(8);b[key//8]|=1<<(key%8);keys(m,b);L.dos64_step(m.m);r=L.dos64_run(m.m,BE['control_intent'],5000000);self.assertEqual(r.status,2)
    m.p('hdc_target',2)if which=='Ctarget'else m.p('dos64_uci_state',1)
    r=L.dos64_run(m.m,BR['modal_wait'],5000000);self.assertEqual((r.status,r.regs.pc),(2,BR['modal_wait']));self.assertEqual(m.g(UI['_mu_result']),5);self.assertEqual(m.g(BE['br_resume']),0);self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(m.get('dos64_disk_b_descriptor',32),meta);self.assertEqual(L.bulk_model_commands(m.m),n);records.append({'withdrawn_context':which,'no_media_change_or_FILE':True,'Resume_fenced':True})
   finally:m.close()
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls));(P/'CONTROLS_UI_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'records':records,'scope':'actual runtime/CIAEjectProtect/corestaging; syntheticmedia; Insertload/durabletransaction not implemented'},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
