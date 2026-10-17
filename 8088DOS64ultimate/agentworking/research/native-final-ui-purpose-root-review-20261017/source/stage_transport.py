"""Purpose-specific five-role composition of the accepted PUT/numeric engine.
No new wire protocol. Stager requests must originate in its typed PutIO owner.
"""
import hashlib,re,zlib
from pathlib import Path
from put_transport import PutREST
from fast_transport import CONFIGURED
from cold_transport import ColdREST
from transport import REST
from host_stream import HOFF

class StageREST(PutREST):
 def __init__(self,host,streams,service,baseline,stager,**kw):
  if set(streams)!={'initial','changed','final'}or len({v[1]for v in streams.values()})!=3:raise ValueError('Three distinct snapshot nonces')
  super().__init__(host,{k:streams[k]for k in ['initial','final']},service,baseline,**kw)
  self.streams=streams;self.stager=stager;self.stage_io=None;self.stage_closed=False;self._stage_terminal=None;self._stage_permit=None;self.stage_started=False
 def _allowed(self,m,r,body):
  if self._stage_permit is not None:
   if self.role!='stage'or self.mode not in ['stage_cold','stage_native']or(m,r,body)!=self._stage_permit:raise ValueError('Exact serialized stager request')
   if m=='POST'or body is not None:raise ValueError('No POST/body')
   return
  # Mandatory recovery is a new, once-only source-gated phase after a
  # known-closed stager, not a repeated failed native command. Numeric
  # transport cleanup_mode preserves the first wire error while permitting
  # these exact private role PUTs under the ORIGINAL core endpoint.
  if self.cleanup_mode and self._stage_terminal is not None and self.role in ['changed','restore','final']and self._permit==(m,r,body)and self._permit is not None:
   if m!='PUT'or body is not None or re.fullmatch(r'machine:writemem\?address=[0-9A-F]+&data=[0-9A-F]{2,256}',r)is None:raise ValueError('Only bounded typed recovery PUT')
   return
  return super()._allowed(m,r,body)
 def cold_begin(self,role):
  previous={'initial':('activate',set()),'changed':('stage_native',{'initial'}),'restore':('changed_done',{'initial','changed'}),'final':('restore_native',{'initial','changed'})}
  if role not in previous or(self.mode,self.stream_done)!=previous[role]:raise ValueError('Fixed initial/stage/changed/restore/final order')
  if role=='changed':
   from preserved_stage import closed_terminal
   if self._stage_terminal is None:raise ValueError('Actual closed stager terminal required')
   closed_terminal(self._stage_terminal,self.stager)
  if role=='final'and not self.restore_done:raise ValueError('Actual original restore DONE required')
  self._once('cold_'+role);self.role=role;self.mode=role+'_cold';self.source=self.streams[role][0]if role in self.streams else self.service
  if role in self.streams:self.ack_next=1;self.ack_attempted=set();self.cancel_attempted=False;self.full_count=0;self._last_full=None
 def accept_stage_terminal(self,raw):
  from preserved_stage import closed_terminal
  if self.role!='stage'or self.mode!='stage_native'or self._stage_terminal is not None:raise ValueError('One current stager terminal')
  closed_terminal(raw,self.stager);self._stage_terminal=bytes(raw);self.stage_closed=True
 def begin_stage(self,io):
  if self.mode!='initial_done'or self.stream_done!={'initial'}or self.stage_io is not None:raise ValueError('One stager after original baseline')
  self._once('cold_stage');self.stage_io=io;self.role='stage';self.mode='stage_cold';self.source=self.stager.configured
 def stage_exchange(self,io,m,r,end,count=None):
  if io is not self.stage_io or self.role!='stage'or self._stage_permit is not None:raise ValueError('One same-engine stager owner')
  allowed=m=='PUT'and r in ['machine:pause','machine:resume','machine:reset']
  match=re.fullmatch(r'machine:readmem\?address=([0-9A-F]+)&length=([0-9]+)',r)if m=='GET'else None
  if match:
   a,n=int(match[1],16),int(match[2]);allowed=0<=a<65536 and 1<=n<=65536-a and count==n
  if m=='PUT'and r.startswith('machine:writemem?'):allowed=io._permit==(m,r)
  if not allowed:raise ValueError('Only source-admitted PutIO operation')
  if m=='PUT'and r=='machine:reset':
   if self.reset_uncertain:raise ValueError('No reset after ambiguous reset')
   self._once('stage_reset')
  if m=='PUT'and r=='machine:resume'and io.loaded:
   # A conservative possibility flag is set before the resume attempt.
   self.stage_started=True;self.mode='stage_native'
  self._stage_permit=(m,r,None)
  try:return self._exchange(m,r,end,count)
  except BaseException:
   if m=='PUT'and r=='machine:reset':self.reset_uncertain=True
   raise
  finally:self._stage_permit=None
 def load(self,end):
  if self.role!='changed':return super().load(end)
  if self.mode!='changed_cold'or'changed'in self.source_loads:raise ValueError('One changed source')
  self._once('changed_load');self.load_attempted=True;body=self.source[2:]
  ledger={'source_sha256':hashlib.sha256(self.source).hexdigest(),'body_sha256':hashlib.sha256(body).hexdigest(),'body_bytes':len(body),'chunks':(len(body)+127)//128,'attempts':[],'ACKs':0,'endpoint':end};self.source_loads['changed']=ledger
  for i in range(ledger['chunks']):
   part=body[128*i:128*(i+1)];self._once('changed_chunk_'+str(i));ledger['attempts'].append(i);self._source_chunk={'role':'changed','index':i,'address':0x801+128*i,'count':len(part),'payload_sha256':hashlib.sha256(part).hexdigest(),'source_sha256':ledger['source_sha256']}
   try:self._post(0x801+128*i,part,end);ledger['ACKs']+=1
   finally:self._source_chunk=None
  return {'role':'changed','chunks':ledger['ACKs'],'bytes':len(body)}
 def _stream(self):
  if self.role not in self.streams or self.mode!=self.role+'_native':raise ValueError('Current native snapshot only')
 def header(self,end):self._stream();return REST.header(self,end)
 def full(self,end):
  self._stream();raw=REST.full(self,end);self._last_full=raw;self.global_full+=1;return raw
 def ack(self,n,end):
  self._stream();self._permit=('PUT',f'machine:writemem?address=3F00&data={n:02X}',None)
  try:v=REST.ack(self,n,end);self.global_acks+=1;return v
  finally:self._permit=None
 def cancel(self,end):
  self._stream();self._permit=('PUT','machine:writemem?address=3F01&data=01',None)
  try:return REST.cancel(self,end)
  finally:self._permit=None
 def finish_stream(self,path):
  self._stream();role=self.role;raw=self._last_full;h=raw[HOFF:HOFF+52]if raw else b''
  if self.ack_next!=129 or self.full_count!=129 or len(h)!=52 or h[:8]!=b'RSF1\1\0\4\0'or h[8:24]!=self.streams[role][1]or int.from_bytes(h[24:26],'little')!=128 or int.from_bytes(h[36:40],'little')!=4194304 or int.from_bytes(h[48:52],'little')!=zlib.crc32(h[:48])or raw[:len(self.source)-2]!=self.source[2:]:raise ValueError('Actual complete source/nonce/terminal snapshot')
  data=Path(path).read_bytes()
  if len(data)!=4194304 or(role!='changed'and data!=self._baseline):raise ValueError('Complete retained snapshot/baseline')
  self.stream_done.add(role);self.mode=role+'_done'

class StageClient:
 """Only the bound PutIO may borrow the SAME wire; no concurrent transport."""
 def __init__(self,wire,budget):self.wire=wire;self.budget=budget;self.io=None
 def request(self,m,r,data=None,content_type=None):
  if self.io is None or data is not None or content_type is not None:raise ValueError('Exact bound bodyless stager client')
  self.budget.remaining();match=re.fullmatch(r'machine:readmem\?address=[0-9A-F]+&length=([0-9]+)',r)
  return self.wire.stage_exchange(self.io,m,r,self.budget.deadline,int(match[1])if match else None)
