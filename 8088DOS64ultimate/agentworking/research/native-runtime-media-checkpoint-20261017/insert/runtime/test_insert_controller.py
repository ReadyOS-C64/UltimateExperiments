from pathlib import Path
import os,sys
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;os.environ['DOS64_MEDIA_TEST_ROLE']='runtime'
import unittest,json,zlib,time,ctypes as C
from controller_fixture import initial
from fixture_base import *
from test_online_save import Regs,HD
AC=labels('controller/controller.labels');IW=labels('worker/incoming.labels');records=[]
symbols['ac_entry']=AC['ac_entry'];L.dos64_step.argtypes=[C.c_void_p]

def configure_empty_B(m,old):
 old=bytearray(old);old[524]&=~2;old[525]&=~2;old[264:392]=bytes(128);old[532:536]=bytes(4);old=resign(old)
 m.put('dos64_disk_b_descriptor',bytes(10));m.p(symbols['dos64_disk_readonly']+1,0);m.p(symbols['dos64_disk_dirty']+1,0)
 for n in ['dos64_disk_mount_generation','dos64_disk_content_generation','dos64_disk_clean_mount','dos64_disk_clean_content','dos64_disk_binding']:m.put(symbols[n]+4,bytes(4))
 L.bulk_model_seed(m.m,b'/usb1/Owned/DOS64.CFG',old,len(old))
 for a,b in [(0x3ff020,old),(0x3ff000,headers(old)[0]),(0x3ff500,headers(old)[1])]:L.bulk_reu_seed(m.m,a,b,len(b))
 return old

def request(m,drive,path,flags=1):
 load(m,'controller/controller.prg');q=b'\xa5\1\1\0'+(4194304).to_bytes(4,'little')+bytes([drive,3])+path.ljust(128,b'\0')+bytes([flags]);assert len(q)==139;m.put(AC['_ac_request'],q)

def seed_menu(m):
 b=(P/'MODAL.MNU').read_bytes();assert len(b)==57344
 for a,v in [(0x3da000,b[:0x6000]),(0x3f0000,b[0x6000:])]:L.bulk_reu_seed(m.m,a,v,len(v))

class Tests(unittest.TestCase):
 def setup_case(self,target=1,drive=1,case='mounted'):
  m,old,f=initial(self,target=target,drive=drive,bank=0x18 if target==2 else 0x10,admit=case!='first_B')
  if case=='first_B':old=configure_empty_B(m,old);self.assertFalse(m.call('modal_admit',2_000_000).regs.p&1)
  if case=='ejected':
   q=bytearray(27);q[0]=4;q[1]=drive;q[2]=2;q[15:19]=m.get(symbols['dos64_disk_mount_generation']+4*drive,4);q[19:23]=m.get(symbols['dos64_disk_content_generation']+4*drive,4);m.put('dos64_floppy_request',q);self.assertFalse(m.call('dos64_overlay_floppy_control',3_000_000).regs.p&1)
  seed_menu(m);return m,old,f
 def guard(self,m,before,free):
  spans=sorted([(free,free+368640),(0x3e0000,0x3e0240),(0x3e0300,0x3e0540),(0x3e0600,0x3e0b04),(0x3ff000,0x3ff260),(0x3ff500,0x3ff520)])
  after=reu(m,0,4194304);at=0
  for a,b in spans:self.assertEqual(after[at:a],before[at:a],(hex(at),hex(a)));at=b
  self.assertEqual(after[at:],before[at:])
 def positive(self,target,drive,case='mounted'):
  m,old,f=self.setup_case(target,drive,case)
  try:
   path=b'/sd/Incoming/New image.IMG';image=fat(('CONTROLLER '+case+'\r\n').encode());L.bulk_model_seed(m.m,path,image,len(image));request(m,drive,path)
   ctx=m.get('dos64_files_state_start',25);hd=m.get('hd_state_start',symbols['hd_state_end']-symbols['hd_state_start']);hdb=m.get('hdb_state_start',symbols['hdb_state_end']-symbols['hdb_state_start']);pos=L.save_model_position(m.m,target);high=bytes((i*13+9)&255 for i in range(96));m.put(128,high);before=reu(m,0,4194304);old_desc=m.get('dos64_disk_reu_base'if not drive else'dos64_disk_b_descriptor',10);n=L.bulk_model_commands(m.m)
   r=m.call('ac_entry',1_600_000_000);v=m.get(AC['_ac_result'],9);(P/'LAST_INSERT_CONTROLLER.json').write_text(json.dumps({'result':v.hex(),'A':r.regs.a,'diag':m.g('dos64_native_diag'),'stage':m.g('dos64_floppy_stage_active'),'fq':m.get('dos64_floppy_request',27).hex(),'case':case,'drive':drive,'target':target},indent=2)+'\n')
   self.assertEqual(r.regs.a,1,v.hex());self.assertEqual(v[:7],bytes([2,0,6,0,1,1,1]));self.assertEqual(v[7:9],b'\1\0');self.assertEqual(m.g('dos64_native_diag'),8);self.assertEqual(m.g('dos64_floppy_stage_active'),0)
   desc=m.get('dos64_disk_reu_base'if not drive else'dos64_disk_b_descriptor',10);free=int.from_bytes(desc[:3],'little');self.assertNotEqual(desc[:3],old_desc[:3]);self.assertEqual(desc[9],1);self.assertEqual(reu(m,free,368640),image);self.assertEqual(m.g(symbols['dos64_disk_dirty']+drive),0);self.assertEqual(m.g(symbols['dos64_disk_readonly']+drive),1);self.assertEqual(int.from_bytes(m.get(symbols['dos64_disk_binding']+drive*4,4),'little'),zlib.crc32(image))
   new=m.bytes(b'/usb1/Owned/DOS64.CFG',576);expected=bytearray(old);off=136+128*drive;expected[off:off+128]=path.ljust(128,b'\0');expected[524]|=1<<drive;expected[525]|=1<<drive;expected[528+4*drive:532+4*drive]=zlib.crc32(image).to_bytes(4,'little');expected=resign(expected);self.assertEqual(new,expected);self.assertEqual(reu(m,0x3ff020,576),new);self.assertEqual(m.bytes(b'/usb1/Owned/S0001.OLD',576),old)
   self.assertEqual(m.get('dos64_files_state_start',25),ctx);self.assertEqual(m.get('hd_state_start',len(hd)),hd);self.assertEqual(m.get('hdb_state_start',len(hdb)),hdb);self.assertEqual(L.save_model_position(m.m,target),pos);self.assertEqual(m.get(128,96),high);self.assertEqual(m.get(0x80,2),high[:2]);self.assertEqual(m.bytes(b'/usb1/Owned/C.IMG',len(HD)),HD);self.assertEqual(m.bytes(path,len(image)),image);self.guard(m,before,free)
   cmds=[L.bulk_model_command(m.m,i,1)for i in range(n,L.bulk_model_commands(m.m))];self.assertIn(0x21,cmds);self.assertEqual(m.g('dos64_floppy_token'),2)
   records.append({'case':case,'target':target,'drive':drive,'actual_controller_PREPARE_Incoming_private_receipt_CANCEL_rePREPARE_PLAN_WIRE_BIND_COMMIT':True,'free_arena':hex(free),'C_context_high96_full4MiB_guards':True,'no_host_completed_worker_facts':True})
  finally:m.close()
 def test01_mounted_B_Ctarget1(self):self.positive(1,1)
 def test02_mounted_A_Ctarget2(self):self.positive(2,0)
 def test03_ejected_B(self):self.positive(1,1,'ejected')
 def test04_first_B(self):self.positive(2,1,'first_B')
 def negative(self,case):
  m,old,f=self.setup_case()
  try:
   path=b'/sd/Incoming/Refused.IMG';image=fat(b'REFUSE\r\n')
   if case=='short':image=image[:-1]
   elif case=='geometry':image=bytearray(image);image[11]^=1;image=bytes(image)
   if case!='missing':L.bulk_model_seed(m.m,path,image,len(image))
   request(m,1,path,flags=0 if case=='dirty_no_discard'else 1);ctx=m.get('dos64_files_state_start',25);old42=m.get('dos64_disk_reu_base',10)+m.get('dos64_disk_b_descriptor',32);pos=L.save_model_position(m.m,1)
   r=m.call('ac_entry',1_600_000_000);v=m.get(AC['_ac_result'],9)
   self.assertEqual(r.regs.a,0);self.assertEqual(v[0],3);self.assertEqual(m.bytes(b'/usb1/Owned/DOS64.CFG',576),old);self.assertEqual(reu(m,0x3ff020,576),old);self.assertEqual(m.get('dos64_disk_reu_base',10)+m.get('dos64_disk_b_descriptor',32),old42);self.assertEqual(m.get('dos64_files_state_start',25),ctx);self.assertEqual(L.save_model_position(m.m,1),pos)
   self.assertEqual(L.bulk_model_size(m.m,b'/usb1/Owned/S0001.OLD'),0xffffffff);self.assertEqual(m.g('dos64_floppy_stage_active'),0)
   if v[5]:self.assertEqual(m.g('dos64_native_diag'),8)
   records.append({'negative':case,'actual_controller_refused':v.hex(),'old_mount_and_CFG_preserved':True,'owned_stage_cancelled':True,'C_exact':True})
  finally:m.close()
 def test05_missing_image(self):self.negative('missing')
 def test06_short_image(self):self.negative('short')
 def test07_bad_geometry(self):self.negative('geometry')
 def test08_dirty_requires_discard(self):self.negative('dirty_no_discard')
 def test09_ejected_A(self):self.positive(2,0,'ejected')

if __name__=='__main__':
 start=time.monotonic();r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));(P/'INSERT_CONTROLLER_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'seconds':time.monotonic()-start,'records':records,'scope':'actual complete runtime controller and workers/nativeCOMMIT; synthetic media/CFG, no CUI/cold/DOS/hardware'},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
