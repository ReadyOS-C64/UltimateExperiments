from pathlib import Path
import sys,os
sys.dont_write_bytecode=True
sys.pycache_prefix=str(Path(__file__).resolve().parent/('.absent-capsule-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import unittest,ctypes as C,struct,zlib,json,re
from test_select import UI,L
from test_browser import Regs
for name,ret,args in [('dos64_reu_poke',None,[C.c_void_p,C.c_uint32,C.c_uint8]),('dos64_reu_peek',C.c_uint8,[C.c_void_p,C.c_uint32]),('dos64_reu_fail_after',None,[C.c_void_p,C.c_uint64,C.c_uint32]),('dos64_dma_transfers',C.c_uint64,[C.c_void_p]),('dos64_dma_bytes',C.c_uint64,[C.c_void_p]),('dos64_reu_read',C.c_uint8,[C.c_void_p,C.c_uint32,C.c_void_p,C.c_size_t]),('bulk_model_seed',None,[C.c_void_p,C.c_char_p,C.c_void_p,C.c_uint32]),('bulk_reu_seed',None,[C.c_void_p,C.c_uint32,C.c_void_p,C.c_uint32])]:
 f=getattr(L,name);f.restype=ret;f.argtypes=args
L.dos64_step.argtypes=[C.c_void_p];L.dos64_step.restype=None
SLOT=0x2c0000;REPORT={}
def prepare(u,existing=False,profile=1):
 rows=[(32,b'DOS 1.img'),(32,b'DOS 2.img'),(32,b'DOS 3.img')]
 if existing:rows.append((32,b'OLD C.IMG'))
 u.directory(b'/',[(16,b'Home')]);u.directory(b'/Home',rows)
 assert u.begin()==1;u.ready();u.key(0,1);u.key(0,4)
 u.key(0,1);u.key(0,7);u.key(0,1);u.key(0,7);u.key(0,7);u.key(0,1)
 if existing:
  for _ in range(3):u.key(0,7)
  u.key(0,1)
 else:u.key(0,4)
 if profile:u.key(0,7)
 u.key(0,1);assert u.key(0,1)==2

def reu(u,offset=0,n=1024):
 b=C.create_string_buffer(n);assert L.dos64_reu_read(u.f.m,SLOT+offset,b,n)==1;return b.raw

def read_page(u,page):
 u.f.write('_sq_page',bytes([page]));low=u.call('_sq_read');n=low+(u.f.last_regs.x<<8);at=int.from_bytes(u.f.read('_sq_bytes',2),'little');return n,u.f.readat(at,n)

class Capsule(unittest.TestCase):
 def setUp(self):self.u=UI()
 def tearDown(self):self.u.close()
 def test_actual_private_done_full_record_and_resident_checked_reads(self):
  u=self.u;prepare(u);before=L.dos64_dma_transfers(u.f.m);self.assertEqual(u.call('_sq_publish'),1);REPORT['publish_cycles']=u.f.lastcost;REPORT['stack_min']=hex(u.f.soft_min);self.assertEqual(u.call('_sq_state'),2);raw=reu(u);self.assertEqual(raw[:8],b'D64Q\1\xa5\xc0\2');self.assertEqual(struct.unpack_from('<HHII',raw,8),(1,u.ticket,0x400000,int.from_bytes(u.f.read('_so_ui_crc',4),'little')));self.assertEqual(raw[20:32],bytes(12));self.assertEqual(raw[32:674],u.f.readat(int.from_bytes(u.f.read('_ss_choices',2),'little'),642));self.assertEqual(raw[674:700],bytes(26));self.assertEqual(zlib.crc32(raw[:700]),int.from_bytes(raw[700:704],'little'));self.assertEqual(raw[704:],bytes(320))
  n,a=read_page(u,0);REPORT['page0_cycles']=u.f.lastcost;self.assertEqual(n,512);n,b=read_page(u,1);REPORT['page1_cycles']=u.f.lastcost;self.assertEqual(n,192);self.assertEqual(a+b,raw[:704]);self.assertEqual(u.call('_sq_publish'),0);self.assertEqual(reu(u),raw);self.assertEqual(u.call('_sq_state'),2);REPORT['record_hex']=raw.hex();REPORT['publish_dma']=L.dos64_dma_transfers(u.f.m)-before-6
 def test_without_done_or_forged_public_phase_never_capture(self):
  u=self.u;u.f.write('_so_result',bytes([2,1,0,0,0,0,0,1,1,0]));self.assertEqual(u.call('_sq_publish'),0);self.assertEqual(u.call('_sq_state'),3);self.assertEqual(u.call('_sq_error'),1);self.assertEqual(reu(u),bytes(1024))
 def test_stale_valid_bytes_without_private_session_never_authorize(self):
  source=UI()
  try:prepare(source);self.assertEqual(source.call('_sq_publish'),1);valid=reu(source)
  finally:source.close()
  u=self.u;L.bulk_reu_seed.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p,C.c_uint32];L.bulk_reu_seed.restype=None;L.bulk_reu_seed(u.f.m,SLOT,valid,1024);self.assertEqual(read_page(u,0)[0],0);self.assertEqual(u.call('_sq_state'),0)
 def test_crc_corruption_in_either_page_revokes_private_capability(self):
  for offset in [0,5,8,12,16,32,511,512,673,699,700,703]:
   u=UI()
   try:
    prepare(u);self.assertEqual(u.call('_sq_publish'),1);L.dos64_reu_poke(u.f.m,SLOT+offset,L.dos64_reu_peek(u.f.m,SLOT+offset)^1);self.assertEqual(read_page(u,0)[0],0);self.assertEqual(u.call('_sq_state'),3);self.assertEqual(u.call('_sq_error'),6)
   finally:u.close()
 def test_partial_DMA_each_publication_step_never_ready(self):
  for skip in range(8):
   u=UI()
   try:
    prepare(u);L.dos64_reu_fail_after(u.f.m,skip,0);self.assertEqual(u.call('_sq_publish'),0);self.assertEqual(u.call('_sq_state'),3);self.assertIn(u.call('_sq_error'),[5,6]);self.assertEqual(u.leave(),1)
   finally:u.close()
 def test_RunStop_before_publish_revokes_and_releases_lease(self):
  u=self.u;prepare(u);u.call('_ps_key_poll');L.dos64_host_input_model_keys(u.f.m,bytes(7)+b'\x80');self.assertEqual(u.call('_sq_publish'),0);self.assertEqual(u.call('_sq_error'),3);L.dos64_host_input_model_keys(u.f.m,bytes(8));self.assertEqual(u.leave(),1)

def private_offsets(u):
 # Exact cc65 emitted storage layout, no guessed product addresses.
 text=Path('build/selection_capsule.s').read_text();segment='';offsets={};at={}
 for line in text.splitlines():
  m=re.match(r'\s*\.segment\s+"([^"]+)"',line)
  if m:segment=m.group(1);offsets.setdefault(segment,0)
  m=re.match(r'([A-Za-z_][A-Za-z_0-9]*):',line)
  if m:at[m.group(1)]=(segment,offsets.get(segment,0))
  m=re.match(r'\s*\.res\s+(\d+)',line)
  if m:offsets[segment]+=int(m.group(1))
 q=u.f.labels['_sq_page']+at['_q'][1]-at['_sq_page'][1]
 m=re.search(r'selection_capsule\.o:\n(?:(?!\w+\.o:).)*?UIBSS\s+Offs=([0-9A-F]+)',Path('build/setup.map').read_text(),re.S);assert m
 record=u.f.labels['__UIBSS_RUN__']+int(m.group(1),16)+at['_record'][1]
 return q,record

def start_to_dma(u,index,entry="_sq_publish"):
 f=u.f;ret=f.labels['fixture_return']-1;L.dos64_clear_writes(f.m);L.dos64_poke(f.m,0x1ff,ret>>8);L.dos64_poke(f.m,0x1fe,ret&255);L.dos64_set_regs(f.m,Regs(f.labels[entry],0xfd,0,0,0,0x24,0,0))
 for i in range(index+1):
  result=L.dos64_run(f.m,f.labels['_nf_dma'],12_000_000)
  assert result.status==2 and result.regs.pc==f.labels['_nf_dma'],('pause',i,result.status,hex(result.regs.pc))
  if i<index:L.dos64_step(f.m)
 return result

def finish_paused(u):
 f=u.f;result=L.dos64_run(f.m,f.labels['fixture_return'],12_000_000)
 assert result.status==0,('resume',result.status,hex(result.regs.pc));assert f.read('sp',2)==b'\xff\xcf'
 assert L.browser_bad_write(f.m,f.guard)==65536
 return result.regs.a

class Lifetime(unittest.TestCase):
 def test_exact_publication_DMA_trace_marker_last_and_private_busy(self):
  u=UI();trace=[]
  try:
   prepare(u);q,_=private_offsets(u);start_to_dma(u,0)
   expected=[(0,512,0),(512,512,0),(0,704,0),(0,512,1),(512,192,1),(704,320,1),(5,1,0),(5,1,1)]
   for index,(offset,n,direction) in enumerate(expected):
    address=int.from_bytes(u.f.read('_nf_io_address',4),'little');length=int.from_bytes(u.f.read('_nf_io_length',2),'little');kind=u.f.byte('_nf_io_direction');state=L.dos64_peek(u.f.m,q+24);marker=reu(u)[5]
    self.assertEqual((address,length,kind),(SLOT+offset,n,direction));self.assertEqual(state,1);self.assertEqual(marker,0xa5 if index==7 else 0)
    trace.append({'index':index,'reu_address':address,'length':length,'direction':kind,'private_state':state,'marker':marker})
    if index<7:
     L.dos64_step(u.f.m);result=L.dos64_run(u.f.m,u.f.labels['_nf_dma'],12_000_000);self.assertEqual((result.status,result.regs.pc),(2,u.f.labels['_nf_dma']))
   self.assertEqual(finish_paused(u),1);self.assertEqual(u.call('_sq_state'),2);Path('../PUBLICATION_TRACE.json').write_text(json.dumps(trace,indent=2)+'\n')
  finally:u.close()

 def test_marker_last_trace_and_source_mutation_before_write_rejected(self):
  for mutate in [False,True]:
   u=UI()
   try:
    prepare(u);_,record=private_offsets(u);start_to_dma(u,2)
    self.assertEqual(reu(u),bytes(1024))
    if mutate:L.dos64_poke(u.f.m,record+40,L.dos64_peek(u.f.m,record+40)^1)
    result=finish_paused(u);self.assertEqual(result,0 if mutate else 1)
    self.assertEqual(u.call('_sq_state'),3 if mutate else 2)
    self.assertEqual(reu(u)[5],0 if mutate else 0xa5);self.assertEqual(u.leave(),1)
   finally:u.close()
 def test_each_DMA_boundary_real_RunStop_never_publishes_private_ready(self):
  for index in range(8):
   u=UI()
   try:
    prepare(u);u.call('_ps_key_poll');start_to_dma(u,index)
    L.dos64_host_input_model_keys(u.f.m,bytes(7)+b'\x80');self.assertEqual(finish_paused(u),0)
    self.assertEqual(u.call('_sq_state'),3);self.assertEqual(u.call('_sq_error'),3)
    L.dos64_host_input_model_keys(u.f.m,bytes(8));self.assertEqual(u.leave(),1)
   finally:u.close()
 def test_each_resident_read_DMA_boundary_RunStop_revokes_before_exposure(self):
  for index in range(3):
   u=UI()
   try:
    prepare(u);self.assertEqual(u.call('_sq_publish'),1);u.f.write('_sq_page',b'\0');u.call('_ps_key_poll');start_to_dma(u,index,'_sq_read');L.dos64_host_input_model_keys(u.f.m,bytes(7)+b'\x80');self.assertEqual(finish_paused(u),0);self.assertEqual(L.dos64_get_regs(u.f.m).x,0);self.assertEqual(u.call('_sq_state'),3);self.assertEqual(u.call('_sq_error'),3)
   finally:u.close()
 def test_actual_UI_FAT_UI_reset_and_read_has_no_retired_UI_call(self):
  u=UI()
  try:
   prepare(u);self.assertEqual(u.call('_sq_publish'),1);raw=reu(u);self.assertEqual(u.leave(),1)
   q=struct.pack('<BIH',0xa5,0x400000,1000)+b'/Home'.ljust(128,b'\0');u.f.write('_so_request',q);self.assertEqual(u.call('_so_bind_home'),1)
   asset=Path('build/SETUP.FAT').read_bytes();L.bulk_model_seed(u.f.m,b'/Home/SETUP.FAT',asset,len(asset));u.f.write('_so_phase_request',b'\2');self.assertEqual(u.call('_so_begin'),1)
   start=int.from_bytes(u.f.read('_so_now',2),'little')
   for tick in range(20000):
    u.f.write('_so_now',struct.pack('<H',start+tick//32));u.call('_so_poll')
    if u.call('_so_state')!=1:break
   self.assertEqual(u.call('_so_state'),2);self.assertEqual(u.call('_so_enter'),1);fat_ticket=int.from_bytes(u.f.read('_so_result',10)[8:10],'little')
   # Actual linked FAT executes under its ticket; its sector buffer stays intact.
   u.f.write('_ns_io_owner',b'\xa5');u.f.write('_ns_capacity',struct.pack('<I',0x400000));self.assertEqual(u.call('_nf_init',2),0);self.assertEqual(u.call('_nf_plan'),0);sector=u.f.read('_nf_sector',512)
   # Poison former UI state getter address inside now-retired UI; resident read
   # must never dispatch it, even if public phase observations say UI.
   L.dos64_poke(u.f.m,u.f.labels['_ss_state'],0);u.f.write('_so_result',bytes([2,1,0,0,0,0,0,1,1,0]))
   self.assertEqual(u.call('_sq_publish'),0);a=read_page(u,0);b=read_page(u,1);self.assertEqual(a[1]+b[1],raw[:704]);self.assertEqual(u.f.read('_nf_sector',512),sector)
   u.f.write('_so_ticket',struct.pack('<H',fat_ticket));self.assertEqual(u.call('_so_leave'),1);u.f.write('_so_phase_request',b'\1');self.assertEqual(u.call('_so_begin'),1)
   start=int.from_bytes(u.f.read('_so_now',2),'little')
   for tick in range(20000):
    u.f.write('_so_now',struct.pack('<H',start+tick//32));u.call('_so_poll')
    if u.call('_so_state')!=1:break
   self.assertEqual(u.call('_so_state'),2);self.assertEqual(u.call('_so_enter'),1);u.ticket=int.from_bytes(u.f.read('_so_result',10)[8:10],'little')
   self.assertEqual(u.call('_ss_state'),0);self.assertEqual(u.f.readat(u.f.labels['__UIBSS_RUN__'],u.f.labels['__UIBSS_SIZE__']),bytes(u.f.labels['__UIBSS_SIZE__']))
   self.assertEqual(read_page(u,0)[1]+read_page(u,1)[1],raw[:704]);prepare(u);self.assertEqual(u.call('_sq_publish'),1);self.assertEqual(struct.unpack_from('<HH',reu(u),8),(2,u.ticket));self.assertEqual(u.leave(),1)
  finally:u.close()


class Boundaries(unittest.TestCase):
 def test_slot_canaries_and_short_prefixes_are_bounded(self):
  for prefix in [1,256,703]:
   u=UI()
   try:
    prepare(u)
    for address in [SLOT-1,SLOT+1024,0x3f0000,0x3ff000]:L.dos64_reu_poke(u.f.m,address,0xa7)
    L.dos64_reu_fail_after(u.f.m,2,prefix);self.assertEqual(u.call('_sq_publish'),0);self.assertEqual(u.call('_sq_error'),5)
    for address in [SLOT-1,SLOT+1024,0x3f0000,0x3ff000]:self.assertEqual(L.dos64_reu_peek(u.f.m,address),0xa7)
   finally:u.close()

 def test_configured_4MiB_bank_and_scaled_capacities(self):
  for capacity in [0x400000,0x410000,0x800000,0x1000000]:
   u=UI(capacity)
   try:
    prepare(u);self.assertEqual(u.call('_sq_publish'),1);self.assertEqual(struct.unpack_from('<I',reu(u),12)[0],capacity);self.assertEqual(read_page(u,0)[0],512);self.assertEqual(u.leave(),1)
   finally:u.close()
 def test_actual_existing_selection_and_both_profiles(self):
  for profile in [0,1]:
   u=UI()
   try:
    prepare(u,existing=True,profile=profile);self.assertEqual(u.call('_sq_publish'),1);raw=reu(u);self.assertEqual(raw[672:674],bytes([profile,1]));self.assertEqual(raw[544:672].split(b'\0')[0],b'/Home/OLD C.IMG')
   finally:u.close()

 def test_full_forged_wire_CRC_does_not_replace_private_identity(self):
  u=UI()
  try:
   prepare(u);self.assertEqual(u.call('_sq_publish'),1);raw=bytearray(reu(u));raw[50]^=1;struct.pack_into('<I',raw,700,zlib.crc32(raw[:700]));L.bulk_reu_seed(u.f.m,SLOT,bytes(raw),len(raw));self.assertEqual(read_page(u,1)[0],0);self.assertEqual(u.call('_sq_error'),6)
  finally:u.close()
 def test_canonical_padding_profile_presence_and_casefold_distinction(self):
  cases=[('home_root',0,b'/\0'),('home118',0,b'/'+b'H'*117+b'\0'),('hidden',128,b'/Home/X\0hidden'),('illegal',128,b'/Home/?.img\0'),('duplicate',256,b'/Home/DOS 1.img\0'),('case_alias',256,b'/home/dos 1.IMG\0'),('profile',640,b'\2'),('present',641,b'\2'),('absent_nonempty',512,b'/Home/C.IMG\0')]
  for name,offset,data in cases:
   u=UI()
   try:
    prepare(u);pointer=int.from_bytes(u.f.read('_ss_choices',2),'little');L.dos64_load(u.f.m,pointer+offset,data,len(data));before=L.dos64_dma_transfers(u.f.m);self.assertEqual(u.call('_sq_publish'),0,name);self.assertEqual(u.call('_sq_error'),1,name);self.assertEqual(L.dos64_dma_transfers(u.f.m),before,name)
   finally:u.close()
 def test_private_generation_wrap_refuses_without_DMA(self):
  u=UI()
  try:
   prepare(u);q,_=private_offsets(u);L.dos64_poke(u.f.m,q+20,255);L.dos64_poke(u.f.m,q+21,255);before=L.dos64_dma_transfers(u.f.m);self.assertEqual(u.call('_sq_publish'),0);self.assertEqual(u.call('_sq_error'),8);self.assertEqual(u.call('_sq_state'),3);self.assertEqual(L.dos64_dma_transfers(u.f.m),before)
  finally:u.close()
 def test_public_request_capacity_and_phase_cannot_rebind_identity(self):
  u=UI()
  try:
   prepare(u);u.f.write('_so_request',struct.pack('<BIH',0,0x1000000,1)+bytes(128));u.f.write('_so_result',bytes([2,2,0,0,0,0,0,1,255,255]));self.assertEqual(u.call('_sq_publish'),1);self.assertEqual(struct.unpack_from('<I',reu(u),12)[0],0x400000);self.assertEqual(read_page(u,0)[0],512)
  finally:u.close()
 def test_real_private_open_handle_prevents_read_even_forged_observation(self):
  u=UI()
  try:
   prepare(u);self.assertEqual(u.call('_sq_publish'),1);L.bulk_model_seed(u.f.m,b'/usb1/Owned/SRC.BIN',b'X',1);u.f.filejob(0,2);u.f.write('_br_result',bytes(18));self.assertEqual(read_page(u,0)[0],0);self.assertEqual(u.call('_sq_error'),2);u.f.filejob(0,3);self.assertEqual(u.leave(),1)
  finally:u.close()
 def test_changed_UI_code_cannot_dispatch_capture_despite_public_UI_phase(self):
  u=UI()
  try:
   prepare(u);before=L.dos64_dma_transfers(u.f.m);L.dos64_poke(u.f.m,u.f.labels['_ss_state'],0);u.f.write('_so_result',bytes([2,1,0,0,0,0,0,1,1,0]));self.assertEqual(u.call('_sq_publish'),0);self.assertEqual(u.call('_sq_state'),0);self.assertEqual(L.dos64_dma_transfers(u.f.m),before)
  finally:u.close()
 def test_resident_read_partial_DMA_and_invalid_page_never_expose(self):
  for page,skip in [(0,0),(0,1),(0,2),(1,2),(2,None)]:
   u=UI()
   try:
    prepare(u);self.assertEqual(u.call('_sq_publish'),1)
    if skip is not None:L.dos64_reu_fail_after(u.f.m,skip,0)
    self.assertEqual(read_page(u,page)[0],0);self.assertEqual(u.call('_sq_state'),3);self.assertIn(u.call('_sq_error'),[5,7]);self.assertEqual(u.leave(),1)
   finally:u.close()
 def test_explicit_cancel_revokes_prior_ready_record(self):
  u=UI()
  try:
   prepare(u);self.assertEqual(u.call('_sq_publish'),1);u.call('_sq_cancel');self.assertEqual(u.call('_sq_state'),3);self.assertEqual(u.call('_sq_error'),3);self.assertEqual(read_page(u,0)[0],0);self.assertEqual(reu(u)[5],0xa5)
  finally:u.close()

if __name__=='__main__':
 result=unittest.main(verbosity=2,exit=False).result;Path('../CAPSULE_RESULTS.json').write_text(json.dumps(REPORT,indent=2)+'\n');raise SystemExit(not result.wasSuccessful())
