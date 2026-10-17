"""Exclusive hybrid qualification; source-gated existing helpers only.
All capture/transition/scratch/safety work shares ONE600s core endpoint.
"""
import json,hashlib
from pathlib import Path
from cold_session import ColdSession,basic_ready
from driver import Driver
from bulk_program import Program,Command,SCRATCH,CHUNK

class HybridProgram(Program):
 def __init__(self,baseline,out,capture,enter,**kw):
  super().__init__(None,baseline,out,**kw);self.capture=capture;self.enter=enter
 def run(self):
  if self.started:raise ValueError('One hybrid core; never rearm')
  self.started=True;self.core_end=self.clock()+600
  try:
   self.capture('initial',self.core_end);self.result['initial_complete']=True
   if self.left()<180:raise TimeoutError('Reserve180s before any pattern WRITE')
   self.service=self.enter('scratch',self.core_end)
   # Cold transition consumes the same budget; check reserve again BEFORE
   # firstpossible WRITE. No fresh600s endpoint is created by any callback.
   if self.left()<180:raise TimeoutError('Reserve180s after scratch cold entry')
   original=self.baseline[SCRATCH:SCRATCH+CHUNK];pattern=bytes(v^255 for v in original)
   self.may_changed=True
   self.command(0,SCRATCH,pattern,'pattern_WRITE')
   if self.command(1,SCRATCH,pattern,'pattern_READ')!=pattern:raise ValueError('Independent changed block readback')
   self.result['pattern_verified']=True
   self.command(0,SCRATCH,original,'original_WRITE')
   if self.command(1,SCRATCH,original,'original_READ')!=original:raise ValueError('Independent original block readback')
   self.restored=True;self.result['original_block_verified']=True
   self.capture('final',self.core_end);self.left();self.result['final_complete']=True
  except BaseException as e:
   if self.first is None:self.first=e
   raise
  return dict(self.result,shared_core_seconds=600,core_end=self.core_end,qualified_span=[SCRATCH,SCRATCH+CHUNK],upper12MiB_access=False)

class Hybrid(ColdSession):
 def __init__(self,wire,streams,baseline,out,*,contracts,**kw):
  super().__init__(wire,streams['initial'][0],streams['initial'][1],baseline,out,contract=contracts['initial'],**kw)
  self.streams=streams;self.contracts=contracts;self.program=None;self.captures={}
 def activate(self):
  self.wire.cold_begin('initial');super().activate();self.wire.started()
 def ready(self,role,parent):
  # Source-backed existing conservative predicate; exponential readiness
  # observations, eight maximum, avoid many earlystartup reads. No blind wait.
  previous=None
  for i in range(8):
   d=self.bound(parent);p=f'{role}_{i}'
   self.tx(p+'_pause',lambda:self.wire.control('pause',p+'_pause',d))
   ram=self.tx(p+'_RAM',lambda:self.wire.ram(p+'_RAM',d));current=basic_ready(ram)
   if current is not None and previous is not None and current['jiffy']>previous['jiffy']:
    self.save(role+'-READY-paused.bin',ram);return ram
   previous=current;self.tx(p+'_resume',lambda:self.wire.control('resume',p+'_resume',d));self.sleep(min(.05*(2**i),max(0,parent-self.clock())))
  raise TimeoutError('Eight observed BASIC readiness attempts')
 def source_gate(self,ram,mailbox=False,queued=False):
  if len(ram)!=65536 or ram[0x801:0x801+len(self.source)-2]!=self.source[2:]:raise ValueError('Complete exact active native cold source')
  if mailbox:
   if self.wire.role in self.streams:
    if ram[0x3f00:0x3f02]!=b'\0\0':raise ValueError('Exact zero stream ACK/cancel')
   elif ram[0x6000:0x6020]!=bytes(32):raise ValueError('Exact postREADY zero DRS')
  if queued:
   if ram[0xc6]!=8 or ram[0x277:0x27f]!=b'SYS2061\r':raise ValueError('Exact count-last SYS readback')
  elif basic_ready(ram)is None:raise ValueError('Actual BASIC empty keyboard before queue')
 def preserve(self,role,parent):
  self.tx(role+'_terminal_pause',lambda:self.wire.control('pause',role+'_terminal_pause',self.bound(parent)))
  ram=self.tx(role+'_terminal_RAM',lambda:self.wire.ram(role+'_terminal_RAM',self.bound(parent)))
  if len(ram)!=65536:raise ValueError('Complete terminal RAM BEFORE helper reset')
  self.save('RAM-'+role+'-terminal-paused.bin',ram)
  self.save(role+'-terminal-source.bin',ram[0x801:0x801+len(self.source)-2])
  self.save(role+'-terminal-mailboxes.bin',ram[0x3e00:0x3f02]+ram[0x6000:0x6020])
  # Retention is mandatory even if source is damaged. Its mismatch is recorded,
  # never used as permission to repeat the previous command/source.
  exact=ram[0x801:0x801+len(self.source)-2]==self.source[2:]
  self.event('terminal_before_phase_reset_durable',role=role,source_exact=exact)
  if not exact and role!='before_safety':raise ValueError('Terminal native source changed before normal phase transition')
  if role=='before_scratch':
   raw=self.wire._last_full
   if raw is None or ram[0x3e00:0x3e34]!=raw[0x3e00-0x801:0x3e34-0x801]:raise ValueError('Current terminal stream header differs before scratch')
  if role=='before_final':
   seq=4;m=ram[0x6000:0x6020];tail=SCRATCH.to_bytes(3,'little')+CHUNK.to_bytes(2,'little')+(seq^65535).to_bytes(2,'little')
   if m[:7]!=b'DRS1\xa5\0\1'or m[7:11]!=seq.to_bytes(2,'little')*2 or m[11:18]!=tail or m[18]:raise ValueError('Current native DRS4 differs before final stream')
 def enter(self,role,parent):
  self.audit.verify()
  self.preserve('before_'+role,parent)
  self.audit.verify()
  self.wire.cold_begin(role);self.source=self.wire.source
  key=role+'_reset';self.tx(key,lambda:self.wire.control('reset',key,self.bound(parent)))
  self.ready(role,parent)
  self.tx(role+'_load',lambda:self.wire.load(self.bound(parent)))
  ram=self.tx(role+'_loaded_RAM',lambda:self.wire.ram(role+'_loaded_RAM',self.bound(parent)));self.source_gate(ram);self.save('RAM-'+role+'-loaded-paused.bin',ram)
  if role in self.streams:self.tx(role+'_header_zero',lambda:self.wire.write('header_zero',self.bound(parent)))
  self.tx(role+'_mailbox_zero',lambda:self.wire.write('mailbox_zero',self.bound(parent)))
  ram=self.tx(role+'_initialized_RAM',lambda:self.wire.ram(role+'_initialized_RAM',self.bound(parent)));self.source_gate(ram,mailbox=True)
  if role in self.streams and ram[0x3e00:0x3e34]!=bytes(52):raise ValueError('Exact stream unready header')
  self.save('RAM-'+role+'-initialized-paused.bin',ram)
  self.tx(role+'_SYS_body',lambda:self.wire.write('SYS_body',self.bound(parent)))
  ram=self.tx(role+'_body_RAM',lambda:self.wire.ram(role+'_body_RAM',self.bound(parent)));self.source_gate(ram,mailbox=True)
  if ram[0x277:0x27f]!=b'SYS2061\r':raise ValueError('SYS body readback before count')
  self.tx(role+'_SYS_count',lambda:self.wire.write('SYS_count',self.bound(parent)))
  ram=self.tx(role+'_queued_RAM',lambda:self.wire.ram(role+'_queued_RAM',self.bound(parent)));self.source_gate(ram,mailbox=True,queued=True);self.save('RAM-'+role+'-queued-paused.bin',ram)
  self.tx(role+'_start_resume',lambda:self.wire.control('resume',role+'_start_resume',self.bound(parent)))
  if role not in self.streams:
   end=self.bound(parent,12)
   for _ in range(600):
    raw=self.wire.read(0x6000,32,end)
    if raw[:5]==b'DRS1\x11'and raw[5:11]==bytes(6):break
    if self.clock()>=end:raise TimeoutError('Fresh40fe ACK0')
    self.sleep(min(.01,max(0,end-self.clock())))
   else:raise TimeoutError('Finite fresh40fe READY observations')
  self.wire.started()
  if role not in self.streams:
   service=Command(self.wire,self.source,clock=self.clock,sleep=self.sleep);service.source_gate(parent);return service
 def capture(self,role,end):
  if role=='final':self.enter(role,end)
  source,nonce=self.streams[role];path=self.out/(role+'4MiB.bin')
  remaining=end-self.clock()
  if not 0<remaining<=600:raise TimeoutError('Original common core endpoint')
  reader=Driver(source,nonce,self.wire,path,self.baseline,clock=self.clock,sleep=self.sleep,cancel=self.cancel,whole=remaining)
  reader.end=min(reader.end,end);reader.frame_end=reader.end
  self.captures[role]={'output':str(path),'report':None,'original_core_end':end}
  try:self.captures[role]['report']=reader.run()
  finally:
   if getattr(reader,'report',None)is not None:self.captures[role]['report']=reader.report
  if self.clock()>=end:raise TimeoutError('Original capture endpoint after durable final validation')
  self.wire.finish_stream(path)
  if self.clock()>=end:raise TimeoutError('Original capture endpoint after immutable archive/source fence')
  return self.captures[role]
 def safety_cold(self,end):
  # First operation in enter is durable terminal preservation BEFORE reset.
  return self.enter('safety',end)
 def _cold_cleanup(self,c):
  # An ambiguous helper reset cannot authorize a secondreset. Preserve RAM
  # once, then independently restore config/inventory in inherited finally.
  if self.wire.reset_uncertain:
   try:self.preserve('cleanup_ambiguous_reset',self.clock()+90);c['terminal_RAM_retained']=True
   except BaseException as e:self._cleanup_error(c,'ambiguous_reset_terminal',e)
   c['errors'].append({'phase':'cleanup_reset','not_attempted':'Prior helper reset ambiguous; no retry'});return
  return super()._cold_cleanup(c)
 def run(self):
  report={'status':'failed','report_scope':'HYBRID_RECOVERY_LIBRARY','qualified_write_span':[SCRATCH,SCRATCH+CHUNK],'original_CPU_RAM_application_restored':False,'upper12MiB_access':False,'FTP':0,'UCI':0,'fullboard_reset':False}
  try:
   self.audit.verify();self.source_audit_before=True;self.activate()
   self.program=HybridProgram(self.baseline,self.out,self.capture,self.enter,clock=self.clock,cancel=self.cancel)
   self.stream_result=self.program.run()
  except BaseException as e:self.latch(e)
  finally:
   try:
    # Same reviewed safety boundary: LOCAL reentry only while actual attempt
    # remains false; never a repeated reset/descriptor/GO or renewed endpoint.
    for _ in range(2):
     try:
      if self.program is None or not self.program.may_changed or self.program.restored or self.program.safety_attempted:break
      self.wire.cleanup_mode=True;self.program.safety(lambda end:None,self.safety_cold)
     except BaseException as e:self.latch(e)
   finally:
    try:self.cleanup()
    except BaseException as e:self.latch(e);self.cleanup_result['orchestration_error']=repr(e)
   try:self.audit.verify();self.source_audit_after=True
   except BaseException as e:self.latch(e)
   report.update(first_error=None if self.first is None else repr(self.first),first_type=None if self.first is None else type(self.first).__name__,program=None if self.program is None else self.program.result,core_end=None if self.program is None else self.program.core_end,captures=self.captures,temporary_turbo=self.turbo_result,cleanup=self.cleanup_result,source_before=self.source_audit_before,source_after=self.source_audit_after,events=self.events,raw_write_responses=self.wire.write_receipts,wire_failures=self.wire.failure_receipts)
   if self.first is None and self.stream_result and self.stream_result['final_complete']and self.source_audit_before and self.source_audit_after and all(self.cleanup_result.get(k)for k in ['terminal_RAM_retained','cold_reset_ack','BASIC_ready_observed','resume_ack','settings_media_equal']):report['status']='passed'
   try:self.save('RESULT.json',(json.dumps(report,indent=2)+'\n').encode())
   except BaseException as e:self.latch(e);report.update(status='failed',first_error=repr(self.first))
   self.report=report
  if self.first is not None:raise self.first
  if report['status']!='passed':raise RuntimeError('Incomplete hybrid qualification')
  return report
