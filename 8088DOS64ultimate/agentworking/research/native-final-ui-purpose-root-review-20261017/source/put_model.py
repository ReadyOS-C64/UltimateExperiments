"""Protocolfixture extendsknownmodel with boundedhexwrites, not CPU/firmware."""
import json
from fast_model import Model,Clock
class PutModel(Model):
 def __init__(self,*a,**kw):
  super().__init__(*a,**kw);self.source_chunks=[];self.partial_chunk=None;self.source_uploads=[]
 def response(self,m,path,body):
  if m=='POST':raise AssertionError('POST forbidden by independentPUTmodel')
  result=super().response(m,path,body)
  if m=='PUT'and path.startswith('/v1/machine:writemem?'):
   q=dict(x.split('=')for x in path.split('?')[1].split('&'));a=int(q['address'],16);part=bytes.fromhex(q['data'])
   if 0x801<=a<0x1a0f:
    assert 0<len(part)<=128 and a+len(part)<=0x1a0f;index=len(self.source_chunks);self.source_chunks.append((a,part))
    if self.partial_chunk==index:self.ram[a+17:a+len(part)]=bytes(len(part)-17)
    for role,source in list((k,v[0])for k,v in self.streams.items())+[('restore',self.service)]:
     if a+len(part)==0x801+len(source)-2 and self.ram[0x801:0x801+len(source)-2]==source[2:]:
      self.kind=role;self.source=source;self.running=False;self.source_uploads.append(role)
      if role in self.streams:self.nonce=self.streams[role][1];self.frame=1;self.acked=0;self.cancelled=False
  return result
