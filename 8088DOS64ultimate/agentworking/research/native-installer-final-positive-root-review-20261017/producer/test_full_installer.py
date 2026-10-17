from pathlib import Path
import sys,os,ctypes as C,struct,zlib,json,hashlib,time,unittest
sys.dont_write_bytecode=True
sys.pycache_prefix=str(Path(__file__).resolve().parent/('.absent-full-root-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
from test_matched_setup import Context,INPUT,L
from dos_disk_inspect import Volume,inspect
P=Path(__file__).resolve().parent.parent
for name,ret,args in [('bulk_model_size',C.c_uint32,[C.c_void_p,C.c_char_p]),('bulk_model_open',C.c_uint8,[C.c_void_p,C.c_uint8]),('fw_crc_write_guard',None,[C.c_void_p,C.c_uint16,C.c_uint16]),('fw_crc_bad_write',C.c_uint32,[C.c_void_p]),('dos64_graphics_color_peek',C.c_uint8,[C.c_void_p,C.c_uint16])]:
 fn=getattr(L,name);fn.restype=ret;fn.argtypes=args
REPORT={}
def canonical_tables():
 table=[]
 for i in range(256):
  v=i
  for _ in range(8):v=(v>>1)^(0xedb88320 if v&1 else 0)
  table.append(v)
 return b''.join(bytes((v>>(8*k))&255 for v in table)for k in range(4))
class Whole(Context):
 def __init__(self):
  super().__init__();data=Path('build/SETUP.PUB').read_bytes();L.bulk_model_seed(self.f.m,b'/Home/SETUP.PUB',data,len(data))
 def root(self):
  L.dos64_cia_clock_advance(self.f.m,1024)
  L.fw_crc_write_guard(self.f.m,self.f.labels['_c32_init'],self.f.labels['_c32_reset'])
  self.f.call('_rc_poll',budget=50_000_000_000);cost=self.f.lastcost
  assert L.fw_crc_bad_write(self.f.m)==65536,'CRC writes outside exact native initializer'
  assert self.f.readat(0xc900,1024)==canonical_tables(),'Canonical complete CRC tables'
  self.state=self.call('_rc_state');return self.state,cost
 def lock_code(self,pub=False):
  g=bytearray(self.f.guard);g[0x6000:0xb000]=bytes(0x5000)
  if pub:
   at=self.f.labels['__PUBBSS_RUN__'];n=self.f.labels['__PUBBSS_SIZE__'];g[at:at+n]=b'\1'*n
  self.f.guard=bytes(g)
 def created(self):
  out=[]
  for i in range(L.bulk_model_commands(self.f.m)):
   if L.bulk_model_command(self.f.m,i,1)==2 and L.bulk_model_command(self.f.m,i,2)&4:
    name=bytearray()
    for j in range(3,131):
     b=L.bulk_model_command(self.f.m,i,j)
     if not b:break
     name.append(b)
    out.append((L.bulk_model_command(self.f.m,i,0),name.decode('ascii')))
  return out
 def prepare(self):
  self.select2m();assert self.finish()==4
  assert self.facts()[180]==0;self.lock_code()
 def build_disks(self):
  state,cost=self.root();assert state==3,('FAT root',state,self.call('_rc_error'),self.f.read('_fw_internal',14))
  assert self.facts()[180]==3 and self.f.byte('_fw_internal')==2
  assert self.call('_nc_pending')==0 and self.call('_bc_files_closed')==1
  assert self.call('_so_fat_ticket')==0,'Root retired FAT before PUB replacement'
  # No overlaid frame is live in state3; only this root-owned replacement may
  # write the phase window. Revoke code writes immediately after authentic entry.
  g=bytearray(self.f.guard);g[0x6000:0xb000]=b'\1'*0x5000;self.f.guard=bytes(g)
  for _ in range(3000):
   state,_=self.root()
   if state!=3:break
  assert state==6,('PUB root',state,self.call('_rc_error'))
  assert self.call('_so_publish_ticket')!=0
  self.lock_code(True);return cost
class Cases(unittest.TestCase):
 def make(self):u=Whole();self.addCleanup(u.close);u.prepare();return u
 def test_full_native_SYS_UI_sources_disks_publication_root_success(self):
  u=self.make();before=u.facts();start=time.monotonic();fwcost=u.build_disks()
  self.assertEqual(u.created(),[(2,'/Home/C.IMG'),(2,'/Home/B.IMG')])
  state,pwcost=u.root();self.assertEqual(state,7,(u.call('_rc_error'),u.call('_pw_error')))
  self.assertEqual(u.call('_rc_error'),0);self.assertEqual(u.facts()[180],31)
  self.assertEqual(u.call('_pw_state'),2);self.assertEqual(u.call('_pw_stage'),5)
  self.assertEqual(u.call('_bc_files_closed'),1);self.assertEqual(u.call('_so_publish_ticket'),0)
  caption=b'INSTALL COMPLETE - RUN START.PRG';self.assertEqual(u.f.readat(0x400+23*40,len(caption)),caption);self.assertEqual(bytes(L.dos64_graphics_color_peek(u.f.m,0xd800+23*40+i)for i in range(len(caption))),bytes([1])*len(caption))
  self.assertEqual(u.created(),[(2,'/Home/'+n)for n in ['C.IMG','B.IMG','A.IMG','START.PRG','DOS64.CFG']])
  output={n:u.file(('/Home/'+n).encode(),size)for n,size in [('C.IMG',2097152),('B.IMG',368640),('A.IMG',368640),('START.PRG',20480),('DOS64.CFG',576)]}
  self.assertEqual(u.f.read('_fd_code',1),b'\0')
  for name in ['DOS64.PRG','DOS64.REL','START.INO','DOS64.MNU','START.RCV','START.RFW']:
   expected=(Path('release-assets')/name).read_bytes();output[name]=u.file(('/Home/'+name).encode(),len(expected));self.assertEqual(output[name],expected)
  c,b,a,cfg=map(output.get,['C.IMG','B.IMG','A.IMG','DOS64.CFG'])
  inspect(c,(128,2,16));vc,vb,va=Volume(c[8192:]),Volume(b),Volume(a);self.assertEqual(vb.payloads,{})
  for i,img in enumerate(INPUT[:3]):
   for name,data in Volume(img).payloads.items():self.assertEqual(vc.payloads['DOS/DISK%d/'%(i+1)+name],data)
  original=Volume(INPUT[0])
  for name in ['IO.SYS','MSDOS.SYS','COMMAND.COM']:self.assertEqual(va.payloads[name],original.payloads[name])
  self.assertEqual(va.payloads['CONFIG.SYS'],b'FILES=20\r\nBUFFERS=10\r\n');self.assertIn(b'C:\\DOS',va.payloads['AUTOEXEC.BAT'])
  facts=u.facts();self.assertEqual(facts[:154],before[:154]);self.assertEqual(struct.unpack_from('<6I',facts,154),(len(c),zlib.crc32(c),len(b),zlib.crc32(b),len(a),zlib.crc32(a)))
  self.assertEqual(zlib.crc32(cfg[:572]),struct.unpack_from('<I',cfg,572)[0]);self.assertEqual(zlib.crc32(cfg),0x2144df1c)
  for at,name in [(8,b'/Home'),(136,b'/Home/A.IMG'),(264,b'/Home/B.IMG'),(392,b'/Home/C.IMG')]:self.assertEqual(cfg[at:at+128].split(b'\0')[0],name)
  self.assertEqual(struct.unpack_from('<II',cfg,528),(zlib.crc32(a),zlib.crc32(b)))
  for path,data in zip([b'/Home/DOS 1.img',b'/Home/DOS 2.img',b'/Home/DOS 3.img'],INPUT[:3]):self.assertEqual(u.file(path,len(data)),data)
  commands=L.bulk_model_commands(u.f.m);self.assertEqual(u.root()[0],7);self.assertEqual(L.bulk_model_commands(u.f.m),commands,'Terminal root has no more IO')
  d=P/'root-output';d.mkdir(exist_ok=True)
  for name,data in output.items():(d/name).write_bytes(data)
  REPORT['full']={'native':hashlib.sha256(Path('build/setup.prg').read_bytes()).hexdigest(),'FW_native_cycles':fwcost,'PW_native_cycles':pwcost,'wall_seconds':time.monotonic()-start,'root_state':7,'private_mask':31,'created':u.created(),'files':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}for n,b in output.items()},'hardware':False}
 def test_existing_C_collision_root_failure_no_publication(self):
  u=self.make();original=b'PRESERVE EXISTING C';L.bulk_model_seed(u.f.m,b'/Home/C.IMG',original,len(original));state,_=u.root()
  self.assertEqual(state,5);self.assertNotEqual(u.call('_rc_error'),0);self.assertEqual(u.facts()[180],0);self.assertEqual(u.file(b'/Home/C.IMG',len(original)),original)
  self.assertEqual(u.call('_bc_files_closed'),1);self.assertEqual(u.call('_si_cleanup_state'),2)
  self.assertEqual(u.call('_so_publish_ticket'),0);self.assertFalse(any(n.endswith('START.PRG')or n.endswith('DOS64.CFG')for _,n in u.created()))
 def pub_collision(self,name,mask):
  u=self.make();original=b'PRESERVE EXISTING '+name.encode();L.bulk_model_seed(u.f.m,('/Home/'+name).encode(),original,len(original));u.build_disks();state,_=u.root()
  self.assertEqual(state,5);self.assertNotEqual(u.call('_rc_error'),0);self.assertEqual(u.facts()[180],mask);self.assertEqual(u.file(('/Home/'+name).encode(),len(original)),original)
  self.assertEqual(u.call('_bc_files_closed'),1);self.assertEqual(u.call('_pw_state'),3)
  if name=='START.PRG':self.assertEqual(L.bulk_model_size(u.f.m,b'/Home/DOS64.CFG'),0xffffffff)
  else:self.assertEqual(L.bulk_model_size(u.f.m,b'/Home/START.PRG'),18432)
  commands=L.bulk_model_commands(u.f.m);self.assertEqual(u.root()[0],5);self.assertEqual(L.bulk_model_commands(u.f.m),commands,'Failed root never replaces or retries')
 def test_START_collision_never_publishes_CFG(self):self.pub_collision('START.PRG',7)
 def test_CFG_collision_preserves_original_after_verified_START(self):self.pub_collision('DOS64.CFG',15)
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:],sys.modules[__name__])if len(sys.argv)>1 else unittest.defaultTestLoader.loadTestsFromTestCase(Cases)
 r=unittest.TextTestRunner(verbosity=2).run(suite);(P/os.environ.get('ROOT_FLOW_REPORT','ROOT_FLOW_RESULTS.json')).write_text(json.dumps(REPORT,indent=2)+'\n');sys.exit(not r.wasSuccessful())
