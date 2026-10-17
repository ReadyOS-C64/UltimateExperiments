from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.pycache_prefix=str(P.parent/'.absent-combined-errors');assert not Path(sys.pycache_prefix).exists()
import unittest,ctypes as C,struct,zlib,json
from config_fixture import F,L,Regs,cfg
L.dos64_step.argtypes=[C.c_void_p];L.dos64_reu_poke.argtypes=[C.c_void_p,C.c_uint32,C.c_uint8]
class Native:
 def __init__(self,data=None,badclose=False):
  self.f=F(auto=False);f=self.f;L.dir_model_path(f.m,b'/');L.dir_model_path(f.m,b'/Existing');L.dir_model_row(f.m,b'/',16,b'Existing',8)
  if data is not None:L.bulk_model_seed(f.m,b'/Existing/DOS64.CFG',data,len(data))
  first=bytearray(f.guard)
  for start,count in [(f.labels['__CONFIG_HIGH_RUN__'],f.labels['__CONFIG_HIGH_TOTAL__']),(f.labels['__FD_SAFE_RUN__'],f.labels['__FD_SAFE_SIZE__'])]:first[start:start+count]=bytes([1])*count
  self.firstguard=bytes(first);self.safe=f.labels['__FD_SAFE_RUN__'];n=f.labels['__FD_SAFE_SIZE__'];raw=Path('config.prg').read_bytes();at=f.labels['__FD_SAFE_LOAD__']-0x801+2;self.safe_bytes=raw[at:at+n]
  L.dos64_poke(f.m,0,0x2f);L.dos64_poke(f.m,1,0x37);L.dos64_set_regs(f.m,Regs(0x80d,0xfd,0,0,0,0x2c,0,0));self.run(self.firstguard)
  self.badclose=badclose
 def close(self):self.f.close()
 def run(self,guard=None):
  f=self.f;L.dos64_clear_writes(f.m);r=L.dos64_run(f.m,f.labels['config_poll_return'],50000000)
  if f.labels['fd_park']<=r.regs.pc<f.labels['fd_park']+3:self.terminal='normal'
  elif self.safe<=r.regs.pc<self.safe+len(self.safe_bytes):self.terminal='fallback'
  else:
   assert r.status in[0,2]and r.regs.pc==f.labels['config_poll_return'],(r.status,hex(r.regs.pc));self.terminal=None
  allowed=bytearray(f.guard if guard is None else guard)
  if self.terminal:
   at=f.labels['__FD_CODE_RUN__'];n=f.labels['__FD_CODE_SIZE__'];allowed[at:at+n]=bytes([1])*n
  assert L.browser_bad_write(f.m,bytes(allowed))==65536,hex(L.browser_bad_write(f.m,bytes(allowed)))
  assert f.read('sp',2)==b'\xff\xcf';return self.terminal
 def poll(self):
  L.dos64_step(self.f.m);L.dos64_cia_clock_advance(self.f.m,1024);return self.run()
 def wait(self):
  for _ in range(4000):
   if self.poll():return
   r=self.f.read('_cg_result',8)
   if r[0]not in[1,3]and not(r[0]==2 and self.f.read('_db_result',1)==b'\1'):return
  raise AssertionError('boundedwait')
 def key(self,row,col):
  k=bytearray(8);k[row]=1<<col;L.dos64_host_input_model_keys(self.f.m,bytes(k));self.poll();L.dos64_host_input_model_keys(self.f.m,bytes(8))
  if not self.terminal:self.poll()
 def inspect(self):
  self.wait();self.key(0,1);self.wait()
  if self.badclose:L.bulk_model_faults(self.f.m,L.bulk_model_commands(self.f.m)+3,-1,-1,0,-1)
  self.key(0,4)
  for _ in range(4000):
   if self.terminal:return
   self.poll()
  raise AssertionError('boundedterminal')
 def final(self,code,op,closed):
  f=self.f;assert self.terminal=='normal';assert f.read('_fd_code',1)==bytes([code]);assert f.read('_fd_op',1)==bytes([op]);assert f.read('_fd_closed',1)==bytes([closed]);assert f.read('_fd_path',128)==b'/Existing/DOS64.CFG'.ljust(128,b'\0')
  n=L.bulk_model_commands(f.m);L.dos64_run(f.m,0x2f0,50000);assert L.bulk_model_commands(f.m)==n
  assert bytes(L.dos64_peek(f.m,self.safe+i)for i in range(len(self.safe_bytes)))==self.safe_bytes
class Errors(unittest.TestCase):
 def make(self,**kw):s=Native(**kw);self.addCleanup(s.close);return s
 def test_actual_SYS_CIA_missing_CFG_full_path_and_no_retry(self):s=self.make();s.inspect();s.final(2,1,1)
 def test_actual_SYS_short_INFO_before_failed_CLOSE_keeps_first_path_and_unknown(self):
  s=self.make(data=b'BAD',badclose=True);s.inspect();s.final(3,2,0);self.assertEqual(L.bulk_model_open(s.f.m,1),1)
 def test_actual_SYS_bad_CFG_semantic_error_without_publication(self):
  b=bytearray(cfg(b'/Existing'));b[0]^=1;s=self.make(data=bytes(b));s.inspect();s.final(4,0,1);self.assertFalse(any(x[1]in[0x05,0x22]for x in s.f.commands()))
 def test_actual_SYS_corrupted_terminal_REU_uses_verified_permanent_fallback(self):
  s=self.make();f=s.f;L.dos64_reu_poke(f.m,0xa0000,0);L.dos64_host_input_model_keys(f.m,bytes(7)+b'\x80')
  for _ in range(1000):
   if s.poll():break
  self.assertEqual(s.terminal,'fallback');self.assertEqual(f.read('_fd_code',1),b'\5');self.assertEqual(bytes(L.dos64_peek(f.m,s.safe+i)for i in range(len(s.safe_bytes))),s.safe_bytes)
  self.assertEqual(bytes(L.dos64_peek(f.m,0x400+i)for i in range(10)),bytes([3,15,14,6,9,7,46,16,18,7]))
if __name__=='__main__':
 r=unittest.main(exit=False).result;(P.parent/'COMBINED_ERRORS_REPORT.json').write_text(json.dumps({'tests':r.testsRun,'passed':r.wasSuccessful()},indent=2)+'\n');sys.exit(not r.wasSuccessful())
