from pathlib import Path
import os,sys
sys.dont_write_bytecode=True;sys.pycache_prefix=str(Path(__file__).resolve().parent/(".absent-sequence-entry-"+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
from test_ui_saveas import *
AC=labels('controller/controller.labels');TW=labels('phase/transaction-wire.labels');records=[]
# Native leaf APIs are never called by this harness. Only actual CIA matrix,
# native loop progression, synthetic firmware files, and explicit fault controls.
def seed(m,p,b):L.bulk_model_seed(m.m,p,bytes(b),len(b))
def enter(t,m):
 body=(P/'MODAL.MNU').read_bytes()
 for a,b in [(0x3da000,body[:0x6000]),(0x3f0000,body[0x6000:])]:L.bulk_reu_seed(m.m,a,b,len(b))
 L.dos64_graphics_color_enable(m.m);load(m,'broker/broker.prg');ret=symbols['fixture_return']-1;m.p(511,ret>>8);m.p(510,ret&255);keys(m,bytes(8));L.dos64_set_regs(m.m,Regs(BR['modal_entry'],0xfd,0x71,0x82,0x93,0x24,0,0));r=L.dos64_run(m.m,BR['modal_wait'],5000000);t.assertEqual(r.status,2,(r.status,hex(r.regs.pc)));loop(t,m)
def prepare(t,m,path,drive=1):
 press(t,m,ord('b'if drive else'a'));current=m.get(UI['_mu_view']+1+129*drive,128).split(b'\0',1)[0];press(t,m,ord('n'));t.assertEqual(m.get(UI['_mu_result'],1),b'\3')
 for i in range(len(current.rsplit(b'/',1)[0])+1):press(t,m,8)
 for c in path:press(t,m,c)
def finish(t,m,path,expected,drive=1):
 press(t,m,13,1400000000);result=m.get(BE['br_last'],9);intent=m.get(BE['br_intent'],133);t.assertEqual((m.g('dos64_native_diag'),m.g(BE['br_success']),m.g(BE['br_error'])),(8,1,0),result.hex());t.assertEqual(int.from_bytes(result[7:9],'little'),expected,result.hex());t.assertEqual(m.get(UI['_mu_result'],1),b'\1');t.assertEqual(m.get(UI['_mu_view']+1+129*drive,128),path.ljust(128,b'\0'));t.assertEqual(m.g(symbols['dos64_disk_dirty']+drive),0)
 return int.from_bytes(intent[:2],'little')
def guard_C(t,m,context,pos):
 t.assertEqual(m.get('dos64_files_state_start',25),context);t.assertEqual(L.save_model_position(m.m,m.target),pos);t.assertEqual(L.bulk_model_open(m.m,m.target),1);t.assertEqual(L.bulk_model_open(m.m,3-m.target),0);t.assertEqual(m.bytes(b'/usb1/Owned/C.IMG',len(HD)),HD)
def guard_REU(t,before,after):
 for a,b in [(0,0x3e0000),(0x3e0b04,0x3e2000),(0x3e23e8,0x3ff000),(0x3ff260,0x3ff500),(0x3ff520,0x400000)]:t.assertEqual(after[a:b],before[a:b],(hex(a),hex(b)))
def until(t,m,pc,budget=5000000):
 r=L.dos64_run(m.m,pc,budget);t.assertEqual(r.status,2,(r.status,hex(r.regs.pc),hex(pc)));return r
def release_enter(t,m,pc,budget=20000000):
 keys(m,bytes(8));loop(t,m);keys(m,bytes([2,0,0,0,0,0,0,0]));L.dos64_step(m.m);return until(t,m,pc,budget)
class SequenceUI(unittest.TestCase):
 def test01_two_actualCIA_jobs_sequences2_4_not_tickets1_2(self):
  m,old,f=initial(self,admit=False)
  try:
   # Existing archives intentionally include one-sided3; no overwrite permitted.
   for n in [b'S0001.OLD',b'S0001.JRN',b'S0003.OLD']:seed(m,b'/usb1/Owned/'+n,b'KEEP '+n)
   enter(self,m);before=reu(m,0,4194304);ctx=m.get('dos64_files_state_start',25);pos=L.save_model_position(m.m,m.target);high=m.get(128,96);oldcfg=old;out=[];archive2=None
   for path,sequence in [(b'/usb1/Owned/NEXT001.IMG',2),(b'/usb1/Owned/NEXT002.IMG',4)]:
    prepare(self,m,path);ticket=finish(self,m,path,sequence);out.append({'ticket':ticket,'sequence':sequence,'path':path.decode()});self.assertNotEqual(ticket,sequence);guard_C(self,m,ctx,pos);self.assertEqual(m.get(128,96),high);self.assertEqual(m.bytes(path,368640),f['working']);self.assertEqual(m.bytes(('/usb1/Owned/S%04X.OLD'%sequence).encode(),576),oldcfg);oldcfg=m.bytes(b'/usb1/Owned/DOS64.CFG',576);self.assertEqual(reu(m,0x3ff020,576),oldcfg)
    if sequence==2:archive2=[m.bytes(b'/usb1/Owned/S0002.OLD',576),m.bytes(b'/usb1/Owned/S0002.JRN',1284)]
    else:self.assertEqual([m.bytes(b'/usb1/Owned/S0002.OLD',576),m.bytes(b'/usb1/Owned/S0002.JRN',1284)],archive2)
   self.assertEqual([v['ticket']for v in out],[1,2]);guard_REU(self,before,reu(m,0,4194304))
   for n in [b'S0001.OLD',b'S0001.JRN',b'S0003.OLD']:self.assertEqual(m.bytes(b'/usb1/Owned/'+n,len(b'KEEP '+n)),b'KEEP '+n)
   self.assertEqual(m.bytes(b'/sd/Media/B.IMG',368640),OLD_B);records.append({'two_actual_CIA_jobs':out,'generated_archive2_bytes_preserved_by_second_save':True,'same_engine':True,'C_context_and_full4MiB_guards':True})
  finally:m.close()
 def test02_fresh_session_archive1_skips_to2_Ctarget2_A(self):
  m,old,f=initial(self,target=2,drive=0,bank=0x18,admit=False)
  try:
   # Native allocation only requires existence; fixtures represent a prior
   # session's immutable archivepair, not a fabricated successful currentjob.
   for n in [b'S0001.OLD',b'S0001.JRN']:seed(m,b'/usb1/Owned/'+n,b'PRIOR SESSION ARCHIVE')
   enter(self,m);before=reu(m,0,4194304);ctx=m.get('dos64_files_state_start',25);pos=L.save_model_position(m.m,2);path=b'/usb1/Owned/FRESH002.IMG';prepare(self,m,path,0);ticket=finish(self,m,path,2,0);self.assertEqual(ticket,1);guard_C(self,m,ctx,pos);guard_REU(self,before,reu(m,0,4194304));self.assertEqual(m.bytes(path,368640),f['working']);records.append({'fresh_session_Ctarget2_A18':True,'CUI_ticket':ticket,'selected':2})
  finally:m.close()
 def test03_actual_CIA_intent_advisory_FFFF_hint_wraps_to1(self):
  m,old,f=initial(self,admit=False)
  try:
   seed(m,b'/usb1/Owned/SFFFF.OLD',b'KEEP FFFF');enter(self,m);path=b'/usb1/Owned/WRAP001.IMG';prepare(self,m,path);release_enter(self,m,AC['ac_entry'])
   # Explicit integration boundary: override caller's advisory hint only.
   # Private CUI intent was captured beforethis; no private sequence minted.
   m.wide(AC['_ac_request']+2,65535,2);r=L.dos64_run(m.m,BR['modal_wait'],1400000000);self.assertEqual(r.status,2,(r.status,hex(r.regs.pc)));self.assertEqual(m.g(BE['br_success']),1);self.assertEqual(m.get(BE['br_last']+7,2),b'\1\0');self.assertEqual(m.bytes(b'/usb1/Owned/SFFFF.OLD',9),b'KEEP FFFF');self.assertEqual(m.bytes(path,368640),f['working']);self.assertEqual(L.bulk_model_size(m.m,b'/usb1/Owned/S0000.OLD'),0xffffffff);records.append({'actualCIA_SaveAs_with_injected_non_authoritative_hintFFFF':True,'selected':1,'zero_unused':True})
  finally:m.close()
 def test04_pending_NEW_blocks_before_image_CREATE(self):
  m,old,f=initial(self,admit=False)
  try:
   seed(m,b'/usb1/Owned/DOS64.NEW',b'KEEP PENDING');enter(self,m);ctx=m.get('dos64_files_state_start',25);pos=L.save_model_position(m.m,1);path=b'/usb1/Owned/BLOCKED.IMG';prepare(self,m,path);press(self,m,13,1400000000);result=m.get(BE['br_last'],9);self.assertEqual((result[0],result[1],result[3]),(3,3,13),result.hex());self.assertEqual(m.g(BE['br_success']),0);self.assertEqual(L.bulk_model_size(m.m,path),0xffffffff);guard_C(self,m,ctx,pos);self.assertEqual(m.bytes(b'/usb1/Owned/DOS64.NEW',12),b'KEEP PENDING');self.assertEqual(reu(m,0x3ff020,576),old);self.assertEqual(m.g(symbols['dos64_disk_dirty']+1),1);records.append({'activeNEW_blocks_before_SAVE':result.hex()})
  finally:m.close()
 def test05_actual_STOP_at_allocator_entry_no_image_or_CFG_mutation(self):
  m,old,f=initial(self,admit=False)
  try:
   enter(self,m);ctx=m.get('dos64_files_state_start',25);pos=L.save_model_position(m.m,1);path=b'/usb1/Owned/CANCELLED.IMG';prepare(self,m,path);release_enter(self,m,TW['tw_begin']);keys(m,bytes(7)+b'\x80');r=L.dos64_run(m.m,BR['modal_wait'],1400000000);self.assertEqual(r.status,2,(r.status,hex(r.regs.pc)));v=m.get(BE['br_last'],9);self.assertEqual(v[0],3,v.hex());self.assertIn(v[1],[3,8]);self.assertEqual(L.bulk_model_size(m.m,path),0xffffffff);self.assertEqual(reu(m,0x3ff020,576),old);guard_C(self,m,ctx,pos);self.assertEqual(m.g(symbols['dos64_disk_dirty']+1),1);records.append({'actualSTOP_during_allocator':v.hex(),'no_SAVE':True})
  finally:m.close()
class SequenceFaults(unittest.TestCase):
 def test06_allocator_sourceCRC_refuses_before_any_FILE_job(self):
  m,old,f=initial(self,admit=False)
  try:
   enter(self,m);ctx=m.get('dos64_files_state_start',25);pos=L.save_model_position(m.m,1);at=json.loads((P/'CONTROLLER_BUILD.json').read_text())['records'][0]['reu'];original=reu(m,at,1);L.bulk_reu_seed(m.m,at,bytes([original[0]^1]),1);path=b'/usb1/Owned/SRCFAULT.IMG';prepare(self,m,path);before=L.bulk_model_commands(m.m);press(self,m,13,1400000000);v=m.get(BE['br_last'],9);self.assertEqual((v[0],v[1]),(3,2),v.hex());self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(L.bulk_model_commands(m.m),before);self.assertEqual(L.bulk_model_size(m.m,path),0xffffffff);guard_C(self,m,ctx,pos);self.assertEqual(reu(m,0x3ff020,576),old);records.append({'allocator_sourceCRC':v.hex(),'no_FILE_commands':True})
  finally:m.close()
 def test07_clock_failure_in_allocator_then_recovery_cannot_Resume_or_SAVE(self):
  m,old,f=initial(self,admit=False)
  try:
   enter(self,m);ctx=m.get('dos64_files_state_start',25);pos=L.save_model_position(m.m,1);path=b'/usb1/Owned/CLOCKFAULT.IMG';prepare(self,m,path);r=release_enter(self,m,TW['tw_poll']);self.assertEqual(m.g(TW['tw_mode']),2);self.assertEqual(m.g(AC['_ac_result']+2),1);m.p('dos64_host_clock_claim',0);ret=int.from_bytes(m.get(0x100+r.regs.sp+1,2),'little')+1;until(self,m,ret,20000000);self.assertEqual(m.g(TW['error']),2);m.p('dos64_host_clock_claim',0xa5);r=L.dos64_run(m.m,BR['modal_wait'],1400000000);self.assertEqual(r.status,2,(r.status,hex(r.regs.pc)));v=m.get(BE['br_last'],9);self.assertEqual((v[0],v[1],v[3],v[5]),(3,3,2,0),v.hex());self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(L.bulk_model_size(m.m,path),0xffffffff);guard_C(self,m,ctx,pos);self.assertEqual(reu(m,0x3ff020,576),old);records.append({'allocator_CLOCK_then_recovery':v.hex(),'firstcause2_kept':True,'no_SAVE_Resume':True})
  finally:m.close()
 def test08_current_CFG_drift_refuses_before_SAVE(self):
  m,old,f=initial(self,admit=False)
  try:
   enter(self,m);ctx=m.get('dos64_files_state_start',25);pos=L.save_model_position(m.m,1);bad=bytearray(old);bad[100]^=1;seed(m,b'/usb1/Owned/DOS64.CFG',bad);path=b'/usb1/Owned/CFGBAD.IMG';prepare(self,m,path);press(self,m,13,1400000000);v=m.get(BE['br_last'],9);self.assertEqual((v[0],v[1],v[3]),(3,3,5),v.hex());self.assertEqual(L.bulk_model_size(m.m,path),0xffffffff);guard_C(self,m,ctx,pos);self.assertEqual(reu(m,0x3ff020,576),old);records.append({'currentCFG_drift_before_SAVE':v.hex()})
  finally:m.close()
 def test09_unknown_CLOSE_one_attempt_no_restore_or_Resume(self):
  m,old,f=initial(self,admit=False)
  try:
   enter(self,m);path=b'/usb1/Owned/CLOSEBAD.IMG';prepare(self,m,path);before=L.bulk_model_commands(m.m);L.save_model_fail_close(m.m,2);press(self,m,13,1400000000);v=m.get(BE['br_last'],9);self.assertEqual((v[0],v[4],v[5]),(3,0,0),v.hex());self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(L.bulk_model_size(m.m,path),0xffffffff);self.assertEqual(m.get(BR['saved_files'],25),f['C']);self.assertEqual(L.bulk_model_open(m.m,1),1);closes=sum(L.bulk_model_command(m.m,i,1)==3 for i in range(before,L.bulk_model_commands(m.m)));self.assertEqual(closes,1);self.assertEqual(reu(m,0x3ff020,576),old);records.append({'unknown_CLOSE':v.hex(),'attempts':closes,'privateC_snapshot_retained':True})
  finally:m.close()
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(SequenceUI),unittest.defaultTestLoader.loadTestsFromTestCase(SequenceFaults)]));(P/'SEQUENCE_UI_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'records':records,'scope':'UNIT actualCIA/broker/CUI/controller/allocator/workers; synthetic firmware/media/acceptedlaunchfixture; advisoryFFFF only injected in specifictest; no runtimeSTART/DOS/device'},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
