from pathlib import Path
import os,sys
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;os.environ['DOS64_MEDIA_TEST_ROLE']='runtime'
import unittest,json,zlib,ctypes as C
from controller_fixture import initial
from fixture_base import *
Q=labels('phase/runtime-plan.labels');V=labels('phase/worker-calls.labels');symbols['plan_init']=V['mw_init'];symbols['plan_build']=V['mw_build'];records=[]
def zero_crc(b):
 b=bytearray(b);b[-4:]=bytes(4);v=zlib.crc32(b);basis={}
 for i in range(32):
  x=bytearray(b);x[-4+i//8]^=1<<(i%8);n=zlib.crc32(x)^v;mask=1<<i
  while n:
   k=n.bit_length()-1
   if k in basis:n^=basis[k][0];mask^=basis[k][1]
   else:basis[k]=(n,mask);break
 n=v;mask=0
 while n:
  k=n.bit_length()-1;n^=basis[k][0];mask^=basis[k][1]
 b[-4:]=mask.to_bytes(4,'little');assert zlib.crc32(b)==0;return bytes(b)
class InsertPlan(unittest.TestCase):
 def prepare(self,case):
  drive=0 if case=='ejected_A'else 1;m,old,f=initial(self,drive=drive,admit=False);old=bytearray(old)
  if case.startswith('first_B'):
   old[524]&=~2;old[525]&=~2;old[264:392]=bytes(128);old[532:536]=bytes(4);m.put('dos64_disk_b_descriptor',bytes(10));m.p(symbols['dos64_disk_readonly']+1,0);m.p(symbols['dos64_disk_dirty']+1,0)
   for name in ['dos64_disk_mount_generation','dos64_disk_content_generation','dos64_disk_clean_mount','dos64_disk_clean_content','dos64_disk_binding']:m.put(symbols[name]+4,bytes(4))
  old=resign(old)
  for at,b in [(0x3ff020,old),(0x3e0000,old),(0x3ff000,headers(old)[0]),(0x3ff500,headers(old)[1])]:L.bulk_reu_seed(m.m,at,b,len(b))
  self.assertFalse(m.call('modal_admit',2000000).regs.p&1)
  if case.startswith('ejected'):
   request=bytearray(27);request[0]=4;request[1]=drive;request[2]=2;request[15:19]=m.get(symbols['dos64_disk_mount_generation']+drive*4,4);request[19:23]=m.get(symbols['dos64_disk_content_generation']+drive*4,4);m.put('dos64_floppy_request',request);self.assertFalse(m.call('dos64_overlay_floppy_control',3000000).regs.p&1)
  snap=m.get('dos64_disk_reu_base',10)+m.get('dos64_disk_b_descriptor',32);image=fat(('INSERT '+case+'\r\n').encode());image=zero_crc(image)if case.endswith('zero')else image;path=b'/usb1/Owned/SAVE0001.IMG';crc=zlib.crc32(image);ledger=bytearray(256);ledger[0]=2;ledger[2]=drive;ledger[3]=0xa5;ledger[4:132]=path.ljust(128,b'\0');ledger[132:174]=snap;ledger[174:178]=crc.to_bytes(4,'little');m.put(0x7f00,ledger)
  load(m,'phase/runtime-plan.prg');load(m,'phase/worker-calls.prg');m.call('plan_init',2000000)
  for n,v in [('mp_drive',drive),('mp_readonly',1)]:m.p(Q['_'+n],v)
  for n,v,size in [('mp_sequence',1,2),('mp_capacity',0x400000,4),('mp_image_crc',crc,4)]:m.wide(Q['_'+n],v,size)
  m.put(Q['_mp_snapshot'],snap);m.put(Q['_mp_image_path'],path.ljust(128,b'\0'));return m,old,snap,image,path
 def build(self,case,export=True):
  m,old,snap,image,path=self.prepare(case)
  try:
   high=bytes((i*7+3)&255 for i in range(96));m.put(128,high);before=reu(m,0,4194304);files=m.get('dos64_files_state_start',25);n=L.bulk_model_commands(m.m);r=m.call('plan_build',50000000);self.assertEqual(r.regs.a,1,(case,m.g(Q['_mp_error'])));self.assertEqual(m.g(Q['_mp_error']),0)
   new=reu(m,0x3e0300,576);jrn=reu(m,0x3e0600,1284);drive=0 if case=='ejected_A'else 1;mask=1<<drive;expected=bytearray(old);off=136+128*drive;expected[off:off+128]=path.ljust(128,b'\0');expected[524]|=mask;expected[525]|=mask;expected[528+drive*4:532+drive*4]=zlib.crc32(image).to_bytes(4,'little');expected=resign(expected)
   self.assertEqual(new,expected);self.assertEqual(jrn[:12],b'D64J\1\4\5\0'+bytes([drive,1,1,0]));self.assertEqual(jrn[12:54],snap);self.assertEqual(jrn[54:58],zlib.crc32(image).to_bytes(4,'little'));self.assertEqual(jrn[58:128],bytes(70));self.assertEqual(jrn[128:704],old);self.assertEqual(jrn[704:1280],new);self.assertEqual(jrn[1280:],zlib.crc32(jrn[:1280]).to_bytes(4,'little'));self.assertEqual(m.get(128,96),high);self.assertEqual(m.get('dos64_files_state_start',25),files);self.assertEqual(L.bulk_model_commands(m.m),n)
   after=reu(m,0,4194304)
   for a,b in [(0,0x3e0300),(0x3e0540,0x3e0600),(0x3e0b04,0x400000)]:self.assertEqual(after[a:b],before[a:b])
   if export:
    d=P.parent/'cold/inputs/journal-fixtures'/('insert-'+case);d.mkdir(exist_ok=True);
    for name,b in [('DOS64.CFG',old),('DOS64.NEW',new),('DOS64.JRN',jrn),('SAVE0001.IMG',image),('C.IMG',bytes(2097152))]:(d/name).write_bytes(b)
   records.append({'case':case,'actual_6510_PLAN':True,'old_selected_loaded':snap[(10 if drive else 0)+9],'old_presence':old[525],'new_presence':new[525],'image_crc':zlib.crc32(image),'no_FILE_or_C_change':True,'whole4MiB_guard':True,'scope':'synthetic verified-image caller receipt; no Input/WIRE/COMMIT authority'})
  finally:m.close()
 def test01_new_B_presence(self):self.build('first_B')
 def test02_new_B_legitimate_zero_CRC(self):self.build('first_B_zero')
 def test03_ejected_B(self):self.build('ejected_B')
 def test04_ejected_A(self):self.build('ejected_A')
 def test05_existing_mounted_format(self):self.build('mounted_B')
 def test06_invalid_old_snapshot_or_receipt_refuses(self):
  for which in ['null_configured_B','null_A','geometry','ledger']:
   m,old,snap,image,path=self.prepare('mounted_B')
   try:
    if which=='null_A':m.p(Q['_mp_drive'],0);m.put(Q['_mp_snapshot'],bytes(10))
    elif which=='null_configured_B':m.put(Q['_mp_snapshot']+10,bytes(10));m.put(0x7f00+142,bytes(10))
    elif which=='geometry':m.p(Q['_mp_snapshot']+16,3);m.p(0x7f00+148,3)
    else:m.p(0x7f00+4,ord('X'))
    before=reu(m,0,4194304);r=m.call('plan_build',50000000);self.assertEqual(r.regs.a,0);self.assertEqual(reu(m,0,4194304),before)
   finally:m.close()
  records.append({'null_configured_B_null_A_bad_geometry_ledger':True,'all_refused_without_REU_writes':True})
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(InsertPlan));(P/'INSERT_PLAN_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'records':records},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
