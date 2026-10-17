"""Bounded transport-neutral consumer of the frozen READ-only stream.
No native load/SYS/retry/FTP/UCI/REU-write capability exists here.
"""
import time,json,zlib,hashlib,os
from pathlib import Path
from host_stream import Stream,BASE,SIZE,HOFF
class Cancelled(Exception):pass
class Driver:
 def __init__(self,source,nonce,wire,output,baseline,clock=time.monotonic,sleep=time.sleep,cancel=lambda:False,whole=600,phase=15,polls=1024):
  if not 0<whole<=600 or not 0<phase<=15 or not 1<=polls<=1024:raise ValueError('Finite bounds')
  if len(baseline)!=0x400000:raise ValueError('Exact original4MiB authority')
  self.clock=clock;self.sleep=sleep;self.cancel=cancel;self.wire=wire;self.end=clock()+whole;self.phase=phase;self.polls=polls;self.first=None;self.events=[];self.cancel_sent=False;self.last=None;self.expected=None;self.frame_end=self.end;self.output=Path(output);self.baseline=baseline
  self.reader=Stream(source,nonce,self.full,self.ack,self.output);self.reader.cold(source[2:]);self.nonce=nonce
 def bound(self,end):
  end=min(end,self.end)
  if self.clock()>=end:raise TimeoutError('Original bounded stream deadline')
  return end
 def parsed(self,h):
  if len(h)!=52 or h[:5]!=b'RSF1\1' or h[8:24]!=self.nonce or int.from_bytes(h[48:52],'little')!=zlib.crc32(h[:48]):raise ValueError('Exact polled header identity/CRC')
  return h[5],h[6],h[7],int.from_bytes(h[24:26],'little'),int.from_bytes(h[26:30],'little'),int.from_bytes(h[30:32],'little')
 def cancel_check(self):
  if not self.cancel():return
  first=Cancelled('Local cancellation requested');self.first=first
  if not self.cancel_sent:
   self.cancel_sent=True
   try:self.wire.cancel(self.bound(self.frame_end));self.events.append({'cancel_sent':True})
   except BaseException as e:self.events.append({'cancel_error':repr(e)})
  raise first
 def wait(self,number,terminal=False):
  self.frame_end=min(self.end,self.clock()+self.phase)
  for i in range(self.polls):
   self.bound(self.frame_end);self.cancel_check();h=self.wire.header(self.frame_end);self.bound(self.frame_end)
   if len(h)==52 and h[5]==0 and (h==bytes(52)or h[:5]!=b'RSF1\1'or int.from_bytes(h[48:52],'little')!=zlib.crc32(h[:48])):
    # Startup zero or a native bytewise unready publication is not authority.
    # Wait boundedly; never GET a frame, publish ACK or advance from this.
    self.events.append({'unready_unpublished':i});self.sleep(min(.01,max(0,self.frame_end-self.clock())));continue
   r,s,e,n,a,c=self.parsed(h)
   self.events.append({'header':i,'frame':n,'ready':r,'state':s,'error':e})
   if e or s==255:raise RuntimeError('Native terminal firstcause '+str(e))
   if terminal:
    if (r,s,e,n)==(0,4,0,128)and int.from_bytes(h[36:40],'little')==0x400000:return h
    if self.last is not None and h==self.last:pass # acknowledged frame128 has not yet been consumed
    else:raise ValueError('Ambiguous final terminal sequence')
   elif (r,s,e,n,a,c)==(0xa5,3,0,number,(number-1)*32768,32768):return h
   elif r==0 and s in(1,2)and e==0 and n==number and a==(number-1)*32768 and c==32768:pass
   elif self.last is not None and h==self.last:pass # same exact previouslyACKed immutable header; never reACK
   else:raise ValueError('Stale/forged/interleaved header sequence')
   self.sleep(min(0.01,max(0,self.frame_end-self.clock())))
  raise TimeoutError('Finite header observation count exhausted')
 def full(self,a,n):
  if (a,n)!=(BASE,SIZE):raise ValueError('One fixed full frame GET')
  self.bound(self.frame_end);raw=self.wire.full(self.frame_end);self.bound(self.frame_end)
  if len(raw)!=SIZE or raw[HOFF:HOFF+52]!=self.expected:raise ValueError('Immutable full GET differs from ready observation')
  return raw
 def ack(self,a,b):
  if a!=0x3f00 or len(b)!=1 or b[0]!=self.reader.next:raise ValueError('One exact private ACK')
  self.bound(self.frame_end);self.wire.ack(b[0],self.frame_end);self.bound(self.frame_end)
 def run(self):
  report={'schema':1,'status':'failed','frames':0,'bytes':0,'REU_write_operations':0,'FTP_connections':0,'first_error':None}
  try:
   for number in range(1,129):
    self.expected=self.wait(number);self.cancel_check();self.reader.receive();self.last=self.expected;report['frames']=number;report['bytes']=number*32768
   self.expected=self.wait(128,True);self.reader.terminal();data=self.output.read_bytes()
   if data!=self.baseline:raise ValueError('Complete4MiB does not match original baseline authority')
   report.update(status='passed',sha256=hashlib.sha256(data).hexdigest(),whole4MiB_exact=True,terminal_verified=True)
  except BaseException as e:
   if self.first is None:self.first=e
   report.update(first_error=repr(self.first),first_type=type(self.first).__name__)
  finally:
   try:self.reader.close()
   except BaseException as e:
    self.events.append({'file_close_error':repr(e)})
    if self.first is None:self.first=e
    report.update(status='failed',first_error=repr(self.first),first_type=type(self.first).__name__)
   report['events']=self.events;report['cancel_sent']=self.cancel_sent
   target=self.output.with_suffix(self.output.suffix+'.report.json')
   try:
    with target.open('xb')as f:f.write((json.dumps(report,indent=2)+'\n').encode());f.flush();os.fsync(f.fileno())
   except BaseException as e:
    if self.first is None:self.first=e
    else:self.events.append({'report_error':repr(e)})
    report.update(status='failed',first_error=repr(self.first),first_type=type(self.first).__name__)
   self.report=report
  if self.first is not None:raise self.first
  return report
