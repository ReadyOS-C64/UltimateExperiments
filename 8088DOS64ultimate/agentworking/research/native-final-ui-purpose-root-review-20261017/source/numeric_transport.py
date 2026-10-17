"""Purpose-limited settings REST; no native/REU/files capabilities.
Network request/read/deadline/close body derived from accepted ColdREST.
Non200 metadata/prefix is durable before raising; never a new request/retry.
"""
import json,time,hashlib
from transport import HOST,INVENTORY,FIELDS
PROFILE='configs/U64%20Specific%20Settings'
RESTORE='configs/U64%20Specific%20Settings/Turbo%20Control?value=C64U%20Turbo%20Registers'
PREFIX='machine:readmem?address=0&length=2048'
class RepairREST:
 def __init__(self,host,*,factory,clock=time.monotonic,archive):
  if host!=HOST:raise ValueError('Exact device')
  self.host=host;self.factory=factory;self.clock=clock;self.archive=archive;self.archive_failure=archive;self.archive_write=archive;self.first=None;self.cleanup_mode=False;self.calls=set();self.events=[];self.write_receipts=[];self.failure_receipts=[];self.response_meta={};self.phase='inspect';self._permit=None;self.requests=0
 def _once(self,key):
  if key in self.calls:raise ValueError('No repeated transaction '+key)
  self.calls.add(key)
 def _allowed(self,m,r,body):
  readonly=m=='GET'and body is None and(r in INVENTORY or r==PREFIX and self.phase=='verify')
  mutation=self._permit==(m,r,body)and body is None and((self.phase=='restore'and m=='PUT'and r==RESTORE)or(self.phase=='verify'and m=='PUT'and r in ['machine:pause','machine:resume']))
  if not(readonly or mutation)or self.requests>=22:raise ValueError('Outside exact one-field repair/readonly2048/once controls capability')
  if mutation and self.archive is None:raise ValueError('Durable response archive required')
  self.requests+=1
 def inventory(self,end):return {r:self._exchange('GET',r,end)for r in INVENTORY}
 def restore(self,end):
  if self.phase!='inspect':raise ValueError('One repair from inspected state')
  self._once('restore');self.phase='restore';self._permit=('PUT',RESTORE,None)
  try:return self._exchange('PUT',RESTORE,end)
  finally:self._permit=None;self.phase='verify';self.cleanup_mode=True
 def verify(self):self.phase='verify';self.cleanup_mode=True
 def profile(self,end):return self._exchange('GET',PROFILE,end)
 def control(self,kind,key,end):
  if kind not in ['pause','resume']or self.phase!='verify':raise ValueError('Only bounded BASIC observation controls')
  self._once(key);route='machine:'+kind;self._permit=('PUT',route,None)
  try:return self._exchange('PUT',route,end)
  finally:self._permit=None
 def prefix(self,key,end):self._once(key);return self._exchange('GET',PREFIX,end,2048)
 def _exchange(self,method,route,deadline,count=None,body=None):
  if self.first is not None and not self.cleanup_mode:raise self.first
  self._allowed(method,route,body)
  conn=None;operation_error=None;pieces=[];primary=None;self.response_meta={}
  try:
   left=deadline-self.clock()
   if not 0<left<=600:raise TimeoutError('Original bounded phase deadline')
   conn=self.factory(self.host,timeout=min(5,left));self.events.append({'method':method,'route':route,'deadline':deadline,'retries':0});
   if body is None:conn.request(method,'/v1/'+route)
   else:conn.request(method,'/v1/'+route,body=body,headers={'Content-Type':'application/json'if route=='configs'else'application/octet-stream','Content-Length':str(len(body))})
   left=deadline-self.clock()
   if left<=0:raise TimeoutError('Original deadline after request; no response retry')
   sock=getattr(conn,'sock',None)
   if sock is not None:sock.settimeout(min(5,left))
   response=conn.getresponse()
   self.response_meta={'HTTP_status':response.status,'HTTP_headers':[],'headers_truncated':False,'non200_body_limit':4096}
   if response.status!=200:primary=ValueError('Exact HTTP200 required, no redirects; status='+str(response.status))
   try:
    total=0
    for key,value in response.getheaders():
     if len(self.response_meta['HTTP_headers'])>=64: self.response_meta['headers_truncated']=True;break
     key=str(key);value=str(value);pair=[key[:128],value[:512]];size=len((pair[0]+pair[1]).encode('utf8'))
     if len(key)>128 or len(value)>512:self.response_meta['headers_truncated']=True
     if total+size>8192:self.response_meta['headers_truncated']=True;break
     total+=size;self.response_meta['HTTP_headers'].append(pair)
   except BaseException as e:
    self.response_meta['headers_capture_error']=repr(e)
    if primary is None:raise
   if primary is not None:
    if self.first is None:self.first=primary
    try:
     got=0
     for _ in range(4098):
      left=deadline-self.clock()
      if left<=0:raise TimeoutError('Original deadline while retaining non200 body')
      sock=getattr(conn,'sock',None)
      if sock is None:sock=getattr(getattr(getattr(response,'fp',None),'raw',None),'_sock',None)
      if sock is None:raise ValueError('Bounded response socket required')
      sock.settimeout(min(5,left));part=response.read1(min(1024,4097-got))
      if part:pieces.append(part);got+=len(part)
      if self.clock()>=deadline:raise TimeoutError('Original deadline after non200 body read')
      if not part or got>=4097:break
     raw=b''.join(pieces);self.response_meta['body_truncated']=len(raw)>4096;pieces=[raw[:4096]]
    except BaseException as e:self.response_meta['body_capture_error']=repr(e)
    raise primary
   # read1 performs at most one underlying bounded socket read. Reapply the
   # ORIGINAL deadline between chunks so a trickling body cannot reset it.
   limit=(count if count is not None else 262144)+1;pieces=[];got=0
   for block in range(262146):
    left=deadline-self.clock()
    if left<=0:raise TimeoutError('Original response deadline during body')
    sock=getattr(conn,'sock',None)
    if sock is None:sock=getattr(getattr(getattr(response,'fp',None),'raw',None),'_sock',None)
    if sock is None:raise ValueError('Bounded response socket required')
    sock.settimeout(min(5,left));part=response.read1(min(16384,limit-got))
    if part:got+=len(part);pieces.append(part)
    if self.clock()>=deadline:raise TimeoutError('Original response deadline after body read')
    if not part:break
    if got==limit:break
   else:raise TimeoutError('Finite response read count')
   body=b''.join(pieces)
   if self.clock()>=deadline:raise TimeoutError('REST response exceeded original deadline')
   if count is not None:
    if len(body)!=count:raise ValueError('Exact binary response count')
    return body
   if len(body)>262144:raise ValueError('Bounded JSON response')
   value=json.loads(body)
   if not isinstance(value,dict)or value.get('errors')!=[]:raise ValueError('Exact errors=[] acknowledgment')
   if method in ['PUT','POST']:self._retain_write(method,route,body,value)
   return value
  except BaseException as e:
   if primary is not None:
    e=primary;raw=b''.join(pieces);self.response_meta['body_truncated']=self.response_meta.get('body_truncated',False)or len(raw)>4096;pieces=[raw[:4096]]
   operation_error=e
   if self.first is None:self.first=e
   self._retain_failure(method,route,b''.join(pieces),e)
   raise e
  finally:
   if conn is not None:
    try:conn.close()
    except BaseException as e:
     self.events.append({'connection_close_error':repr(e)})
     if self.first is None:self.first=e
     if operation_error is None:
      self._retain_failure(method,route,b''.join(pieces),e);raise

 def _retain_failure(self,method,route,body,error):
  item={'index':len(self.failure_receipts)+1,'kind':'failure','method':method,'route':route,'received_bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'error':repr(error),**self.response_meta,'durable':False}
  self.failure_receipts.append(item)
  if self.archive_failure is not None:
   try:self.archive_failure(item,body);item['durable']=True
   except BaseException as e:item['archive_error']=repr(e)
 def _retain_write(self,method,route,body,value):
  item={'index':len(self.write_receipts)+1,'kind':'write','method':method,'route':route,'received_bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'parsed':value,**self.response_meta,'durable':False}
  self.write_receipts.append(item)
  self.archive_write(item,body);item['durable']=True
