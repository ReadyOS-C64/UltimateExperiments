"""Typed, one-shot 40fe scratch qualification. No transport or device creation.

One core endpoint covers initial full read, one changed block, restoration,
final full read and (only on failure) one cold safety restoration. No generic
REU write capability is exposed to the physical-purpose caller.
"""
from pathlib import Path
import hashlib,time,os
SIZE=0x400000;CHUNK=0x4000;SCRATCH=0x200000
BASELINE='ac43c06b5e23774b298011c1a97bfbc72eb8395020465c747b135a83e9cd3eb3'
SOURCE='40fe690953c245c8093c7cd5e5cb91684df7290602d8afa44dbd2e0b5b30d09e'
def sha(b):return hashlib.sha256(b).hexdigest()
def exact_baseline(b):
 if not isinstance(b,bytes)or len(b)!=SIZE or sha(b)!=BASELINE:raise ValueError('Immutable complete ac43 authority required')
 return b

class Program:
 def __init__(self,service,baseline,out,*,clock=time.monotonic,cancel=lambda:False):
  self.baseline=exact_baseline(baseline);self.service=service;self.out=Path(out);self.clock=clock;self.cancel=cancel;self.started=False;self.first=None;self.may_changed=False;self.restored=False;self.safety_attempted=False;self.core_end=None;self.result={'initial_complete':False,'pattern_verified':False,'original_block_verified':False,'final_complete':False,'safety_attempted':False,'safety_restored':False}
 def left(self):
  if self.core_end is None or self.clock()>=self.core_end:raise TimeoutError('Original shared600s core deadline')
  return self.core_end-self.clock()
 def command(self,d,a,b,role):
  self.left()
  if self.cancel():raise KeyboardInterrupt('Cancellation before '+role)
  return self.service.command(d,a,CHUNK,b,role=role,end=self.core_end)
 def whole(self,name):
  path=self.out/name;digest=hashlib.sha256()
  with path.open('xb')as f:
   for a in range(0,SIZE,CHUNK):
    expected=self.baseline[a:a+CHUNK];got=self.command(1,a,expected,name)
    if not isinstance(got,bytes)or len(got)!=CHUNK:raise ValueError('Exact complete block required')
    if f.write(got)!=CHUNK:raise IOError('Whole capture short durable write')
    f.flush();os.fsync(f.fileno());digest.update(got)
    if got!=expected:raise ValueError(f'{name} baseline mismatch at {a:06x}')
  if digest.hexdigest()!=BASELINE:raise ValueError('Complete baseline digest')
  self.service.source_gate(self.core_end)
  return digest.hexdigest()
 def run(self):
  if self.started:raise ValueError('Program never rearmed')
  self.started=True;self.core_end=self.clock()+600
  try:
   self.whole('initial4MiB.bin');self.result['initial_complete']=True
   if self.left()<180:raise TimeoutError('Reserve180s for owned scratch recovery before any pattern WRITE')
   original=self.baseline[SCRATCH:SCRATCH+CHUNK];pattern=bytes(v^255 for v in original)
   # Conservative authority: even an exception before a known GO is treated
   # as possibly changed. This never authorizes replay of the pattern.
   self.may_changed=True
   self.command(0,SCRATCH,pattern,'pattern_WRITE')
   if self.command(1,SCRATCH,pattern,'pattern_READ')!=pattern:raise ValueError('Changed scratch bytes not independently read')
   self.result['pattern_verified']=True
   self.command(0,SCRATCH,original,'original_WRITE')
   if self.command(1,SCRATCH,original,'original_READ')!=original:raise ValueError('Original scratch not independently restored')
   self.restored=True;self.result['original_block_verified']=True
   self.whole('final4MiB.bin');self.result['final_complete']=True
  except BaseException as e:
   if self.first is None:self.first=e
   raise
  return dict(self.result,shared_core_seconds=600,core_end=self.core_end,baseline_sha256=BASELINE,qualified_span=[SCRATCH,SCRATCH+CHUNK],upper12MiB_access=False)
 def safety(self,preserve,cold):
  """ONE separate cold authority, original-only, original core endpoint.

  Preserve callback must durably retain paused terminal RAM/source/DRS first.
  Cold callback creates a new source-gated40fe instance with fresh ACK0; it
  does not retry a previous descriptor/GO. No safety attempt after proven
  original readback; failures remain failed even if safety restores bytes.
  """
  if not self.may_changed or self.restored:return False
  if self.safety_attempted:raise ValueError('No second safety restoration')
  self.safety_attempted=True;self.result['safety_attempted']=True
  try:
   self.left();preserve(self.core_end);self.left();service=cold(self.core_end)
   original=self.baseline[SCRATCH:SCRATCH+CHUNK]
   service.command(0,SCRATCH,CHUNK,original,role='safety_original_WRITE',end=self.core_end)
   got=service.command(1,SCRATCH,CHUNK,original,role='safety_original_READ',end=self.core_end)
   if got!=original:raise ValueError('Safety restoration independent READ mismatch')
   service.source_gate(self.core_end);self.restored=True;self.result['safety_restored']=True
   return True
  except BaseException as e:
   self.result['safety_error']=repr(e)
   if self.first is None:self.first=e
   raise

class Command:
 """Narrow derivative of unchanged40fe host descriptor/GO protocol.

 READ adds verified complement poison BEFORE GO. Every command checks exact
 linked code while paused before committing, descriptor coherence at DONE,
 and source again before consuming data. No command retry, no seq wrap.
 """
 def __init__(self,wire,source,*,clock=time.monotonic,sleep=time.sleep):
  if not isinstance(source,bytes)or sha(source)!=SOURCE:raise ValueError('Exact40fe source')
  self.wire=wire;self.source=source;self.clock=clock;self.sleep=sleep;self.seq=0;self.dead=False;self.calls=0
 def source_gate(self,end):
  if self.wire.read(0x801,len(self.source)-2,end)!=self.source[2:]:raise ValueError('Exact native source fence')
 def command(self,d,a,n,b,*,role,end):
  if self.dead:raise RuntimeError('Failed command instance cannot issue another descriptor')
  if not isinstance(b,bytes)or n!=CHUNK or len(b)!=n or a%CHUNK or not 0<=a<=SIZE-CHUNK or d not in (0,1):raise ValueError('Exact bounded16KiB block')
  if d==0 and a!=SCRATCH:raise ValueError('Only owned scratch WRITE')
  if self.seq>=0xffff:raise ValueError('No sequence wrap')
  deadline=min(end,self.clock()+12);self.calls+=1
  try:
   self.wire.begin(role,d,a,n,b,deadline)
   self.wire.pause(deadline);self.source_gate(deadline)
   old=self.wire.read(0x6000,32,deadline)
   if len(old)!=32 or old[:4]!=b'DRS1'or old[4]not in (0x11,0xa5)or old[5]or int.from_bytes(old[9:11],'little')!=self.seq:raise ValueError('Fresh coherent DRS state/ack')
   seq=self.seq+1;body=bytes([d])+seq.to_bytes(2,'little');tail=a.to_bytes(3,'little')+n.to_bytes(2,'little')+(seq^0xffff).to_bytes(2,'little')
   staging=b if d==0 else bytes(v^255 for v in b)
   self.wire.write(0x8000,staging,deadline)
   if self.wire.read(0x8000,n,deadline)!=staging:raise ValueError('Exact staging/poison before GO')
   self.wire.write(0x6006,body,deadline);self.wire.write(0x600b,tail,deadline)
   frozen=self.wire.read(0x6000,32,deadline)
   if frozen[6:9]!=body or frozen[11:18]!=tail or frozen[:6]!=old[:6]or frozen[9:11]!=old[9:11]:raise ValueError('Frozen exact descriptor before GO')
   self.source_gate(deadline)
   self.wire.write(0x6004,b'G',deadline)
   if self.wire.read(0x6004,1,deadline)!=b'G':raise ValueError('Exact GO readback; never retry')
   self.wire.resume(deadline)
   for _ in range(600):
    raw=self.wire.read(0x6000,32,deadline)
    if raw[4]in (0xa5,0xe1):
     if raw[:4]!=b'DRS1'or raw[6:9]!=body or raw[11:18]!=tail or int.from_bytes(raw[9:11],'little')!=seq:raise ValueError('Stale/corrupt completion descriptor/ack')
     if raw[4]!=0xa5 or raw[5]or raw[18]:raise ValueError('Native DMA failed: '+raw.hex())
     self.seq=seq;self.source_gate(deadline)
     if d==1:
      result=self.wire.read(0x8000,n,deadline)
      if result!=b:raise ValueError('Independent poisoned DMA readback mismatch')
      return result
     return None
    if self.clock()>=deadline:raise TimeoutError('Original12s command deadline')
    self.sleep(min(.01,max(0,deadline-self.clock())))
   raise TimeoutError('Finite600 command observations')
  except BaseException:
   self.dead=True;raise
  finally:self.wire.end()
