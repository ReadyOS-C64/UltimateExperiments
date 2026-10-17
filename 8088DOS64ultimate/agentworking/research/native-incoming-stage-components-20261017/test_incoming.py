from pathlib import Path
import os,sys
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/'.absent-iw-tests');assert not Path(sys.pycache_prefix).exists();os.environ['DOS64_MEDIA_TEST_ROLE']='runtime'
import json,hashlib,ctypes as C,unittest,zlib
from controller_fixture import initial
from fixture_base import *
from test_online_save import HD
IW=labels('worker/incoming.labels');symbols.update({n:v for n,v in IW.items()if n.startswith('iw_')});out=[]
def seed(m,p,b):L.bulk_model_seed(m.m,p,bytes(b),len(b))
def setup(t,target=1,drive=1,image=None):
 m,old,f=initial(t,target=target,admit=True)
 try:
  path=b'/sd/Incoming/New image.IMG';image=fat(b'INCOMING ACTUAL NATIVE\r\n')if image is None else image;seed(m,path,image)
  fq=symbols['dos64_floppy_request'];m.put(fq,bytes(27));m.p(fq,1);m.p(fq+1,drive);m.p(fq+2,3 if drive else 0);m.p(fq+4,4)
  r=m.call('dos64_overlay_floppy_control',2000000);t.assertFalse(r.regs.p&1,('PREPARE',m.g('dos64_floppy_status')));q=m.get(fq,27);t.assertEqual(q[5:8],b'\0\0\x18');t.assertEqual(m.g('dos64_floppy_stage_active'),0xa5)
  b=(P/'worker/incoming.prg').read_bytes();L.dos64_load(m.m,int.from_bytes(b[:2],'little'),b[2:],len(b)-2)
  m.put(0x7d00,bytes(IW['__BSS_SIZE__']));m.put(IW['iw_path'],path.ljust(128,b'\0'));m.p(IW['iw_enable'],0xa5);m.wide(IW['iw_limit'],30000,2)
  return m,old,f,path,image,q
 except BaseException:m.close();raise

def run(t,m,hook=None):
 r=m.call('iw_begin',2000000);t.assertEqual(r.regs.a,1,('begin',r.regs.a,m.g(IW['state']),m.g(IW['error'])))
 for i in range(60000):
  if m.g(IW['state'])!=1:break
  if hook:hook(m,i)
  m.call('iw_poll',2000000)
 t.assertNotEqual(m.g(IW['state']),1,('pollbound',m.g(IW['phase']),m.g(IW['error'])));return i
class Incoming(unittest.TestCase):
 def success(self,target,drive,image=None):
  m,old,f,path,image,q=setup(self,target,drive,image=image)
  try:
   before=reu(m,0,4194304);ctx=m.get('dos64_files_state_start',25);hd=m.get('hd_state_start',symbols['hd_state_end']-symbols['hd_state_start']);hdb=m.get('hdb_state_start',symbols['hdb_state_end']-symbols['hdb_state_start']);high=m.get(128,96);nativezp=m.get(32,36);ports={n:m.g(n)for n in [0,1,0xdc02,0xdc03]};pos=L.save_model_position(m.m,target);polls=run(self,m)
   d={'state':m.g(IW['state']),'error':m.g(IW['error']),'closed':m.g(IW['closed']),'phase':m.g(IW['phase']),'FILE_state':m.g('dos64_files_state'),'FILE_err':m.g('dos64_files_error'),'UCI_state':m.g('dos64_uci_state'),'UCI_err':m.g('dos64_uci_error'),'polls':polls};(P/'LAST_IW.json').write_text(json.dumps(d,indent=2)+'\n');self.assertEqual((d['state'],d['error'],d['closed']),(2,0,1),d)
   r=m.call('iw_take',2000000);ptr=r.regs.a|(r.regs.x<<8);self.assertEqual(ptr,IW['receipt']);v=m.get(ptr,149);self.assertEqual(v[:2],bytes([drive,q[2]]));self.assertEqual(v[2:5],q[5:8]);self.assertEqual(v[5:9],q[11:15]);self.assertEqual(v[9:17],q[15:23]);self.assertEqual(int.from_bytes(v[17:21],'little'),zlib.crc32(image));self.assertEqual(v[21:],path.ljust(128,b'\0'));r=m.call('iw_take',2000000);self.assertEqual(r.regs.a|(r.regs.x<<8),0)
   self.assertEqual(m.get('dos64_files_state_start',25),ctx);self.assertEqual(m.get('hd_state_start',len(hd)),hd);self.assertEqual(m.get('hdb_state_start',len(hdb)),hdb);self.assertEqual(m.get(128,96),high);self.assertEqual(m.get(32,36),nativezp);self.assertEqual({n:m.g(n)for n in ports},ports);self.assertEqual(L.save_model_position(m.m,target),pos);self.assertEqual(L.bulk_model_open(m.m,target),1);self.assertEqual(L.bulk_model_open(m.m,3-target),0);self.assertEqual(m.bytes(b'/usb1/Owned/C.IMG',len(HD)),HD);self.assertEqual(m.bytes(path,len(image)),image)
   after=reu(m,0,4194304);self.assertEqual(after[0x180000:0x1da000],image);self.assertEqual(after[:0x180000],before[:0x180000]);self.assertEqual(after[0x1da000:],before[0x1da000:]);self.assertEqual(m.get('dos64_floppy_request',27),q);self.assertEqual(m.g('dos64_floppy_stage_active'),0xa5);self.assertEqual(m.g('dos64_native_diag'),8);out.append(d|{'target':target,'drive':drive,'CRC':zlib.crc32(image),'one_shot_receipt':True,'full4M_except_free18':True,'C25_HD129_HDB47_high96_ZP20_43_ports_exact':True,'noCOMMIT_CANCEL':True})
  finally:m.close()
 def test01_Ctarget1_B(self):self.success(1,1)
 def test02_Ctarget2_A(self):self.success(2,0)
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Incoming));(P/'INCOMING_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'records':out,'scope':'actualruntime nativeworker/realPREPARE/model firmware; noUI/COMMIT/CFG/cold/device'},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
