"""Typedthree-rolePUTupload; noPOST/attachment/arbitrarymemorywrite."""
import hashlib
from fast_transport import FastREST
class PutREST(FastREST):
 def __init__(self,*args,**kw):
  super().__init__(*args,**kw);self.source_loads={};self._source_chunk=None;self.archive_request=None;self.request_plans=[];self._field_write=None
 def _allowed(self,m,r,body):
  if m=='POST'or body is not None:raise ValueError('NoPOST/body/attachment capability')
  return super()._allowed(m,r,body)
 def _exchange(self,m,r,end,count=None,body=None):
  if self.first is not None and not self.cleanup_mode:raise self.first
  if self.archive_request is None:raise ValueError('Durable precall source/route metadata required')
  item={'index':len(self.request_plans)+1,'kind':'request_plan','method':m,'route':'/v1/'+r,'deadline':end,'body_bytes':0 if body is None else len(body),'raw_wire_packet_capture':False,'role':self.role,'retries':0}
  if self._source_chunk is not None:item['source_chunk']=self._source_chunk.copy()
  self.archive_request(item);self.request_plans.append(item)
  return FastREST._exchange(self,m,r,end,count,body)
 def _post(self,a,b,end):
  # Legacy inherited cold-field call name; actualwire is boundedPUTHEX only.
  if not isinstance(b,bytes)or not 1<=len(b)<=128:raise ValueError('DocumentedPUT max128')
  if self.mode!=self.role+'_cold':raise ValueError('CPUwrites only during admittedcoldrole')
  if self._source_chunk is not None:
   v=self._source_chunk;i=v['index'];source=self.source[2:];expected=source[128*i:128*(i+1)]
   if v['role']!=self.role or a!=0x801+128*i or b!=expected:raise ValueError('Exact role/sourcechunk only')
  else:
   if self._field_write is None:raise ValueError('Only typedcoldfield operation')
   key=self._field_write;fields={'SYS_body':(0x277,b'SYS2061\r'),'SYS_count':(0xc6,b'\x08')}
   if self.role in self.streams:fields.update(header_zero=(0x3e00,bytes(52)),mailbox_zero=(0x3f00,bytes(2)))
   else:fields['mailbox_zero']=(0x6000,bytes(32))
   if key not in fields or(a,b)!=fields[key]:raise ValueError('Exact admittedcoldfield bytes')
  r=f'machine:writemem?address={a:X}&data='+b.hex().upper();self._permit=('PUT',r,None)
  try:
   value=self._exchange('PUT',r,end);self._address(value,a,len(b));return value
  finally:self._permit=None
 def load(self,end):
  role=self.role
  if self.mode!=role+'_cold'or role not in ['initial','restore','final']or role in self.source_loads:raise ValueError('One role/source upload neverrearm')
  self._once(role+'_load');self.load_attempted=True
  body=self.source[2:];expected=self.streams[role][0][2:]if role in self.streams else self.service[2:]
  if body!=expected or len(body)not in [4592,4622]:raise ValueError('Exact currentlyadmittedrole source')
  ledger={'source_sha256':hashlib.sha256(self.source).hexdigest(),'body_sha256':hashlib.sha256(body).hexdigest(),'body_bytes':len(body),'chunks':(len(body)+127)//128,'attempts':[],'ACKs':0,'endpoint':end};self.source_loads[role]=ledger
  for i in range(ledger['chunks']):
   if i!=len(ledger['attempts'])or i!=ledger['ACKs']:raise ValueError('Monotone chunkattempt/completion')
   part=body[i*128:(i+1)*128];a=0x801+i*128
   self._once(role+'_chunk_'+str(i));ledger['attempts'].append(i);self._source_chunk={'role':role,'index':i,'address':a,'count':len(part),'payload_sha256':hashlib.sha256(part).hexdigest(),'source_sha256':ledger['source_sha256']}
   try:self._post(a,part,end);ledger['ACKs']+=1
   finally:self._source_chunk=None
  return dict(role=role,chunks=ledger['ACKs'],bytes=len(body))

 def write(self,*args):
  if len(args)!=2:raise ValueError('No descriptor/arbitraryCPUwrite capability')
  key,end=args;x=self.source_loads.get(self.role)
  if x is None or x['ACKs']!=x['chunks']:raise ValueError('Complete admittedrole source before coldfields/SYS')
  self._field_write=key
  try:return super().write(*args)
  finally:self._field_write=None
