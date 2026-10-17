"""Proposed purpose-limited REST transport. No redirects, retries or FTP.
Constructing does not connect. All tests inject a local response factory.
Physical activation is separately BLOCKED in launch.py.
"""
import http.client,json,time,re
HOST='10.0.0.79';FIELDS={'product':'C64 Ultimate','firmware_version':'3.14','fpga_version':'121','core_version':'1.47','unique_id':'DCAF71'}
INVENTORY=('info','configs/U64%20Specific%20Settings','configs/C64%20and%20Cartridge%20Settings','drives')
class REST:
 def __init__(self,host,clock=time.monotonic,factory=http.client.HTTPConnection):
  if host!=HOST:raise ValueError('Exact device')
  self.host=host;self.clock=clock;self.factory=factory;self.first=None;self.ack_next=1;self.ack_attempted=set();self.cancel_attempted=False;self.full_count=0;self.RAM_count=0;self.events=[]
 def _raw(self,method,route,deadline,count=None):
  if self.first is not None:raise self.first
  readonly=method=='GET'and(route in INVENTORY or route in {'machine:readmem?address=0&length=65536','machine:readmem?address=3E00&length=52','machine:readmem?address=801&length=47103'})
  mutation=method=='PUT'and re.fullmatch(r'machine:writemem\?address=3F00&data=(?:0[1-9A-F]|[1-7][0-9A-F]|80)',route)or method=='PUT'and route=='machine:writemem?address=3F01&data=01'
  if not(readonly or mutation):raise ValueError('Route outside inventory/readonlyRAM/onebyteACKcancel capability')
  conn=None
  try:
   left=deadline-self.clock()
   if not 0<left<=600:raise TimeoutError('Original bounded phase deadline')
   conn=self.factory(self.host,timeout=min(5,left));self.events.append({'method':method,'route':route,'deadline':deadline,'retries':0});conn.request(method,'/v1/'+route);response=conn.getresponse()
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
    if self.clock()>=deadline:raise TimeoutError('Original response deadline after body read')
    if not part:break
    got+=len(part);pieces.append(part)
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
   return value
  except BaseException as e:
   if self.first is None:self.first=e
   raise
  finally:
   if conn is not None:
    try:conn.close()
    except BaseException as e:
     self.events.append({'connection_close_error':repr(e)})
     if self.first is None:self.first=e;raise
 def inventory(self,deadline):
  result={r:self._raw('GET',r,deadline)for r in INVENTORY}
  if any(result['info'].get(k)!=v for k,v in FIELDS.items()):raise ValueError('Exact current device/firmware before takeover')
  return result
 def original_RAM(self,deadline):
  if self.RAM_count:raise ValueError('Single original64KiB RAM capture')
  self.RAM_count=1;return self._raw('GET','machine:readmem?address=0&length=65536',deadline,65536)
 def header(self,deadline):return self._raw('GET','machine:readmem?address=3E00&length=52',deadline,52)
 def full(self,deadline):
  if self.full_count>=129:raise ValueError('At most128frame+1terminal fullGET')
  self.full_count+=1;return self._raw('GET','machine:readmem?address=801&length=47103',deadline,47103)
 def ack(self,n,deadline):
  if not isinstance(n,int)or n!=self.ack_next or not 1<=n<=128 or n in self.ack_attempted:raise ValueError('One monotone exact atomic ACK')
  self.ack_attempted.add(n)
  result=self._raw('PUT',f'machine:writemem?address=3F00&data={n:02X}',deadline)
  self._address(result,0x3f00,1)
  self.ack_next+=1
 def cancel(self,deadline):
  if self.cancel_attempted:raise ValueError('Single cancellation byte')
  self.cancel_attempted=True
  result=self._raw('PUT','machine:writemem?address=3F01&data=01',deadline)
  self._address(result,0x3f01,1)

 @staticmethod
 def _address(r,a,n):
  # Installed firmware uses uppercase hex; accept ASCII case equivalence only.
  value=r.get('address')
  if not isinstance(value,str)or re.fullmatch(r'[0-9a-fA-F]{4}-[0-9a-fA-F]{4}',value) is None or int(value[:4],16)!=a or int(value[5:],16)!=a+n-1:
   raise ValueError(f'Exact write acknowledgment address: expected {a:04x}-{a+n-1:04x}; actual parsed JSON={r!r}')
