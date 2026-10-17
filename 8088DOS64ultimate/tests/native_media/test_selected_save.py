from pathlib import Path
import sys,os
sys.dont_write_bytecode=True;sys.pycache_prefix=str(Path.cwd()/('.absent-selected-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import ctypes as C,json,hashlib,unittest,zlib
from test_online_save import Machine,L,symbols,A,HD
P=Path.cwd();B=bytes(x^0xa7 for x in A);receipts=[]
def desc(bank):return bytes([0,0,bank,0xd0,2,40,0,2,9,1])
def setup(drive,bank,target=2,readonly=0,dirty=1):
 m=Machine(target=target)
 other=0x18 if bank!=0x18 else 0x10
 abank=bank if drive==0 else other;bbank=bank if drive==1 else other
 m.put('dos64_disk_reu_base',desc(abank));m.put('dos64_disk_b_descriptor',desc(bbank))
 L.bulk_reu_seed(m.m,abank<<16,A,len(A));L.bulk_reu_seed(m.m,bbank<<16,B,len(B))
 m.put('dos64_disk_mount_generation',bytes.fromhex('78563412f0debc9a'));m.put('dos64_disk_content_generation',bytes.fromhex('21436587a9cbed0f'))
 m.p(symbols['dos64_disk_readonly']+drive,readonly);m.p(symbols['dos64_disk_dirty']+drive,dirty)
 m.p('sav_drive',drive);m.p('dos64_export_bank',bank)
 m.path=('/usb1/Owned/SAVE-%d-%02X.IMG'%(drive,bank)).encode();m.p('dos64_export_path_len',len(m.path)+1);m.put('dos64_export_path',m.path+b'\0')
 return m
def finish(m):
 for i in range(250000):
  if not m.g('sav_borrowed'):return i
  m.call('dos64_native_tick',200000)
 raise AssertionError('bounded save did not terminate')
def image(m):return m.get('dos64_disk_reu_base',10)+m.get('dos64_disk_b_descriptor',32)
class Tests(unittest.TestCase):
 def test_01_A_B_all_three_arenas_full_output_and_C_context(self):
  for drive in (0,1):
   for bank in (0x10,0x18,0x38):
    with self.subTest(drive=drive,bank=bank):
     m=setup(drive,bank,target=1 if bank==0x38 else 2)
     try:
      before=m.get('dos64_files_state_start',25);media=image(m);re=C.create_string_buffer(4*1024*1024);assert L.dos64_reu_read(m.m,0,re,len(re))
      m.call('dos64_native_tick',2000000);self.assertEqual(m.g('sav_borrowed'),1);self.assertEqual(m.g('sav_selected_drive'),drive);self.assertEqual(m.get('sav_media_snapshot',42),media)
      polls=finish(m);self.assertEqual(m.g(symbols['dos64_native_diag']+4),0xa5);self.assertEqual(m.g('sav_error'),0);self.assertEqual(int.from_bytes(m.get('dos64_export_crc_raw',4),'little')^0xffffffff,zlib.crc32(A if drive==0 else B));self.assertEqual(m.bytes(m.path,len(A)),A if drive==0 else B);self.assertEqual(m.bytes(b'/usb1/Owned/C.IMG',len(HD)),HD);self.assertEqual(m.get('dos64_files_state_start',25),before);self.assertEqual(image(m),media)
      after=C.create_string_buffer(len(re));self.assertEqual(L.dos64_reu_read(m.m,0,after,len(after)),1);self.assertEqual(after.raw,re.raw)
      receipts.append({'drive':drive,'bank':bank,'polls':polls,'output_sha256':hashlib.sha256(A if drive==0 else B).hexdigest(),'whole4MiB_equal':True,'C_context_equal':True,'CRC32':'%08x'%zlib.crc32(A if drive==0 else B)})
     finally:m.close()
 def test_02_all42_snapshot_bytes_and_partial_descriptor_mutations_refuse(self):
  m=setup(1,0x38)
  try:
   m.call('dos64_native_tick',2000000);self.assertEqual(m.g('sav_borrowed'),1)
   fields=[symbols['dos64_disk_reu_base']+i for i in range(10)]+[symbols['dos64_disk_b_descriptor']+i for i in range(32)]
   for n,addr in enumerate(fields):
    old=m.g(addr);m.p(addr,old^1);m.p('sav_error',0);r=m.call('sav_validate_media');self.assertEqual(r.regs.p&1,1,n);self.assertEqual(m.g('sav_error'),6,n);m.p(addr,old)
   m.p('sav_error',0);self.assertEqual(m.call('sav_validate_media').regs.p&1,0)
   m.p(symbols['dos64_native_diag']+3,9);finish(m);self.assertEqual(m.g('sav_context_pending'),0)
   receipts.append({'per_byte_snapshot_negative_controls':42,'partial_descriptor_fields':20,'both_drive_metadata':22})
  finally:m.close()
 def test_03_completion_rejects_changed_selected_descriptor_or_generations(self):
  for field,offset in [('dos64_disk_b_descriptor',5),('dos64_disk_mount_generation',7),('dos64_disk_content_generation',4)]:
   with self.subTest(field=field):
    m=setup(1,0x38)
    try:
     before=m.get('dos64_files_state_start',25);binding=m.get('dos64_disk_binding',8);clean=m.get('dos64_disk_clean_mount',16);m.call('dos64_native_tick',2000000);a=symbols[field]+offset;m.p(a,m.g(a)^1)
     polls=finish(m);self.assertEqual(m.g(symbols['dos64_native_diag']+4),0xe1);self.assertEqual(m.g('sav_error'),6);self.assertEqual(m.g('sav_context_pending'),0);self.assertEqual(m.g('hdb_online'),1);self.assertEqual(m.get('dos64_files_state_start',25),before);self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(m.get('dos64_disk_binding',8),binding);self.assertEqual(m.get('dos64_disk_clean_mount',16),clean);self.assertEqual(int.from_bytes(m.get('dos64_export_crc_raw',4),'little')^0xffffffff,zlib.crc32(B))
     receipts.append({'terminal_mutation':field,'offset':offset,'polls':polls,'ack':225,'first_error':6,'C_context_equal':True,'no_binding_or_clean_change':True})
    finally:m.close()
 def test_04_readonly_clean_dirty_policy_preserved_and_input_drive_immutable(self):
  for ro,dirty in [(1,0),(0,0),(0,1)]:
   m=setup(1,0x18,readonly=ro,dirty=dirty)
   try:
    before=image(m);binding=m.get('dos64_disk_binding',8);clean=m.get('dos64_disk_clean_mount',16);m.call('dos64_native_tick',2000000);m.p('sav_drive',0);finish(m)
    self.assertEqual(m.g(symbols['dos64_native_diag']+4),0xa5);self.assertEqual(m.g('sav_selected_drive'),1);self.assertEqual(m.bytes(m.path,len(B)),B);self.assertEqual(image(m),before);self.assertEqual(m.get('dos64_disk_binding',8),binding);self.assertEqual(m.get('dos64_disk_clean_mount',16),clean)
   finally:m.close()
 def test_05_invalid_drive_and_initial_geometry_bank_fail_before_file_jobs(self):
  for fault in ['drive2','drive255','loaded','sectors','cylinders','heads','spt','unaligned','bank']:
   with self.subTest(fault=fault):
    m=setup(1,0x38)
    try:
     if fault.startswith('drive'):m.p('sav_drive',int(fault[5:]))
     elif fault=='bank':m.p('dos64_export_bank',0x10)
     else:
      off={'loaded':9,'sectors':3,'cylinders':5,'heads':7,'spt':8,'unaligned':0}[fault];a=symbols['dos64_disk_b_descriptor']+off;m.p(a,m.g(a)^1)
     before=m.get('dos64_files_state_start',25);wire=L.bulk_model_commands(m.m);m.call('dos64_native_tick',2000000)
     self.assertEqual(m.g('sav_borrowed'),0);self.assertEqual(m.g(symbols['dos64_native_diag']+4),0xe1);self.assertEqual(L.bulk_model_commands(m.m),wire);self.assertEqual(m.get('dos64_files_state_start',25),before);self.assertEqual(m.g('hdb_online'),1);self.assertEqual(L.bulk_model_size(m.m,m.path),0xffffffff)
    finally:m.close()
if __name__=='__main__':
 r=unittest.main(exit=False,verbosity=2).result;(P/'SELECTED_RESULT.json').write_text(json.dumps({'successful':r.wasSuccessful(),'tests':r.testsRun,'receipts':receipts},indent=2)+'\n');sys.exit(not r.wasSuccessful())
