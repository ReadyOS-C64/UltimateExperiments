"""LOCAL cold-session REST capability; live dispatch remains blocked.
Raw POST writes only configured native bytes at0801, PUTs only queue/mailbox.
The inherited stream engine remains READ-only with one ACK per durable frame.
"""
import json,time,re,hashlib
from transport import REST,HOST,FIELDS,INVENTORY
class ColdREST(REST):
 def __init__(self,host,source,*,factory,clock=time.monotonic):
  super().__init__(host,clock=clock,factory=factory)
  if not isinstance(source,bytes) or source[:2]!=b'\x01\x08' or not 2<len(source)<0x3e00-0x801+2:raise ValueError('Exact bounded source')
  self.source=source;self.cleanup_mode=False;self.calls={};self.load_attempted=False;self.failure_receipts=[];self.archive_failure=None;self.write_receipts=[];self.archive_write=None;self._turbo_original=None;self._turbo_restore_body=None;self._turbo_temporary_body=json.dumps({"U64 Specific Settings":{"Turbo Control":"Manual","CPU Speed":"64"}},separators=(",",":")).encode()
 def _once(self,key):
  if key in self.calls:raise ValueError('No repeated transaction '+key)
  self.calls[key]=1
 def _allowed(self,m,r,body):
  readonly=m=='GET' and (r in INVENTORY or r in {'machine:readmem?address=0&length=65536','machine:readmem?address=3E00&length=52','machine:readmem?address=801&length=47103'})
  control=m=='PUT' and r in {'machine:pause','machine:resume','machine:reset'} and body is None
  small=m=='PUT' and (r in {'machine:writemem?address=3E00&data='+'00'*52,'machine:writemem?address=3F00&data=0000','machine:writemem?address=277&data=535953323036310D','machine:writemem?address=C6&data=08','machine:writemem?address=3F01&data=01'} or re.fullmatch(r'machine:writemem\?address=3F00&data=(?:0[1-9A-F]|[1-7][0-9A-F]|80)',r)) and body is None
  load=m=='POST' and r=='machine:writemem?address=801' and body==self.source[2:]
  config=m=='POST'and r=='configs'and self._turbo_original is not None and body==(self._turbo_restore_body if self.cleanup_mode else self._turbo_temporary_body)
  if config and self.cleanup_mode and 'turbo_temporary'not in self.calls:raise ValueError('No restoration authority without owned set attempt')
  if (load or small or config)and self.archive_write is None:raise ValueError('Durable write-response recorder required before mutation')
  if self.cleanup_mode and (load or small):raise ValueError('Cleanup cannot write source, mailbox, SYS or ACK')
  if not (readonly or control or small or load or config):raise ValueError('Outside exact cold/stream capability')
 def arm_turbo(self,inventory):
  if self._turbo_original is not None:raise ValueError('Captured profile is single-use')
  v=inventory['configs/U64%20Specific%20Settings']['U64 Specific Settings']
  if v.get('System Mode')!='PAL'or v.get('Turbo Control')!='C64U Turbo Registers'or v.get('CPU Speed')!='64':raise ValueError('Exact current PAL/register-control64 profile required')
  self._turbo_original=(v['Turbo Control'],v['CPU Speed'])
  self._turbo_restore_body=json.dumps({'U64 Specific Settings':{'Turbo Control':self._turbo_original[0],'CPU Speed':self._turbo_original[1]}},separators=(',',':')).encode()
  return self._turbo_original
 def configure_turbo(self,role,deadline):
  if role not in ['temporary','restore']or self._turbo_original is None or (role=='restore')!=self.cleanup_mode:raise ValueError('Exact captured temporary/cleanup profile only')
  self._once('turbo_'+role)
  return self._exchange('POST','configs',deadline,body=self._turbo_restore_body if role=='restore'else self._turbo_temporary_body)
 def turbo_settings(self,deadline):return self._exchange('GET','configs/U64%20Specific%20Settings',deadline)
 def _raw(self,m,r,d,count=None):return self._exchange(m,r,d,count)
 def control(self,kind,key,deadline):
  if kind not in ['pause','resume','reset']:raise ValueError('Only C64 control')
  self._once(key);return self._exchange('PUT','machine:'+kind,deadline)
 def ram(self,key,deadline):
  self._once(key);return self._exchange('GET','machine:readmem?address=0&length=65536',deadline,65536)
 def load(self,deadline):
  self._once('load');self.load_attempted=True;r=self._exchange('POST','machine:writemem?address=801',deadline,body=self.source[2:]);self._address(r,0x801,len(self.source)-2);return r
 def write(self,kind,deadline):
  routes={'mailbox_zero':(0x3f00,b'\0\0'),'header_zero':(0x3e00,bytes(52)),'SYS_body':(0x277,b'SYS2061\r'),'SYS_count':(0xc6,b'\x08')}
  if kind not in routes:raise ValueError('No arbitrary raw writes')
  a,b=routes[kind];self._once(kind);r=self._exchange('PUT',f'machine:writemem?address={a:X}&data='+b.hex().upper(),deadline);self._address(r,a,len(b));return r
 def _exchange(self,method,route,deadline,count=None,body=None):
  if self.first is not None and not self.cleanup_mode:raise self.first
  self._allowed(method,route,body)
  conn=None;operation_error=None;pieces=[]
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
   if response.status!=200:raise ValueError('Exact HTTP200 required, no redirects')
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
   if method in ['PUT','POST']and (route.startswith('machine:writemem?')or route=='configs'):self._retain_write(method,route,body,value)
   return value
  except BaseException as e:
   operation_error=e
   if self.first is None:self.first=e
   self._retain_failure(method,route,b''.join(pieces),e)
   raise
  finally:
   if conn is not None:
    try:conn.close()
    except BaseException as e:
     self.events.append({'connection_close_error':repr(e)})
     if self.first is None:self.first=e
     if operation_error is None:
      self._retain_failure(method,route,b''.join(pieces),e);raise

 def _retain_failure(self,method,route,body,error):
  # Bounded per-response raw evidence; never repeat the request to fill gaps.
  item={'index':len(self.failure_receipts)+1,'method':method,'route':route,'received_bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'error':repr(error),'durable':False}
  self.failure_receipts.append(item)
  if self.archive_failure is not None:
   try:self.archive_failure(item,body);item['durable']=True
   except BaseException as e:item['archive_error']=repr(e)

 def _retain_write(self,method,route,body,value):
  # Preserve exact received JSON bytes before semantic address admission.
  item={'index':len(self.write_receipts)+1,'method':method,'route':route,'HTTP_status':200,'received_bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'parsed':value,'durable':False}
  self.write_receipts.append(item)
  if self.archive_write is None:raise ValueError('Durable write-response recorder missing')
  self.archive_write(item,body);item['durable']=True
