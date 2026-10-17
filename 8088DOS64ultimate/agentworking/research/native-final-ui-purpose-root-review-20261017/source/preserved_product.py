"""Bounded composition; callbacks must be frozen source-bound backends.
This is not a physical client/launcher and cannot activate a device by itself.
"""
import time,hashlib,copy
from native_file_receipt import resident_identity,done_mailbox
from basic_ready import basic_ready
BASELINE='ac43c06b5e23774b298011c1a97bfbc72eb8395020465c747b135a83e9cd3eb3'
RESTORE='5c709f00cf2a359856eb2866ffb0c3f4f5a8af35d2024992e97573ad423d23cc'
def closed_terminal(raw,source):
 if not isinstance(raw,bytes)or len(raw)!=65536:raise ValueError('Durable whole terminal RAM required')
 source.verify(raw[source.low:source.high]);r=raw[0x2a0:0x2e0]
 if r[:4]!=b'AST1'or r[4]not in[0x11,0xa5,0xff]or r[9]!=3 or r[30]or r[31]or r[33]or r[34]not in[0,9,10]or r[35]:raise ValueError('Unknown stager FILES/UCI ownership; no helper overwrite')
 if r[4]==0xff and not r[32]:raise ValueError('Native failed cleanup not complete')
 return {'known_closed':True,'quiet':True,'native_STOP':bool(r[32]),'native_error':r[8]}
class PreservedProduct:
 def __init__(self,baseline,restore_source,source,*,terminal_validator,clock=time.monotonic,cleanup_clock=time.monotonic):
  if len(baseline)!=4194304 or hashlib.sha256(baseline).hexdigest()!=BASELINE or hashlib.sha256(restore_source).hexdigest()!=RESTORE:raise ValueError('Exact original4MiB/historical restore source')
  self.terminal_validator=terminal_validator;self.baseline=baseline;self.restore_source=restore_source;self.source=source;self.clock=clock;self.cleanup_clock=cleanup_clock;self.first=None;self.calls={};self.facts={};self.started=False
 def latch(self,e):
  if self.first is None:self.first=e
 def check(self):
  if self.clock()>=self.end:raise TimeoutError('Original shared600s staging/retention/restoration endpoint exhausted')
 def once(self,name,fn,*args):
  if name in self.calls:raise ValueError('No repeated phase '+name)
  self.check();self.calls[name]=1;v=fn(*args,self.end);self.check();return v
 def run(self,*,originals,set_temporary,snapshot,stage,terminal_RAM,restore,basic_cleanup,profile_restore,retain):
  if self.started:raise ValueError('Single campaign object')
  self.started=True;self.end=self.clock()+600;owned_change=False;initial=False;original=None
  try:
   ram,inventory=self.once('originals',originals)
   if not isinstance(ram,bytes)or len(ram)!=65536 or not isinstance(inventory,dict):raise ValueError('Complete originals before mutations')
   original=copy.deepcopy(inventory);retain('original_RAM',ram);retain('original_inventory',copy.deepcopy(original));owned_change=True
   active=self.once('set_temporary',set_temporary,copy.deepcopy(original))
   if active.get('Turbo Control')!='Manual'or active.get('CPU Speed')!='64'or active.get('System Mode')!='PAL':raise ValueError('Exact temporary Manual64/PAL readback')
   before=self.once('initial_snapshot',snapshot,'initial');retain('initial4MiB',before)
   if before!=self.baseline:raise ValueError('Initial full4MiB is not exact original baseline')
   initial=True;self.once('stage',stage)
  except BaseException as e:self.latch(e)
  finally:
   try:
    if initial:
     raw=self.once('terminal_RAM',terminal_RAM);retain('terminal_RAM',raw);self.facts['terminal']=self.terminal_validator(raw)
     changed=self.once('changed_snapshot',snapshot,'changed');retain('changed4MiB',changed)
     if not isinstance(changed,bytes)or len(changed)!=4194304:raise ValueError('Complete changed4MiB before original restore')
     # One original-only restore, never a retry, only after knownquiet retention.
     restored=self.once('native_restore',restore);retain('restore_terminal_RAM',restored);resident_identity(restored,self.restore_source,True);done_mailbox(restored[0x6000:0x6020],self.baseline);self.facts['native_restore_known_closed']=True
     final=self.once('final_snapshot',snapshot,'final');retain('final4MiB',final)
     if final!=self.baseline:raise ValueError('Final complete4MiB comparison differs')
     self.facts['original4MiB_verified']=True
   except BaseException as e:self.latch(e)
   finally:
    try:
     if original is not None:
      # No reset of an uncertain writer. The callback must honor false by
      # observing/retaining only; that restriction is part of its frozen API.
      allow=bool(self.facts.get('native_restore_known_closed')or('native_restore'not in self.calls and self.facts.get('terminal',{}).get('known_closed')))
      end=self.cleanup_clock()+90;self.calls['basic_cleanup']=1;a,b,ack=basic_cleanup(allow,end);retain('BASIC_first_RAM',a);retain('BASIC_second_RAM',b)
      av,bv=basic_ready(a),basic_ready(b)
      if self.cleanup_clock()>=end or av is None or bv is None or av['jiffy']==bv['jiffy']or not isinstance(ack,dict)or ack.get('errors')!=[]:raise ValueError('Paired exact BASIC READY and final resume ACK required')
      self.facts['BASIC_cleanup_verified']=True;self.facts['BASIC_reset_allowed']=allow
    except BaseException as e:self.latch(e)
    finally:
     if owned_change:
      # Structurally independent even if core/BASIC orchestration aborts.
      try:
       end=self.cleanup_clock()+45;self.calls['profile_restore']=1;actual=profile_restore(copy.deepcopy(original),end)
       if self.cleanup_clock()>=end or actual!=original:raise ValueError('Exact original profile/inventory restoration not verified')
       self.facts['original_settings_verified']=True
      except BaseException as e:self.latch(e)
  report={'status':'passed'if self.first is None else'failed','facts':copy.deepcopy(self.facts),'calls':dict(self.calls),'shared_core_end':self.end,'profile_seconds_max':45,'execution_context':'enclosing validated purpose supplies physical/local context','callback_backends_not_automatically_qualified':True}
  if self.first is not None:
   try:self.first.preserved_stage_report=report
   except BaseException:pass
   raise self.first
  return report
