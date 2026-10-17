from pathlib import Path
import sys,os
W=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(W/('.absent-policy-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import unittest,types,json,zlib
from product_transport import ProductREST
from preserved_product import PreservedProduct
from model_api import contract
class Policy(unittest.TestCase):
 def wire(self):
  w=object.__new__(ProductREST);w.product=types.SimpleNamespace(observer=contract);w.role='product';w.mode='product_native';w._product_permit=None;w.product_load_attempted=False;w.product_fields=set();w.product_terminal=None;w.stager=types.SimpleNamespace(home=b'/usb1/DOS64_TEST/test');w.calls=[];w.fail=None
  def exchange(m,r,e,count=None):
   w._allowed(m,r,None);w.calls.append((m,r,count))
   if w.fail:raise w.fail
   if m=='GET':return bytes(count)
   if 'writemem'in r:
    a=int(r.split('address=')[1].split('&')[0],16);n=len(r.split('data=')[1])//2;return {'errors':[],'address':'%04X-%04X'%(a,a+n-1)}
   return {'errors':[]}
  w._exchange=exchange;return w
 def test_request_whitelist_exact_source_read_and_owner(self):
  w=self.wire();o=w.product
  for m,r,n in [('GET','machine:readmem?address=0&length=65536',65536),('GET',f"machine:readmem?address={contract.p('coordinator','state'):X}&length=12",12),('PUT','machine:pause',None),('PUT','machine:resume',None)]:w.product_exchange(o,m,r,100,n)
  for m,r,n in [('PUT','machine:reset',None),('GET','machine:readmem?address=DF00&length=1',1),('PUT','machine:writemem?address=C6&data=01',None),('POST','machine:writemem?address=801',None),('PUT','runners:load_prg?file=OTHER',None)]:
   with self.assertRaises(ValueError):w.product_exchange(o,m,r,100,n)
  with self.assertRaises(ValueError):w.product_exchange(object(),'PUT','machine:pause',100)
  self.assertEqual(len(w.calls),4)
 def test_ambiguous_LOAD_and_SYS_are_attempted_once(self):
  from urllib.parse import quote
  w=self.wire();err=ConnectionResetError(54,'ambiguous');w.fail=err;r='runners:load_prg?file='+quote(w.stager.home.decode()+'/SETUP.PRG',safe='')
  with self.assertRaises(ConnectionResetError)as e:w.product_exchange(w.product,'PUT',r,100)
  self.assertIs(e.exception,err)
  with self.assertRaises(ValueError):w.product_exchange(w.product,'PUT',r,100)
  with self.assertRaises(ValueError):w.product_field(w.product,0xc6,b'\x08',100,'count')
  with self.assertRaises(ConnectionResetError):w.product_field(w.product,0x277,b'SYS2061\r',100,'body')
  with self.assertRaises(ValueError):w.product_field(w.product,0x277,b'SYS2061\r',100,'body')
  self.assertIsNone(w._product_permit);self.assertEqual(len(w.calls),2)
 def test_exact_body_count_and_terminal_source_gate(self):
  w=self.wire();w.product_field(w.product,0x277,b'SYS2061\r',100,'body');w.product_field(w.product,0xc6,b'\x08',100,'count')
  with self.assertRaises(ValueError):w.product_field(w.product,0xc6,b'\x08',100,'count')
  raw=(W.parent/'ACTUAL_PRODUCT_TERMINAL.bin').read_bytes();proof=w.accept_product_terminal(raw);self.assertTrue(proof['known_closed_quiet'])
  b=bytearray(raw);b[contract.at('dos64_files_handle')]=2
  with self.assertRaises(ValueError):w.accept_product_terminal(bytes(b))
class Cleanup(unittest.TestCase):
 def make(self):
  base=(W/'BASELINE.reu').read_bytes();service=(W/'service.prg').read_bytes();raw=bytearray(65536);raw[0x801:0x801+len(service)-2]=service[2:]
  for a,v in [(0x12b9,0xc101),(0x135f,0xc67f)]:raw[a:a+2]=v.to_bytes(2,'little')
  q=memoryview(raw)[0x6000:0x6020];q[:4]=b'DRF1';q[4]=0xa5;q[7]=6;crc=(zlib.crc32(base)&0xffffffff).to_bytes(4,'little');q[16:20]=crc;q[20:24]=crc;q[28:30]=b'\0\x20'
  # Explicit host receipt fixture, not a new native execution.
  ready=bytearray(65536);ready[0x288:0x28a]=b'\4\x0a';ready[0xd6]=5;ready[0xd1:0xd3]=(0x4c8).to_bytes(2,'little');ready[0x4a0:0x4c8]=bytes([18,5,1,4,25,46])+b' '*34;ready[0x4c8:0x4f0]=b' '*40;a=bytes(ready);ready[0xa2]=1;b=bytes(ready)
  original={'settings':{'original':True}};calls=[];machine=PreservedProduct(base,service,None,terminal_validator=lambda ram:dict(contract.terminal(ram),known_closed=True),clock=lambda:0,cleanup_clock=lambda:0)
  def call(n,v):
   def f(*args):calls.append((n,args));return v
   return f
  cb=dict(originals=call('originals',(bytes(65536),original)),set_temporary=call('temporary',{'Turbo Control':'Manual','CPU Speed':'64','System Mode':'PAL'}),snapshot=lambda role,end:(calls.append(('snapshot',role))or base),stage=call('stage',None),terminal_RAM=call('terminal',(W.parent/'ACTUAL_PRODUCT_TERMINAL.bin').read_bytes()),restore=call('restore',bytes(raw)),basic_cleanup=call('basic',(a,b,{'errors':[]})),profile_restore=call('profile',original),retain=lambda *a:None)
  return machine,calls,cb
 def test_terminal_callback_full_cleanup_receipt(self):
  m,c,k=self.make();r=m.run(**k);self.assertEqual(r['status'],'passed');self.assertTrue(r['facts']['original4MiB_verified']);self.assertEqual(m.calls['native_restore'],1);self.assertTrue(r['facts']['BASIC_reset_allowed'])
 def test_unknown_terminal_blocks_restore_reset_but_profile_finally(self):
  m,c,k=self.make();raw=bytearray(k['terminal_RAM'](600));raw[contract.at('dos64_files_handle')]=2;k['terminal_RAM']=lambda end:bytes(raw)
  with self.assertRaises(ValueError):m.run(**k)
  self.assertNotIn('native_restore',m.calls);self.assertFalse(next(args for name,args in c if name=='basic')[0]);self.assertEqual(sum(name=='profile'for name,args in c),1)
 def test_firstcause_preserved_with_later_terminal_and_cleanup_faults(self):
  m,c,k=self.make();first=ConnectionResetError(54,'first');k['stage']=lambda end:(_ for _ in()).throw(first);k['terminal_RAM']=lambda end:(_ for _ in()).throw(RuntimeError('unknown terminal'));k['basic_cleanup']=lambda *a:(_ for _ in()).throw(KeyboardInterrupt())
  with self.assertRaises(ConnectionResetError)as e:m.run(**k)
  self.assertIs(e.exception,first);self.assertEqual(sum(name=='profile'for name,args in c),1);self.assertNotIn('native_restore',m.calls)
 def test_original_endpoint_not_renewed_and_profile_independent_of_clock(self):
  m,c,k=self.make();ticks=[0];m.clock=lambda:ticks[0];k['stage']=lambda end:ticks.__setitem__(0,601)
  with self.assertRaises(TimeoutError):m.run(**k)
  self.assertNotIn('native_restore',m.calls);self.assertEqual(sum(name=='profile'for name,args in c),1);self.assertEqual(m.end,600)
if __name__=='__main__':unittest.main(verbosity=2)
