from pathlib import Path
import json,hashlib,time,http.client,ftplib,io,os
HOST='10.0.0.79'
P=Path(__file__).resolve().parents[3]; ACTIVE=P/'agentworking/ACTIVE_HARDWARE_SESSION.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def save(path,data):
 with Path(path).open('xb')as f:f.write(data if isinstance(data,bytes)else(json.dumps(data,indent=2)+'\n').encode());f.flush();os.fsync(f.fileno())
def state(**kw):
 a=json.loads(ACTIVE.read_text());a.update(kw);tmp=ACTIVE.with_suffix('.session.tmp');tmp.write_text(json.dumps(a,indent=2)+'\n');os.replace(tmp,ACTIVE)
class Rest:
 def __init__(self,out,seconds=300):self.out=Path(out);self.end=time.monotonic()+seconds;self.seq=0
 def tx(self,method,route,count=None):
  left=self.end-time.monotonic();assert left>0,'Campaign deadline';self.seq+=1;t=time.monotonic();c=http.client.HTTPConnection(HOST,timeout=min(8,left))
  try:
   c.request(method,'/v1/'+route);r=c.getresponse();raw=r.read((count if count is not None else 262144)+1);save(self.out/('http-%04d.json'%self.seq),{'method':method,'route':route,'status':r.status,'bytes':len(raw),'sha256':sha(raw),'elapsed':time.monotonic()-t});assert r.status==200,(r.status,raw[:200]);
   if count is not None:assert len(raw)==count;return raw
   v=json.loads(raw);assert v.get('errors')==[],v;return v
  finally:c.close()
 def get(self,r):return self.tx('GET',r)
 def put(self,r):return self.tx('PUT',r)
 def read(self,a,n):return self.tx('GET',f'machine:readmem?address={a:X}&length={n}',n)
 def write(self,a,b):
  assert isinstance(b,bytes)and 0<len(b)<=128
  return self.put(f'machine:writemem?address={a:X}&data='+b.hex())
 def ram(self):return self.read(0,32768)+self.read(32768,32768)
 def inventory(self):return {r:self.get(r)for r in ['info','configs/U64%20Specific%20Settings','configs/C64%20and%20Cartridge%20Settings','drives']}
 def ready(self,name):
  import sys
  sys.path.insert(0,str(P/'agentworking/scratch/native-copy-wait76-recovery-purpose-20261017/work'))
  from ready_prefix import basic_ready
  last=None
  for i in range(40):
   self.put('machine:pause');ram=self.read(0,2048);v=basic_ready(ram)
   if v and last and v['jiffy']!=last['jiffy']:save(self.out/(name+'.bin'),ram);return v
   last=v;self.put('machine:resume');time.sleep(.08)
  raise TimeoutError('No advancing BASIC READY')
 def sys(self,entry):
  s=('SYS'+str(entry)+'\r').encode();assert len(s)<=10;self.write(0x277,s);assert self.read(0x277,len(s))==s;self.write(0xc6,bytes([len(s)]));assert self.read(0xc6,1)==bytes([len(s)]);self.put('machine:resume')
def ftp():
 f=ftplib.FTP();f.connect(HOST,21,timeout=8);f.login('anonymous','anonymous@');return f
def putcheck(f,name,body):
 f.storbinary('STOR '+name,io.BytesIO(body),blocksize=32768);parts=[];f.retrbinary('RETR '+name,parts.append,blocksize=32768);assert b''.join(parts)==body
