"""Purpose-bound synchronous host protocol; IO is injected, never implicit network.
No mutation retry. Physical runner/preservation/recovery are deliberately separate.
"""
from pathlib import Path
import struct,time,zlib,hashlib,re,math
TEMPLATE_SHA='da2e6ee87521cb1a63b16110153d1cb651b791bc9ecda4945781fbacbf0497a3'
LABELS_SHA='644650eda66993c111b4a5e972ccc26ae0a0bc978497cda33ab6f673c4e2840e'
LEAVES={'START.REL', 'DOS3.IMG', 'DOS64.REL', 'DOS1.IMG', 'DOS2.IMG', 'CONFIG.PRG', 'SETUP.PUB', 'SETUP.FAT', 'START.RFW', 'DOS64.PRG', 'OWNER.JSON', 'DOS64.MNU', 'START.TPL', 'START.INO', 'START.RCV', 'SETUP.PRG'}
class NativeFailure(RuntimeError):pass
def sha(b):return hashlib.sha256(b).hexdigest()
class Source:
 def __init__(self,prg,labels,home):
  if sha(prg)!=TEMPLATE_SHA or sha(labels.encode())!=LABELS_SHA:raise ValueError('Exact native stager source cohort required')
  if not re.fullmatch(rb'/usb1/DOS64_TEST/[a-z0-9_-]{1,64}',home):raise ValueError('Fresh strict owned development root')
  self.symbols={}
  for row in labels.splitlines():
   if not row.startswith('al '):continue
   _,addr,name=row.split();name=name.lstrip('.');value=int(addr,16)
   if name not in ['_st_owner','_br_config','_st_request','_st_result','_st_cancel','_uci_command','_uci_data','_st_eof_wire','_st_step','ps_rti','stager_entry','uci_status_read','uci_control_write','uci_id_read','uci_command_write','uci_data_read','uci_stat_read','read','store']:continue
   if name in self.symbols and self.symbols[name]!=value:raise ValueError('Ambiguous native export '+name)
   self.symbols[name]=value
  self.low=int.from_bytes(prg[:2],'little');self.high=self.low+len(prg)-2
  if self.low!=0x801 or self.high>0x4000:raise ValueError('Exact visible code before CPUslab')
  body=bytearray(prg[2:]);self.home=home
  body[self.at('_st_owner')-self.low]=0xa5
  off=self.at('_br_config')-self.low;body[off:off+134]=b'\xa5\x02'+struct.pack('<I',4194304)+home.ljust(128,b'\0')
  self.configured=prg[:2]+bytes(body);self.body=bytes(body)
  self.port_words={self.at(n)+1:0xdf1c+o for n,o in [('uci_status_read',0),('uci_control_write',0),('uci_id_read',1),('uci_command_write',1),('uci_data_read',2),('uci_stat_read',3)]}
  self.dynamic={self.at('read')+1:(self.at('_uci_command'),896),self.at('store')+1:(self.at('_uci_data'),896)}
  self.mutable=set()
  for a in [*self.port_words,*self.dynamic]:self.mutable.update([a,a+1])
  if len(self.mutable)!=16 or any(not self.low<=a<self.high for a in self.mutable):raise ValueError('Exact eight SMC operand spans')
  if self.at('_st_request')!=0x200 or self.at('_st_result')!=0x2a0 or self.at('_st_cancel')!=0x290:raise ValueError('Fixed request/result/cancel ABI')
 def at(self,n):return self.symbols[n]
 def verify(self,body,*,cold=False):
  if len(body)!=len(self.body):raise ValueError('Complete source byte count required')
  if cold:
   if body!=self.body:raise ValueError('Cold complete configured program differs')
   return
  for i,(a,b) in enumerate(zip(body,self.body)):
   if a!=b and self.low+i not in self.mutable:raise ValueError('Immutable native byte changed at%04x'%(self.low+i))
  def word(a):return int.from_bytes(body[a-self.low:a-self.low+2],'little')
  for a,v in self.port_words.items():
   if word(a)!=v:raise ValueError('UCI register operand differs')
  for a,(lo,n) in self.dynamic.items():
   v=word(a)
   if v!=0xffff and not lo<=v<lo+n:raise ValueError('UCI self-modified pointer escaped source-bound buffer')
  return {'source_exact_except_16_bounded_SMC_operand_bytes':True,'configured_sha256':sha(self.configured)}
class Protocol:
 def __init__(self,io,source,*,clock=time.monotonic,seconds=600,event=lambda *a,**k:None):
  if isinstance(seconds,bool) or not isinstance(seconds,(int,float)) or not math.isfinite(seconds) or not 1<=seconds<=600:raise ValueError('Finite whole watchdog1..600seconds required')
  self.io=io;self.source=source;self.clock=clock;self.deadline=clock()+seconds;self.event=event;self.sequence=0;self.first=None;self.records=[];self.file_position=0;self.open=False
 def remaining(self,deadline):
  n=min(self.deadline,deadline)-self.clock()
  if n<=0:raise TimeoutError('Bounded native stager phase/whole watchdog')
  return n
 def exact_read(self,a,n,deadline):
  self.remaining(deadline);b=self.io.read(a,n);self.remaining(deadline)
  if not isinstance(b,bytes) or len(b)!=n:raise ValueError('Exact memory read required')
  return b
 def put(self,a,b,deadline):
  self.remaining(deadline);self.event('before_memory_write',address=a,bytes=len(b));value=self.io.write(a,b);self.remaining(deadline)
  if not isinstance(value,dict) or value.get('errors')!=[]:raise ValueError('Exact errors=[] memory-write acknowledgement required')
  if self.exact_read(a,len(b),deadline)!=b:raise ValueError('Full memory write readback differs')
 def result(self,deadline):
  b=self.exact_read(0x2a0,64,deadline)
  if b[:4]!=b'AST1' or any(b[i] for i in [5,37,*range(40,64)]):raise ValueError('Exact native result magic/reserved ABI')
  return b
 def boundary(self,deadline):
  self.io.pause();self.remaining(deadline);body=self.exact_read(self.source.low,len(self.source.body),deadline);self.source.verify(body)
  r=self.result(deadline)
  if r[4] not in [0x11,0xa5] or r[8] or r[30] or r[33] or r[35] or int.from_bytes(r[6:8],'little')!=self.sequence:raise ValueError('Exact prior quiet successful native boundary required')
  return r
 def job(self,op,*,offset=0,data=b'',leaf='',expected_size=None):
  deadline=min(self.deadline,self.clock()+12)
  if hasattr(self.io,'bound_until'):self.io.bound_until(deadline)
  try:
   if self.first is not None:raise ValueError('First failed native session is terminal')
   self.boundary(deadline)
   if self.sequence==65535:raise ValueError('No native sequence wrap')
   if not 1<=op<=10 or not 0<=offset<=0xffffffff or not isinstance(data,bytes) or len(data)>16384:raise ValueError('Bounded native request fields')
   if op in [2,6]:
    if leaf not in LEAVES:raise ValueError('Exact owned asset whitelist required')
   elif leaf:raise ValueError('Path only on OPEN')
   if op not in [3,4,8] and data:raise ValueError('Payload only on STASH/SAVE/LOAD')
   if op in [3,4,8] and not data:raise ValueError('Positive bounded data transfer')
   seq=self.sequence+1;crc=zlib.crc32(data)
   if data:self.put(0x4000,data,deadline)
   q=struct.pack('<BBHIHI',0,op,seq,offset,len(data),crc)+leaf.encode().ljust(128,b'\0')
   self.put(0x200,q,deadline)
   self.event('before_count_last_GO',sequence=seq,op=op)
   self.put(0x200,b'\x22',deadline) # one write only; ambiguous acknowledgement is fatal
   self.io.resume();self.remaining(deadline)
   while True:
    r=self.result(deadline)
    if r[4]==0xff:
     error=NativeFailure('Native stager first error%d cleanup%d'%(r[8],r[30]));error.native_result=r;self.first=error
     try:
      while not r[32]:r=self.result(deadline)
      self.io.pause();self.remaining(deadline);self.source.verify(self.exact_read(self.source.low,len(self.source.body),deadline));error.native_cleanup_result=r
     except BaseException as secondary:error.native_cleanup_interruption=secondary
     raise error
    if int.from_bytes(r[6:8],'little')==seq and r[4] in [0x11,0xa5]:break
   self.io.pause();self.remaining(deadline);self.source.verify(self.exact_read(self.source.low,len(self.source.body),deadline));r=self.result(deadline)
   if r[8] or r[30] or r[35] or int.from_bytes(r[6:8],'little')!=seq:raise ValueError('Final source/sequence/error boundary changed')
   if op in [3,8]:
    self.last_payload=self.exact_read(0x4000,len(data),deadline)
    if self.last_payload!=data:raise ValueError('Independent every-byte source/readback payload differs')
   if op in [4,8] and (int.from_bytes(r[16:20],'little')!=len(data) or int.from_bytes(r[12:16],'little')!=offset+len(data)):raise ValueError('Exact transferred count and new position required')
   if op==3 and int.from_bytes(r[12:16],'little')!=offset:raise ValueError('STASH does not advance file position')
   if op==7 and int.from_bytes(r[20:24],'little')!=offset:raise ValueError('Exact native fileSIZE required')
   if op==9:
    if not r[36] or int.from_bytes(r[38:40],'little')!=self.source.at('_st_eof_wire'):raise ValueError('Source-bound private EOF capture required')
    wire=self.exact_read(self.source.at('_st_eof_wire'),40,deadline)
    if wire not in [b'$     0 BYTES LOADED TO REU $20000000,OK',b'$000000 BYTES LOADED TO REU $20000000,OK']:raise ValueError('Exact EOF count/address/status capture required')
   if op in [5,10] and (r[9]!=3 or r[31]):raise ValueError('Known closed both targets required')
   if op==10 and not r[32]:raise ValueError('Native STOP completion signal required')
   self.sequence=seq;record={'sequence':seq,'op':op,'offset':offset,'bytes':len(data),'crc32':crc,'result':r.hex()};self.records.append(record);self.event('native_job_complete',**record);return r
  except BaseException as e:
   if self.first is None:self.first=e
   raise
 def file(self,leaf,body):
  if leaf not in LEAVES or not isinstance(body,bytes):raise ValueError('Exact immutable asset bytes')
  self.job(2,leaf=leaf)
  for offset in range(0,len(body),16384):
   chunk=body[offset:offset+16384];self.job(3,offset=offset,data=chunk);self.job(4,offset=offset,data=chunk)
  self.job(5);self.job(6,leaf=leaf);self.job(7,offset=len(body))
  for offset in range(0,len(body),16384):self.job(8,offset=offset,data=body[offset:offset+16384])
  self.job(9,offset=len(body));self.job(5)
  return {'bytes':len(body),'sha256':sha(body),'independent_full_readback':True,'native_EOF':True,'known_closed':True}

def publish_bundle(protocol,bundle,assets):
 """All immutable inputs verified before first native mkdir. START is last."""
 order=['OWNER.JSON','DOS64.PRG','DOS64.REL','A.IMG','B.IMG','DOS64.CFG','START.PRG']
 if bundle.get('status')!='PREPARED_OFFLINE_ONLY' or bundle.get('home','').encode()!=protocol.source.home or bundle.get('publication_order')!=order or set(assets)!=set(order) or set(bundle.get('files',{}))!=set(order):raise ValueError('Exact concrete owned START bundle required')
 for name,body in assets.items():
  row=bundle['files'][name]
  if not isinstance(body,bytes) or len(body)!=row.get('bytes') or sha(body)!=row.get('sha256') or zlib.crc32(body)!=row.get('crc32'):raise ValueError('Complete immutable asset differs '+name)
 protocol.job(1);completed={}
 for name in order:completed[name]=protocol.file(name,assets[name])
 protocol.job(10)
 return {'status':'passed','files':completed,'publication_order':order,'START_was_last':True,'full_native_and_independent_memory_readback':True,'native_known_closed_and_stopped':True,'REU_recovery_required':True,'physical':False}
