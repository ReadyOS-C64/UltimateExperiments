from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-product-tests-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import json,hashlib,unittest,ctypes as C,socket
socket.socket.connect=lambda *a,**k:(_ for _ in ()).throw(AssertionError('NoLAN'))
from model_api import M,L,Regs,contract
from stage_model import Clock
from protocol import Source
from bound_release import BoundRelease,Release16Protocol,NAMES
from product import Product
from product_transport import ProductREST
L.dos64_host_input_model_keys.argtypes=[C.c_void_p,C.c_void_p]
L.dir_model_enable.argtypes=[C.c_void_p];L.dir_model_path.argtypes=[C.c_void_p,C.c_char_p]
class FixtureWire:
 def __init__(self,m,clock,fault=None):self.m=m;self.clock=clock;self.owner=None;self.native=False;self.calls=[];self.fields=[];self.fault=fault;self.error=ConnectionResetError(54,'ambiguous product');self.stopped=False;self.human_stop=True
 def begin_product(self,owner,raw):self.owner=owner
 def advance(self):
  if not self.native:return
  for i in range(40):
   L.dos64_step(self.m.m);L.dos64_cia_clock_advance(self.m.m,1024);v=L.dos64_run(self.m.m,contract.at('setup_loop'),40000000);
   if v.status==3 and v.regs.pc==contract.at('bd_park') and L.dos64_peek(self.m.m,contract.p('coordinator','state'))==5:return
   assert v.status in[0,2],(v.status,hex(v.regs.pc))
   state=L.dos64_peek(self.m.m,contract.p('coordinator','state'))
   if state in[2,5,7]:break
 def product_exchange(self,owner,m,r,end,count=None):
  assert owner is self.owner and self.clock()<end;self.calls.append((m,r));self.clock.t+=.001
  if self.fault=='LOAD'and'load_prg'in r:raise self.error
  if m=='PUT'and r=='machine:resume':
   if not self.native and L.dos64_peek(self.m.m,0xc6)==8:
    self.native=True;L.dos64_poke(self.m.m,0xc6,0);L.dos64_set_regs(self.m.m,Regs(0x80d,0xfd,0,0,0,0x24,0,0))
   if self.native and owner.report.get('postentry')and not self.stopped and self.human_stop:
    L.dos64_host_input_model_keys(self.m.m,bytes([0,0,0,0,0,0,0,128]));self.stopped=True
   self.advance()
  if m=='GET':
   if not self.native:
    j=L.dos64_peek(self.m.m,0xa2)+1;L.dos64_poke(self.m.m,0xa2,j&255)
   else:self.advance()
   q=dict(x.split('=')for x in r.split('?')[1].split('&'));a=int(q['address'],16);n=int(q['length']);return bytes(L.dos64_peek(self.m.m,a+i)for i in range(n))
  return {'errors':[]}
 def product_field(self,owner,a,b,end,key):
  self.fields.append((a,b,key));L.dos64_load(self.m.m,a,b,len(b))
  if self.fault==key:raise self.error
class Tests(unittest.TestCase):
 def fixture(self,fault=None):
  c=Clock();r=(P/'STAGING_INVENTORY.json').read_bytes();release=BoundRelease(r,hashlib.sha256(r).hexdigest(),{n:(P/'assets'/n).read_bytes()for n in NAMES});source=Source((P/'stager.prg').read_bytes(),(P/'stager.labels').read_text(),b'/usb1/DOS64_TEST/v1-ui-model');assets=release.assets(source.home,b'2'*16);p=Release16Protocol(None,source,clock=c);p.sequence=380;p.records=[{'op':0}for _ in range(379)]
  terminal=bytearray(65536);terminal[source.low:source.high]=source.body
  for a,v in source.port_words.items():terminal[a:a+2]=v.to_bytes(2,'little')
  for a in source.dynamic:terminal[a:a+2]=b'\xff\xff'
  q=memoryview(terminal)[0x2a0:0x2e0];q[:4]=b'AST1';q[4]=0xa5;q[6:8]=(380).to_bytes(2,'little');q[9]=3;q[32]=1;q[34]=9;p.records.append({'op':10,'result':bytes(q).hex()})
  m=M();self.addCleanup(m.close);L.dir_model_enable(m.m);L.dir_model_path(m.m,b'/');ram=bytearray(m.ram());ram[0x288]=4;ram[0x289]=10;ram[0xd6]=5;ram[0xd3]=0;ram[0xd1:0xd3]=(0x400+200).to_bytes(2,'little');ram[0x4a0:0x4c8]=bytes([18,5,1,4,25,46])+b' '*34;ram[0x4c8:0x4f0]=b' '*40;
  for a,n in [(0xa0,3),(0xc6,1),(0xd1,3),(0xd6,1),(0x288,2),(0x4a0,80)]:L.dos64_load(m.m,a,bytes(ram[a:a+n]),n)
  w=FixtureWire(m,c,fault);saved={};product=Product(w,p,release,assets,contract,save=lambda n,b:saved.__setitem__(n,b),clock=c,sleep=c.sleep);return product,c,w,m,bytes(terminal),saved
 def test_actual_native_SYS_to_physical_matrix_STOP_terminal(self):
  p,c,w,m,t,saved=self.fixture();r=p.run(t,600);self.assertEqual(r['terminal']['outcome'],'STOPPED_NATIVE_UI');self.assertEqual(r['terminal']['native_first_error'],0x13);self.assertEqual([x[2]for x in w.fields],['body','count']);self.assertEqual(sum('load_prg'in route for meth,route in w.calls),1);self.assertFalse(r['human_CIA_input_synthesized'])
  # Human behavior is represented only by actual CIA matrix in this LOCAL model.
  (P.parent/'ACTUAL_PRODUCT.json').write_text(json.dumps({'status':'LOCAL_NATIVE_ENTRY_AND_CIA_STOP_PASS','transport_BASIC_registeredLOAD':'mocked, not firmware','native_SYS_bankguard_UI_source_and_STOP':'actual Peddle/e710','report':r,'CIA_model_only':True,'physical':False},indent=2)+'\n');(P.parent/'ACTUAL_PRODUCT_TERMINAL.bin').write_bytes(p.terminal_raw);(P.parent/'ACTUAL_PRODUCT_ADMISSION.bin').write_bytes(saved['product-admitted-RAM.bin'])
 def test_ambiguous_registeredLOAD_noSYS_or_reissue(self):
  p,c,w,m,t,s=self.fixture('LOAD')
  with self.assertRaises(ConnectionResetError)as e:p.run(t,600)
  self.assertIs(e.exception,w.error);self.assertEqual(w.fields,[]);self.assertFalse(p.resume_attempted)
  with self.assertRaises(ValueError):p.run(t,600)
 def test_ambiguous_body_or_count_never_resumes_native(self):
  for key in['body','count']:
   p,c,w,m,t,s=self.fixture(key)
   with self.assertRaises(ConnectionResetError)as e:p.run(t,600)
   self.assertIs(e.exception,w.error);self.assertFalse(p.resume_attempted);self.assertFalse(w.native)
 def test_human_cancel_and_window_timeout_do_not_emit_STOP_or_reset(self):
  for case in ['cancel','deadline']:
   p,c,w,m,t,s=self.fixture();w.human_stop=False
   if case=='cancel':p.cancel=lambda:True
   else:
    old=p.sleep
    def sleep(n):
     if p.report.get('postentry'):c.t+=121
     else:old(n)
    p.sleep=sleep
   with self.assertRaises(KeyboardInterrupt if case=='cancel'else TimeoutError):p.run(t,600)
   self.assertFalse(w.stopped);self.assertIsNone(p.terminal_raw);self.assertTrue(p.report['SYS_resume_attempted']);self.assertFalse(any('reset'in route for meth,route in w.calls))
   with self.assertRaises(ValueError):contract.terminal(m.ram())
 def test_private_unknown_handle_blocks_terminal_and_reset(self):
  p,c,w,m,t,s=self.fixture();p.run(t,600);b=bytearray(p.terminal_raw);b[contract.at('dos64_files_handle')]=2
  with self.assertRaises(ValueError):contract.terminal(bytes(b))
 def test_source_mismatch_and_public_terminal_forgery_refused(self):
  p,c,w,m,t,s=self.fixture();p.run(t,600)
  for a in [contract.at('setup_boot'),contract.p('coordinator','failure_closed'),contract.p('startup_close','sc_private')+4]:
   b=bytearray(p.terminal_raw);b[a]^=1
   with self.assertRaises(ValueError):contract.terminal(bytes(b))
if __name__=='__main__':unittest.main(verbosity=2)
