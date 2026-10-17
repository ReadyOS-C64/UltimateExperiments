from pathlib import Path
import sys,os
D=Path(__file__).resolve().parent;P=D.parents[2]
sys.dont_write_bytecode=True;sys.pycache_prefix=str(D/'.absent-test-cache');assert not Path(sys.pycache_prefix).exists()
sys.path.insert(0,str(P/'agentworking/scratch/live-media-broker-root-20261017'))
import test_broker as T
import json,ctypes as C,unittest,hashlib
L=T.L;symbols=T.symbols
B={x.split()[2].lstrip('.'):int(x.split()[1],16)for x in(D/'broker/broker.labels').read_text().splitlines()if x.startswith('al ')}
U={x.split()[2].lstrip('.'):int(x.split()[1],16)for x in(D/'ui/panel.labels').read_text().splitlines()if x.startswith('al ')}
symbols.update({n:v for n,v in B.items()if n.startswith('modal_')});symbols.update({n:v for n,v in U.items()if n.startswith('_mu_')or n=='sp'})
for n,r,a in [('dos64_graphics_color_enable',None,[C.c_void_p]),('dos64_host_input_model_keys',None,[C.c_void_p,C.c_void_p]),('dos64_native_display_reg',C.c_uint8,[C.c_void_p,C.c_uint8]),('dos64_cia_clock_writes',C.c_uint32,[C.c_void_p,C.c_uint8]),('browser_bad_write',C.c_uint32,[C.c_void_p,C.c_void_p]),('dos64_clear_writes',None,[C.c_void_p])]:f=getattr(L,n);f.restype=r;f.argtypes=a
NORMAL=[8,13,0x83,0x96,0x90,0x92,0x94,0x81,ord('3'),ord('w'),ord('a'),ord('4'),ord('z'),ord('s'),ord('e'),0,ord('5'),ord('r'),ord('d'),ord('6'),ord('c'),ord('f'),ord('t'),ord('x'),ord('7'),ord('y'),ord('g'),ord('8'),ord('b'),ord('h'),ord('u'),ord('v'),ord('9'),ord('i'),ord('j'),ord('0'),ord('m'),ord('k'),ord('o'),ord('n'),ord('+'),ord('p'),ord('l'),ord('-'),ord('.'),ord(':'),ord('@'),ord(','),ord('\\'),ord('*'),ord(';'),0x84,0,ord('='),ord('^'),ord('/'),ord('1'),9,0,ord('2'),ord(' '),0,ord('q'),27]
receipts=[]
def load(m,p):b=p.read_bytes();L.dos64_load(m.m,int.from_bytes(b[:2],'little'),b[2:],len(b)-2)
class F:
 def __init__(self,target=2):
  self.m=T.machine(target);m=self.m;L.dos64_graphics_color_enable(m.m);m.call('dos64_overlay_text_setup');load(m,D/'broker/broker.prg');T.admitted(m);load(m,D/'ui/panel.prg')
  self.orig_native_zp=m.get(0x80,96);self.calls=0
  self.guard=bytearray(65536)
  for lo,hi in [(0,2),(0x20,0xe0),(0x100,0x200),(0x400,0x7e8),(B['modal_owned'],B['modal_display_active']+1),(B['saved_hd'],0x7430),(0x7700,0x77dd),(0x7800,0x7c97),(0x9c76,0x9c77),(0xba00,0xc000),(0xc000,0xc010),(0xd800,0xdbe8),(0xdc00,0xdc04),(0xdf00,0xdf0b),(0xe000,0xf000)]:self.guard[lo:hi]=bytes([1])*(hi-lo)
  for a in [0xd011,0xd016,0xd018,0xd015,0xd020,0xd021,0xdd00,0xdd02]:self.guard[a]=1
  L.dos64_clear_writes(m.m);self.before_display=[L.dos64_native_display_reg(m.m,i)for i in range(8)];self.timerwrites=[L.dos64_cia_clock_writes(m.m,i)for i in range(16)];self.reu=T.reu(m);self.files=m.get('dos64_files_state_start',25);self.Cpos=L.save_model_position(m.m,target);self.target=target
  assert not m.call('modal_display_on').regs.p&1
  assert [L.dos64_native_display_reg(m.m,i)for i in range(6)]==[0x1b,8,0x16,0,0,0]
  # BSS carries retired bitmap garbage. The actual native init must establish
  # its own state; no host zero-fill stands in for initialization.
  m.put(0x7800,bytes([0xa6])*0x800)
  self.view();self.ui('_mu_fixture_init');self.keys(bytes(8));self.ui('_mu_poll')
 def view(self):
  self.m.put('_mu_view',bytes([5])+b'/usb1/A.IMG'.ljust(128,b'\0')+bytes([3])+b'/usb1/B.IMG'.ljust(128,b'\0')+bytes([1,0])+bytes(40))
 def ui(self,n):
  m=self.m;assert not m.call('modal_ui_on').regs.p&1;r=m.call(n,2000000);self.calls+=1
  assert m.get('sp',2)==b'\xff\xbf';assert not m.call('modal_ui_off').regs.p&1
  rclock=m.call('modal_poll');assert not rclock.regs.p&1,(m.g('modal_error'),m.g('dos64_host_clock_status'))
  assert m.g('dos64_cache_limit')==0 and m.g('dos64_native_diag')==8
  return r.regs.a
 def keys(self,b):L.dos64_host_input_model_keys(self.m.m,b)
 def press(self,c):
  n=NORMAL.index(ord(c)if isinstance(c,str)else c);b=bytearray(8);b[n//8]|=1<<(n%8);self.keys(bytes(b));self.ui('_mu_poll');self.keys(bytes(8));self.ui('_mu_poll')
 def mode(self):return self.m.g('_mu_result')
 def event(self):
  assert self.ui('_mu_take')==1;b=self.m.get('_mu_event',133);return {'ticket':int.from_bytes(b[:2],'little'),'action':b[2],'drive':b[3],'flags':b[4],'path':b[5:].split(b'\0')[0]}
 def unchanged(self):
  m=self.m;assert T.reu(m)==self.reu;assert m.get('dos64_files_state_start',25)==self.files;assert L.save_model_position(m.m,self.target)==self.Cpos
  assert [L.dos64_cia_clock_writes(m.m,i)for i in range(16)]==self.timerwrites
  allowed=C.create_string_buffer(bytes(self.guard));bad=L.browser_bad_write(m.m,allowed);assert bad==65536,hex(bad)
 def release(self):
  m=self.m;assert not m.call('modal_display_off').regs.p&1
  # Hardware read-only/ignored bits are compared by observable masks.
  after=[L.dos64_native_display_reg(m.m,i)for i in range(8)];masks=[0x7f,0x3f,0xfe,255,15,15,255,255]
  assert [a&k for a,k in zip(after,masks)]==[a&k for a,k in zip(self.before_display,masks)]
  assert not m.call('modal_release').regs.p&1;assert (m.g('dos64_native_diag'),m.g('dos64_cache_limit'))==(5,32)
 def close(self):self.m.close()
class Tests(unittest.TestCase):
 def test_01_actual_native_CUI_CIA_and_broker_resume_both_C_targets(self):
  for target in [1,2]:
   f=F(target)
   try:
    self.assertEqual(f.mode(),1);f.press('b');self.assertEqual(f.m.g(symbols['_mu_result']+1),1);f.press('r');self.assertEqual(f.mode(),4);event=f.event();self.assertEqual((event['action'],event['drive']),(6,1));f.unchanged()
    self.assertTrue(f.m.call('modal_release').regs.p&1);f.release();f.unchanged();receipts.append({'case':'actualCUI_resume','C_target':target,'CIA_calls':f.calls,'cache0_stage8_during_UI':True,'whole4MiB_files_Cposition_and_clock_controls_unchanged':True,'VIC_text_charset16_and_restore':True})
   finally:f.close()
 def test_02_actual_SaveAs_intent_error_cancel_then_resume_no_disk_claim(self):
  f=F()
  try:
   f.press('b');f.press('n')
   for c in 'copy.img':f.press(c)
   f.press(13);event=f.event();self.assertEqual((event['action'],event['drive'],event['path']),(2,1,b'/usb1/copy.img'))
   f.press(27);self.assertEqual(f.ui('_mu_cancel_requested'),1)
   f.m.wide('_mu_reply_ticket',event['ticket'],2);f.m.p('_mu_reply_error',0x42);f.m.p('_mu_reply_safe',0);self.assertEqual(f.ui('_mu_reply'),1);self.assertEqual(f.mode(),5)
   # Deliberately no backend was run: this error reply cannot make a file or
   # change readonly/dirty/binding; observed display remains just presentation.
   f.press(13);self.assertEqual(f.mode(),1);f.press('r');self.assertEqual(f.event()['action'],6);f.unchanged();f.release();f.unchanged();receipts.append({'case':'SaveAs_intent_only','raw_path':event['path'].decode(),'native_CUI_cancel_error_and_resume':True,'no_actual_save_claim':True,'CIA_calls':f.calls})
  finally:f.close()
if __name__=='__main__':
 r=unittest.main(exit=False,verbosity=2).result;(D/'RESULT.json').write_text(json.dumps({'successful':r.wasSuccessful(),'tests':r.testsRun,'receipts':receipts,'scope':'Actual broker/CUI/CIA composition, no resident loader/hotkey/backend/physical acceptance'},indent=2)+'\n');sys.exit(not r.wasSuccessful())
