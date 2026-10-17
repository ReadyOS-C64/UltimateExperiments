"""Fixed two snapshots/four scratch commands, over unchanged bounded HTTP.
The coordinator is trusted code; no public observations confer authority.
No files/UCI/FTP or arbitrary REU direction/range is admitted.
"""
import zlib
from cold_transport import ColdREST
from transport import INVENTORY
from bulk_program import exact_baseline,SOURCE,SCRATCH,CHUNK,sha
from host_stream import HOFF,SIZE

class HybridREST(ColdREST):
 def __init__(self,host,streams,service,baseline,**kw):
  if set(streams)!={'initial','final'}or sha(service)!=SOURCE:raise ValueError('Exact two configured streams and40fe')
  if streams['initial'][1]==streams['final'][1]:raise ValueError('Distinct phase nonces required')
  self.streams=streams;self.service=service;self._baseline=exact_baseline(baseline)
  super().__init__(host,streams['initial'][0],**kw)
  self.mode='activate';self.role=None;self._permit=None;self._command=None;self._command_index=0;self._safety_index=0;self._seq=0;self.stream_done=set();self._last_full=None;self.reset_uncertain=False;self.global_full=0;self.global_acks=0
 def _allowed(self,m,r,body):
  reads={(0,65536),(0x801,len(self.source)-2)}
  if self.role in ('initial','final'):reads.update({(0x3e00,52),(0x801,SIZE)})
  if self.role in ('scratch','safety'):reads.update({(0x6000,32),(0x6004,1),(0x8000,CHUNK)})
  readonly=m=='GET'and body is None and r in INVENTORY
  if m=='GET'and body is None and r.startswith('machine:readmem?'):
   try:
    q=dict(v.split('=')for v in r.split('?')[1].split('&'));readonly=set(q)=={'address','length'}and(int(q['address'],16),int(q['length']))in reads
   except (ValueError,KeyError):readonly=False
  control=m=='PUT'and r in {'machine:pause','machine:resume','machine:reset'}and body is None
  config=m=='POST'and r=='configs'and self._turbo_original is not None and body==(self._turbo_restore_body if self.cleanup_mode else self._turbo_temporary_body)
  if config and self.cleanup_mode and'turbo_temporary'not in self.calls:raise ValueError('No restore without owned temporary attempt')
  write=self._permit is not None and(m,r,body)==self._permit
  if(config or write)and self.archive_write is None:raise ValueError('Durable raw reply required before mutation')
  if not(readonly or control or config or write):raise ValueError('Outside exact hybrid capability')
 def _post(self,a,b,end):
  r=f'machine:writemem?address={a:X}';self._permit=('POST',r,b)
  try:
   result=self._exchange('POST',r,end,body=b);self._address(result,a,len(b));return result
  finally:self._permit=None
 def control(self,kind,key,deadline):
  if kind=='reset'and self.reset_uncertain:raise ValueError('No reset following ambiguous reset')
  try:return super().control(kind,key,deadline)
  except BaseException:
   if kind=='reset':self.reset_uncertain=True
   raise
 def cold_begin(self,role):
  if role=='initial':allowed=self.mode=='activate'
  elif role=='scratch':allowed=self.mode=='initial_done'and self.stream_done=={'initial'}
  elif role=='final':allowed=self.mode=='scratch_native'and self._command_index==4
  elif role=='safety':allowed=self.mode=='scratch_native'and self.cleanup_mode
  else:allowed=False
  if not allowed:raise ValueError('Monotone fixed hybrid phases')
  self._once('cold_'+role);self.role=role;self.mode=role+'_cold';self._seq=0
  self.source=self.streams[role][0]if role in self.streams else self.service
  if role in self.streams:
   self.ack_next=1;self.ack_attempted=set();self.cancel_attempted=False;self.full_count=0;self._last_full=None
 def load(self,end):
  if self.mode!=self.role+'_cold':raise ValueError('Only cold load')
  self._once(self.role+'_load');self.load_attempted=True;return self._post(0x801,self.source[2:],end)
 def write(self,*args):
  if len(args)==2:
   kind,end=args
   if self.mode!=self.role+'_cold':raise ValueError('Only cold initialization')
   routes={'SYS_body':(0x277,b'SYS2061\r'),'SYS_count':(0xc6,b'\x08')}
   if self.role in self.streams:routes.update(mailbox_zero=(0x3f00,b'\0\0'),header_zero=(0x3e00,bytes(52)))
   else:routes['mailbox_zero']=(0x6000,bytes(32))
   if kind not in routes:raise ValueError('Exact cold writable fields')
   self._once(self.role+'_'+kind);a,b=routes[kind];return self._post(a,b,end)
  a,b,end=args
  if self._command is None:raise ValueError('No native descriptor authority')
  d,reu,n,expected,seq,index=self._command
  values=[(0x8000,expected if d==0 else bytes(v^255 for v in expected)),(0x6006,bytes([d])+seq.to_bytes(2,'little')),(0x600b,reu.to_bytes(3,'little')+n.to_bytes(2,'little')+(seq^0xffff).to_bytes(2,'little')),(0x6004,b'G')]
  if index>=4 or(a,b)!=values[index]:raise ValueError('Exact once staging/body/tail/GO')
  self._command=(d,reu,n,expected,seq,index+1);return self._post(a,b,end)
 def started(self):
  if self.mode!=self.role+'_cold':raise ValueError('One fresh native entry')
  self.mode=self.role+'_native'
 def begin(self,role,d,a,n,b,end):
  if self._command is not None:raise ValueError('Exclusive descriptor')
  original=self._baseline[SCRATCH:SCRATCH+CHUNK];pattern=bytes(v^255 for v in original)
  if self.mode=='scratch_native':
   values=[('pattern_WRITE',0,pattern),('pattern_READ',1,pattern),('original_WRITE',0,original),('original_READ',1,original)]
   if self._command_index>=4:raise ValueError('No fifth command')
   want=values[self._command_index]
   if(role,d,b)!=want or(a,n)!=(SCRATCH,CHUNK):raise ValueError('Only four owned scratch operations')
   self._command_index+=1
  elif self.mode=='safety_native':
   if self._safety_index>=2:raise ValueError('Only one original-only safety pair')
   want=('safety_original_WRITE'if self._safety_index==0 else'safety_original_READ',self._safety_index,original)
   if(role,d,b)!=want or(a,n)!=(SCRATCH,CHUNK):raise ValueError('Safety original-only exact span')
   self._safety_index+=1
  else:raise ValueError('No scratch authority in stream phase')
  self._seq+=1;self._command=(d,a,n,b,self._seq,0)
 def end(self):self._command=None
 def read(self,a,n,end):return self._exchange('GET',f'machine:readmem?address={a:X}&length={n}',end,n)
 def pause(self,end):return self._exchange('PUT','machine:pause',end)
 def resume(self,end):return self._exchange('PUT','machine:resume',end)
 def header(self,end):
  if self.mode not in ['initial_native','final_native']:raise ValueError('No stream header outside native phase')
  return super().header(end)
 def full(self,end):
  if self.mode not in ['initial_native','final_native']:raise ValueError('No stream frame outside phase')
  raw=super().full(end);self._last_full=raw;self.global_full+=1;return raw
 def ack(self,n,end):
  if self.mode not in ['initial_native','final_native']:raise ValueError('No stream ACK outside phase')
  route=f'machine:writemem?address=3F00&data={n:02X}';self._permit=('PUT',route,None)
  try:r=super().ack(n,end);self.global_acks+=1;return r
  finally:self._permit=None
 def cancel(self,end):
  if self.mode not in ['initial_native','final_native']:raise ValueError('No cancel outside active stream')
  self._permit=('PUT','machine:writemem?address=3F01&data=01',None)
  try:return super().cancel(end)
  finally:self._permit=None
 def finish_stream(self,path):
  from pathlib import Path
  role=self.role
  if role not in self.streams or self.mode!=role+'_native'or self.ack_next!=129 or self.full_count!=129:raise ValueError('Complete private stream ledger')
  raw=self._last_full;h=raw[HOFF:HOFF+52]if raw is not None else b''
  if len(h)!=52 or h[:8]!=b'RSF1\1\0\4\0'or h[8:24]!=self.streams[role][1]or int.from_bytes(h[24:26],'little')!=128 or int.from_bytes(h[36:40],'little')!=0x400000 or int.from_bytes(h[48:52],'little')!=zlib.crc32(h[:48])or raw[:len(self.source)-2]!=self.source[2:]:raise ValueError('Exact final native/source/nonce proof')
  if Path(path).read_bytes()!=self._baseline:raise ValueError('Durable whole4MiB before advancing phase')
  self.stream_done.add(role);self.mode=role+'_done'
