"""Synthetic fixture only: actual broker admission, zero WIRE/SAVE/PLAN calls.
ROOT controller owns all subsequent jobs. No synthetic completed worker facts.
"""
from fixture_base import headers
from fixture_base import Machine,L,symbols,load,cfg,resign,fat,A,OLD_B,NEW_B,reu
import zlib

def initial(test,target=1,drive=1,bank=0x10,admit=True):
 m=Machine(target=target,warm=True)
 try:
  m.call('dos64_bios_init',40000000);m.call('dos64_cold_release');m.call('dos64_cache_flush',2000000)
  m.put('dos64_disk_reu_base',bytes([0,0,bank])+bytes.fromhex('d0022800020901'));m.put('dos64_disk_b_descriptor',bytes.fromhex('000038d0022800020901'));m.put('dos64_disk_mount_generation',bytes.fromhex('78563412efcdab90'));m.put('dos64_disk_content_generation',bytes.fromhex('21436587ab89efcd'));m.p(symbols['dos64_disk_readonly']+1,1);m.p(symbols['dos64_disk_dirty']+1,1)
  working=A if drive else fat(b'A WORKING MODIFIED\r\n')
  if not drive:m.p('dos64_disk_readonly',1);m.p('dos64_disk_dirty',1)
  for at,b in [(bank<<16,working),(0x380000,NEW_B)]:L.bulk_reu_seed(m.m,at,b,len(b))
  old=bytearray(cfg());old[524]=2 if drive else 3;old[392:520]=b'/usb1/Owned/C.IMG\0'.ljust(128,b'\0');old[528:532]=zlib.crc32(A).to_bytes(4,'little');old[532:536]=zlib.crc32(OLD_B).to_bytes(4,'little');old=resign(old)
  for path,b in [(b'/usb1/Owned/DOS64.CFG',old),(b'/usb1/Media/A.IMG',A),(b'/sd/Media/B.IMG',OLD_B)]:L.bulk_model_seed(m.m,path,b,len(b))
  for at,b in [(0x3ff020,old),(0x3ff000,headers(old)[0]),(0x3ff500,headers(old)[1])]:L.bulk_reu_seed(m.m,at,b,len(b))
  m.put('dos64_disk_binding',old[528:536]);m.put('dos64_disk_clean_mount',m.get('dos64_disk_mount_generation',8));m.put('dos64_disk_clean_content',m.get('dos64_disk_content_generation',8));m.put(0x7f00,bytes(256));load(m,'broker/broker.prg');m.p(symbols['dos64_native_diag']+3,0)
  if admit:test.assertFalse(m.call('modal_admit',2000000).regs.p&1)
  if admit:test.assertEqual((m.g('dos64_native_diag'),m.g('dos64_cache_limit')),(8,0))
  test.assertEqual(L.bulk_model_size(m.m,b'/usb1/Owned/SAVE0001.IMG'),0xffffffff);test.assertEqual(m.get(0x7f00,256),bytes(256))
  return m,old,{'C':m.get('dos64_files_state_start',25),'HD':m.get('hd_state_start',symbols['hd_state_end']-symbols['hd_state_start']),'drive':drive,'path':b'/usb1/Owned/SAVE0001.IMG','home':b'/usb1/Owned','sequence':1,'working':NEW_B if drive else working,'binding':m.get('dos64_disk_binding',8)}
 except BaseException:m.close();raise
if __name__=='__main__':
 import unittest,json
 cases=[]
 for target,drive,bank in [(1,1,0x10),(2,0,0x18)]:
  m,old,f=initial(unittest.TestCase(),target,drive,bank)
  try:cases.append({'target':target,'drive':drive,'bank':bank,'broker_admitted':True,'job_zero':m.get(0x7f00,256)==bytes(256),'CFG_exact':reu(m,0x3ff020,576)==old,'saved_file_absent':True,'no_WIRE_SAVE_PLAN_calls':True})
  finally:m.close()
 from pathlib import Path
 Path('CONTROLLER_FIXTURE_RESULT.json').write_text(json.dumps({'passed':True,'cases':cases},indent=2)+'\n')
