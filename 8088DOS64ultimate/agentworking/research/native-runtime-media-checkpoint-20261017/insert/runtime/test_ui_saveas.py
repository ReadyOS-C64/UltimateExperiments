from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-ui-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import ctypes as C,json,unittest,zlib,time,hashlib
from controller_fixture import initial
from fixture_base import *
from test_online_save import Regs,HD
BR=labels('broker/broker.labels');UI=labels('ui/panel.labels');BE=labels('bridge/bridge.labels');symbols.update(BR);symbols['bridge_entry']=BE['bridge_entry'];records=[]
for n,r,a in [('dos64_host_input_model_keys',None,[C.c_void_p,C.c_void_p]),('dos64_step',None,[C.c_void_p]),('dos64_graphics_color_enable',None,[C.c_void_p]),('dos64_graphics_color_peek',C.c_uint8,[C.c_void_p,C.c_uint16])]:f=getattr(L,n);f.restype=r;f.argtypes=a
normal=[8,13,0x83,0x96,0x90,0x92,0x94,0x81,*map(ord,'3wa4zse'),0,*map(ord,'5rd6cftx'),*map(ord,'7yg8bhuv'),*map(ord,'9ij0mkon'),*map(ord,'+pl-.:@,'),ord('\\'),ord('*'),ord(';'),0x84,0,ord('='),ord('^'),ord('/'),ord('1'),9,0,ord('2'),ord(' '),0,ord('q'),27]
assert len(normal)==64

def keys(m,b):L.dos64_host_input_model_keys(m.m,C.create_string_buffer(bytes(b)))
def loop(test,m,budget=5000000):
 L.dos64_step(m.m);r=L.dos64_run(m.m,BR['modal_wait'],budget)
 if r.status!=2:(P/'EARLY_NATIVE_FAILURE.json').write_text(json.dumps({'status':r.status,'pc':hex(r.regs.pc),'sp':r.regs.sp,'p':r.regs.p,'bridge_intent':m.get(BE['br_intent'],133).hex(),'bridge_result':m.get(BE['br_last'],9).hex(),'bridge_busy':m.g(BE['br_busy']),'stage':m.get('dos64_native_diag',6).hex(),'controller_result':m.get(labels('controller/controller.labels')['_ac_result'],9).hex(),'controller_active':m.g(labels('controller/controller.labels')['ac_active']),'native_error':m.g('sav_error'),'bridge_bytes':m.get(0x6000,12).hex(),'stack':m.get(0x1e0,32).hex()},indent=2)+'\n')
 test.assertEqual(r.status,2,(r.status,hex(r.regs.pc),m.g('dos64_native_diag'),m.get(BE['br_last'],9).hex()));return r

def press(test,m,c,budget=5000000):
 keys(m,bytes(8));loop(test,m)
 shift=65<=c<=90;raw=c+32 if shift else c;index=normal.index(raw);b=bytearray(8);b[index//8]|=1<<(index%8)
 if shift:b[1]|=128
 keys(m,b);return loop(test,m,budget)

def glyph(c):
 if 97<=c<=122:return c-96
 if c==64:return 0
 if c==91:return 27
 if c==93:return 29
 return c
class Tests(unittest.TestCase):
 def complete(self,target=1,drive=1,bank=0x10,collision=False,fault=None,forge=False,cancel=False):
  m,old,facts=initial(self,target=target,drive=drive,bank=bank,admit=False)
  try:
   if collision:L.bulk_model_seed(m.m,facts['path'],b'KEEP EXISTING FILE',18)
   L.dos64_graphics_color_enable(m.m)
   body=(P/'MODAL.MNU').read_bytes()
   for a,b in [(0x3da000,body[:0x6000]),(0x3f0000,body[0x6000:])]:L.bulk_reu_seed(m.m,a,b,len(b))
   before=reu(m,0,4194304);context=m.get('dos64_files_state_start',25);position=L.save_model_position(m.m,target);high=bytes((i*11+17)&255 for i in range(96));m.put(128,high);load(m,'broker/broker.prg')
   ret=symbols['fixture_return']-1;m.p(0x1ff,ret>>8);m.p(0x1fe,ret&255);keys(m,bytes(8));L.dos64_set_regs(m.m,Regs(BR['modal_entry'],0xfd,0x71,0x82,0x93,0x24,0,0));r=L.dos64_run(m.m,BR['modal_wait'],5000000)
   self.assertEqual(r.status,2,(r.status,hex(r.regs.pc),m.g('dos64_native_diag')));self.assertEqual(m.get(UI['_mu_view']+1,128),old[136:264]);self.assertEqual(m.get(UI['_mu_view']+130,128),old[264:392]);self.assertEqual(m.g('dos64_native_diag'),8)
   keys(m,bytes(8));loop(self,m);press(self,m,ord('b'if drive else'a'));press(self,m,ord('n'));self.assertEqual(m.get(UI['_mu_result'],1),b'\3')
   for i in range(len(old[136+drive*128:264+drive*128].split(b'\0',1)[0].rsplit(b'/',1)[0])+1):press(self,m,8)
   path=b'/usb1/Owned/SAVE0001.IMG'
   for c in path:press(self,m,c)
   if fault:
    offset=0x6000 if fault=='controller_source'else 0xa00;addr=0x3f0000 if offset==0x6000 else 0x3daa00;original=reu(m,addr,1);L.bulk_reu_seed(m.m,addr,bytes([original[0]^1]),1);commands_before=L.bulk_model_commands(m.m);keys(m,bytes(8));loop(self,m);keys(m,bytes([2,0,0,0,0,0,0,0]));L.dos64_step(m.m);r=L.dos64_run(m.m,symbols['fixture_return'],1400000000)
    self.assertEqual(r.status,0,(fault,r.status,hex(r.regs.pc)));self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(m.g(BR['ui_ready']),0);self.assertEqual(m.get(0x400,35),b'DISK CONTROL FAILED. KEEP POWER ON.');self.assertEqual(m.get('dos64_files_state_start',25),context);self.assertEqual(L.save_model_position(m.m,target),position);self.assertTrue(m.call('modal_release',2000000).regs.p&1)
    if fault=='controller_source':self.assertEqual(L.bulk_model_commands(m.m),commands_before);self.assertEqual(reu(m,0x3ff020,576),old);self.assertEqual(m.g(symbols['dos64_disk_dirty']+drive),1);self.assertEqual(m.g(BE['br_last']),0)
    else:self.assertEqual(m.bytes(path,368640),facts['working']);self.assertEqual(m.g(symbols['dos64_disk_dirty']+drive),0);self.assertEqual(m.g(BE['br_success']),1)
    records.append({'fault':fault,'no_incomplete_CUI_execution':True,'native_fallback_screen':True,'native_release_denied':True,'C_exact':True});return
   started=time.monotonic()
   if forge or cancel:
    keys(m,bytes(8));loop(self,m);keys(m,bytes([2,0,0,0,0,0,0,0]));L.dos64_step(m.m);stop=BE['bridge_entry']if forge else labels('controller/controller.labels')['ac_entry'];r=L.dos64_run(m.m,stop,5000000);self.assertEqual(r.status,2,(r.status,hex(r.regs.pc)))
    if forge:m.put(UI['_mu_event'],b'\xff\xff\6\0\0'+b'/usb1/Owned/WRONG.IMG'.ljust(128,b'\0'))
    else:keys(m,bytes(7)+b'\x80')
    r=L.dos64_run(m.m,BR['modal_wait'],1400000000);self.assertEqual(r.status,2,(r.status,hex(r.regs.pc)))
   else:press(self,m,13,1400000000)
   elapsed=time.monotonic()-started
   d={'native_stage':m.g('dos64_native_diag'),'UI_result':m.get(UI['_mu_result'],6).hex(),'bridge_result':m.get(BE['br_last'],9).hex(),'bridge_error':m.g(BE['br_error']),'bridge_success':m.g(BE['br_success']),'wire_commands':L.bulk_model_commands(m.m),'elapsed':elapsed};(P/'LAST_UI_DIAGNOSTIC.json').write_text(json.dumps(d,indent=2)+'\n')
   if cancel:
    self.assertEqual(d['native_stage'],8,d);self.assertEqual(d['bridge_error'],8,d);self.assertEqual(d['bridge_success'],0);self.assertEqual(m.get(UI['_mu_result'],1),b'\5');self.assertEqual(L.bulk_model_size(m.m,path),0xffffffff);self.assertEqual(m.get('dos64_files_state_start',25),context);self.assertEqual(reu(m,0x3ff020,576),old);self.assertEqual(m.g(symbols['dos64_disk_dirty']+drive),1)
    press(self,m,13);self.assertEqual(m.get(UI['_mu_result'],1),b'\1');keys(m,bytes(8));loop(self,m);keys(m,bytes([0,0,2,0,0,0,0,0]));L.dos64_step(m.m);r=L.dos64_run(m.m,symbols['fixture_return'],5000000);self.assertEqual(r.status,0,(r.status,hex(r.regs.pc)));self.assertEqual(m.g('dos64_native_diag'),5);self.assertEqual(m.g('dos64_cache_limit'),32);self.assertEqual(m.get('dos64_files_state_start',25),context);self.assertEqual(L.save_model_position(m.m,target),position);records.append(d|{'physical_STOP_before_controller':True,'no_image_created':True,'Return_then_private_Resume':True,'C_exact':True});return
   if collision:
    self.assertEqual(d['native_stage'],0xe1,d);self.assertEqual(d['bridge_success'],0,d);self.assertEqual(d['bridge_error'],4,d);self.assertEqual(m.get(UI['_mu_result'],1),b'\5');self.assertEqual(m.bytes(facts['path'],18),b'KEEP EXISTING FILE');self.assertEqual(reu(m,0x3ff020,576),old);self.assertEqual(m.get('dos64_files_state_start',25),context);self.assertEqual(L.save_model_position(m.m,target),position);self.assertEqual(m.g(symbols['dos64_disk_dirty']+drive),1);self.assertEqual(m.get(UI['_mu_view']+1+129*drive,128),old[136+drive*128:264+drive*128]);self.assertTrue(m.call('modal_release',2000000).regs.p&1);records.append(d|{'existing_file_preserved':True,'terminal_UI_blocked':True,'C_exact':True});return
   self.assertEqual(d['native_stage'],8,d);self.assertEqual(d['bridge_success'],1,d);self.assertEqual(d['bridge_error'],0,d);self.assertEqual(m.get(UI['_mu_result'],1),b'\1',d);self.assertEqual(m.get(UI['_mu_view']+1+129*drive,128),path.ljust(128,b'\0'));self.assertEqual(m.g(UI['_mu_view']+129*drive),1);self.assertEqual(m.bytes(path,368640),facts['working']);self.assertEqual(m.get('dos64_files_state_start',25),context);self.assertEqual(L.save_model_position(m.m,target),position)
   new=m.bytes(b'/usb1/Owned/DOS64.CFG',576);self.assertEqual(new[136+drive*128:264+drive*128],path.ljust(128,b'\0'));self.assertEqual(reu(m,0x3ff020,576),new);self.assertEqual(m.g(symbols['dos64_disk_dirty']+drive),0);self.assertEqual(m.g(BR['modal_context']),1);self.assertEqual(m.get(128,96),high)
   screen=m.get(0x400,1000);saved=bytes(glyph(c)for c in b'Saved');self.assertEqual(screen[6*40+12:6*40+17],saved)
   after=reu(m,0,4194304)
   for a,b in [(0,0x3e0000),(0x3e0b04,0x3e2000),(0x3e23e8,0x3ff000),(0x3ff260,0x3ff500),(0x3ff520,0x400000)]:self.assertEqual(after[a:b],before[a:b],(hex(a),hex(b)))
   self.assertEqual(m.bytes(b'/usb1/Media/A.IMG',368640),A);self.assertEqual(m.bytes(b'/sd/Media/B.IMG',368640),OLD_B);self.assertEqual(m.bytes(b'/usb1/Owned/C.IMG',len(HD)),HD);self.assertEqual(L.bulk_model_size(m.m,b'/usb1/Owned/WRONG.IMG'),0xffffffff);records.append(d|{'forged_public_event_ignored':forge,'C_exact':True,'all4M_guards':True,'actual_CIA_path':True,'UI_code_reloaded_and_WAIT_ticket_consumed':True,'new_path_exact':True})
  finally:m.close()
 def test_01_B38_Ctarget1(self):self.complete()
 def test_02_A18_Ctarget2(self):self.complete(2,0,0x18)
 def test_03_collision_C_preserved_terminal_UI(self):self.complete(collision=True)
 def test_07_CIA_Stop_before_job_then_Return_and_Resume(self):self.complete(cancel=True)
 def test_08_public_event_forgery_after_take_uses_private_capture(self):self.complete(forge=True)
 def test_04_controller_CRC_failure_uses_native_error_screen(self):self.complete(fault='controller_source')
 def test_05_CUI_reload_CRC_failure_uses_native_error_screen(self):self.complete(fault='ui_reload_source')

 def test_06_initial_bridge_and_CUI_CRC_refuse_before_execution(self):
  for kind in ['bridge','ui']:
   with self.subTest(kind=kind):
    m,old,facts=initial(self,admit=False)
    try:
     L.dos64_graphics_color_enable(m.m);body=bytearray((P/'MODAL.MNU').read_bytes());offset=json.loads((P/'CONTROLLER_BUILD.json').read_text())['core_end']if kind=='bridge'else 0xa00;body[offset]^=1
     for a,b in [(0x3da000,bytes(body[:0x6000])),(0x3f0000,bytes(body[0x6000:]))]:L.bulk_reu_seed(m.m,a,b,len(b))
     context=m.get('dos64_files_state_start',25);commands=L.bulk_model_commands(m.m);load(m,'broker/broker.prg');ret=symbols['fixture_return']-1;m.p(0x1ff,ret>>8);m.p(0x1fe,ret&255);keys(m,bytes(8));L.dos64_set_regs(m.m,Regs(BR['modal_entry'],0xfd,0x71,0x82,0x93,0x24,0,0));r=L.dos64_run(m.m,symbols['fixture_return'],5000000)
     self.assertEqual(r.status,0,(kind,r.status,hex(r.regs.pc)));self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(m.g(BR['ui_ready']),0);self.assertEqual(m.get(0x400,35),b'DISK CONTROL FAILED. KEEP POWER ON.');self.assertEqual(L.bulk_model_commands(m.m),commands);self.assertEqual(m.get('dos64_files_state_start',25),context);self.assertEqual(reu(m,0x3ff020,576),old);self.assertEqual(L.bulk_model_size(m.m,facts['path']),0xffffffff);records.append({'initial_asset':kind,'CRC_refused':True,'native_fallback_screen':True,'no_FILE_job':True})
    finally:m.close()
 def test_09_direct_bridge_public_forgery_without_private_WAIT_has_no_FILE_job(self):
  m,old,facts=initial(self,admit=False)
  try:
   L.dos64_graphics_color_enable(m.m);body=(P/'MODAL.MNU').read_bytes()
   for a,b in [(0x3da000,body[:0x6000]),(0x3f0000,body[0x6000:])]:L.bulk_reu_seed(m.m,a,b,len(b))
   load(m,'broker/broker.prg');ret=symbols['fixture_return']-1;m.p(0x1ff,ret>>8);m.p(0x1fe,ret&255);keys(m,bytes(8));L.dos64_set_regs(m.m,Regs(BR['modal_entry'],0xfd,0x71,0x82,0x93,0x24,0,0));r=L.dos64_run(m.m,BR['modal_wait'],5000000);self.assertEqual(r.status,2);before=L.bulk_model_commands(m.m);context=m.get('dos64_files_state_start',25)
   m.put(UI['_mu_event'],b'\1\0\2\1\0'+facts['path'].ljust(128,b'\0'));r=m.call('bridge_entry',5000000);self.assertTrue(r.regs.p&1);self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(L.bulk_model_commands(m.m),before);self.assertEqual(m.get('dos64_files_state_start',25),context);self.assertEqual(reu(m,0x3ff020,576),old);self.assertEqual(L.bulk_model_size(m.m,facts['path']),0xffffffff);self.assertTrue(m.call('modal_release',2000000).regs.p&1);records.append({'forged_public_event_without_private_WAIT_refused':True,'no_FILE_job':True,'C_exact':True})
  finally:m.close()
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));(P/'UI_TEST_RESULT.json').write_text(json.dumps({'pass':r.wasSuccessful(),'tests':r.testsRun,'records':records,'scope':'real CIA+native broker/UI/bridge/controller/worker; syntheticcfg/media/headers; no coldSTART/DOS/physical; corrected c508 STOP source; sequence allocation pending'},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
