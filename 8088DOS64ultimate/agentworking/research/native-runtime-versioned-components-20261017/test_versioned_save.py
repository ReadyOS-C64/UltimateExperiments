from test_sequence_ui import *
results=[]
def writable(t,target=1,drive=1,bank=0x10,home=b'/usb1/Owned'):
 m,old,f=initial(t,target,drive,bank,False)
 m.p(symbols['dos64_disk_readonly']+drive,0)
 old=bytearray(old);old[524]&=~(1<<drive);old[8:136]=home.ljust(128,b'\0');old=resign(old)
 seed(m,home+b'/DOS64.CFG',old)
 for at,b in [(0x3ff020,old),(0x3ff000,headers(old)[0]),(0x3ff500,headers(old)[1])]:L.bulk_reu_seed(m.m,at,b,len(b))
 return m,old,f

def save_key(t,m,sequence,path,drive=1):
 press(t,m,ord('b'if drive else'a'));press(t,m,ord('s'),1400000000)
 v=m.get(BE['br_last'],9);t.assertEqual((v[0],v[1],v[4],v[5]),(2,0,1,1),v.hex());t.assertEqual(m.g(BE['br_success']),1);t.assertEqual(int.from_bytes(v[7:9],'little'),sequence,v.hex());t.assertEqual(m.get(UI['_mu_view']+1+129*drive,128),path.ljust(128,b'\0'));t.assertEqual(m.get(UI['_mu_result'],1),b'\1');t.assertEqual(m.g(symbols['dos64_disk_dirty']+drive),0)
 return int.from_bytes(m.get(BE['br_intent'],2),'little')

class Versioned(unittest.TestCase):
 def test01_repeated_S_skips_archive_and_orphan_images(self):
  m,old,f=writable(self)
  try:
   keep={b'S0001.OLD':b'prior old',b'S0001.JRN':b'prior journal',b'B0002.IMG':b'orphan image',b'S0004.JRN':b'one sided'}
   for name,b in keep.items():seed(m,b'/usb1/Owned/'+name,b)
   enter(self,m);before=reu(m,0,4194304);ctx=m.get('dos64_files_state_start',25);pos=L.save_model_position(m.m,1);high=m.get(128,96);oldcfg=old;out=[]
   for seq in [3,5]:
    path=('/usb1/Owned/B%04X.IMG'%seq).encode();ticket=save_key(self,m,seq,path);self.assertNotEqual(ticket,seq);guard_C(self,m,ctx,pos);self.assertEqual(m.get(128,96),high);self.assertEqual(m.bytes(path,368640),f['working']);self.assertEqual(m.bytes(('/usb1/Owned/S%04X.OLD'%seq).encode(),576),oldcfg);oldcfg=m.bytes(b'/usb1/Owned/DOS64.CFG',576);self.assertEqual(oldcfg[264:392],path.ljust(128,b'\0'));self.assertEqual(reu(m,0x3ff020,576),oldcfg);out.append({'sequence':seq,'ticket':ticket,'path':path.decode()})
   for name,b in keep.items():self.assertEqual(m.bytes(b'/usb1/Owned/'+name,len(b)),b)
   self.assertEqual(m.bytes(b'/sd/Media/B.IMG',368640),OLD_B);self.assertEqual(m.bytes(b'/usb1/Owned/B0003.IMG',368640),f['working']);guard_REU(self,before,reu(m,0,4194304));results.append({'repeated_CIA_S':out,'originals_and_orphans_preserved':True,'full4M_C_high96':True})
  finally:m.close()
 def test02_fresh_target2_A18_longhome117(self):
  home=b'/'+b'h'*116;self.assertEqual(len(home),117)
  m,old,f=writable(self,2,0,0x18,home)
  try:
   for n in [b'S0001.OLD',b'S0001.JRN',b'A0002.IMG']:seed(m,home+b'/'+n,b'KEEP')
   enter(self,m);before=reu(m,0,4194304);ctx=m.get('dos64_files_state_start',25);pos=L.save_model_position(m.m,2);path=home+b'/A0003.IMG';self.assertEqual(len(path),127);ticket=save_key(self,m,3,path,0);self.assertEqual(ticket,1);guard_C(self,m,ctx,pos);guard_REU(self,before,reu(m,0,4194304));self.assertEqual(m.bytes(path,368640),f['working']);self.assertEqual(m.bytes(home+b'/S0003.OLD',576),old);self.assertEqual(m.bytes(b'/usb1/Media/A.IMG',368640),A);results.append({'fresh_Ctarget2_A18_longhome117':True,'pathlen':127,'ticket':ticket,'sequence':3})
  finally:m.close()
 def test03_FFFF_wrap_skips_image_to1(self):
  m,old,f=writable(self)
  try:
   seed(m,b'/usb1/Owned/BFFFF.IMG',b'KEEP FFFF');enter(self,m);press(self,m,ord('b'));keys(m,bytes(8));loop(self,m);index=normal.index(ord('s'));b=bytearray(8);b[index//8]|=1<<(index%8);keys(m,b);L.dos64_step(m.m);until(self,m,AC['ac_entry'],20000000);m.wide(AC['_ac_request']+2,65535,2);r=L.dos64_run(m.m,BR['modal_wait'],1400000000);self.assertEqual(r.status,2);v=m.get(BE['br_last'],9);self.assertEqual((v[0],v[1]),(2,0),v.hex());self.assertEqual(v[7:9],b'\1\0');self.assertEqual(m.bytes(b'/usb1/Owned/BFFFF.IMG',9),b'KEEP FFFF');self.assertEqual(m.bytes(b'/usb1/Owned/B0001.IMG',368640),f['working']);self.assertEqual(L.bulk_model_size(m.m,b'/usb1/Owned/B0000.IMG'),0xffffffff);results.append({'advisoryFFFF_wrap':1,'orphan_preserved':True})
  finally:m.close()
 def test04_readonly_S_opens_SaveAs(self):
  m,old,f=initial(self,admit=False)
  try:
   enter(self,m);press(self,m,ord('b'));before=L.bulk_model_commands(m.m);press(self,m,ord('s'));self.assertEqual(m.get(UI['_mu_result'],1),b'\3');self.assertEqual(L.bulk_model_commands(m.m),before);self.assertEqual(reu(m,0x3ff020,576),old);results.append({'readonly_S_routes_SaveAs':True})
  finally:m.close()

 def test09_captured_mode_drive_hint_not_public_observations(self):
  m,old,f=writable(self)
  try:
   enter(self,m);press(self,m,ord('b'));keys(m,bytes(8));loop(self,m);index=normal.index(ord('s'));b=bytearray(8);b[index//8]|=1<<(index%8);keys(m,b);L.dos64_step(m.m);until(self,m,TW['tw_poll'],50000000)
   self.assertEqual(m.g(TW['tw_mode']),3);m.p(TW['tw_drive'],0);m.wide(TW['tw_sequence'],0xbeef,2);m.p(TW['tw_mode'],0)
   r=L.dos64_run(m.m,BR['modal_wait'],1400000000);self.assertEqual(r.status,2);v=m.get(BE['br_last'],9);self.assertEqual((v[0],v[1]),(2,0),v.hex());self.assertEqual(v[7:9],b'\1\0');self.assertEqual(m.bytes(b'/usb1/Owned/B0001.IMG',368640),f['working']);self.assertEqual(L.bulk_model_size(m.m,b'/usb1/Owned/A0001.IMG'),0xffffffff);self.assertEqual(L.bulk_model_size(m.m,b'/usb1/Owned/BBEEF.IMG'),0xffffffff);results.append({'captured_mode_drive_hint_ignore_public_forgery':True})
  finally:m.close()

class Faults(unittest.TestCase):
 def prepare_S(self,m):
  press(self,m,ord('b'));keys(m,bytes(8));loop(self,m);index=normal.index(ord('s'));b=bytearray(8);b[index//8]|=1<<(index%8);keys(m,b);L.dos64_step(m.m)
 def done(self,m):
  r=L.dos64_run(m.m,BR['modal_wait'],1400000000);self.assertEqual(r.status,2,(r.status,hex(r.regs.pc)));return m.get(BE['br_last'],9)
 def test05_STOP_at_allocator_no_create(self):
  m,old,f=writable(self)
  try:
   enter(self,m);self.prepare_S(m);until(self,m,TW['tw_begin'],50000000);keys(m,bytes(7)+b'\x80');v=self.done(m);self.assertEqual(v[0],3,v.hex());self.assertIn(v[1],[3,8]);self.assertEqual(L.bulk_model_size(m.m,b'/usb1/Owned/B0001.IMG'),0xffffffff);self.assertEqual(reu(m,0x3ff020,576),old);results.append({'STOP_mode3':v.hex()})
  finally:m.close()
 def test06_sourceCRC_before_FILES(self):
  m,old,f=writable(self)
  try:
   enter(self,m);at=json.loads((P/'CONTROLLER_BUILD.json').read_text())['records'][0]['reu'];b=reu(m,at,1);L.bulk_reu_seed(m.m,at,bytes([b[0]^1]),1);before=L.bulk_model_commands(m.m);press(self,m,ord('b'));press(self,m,ord('s'),1400000000);v=m.get(BE['br_last'],9);self.assertEqual((v[0],v[1]),(3,2),v.hex());self.assertEqual(L.bulk_model_commands(m.m),before);self.assertEqual(L.bulk_model_size(m.m,b'/usb1/Owned/B0001.IMG'),0xffffffff);results.append({'CRC_before_FILES':v.hex()})
  finally:m.close()
 def test07_unknown_CLOSE_once_no_resume(self):
  m,old,f=writable(self)
  try:
   enter(self,m);before=L.bulk_model_commands(m.m);L.save_model_fail_close(m.m,2);press(self,m,ord('b'));press(self,m,ord('s'),1400000000);v=m.get(BE['br_last'],9);self.assertEqual((v[0],v[4],v[5]),(3,0,0),v.hex());self.assertEqual(sum(L.bulk_model_command(m.m,i,1)==3 for i in range(before,L.bulk_model_commands(m.m))),1);self.assertEqual(L.bulk_model_size(m.m,b'/usb1/Owned/B0001.IMG'),0xffffffff);self.assertEqual(reu(m,0x3ff020,576),old);results.append({'unknown_CLOSE_one_attempt':v.hex()})
  finally:m.close()
 def test08_clock_failure_recovery_cannot_create(self):
  m,old,f=writable(self)
  try:
   enter(self,m);self.prepare_S(m);r=until(self,m,TW['tw_poll'],50000000);self.assertEqual(m.g(TW['tw_mode']),3);m.p('dos64_host_clock_claim',0);ret=int.from_bytes(m.get(0x100+r.regs.sp+1,2),'little')+1;until(self,m,ret,20000000);self.assertEqual(m.g(TW['error']),2);m.p('dos64_host_clock_claim',0xa5);v=self.done(m);self.assertEqual((v[0],v[1],v[3],v[5]),(3,3,2,0),v.hex());self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(L.bulk_model_size(m.m,b'/usb1/Owned/B0001.IMG'),0xffffffff);self.assertEqual(reu(m,0x3ff020,576),old);results.append({'clock_failure_then_recovery':v.hex()})
  finally:m.close()

 def test10_mode3_rejects_actual_readonly_caller_attempt(self):
  m,old,f=initial(self,admit=False)
  try:
   enter(self,m);prepare(self,m,b'/usb1/Owned/IGNORED.IMG');release_enter(self,m,AC['ac_entry']);m.p(AC['_ac_request']+9,1)
   before=L.bulk_model_commands(m.m);v=self.done(m);self.assertEqual((v[0],v[1]),(3,3),v.hex());self.assertEqual(L.bulk_model_commands(m.m),before);self.assertEqual(L.bulk_model_size(m.m,b'/usb1/Owned/B0001.IMG'),0xffffffff);self.assertEqual(reu(m,0x3ff020,576),old);self.assertEqual(m.g(symbols['dos64_disk_dirty']+1),1);results.append({'explicit_caller_action1_on_actual_readonly_refused_before_FILES':True,'qualification':'caller action override only; ordinary readonly CIA S remains SaveAs dialog'})
  finally:m.close()

if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(Versioned),unittest.defaultTestLoader.loadTestsFromTestCase(Faults)]));(P/'VERSIONED_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'records':results,'scope':'UNIT actual CIA/nativeUI/bridge/controller/mode3/workers and modeled firmware; no runtime/device'},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
