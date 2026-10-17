"""Exact four-role PUT128/readonly snapshots + fixed owned file component.
No FTP/POST/descriptor/REU-write/arbitrary filesystem request capability.
"""
import hashlib,zlib
from cold_transport import ColdREST
from put_transport import PutREST
from fast_transport import FastREST
from transport import INVENTORY
from host_stream import HOFF
from copy_reader_host import Source as ReaderSource
from directory_host import DirectorySource
class CopyREST(PutREST):
 def __init__(self,host,streams,directory,reader,expected,**kw):
  if set(streams)!={'initial','final'}or type(directory)is not DirectorySource or type(reader)is not ReaderSource or len(expected)!=20971520 or hashlib.sha256(expected).hexdigest()!='78b941711081e5ee8b1e2855b1ca4d4876160f97a5dfdb1e475fa65a699d102c':raise ValueError('Exact owned source components/content')
  if directory.root!=reader.root or directory.nonce!=reader.nonce or streams['initial'][1]==streams['final'][1]or directory.nonce in [v[1]for v in streams.values()]:raise ValueError('Exact root/purpose nonce and distinct snapshots')
  self.streams=streams;self.directory=directory;self.reader=reader;self.expected=expected;self._baseline=None
  ColdREST.__init__(self,host,streams['initial'][0],**kw)
  self.role=None;self.mode='activate';self._permit=None;self._control_permit=None;self._profile_permit=None;self.source_loads={};self._source_chunk=None;self._field_write=None;self.archive_request=None;self.request_plans=[];self.response_meta={};self.stream_done=set();self.global_full=0;self.global_acks=0;self._last_full=None;self.reset_uncertain=False;self.requests=0;self.native_start_attempted=set();self.files_quiet=True;self.directory_receipt=None;self.reader_receipt=None;self.reader_next=1;self.reader_seq=set();self.reader_go=set();self.reader_frames=set();self.reader_polled=None;self.reader_full=None;self.reader_cancel_attempted=False;self.header_polls=0;self.field_ACKs={}
 def _allowed(self,m,r,body):
  reads={(0,65536),(0x801,len(self.source)-2)}
  if self.role in self.streams:reads|={(0x3e00,52),(0x801,47103)}
  if self.role=='directory':reads|={(0x200,84),(self.directory.at('sp'),2)}
  if self.role=='reader':reads|={(0x200,141),(self.reader.at('sp'),2),(0x260,4),(0x263,1)}
  readonly=m=='GET'and body is None and r in INVENTORY
  if m=='GET'and body is None and r.startswith('machine:readmem?'):
   try:
    q=dict(v.split('=')for v in r.split('?')[1].split('&'));readonly=set(q)=={'address','length'}and(int(q['address'],16),int(q['length']))in reads
   except (ValueError,KeyError):readonly=False
  control=m=='PUT'and body is None and self._control_permit==r
  profile=m=='PUT'and body is None and self._profile_permit==r
  write=m=='PUT'and body is None and self._permit==(m,r,None)
  if self.requests>=30000 or not(readonly or control or profile or write)or m=='POST'or body is not None:raise ValueError('Fixed finite ownedcopy capability only')
  if(write or profile or control)and self.archive_write is None:raise ValueError('Durable raw reply recorder before mutation')
  if self.cleanup_mode and write and r!='machine:writemem?address=262&data=01':raise ValueError('Cleanup cannot load/SYS/ACK/GO/restart')
  self.requests+=1
 def control(self,kind,key,end):
  if kind not in ['pause','resume','reset']:raise ValueError('Only documented C64 controls')
  if kind=='reset'and(self.reset_uncertain or not self.files_quiet):raise ValueError('No reset of ambiguous reset or unknown nativeFILES writer')
  if key=='start_resume'or key.endswith('_start_resume'):
   if self.role not in ['initial','directory','reader','final']or self.mode!=self.role+'_cold'or self.role in self.native_start_attempted or self.field_ACKs.get(self.role)!=['header_zero','mailbox_zero','SYS_body','SYS_count']:raise ValueError('One source-gated count-last SYS per role')
   self.native_start_attempted.add(self.role)
   if self.role in ['directory','reader']:self.files_quiet=False
  route='machine:'+kind;self._control_permit=route
  try:return ColdREST.control(self,kind,key,end)
  except BaseException:
   if kind=='reset':self.reset_uncertain=True
   raise
  finally:self._control_permit=None
 def cold_begin(self,role):
  allowed=(role=='initial'and self.mode=='activate')or(role=='directory'and self.mode=='initial_done'and self.stream_done=={'initial'})or(role=='reader'and self.mode=='directory_done'and self.directory_receipt is not None and self.files_quiet)or(role=='final'and self.mode=='reader_done'and self.reader_receipt is not None and self.files_quiet)
  if self.cleanup_mode or not allowed:raise ValueError('Monotone source/private-receipt phases')
  self._once('cold_'+role);self.field_ACKs[role]=[];self.role=role;self.mode=role+'_cold';self.source=self.streams[role][0]if role in self.streams else self.directory.configured if role=='directory'else self.reader.configured
  if role in self.streams:self.ack_next=1;self.ack_attempted=set();self.cancel_attempted=False;self.full_count=0;self._last_full=None
 def _small(self,a,b,end):
  if not isinstance(b,bytes)or not 1<=len(b)<=128:raise ValueError('Documented PUT128 bound')
  r=f'machine:writemem?address={a:X}&data='+b.hex().upper();self._permit=('PUT',r,None)
  try:v=self._exchange('PUT',r,end);self._address(v,a,len(b));return v
  finally:self._permit=None
 def load(self,end):
  role=self.role
  if self.cleanup_mode or self.mode!=role+'_cold'or role in self.source_loads:raise ValueError('Once typed cold source upload')
  expected=self.streams[role][0]if role in self.streams else self.directory.configured if role=='directory'else self.reader.configured
  if self.source!=expected:raise ValueError('Immutable role source mismatch')
  self._once(role+'_load');body=self.source[2:];row={'source_sha256':hashlib.sha256(self.source).hexdigest(),'body_bytes':len(body),'chunks':(len(body)+127)//128,'attempts':[],'ACKs':0,'endpoint':end};self.source_loads[role]=row
  for i in range(row['chunks']):
   self._once(role+'_chunk_'+str(i));part=body[128*i:128*(i+1)];row['attempts'].append(i);self._source_chunk={'role':role,'index':i,'address':0x801+128*i,'count':len(part),'source_sha256':row['source_sha256'],'payload_sha256':hashlib.sha256(part).hexdigest()}
   try:self._small(0x801+128*i,part,end);row['ACKs']+=1
   finally:self._source_chunk=None
  return row
 def write(self,kind,end):
  x=self.source_loads.get(self.role)
  if self.cleanup_mode or self.mode!=self.role+'_cold'or x is None or x['ACKs']!=x['chunks']:raise ValueError('Complete cold source before typed fields/SYS')
  fields={'SYS_body':(0x277,b'SYS2061\r'),'SYS_count':(0xc6,b'\x08')}
  if self.role in self.streams:fields.update(header_zero=(0x3e00,bytes(52)),mailbox_zero=(0x3f00,bytes(2)))
  else:fields.update(header_zero=(0x200,bytes(84 if self.role=='directory'else 48)),mailbox_zero=(0x260,bytes(4)))
  if kind not in fields:raise ValueError('No descriptor/arbitrary CPU orREUwrite')
  order=['header_zero','mailbox_zero','SYS_body','SYS_count']
  if kind!=order[len(self.field_ACKs[self.role])]:raise ValueError('Monotone initialization/body/count-last order')
  self._once(self.role+'_'+kind);v=self._small(*fields[kind],end);self.field_ACKs[self.role].append(kind);return v
 def started(self):
  if self.mode!=self.role+'_cold'or self.role not in self.native_start_attempted:raise ValueError('Only attempted same nativeSYS')
  self.mode=self.role+'_native'
 def finish_stream(self,path):
  from pathlib import Path
  if self.role not in self.streams or self.mode!=self.role+'_native'or self.ack_next!=129 or self.full_count!=129:raise ValueError('Complete private snapshot ledger')
  raw=self._last_full;h=raw[HOFF:HOFF+52]if raw else b''
  if len(h)!=52 or h[:8]!=b'RSF1\1\0\4\0'or h[8:24]!=self.streams[self.role][1]or int.from_bytes(h[24:26],'little')!=128 or int.from_bytes(h[36:40],'little')!=4194304 or int.from_bytes(h[48:52],'little')!=zlib.crc32(h[:48])or raw[:len(self.source)-2]!=self.source[2:]or Path(path).read_bytes()!=self._baseline:raise ValueError('Fresh exact native/nonce/full4MiB baseline proof')
  self.stream_done.add(self.role);self.mode=self.role+'_done'
 def directory_done(self,ram):
  if self.role!='directory'or self.mode not in['directory_native','directory_cold']or'directory'not in self.native_start_attempted:raise ValueError('No public directory authority')
  self.directory_receipt=self.directory.receipt(ram);self.files_quiet=True;self.mode='directory_done';return self.directory_receipt
 def reader_done(self,ram,path):
  from pathlib import Path
  if self.role!='reader'or self.mode!='reader_native'or self.reader_next!=641 or len(self.reader_go)!=640 or Path(path).read_bytes()!=self.expected:raise ValueError('Whole durable20MiB/private ACK ledger before use')
  self.reader_receipt=self.reader.terminal(ram);self.files_quiet=True;self.mode='reader_done';return self.reader_receipt
 def reader_write(self,a,b,end):
  n=self.reader_next
  if self.cleanup_mode or self.role!='reader'or self.mode!='reader_native'or n not in self.reader_frames:raise ValueError('Source-validated same reader frame required')
  if a==0x260 and b==n.to_bytes(2,'little'):
   if n in self.reader_seq:raise ValueError('No reissuing ambiguous sequence')
   self.reader_seq.add(n)
  elif a==0x263 and b==b'\xa5'and n in self.reader_seq:
   if n in self.reader_go:raise ValueError('No reissuing ambiguous GO')
   self.reader_go.add(n)
  else:raise ValueError('Only exact LE16 frame then atomic GOA5')
  return self._small(a,b,end)
 def reader_cancel(self,ram,end):
  if not self.cleanup_mode or self.role!='reader'or self.reader_cancel_attempted or 'reader'not in self.native_start_attempted:raise ValueError('Once owned cleanup cancellation only')
  h=self.reader.header(ram[0x200:0x230]);n=h['frame']
  if not 1<=n<=640:raise ValueError('No cancellation authority from unknown copy/owner')
  self.reader.frame(ram,n);self.reader_cancel_attempted=True
  return self._small(0x262,b'\1',end)
 def reader_failed_quiet(self,ram):
  self.reader.verify(ram);s=self.reader
  if ram[s.at('_cr_p_phase')]!=12 or not ram[s.at('_cr_p_first')]or ram[s.at('_files_handle')]!=0 or ram[s.at('_uci_state')]not in[9,10]or ram[s.at('_uci_recovery_failed')]:raise ValueError('Failed reader is not privately quiet')
  for n,v in {'copy_uncertain':0,'cwd_changed':0,'initialclosed':1,'raw':0}.items():
   if ram[s.at('_cr_p_'+n)]!=v:raise ValueError('Unknown file/CWD blocks replacement')
  if ram[s.at('sp'):s.at('sp')+2]!=b'\xff\xcf':raise ValueError('Native C frames still active')
  self.files_quiet=True;return True
