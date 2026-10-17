from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-controller-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import ctypes as C,json,unittest,zlib,hashlib,time
from controller_fixture import initial
from fixture_base import *
from test_online_save import HD
AC=labels('controller/controller.labels');BB=labels('binding/binding.labels');symbols.update(AC);reports=[]
for n,r,a in [('bind_watch',None,[C.c_void_p,C.c_uint16,C.c_uint16,C.c_uint32,C.c_uint8]),('bind_seen',C.c_uint8,[C.c_void_p]),('bind_clean_snapshot',C.c_uint8,[C.c_void_p,C.c_void_p]),('bind_wire_after_clean',C.c_uint64,[C.c_void_p])]:f=getattr(L,n);f.restype=r;f.argtypes=a
class Tests(unittest.TestCase):
 def complete(self,target,drive,bank):
  m,old,facts=initial(self,target,drive,bank)
  try:
   container=(P/'WORKERS.MNU').read_bytes()
   for a,b in [(0x3da000,container[:0x6000]),(0x3f0000,container[0x6000:])]:L.bulk_reu_seed(m.m,a,b,len(b))
   load(m,'controller/controller.prg');path=facts['path'];m.put(AC['_ac_request'],b'\xa5\0\1\0'+(4194304).to_bytes(4,'little')+bytes([drive,2])+path.ljust(128,b'\0'))
   whole=reu(m,0,4194304);high=bytes((i*7+33)&255 for i in range(96));m.put(128,high);L.bind_watch(m.m,symbols['dos64_disk_dirty']+drive,BB['_mb_clean'],65536,0)
   started=time.monotonic();r=m.call('ac_entry',1400000000);result=m.get(AC['_ac_result'],9);d={'target':target,'drive':drive,'bank':bank,'result':result.hex(),'returnA':r.regs.a,'stage':m.g('dos64_native_diag'),'wire_commands':L.bulk_model_commands(m.m),'elapsed':time.monotonic()-started};(P/'LAST_DIAGNOSTIC.json').write_text(json.dumps(d,indent=2)+'\n')
   self.assertEqual(r.regs.a,1,d);self.assertEqual(result[:2],b'\2\0');self.assertEqual(result[4:7],b'\1\1\1');self.assertEqual(result[7:9],b'\1\0');self.assertEqual(m.get(128,96),high);self.assertEqual(r.regs.p&0xcd,0x24&0xcd);self.assertEqual(m.g('ac_active'),0)
   self.assertEqual(m.get('dos64_files_state_start',25),facts['C']);self.assertEqual(m.get('hd_state_start',len(facts['HD'])),facts['HD']);self.assertEqual(L.save_model_position(m.m,target),12345)
   self.assertEqual(m.bytes(path,368640),facts['working']);self.assertEqual(m.bytes(b'/usb1/Media/A.IMG',368640),A);self.assertEqual(m.bytes(b'/sd/Media/B.IMG',368640),OLD_B);self.assertEqual(m.bytes(b'/usb1/Owned/C.IMG',len(HD)),HD)
   new=m.bytes(b'/usb1/Owned/DOS64.CFG',576);self.assertNotEqual(old,new);self.assertEqual(new,resign(new));self.assertEqual(reu(m,0x3ff020,576),new);self.assertEqual(new[136+drive*128:264+drive*128],path.ljust(128,b'\0'));self.assertEqual(new[528+drive*4:532+drive*4],zlib.crc32(facts['working']).to_bytes(4,'little'))
   self.assertEqual(m.g(symbols['dos64_disk_dirty']+drive),0);self.assertEqual(m.g(symbols['dos64_disk_readonly']+drive),0);self.assertEqual(L.bind_seen(m.m),1);self.assertEqual(L.bind_wire_after_clean(m.m),0);b=C.create_string_buffer(640);self.assertEqual(L.bind_clean_snapshot(m.m,b),1);self.assertEqual(b.raw[32:608],new)
   after=reu(m,0,4194304)
   for a,b in [(0,0x3e0000),(0x3e0b04,0x3ff000),(0x3ff260,0x3ff500),(0x3ff520,0x400000)]:self.assertEqual(after[a:b],whole[a:b],(hex(a),hex(b)))
   self.assertEqual(L.bulk_model_open(m.m,target),1);self.assertEqual(L.bulk_model_open(m.m,3-target),0);reports.append(d|{'image_sha256':hashlib.sha256(facts['working']).hexdigest(),'cfg_sha256':hashlib.sha256(new).hexdigest(),'C_exact':True,'all_REU_guards':True,'one_controller_entry':True})
  finally:m.close()
 def faults(self,phase):
  m,old,facts=initial(self)
  try:
   container=bytearray((P/'WORKERS.MNU').read_bytes());rec=json.loads((P/'CONTROLLER_BUILD.json').read_text())['records'][phase-1];container[rec['logical_offset']]^=1
   for a,b in [(0x3da000,container[:0x6000]),(0x3f0000,container[0x6000:])]:L.bulk_reu_seed(m.m,a,bytes(b),len(b))
   load(m,'controller/controller.prg');m.put(AC['_ac_request'],b'\xa5\0\1\0'+(4194304).to_bytes(4,'little')+bytes([1,2])+facts['path'].ljust(128,b'\0'));before=reu(m,0,4194304);high=m.get(128,96);m.put(0x9de0,bytes([0x97])*32)
   r=m.call('ac_entry',1400000000);result=m.get(AC['_ac_result'],9);self.assertEqual(r.regs.a,0);self.assertEqual(result[:2],b'\3\2');self.assertEqual(result[4:6],b'\0\0');self.assertEqual(m.get(0x9de0,32),bytes([0x97])*32);self.assertEqual(m.get(128,96),high);self.assertEqual(m.get('dos64_files_state_start',25),facts['C']);self.assertEqual(L.save_model_position(m.m,1),12345);self.assertEqual(m.g(symbols['dos64_disk_dirty']+1),1)
   self.assertEqual(reu(m,0x3ff020,576),old);self.assertEqual(reu(m,0x3ff000,32),before[0x3ff000:0x3ff020]);self.assertEqual(reu(m,0x3ff500,32),before[0x3ff500:0x3ff520]);saved=L.bulk_model_size(m.m,facts['path'])
   if phase<3:self.assertEqual(saved,0xffffffff)
   else:self.assertEqual(m.bytes(facts['path'],368640),facts['working'])
   current=m.bytes(b'/usb1/Owned/DOS64.CFG',576)
   if phase==4:self.assertNotEqual(current,old);self.assertEqual(result[6],1)
   else:self.assertEqual(current,old);self.assertEqual(result[6],0)
   self.assertTrue(m.call('modal_release',2000000).regs.p&1,'denied controller resume must block native broker release')
   reports.append({'corrupt_phase':phase,'result':result.hex(),'file_size':saved,'C_exact':True,'live_CFG_old':True,'dirty_retained':True,'outer_stack_guard':True})
  finally:m.close()
 def test_03_corrupt_WIRE_asset(self):self.faults(1)
 def test_04_corrupt_SAVE_asset(self):self.faults(2)
 def test_05_corrupt_PLAN_asset(self):self.faults(3)
 def test_06_corrupt_BIND_asset_after_commit(self):self.faults(4)
 def test_07_destination_collision(self):
  m,old,facts=initial(self)
  try:
   original=b'KEEP THIS EXISTING FILE';L.bulk_model_seed(m.m,facts['path'],original,len(original));container=(P/'WORKERS.MNU').read_bytes()
   for a,b in [(0x3da000,container[:0x6000]),(0x3f0000,container[0x6000:])]:L.bulk_reu_seed(m.m,a,b,len(b))
   load(m,'controller/controller.prg');m.put(AC['_ac_request'],b'\xa5\0\1\0'+(4194304).to_bytes(4,'little')+bytes([1,2])+facts['path'].ljust(128,b'\0'));high=m.get(128,96);r=m.call('ac_entry',100000000)
   result=m.get(AC['_ac_result'],9);self.assertEqual(r.regs.a,0);self.assertEqual(result[:3],b'\3\4\2');self.assertNotEqual(result[3],0);self.assertEqual(result[4:7],b'\1\0\0');self.assertEqual(m.bytes(facts['path'],len(original)),original);self.assertEqual(reu(m,0x3ff020,576),old);self.assertEqual(m.bytes(b'/usb1/Owned/DOS64.CFG',576),old);self.assertEqual(m.get('dos64_files_state_start',25),facts['C']);self.assertEqual(m.get(128,96),high);self.assertEqual(m.g(symbols['dos64_disk_dirty']+1),1);self.assertEqual(L.save_model_position(m.m,1),12345);reports.append({'existing_destination_preserved':True,'result':result.hex(),'terminal_stage_retained':True,'known_C_closed_and_preserved':True,'C_exact':True,'dirty_retained':True})
  finally:m.close()
 def test_01_B38_Ctarget1(self):self.complete(1,1,0x10)
 def test_02_A18_Ctarget2(self):self.complete(2,0,0x18)
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));(P/'CONTROLLER_TEST_RESULT.json').write_text(json.dumps({'pass':r.wasSuccessful(),'tests':r.testsRun,'reports':reports,'scope':'real native unitrole/controller; modeled UCI/REU; synthetic consumed launch headers; no UI/DOS/physical acceptance'},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
