from pathlib import Path
import os,sys
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;os.environ['DOS64_MEDIA_TEST_ROLE']='runtime'
import unittest,json,zlib,time
from test_insert_controller import Tests as Setup,request,AC,Regs
from fixture_base import *
records=[]
def zero_crc(b):
 b=bytearray(b);b[-4:]=bytes(4);v=zlib.crc32(b);basis={}
 for i in range(32):
  x=bytearray(b);x[-4+i//8]^=1<<(i%8);n=zlib.crc32(x)^v;mask=1<<i
  while n:
   k=n.bit_length()-1
   if k in basis:n^=basis[k][0];mask^=basis[k][1]
   else:basis[k]=(n,mask);break
 n=v;mask=0
 while n:k=n.bit_length()-1;n^=basis[k][0];mask^=basis[k][1]
 b[-4:]=mask.to_bytes(4,'little');assert zlib.crc32(b)==0;return bytes(b)

class Tests(unittest.TestCase):
 def setup_case(self):return Setup.setup_case(self)
 def begin(self,m):
  m.p(511,2);m.p(510,255);L.dos64_set_regs(m.m,Regs(AC['ac_entry'],0xfd,0x71,0x82,0x93,0x24,0,0))
 def loader(self,m,phase):
  self.begin(m)
  for _ in range(8):
   r=L.dos64_run(m.m,AC['_ac_load'],1_600_000_000);self.assertEqual((r.status,r.regs.pc),(2,AC['_ac_load']))
   if r.regs.a==phase:return
   L.dos64_step(m.m)
  self.fail('requested phase not reached')
 def finish(self,m):
  L.dos64_step(m.m);r=L.dos64_run(m.m,0x0300,1_600_000_000);self.assertEqual((r.status,r.regs.pc),(0,0x0300));return m.get(AC['_ac_result'],9)
 def test01_legitimate_zero_CRC(self):
  m,old,f=self.setup_case()
  try:
   p=b'/sd/Incoming/CRC0.IMG';image=zero_crc(fat(b'ZERO CRC COMPLETE CONTROLLER\r\n'));L.bulk_model_seed(m.m,p,image,len(image));request(m,1,p);r=m.call('ac_entry',1_600_000_000);self.assertEqual(r.regs.a,1);self.assertEqual(m.get(symbols['dos64_disk_binding']+4,4),bytes(4));self.assertEqual(m.bytes(b'/usb1/Owned/DOS64.CFG',576)[532:536],bytes(4));self.assertEqual(m.g('dos64_floppy_stage_active'),0);records.append({'actual_whole_controller_CRC0':True})
  finally:m.close()
 def test02_rotate_all_three_arenas(self):
  m,old,f=self.setup_case()
  try:
   ctx=m.get('dos64_files_state_start',25);banks=[]
   for i,drive in enumerate([1,0,1],1):
    p=('/sd/Incoming/ROTATE%d.IMG'%i).encode();image=fat(('ROTATE %d\r\n'%i).encode());L.bulk_model_seed(m.m,p,image,len(image));request(m,drive,p);r=m.call('ac_entry',1_600_000_000);self.assertEqual(r.regs.a,1,m.get(AC['_ac_result'],9).hex());self.assertEqual(int.from_bytes(m.get(AC['_ac_result']+7,2),'little'),i);desc=m.get('dos64_disk_reu_base'if not drive else'dos64_disk_b_descriptor',10);bank=int.from_bytes(desc[:3],'little');banks.append(bank);self.assertEqual(reu(m,bank,368640),image);self.assertEqual(m.get('dos64_files_state_start',25),ctx)
   self.assertEqual(banks,[0x180000,0x380000,0x100000]);records.append({'three_actual_controller_jobs':True,'free_arena_rotation':list(map(hex,banks)),'durable_sequences':[1,2,3],'C_preserved':True})
  finally:m.close()
 def test03_late_staged_image_change_before_PLAN_never_publishes(self):
  m,old,f=self.setup_case()
  try:
   p=b'/sd/Incoming/LATE.IMG';image=fat(b'LATE STAGED CHANGE\r\n');L.bulk_model_seed(m.m,p,image,len(image));request(m,1,p);old42=m.get('dos64_disk_reu_base',10)+m.get('dos64_disk_b_descriptor',32);self.loader(m,3);base=int.from_bytes(m.get(symbols['dos64_floppy_request']+5,3),'little');L.bulk_reu_seed(m.m,base+368639,bytes([image[-1]^1]),1);v=self.finish(m);self.assertEqual(v[0],3,v.hex());self.assertEqual(m.bytes(b'/usb1/Owned/DOS64.CFG',576),old);self.assertEqual(m.get('dos64_disk_reu_base',10)+m.get('dos64_disk_b_descriptor',32),old42);self.assertEqual(L.bulk_model_size(m.m,b'/usb1/Owned/S0001.OLD'),0xffffffff);self.assertEqual(v[5],0);self.assertEqual(m.g('dos64_native_diag'),0xe1);records.append({'late_last_byte_corruption':v.hex(),'no_durable_or_mount_publication':True,'Resume_blocked':True})
  finally:m.close()
 def test04_insert_aux_corruption_after_durable_commit_blocks_old_mount(self):
  m,old,f=self.setup_case()
  try:
   p=b'/sd/Incoming/AUX.IMG';image=fat(b'AUX CRC FAIL\r\n');L.bulk_model_seed(m.m,p,image,len(image));request(m,1,p);old42=m.get('dos64_disk_reu_base',10)+m.get('dos64_disk_b_descriptor',32);ctx=m.get('dos64_files_state_start',25);self.loader(m,6);n=json.loads((P/'CONTROLLER_BUILD.json').read_text())['records'][5]['aux_reu'];b=reu(m,n,1);L.bulk_reu_seed(m.m,n,bytes([b[0]^1]),1);v=self.finish(m);self.assertEqual(v[:2],b'\3\2');self.assertEqual(v[5:7],b'\0\1');self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(m.get('dos64_disk_reu_base',10)+m.get('dos64_disk_b_descriptor',32),old42);self.assertEqual(m.get('dos64_files_state_start',25),ctx);self.assertEqual(m.bytes(b'/usb1/Owned/DOS64.CFG',576)[264:392],p.ljust(128,b'\0'));self.assertEqual(m.g('dos64_floppy_stage_active'),0xa5);self.assertTrue(m.call('modal_release',2_000_000).regs.p&1);records.append({'aux_source_CRC_after_CFG_commit':v.hex(),'old_live_mount_retained':True,'private_stage_retained_no_COMMIT':True,'native_Resume_denied':True,'C_preserved':True})
  finally:m.close()
 def test05_unknown_incoming_CLOSE_has_no_caller_retry_or_CANCEL(self):
  m,old,f=self.setup_case()
  try:
   p=b'/sd/Incoming/CLOSE.IMG';image=fat(b'UNKNOWN CLOSE\r\n');L.bulk_model_seed(m.m,p,image,len(image));request(m,1,p);old42=m.get('dos64_disk_reu_base',10)+m.get('dos64_disk_b_descriptor',32);self.loader(m,5);n=L.bulk_model_commands(m.m);L.save_model_fail_close(m.m,2);v=self.finish(m);cmds=[L.bulk_model_command(m.m,i,1)for i in range(n,L.bulk_model_commands(m.m))];self.assertEqual(cmds,[3]);self.assertEqual(v[0],3);self.assertEqual(v[4:6],b'\0\0');self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(m.g('dos64_floppy_stage_active'),0xa5);self.assertEqual(m.bytes(b'/usb1/Owned/DOS64.CFG',576),old);self.assertEqual(m.get('dos64_disk_reu_base',10)+m.get('dos64_disk_b_descriptor',32),old42);self.assertEqual(L.bulk_model_open(m.m,1),1);self.assertTrue(m.call('modal_release',2_000_000).regs.p&1);records.append({'unknown_Incoming_CLOSE':v.hex(),'exactly_one_CLOSE_no_caller_retry':True,'owned_stage_retained':True,'old_mount_CFG_C_handle_preserved':True,'native_Resume_denied':True})
  finally:m.close()

if __name__=='__main__':
 start=time.monotonic();r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));(P/'INSERT_COMPOSITION_FAULT_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'seconds':time.monotonic()-start,'records':records},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
