"""Injected offline host driver for the fixed owned20MiB clone/read component.
No network client or activation. Native may only COPY fixedsource -> freshroot,
then readonly READ04. Caller supplies paused exactsource and safe IO ownership.
"""
import hashlib,struct,zlib,re,time,math
TOTAL=20*1024*1024;SIZE=32768
sha=lambda b:hashlib.sha256(b).hexdigest()
class Source:
 def __init__(self,prg,labels,expected_prg_sha,expected_labels_sha,root,nonce):
  if sha(prg)!=expected_prg_sha or sha(labels.encode())!=expected_labels_sha:raise ValueError('Pinned exact native cohort')
  if not re.fullmatch(rb'/usb1/DOS64_TEST/[a-z0-9_-]{1,64}',root)or root==b'/usb1/DOS64_TEST/ac-media-20261016-081300' or len(root)>81 or not isinstance(nonce,bytes)or len(nonce)!=16 or not any(nonce):raise ValueError('Exactownedroot/nonzero nonce')
  self.labels={}
  for line in labels.splitlines():
   if line.startswith('al '):
    _,a,n=line.split();n=n.lstrip('.');a=int(a,16)
    if n not in ['_cr_p_first','_cr_p_phase','_cr_p_cleanup','_cr_p_copy_uncertain','_cr_p_cwd_changed','_cr_p_initialclosed','_cr_p_frame','_cr_p_offset','_cr_p_raw','_files_handle','_uci_state','_uci_error','_uci_recovery_failed','_br_config','_cr_control','_cr_header','_cr_ack','_cr_result','_cr_abi_sizes','_cr_init','_cr_step','_cr_entry','copy_reader_entry','runtime_init','fixture_return','sp','ps_rti','_ps_init','uci_status_read','uci_control_write','uci_id_read','uci_command_write','uci_data_read','uci_stat_read','read','store','_uci_command','_uci_data']:continue
    if n in self.labels and self.labels[n]!=a:raise ValueError('Ambiguous source label')
    self.labels[n]=a
  self.low=int.from_bytes(prg[:2],'little');self.high=self.low+len(prg)-2
  if self.low!=0x801 or self.high>0x4000 or self.at('_cr_header')!=0x200 or self.at('_cr_ack')!=0x260 or self.at('_cr_result')!=0x270:raise ValueError('Actual linker/source ABI')
  b=bytearray(prg[2:]);at=self.at('_cr_control')-self.low;b[at:at+145]=b'\xa5'+nonce+root.ljust(128,b'\0');at=self.at('_br_config')-self.low;b[at:at+134]=b'\xa5\x02'+struct.pack('<I',4194304)+root.ljust(128,b'\0');self.body=bytes(b);self.configured=prg[:2]+self.body;self.nonce=nonce;self.root=root
  self.ports={self.at(n)+1:0xdf1c+o for n,o in [('uci_status_read',0),('uci_control_write',0),('uci_id_read',1),('uci_command_write',1),('uci_data_read',2),('uci_stat_read',3)]};self.dynamic={self.at('read')+1:(self.at('_uci_command'),896),self.at('store')+1:(self.at('_uci_data'),896)};self.mutable={a+i for a in [*self.ports,*self.dynamic]for i in [0,1]}
  if len(self.mutable)!=16 or any(not self.low<=a<self.high for a in self.mutable):raise ValueError('Eight bounded UCI operand spans')
 def at(self,n):return self.labels[n]
 def verify(self,ram):
  if not isinstance(ram,bytes)or len(ram)!=65536 or ram[0]&7!=7 or ram[1]&7!=5:raise ValueError('Coherently paused whole mapped35 RAM')
  for i,b in enumerate(self.body):
   if self.low+i not in self.mutable and ram[self.low+i]!=b:raise ValueError('Immutable native source changed')
  for a,v in self.ports.items():
   if int.from_bytes(ram[a:a+2],'little')!=v:raise ValueError('Native UCI register operand')
  for a,(lo,n)in self.dynamic.items():
   v=int.from_bytes(ram[a:a+2],'little')
   if v!=0xffff and not lo<=v<lo+n:raise ValueError('Native buffer pointer escaped')
  if not 0xcd00<=int.from_bytes(ram[self.at('sp'):self.at('sp')+2],'little')<=0xcfff:raise ValueError('Native C stack outside owned range')
  if int.from_bytes(ram[0xfffa:0xfffc],'little')!=self.at('ps_rti')or ram[self.at('ps_rti')]!=0x40:raise ValueError('Native safe NMI source')
 def header(self,raw):
  if len(raw)!=48 or raw[:5]!=b'CFR1\x01'or raw[8:24]!=self.nonce or raw[30:32]!=b'\0\0'or int.from_bytes(raw[40:44],'little')!=TOTAL or int.from_bytes(raw[44:48],'little')!=zlib.crc32(raw[:44]):raise ValueError('Exact immutable header/nonce/CRC')
  return dict(state=raw[5],frame=int.from_bytes(raw[6:8],'little'),offset=int.from_bytes(raw[24:28],'little'),count=int.from_bytes(raw[28:30],'little'),crc=int.from_bytes(raw[32:36],'little'),read=int.from_bytes(raw[36:40],'little'))
 def frame(self,ram,n):
  self.verify(ram);h=self.header(ram[0x200:0x230]);r=ram[0x270:0x28d]
  if r[:5]!=b'CCR1\x01'or r[5:7]!=b'\0\0'or r[10:12]!=b'\1\0'or h!={'state':2,'frame':n,'offset':(n-1)*SIZE,'count':SIZE,'crc':zlib.crc32(ram[0x4000:0xc000]),'read':n*SIZE}:raise ValueError('Exactcurrent successful frame/result')
  self.private(ram,n,False)
  return ram[0x4000:0xc000]
 def private(self,ram,n,terminal):
  for name,v in {'first':0,'cleanup':0,'copy_uncertain':0,'cwd_changed':0,'initialclosed':1,'raw':0,'phase':12 if terminal else 7}.items():
   if ram[self.at('_cr_p_'+name)]!=v:raise ValueError('Private native '+name+' differs')
  if int.from_bytes(ram[self.at('_cr_p_frame'):self.at('_cr_p_frame')+2],'little')!=n or int.from_bytes(ram[self.at('_cr_p_offset'):self.at('_cr_p_offset')+4],'little')!=n*SIZE or ram[self.at('_files_handle')]!=(0 if terminal else 1)or ram[self.at('_uci_state')]!=9:raise ValueError('Private native position/frame/handle/quiet differs')
 def terminal(self,ram):
  self.verify(ram);h=self.header(ram[0x200:0x230]);r=ram[0x270:0x28d]
  if r[:12]!=b'CCR1\4\0\0\1\x0c\1\1\0'or r[24:29]!=b'\0\0\0\0\0'or int.from_bytes(r[12:16],'little')!=TOTAL or h['state']!=4 or h['frame']!=640 or h['offset']!=TOTAL or h['count']or h['read']!=TOTAL:raise ValueError('FullnativeEOF/knownCLOSE terminal')
  if ram[self.at('sp'):self.at('sp')+2]!=b'\xff\xcf':raise ValueError('Native terminal C frames not returned')
  self.private(ram,640,True)
  return {'read_bytes':TOTAL,'frames':640,'EOF_zero':True,'known_closed':True,'REU_commands':0}
class Driver:
 def __init__(self,io,source,*,clock=time.monotonic,seconds=600):
  if isinstance(seconds,bool)or not isinstance(seconds,(int,float))or not math.isfinite(seconds)or not 1<=seconds<=600:raise ValueError('Finite600s bound')
  self.io=io;self.source=source;self.clock=clock;self.end=clock()+seconds;self.started=False;self.acks=[];self.first=None;self.frames=[];self.calls=[]
 def check(self):
  if self.clock()>=self.end:raise TimeoutError('Original file readback endpoint')
 def once(self,label,fn):
  if label in self.calls:raise ValueError('No repeated ambiguous operation')
  self.check();self.calls.append(label);v=fn();self.check();return v
 def put(self,label,a,b):
  v=self.once(label,lambda:self.io.write(a,b))
  if not isinstance(v,dict)or v.get('errors')!=[] or not isinstance(v.get('address'),str)or re.fullmatch('[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}',v['address'])is None or tuple(int(x,16)for x in v['address'].split('-'))!=(a,a+len(b)-1):raise ValueError('Exact paused write range ACK')
  return v
 def run(self,retain,expected):
  if self.started or not callable(retain)or not isinstance(expected,bytes)or len(expected)!=TOTAL:raise ValueError('Onefixed whole20MiB source/sink')
  self.started=True;actual=bytearray()
  try:
   for n in range(1,641):
    # The injected IO owns bounded header-only readiness polling/paused consistency.
    self.once('wait'+str(n),lambda:self.io.ready(self.end));raw=self.once('frame'+str(n),lambda:self.io.read(0,65536));b=self.source.frame(raw,n)
    if b!=expected[(n-1)*SIZE:n*SIZE]:raise ValueError('Independent wholefile bytes differ atframe%d'%n)
    retain(n,b);actual.extend(b);self.frames.append(n)
    self.put('seq'+str(n),0x260,n.to_bytes(2,'little'))
    if self.once('seqread'+str(n),lambda:self.io.read(0x260,4))!=n.to_bytes(2,'little')+b'\0\0':raise ValueError('Exact paused ACK fields before GO')
    self.acks.append(n);self.put('go'+str(n),0x263,b'\xa5')
    if self.once('goread'+str(n),lambda:self.io.read(0x263,1))!=b'\xa5':raise ValueError('Exact GO readback before resume')
    self.once('resume'+str(n),self.io.resume)
   self.once('terminalwait',lambda:self.io.done(self.end));raw=self.once('terminal',lambda:self.io.read(0,65536));proof=self.source.terminal(raw)
   if bytes(actual)!=expected:raise ValueError('Completeindependent20MiB differs')
   return dict(proof,sha256=sha(bytes(actual)),source_sha256=sha(self.source.configured),execution_context='supplied by enclosing purpose; no network client here')
  except BaseException as e:
   if self.first is None:self.first=e
   raise self.first
