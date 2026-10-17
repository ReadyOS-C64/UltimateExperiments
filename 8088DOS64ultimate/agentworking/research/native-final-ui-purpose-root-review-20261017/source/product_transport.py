import re
from urllib.parse import quote
from stage_transport import StageREST
from preserved_stage import closed_terminal
class ProductREST(StageREST):
 def __init__(self,*a,**kw):super().__init__(*a,**kw);self.product=None;self._product_permit=None;self.product_load_attempted=False;self.product_fields=set();self.product_terminal=None
 def _allowed(self,m,r,body):
  if self._product_permit is not None:
   if self.role!='product'or(m,r,body)!=self._product_permit or body is not None:raise ValueError('Exact serialized product request')
   return
  return super()._allowed(m,r,body)
 def begin_product(self,owner,raw):
  if self.product is not None or self.mode!='stage_native'or not self.stage_closed or self._stage_terminal!=raw:raise ValueError('One product after actual knownclosed stager')
  closed_terminal(raw,self.stager);self.product=owner;self.role='product';self.mode='product_native'
 def product_exchange(self,owner,m,r,end,count=None):
  if owner is not self.product or self.role!='product'or self._product_permit is not None:raise ValueError('One same-engine product owner')
  load='runners:load_prg?file='+quote(self.stager.home.decode()+'/SETUP.PRG',safe='')
  allowed=m=='PUT'and r in['machine:pause','machine:resume']
  if m=='PUT'and r==load:
   if self.product_load_attempted:raise ValueError('No second registered LOAD')
   self.product_load_attempted=True;allowed=True
  if m=='GET':
   a=owner.observer.p('coordinator','state');allowed=(r,count)in[('machine:readmem?address=0&length=65536',65536),(f'machine:readmem?address={a:X}&length=12',12)]
  if not allowed:raise ValueError('No synthetic native keys/reset/arbitrary productoperation')
  self._product_permit=(m,r,None)
  try:return self._exchange(m,r,end,count)
  finally:self._product_permit=None
 def control(self,kind,key,deadline):
  if self.role=='product':
   if kind not in['pause','resume']:raise ValueError('No reset while product owner active')
   self._once(key);return self.product_exchange(self.product,'PUT','machine:'+kind,deadline)
  return super().control(kind,key,deadline)
 def ram(self,key,deadline):
  if self.role=='product':
   self._once(key);return self.product_exchange(self.product,'GET','machine:readmem?address=0&length=65536',deadline,65536)
  return super().ram(key,deadline)
 def product_field(self,owner,a,b,end,key):
  if owner is not self.product or self.role!='product'or key in self.product_fields or (a,b,key)not in[(0x277,b'SYS2061\r','body'),(0xc6,b'\x08','count')]or(key=='count'and self.product_fields!={'body'}):raise ValueError('Exact one owned SYS body/count only')
  self.product_fields.add(key);r=f'machine:writemem?address={a:X}&data='+b.hex().upper();self._product_permit=('PUT',r,None)
  try:v=self._exchange('PUT',r,end);self._address(v,a,len(b));return v
  finally:self._product_permit=None
 def accept_product_terminal(self,raw):
  if self.product is None or self.role!='product':raise ValueError('Actualproduct owner')
  proof=self.product.observer.terminal(raw);self.product_terminal=bytes(raw);return proof
 def cold_begin(self,role):
  if role=='changed'and self.role=='product':
   if self.product_terminal is None:raise ValueError('No replacement while nativeUI/writer uncertain')
   self.product.observer.terminal(self.product_terminal);self.mode='stage_native'
  return super().cold_begin(role)
