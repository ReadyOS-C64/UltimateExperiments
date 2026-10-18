from pathlib import Path
import sys,os
sys.dont_write_bytecode=True;sys.pycache_prefix=str(Path.cwd()/('.absent-sys-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import ctypes as C,struct,zlib,json,hashlib,unittest
from config_fixture import F,L,Regs,cfg
from test_publisher import A,B,hd
P=Path.cwd();assert P.name=='work'
class Sys:
 def __init__(self,columns=80,media=None):
  self.f=F(auto=False);f=self.f;self.columns=columns;self.polls=0;self.media=media if media is not None else[A,B,hd()]
  self.guard=f.guard;first=bytearray(self.guard);a=f.labels['__CONFIG_HIGH_RUN__'];n=f.labels['__CONFIG_HIGH_TOTAL__'];first[a:a+n]=bytes([1])*n;self.first_guard=bytes(first)
  L.dir_model_path(f.m,b'/')
  for name in [b'Existing',b'Release',b'New launch']:
   path=b'/'+name;L.dir_model_path(f.m,path);L.dir_model_row(f.m,b'/',16,name,len(name))
  self.original=cfg(b'/Existing',ro=3);self.old_start=b'OLD START UNTOUCHED';L.bulk_model_seed(f.m,b'/Existing/DOS64.CFG',self.original,len(self.original));L.bulk_model_seed(f.m,b'/Existing/START.PRG',self.old_start,len(self.old_start))
  for path,data in zip([b'/usb1/Media/A.IMG',b'/sd/Media/B.IMG',b'/usb1/HD/C.IMG'],self.media):L.bulk_model_seed(f.m,path,data,len(data))
  for p in (P/'release-assets').iterdir():L.bulk_model_seed(f.m,b'/Release/'+p.name.encode(),p.read_bytes(),p.stat().st_size)
  for t in [1,2]:L.bulk_model_seed(f.m,b'/Old',b'UNCHANGED',9);L.bulk_model_seed_open(f.m,t,b'/Old',3,7)
  # True BASIC SYS machine entry: bank37 and decimal set; no C leaf call.
  L.dos64_poke(f.m,0,0x2f);L.dos64_poke(f.m,1,0x37);L.dos64_set_regs(f.m,Regs(0x080d,0xfd,0x71,0x82,0x93,0x2c,0,0))
  self.run(f.labels['config_poll_return'],self.first_guard)
 def close(self):self.f.close()
 def run(self,target,guard):
  f=self.f;L.dos64_clear_writes(f.m);r=L.dos64_run(f.m,target,100000000)
  # Bridge's subroutine convention labels SYS SPFD as STACK_IMBALANCE(2).
  # Require exact PC/SP for this non-returning BASIC application checkpoint.
  assert r.status==2 and r.regs.pc==target and r.regs.sp==0xfd,(r.status,hex(r.regs.pc),r.regs.sp)
  assert r.stack<120;assert L.browser_bad_write(f.m,guard)==65536,hex(L.browser_bad_write(f.m,guard))
  assert f.read('sp',2)==b'\xff\xcf'
 def poll(self):
  f=self.f;L.dos64_cia_clock_advance(f.m,1024);self.run(f.labels['config_poll_loop'],self.guard);self.run(f.labels['config_poll_return'],self.guard);self.polls+=1
  return f.read('co_state',1)[0]
 def ui_ready(self):
  for _ in range(4000):
   self.poll();r=self.f.read('_cg_result',8);s=r[0]
   if s not in [1,3]and not(s==2 and self.f.read('_db_result',1)==b'\1'):return s
  raise AssertionError('UI bound')
 def key(self,row,col,shift=False):
  key=bytearray(8);key[row]|=1<<col
  if shift:key[1]|=128
  L.dos64_host_input_model_keys(self.f.m,bytes(key));self.poll();L.dos64_host_input_model_keys(self.f.m,bytes(8));self.poll()
  return self.ui_ready()
 def select(self):
  assert self.ui_ready()==2;self.key(0,1);assert self.key(0,4)==4
  if self.columns==40:self.key(0,7,True)
  self.key(0,1);self.key(0,7);self.key(0,1);self.key(0,4);self.key(0,7);self.key(0,7);self.key(0,1);assert self.key(0,4)==5
  self.key(0,1)
 def finish(self):
  for _ in range(140000):
   s=self.poll()
   if s in [3,4]:return s
  raise AssertionError(('SYS bound',self.f.read('co_state',1),self.f.read('_rm_result',11),self.f.read('_cp_result',12)))
 def actual(self,n):
  f=self.f;path=b'/New launch/'+n.encode();n=L.bulk_model_size(f.m,path);assert n!=0xffffffff;out=C.create_string_buffer(n);assert L.bulk_model_read(f.m,path,out,n);return out.raw
class NativeSys(unittest.TestCase):
 def test_actual_SYS_keyboard_only_to_six_model_outputs(self):
  media=[(P/'media-inputs'/n).read_bytes()for n in ['A.IMG','B.IMG','C.IMG']]if (P/'media-inputs/A.IMG').exists()else None;s=Sys(80,media);self.addCleanup(s.close);s.select();self.assertEqual(s.finish(),3,(s.f.read('co_error',1),s.f.read('co_stage',1),s.f.read('_cp_result',12)))
  expected={n:(P/'release-assets'/n).read_bytes()for n in ['DOS64.PRG','DOS64.REL','START.INO']};tpl=bytearray((P/'release-assets/START.TPL').read_bytes());d=(P/'release-assets/START.REL').read_bytes();at=int.from_bytes(d[24:28],'little');tpl[at:at+131]=b'\xa5\x1c\xdf'+b'/New launch'.ljust(128,b'\0');expected['START.PRG']=bytes(tpl);expected['DOS64.INI']=b'[emulator]\r\ninitial_columns=80\r\n';b=bytearray(s.original);b[8:136]=b'/New launch'.ljust(128,b'\0');struct.pack_into('<II',b,528,zlib.crc32(s.media[0]),zlib.crc32(s.media[1]));struct.pack_into('<I',b,572,zlib.crc32(b[:572]));expected['DOS64.CFG']=bytes(b)
  out=P.parent/'actual-output-80';out.mkdir(exist_ok=True);receipt={}
  for n,w in expected.items():actual=s.actual(n);self.assertEqual(actual,w,n);(out/n).write_bytes(actual);receipt[n]={'sha256':hashlib.sha256(actual).hexdigest(),'bytes':len(actual)}
  self.assertEqual([L.bulk_model_open(s.f.m,t)for t in [1,2]],[0,0]);self.assertEqual(s.f.read('_cp_result',12)[7],63)
  (P.parent/'ACTUAL_SYS_OUTPUT.json').write_text(json.dumps({'status':'PASS','entry':0x080d,'initial_bank':0x37,'host_leaf_calls':0,'polls':s.polls,'actual_model_files':receipt,'synthetic_media':media is None,'genuine_DOS_execution':False},indent=2)+'\n')
 def test_new_folder_root_refuses_with_explanation_before_media(self):
  s=Sys();self.addCleanup(s.close);self.assertEqual(s.ui_ready(),2);s.key(0,1);self.assertEqual(s.key(0,4),4);s.key(0,1);s.key(0,7);s.key(0,1);s.key(0,4)
  self.assertEqual(s.key(0,4),2);self.assertEqual(s.f.read('_cg_result',8)[4],2);self.assertEqual(s.f.read('co_state',1),b'\0');self.assertEqual(s.f.read('_rm_result',1),b'\0');self.assertFalse(any(c[1]==0x21 for c in s.f.commands()))
  row=bytes(L.dos64_peek(s.f.m,0x400+20*40+i)for i in range(40));self.assertNotEqual(row,bytes([32])*40)
 def test_actual_SYS_startup_STOP_has_terminal_firstcause_and_no_OPEN(self):
  s=Sys();self.addCleanup(s.close);L.dos64_host_input_model_keys(s.f.m,bytes(7)+b'\x80')
  for _ in range(500):
   if s.poll()==4:break
  self.assertEqual(s.f.read('co_state',1),b'\4');self.assertEqual(s.f.read('co_error',1),b'\5');self.assertEqual(s.f.read('co_stage',1),b'\0');self.assertFalse(any(c[1]==2 for c in s.f.commands()));self.assertEqual(s.f.read('_rm_result',1),b'\0');self.assertEqual(s.f.read('_cp_result',1),b'\0')
 def test_new_folder_117_accepts_and_118_refuses_before_media(self):
  for length in [117,118]:
   s=Sys();self.addCleanup(s.close);name=b'L'*(length-1);path=b'/'+name;L.dir_model_path(s.f.m,path);L.dir_model_row(s.f.m,b'/',16,name,len(name))
   self.assertEqual(s.ui_ready(),2);s.key(0,1);self.assertEqual(s.key(0,4),4);s.key(0,1);s.key(0,7);s.key(0,1);s.key(0,4)
   for _ in range(3):s.key(0,7)
   s.key(0,1);self.assertEqual(s.key(0,4),5 if length==117 else 2);self.assertEqual(s.f.read('co_state',1),b'\0');self.assertEqual(s.f.read('_rm_result',1),b'\0');self.assertFalse(any(c[1]==0x21 for c in s.f.commands()))
   if length==118:
    text=b'New folder must be 2..117 characters.';expected=bytes(c-96 if 97<=c<=122 else c for c in text);row=bytes(L.dos64_peek(s.f.m,0x400+20*40+i)for i in range(len(expected)));self.assertEqual(row,expected)
if __name__=='__main__':
 result=unittest.main(exit=False).result;(P.parent/'SYS_TEST_REPORT.json').write_text(json.dumps({'tests_run':result.testsRun,'successful':result.wasSuccessful()},indent=2)+'\n');sys.exit(0 if result.wasSuccessful()and result.testsRun else 1)
