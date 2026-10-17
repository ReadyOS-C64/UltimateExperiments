from pathlib import Path
import sys,os
sys.dont_write_bytecode=True;sys.pycache_prefix=str(Path.cwd()/('.absent-save-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import ctypes as C,json,hashlib,unittest
P=Path.cwd();W=P/'work';symbols={x.split()[2].lstrip('.'):int(x.split()[1],16)for x in(W/'build/dos64-tests.labels').read_text().splitlines()if x.startswith('al ')};L=C.CDLL(str(P/'model/save-peddle.dylib'));ptr=C.c_void_p;u8=C.c_uint8;u16=C.c_uint16;u32=C.c_uint32;u64=C.c_uint64
class Regs(C.Structure):_fields_=[('pc',u16),('sp',u8),('a',u8),('x',u8),('y',u8),('p',u8),('cycles',u64),('instructions',u64)]
class Result(C.Structure):_fields_=[('regs',Regs),('status',C.c_uint),('stack',u8)]
for n,r,a in [('dos64_create',ptr,[]),('dos64_destroy',None,[ptr]),('dos64_load',None,[ptr,u16,ptr,C.c_size_t]),('dos64_peek',u8,[ptr,u16]),('dos64_poke',None,[ptr,u16,u8]),('dos64_get_regs',Regs,[ptr]),('dos64_set_regs',None,[ptr,Regs]),('dos64_run',Result,[ptr,u16,u64]),('dos64_cia_clock_advance',None,[ptr,u32]),('dos64_cia_clock_step',None,[ptr,u32]),('dos64_uci_model_enable',None,[ptr,u16,u8,u8]),('save_model_fail_close',None,[ptr,C.c_int]),('dos64_uci_model_stuck',None,[ptr,u8]),('dos64_uci_model_count',u64,[ptr,u8]),('bulk_model_faults',None,[ptr,C.c_int,C.c_int,C.c_int,C.c_int,C.c_int]),('bulk_model_seed',None,[ptr,C.c_char_p,ptr,u32]),('bulk_reu_seed',None,[ptr,u32,ptr,u32]),('bulk_model_read',u8,[ptr,C.c_char_p,ptr,u32]),('bulk_model_size',u32,[ptr,C.c_char_p]),('bulk_model_open',u8,[ptr,u8]),('save_model_position',u32,[ptr,u8]),('bulk_model_commands',u32,[ptr]),('bulk_model_command',u8,[ptr,u32,u32]),('dos64_reu_read',u8,[ptr,u32,ptr,C.c_size_t])]:f=getattr(L,n);f.restype=r;f.argtypes=a
for n in ['dos64_enable_reu','dos64_cia_clock_enable','dos64_native_display_enable','dos64_host_input_model_enable','native_runtime_control_enable','bulk_model_enable']:getattr(L,n).argtypes=[ptr]
A=bytes((i*19+(i>>9))&255 for i in range(368640));HD=bytes((i*37^(i>>17))&255 for i in range(2097152));records=[]
class Machine:
 def __init__(self,target=2,warm=False):
  self.target=target;self.m=L.dos64_create();b=(W/'build/dos64-tests.prg').read_bytes();L.dos64_load(self.m,int.from_bytes(b[:2],'little'),b[2:],len(b)-2)
  for n in ['dos64_enable_reu','dos64_cia_clock_enable','dos64_native_display_enable','dos64_host_input_model_enable','native_runtime_control_enable']:getattr(L,n)(self.m)
  L.dos64_uci_model_enable(self.m,0xdf1c,3,0xc9);L.bulk_model_enable(self.m);L.dos64_cia_clock_step(self.m,1)
  self.p(0,0x2f);self.p(1,0x35);self.call('dos64_overlay_init');self.p('dos64_overlay_reu_mib',4);self.call('dos64_overlay_bootstrap',2000000)
  self.call('dos64_cpu_init');self.p('dos64_cache_limit',32);self.call('dos64_cache_init');self.call('dos64_disk_init');self.call('dos64_uci_init');self.call('dos64_overlay_files_init');self.p('dos64_host_clock_claim',0xa5);self.call('dos64_host_clock_init');self.call('dos64_elapsed_poll')
  L.bulk_model_seed(self.m,b'/usb1/Owned/C.IMG',HD,len(HD));self.p('dos64_files_target',target);self.p('dos64_files_mode',3);self.file(2,b'/usb1/Owned/C.IMG\0');self.p('hdc_target',target);self.p('hd_profile',0);self.p('hd_slots',2);self.p('hd_readonly',0);self.call('hdb_mount',1000000);
  if warm:self.hd_read(0)
  self.wide('dos64_files_offset',12345,4);self.file(6);self.call('dos64_cache_flush',1000000)
  L.bulk_reu_seed(self.m,0x100000,A,len(A));self.p('dos64_disk_loaded',1);self.wide('dos64_disk_reu_base',0x100000,3);self.wide('dos64_disk_sectors',720,2);self.p('dos64_native_diag',5);self.p(symbols['dos64_native_diag']+3,7);self.p('dos64_export_owned',0xa5);self.p('dos64_export_paused',0xa5);self.p('dos64_export_bank',0x10);self.path=b'/usb1/Owned/SAVE.IMG';self.p('dos64_export_path_len',len(self.path)+1);self.put('dos64_export_path',self.path+b'\0')
 def addr(self,n):return symbols[n]if isinstance(n,str)else n
 def p(self,n,v):L.dos64_poke(self.m,self.addr(n),v)
 def g(self,n):return L.dos64_peek(self.m,self.addr(n))
 def put(self,n,b):
  a=self.addr(n)
  for i,v in enumerate(b):self.p(a+i,v)
 def get(self,n,count):return bytes(self.g(self.addr(n)+i)for i in range(count))
 def wide(self,n,v,count):self.put(n,v.to_bytes(count,'little'))
 def call(self,n,budget=100000):
  before=L.dos64_get_regs(self.m).cycles;ret=symbols['fixture_return']-1;self.p(0x1ff,ret>>8);self.p(0x1fe,ret&255);L.dos64_set_regs(self.m,Regs(symbols[n],0xfd,0x71,0x82,0x93,0x24,0,0));r=L.dos64_run(self.m,symbols['fixture_return'],budget)
  assert r.status==0,(n,r.status,hex(r.regs.pc),r.regs.cycles)
  L.dos64_cia_clock_advance(self.m,(r.regs.cycles-before)//64);return r
 def file(self,op,path=None):
  self.p('dos64_files_op',op)
  if path is not None:self.p('dos64_files_path_len',len(path));self.put(symbols['dos64_uci_command']+3,path)
  self.call('dos64_elapsed_poll');self.put('dos64_files_now',self.get('dos64_elapsed_now',2));self.call('dos64_overlay_files_start')
  for i in range(5000):
   if self.g('dos64_files_state')!=1:break
   self.call('dos64_elapsed_poll');self.put('dos64_files_now',self.get('dos64_elapsed_now',2));self.call('dos64_overlay_files_poll')
  assert self.g('dos64_files_state')==2,('file',op,self.g('dos64_files_error'),self.g('dos64_uci_state'))
 def hd_read(self,lba):
  self.wide('hd_lba',lba,2);self.p('hd_count',1);self.p('hd_op',0);self.call('dos64_overlay_hd_prepare')
  for i in range(100):
   if self.g('hd_state')!=1:break
   assert self.g('hd_request')==1
   self.file(self.g('dos64_files_op'));self.call('dos64_overlay_hd_advance')
  assert self.g('hd_state')==2,('HD',self.g('hd_state'),self.g('hd_error'))
 def bytes(self,name,count):
  b=C.create_string_buffer(count);assert L.bulk_model_read(self.m,name,b,count);return b.raw
 def close(self):L.dos64_destroy(self.m)
class Tests(unittest.TestCase):
 def test_01_real_files_online_c_preserved_then_read(self):
  m=Machine()
  try:
   before=m.get('dos64_files_state_start',25);hdstate=m.get('hd_state_start',symbols['hd_state_end']-symbols['hd_state_start']);guest=m.get('dos64_guest',28);pos=L.save_model_position(m.m,2);self.assertEqual(pos,12345)
   r=m.call('dos64_native_tick',2000000);self.assertEqual(r.regs.p&1,0);self.assertEqual(m.g('sav_borrowed'),1);self.assertEqual(m.g('hdb_online'),0)
   for i in range(250000):
    if not m.g('sav_borrowed'):break
    m.call('dos64_native_tick',200000)
   diagnostic={n:m.g(n)for n in ['sav_borrowed','sav_error','sav_context_pending','sav_context_phase','sav_expected_handle','dos64_native_diag','dos64_export_state','dos64_export_error','dos64_export_failure_phase','dos64_export_failure_files_error','dos64_export_failure_transport_error','dos64_files_state','dos64_files_error','dos64_files_handle','dos64_files_target','dos64_uci_state','dos64_uci_error']};diagnostic['polls']=i;diagnostic['wire']=[[L.bulk_model_command(m.m,k,x)for x in range(10)]for k in range(L.bulk_model_commands(m.m))];(P/'LAST_DIAGNOSTIC.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
   self.assertEqual(m.g('sav_borrowed'),0);self.assertEqual(m.g('dos64_native_diag'),5);self.assertEqual(m.g(symbols['dos64_native_diag']+4),0xa5);self.assertEqual(m.g('dos64_export_verified'),1);self.assertEqual(m.get('dos64_files_state_start',25),before);self.assertEqual(m.get('hd_state_start',len(hdstate)),hdstate);self.assertEqual(m.get('dos64_guest',28),guest);self.assertEqual(L.bulk_model_open(m.m,2),1);self.assertEqual(L.bulk_model_open(m.m,1),0);self.assertEqual(L.save_model_position(m.m,2),pos);self.assertEqual(m.bytes(m.path,len(A)),A);self.assertEqual(m.bytes(b'/usb1/Owned/C.IMG',len(HD)),HD)
   m.wide('dos64_files_count',512,2);m.file(4);self.assertEqual(m.get('dos64_uci_data',512),HD[pos:pos+512]);self.assertEqual(L.save_model_position(m.m,2),pos+512)
   records.append({'polls':i,'snapshot_restored':True,'HD_sha256':hashlib.sha256(HD).hexdigest(),'A_sha256':hashlib.sha256(A).hexdigest(),'read_after_save':512,'wire_commands':L.bulk_model_commands(m.m)})
  finally:m.close()
 def test_02_close_leaf_precedes_later_clock_failure(self):
  m=Machine()
  try:
   before=m.get('dos64_files_state_start',25);L.bulk_model_faults(m.m,3,-1,-1,0,-1);m.call('dos64_native_tick',2000000)
   for i in range(200):
    m.call('dos64_native_tick',200000)
    if m.g('dos64_files_error'):break
   self.assertTrue(m.g('dos64_files_error'));self.assertEqual(m.g('sav_borrowed'),1);first=m.g('dos64_files_error');m.p('dos64_host_clock_claim',0);m.p(symbols['dos64_native_diag']+3,9)
   for count in range(300):
    m.call('dos64_native_tick',200000)
    if not m.g('sav_borrowed'):break
   d={n:m.g(n)for n in ['sav_error','sav_context_pending','hdb_online','dos64_files_handle','dos64_files_state','dos64_uci_state']};d.update(first_files_error=first,drain_calls=count+1,c_snapshot_retained=m.get('sav_context_snapshot',25)==before);(P/'CLOSE_FIRST_CAUSE.json').write_text(json.dumps(d,indent=2)+'\n')
   self.assertEqual(m.g('sav_error'),5);self.assertEqual(m.g('hdb_online'),0);self.assertEqual(m.g('sav_context_pending'),1);self.assertEqual(m.get('sav_context_snapshot',25),before);self.assertEqual(L.bulk_model_open(m.m,2),1)
  finally:m.close()
 def test_03_target1_c_warm_cache_and_whole_reu(self):
  m=Machine(target=1,warm=True)
  try:
   before=m.get('dos64_files_state_start',25);tags=m.get('hd_state_start',symbols['hd_state_end']-symbols['hd_state_start']);self.assertEqual(m.g('hd_valid'),1);reu=C.create_string_buffer(4*1024*1024);self.assertEqual(L.dos64_reu_read(m.m,0,reu,len(reu)),1);m.call('dos64_native_tick',2000000)
   for i in range(250000):
    if not m.g('sav_borrowed'):break
    m.call('dos64_native_tick',200000)
   self.assertEqual(m.g(symbols['dos64_native_diag']+4),0xa5);self.assertEqual(m.get('dos64_files_state_start',25),before);self.assertEqual(m.get('hd_state_start',len(tags)),tags);after=C.create_string_buffer(len(reu));self.assertEqual(L.dos64_reu_read(m.m,0,after,len(after)),1);self.assertEqual(after.raw,reu.raw);self.assertEqual(L.bulk_model_open(m.m,1),1);self.assertEqual(L.bulk_model_open(m.m,2),0);self.assertEqual(L.save_model_position(m.m,1),12345);commands=L.bulk_model_commands(m.m);m.hd_read(0);self.assertEqual(L.bulk_model_commands(m.m),commands);self.assertEqual(m.get('dos64_uci_data',512),HD[:512]);self.assertEqual(L.save_model_position(m.m,1),12345)
   records.append({'case':'target1-C-warmcache','polls':i,'whole_REU_4MiB_equal':True,'HD_cache_hit_no_wire':True})
  finally:m.close()
 def test_04_wrong_owner_target_rejects_without_wire(self):
  for target in [0,1,3]:
   m=Machine()
   try:
    before=m.get('dos64_files_state_start',25);m.p('hdc_target',target);count=L.bulk_model_commands(m.m);m.call('dos64_native_tick',2000000);self.assertEqual(L.bulk_model_commands(m.m),count);self.assertEqual(m.g('sav_borrowed'),0);self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(m.get('dos64_files_state_start',25),before);self.assertEqual(L.bulk_model_open(m.m,2),1)
   finally:m.close()
 def test_05_cancel_safety_close_defers_then_restores_c(self):
  m=Machine()
  try:
   before=m.get('dos64_files_state_start',25);m.call('dos64_native_tick',2000000);m.p(symbols['dos64_native_diag']+3,9)
   for i in range(1000):
    if not m.g('sav_borrowed'):break
    m.call('dos64_native_tick',200000)
   self.assertEqual(m.g('sav_borrowed'),0);self.assertEqual(m.g('dos64_native_diag'),5);self.assertEqual(m.g(symbols['dos64_native_diag']+4),0xe1);self.assertEqual(m.get('dos64_files_state_start',25),before);self.assertEqual(m.g('hdb_online'),1);self.assertEqual(L.bulk_model_size(m.m,m.path),0xffffffff);self.assertEqual(L.bulk_model_commands(m.m),3)
  finally:m.close()
 def test_06_create_new_collision_preserves_both_files_and_c(self):
  m=Machine()
  try:
   original=b'keep-existing-save';L.bulk_model_seed(m.m,m.path,original,len(original));before=m.get('dos64_files_state_start',25);m.call('dos64_native_tick',2000000)
   for i in range(5000):
    if not m.g('sav_borrowed'):break
    m.call('dos64_native_tick',200000)
   self.assertEqual(m.g('sav_borrowed'),0);self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(m.g(symbols['dos64_native_diag']+4),0xe1);self.assertEqual(m.g('dos64_export_verified'),0);self.assertEqual(m.get('dos64_files_state_start',25),before);self.assertEqual(m.bytes(m.path,len(original)),original);self.assertEqual(m.bytes(b'/usb1/Owned/C.IMG',len(HD)),HD)
  finally:m.close()
 def test_07_unknown_final_close_retains_c_and_blocks_guest(self):
  m=Machine()
  try:
   before=m.get('dos64_files_state_start',25);m.call('dos64_native_tick',2000000);injected=False
   for i in range(250000):
    if not m.g('sav_borrowed'):break
    if m.g('dos64_export_phase')==10:L.save_model_fail_close(m.m,1);injected=True
    m.call('dos64_native_tick',200000)
   self.assertTrue(injected);self.assertEqual(m.g('sav_borrowed'),0);self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(m.g('sav_context_pending'),1);self.assertEqual(m.get('sav_context_snapshot',25),before);self.assertEqual(m.g('hdb_online'),0);self.assertEqual(m.g('dos64_files_handle'),2);self.assertEqual(L.bulk_model_open(m.m,1),1);self.assertEqual(L.bulk_model_open(m.m,2),1);self.assertEqual(L.save_model_position(m.m,2),12345);self.assertEqual(m.bytes(b'/usb1/Owned/C.IMG',len(HD)),HD);m.p(symbols['dos64_native_diag']+3,3);m.call('dos64_native_tick');self.assertEqual(m.g('dos64_native_diag'),0xe1);self.assertEqual(m.g('hdb_online'),0)
   records.append({'case':'unknown-final-close','polls':i,'C_snapshot_retained':True,'both_firmware_handles_still_open':True,'RUN_rejected':True})
  finally:m.close()
 def test_08_clock_failure_stuck_transport_exact256_drain(self):
  m=Machine()
  try:
   before=m.get('dos64_files_state_start',25);m.call('dos64_native_tick',2000000);L.dos64_uci_model_stuck(m.m,1);m.wide('dos64_uci_recovery_timeout',0x7000,2);m.p('dos64_host_clock_claim',0)
   for count in range(300):
    m.call('dos64_native_tick',200000)
    if not m.g('sav_borrowed'):break
   self.assertEqual(count+1,256);self.assertEqual(m.g('sav_error'),2);self.assertEqual(m.g('sav_context_pending'),1);self.assertEqual(m.get('sav_context_snapshot',25),before);self.assertEqual(m.g('hdb_online'),0);self.assertEqual(m.g('dos64_files_state'),1);self.assertEqual(m.g('dos64_uci_state'),8);self.assertEqual(L.dos64_uci_model_count(m.m,2),1);self.assertEqual(L.bulk_model_open(m.m,2),1);self.assertEqual(m.g('dos64_native_diag'),0xe1)
   records.append({'case':'stuck-clock-failure','drain_calls':count+1,'ABORTs':L.dos64_uci_model_count(m.m,2),'pending_transport_truthful':True})
  finally:m.close()
 def test_09_cancel_mid_write_restores_only_after_close(self):
  m=Machine()
  try:
   before=m.get('dos64_files_state_start',25);m.call('dos64_native_tick',2000000);cancel=False
   for i in range(5000):
    if not m.g('sav_borrowed'):break
    if m.g('dos64_export_phase')==3 and not cancel:m.p(symbols['dos64_native_diag']+3,9);cancel=True
    m.call('dos64_native_tick',200000)
   self.assertTrue(cancel);self.assertEqual(m.g('sav_borrowed'),0);self.assertEqual(m.g('sav_context_pending'),0);self.assertEqual(m.get('dos64_files_state_start',25),before);self.assertEqual(m.g('hdb_online'),1);self.assertEqual(L.bulk_model_open(m.m,1),0);self.assertEqual(L.bulk_model_open(m.m,2),1);self.assertEqual(L.save_model_position(m.m,2),12345);self.assertEqual(m.g('dos64_export_verified'),0);self.assertEqual(m.g('dos64_export_error'),7)
  finally:m.close()
 def test_10_invalid_native_ownership_rejects_before_wire(self):
  for field,value in [('dos64_files_owned_target',1),('dos64_files_target',1),('hdb_active',1),('hd_uncertain',1),('dos64_files_handle',2),('dos64_overlay_busy',1)]:
   m=Machine()
   try:
    m.p(field,value);commands=L.bulk_model_commands(m.m);m.call('dos64_native_tick',2000000);self.assertEqual(L.bulk_model_commands(m.m),commands);self.assertEqual(m.g('sav_borrowed'),0);self.assertEqual(L.bulk_model_open(m.m,2),1)
   finally:m.close()
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));(P/'ONLINE_SAVE_REPORT.json').write_text(json.dumps({'successful':r.wasSuccessful(),'tests':r.testsRun,'cases':records},indent=2)+'\n');sys.exit(not r.wasSuccessful())
