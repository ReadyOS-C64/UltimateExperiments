"""Explicit stager-only load-only + source-bound SYS2061 startup.
No implicit IO or mutation on import. Caller already captured RAM/settings/REU.
"""
import time
from basic_ready import basic_ready
from protocol import sha
class Startup:
 def __init__(self,io,source,*,clock=time.monotonic,event=lambda *a,**k:None):self.io=io;self.source=source;self.clock=clock;self.event=event;self.load_attempted=False;self.resume_attempted=False;self.go_attempted=False;self.withdraw_attempted=False;self.first=None
 def bound(self,end):
  if self.clock()>=end:raise TimeoutError('Bounded stager-only load/SYS startup; no fallback/retry')
 def read(self,a,n,end):
  self.bound(end);v=self.io.read(a,n);self.bound(end)
  if not isinstance(v,bytes)or len(v)!=n:raise ValueError('Full exact startup memory read')
  return v
 def ack(self,value):
  if not isinstance(value,dict)or value.get('errors')!=[]:raise ValueError('Exact errors=[] acknowledgement required')
 def write(self,a,b,end):
  self.bound(end);self.ack(self.io.startup_write(a,b));self.bound(end)
  if self.read(a,len(b),end)!=b:raise ValueError('Exact startup write readback required')
 def loaded(self,end):
  ram=self.read(0,65536,end);self.source.verify(ram[self.source.low:self.source.high],cold=True)
  if ram[0x2a0:0x2e0]!=bytes(64):raise ValueError('Stager load must remain unstarted sentinel zero')
  return ram
 def withdraw(self):
  if not self.go_attempted or self.resume_attempted or self.withdraw_attempted:return
  self.withdraw_attempted=True;end=self.clock()+30
  if hasattr(self.io,'bound_until'):self.io.bound_until(end)
  self.io.pause();ram=self.loaded(end);body=b'SYS2061\r'
  if ram[0x277:0x27f]!=body or ram[0xc6]not in[0,8]:raise ValueError('Ambiguous keyboard ownership; no overwrite')
  if ram[0xc6]:self.write(0xc6,b'\0',end)
 def start(self):
  end=self.clock()+30
  if hasattr(self.io,'bound_until'):self.io.bound_until(end)
  try:
   self.ack(self.io.reset());self.bound(end);self.io.pause();self.write(0x2a0,bytes(64),end)
   self.event('before_exact_stager_PUT_load',sha256=sha(self.source.configured));self.load_attempted=True
   self.ack(self.io.load_prg(self.source.configured));self.bound(end);self.io.pause();self.loaded(end)
   previous=None
   while True:
    self.io.resume();self.bound(end);self.io.pause();ram=self.loaded(end);ready=basic_ready(ram)
    if ready is not None and previous is not None and ready['jiffy']!=previous['jiffy']:break
    previous=ready
   self.write(0x277,b'SYS2061\r',end)
   self.event('before_owned_SYS_count_last');self.go_attempted=True;self.write(0xc6,b'\x08',end)
   self.event('before_owned_SYS_resume');self.resume_attempted=True;self.io.resume();self.bound(end)
   while True:
    r=self.read(0x2a0,64,end)
    if r[:4]==b'AST1':
     if r[4]==0xff:raise RuntimeError('Native startup first error%d'%r[8])
     if r[4]in[0x11,0xa5]:
      self.io.pause();self.source.verify(self.read(self.source.low,len(self.source.body),end));r=self.read(0x2a0,64,end)
      if r[:4]!=b'AST1'or r[4]not in[0x11,0xa5]or r[6:10]!=b'\0\0\0\3'or r[30:34]!=bytes(4)or r[34]!=9 or r[35]:raise ValueError('Native startup both targets knownclosed/quiet/no error required')
      return {'load_only_source_exact':True,'unstarted_sentinel':True,'two_READY_jiffies':True,'SYS2061_body_count_last':True,'resume_attempts':1,'startup_CLOSE1_2':True,'private_RTI_source':self.source.at('ps_rti')}
  except BaseException as e:
   if self.first is None:self.first=e
   try:self.withdraw()
   except BaseException as cleanup:e.stager_SYS_withdraw_error=repr(cleanup)
   raise
