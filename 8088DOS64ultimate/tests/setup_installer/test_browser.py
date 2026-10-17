from pathlib import Path
import sys,os
sys.dont_write_bytecode=True;sys.pycache_prefix=str(Path(__file__).resolve().parent/('.absent-source-cache-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import ctypes as C,struct,unittest
P=Path(__file__).resolve().parent;L=C.CDLL(str(P/'browser-peddle.dylib'))
class Regs(C.Structure):_fields_=[('pc',C.c_uint16),('sp',C.c_uint8),('a',C.c_uint8),('x',C.c_uint8),('y',C.c_uint8),('p',C.c_uint8),('cycles',C.c_uint64),('instructions',C.c_uint64)]
class Result(C.Structure):_fields_=[('regs',Regs),('status',C.c_uint),('stack',C.c_uint8)]
L.setup_crc_table_write.restype=C.c_uint16;L.setup_crc_table_write.argtypes=[C.c_void_p]
L.setup_soft_stack_min.restype=C.c_uint16;L.setup_soft_stack_min.argtypes=[C.c_void_p]
L.dos64_get_regs.restype=Regs;L.dos64_get_regs.argtypes=[C.c_void_p]
ptr=C.c_void_p;u8=C.c_uint8;u16=C.c_uint16;u32=C.c_uint32;u64=C.c_uint64;size=C.c_size_t
for n,ret,args in [('dos64_create',ptr,[]),('dos64_destroy',None,[ptr]),('dos64_load',None,[ptr,u16,ptr,size]),('dos64_peek',u8,[ptr,u16]),('dos64_poke',None,[ptr,u16,u8]),('dos64_set_regs',None,[ptr,Regs]),('dos64_run',Result,[ptr,u16,u64]),('dos64_clear_writes',None,[ptr]),('browser_bad_write',u32,[ptr,ptr]),('browser_bank',u16,[ptr]),('dos64_uci_model_enable',None,[ptr,u16,u32,u8]),('dos64_uci_model_stuck',None,[ptr,u8]),('dos64_uci_model_count',u64,[ptr,u8]),('dos64_enable_reu',None,[ptr]),('bulk_model_enable',None,[ptr]),('bulk_model_seed',None,[ptr,C.c_char_p,ptr,u32]),('dir_model_enable',None,[ptr]),('dir_model_path',None,[ptr,C.c_char_p]),('dir_model_row',None,[ptr,C.c_char_p,u8,ptr,u32]),('dir_model_fault',None,[ptr,C.c_int,C.c_int,C.c_int]),('dir_model_commands',u32,[ptr]),('dir_model_cmd_size',u32,[ptr,u32]),('dir_model_cmd_byte',u8,[ptr,u32,u32])]:
 f=getattr(L,n);f.restype=ret;f.argtypes=args
class F:
 def __init__(self):
  self.labels={s.split()[2].lstrip('.'):int(s.split()[1],16)for s in(P/'build/setup.labels').read_text().splitlines()if s.startswith('al ')}
  self.guard=bytearray(65536)
  for start,count in [(0,2),(0x20,32),(0x100,256),(0xc900,1024),(0xcd00,768),(self.labels['__BSS_RUN__'],self.labels['__BSS_SIZE__']),(self.labels['__HIGHBSS_RUN__'],self.labels['__HIGHBSS_SIZE__']),(self.labels['dos64_uci_state_start'],self.labels['dos64_files_state_end']-self.labels['dos64_uci_state_start']),(0xc000,2048),(self.labels['_br_config'],134),(0xdf1c,2)]:self.guard[start:start+count]=b'\1'*count
  for name in ['uci_status_read','uci_control_write','uci_id_read','uci_command_write','uci_data_read','uci_stat_read','read','store']:self.guard[self.labels[name]+1:self.labels[name]+3]=b'\1\1'
  self.guard=bytes(self.guard)
  self.m=L.dos64_create();b=(P/'build/setup.prg').read_bytes();L.dos64_load(self.m,int.from_bytes(b[:2],'little'),b[2:],len(b)-2)
  L.dos64_uci_model_enable(self.m,0xdf1c,3,0xc9);L.dos64_enable_reu(self.m);L.bulk_model_enable(self.m);L.dir_model_enable(self.m);self.call('runtime_init');self.call('_bc_init');self.tick=0
  root=b'/usb1/Owned';config=b'\xa5\1'+struct.pack('<I',0x400000)+root.ljust(128,b'\0')+b'\xa5\2'+struct.pack('<I',0x400000)+root.ljust(128,b'\0');self.write('_bc_config',config)
  if os.environ.get('DOS64_TEST_PHASE')=='FAT':self.install_phase('FAT')
 def install_phase(self,phase):
  # Explicit test-fixture DMA, not a qualified product loader or dispatch gate.
  assert phase in ['UI','FAT'];b=(P/'build/setup.prg').read_bytes();data=b[0x6000-0x0801+2:]if phase=='UI'else(P/'build/fat-overlay.bin').read_bytes();assert 0<len(data)<=0x5000
  data=data.ljust(0x5000,b'\0');slot=0x3e0000 if phase=='UI'else 0x3e8000
  L.bulk_reu_seed.restype=None;L.bulk_reu_seed.argtypes=[C.c_void_p,C.c_uint32,C.c_void_p,C.c_uint32];L.bulk_reu_seed(self.m,slot,data,len(data))
  self.write('_nf_io_address',struct.pack('<I',slot));self.write('_nf_io_buffer',struct.pack('<H',0x6000));self.write('_nf_io_length',struct.pack('<H',len(data)));self.write('_nf_io_direction',b'\1')
  old=self.guard;guard=bytearray(old);guard[0x6000:0xb000]=b'\1'*0x5000;guard[0xdf01:0xdf0b]=b'\1'*10;self.guard=bytes(guard)
  try:self.call('_nf_dma');assert self.byte('_nf_io_status')==0;assert self.readat(0x6000,0x5000)==data
  finally:self.guard=old
 def close(self):L.dos64_destroy(self.m)
 def readat(self,a,n):return bytes(L.dos64_peek(self.m,a+i)for i in range(n))
 def read(self,n,length):return self.readat(self.labels[n],length)
 def write(self,n,b):L.dos64_load(self.m,self.labels[n],b,len(b))
 def byte(self,n):return self.read(n,1)[0]
 def call(self,n,arg=0x71,budget=2000000):
  coststart=L.dos64_get_regs(self.m).cycles;bank=L.browser_bank(self.m);L.dos64_clear_writes(self.m);ret=self.labels['fixture_return']-1;L.dos64_poke(self.m,0x1ff,ret>>8);L.dos64_poke(self.m,0x1fe,ret&255);L.dos64_set_regs(self.m,Regs(self.labels[n],0xfd,arg,0x82,0x93,0x24,0,0));r=L.dos64_run(self.m,self.labels['fixture_return'],budget)
  self.last_regs=r.regs;self.lastcost=r.regs.cycles-coststart;self.soft_min=min(getattr(self,"soft_min",0xd000),L.setup_soft_stack_min(self.m));bad=L.browser_bad_write(self.m,self.guard)
  if n!='_ps_init' and L.browser_bank(self.m)!=bank:raise AssertionError(('nativebank restore',n))
  if n not in ['_si_begin','_rw_begin','_sl_begin','_c32_init','_so_prepare','_su_poll','_rc_poll','_fw_run'] and L.setup_crc_table_write(self.m)!=0xcd00:raise AssertionError(('CRCtablewrite/softstackoverflow',n,hex(L.setup_crc_table_write(self.m))))
  if self.soft_min<0xcd00:raise AssertionError(('actualsoftstackoverflow',hex(self.soft_min)))
  if bad!=65536:raise AssertionError(('forbidden nativewrite',n,hex(bad)))
  if r.status:raise AssertionError((n,r.status,hex(r.regs.pc),r.regs.cycles))
  if self.read('sp',2)!=b'\xff\xcf':raise AssertionError(('softstack',n,self.read('sp',2)))
  if r.stack>=120:raise AssertionError(('hardwarestack',r.stack))
  return r.regs.a
 def directory(self,path=b'/',rows=()):
  L.dir_model_path(self.m,path)
  for attr,name in rows:L.dir_model_row(self.m,path,attr,name,len(name))
 def request(self,path=b'/',first=0,folders=0,timeout=1000,owner=0xa5,target=1):
  self.write('_db_request',struct.pack('<BBBHH',owner,target,folders,first,timeout)+path.ljust(128,b'\0'))
 def begin(self,**kw):self.request(**kw);return self.call('_db_begin')
 def result(self):return struct.unpack('<6BHH',self.read('_db_result',10))
 def poll(self,now=None):
  if now is None:self.tick+=1;now=self.tick//32
  self.write('_db_now',struct.pack('<H',now&65535));self.call('_db_poll')
 def finish(self):
  for _ in range(200000):
   if self.result()[0]!=1:return self.result()
   self.poll()
  raise AssertionError('bounded native directory poll budget')
 def run(self,**kw):assert self.begin(**kw)==1;return self.finish()
 def pagebytes(self):return self.readat(int.from_bytes(self.read('_db_page',2),'little'),2216)
 def page(self):
  b=self.pagebytes();rows=[]
  for i in range(b[2212]):
   row=b[128+173*i:128+173*(i+1)];n=int.from_bytes(row[168:170],'little');rows.append({'raw':row[:128],'name':row[:n]if n<=127 else None,'display':row[128:168].split(b'\0')[0],'length':n,'attr':row[170],'usable':row[171],'cut':row[172]})
  return {'path':b[:128].split(b'\0')[0],'rows':rows,'first':int.from_bytes(b[2204:2206],'little'),'total':int.from_bytes(b[2206:2208],'little'),'scanned':int.from_bytes(b[2208:2210],'little'),'prev':b[2213],'next':b[2214],'valid':b[2215]}
 def wire(self):return [bytes(L.dir_model_cmd_byte(self.m,i,j)for j in range(L.dir_model_cmd_size(self.m,i)))for i in range(L.dir_model_commands(self.m))]
 def filejob(self,slot,op,mode=1,path=b'/usb1/Owned/SRC.BIN'):
  self.write('_bc_slot',bytes([slot]));self.write('_br_request',struct.pack('<BBIII',op,mode,0,0x200000,1)+path.ljust(128,b'\0'));assert self.call('_bc_start')==1
  for _ in range(10000):
   self.tick+=1;self.write('_br_now',struct.pack('<H',self.tick//32));self.call('_bc_poll')
   if self.read('_bc_status',29*2)[slot*29]!=1:return
  raise AssertionError('file job bound')
class Browser(unittest.TestCase):
 def setUp(self):self.f=F()
 def tearDown(self):self.f.close()
 def test_target_ABI_defaultoff_and_exactwire(self):
  f=self.f;self.assertEqual(struct.unpack('<4H',f.read('_db_abi_sizes',8)),(135,10,173,2216));f.directory(rows=[(0x10,b'DOS 3.3'),(0x20,b'MS-DOS Version 3.3 (Microsoft) (1988) - 1 of 3.img')]);self.assertEqual(f.begin(owner=0),0);self.assertEqual(f.wire(),[]);self.assertEqual(f.run()[0],2);self.assertEqual(f.wire(),[b'\1\x11/',b'\1\x13',b'\1\x14']);p=f.page();self.assertEqual((p['valid'],p['total']), (0xa5,2));self.assertEqual(p['rows'][1]['name'],b'MS-DOS Version 3.3 (Microsoft) (1988) - 1 of 3.img');self.assertEqual(p['rows'][1]['cut'],1);self.assertEqual(f.call('_db_select',1),1);self.assertEqual(f.read('_db_selected_path',128).split(b'\0')[0],b'/MS-DOS Version 3.3 (Microsoft) (1988) - 1 of 3.img')
 def test_root_parent_spaces_and_pages(self):
  f=self.f;path=b'/sd/ My DOS';rows=[(0x10 if i%2==0 else 0x20,('ENTRY %02d'%i).encode())for i in range(25)];f.directory(path,rows);self.assertEqual(f.run(path=path)[0],2);p=f.page();self.assertEqual((len(p['rows']),p['total'],p['next'],p['prev']),(12,25,1,0));self.assertEqual(f.call('_db_parent'),1);self.assertEqual(f.read('_db_selected_path',128).split(b'\0')[0],b'/sd');self.assertEqual(f.run(path=path,first=24)[0],2);p=f.page();self.assertEqual((len(p['rows']),p['first'],p['next'],p['prev']),(1,24,0,1));self.assertEqual(f.run(path=path,folders=1)[0],2);p=f.page();self.assertEqual((p['total'],p['scanned'],len(p['rows']),p['next']),(13,25,12,1));f.directory();self.assertEqual(f.run()[0],2);self.assertEqual(f.call('_db_parent'),1);self.assertEqual(f.read('_db_selected_path',128).split(b'\0')[0],b'/')
 def test_pageboundary12and13_fulldrain(self):
  f=self.f
  for n in [12,13]:
   rows=[(0x20,('F%d'%i).encode())for i in range(n)];f.directory(rows=rows);before=L.dos64_uci_model_count(f.m,4);self.assertEqual(f.run()[0],2);p=f.page();self.assertEqual((len(p['rows']),p['total'],p['next']),(12,n,int(n==13)));self.assertEqual(L.dos64_uci_model_count(f.m,4)-before,sum(1+len(x[1])for x in rows));self.assertEqual(f.result()[4],0)
 def test_empty_primary_ONLY_open_exactexception(self):
  f=self.f;f.directory();self.assertEqual(f.run()[0],2);self.assertEqual(f.wire(),[b'\1\x11/',b'\1\x13']);self.assertEqual(f.page()['total'],0);old=f.pagebytes()
  for opcode,kind in [(0x11,5),(0x13,6)]:L.dir_model_fault(f.m,opcode,0,kind);self.assertEqual(f.run()[1],4);self.assertEqual(f.pagebytes(),old)
  f.directory(rows=[(0x20,b'X')]);L.dir_model_fault(f.m,0x14,0,5);self.assertEqual(f.run()[1],4);self.assertEqual(f.pagebytes(),old)
 def test_lateerror_afterfullpage_preservescommitted(self):
  f=self.f;f.directory(rows=[(0x20,b'ORIGINAL')]);self.assertEqual(f.run()[0],2);old=f.pagebytes();f.directory(rows=[(0x20,('NEW%d'%i).encode())for i in range(20)]);L.dir_model_fault(f.m,0x14,19,1);before=L.dos64_uci_model_count(f.m,4);r=f.run();self.assertEqual((r[0],r[1],r[4]),(3,4,0));self.assertEqual(f.pagebytes(),old);self.assertEqual(L.dos64_uci_model_count(f.m,4)-before,sum(1+len(('NEW%d'%i).encode())for i in range(20)))
 def test_long_noncanonical_raw_neverselect_and_display_separate(self):
  f=self.f;names=[b'A..B.IMG',b' leading space.img',b'bad/name',b'a.',b'a ',b'a\x00b',b'\x80bad',b'X'*128,b'X'*255];f.directory(rows=[(0x20,n)for n in names]);self.assertEqual(f.run()[0],2);p=f.page();self.assertEqual([r['usable']for r in p['rows']],[1,1,0,0,0,0,0,0,0]);self.assertEqual(p['rows'][5]['name'],b'a\x00b');self.assertEqual(p['rows'][7]['raw'],bytes(128));self.assertEqual(p['rows'][8]['length'],255);f.write('_db_selected_path',b'OLD\0'.ljust(128,b'\0'))
  for i in range(2,9):self.assertEqual(f.call('_db_select',i),0);self.assertEqual(f.read('_db_selected_path',128).split(b'\0')[0],b'OLD')
 def test_canonical_request_boundaries_no_wire_or_truncation(self):
  f=self.f
  for bad in [b'',b'relative',b'/usb1//a',b'/usb1/..',b'/usb1/a.',b'/usb1/a ',b'/usb1/a?',b'/usb1/\x80',b'/'+b'x'*127]:self.assertEqual(f.begin(path=bad),0);self.assertEqual(f.wire(),[])
  path=b'/'+b'x'*126;f.directory(path,[(0x20,b'X')]);self.assertEqual(f.run(path=path)[0],2);self.assertEqual(f.wire()[0],b'\1\x11'+path);self.assertEqual(f.page()['rows'][0]['usable'],0)
 def test_queue_overflow_More_and_entrybounds_failclosed(self):
  f=self.f;f.directory(rows=[(0x20,b'OLD')]);f.run();old=f.pagebytes()
  for kind in [2,3,4,7]:
   f.directory(rows=[(0x20,b'A'),(0x20,b'B')]);L.dir_model_fault(f.m,0x14,0,kind);r=f.run();self.assertEqual(r[0],3);self.assertEqual(f.pagebytes(),old)
  L.dir_model_fault(f.m,0,0,0);f.directory(rows=[(0x20,b'X')]*1025);r=f.run();self.assertEqual(r[1],6);self.assertEqual(r[7],1024);self.assertEqual(f.pagebytes(),old)
 def test_cancel_once_firsterror_and_oldpage(self):
  f=self.f;f.directory(rows=[(0x20,b'OLD')]);f.run();old=f.pagebytes();f.directory(rows=[(0x20,b'NEW')]*20);self.assertEqual(f.begin(),1);before=L.dos64_uci_model_count(f.m,2);f.call('_db_cancel');f.call('_db_cancel');r=f.finish();self.assertEqual((r[1],r[4]),(7,0));self.assertEqual(L.dos64_uci_model_count(f.m,2)-before,1);self.assertEqual(f.pagebytes(),old)
 def test_elapsed_wrap_timeout_nofixedpoll_pacing_and_failedrecovery(self):
  f=self.f;f.directory(rows=[(0x20,b'X')]);f.write('_db_now',struct.pack('<H',65534));self.assertEqual(f.begin(timeout=4),1);L.dos64_uci_model_stuck(f.m,1)
  for _ in range(1000):f.call('_db_poll')
  self.assertEqual(f.result()[0],1);f.poll(3);self.assertEqual(f.result()[1],8);L.dos64_uci_model_stuck(f.m,0)
  for n in range(4,20):f.poll(n)
  self.assertEqual((f.result()[0],f.result()[4]),(3,0))
  f.write('_uci_recovery_timeout',struct.pack('<H',3));f.write('_db_now',struct.pack('<H',100));self.assertEqual(f.begin(timeout=2),1);L.dos64_uci_model_stuck(f.m,1);f.poll(103);f.poll(107);self.assertEqual((f.result()[0],f.result()[1],f.result()[4],f.result()[5]),(3,8,1,1))
 def test_both_private_filecontexts_closed_and_browser_exclusive(self):
  f=self.f;f.directory(rows=[(0x20,b'X')]);L.bulk_model_seed(f.m,b'/usb1/Owned/SRC.BIN',b'X',1);f.filejob(0,2,mode=1);self.assertEqual(f.begin(),0);self.assertEqual(f.result()[3],2);self.assertEqual(f.wire(),[]);f.filejob(1,2,mode=6,path=b'/usb1/Owned/OUT.BIN');f.filejob(1,3);self.assertEqual(f.begin(),0);self.assertEqual(f.wire(),[]);f.filejob(0,3);self.assertEqual(f.begin(),1);self.assertEqual(f.call('_bc_start'),0);self.assertEqual(f.finish()[0],2)
 def test_outofrange_page_retains_oldcommit(self):
  f=self.f;f.directory(rows=[(0x20,b'ONLY')]);f.run();old=f.pagebytes();self.assertEqual(f.run(first=12)[1],9);self.assertEqual(f.pagebytes(),old)

 def test_no_publication_until_finalquiet_and1024_positiveboundary(self):
  f=self.f;f.directory(rows=[(0x20,b'OLD')]);f.run();old=f.pagebytes();f.directory(rows=[(0x20,b'NEW')]*1024);self.assertEqual(f.begin(),1)
  while f.result()[0]==1:self.assertEqual(f.pagebytes(),old);f.poll()
  self.assertEqual((f.result()[0],f.result()[7],f.result()[4]),(2,1024,0));self.assertEqual(f.byte('_uci_state'),9);self.assertEqual(f.page()['total'],1024)
 def test_raw_exact_path_fit_attributes_and_hidden_input(self):
  f=self.f;f.directory(rows=[(0x20,b'X'*126),(0x20,b'Y'*127),(8,b'VOLUME'),(0x80,b'BAD'),(0x10,b'.'),(0x10,b'..')]);self.assertEqual(f.run()[0],2);self.assertEqual([r['usable']for r in f.page()['rows']],[1,0,0,0,0,0]);self.assertEqual(f.call('_db_select',0),1);self.assertEqual(f.read('_db_selected_path',128),b'/'+b'X'*126+b'\0');old=f.pagebytes();before=f.wire();self.assertEqual(f.begin(path=b'/\0HIDDEN'),0);self.assertEqual(f.pagebytes(),old);self.assertEqual(f.wire(),before)
 def test_status_then_cancel_preserves_first_error_and_abortonce(self):
  f=self.f;f.directory(rows=[(0x20,b'OLD')]);f.run();old=f.pagebytes();f.directory(rows=[(0x20,b'NEW')]*20);L.dir_model_fault(f.m,0x14,19,1);self.assertEqual(f.begin(),1);before=L.dos64_uci_model_count(f.m,2)
  while not f.result()[1]:f.poll()
  self.assertEqual(f.result()[1],4);f.call('_db_cancel');f.call('_db_cancel');self.assertEqual(f.finish()[1],4);self.assertEqual(L.dos64_uci_model_count(f.m,2)-before,1);self.assertEqual(f.pagebytes(),old)
 def test_activequeue_and_unknown_file_handle_refuse_without_wire(self):
  f=self.f;f.directory(rows=[(0x20,b'X')])
  for state in range(1,9):f.write('_uci_state',bytes([state]));self.assertEqual(f.begin(),0);self.assertEqual(f.wire(),[])
  f.write('_uci_state',b'\0');f.filejob(0,2,mode=1,path=b'/usb1/Owned/MISSING.BIN');self.assertEqual(f.begin(),0);self.assertEqual(f.wire(),[])
 def test_wrong_transport_ID_cannot_release_unproven_lease(self):
  f=self.f;f.directory(rows=[(0x20,b'X')]);L.dos64_uci_model_enable(f.m,0xdf1c,3,0xce);self.assertEqual(f.begin(),1);self.assertEqual((f.result()[0],f.result()[1],f.result()[4]),(3,3,1));self.assertEqual(f.wire(),[]);self.assertEqual(f.begin(),0)
 def test_target2_directory_and_snapshot_inputs(self):
  f=self.f;f.directory(b'/sd/My DOS',[(0x10,b'SUBDIR'),(0x20,b'A.IMG')]);self.assertEqual(f.begin(path=b'/sd/My DOS',target=2),1);f.request(path=b'/wrong',target=1);self.assertEqual(f.call('_db_begin'),0);self.assertEqual(f.finish()[0],2);self.assertEqual(f.page()['path'],b'/sd/My DOS');self.assertEqual(f.wire(),[b'\2\x11/sd/My DOS',b'\2\x13',b'\2\x14'])


 def test_forged_publichandle_cannot_launder_source_through_closed_othercontext(self):
  f=self.f;f.directory(rows=[(0x20,b'X')]);L.bulk_model_seed(f.m,b'/usb1/Owned/SRC.BIN',b'X',1);f.filejob(0,2,mode=1);self.assertEqual(f.begin(),0)
  L.dos64_poke(f.m,f.labels['_br_result']+3,0);f.write('_bc_slot',b'\1');self.assertEqual(f.call('_bc_clear_error'),1);self.assertEqual(f.begin(),0);self.assertEqual(f.result()[3],2);self.assertEqual(f.wire(),[])

if __name__=='__main__':unittest.main(verbosity=2)
