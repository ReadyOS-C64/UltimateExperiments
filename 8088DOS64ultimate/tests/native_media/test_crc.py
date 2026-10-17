from pathlib import Path
import sys,os
sys.dont_write_bytecode=True
sys.pycache_prefix=str(Path.cwd()/('.absent-crc-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import ctypes as C, unittest, zlib, random, json, time, hashlib
from test_online_save import Machine,L,Regs,symbols,A,HD
records=[]
def raw(m):return int.from_bytes(m.get('dos64_export_crc_raw',4),'little')
def finish(m):
 maximum=0
 for count in range(250000):
  if not m.g('sav_borrowed'):return count,maximum
  before=L.dos64_get_regs(m.m).cycles;m.call('dos64_native_tick',220000);maximum=max(maximum,L.dos64_get_regs(m.m).cycles-before)
 raise AssertionError('bounded actual native completion')
def new_path(m,path):
 m.path=path;m.p('dos64_export_path_len',len(path)+1);m.put('dos64_export_path',path+b'\0');m.p(symbols['dos64_native_diag']+3,7)
class Tests(unittest.TestCase):
 def test_01_standard_and_random_feed_preserves_page_index(self):
  m=Machine()
  try:
   m.call('dos64_native_tick',2000000)
   self.assertEqual(m.g('sav_borrowed'),1)
   vectors=[b'',b'123456789',bytes(range(256)),bytes(reversed(range(256))),random.Random(0xc64).randbytes(1024)]
   for data in vectors:
    m.put('dos64_export_crc_raw',b'\xff'*4)
    for i,value in enumerate(data):
     page_index=(i*37+19)&255;ret=symbols['fixture_return']-1;m.p(0x1ff,ret>>8);m.p(0x1fe,ret&255)
     L.dos64_set_regs(m.m,Regs(symbols['export_crc_byte'],0xfd,value,0x77,page_index,0x24,0,0));result=L.dos64_run(m.m,symbols['fixture_return'],2000)
     self.assertEqual(result.status,0);self.assertEqual(result.regs.y,page_index)
    self.assertEqual(raw(m)^0xffffffff,zlib.crc32(data))
   records.append({'case':'feed','vectors':[len(x) for x in vectors],'known_123456789':'cbf43926','Y_preserved':True})
  finally:m.close()
 def test_02_complete_C_online_export_crc_and_context(self):
  m=Machine(target=1,warm=True)
  try:
   context=m.get('dos64_files_state_start',25);tags=m.get('hd_state_start',symbols['hd_state_end']-symbols['hd_state_start']);reu=C.create_string_buffer(4194304);self.assertEqual(L.dos64_reu_read(m.m,0,reu,len(reu)),1)
   m.call('dos64_native_tick',2000000);polls,maximum=finish(m)
   self.assertEqual(m.g('dos64_export_state'),2);self.assertEqual(m.g('dos64_export_verified'),1);self.assertEqual(m.g(symbols['dos64_native_diag']+4),0xa5)
   self.assertEqual(raw(m)^0xffffffff,zlib.crc32(A));self.assertEqual(m.bytes(m.path,len(A)),A);self.assertEqual(m.bytes(b'/usb1/Owned/C.IMG',len(HD)),HD)
   self.assertEqual(m.get('dos64_files_state_start',25),context);self.assertEqual(m.get('hd_state_start',len(tags)),tags);self.assertEqual(L.save_model_position(m.m,1),12345)
   after=C.create_string_buffer(len(reu));self.assertEqual(L.dos64_reu_read(m.m,0,after,len(after)),1);self.assertEqual(after.raw,reu.raw)
   records.append({'case':'C_online_verified','polls':polls,'max_poll_cycles':maximum,'CRC32':'%08x'%zlib.crc32(A),'whole_REU_equal':True,'C_context_equal':True})
  finally:m.close()
 def test_03_partial_cancel_then_fresh_verified_save(self):
  m=Machine()
  try:
   context=m.get('dos64_files_state_start',25);m.call('dos64_native_tick',2000000)
   for i in range(250000):
    if m.g('dos64_export_phase')==8 and m.g('export_page')==1:break
    self.assertEqual(m.g('sav_borrowed'),1);m.call('dos64_native_tick',220000)
   else:self.fail('did not reach actual first256byte compare')
   partial=raw(m);self.assertEqual(partial^0xffffffff,zlib.crc32(A[:256]));m.p(symbols['dos64_native_diag']+3,9);finish(m)
   self.assertEqual(m.g('dos64_export_verified'),0);self.assertEqual(raw(m),partial);self.assertEqual(m.get('dos64_files_state_start',25),context)
   new_path(m,b'/usb1/Owned/SECOND.IMG');m.call('dos64_native_tick',2000000)
   for i in range(100):
    if m.g('dos64_export_state')==1:break
    m.call('dos64_native_tick',220000)
   self.assertEqual(m.g('dos64_export_cancel'),0);self.assertEqual(raw(m),0xffffffff)
   polls,maximum=finish(m);self.assertEqual(m.g('dos64_export_verified'),1);self.assertEqual(raw(m)^0xffffffff,zlib.crc32(A));self.assertEqual(m.bytes(m.path,len(A)),A);self.assertEqual(m.get('dos64_files_state_start',25),context)
   records.append({'case':'partial_cancel_then_second','partial_bytes':256,'first_not_verified':True,'second_polls':polls,'max_poll_cycles':maximum,'second_crc':'%08x'%zlib.crc32(A)})
  finally:m.close()
 def test_04_changed_file_first_compare_is_not_receipt(self):
  m=Machine()
  try:
   context=m.get('dos64_files_state_start',25);m.call('dos64_native_tick',2000000)
   for i in range(250000):
    if m.g('dos64_export_phase')==12:break
    self.assertEqual(m.g('sav_borrowed'),1);m.call('dos64_native_tick',220000)
   else:self.fail('did not reach actual reopened INFO')
   changed=bytes([A[0]^1])+A[1:];L.bulk_model_seed(m.m,m.path,changed,len(changed));polls,maximum=finish(m)
   self.assertEqual(m.g('dos64_export_verified'),0);self.assertEqual(m.g('dos64_export_error'),4);self.assertEqual(raw(m),0xffffffff);self.assertEqual(m.get('dos64_files_state_start',25),context)
   records.append({'case':'changed_file_compare_fail','polls':polls,'CRC32_is_partial_not_receipt':True,'raw_unchanged':'ffffffff'})
  finally:m.close()
 def test_05_complete_zero_CRC_is_valid(self):
  # Independent zlib linear patch construction, not the target CRC algorithm.
  initial=A[:-4]+bytes(4);base=zlib.crc32(initial);basis={}
  for i in range(32):
   patch=(1<<i).to_bytes(4,'little');column=zlib.crc32(A[:-4]+patch)^base;mask=1<<i
   while column:
    bit=column.bit_length()-1
    if bit in basis:column^=basis[bit][0];mask^=basis[bit][1]
    else:basis[bit]=(column,mask);break
  target=base;mask=0
  while target:
   bit=target.bit_length()-1;target^=basis[bit][0];mask^=basis[bit][1]
  data=A[:-4]+mask.to_bytes(4,'little');self.assertEqual(zlib.crc32(data),0)
  m=Machine()
  try:
   context=m.get('dos64_files_state_start',25);L.bulk_reu_seed(m.m,0x100000,data,len(data));m.call('dos64_native_tick',2000000);polls,maximum=finish(m)
   self.assertEqual(m.g('dos64_export_verified'),1);self.assertEqual(m.g('dos64_export_state'),2);self.assertEqual(raw(m),0xffffffff);self.assertEqual(m.bytes(m.path,len(data)),data);self.assertEqual(m.get('dos64_files_state_start',25),context)
   records.append({'case':'full_zero_CRC_valid','CRC32':'00000000','patch_hex':data[-4:].hex(),'verified':True,'polls':polls,'max_poll_cycles':maximum})
  finally:m.close()
if __name__=='__main__':
 start=time.monotonic();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));Path('CRC_RESULT.json').write_text(json.dumps({'successful':result.wasSuccessful(),'tests':result.testsRun,'seconds':time.monotonic()-start,'receipts':records},indent=2)+'\n');sys.exit(not result.wasSuccessful())
