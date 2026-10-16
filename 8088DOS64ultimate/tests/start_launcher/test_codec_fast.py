import sys,os
from pathlib import Path
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.pycache_prefix=str(P/('.absent-fastcodec-'+str(os.getpid())))
assert not Path(sys.pycache_prefix).exists()
import ctypes as C,struct,zlib,json,hashlib,unittest,time
from test_actual import L,Regs
from test_controller import cfg,release_fixture,Controller
L.dos64_clear_writes.argtypes=[C.c_void_p];L.lc_check_writes.argtypes=[C.c_void_p,C.c_void_p];L.lc_check_writes.restype=C.c_uint32
REPORT={}
def sign(v):v=bytearray(v);struct.pack_into('<I',v,len(v)-4,zlib.crc32(v[:-4]));return bytes(v)
def zero_crc_patch(body,at):
 b=bytearray(body);b[at:at+4]=bytes(4);base=zlib.crc32(b);basis={}
 for i in range(32):
  c=bytearray(b);c[at+i//8]^=1<<(i%8);v=zlib.crc32(c)^base;mask=1<<i
  while v:
   k=v.bit_length()-1
   if k not in basis:basis[k]=(v,mask);break
   v^=basis[k][0];mask^=basis[k][1]
 v=base;mask=0
 while v:
  k=v.bit_length()-1;v^=basis[k][0];mask^=basis[k][1]
 b[at:at+4]=mask.to_bytes(4,'little');assert zlib.crc32(b)==0;return bytes(b)
class Codec:
 def __init__(self):
  d=P/'codec-fixtures/full-fast';self.labels={l.split()[2].lstrip('.'):int(l.split()[1],16) for l in (d/'codec.labels').read_text().splitlines() if l.startswith('al ')}
  self.m=L.dos64_create();b=(d/'codec.prg').read_bytes();L.dos64_load(self.m,0x0801,b[2:],len(b)-2);L.dos64_poke(self.m,0,0x2f);L.dos64_poke(self.m,1,0x35);self.calls=0;self.call('runtime_init')
 def at(self,n):return self.labels[n]
 def write(self,n,b):L.dos64_load(self.m,self.at(n),b,len(b))
 def read(self,n,nbytes):return bytes(L.dos64_peek(self.m,self.at(n)+i) for i in range(nbytes))
 def close(self):L.dos64_destroy(self.m)
 def call(self,n,inject=None):
  ret=self.at('fixture_return')-1;L.dos64_poke(self.m,0x1ff,ret>>8);L.dos64_poke(self.m,0x1fe,ret&255);L.dos64_set_regs(self.m,Regs(self.at(n),0xfd,0x71,0x82,0x93,0x24,0,0));L.dos64_clear_writes(self.m)
  if inject:
   r=L.dos64_run(self.m,self.at('_c32_update'),2_000_000);assert r.regs.pc==self.at('_c32_update'),('injection point',r.status,hex(r.regs.pc));self.write(inject,b'\xff\xff')
  r=L.dos64_run(self.m,self.at('fixture_return'),2_000_000);assert not r.status,(n,r.status,hex(r.regs.pc));assert self.read('sp',2)==b'\xff\xcf';assert r.stack<120
  bs=self.at('__BSS_RUN__');be=bs+self.at('__BSS_SIZE__');ze=self.at('__ZEROPAGE_RUN__')+self.at('__ZEROPAGE_SIZE__')
  mask=bytes(int(0x20<=a<ze or 0x100<=a<0x200 or bs<=a<be or 0xcd00<=a<0xd000 or 0xc900<=a<0xcd00) for a in range(65536));assert L.lc_check_writes(self.m,mask)==65536,'native bounds';self.calls+=1;return r.regs.a
class Tests(unittest.TestCase):
 def setUp(self):self.f=Codec();self.product=Controller()
 def tearDown(self):self.f.close();self.product.close()
 def check(self,f,kind,data,valid,make=False,inject=None):
  k='cfg' if kind=='config' else 'release';size=len(data);f.write('_d64_'+k+'_input',data);canary=b'\xa7'*size;f.write('_d64_'+k+'_output',canary)
  name='_d64_'+kind+('_make' if make else '_validate')
  r=f.call(name,inject=inject) if isinstance(f,Codec) else f.call(name)
  self.assertEqual(r,int(valid),(kind,make,data.hex()))
  if valid:self.assertEqual(f.read('_d64_'+k+'_output',size),sign(data) if make else data)
  else:self.assertEqual(f.read('_d64_'+k+'_output',size),canary)
 def test_exhaustive_single_byte_record_faults_full_and_product_decoder(self):
  v=cfg(b'A',b'B');_,rel=release_fixture();total=0
  for kind,data in [('config',v),('release',rel)]:
   for i in range(len(data)):
    b=bytearray(data);b[i]^=1
    for f in [self.f,self.product]:self.check(f,kind,bytes(b),False);total+=1
  REPORT['single_byte_faults']={'actual_calls':total,'output_atomic':True}
 def test_make_validate_field_capacity_matrix_and_reserved_canonicalization(self):
  total=0
  for present in range(8):
   for ro in range(8):
    for profile in range(3):
     v=bytearray(cfg(b'A',b'B'));v[525]=present;v[524]=ro;v[522]=profile
     for bit,at in [(2,264),(4,392)]:
      if not present&bit:v[at:at+128]=bytes(128)
     if not present&2:v[532:536]=bytes(4)
     v=sign(v);good=bool(present&1) and not ro&~present and profile<=1 and (bool(present&4) or profile==0)
     self.check(self.f,'config',v,good,True);self.check(self.f,'config',v,good);self.check(self.product,'config',v,good);total+=3
  for cap in [0,0x3f0000,0x400000,0x410000,0xff0000,0x1000000,0x1010000,0xffffffff,0x400001]:
   v=sign(cfg(b'A',b'B',cap));good=0x400000<=cap<=0x1000000 and cap%65536==0
   self.check(self.f,'config',v,good,True);self.check(self.product,'config',v,good);total+=2
  v=bytearray(cfg(b'A',b'B'));v[0:8]=b'x'*8;v[526:528]=b'xx';v[542:572]=b'x'*30;v[572:576]=b'x'*4
  self.f.write('_d64_cfg_input',bytes(v));self.assertEqual(self.f.call('_d64_config_make'),1);made=self.f.read('_d64_cfg_output',576);self.assertEqual(made,cfg(b'A',b'B'));self.check(self.product,'config',made,True)
  REPORT['field_matrix']={'actual_calls':total+2,'make_reserved_bytes_zeroed':True}
 def test_signed_semantic_faults_and_path_aliases(self):
  faults=[];base=cfg(b'A',b'B')
  for at,value in [(7,1),(526,1),(527,1),(542,1),(571,1),(520,1),(521,1),(523,1),(525,0x87),(524,0x87),(536,2),(537,1)]:
   v=bytearray(base);v[at]=value;faults.append(sign(v))
  for name in [b'/usb1//bad',b'/usb1/../x',b'/usb1/a.',b'/usb1/a ',b'/usb1/a\\b',b'/usb1/\x80bad',b'',b'/usb1/'+b'x'*122]:
   v=bytearray(base);v[8:136]=name.ljust(128,b'\0')[:128];faults.append(sign(v))
  for v in faults:self.check(self.f,'config',v,False);self.check(self.product,'config',v,False)
  _,rel=release_fixture();rs=[]
  for at,fmt,val in [(16,'H',0x0802),(26,'H',0x5883),(40,'I',0x3e0001),(44,'I',0x3ff001),(48,'H',575),(56,'I',1),(8,'I',0xb802),(20,'H',0x4000),(28,'I',1),(32,'I',int.from_bytes(rel[28:32],'little'))]:
   v=bytearray(rel);struct.pack_into('<'+fmt,v,at,val);rs.append(sign(v))
  for v in rs:self.check(self.f,'release',v,False);self.check(self.product,'release',v,False)
  REPORT['signed_semantic_faults']={'config':len(faults),'release':len(rs),'both_native_builds':True}
 def test_legitimate_CRC_zero_and_pointer_count_failure_not_success(self):
  _,rel=release_fixture();r=zero_crc_patch(rel[:60],12)+bytes(4);self.check(self.f,'release',r,True);self.check(self.product,'release',r,True)
  v=bytearray(cfg(b'A',b'B'));v[8:136]=b'/usb1/CRC-zero-prefix-0000-END'.ljust(128,b'\0');legal=set(range(0x21,0x7f))-set(b'\\:"*<>?|/')
  for n in range(100000):
   v[14:18]=('%04X'%n).encode()[-4:];b=zero_crc_patch(v[:572],29)
   if all(c in legal for c in b[29:33]):v=b+bytes(4);break
  else:raise AssertionError('bounded canonical CRC0 fixture search')
  self.check(self.f,'config',v,True);self.check(self.f,'config',v,True,True);self.check(self.product,'config',v,True)
  for kind,data in [('config',v),('release',r)]:
   for injected in ['_c32_address','_c32_length']:
    self.check(self.f,kind,data,False,inject=injected);self.assertEqual(self.f.read('_d64_'+('cfg' if kind=='config' else 'release')+'_error',1),b'\x02')
  self.check(self.f,'config',v,False,True,inject='_c32_length')
  REPORT['CRC_zero']={'config_sha256':hashlib.sha256(v).hexdigest(),'release_sha256':hashlib.sha256(r).hexdigest(),'valid_full_make_decoder_and_product_decoder':True,'actual_midcall_pointer_count_injections':5,'failed_CRC_zero_not_accepted':True}
if __name__=='__main__':
 t=time.monotonic();r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));REPORT['elapsed_seconds']=time.monotonic()-t;(P.parent/'CODEC_FAST_RESULTS.json').write_text(json.dumps(REPORT,indent=2)+'\n');sys.exit(not r.wasSuccessful())
