"""Separately typed live-MAIN close executor; NOT admitted by BASIC-only purpose.
Uses the same numeric HTTP engine and PUT128 source uploader, no second engine.
Caller must already have a complete original4MiB retention and cache-flushed
coherently paused actual current MAIN. No public positive observation grants it.
"""
import time,re,hashlib
from protocol import sha
from stage_transport import StageREST,StageClient
from rest_io import Intersection
from put_io import PutIO
from close_contract import Contract,configure,result
from takeover import MainTakeover
from basic_ready import basic_ready

class CloseSource:
 def __init__(self,configured,labels):self.configured=configured;self.body=configured[2:];self.low=0x801;self.high=self.low+len(self.body);self.labels=labels
 def verify(self,b,cold=False):
  if b!=self.body:raise ValueError('Exact unstarted close helper source')

class ClosePutIO(PutIO):
 def startup_write(self,a,b):
  if not self.paused or(a,b)not in [(0x6000,bytes(48)),(0x277,b'SYS2061\r'),(0xc6,b'\x08')]:raise ValueError('Exact close sentinel/SYS fields')
  return self._span(a,b,'close_sentinel'if a==0x6000 else'close_SYS')
 def write(self,*a):raise ValueError('No stager/REU command in close executor')

class TakeoverREST(StageREST):
 """Only a separate reviewed live-MAIN purpose may construct this derivative."""
 def __init__(self,*a,**kw):super().__init__(*a,**kw);self.close_io=None;self._close_permit=None;self.close_attempted=False;self.close_known=False
 def _allowed(self,m,r,body):
  if self._close_permit is not None:
   if self.role!='close'or(m,r,body)!=self._close_permit:raise ValueError('One close transport owner')
   return
  return super()._allowed(m,r,body)
 def begin_close(self,io):
  if self.mode!='activate'or self.close_attempted or self.stage_io is not None:raise ValueError('Live close must precede all source replacement')
  self.close_attempted=True;self.close_io=io;self.role='close';self.mode='close_cold';self.source=io.source.configured
 def stage_exchange(self,io,m,r,end,count=None):
  if io is not self.close_io:return super().stage_exchange(io,m,r,end,count)
  if self.role!='close'or self._close_permit is not None:raise ValueError('Exclusive close owner')
  allowed=m=='PUT'and r in ['machine:pause','machine:resume','machine:reset']
  q=re.fullmatch(r'machine:readmem\?address=([0-9A-F]+)&length=([0-9]+)',r)if m=='GET'else None
  if q:allowed=0<=int(q[1],16)<65536 and 1<=int(q[2])<=65536-int(q[1],16)and count==int(q[2])
  if m=='PUT'and r.startswith('machine:writemem?'):allowed=io._permit==(m,r)
  if not allowed:raise ValueError('Only typed close IO')
  if r=='machine:reset':
   if self.reset_uncertain:raise ValueError('No reset retry')
   self._once('close_reset')
  self._close_permit=(m,r,None)
  try:return self._exchange(m,r,end,count)
  except BaseException:
   if r=='machine:reset':self.reset_uncertain=True
   raise
  finally:self._close_permit=None

class KnownCloseBackend:
 def __init__(self,wire,*,main,labels,map_text,C_path,base,close_labels,nonce,retained4M,save,clock=time.monotonic,sleep=time.sleep):
  if type(wire)is not TakeoverREST or sha(retained4M)!='ac43c06b5e23774b298011c1a97bfbc72eb8395020465c747b135a83e9cd3eb3'or len(retained4M)!=4194304:raise ValueError('Separate source-bound close capability and prior full baseline')
  self.wire=wire;self.main=main;self.labels=labels;self.map=map_text;self.path=C_path;self.base=base;self.close_labels=close_labels;self.nonce=nonce;self.save=save;self.clock=clock;self.sleep=sleep;self.takeover=MainTakeover(base,close_labels,clock=clock);self.io=None;self.events=[]
 def execute(self,deadline):
  self.wire.control('pause','live_MAIN_pause',deadline);raw=self.wire.ram('live_MAIN_fresh_RAM',deadline);self.save('live_MAIN_before_close.bin',raw)
  # Contract.admit insists on actual cache-flushed stage5, current source/path,
  # empty command/UCI and known open C; BASIC or injected stage-only flags fail.
  return self.takeover.close(raw,self.main,self.labels,self.map,self.path,self.nonce,self._execute,deadline)
 def _execute(self,configured,labels,nonce,end):
  source=CloseSource(configured,labels);client=StageClient(self.wire,Intersection(self.clock,end,None));index=[0]
  def record(row):index[0]+=1;self.save('close-HTTP-plan-%06d.json'%index[0],(__import__('json').dumps(row)+'\n').encode())
  io=ClosePutIO(client,source,clock=self.clock,seconds=max(1,min(600,end-self.clock())),record=record);client.io=io;self.io=io;self.wire.begin_close(io)
  def read():
   io.bound_until(end);raw=io.read(0,65536)
   if self.clock()>=end:raise TimeoutError('Original known-C close endpoint')
   return raw
  def put(a,b):
   io.startup_write(a,b)
   if io.read(a,len(b))!=b:raise ValueError('Close startup exact write readback')
  try:
   io.reset();previous=None
   for _ in range(64):
    io.pause();ram=read();v=basic_ready(ram)
    if v is not None and previous is not None and v['jiffy']!=previous['jiffy']:break
    previous=v;io.resume();self.sleep(min(.02,max(0,end-self.clock())))
   else:raise TimeoutError('Close cold BASIC readiness')
   io.load_prg(configured);ram=read();source.verify(ram[source.low:source.high],cold=True)
   # The inherited source loader's15s endpoint can only tighten the parent.
   end=min(end,io.budget.deadline);put(0x6000,bytes(48));put(0x277,b'SYS2061\r');put(0xc6,b'\x08');ram=read()
   if ram[0xc6]!=8 or ram[0x277:0x27f]!=b'SYS2061\r'or ram[0x6000:0x6030]!=bytes(48):raise ValueError('Exact cold close source/sentinel/count-last')
   source.verify(ram[source.low:source.high],cold=True);self.save('close-cold-queued.bin',ram);io.resume()
   for _ in range(65535):
    b=io.read(0x6000,48)
    if self.clock()>=end:raise TimeoutError('Bounded close native terminal')
    if b[:4]==b'DCC1'and b[4]in[0xa5,0xe1]:break
    self.sleep(min(.01,max(0,end-self.clock())))
   else:raise TimeoutError('Finite close observations')
   io.pause();terminal=read();self.save('close-terminal.bin',terminal);result(terminal,configured,labels,nonce);self.wire.close_known=True
   # Only actual raw terminal acceptance permits subsequent source replacement.
   self.wire.mode='activate';self.wire.role=None;return terminal
  finally:io.restore_budget()
