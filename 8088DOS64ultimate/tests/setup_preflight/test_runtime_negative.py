from pathlib import Path
import sys,os
D=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(D/'.absent-runtime-negative');assert not Path(sys.pycache_prefix).exists()
import unittest,ctypes as C,struct,json,zlib
from test_capsule import UI,L,prepare,reu
ASSET=[(D/'release-assets'/n).read_bytes()for n in ['START.TPL','START.REL','DOS64.PRG','DOS64.REL','START.INO']]
PATH=[b'/Home/START.TPL',b'/Home/START.REL',b'/Home/DOS64.PRG',b'/Home/DOS64.REL',b'/Home/START.INO']
REPORT=[]
class Job:
 def __init__(self,skip=None):
  self.u=UI();u=self.u;prepare(u);assert u.call('_sq_publish')==1;self.capsule=reu(u);u.f.write('_ns_io_owner',b'\xa5');u.f.write('_ns_capacity',struct.pack('<I',0x400000))
  for k,(p,data)in enumerate(zip(PATH,ASSET)):
   if k+3!=skip:L.bulk_model_seed(u.f.m,p,data,len(data))
 def start(self,k):self.u.f.write('_sl_kind',bytes([k]));self.u.f.write('_sl_timeout',struct.pack('<H',1000));return self.u.call('_sl_begin')
 def poll(self):L.dos64_cia_clock_advance(self.u.f.m,1024);self.u.call('_sl_poll');return self.u.call('_sl_state')
 def result(self):return tuple(self.u.f.read('_sl_result',6))
 def finish(self):
  for _ in range(30000):
   if self.u.call('_sl_state')!=1:return self.result()
   self.poll()
  raise AssertionError('bounded runtime source')
 def phase(self,n):
  for _ in range(30000):
   if self.result()[2]==n:return
   assert self.poll()==1
  raise AssertionError('runtime phase bound')
 def closed_failure(self):
  # Same explicit cleanup contract as SU: close unknown/open source on slot0.
  u=self.u;u.f.write('_bc_slot',b'\0');u.f.write('_br_request',struct.pack('<BBIII',3,0,0,0,0)+bytes(128));u.f.write('_br_now',u.f.read('_ps_ticks',2));assert u.call('_bc_start')==1
  for _ in range(1000):
   L.dos64_cia_clock_advance(u.f.m,1024);u.call('_ps_clock_poll');u.f.write('_br_now',u.f.read('_ps_ticks',2));u.call('_bc_poll')
   if u.call('_bc_files_closed'):return
  raise AssertionError('known close bound')
 def close(self):self.u.close()
class Tests(unittest.TestCase):
 def test_01_real_missing_OPEN_not_zero_length_and_forgery_never_DONE(self):
  for k in [5,6,7]:
   j=Job(skip=k)
   try:
    self.assertEqual(j.start(k),1);self.assertEqual(j.finish()[:2],(3,2));j.u.f.write('_sl_result',b'\2'+bytes(5));self.assertEqual(j.u.call('_sl_state'),3);self.assertEqual(j.start(k),0);j.closed_failure();self.assertEqual(j.u.call('_bc_files_closed'),1)
   finally:j.close()
 def test_02_exact_descriptor_bytes_refuse_resigned_same_CRC(self):
  for k in [4,6]:
   j=Job()
   try:
    data=bytearray(ASSET[k-3]);data[12]^=1;data[60:64]=struct.pack('<I',zlib.crc32(data[:60]));self.assertEqual(zlib.crc32(data),zlib.crc32(ASSET[k-3]));L.bulk_model_seed(j.u.f.m,PATH[k-3],bytes(data),len(data));self.assertEqual(j.start(k),1);self.assertEqual(j.finish()[:2],(3,8))
   finally:j.close()
 def test_03_template_BASIC_and_default131_are_early_refused(self):
  control=int.from_bytes(ASSET[1][24:28],'little')
  for pos in [0,6,control,control+3,control+130]:
   j=Job()
   try:
    data=bytearray(ASSET[0]);data[pos]^=1;L.bulk_model_seed(j.u.f.m,PATH[0],bytes(data),len(data));self.assertEqual(j.start(3),1);self.assertEqual(j.finish()[:2],(3,8))
   finally:j.close()
 def test_04_new_runtime_final_CLOSE_Stop_prevents_private_DONE(self):
  j=Job()
  try:
   self.assertEqual(j.start(7),1);j.phase(13);L.dos64_host_input_model_keys(j.u.f.m,bytes(7)+b'\x80');self.assertEqual(j.finish()[:2],(3,5));self.assertEqual(j.start(7),0)
  finally:j.close()
 def test_05_new_runtime_partial_poison_DMA_refuses_LOAD(self):
  j=Job()
  try:
   self.assertEqual(j.start(7),1);j.phase(3);L.dos64_reu_fail_after(j.u.f.m,0,7);self.assertEqual(j.finish()[:2],(3,3))
  finally:j.close()
 def test_06_captured_kind_timeout_and_capacity_guard(self):
  j=Job()
  try:
   self.assertEqual(j.start(7),1);j.u.f.write('_sl_kind',b'\0');j.u.f.write('_sl_timeout',bytes(2));self.assertEqual(j.finish()[:2],(2,0));j.u.f.write('_sl_kind',b'\7');self.assertEqual(j.start(7),0)
  finally:j.close()
  j=Job()
  try:
   self.assertEqual(j.start(7),1);j.phase(3);j.u.f.write('_ns_capacity',struct.pack('<I',0x800000));self.assertEqual(j.finish()[:2],(3,3))
  finally:j.close()
if __name__=='__main__':
 r=unittest.main(exit=False,verbosity=2).result;(D/'RUNTIME_NEGATIVE_RESULTS.json').write_text(json.dumps({'passed':r.wasSuccessful(),'tests':r.testsRun,'scope':'Actual native source-loader controls from legitimate CIA-selected capsule, no FAT/guest/hardware or full coordinator claim'},indent=2)+'\n');sys.exit(not r.wasSuccessful())
