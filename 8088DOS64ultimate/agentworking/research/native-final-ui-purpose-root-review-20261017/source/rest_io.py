"""Strict REST-only development transport. Inject a frozen DeadlineClient.
No FTP, persistent REST-file route, run_prg, retry, or IO on construction/import.
"""
import time
class Intersection:
 def __init__(self,clock,end,parent):self.clock=clock;self.deadline=end;self.parent=parent
 def remaining(self):
  n=self.deadline-self.clock()
  if self.parent is not None:n=min(n,self.parent.remaining())
  if n<=0:raise TimeoutError('Native stager request/whole deadline exhausted')
  return n
class RestIO:
 def __init__(self,client,source,*,clock=time.monotonic,seconds=600,event=lambda *a,**k:None):
  if not 1<=seconds<=600 or not hasattr(client,'budget'):raise ValueError('Frozen bounded client and finite whole phase required')
  self.client=client;self.source=source;self.clock=clock;self.event=event;self.whole=clock()+seconds;self.parent=client.budget;self.budget=Intersection(clock,self.whole,self.parent);self.client.budget=self.budget;self.paused=False;self.loaded=False;self.closed=False
 def bound_until(self,end):self.budget.deadline=min(self.whole,end)
 def restore_budget(self):self.client.budget=self.parent;self.closed=True
 def request(self,method,route,data=None):
  if self.closed:raise ValueError('Transport context ended')
  self.budget.remaining();self.event('before_REST',method=method,route=route,bytes=len(data)if data is not None else 0)
  try:
   value=self.client.request(method,route,data,'application/octet-stream'if data is not None else None);self.budget.remaining()
   return value
  except BaseException as e:
   e.stager_REST={'method':method,'route':route,'bytes':len(data)if data is not None else 0,'retries':0};raise
 def ack(self,v):
  if not isinstance(v,dict)or v.get('errors')!=[]:raise ValueError('Exact errors=[] REST acknowledgement required')
  return v
 def pause(self):
  self.paused=False # no authority until exact pause acknowledgement
  v=self.ack(self.request('PUT','machine:pause'));self.paused=True;return v
 def resume(self):
  self.paused=False # ambiguous resume may already have started execution
  return self.ack(self.request('PUT','machine:resume'))
 def reset(self):
  self.paused=False
  return self.ack(self.request('PUT','machine:reset'))
 def read(self,a,n):
  if not isinstance(a,int)or not isinstance(n,int)or not 0<=a<65536 or not 1<=n<=65536-a:raise ValueError('Exact no-wrap RAM read')
  b=self.request('GET',f'machine:readmem?address={a:X}&length={n}')
  if not isinstance(b,bytes)or len(b)!=n:raise ValueError('Exact RAM bytes/count required')
  return b
 def write(self,a,b):
  if not self.paused or not isinstance(b,bytes)or not((a==0x200 and len(b)in[1,142])or(a==0x4000 and 0<len(b)<=16384)):raise ValueError('Only paused fixed owned request/payload writes')
  if a==0x200 and len(b)==1 and b!=b'\x22':raise ValueError('Count-last GO only')
  return self.ack(self.request('POST',f'machine:writemem?address={a:X}',b))
 def startup_write(self,a,b):
  if not self.paused or not((a==0x2a0 and b==bytes(64))or(a==0x277 and b==b'SYS2061\r')or(a==0xc6 and b in[b'\0',b'\x08'])):raise ValueError('Exact paused unstarted sentinel/ownedSYS writes only')
  return self.ack(self.request('POST',f'machine:writemem?address={a:X}',b))
 def load_prg(self,body):
  if not self.paused or self.loaded or body!=self.source.configured:raise ValueError('One exact paused stager-only load attempt')
  self.loaded=True # ambiguity never permits retry
  return self.ack(self.request('POST','runners:load_prg',body))
