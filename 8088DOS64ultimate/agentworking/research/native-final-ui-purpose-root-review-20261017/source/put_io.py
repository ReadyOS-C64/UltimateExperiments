"""Typed bounded PUT128 replacement of the old POST stager transport.
Inject a frozen budgeted client and durable request/response recorder; no IO here.
"""
import time,re,hashlib
from rest_io import RestIO
class PutIO(RestIO):
 def __init__(self,*args,record,**kw):
  if not callable(record):raise ValueError('Durable pre-call/response recorder required')
  super().__init__(*args,**kw);self.record=record;self.first=None;self._permit=None;self.ledger=[];self.reset_attempted=False
 def request(self,method,route,data=None):
  if self.first is not None:raise self.first
  if method=='POST'or data is not None:raise ValueError('No POST/attachment/body')
  control=method=='PUT'and route in ['machine:pause','machine:resume','machine:reset']
  read=method=='GET'and re.fullmatch(r'machine:readmem\?address=[0-9A-F]+&length=[0-9]+',route)
  if not(control or read or self._permit==(method,route)):raise ValueError('No raw mutation capability')
  plan={'event':'before_request','method':method,'route':route,'body_bytes':0,'deadline':self.budget.deadline,'retries':0,'wire_packet_capture':False}
  try:
   self.record(plan);v=super().request(method,route);self.record({'event':'response','method':method,'route':route,'parsed':v if isinstance(v,dict)else None,'bytes':len(v)if isinstance(v,bytes)else None});return v
  except BaseException as e:
   if self.first is None:self.first=e
   raise
 def _span(self,a,b,role):
  if not self.paused or not isinstance(b,bytes)or not b or a<0 or a+len(b)>65536:raise ValueError('Exact paused owned span required')
  end=self.budget.deadline;row={'role':role,'address':a,'count':len(b),'sha256':hashlib.sha256(b).hexdigest(),'deadline':end,'attempts':[],'ACKs':0};self.ledger.append(row)
  for off in range(0,len(b),128):
   if self.first is not None:raise self.first
   part=b[off:off+128];address=a+off;route=f'machine:writemem?address={address:X}&data='+part.hex().upper();row['attempts'].append(off//128);self._permit=('PUT',route)
   try:
    value=self.ack(self.request('PUT',route));v=value.get('address')
    if not isinstance(v,str)or re.fullmatch(r'[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}',v)is None or(int(v[:4],16),int(v[5:],16))!=(address,address+len(part)-1):raise ValueError('Exact ASCII range ACK required; parsed='+repr(value))
    self.budget.remaining();row['ACKs']+=1
   except BaseException as e:
    if self.first is None:self.first=e
    raise
   finally:self._permit=None
  return {'errors':[]}
 def load_prg(self,body):
  if not self.paused or self.loaded or body!=self.source.configured:raise ValueError('One exact source-only load')
  self.loaded=True
  end=min(self.budget.deadline,self.clock()+15);self.budget.deadline=end
  return self._span(self.source.low,body[2:],'configured_source')
 def write(self,a,b):
  if not self.loaded or not self.paused or not isinstance(b,bytes)or not((a==0x200 and len(b)in[1,142])or(a==0x4000 and 0<len(b)<=16384)):raise ValueError('Fixed source-admitted stager fields only')
  if a==0x200 and len(b)==1 and b!=b'\x22':raise ValueError('Atomic GO22 only')
  return self._span(a,b,'GO'if a==0x200 and len(b)==1 else'descriptor'if a==0x200 else'CPUslab')
 def startup_write(self,a,b):
  if not self.paused or not((a==0x2a0 and b==bytes(64))or(a==0x277 and b==b'SYS2061\r')or(a==0xc6 and b in[b'\0',b'\x08'])):raise ValueError('Exact owned startup fields')
  return self._span(a,b,'sentinel'if a==0x2a0 else'SYSbody'if a==0x277 else'SYScount')
 def reset(self):
  if self.reset_attempted:raise ValueError('Single reset, no ambiguous retry')
  self.reset_attempted=True;return super().reset()
