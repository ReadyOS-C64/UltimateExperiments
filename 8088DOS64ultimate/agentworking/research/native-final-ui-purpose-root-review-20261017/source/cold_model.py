"""Independent local HTTP/memory state fixture. Not a native/firmware simulator."""
from pathlib import Path
import json,struct,zlib
from transport import FIELDS
from host_stream import SIZE,HOFF,POFF
class Clock:
 def __init__(self):self.t=0
 def __call__(self):return self.t
 def sleep(self,n):self.t+=n
class Firmware:
 def __init__(self,source,nonce,data,clock):
  self.source=source;self.nonce=nonce;self.data=data;self.clock=clock;self.ram=bytearray((i^0x6d)&255 for i in range(65536));self.original=bytes(self.ram);self.paused=None;self.jiffy=1;self.running=False;self.frame=1;self.acked=0;self.calls=[];self.writes=[];self.fault=None;self.error=ConnectionResetError(54,'exact local wire failure');self.cancelled=False;self.turbo_control="C64U Turbo Registers";self.cpu_speed="64";self.system_mode="PAL"
 def ready(self):
  self.ram=bytearray(65536);r=self.ram;r[0]=0x2f;r[1]=0x37;r[0xd6]=3;r[0x288]=4;r[0x289]=10;r[0xd1:0xd3]=(0x478).to_bytes(2,'little');r[0x450:0x478]=bytes([18,5,1,4,25,46])+b' '*34;r[0x478:0x4a0]=b' '*40;r[0xa0:0xa3]=self.jiffy.to_bytes(3,'big');self.running=False
 def header(self):
  h=bytearray(52);terminal=self.acked==128;h[:8]=b'RSF1\1'+bytes([0 if terminal or self.cancelled else 0xa5,255 if self.cancelled else 4 if terminal else 3,3 if self.cancelled else 0]);h[8:24]=self.nonce;n=min(self.frame,128);struct.pack_into('<HIHI',h,24,n,(n-1)*32768,32768,zlib.crc32(self.data[(n-1)*32768:n*32768]));struct.pack_into('<I',h,36,0x400000 if terminal else(n-1)*32768);struct.pack_into('<I',h,44,0xffffffff);struct.pack_into('<I',h,48,zlib.crc32(h[:48]));return bytes(h)
 def response(self,method,path,body):
  route=path[4:];result={'errors':[]}
  if route=='info':return json.dumps(dict(FIELDS,errors=[])).encode()
  if route=='configs/C64%20and%20Cartridge%20Settings':return json.dumps({'errors':[],'C64 and Cartridge Settings':{'RAM Expansion Unit':'Enabled','REU Size':'16 MB','REU Preload':'Disabled'}}).encode()
  if route=='configs/U64%20Specific%20Settings':return json.dumps({'errors':[],'U64 Specific Settings':{'System Mode':self.system_mode,'Turbo Control':self.turbo_control,'CPU Speed':self.cpu_speed,'Unchanged field':'sentinel'}}).encode()
  if route=='configs':
   value=json.loads(body);assert set(value)=={'U64 Specific Settings'}and set(value['U64 Specific Settings'])=={'Turbo Control','CPU Speed'}
   self.turbo_control=value['U64 Specific Settings']['Turbo Control'];self.cpu_speed=value['U64 Specific Settings']['CPU Speed'];return json.dumps(result).encode()
  if route.startswith('configs/')or route=='drives':return json.dumps({'errors':[],'captured':route,'immutable':True}).encode()
  if route=='machine:pause':self.paused=True
  elif route=='machine:reset':self.jiffy+=1;self.ready();self.paused=False
  elif route=='machine:resume':
   self.paused=False;self.jiffy+=1;self.ram[0xa0:0xa3]=self.jiffy.to_bytes(3,'big')
   if self.ram[0xc6]==8 and self.ram[0x277:0x27f]==b'SYS2061\r':self.running=True;self.ram[0xc6]=0
  elif route.startswith('machine:writemem?'):
   fields=dict(x.split('=')for x in route.split('?')[1].split('&'));a=int(fields['address'],16);b=body if method=='POST'else bytes.fromhex(fields['data']);self.ram[a:a+len(b)]=b;self.writes.append((a,bytes(b)));result['address']=f'{a:04x}-{a+len(b)-1:04x}'
   if a==0x3f00 and len(b)==1:self.acked=b[0];self.frame=min(b[0]+1,128)
   if a==0x3f01:self.cancelled=True
  elif route.startswith('machine:readmem?'):
   fields=dict(x.split('=')for x in route.split('?')[1].split('&'));a=int(fields['address'],16);n=int(fields['length'])
   if self.running and a==0x3e00 and n==52:return self.header()
   if self.running and a==0x801 and n==SIZE:
    b=bytearray(SIZE);b[:len(self.source)-2]=self.source[2:];b[HOFF:HOFF+52]=self.header();m=min(self.frame,128);b[POFF:]=self.data[(m-1)*32768:m*32768];return bytes(b)
   return bytes(self.ram[a:a+n])
  else:raise AssertionError(('Unexpected local route',method,path))
  return json.dumps(result).encode()
 def __call__(self,host,timeout):
  model=self
  class Sock:
   def settimeout(self,n):assert 0<n<=5
  class Conn:
   sock=Sock()
   def request(self,method,path,body=None,headers=None):
    model.clock.t+=.001;self.index=len(model.calls)+1;model.calls.append({'index':self.index,'method':method,'path':path,'body_bytes':0 if body is None else len(body),'headers':headers,'request_body':None if body is None else body.decode('ascii')if path=='/v1/configs'else None,'timeout':timeout});self.body=model.response(method,path,body);self.mode=None if model.fault is None else model.fault(model,self.index,method,path)
    if self.mode=='reset':raise model.error
    if self.mode=='interrupt':raise KeyboardInterrupt('request interrupted')
    if self.mode=='short':self.body=self.body[:-1]
    if self.mode=='wrong_address':self.body=b'{"errors":[],"address":"ffff-ffff"}'
   def getresponse(self):
    outer=self
    class Response:
     status=400 if outer.mode=='http400'else 200
     def read1(self,n):
      if outer.mode=='drip':model.clock.t+=6
      b=outer.body[:n];outer.body=outer.body[n:];return b
    return Response()
   def close(self):pass
  return Conn()
