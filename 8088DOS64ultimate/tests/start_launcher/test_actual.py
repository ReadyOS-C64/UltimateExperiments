import ctypes as C,struct,unittest,hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
L=C.CDLL(str(P/'bulk-peddle.dylib'))
class Regs(C.Structure):_fields_=[('pc',C.c_uint16),('sp',C.c_uint8),('a',C.c_uint8),('x',C.c_uint8),('y',C.c_uint8),('p',C.c_uint8),('cycles',C.c_uint64),('instructions',C.c_uint64)]
class Result(C.Structure):_fields_=[('regs',Regs),('status',C.c_uint),('stack',C.c_uint8)]
def bind(n,ret,args):f=getattr(L,n);f.restype=ret;f.argtypes=args;return f
ptr=C.c_void_p;u8=C.c_uint8;u16=C.c_uint16;u32=C.c_uint32;u64=C.c_uint64;size=C.c_size_t
bind('dos64_create',ptr,[]);bind('dos64_destroy',None,[ptr]);bind('dos64_load',None,[ptr,u16,ptr,size]);bind('dos64_poke',None,[ptr,u16,u8]);bind('dos64_peek',u8,[ptr,u16]);bind('dos64_set_regs',None,[ptr,Regs]);bind('dos64_run',Result,[ptr,u16,u64]);bind('dos64_uci_model_enable',None,[ptr,u16,u32,u8]);bind('dos64_enable_reu',None,[ptr]);bind('dos64_enable_reu_sized',u8,[ptr,u32]);bind('dos64_uci_model_stuck',None,[ptr,u8]);bind('dos64_uci_model_count',u64,[ptr,u8]);bind('bulk_model_enable',None,[ptr]);bind('bulk_model_faults',None,[ptr,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int]);bind('bulk_model_commands',u32,[ptr]);bind('bulk_model_command',u8,[ptr,u32,u32]);bind('bulk_model_size',u32,[ptr,C.c_char_p]);bind('bulk_model_read',u8,[ptr,C.c_char_p,ptr,u32]);bind('bulk_model_seed',None,[ptr,C.c_char_p,ptr,u32]);bind('bulk_reu_seed',None,[ptr,u32,ptr,u32]);bind('dos64_was_written',u8,[ptr,u16]);bind('dos64_reu_read',u8,[ptr,u32,ptr,size]);bind('dos64_reu_peek',u8,[ptr,u32]);bind('dos64_reu_fail_after',None,[ptr,u64,u32])
ROOT=b'/usb1/DOS64_TEST/offline-bulk';PATH=ROOT+b'/BULK.BIN'
class F:
 def __init__(self,prefix='bulk-template'):
  self.labels={l.split()[2].lstrip('.'):int(l.split()[1],16) for l in (P/(prefix+'.labels')).read_text().splitlines() if l.startswith('al ')}
  self.m=L.dos64_create();b=(P/(prefix+'.prg')).read_bytes();L.dos64_load(self.m,int.from_bytes(b[:2],'little'),b[2:],len(b)-2);L.dos64_poke(self.m,0,0x2f);L.dos64_poke(self.m,1,0x35);L.dos64_uci_model_enable(self.m,0xdf1c,3,0xc9);L.dos64_enable_reu(self.m);L.bulk_model_enable(self.m);self.call('runtime_init');self.call('_br_init');self.config();self.tick=0
 def close(self):L.dos64_destroy(self.m)
 def at(self,n):return self.labels[n]
 def write(self,n,b):L.dos64_load(self.m,self.at(n),b,len(b))
 def read(self,n,length):return bytes(L.dos64_peek(self.m,self.at(n)+i) for i in range(length))
 def poke(self,n,v):L.dos64_poke(self.m,self.at(n),v)
 def byte(self,n):return L.dos64_peek(self.m,self.at(n))
 def config(self,cap=0x400000,target=1,root=ROOT,owner=0xa5):self.write('_br_config',bytes([owner,target])+struct.pack('<I',cap)+root.ljust(128,b'\0'))
 def request(self,op,mode=6,offset=0,address=0x200000,length=32768,path=PATH):self.write('_br_request',struct.pack('<BBIII',op,mode,offset,address,length)+path.ljust(128,b'\0'))
 def call(self,n,budget=2000000):
  ret=self.at('fixture_return')-1;L.dos64_poke(self.m,0x1ff,ret>>8);L.dos64_poke(self.m,0x1fe,ret&255);L.dos64_set_regs(self.m,Regs(self.at(n),0xfd,0x71,0x82,0x93,0x24,0,0));r=L.dos64_run(self.m,self.at('fixture_return'),budget)
  if r.status:raise AssertionError((n,r.status,hex(r.regs.pc),r.regs.cycles))
  if self.read('sp',2)!=b'\xff\xbf':raise AssertionError(('C software stack imbalance',n,self.read('sp',2)))
  return r.regs.a
 def result(self):return struct.unpack('<8BIIH',self.read('_br_result',18))
 def poll(self):
  self.tick+=1;self.write('_br_now',struct.pack('<H',self.tick//32));self.call('_br_poll')
 def finish(self):
  for _ in range(30000):
   if self.result()[0]!=1:return self.result()
   self.poll()
  raise AssertionError('bounded poll budget')
 def op(self,op,**kw):
  self.request(op,**kw)
  if self.call('_br_start')!=1:raise AssertionError(('rejected',op,self.result()))
  return self.finish()
 def faults(self,fail=-1,short=-1,reply=-1,kind=0,corrupt=-1):L.bulk_model_faults(self.m,fail,short,reply,kind,corrupt)
 def seed(self,b,addr=0x200000):L.bulk_reu_seed(self.m,addr,b,len(b))
 def file(self):
  n=L.bulk_model_size(self.m,PATH);b=C.create_string_buffer(n);assert L.bulk_model_read(self.m,PATH,b,n);return b.raw
 def reu(self,addr,n):b=C.create_string_buffer(n);assert L.dos64_reu_read(self.m,addr,b,n);return b.raw
class Actual(unittest.TestCase):
 def setUp(self):self.f=F()
 def tearDown(self):self.f.close()
 def test_abi_and_default_off(self):
  f=self.f;self.assertEqual(f.read('_br_abi_sizes',3),bytes([134,142,18]));f.config(owner=0);f.request(2);self.assertEqual(f.call('_br_start'),0);self.assertEqual(L.bulk_model_commands(f.m),0)
 def test_roundtrip_count_marker_eof_close(self):
  f=self.f;data=bytes((i^(i>>8)^0xa7)&255 for i in range(32768));f.seed(data);self.assertEqual(f.op(2)[0],2);r=f.op(0x22);self.assertEqual((r[0],r[4],r[8]),(2,1,len(data)));self.assertEqual(f.file(),data);self.assertEqual(f.op(3)[3],0);f.op(2,mode=1);self.assertEqual(f.op(7)[9],32768);f.seed(bytes(32768));self.assertEqual(f.op(0x21)[0],2);self.assertEqual(f.reu(0x200000,32768),data);r=f.op(0x21,length=1);self.assertEqual((r[0],r[1],r[4],r[8]),(3,5,1,0));self.assertEqual(f.op(3)[3],0)
 def test_paths_and_capacity_no_wire(self):
  f=self.f
  for root in [b'',b'/usb1/',b'/usb1//bad',b'/usb1/a/../b',b'/usb1/a/',b'/usb1/a. ']:
   f.config(root=root);f.request(2);self.assertEqual(f.call('_br_start'),0)
  f.config()
  for path in [ROOT+b'evil/F',ROOT+b'/../F',ROOT+b'/A/B',ROOT+b'/..',ROOT+b'/A.',b'/usb1/other/F']:
   f.request(2,path=path);self.assertEqual(f.call('_br_start'),0)
  for cap in [0,0x200000,0x400001,0xffffffff]:f.config(cap=cap);f.request(2);self.assertEqual(f.call('_br_start'),0)
  self.assertEqual(L.bulk_model_commands(f.m),0)
 def test_reu_boundaries_no_silent_mask(self):
  f=self.f;f.op(2)
  for a,n in [(0,0),(0x400000,1),(0x3fffff,2),(0x1000000,1),(0xffffffff,512),(0,0x2000000),(0,0x400001)]:
   f.request(0x22,address=a,length=n);self.assertEqual(f.call('_br_start'),0)
  f.seed(b'Z',0x3fffff);self.assertEqual(f.op(0x22,address=0x3fffff,length=1)[8],1);self.assertEqual(f.file(),b'Z')
 def test_request_snapshot_and_busy_rejection(self):
  f=self.f;f.op(2);f.seed(b'Q'*32768);f.request(0x22);self.assertEqual(f.call('_br_start'),1);f.request(0x21,address=0,length=1,path=b'/wrong');self.assertEqual(f.call('_br_start'),0);r=f.finish();self.assertEqual((r[0],r[7],r[8]),(2,0x22,32768));self.assertEqual(f.file(),b'Q'*32768)
 def test_changed_config_requires_original_owner(self):
  f=self.f;f.op(2);f.config(target=2);f.request(3);self.assertEqual(f.call('_br_start'),0);f.config();self.assertEqual(f.op(3)[0],2)
 def test_short_and_status_failure_never_success(self):
  for kind in ['short','status']:
   f=F()
   try:
    f.op(2);f.seed(b'X'*32768);f.faults(**({'short':2} if kind=='short' else {'fail':2}));r=f.op(0x22);self.assertEqual((r[0],r[1]),(3,5 if kind=='short' else 3));self.assertEqual(f.op(3)[3],0)
   finally:f.close()
 def test_strict_reply_all_fields_and_more(self):
  for kind in range(1,10):
   f=F()
   try:
    f.op(2);f.faults(reply=2,kind=kind);r=f.op(0x22);self.assertEqual(r[0],3,(kind,r));self.assertNotEqual(r[1],0);self.assertEqual(L.bulk_model_commands(f.m),2)
   finally:f.close()
 def test_cancel_once_and_unknown_only_close(self):
  f=self.f;f.op(2);f.request(0x22);f.call('_br_start');f.call('_br_cancel');f.call('_br_cancel');r=f.finish();self.assertEqual((r[0],r[1],r[3]),(3,6,2));self.assertEqual(L.dos64_uci_model_count(f.m,2),1);f.request(0x21);self.assertEqual(f.call('_br_start'),0);self.assertEqual(f.op(3)[3],0)
 def test_external_ui_lease_exclusive(self):
  f=self.f;self.assertEqual(f.call('_br_ui_acquire'),1);f.request(2);self.assertEqual(f.call('_br_start'),0);self.assertEqual(f.call('_br_ui_acquire'),0);self.assertEqual(f.call('_br_ui_release'),1);f.op(2);self.assertEqual(f.call('_br_ui_acquire'),0);f.op(3);self.assertEqual(f.call('_br_ui_acquire'),1);self.assertEqual(f.call('_br_ui_release'),1)
 def test_preexisting_create_new_preserves_all_bytes(self):
  f=self.f;data=b'original'*123;L.bulk_model_seed(f.m,PATH,data,len(data));r=f.op(2);self.assertEqual(r[0],3);self.assertEqual(f.file(),data);self.assertEqual(r[3],2);self.assertEqual(f.op(3)[3],0)
 def test_timeout_then_cancel_preserves_first_transport_reason(self):
  f=self.f;f.op(2);f.write('_uci_timeout',struct.pack('<H',4));f.write('_uci_recovery_timeout',struct.pack('<H',10));f.request(0x22);f.call('_br_start');L.dos64_uci_model_stuck(f.m,1);f.write('_br_now',struct.pack('<H',9));f.call('_br_poll');self.assertEqual(f.result()[1],2);f.call('_br_cancel');L.dos64_uci_model_stuck(f.m,0);r=f.finish();self.assertEqual((r[0],r[1],r[2]),(3,2,3));self.assertEqual(L.dos64_uci_model_count(f.m,2),1)
 def test_status_seen_then_cancel_preserves_status(self):
  f=self.f;f.faults(fail=1);f.request(2);f.call('_br_start')
  for _ in range(1000):
   f.poll()
   if f.result()[1]:break
  self.assertEqual(f.result()[1],3);f.call('_br_cancel');self.assertEqual(f.finish()[1],3)
 def test_clock_wrap_timeout_quiet_and_recovery_failure(self):
  for stuck in [False,True]:
   f=F()
   try:
    f.op(2);f.write('_br_now',struct.pack('<H',65534));f.write('_uci_timeout',struct.pack('<H',4));f.write('_uci_recovery_timeout',struct.pack('<H',3));f.request(0x22);f.call('_br_start');L.dos64_uci_model_stuck(f.m,1);f.write('_br_now',struct.pack('<H',3));f.call('_br_poll');self.assertEqual(f.result()[1],2)
    if not stuck:L.dos64_uci_model_stuck(f.m,0)
    for n in range(4,12):f.write('_br_now',struct.pack('<H',n));f.call('_br_poll')
    self.assertEqual(f.result()[0],3);self.assertEqual(f.result()[3],2);self.assertEqual(f.byte('_uci_recovery_failed'),int(stuck));self.assertEqual(L.dos64_uci_model_count(f.m,2),1)
   finally:f.close()
 def test_target2_counted128k_and2m_transfers(self):
  f=self.f;f.config(target=2)
  for n in [131072,2097152]:
   path=ROOT+(b'/MID.BIN' if n==131072 else b'/LARGE.BIN');f.seed(bytes([0x39])*n);f.op(2,path=path);r=f.op(0x22,length=n);self.assertEqual((r[0],r[8]),(2,n));self.assertEqual(L.bulk_model_size(f.m,path),n);f.op(3);f.op(2,mode=1,path=path);self.assertEqual(f.op(0x21,length=n)[8],n);self.assertEqual(f.reu(0x200000,n),bytes([0x39])*n);f.op(3)
 def test_no_tick_no_timeout_from_poll_count(self):
  f=self.f;f.op(2);f.request(0x22);f.call('_br_start');L.dos64_uci_model_stuck(f.m,1)
  for _ in range(1000):f.call('_br_poll')
  self.assertEqual(f.result()[0],1);self.assertEqual(f.result()[1],0);L.dos64_uci_model_stuck(f.m,0);f.call('_br_cancel');self.assertEqual(f.finish()[1],6)
 def diagnostic(self,n=32768,corrupt=-1,partial=False,cancel=False):
  f=self.f;f.write('_diag_control',b'\xa5BR1');f.write('_diag_path',PATH.ljust(128,b'\0'));f.write('_diag_size',struct.pack('<I',n));f.faults(corrupt=corrupt)
  if partial:L.dos64_reu_fail_after(f.m,0,17)
  f.call('_diag_init')
  for _ in range(30000):
   if f.byte('_diag_state')!=1:break
   if cancel and L.bulk_model_commands(f.m)>=2:f.poke('_diag_cancel',1)
   f.tick+=1;f.write('_br_now',struct.pack('<H',f.tick//32));f.call('_diag_step')
  return f.byte('_diag_state')
 def test_diagnostic128k_and2m_pattern_allbytes_markers(self):
  for n in [131072,2097152]:
   self.assertEqual(self.diagnostic(n),0xa5,(n,self.f.byte('_diag_first_error')));data=self.f.file();expected=bytearray((i^(i>>8)^(i>>16)^0xa7)&255 for i in range(n));expected[:4]=b'BR01';expected[-4:]=b'END!';self.assertEqual(data,expected);self.assertEqual(self.f.read('_diag_compared',4),struct.pack('<I',n));self.assertEqual(self.f.result()[3],0)
   self.f.close();self.f=F()
 def test_diagnostic_corrupt_and_partial_dma_never_accept(self):
  for which in ['corrupt','partial']:
   self.assertEqual(self.diagnostic(corrupt=1234 if which=='corrupt' else -1,partial=which=='partial'),0xff);self.assertEqual(self.f.byte('_diag_first_error'),7);self.assertEqual(self.f.result()[3],0)
   self.f.close();self.f=F()
 def test_diagnostic_cancel_preserves_first_and_closes_once(self):
  self.assertEqual(self.diagnostic(cancel=True),0xff);self.assertEqual(self.f.byte('_diag_first_error'),6);self.assertEqual(self.f.result()[3],0)
 def test_default_diagnostic_never_touches_remote_or_reu(self):
  f=self.f;f.call('_diag_init');self.assertEqual(f.byte('_diag_state'),0xff);self.assertEqual(L.bulk_model_commands(f.m),0);self.assertEqual(f.reu(0x200000,512),bytes(512))
 def test_unproven_id_rejection_cannot_release_to_ui(self):
  f=self.f;L.dos64_uci_model_enable(f.m,0xdf1c,3,0x77);f.request(2);self.assertEqual(f.call('_br_start'),0);self.assertEqual(f.call('_br_ui_acquire'),0);self.assertEqual(L.bulk_model_commands(f.m),0)
 def test_open_state_machine_failure_cleanup_first_reason(self):
  f=self.f;f.write('_diag_control',b'\xa5BR1');f.write('_diag_path',PATH.ljust(128,b'\0'));f.faults(fail=2);f.call('_diag_init')
  for _ in range(30000):
   if f.byte('_diag_state')!=1:break
   f.tick+=1;f.write('_br_now',struct.pack('<H',f.tick//32));f.call('_diag_step')
  self.assertEqual(f.byte('_diag_state'),0xff);self.assertEqual(f.byte('_diag_first_error'),3);self.assertEqual(f.result()[3],0);self.assertEqual(L.bulk_model_commands(f.m),3)
 def test_usable_capacity64k_granularity_with_actual8m_model(self):
  f=self.f;self.assertEqual(L.dos64_enable_reu_sized(f.m,8192),1);f.config(cap=0x600000);f.op(2);f.seed(b'V',0x5fffff);self.assertEqual(f.op(0x22,address=0x5fffff,length=1)[8],1);f.request(0x22,address=0x600000,length=1);self.assertEqual(f.call('_br_start'),0);self.assertEqual(f.file(),b'V')
 def test_canonical_generic_space_SD_and_supplied_filename(self):
  f=self.f
  for root,name in [(b'/usb1/My DOS home',b'MS-DOS Version 3.3 - 1 of 3.img'),(b'/sd/Install Folder',b'A..B.img'),(b'/usb0/Family..Files',b'.hidden.img')]:
   path=root+b'/'+name;f.config(root=root);self.assertEqual(f.op(2,path=path)[0],2);self.assertEqual(f.op(3)[3],0)
  self.assertEqual(L.bulk_model_commands(f.m),6)
 def test_canonical_alias_and_control_paths_rejected(self):
  f=self.f
  for root in [b'/',b'/usb1//home',b'/usb1/./home',b'/usb1/../home',b'/usb1/home ',b'/usb1/home.',b'/usb1/.. /home',b'/usb1/home\\bad',b'/usb1/home:bad',b'/usb1/\x7fhome',b'/usb1/\x80home']:
   f.config(root=root);f.request(2,path=root+b'/X');self.assertEqual(f.call('_br_start'),0,root)
  f.config(root=b'/sd/My home')
  for leaf in [b'',b'.',b'..',b'.. ',b'A/B',b'A\\B',b'A:B',b'A.',b'A ',b'A\x1fB',b'A\x80B']:
   f.request(2,path=b'/sd/My home/'+leaf);self.assertEqual(f.call('_br_start'),0,leaf)
  f.request(2,path=b'/sd/My homeSibling/X');self.assertEqual(f.call('_br_start'),0);self.assertEqual(L.bulk_model_commands(f.m),0)
 def test_unexpected_MORE_aborts_once_without_accepting_stream(self):
  f=self.f;f.op(2);before=L.dos64_uci_model_count(f.m,1);f.faults(reply=2,kind=6);r=f.op(0x22);self.assertEqual((r[0],r[1]),(3,4));self.assertEqual(L.dos64_uci_model_count(f.m,2),1);self.assertEqual(L.dos64_uci_model_count(f.m,1),before)
 def test_diagnostic_cancel_then_failed_CLOSE_keeps_first_cancel(self):
  f=self.f;f.write('_diag_control',b'\xa5BR1');f.write('_diag_path',PATH.ljust(128,b'\0'));f.faults(fail=3);f.call('_diag_init')
  for _ in range(30000):
   if f.byte('_diag_state')!=1:break
   if L.bulk_model_commands(f.m)>=2:f.poke('_diag_cancel',1)
   f.tick+=1;f.write('_br_now',struct.pack('<H',f.tick//32));f.call('_diag_step')
  self.assertEqual((f.byte('_diag_state'),f.byte('_diag_first_error'),f.byte('_diag_cleanup_error')),(0xff,6,3));self.assertEqual(f.result()[3],2);self.assertEqual(L.bulk_model_commands(f.m),3)
 def test_FatFs_invalid_chars_and_leading_spaces(self):
  f=self.f
  for bad in [b'"',b'*',b':',b'<',b'>',b'?',b'|']:
   f.config(root=b'/sd/My'+bad+b'home');f.request(2,path=b'/sd/My'+bad+b'home/X');self.assertEqual(f.call('_br_start'),0)
   f.config(root=b'/sd/My home');f.request(2,path=b'/sd/My home/A'+bad+b'B.img');self.assertEqual(f.call('_br_start'),0)
  f.config(root=b'/sd/ Leading home');self.assertEqual(f.op(2,path=b'/sd/ Leading home/ Leading file (1).img')[0],2);f.op(3)
 def test_read_mode_is_actual_write_capability_boundary(self):
  f=self.f;f.op(2);f.seed(b'X'*32768);f.op(0x22);f.op(3);f.op(2,mode=1);before=L.bulk_model_commands(f.m)
  for mode in [1,3,7]:f.request(0x22,mode=mode);self.assertEqual(f.call('_br_start'),0)
  self.assertEqual(L.bulk_model_commands(f.m),before);self.assertEqual(f.op(0x21)[0],2);f.op(3)
 def test_EOF_zero_count_still_requires_exact_REU_address(self):
  f=self.f;f.write('_diag_control',b'\xa5BR1');f.write('_diag_path',PATH.ljust(128,b'\0'));f.faults(reply=8,kind=4);f.call('_diag_init')
  for _ in range(30000):
   if f.byte('_diag_state')!=1:break
   f.tick+=1;f.write('_br_now',struct.pack('<H',f.tick//32));f.call('_diag_step')
  self.assertEqual((f.byte('_diag_state'),f.byte('_diag_first_error'),f.byte('_diag_eof_known')),(0xff,4,0));self.assertEqual(f.result()[3],0)
 def test_full127_byte_path_and_unterminated128_refusal(self):
  f=self.f;root=b'/sd/'+b'A'*116;f.config(root=root);path=root+b'/B1.BIN';self.assertEqual(len(path),127);self.assertEqual(f.op(2,path=path)[0],2);f.op(3);before=L.bulk_model_commands(f.m);f.request(2,path=root+b'/B11.BIN');self.assertEqual(f.call('_br_start'),0);self.assertEqual(L.bulk_model_commands(f.m),before)
 def test_suppressed_LOAD_exact_ack_cannot_pass_diagnostic(self):
  self.assertEqual(self.diagnostic(corrupt=-2),0xff);self.assertEqual(self.f.byte('_diag_first_error'),7);self.assertEqual(self.f.byte('_diag_eof_known'),0);self.assertEqual(self.f.result()[3],0)
 def test_partial_poison_DMA_cannot_certify_destination(self):
  f=self.f;f.write('_diag_control',b'\xa5BR1');f.write('_diag_path',PATH.ljust(128,b'\0'));f.call('_diag_init');armed=False
  for _ in range(30000):
   if f.byte('_diag_state')!=1:break
   if not armed and L.bulk_model_commands(f.m)>=5 and f.byte('_br_result')!=1:L.dos64_reu_fail_after(f.m,0,17);armed=True
   f.tick+=1;f.write('_br_now',struct.pack('<H',f.tick//32));f.call('_diag_step')
  self.assertTrue(armed);self.assertEqual(f.byte('_diag_state'),0xff);self.assertEqual(f.byte('_diag_first_error'),8);self.assertEqual(f.result()[3],0)
 def test_native_diagnostic32k(self):
  f=self.f;f.write('_diag_control',b'\xa5BR1');f.write('_diag_path',PATH.ljust(128,b'\0'));f.call('_diag_init')
  for _ in range(30000):
   if f.byte('_diag_state')!=1:break
   f.tick+=1;f.write('_br_now',struct.pack('<H',f.tick//32));f.call('_diag_step')
  self.assertEqual(f.byte('_diag_state'),0xa5,(f.byte('_diag_first_error'),f.result(),f.byte('_diag_cleanup_error')));self.assertEqual(f.read('_diag_compared',4),struct.pack('<I',32768));self.assertEqual(f.file()[:4],b'BR01');self.assertEqual(f.file()[-4:],b'END!');self.assertEqual(f.result()[3],0)
if __name__=='__main__':unittest.main(verbosity=2)
