"""One autonomous native restore inside one original600-second endpoint."""
import json
from hybrid import Hybrid
from cold_session import ColdSession,basic_ready
from driver import Cancelled
from native_file import resident_identity,done_mailbox
class Fast(Hybrid):
 def __init__(self,*args,**kw):
  super().__init__(*args,**kw);self.core_end=None;self.native_result=None;self.native_may_write=False;self.native_known_closed=False;self.polls=0
 def source_gate(self,ram,mailbox=False,queued=False):
  if self.wire.role!='restore':return Hybrid.source_gate(self,ram,mailbox,queued)
  if len(ram)!=65536 or ram[0x801:0x801+len(self.source)-2]!=self.source[2:]:raise ValueError('Complete exact cold restore source before SYS')
  if mailbox and ram[0x6000:0x6020]!=bytes(32):raise ValueError('Exact postREADY DRF zero before SYS')
  if queued:
   if ram[0xc6]!=8 or ram[0x277:0x27f]!=b'SYS2061\r':raise ValueError('Exact count-last restore SYS')
  elif basic_ready(ram)is None:raise ValueError('Conservative READY before restore queue')
 def preserve(self,role,parent):
  # Capture before every reset. Restore source has exactly two permitted SMC
  # operand pairs; all other bytes remain immutable through DONE.
  self.tx(role+'_terminal_pause',lambda:self.wire.control('pause',role+'_terminal_pause',self.bound(parent)))
  ram=self.tx(role+'_terminal_RAM',lambda:self.wire.ram(role+'_terminal_RAM',self.bound(parent)))
  if len(ram)!=65536:raise ValueError('Full terminal RAM mandatory BEFORE reset')
  self.save('RAM-'+role+'-terminal-paused.bin',ram);self.save(role+'-terminal-source.bin',ram[0x801:0x801+len(self.source)-2])
  if self.wire.role=='restore':
   resident_identity(ram,self.source,terminal=True);done_mailbox(ram[0x6000:0x6020],self.baseline)
  else:
   if ram[0x801:0x801+len(self.source)-2]!=self.source[2:]:raise ValueError('Exact terminal stream source before helper reset')
   raw=self.wire._last_full
   if raw is None or ram[0x3e00:0x3e34]!=raw[0x3e00-0x801:0x3e34-0x801]:raise ValueError('Exact terminal stream header before restore')
 def enter(self,role,parent):
  if role!='restore':return Hybrid.enter(self,role,parent)
  if self.before['configs/C64%20and%20Cartridge%20Settings']['C64 and Cartridge Settings'].get('Command Interface')!='Enabled':raise ValueError('Enabled Command Interface required before native FILES; no repair')
  self.audit.verify();self.preserve('before_restore',parent);self.audit.verify()
  self.wire.cold_begin(role);self.source=self.wire.source
  self.tx(role+'_reset',lambda:self.wire.control('reset',role+'_reset',self.bound(parent)))
  self.ready(role,parent)
  self.tx(role+'_load',lambda:self.wire.load(self.bound(parent)))
  ram=self.tx(role+'_loaded_RAM',lambda:self.wire.ram(role+'_loaded_RAM',self.bound(parent)));self.source_gate(ram);self.save('RAM-restore-loaded-paused.bin',ram)
  self.tx(role+'_mailbox_zero',lambda:self.wire.write('mailbox_zero',self.bound(parent)))
  ram=self.tx(role+'_initialized_RAM',lambda:self.wire.ram(role+'_initialized_RAM',self.bound(parent)));self.source_gate(ram,mailbox=True);self.save('RAM-restore-initialized-paused.bin',ram)
  self.tx(role+'_SYS_body',lambda:self.wire.write('SYS_body',self.bound(parent)))
  ram=self.tx(role+'_body_RAM',lambda:self.wire.ram(role+'_body_RAM',self.bound(parent)));self.source_gate(ram,mailbox=True)
  if ram[0x277:0x27f]!=b'SYS2061\r':raise ValueError('Restore SYS body readback before count')
  self.tx(role+'_SYS_count',lambda:self.wire.write('SYS_count',self.bound(parent)))
  ram=self.tx(role+'_queued_RAM',lambda:self.wire.ram(role+'_queued_RAM',self.bound(parent)));self.source_gate(ram,mailbox=True,queued=True);self.save('RAM-restore-queued-paused.bin',ram)
  # Attempt flag BEFORE actual resume, no retry even on absent/ambiguous ACK.
  self.native_may_write=True
  self.tx(role+'_start_resume',lambda:self.wire.control('resume',role+'_start_resume',self.bound(parent)))
  self.wire.started()
  # Pause only for source attestation. No second SYS/resume-start or helper;
  # normal continuation resumes this same native invocation once.
  self.tx('restore_active_pause',lambda:self.wire.control('pause','restore_active_pause',self.bound(parent)))
  ram=self.tx('restore_active_RAM',lambda:self.wire.ram('restore_active_RAM',self.bound(parent)));self.save('RAM-restore-active-paused.bin',ram)
  resident_identity(ram,self.source);m=ram[0x6000:0x6020]
  if m[:4]!=b'DRF1'or m[4]not in [1,2]or m[5]or m[6]or m[7]not in [0,1,2,3,4,5,6,9]:raise ValueError('Fresh INIT/BUSY native source-bound authority required')
  self.save('restore-fresh-active-DRF.bin',m)
  self.tx('restore_continue_resume',lambda:self.wire.control('resume','restore_continue_resume',self.bound(parent)))
 def restore(self,end):
  self.enter('restore',end)
  for i in range(600):
   if self.cancel():raise Cancelled('Cancelled autonomous native restoration; no retry')
   d=self.bound(end,12);raw=self.tx('restore_poll_'+str(i),lambda:self.wire.read(0x6000,32,d));self.polls+=1
   self.save(f'restore-DRF-{i:03d}.bin',raw)
   if raw[:4]!=b'DRF1'or len(raw)!=32:raise ValueError('Exact live DRF source purpose')
   if raw[4]==0xa5:
    done_mailbox(raw,self.baseline)
    self.tx('restore_done_pause',lambda:self.wire.control('pause','restore_done_pause',self.bound(end)))
    ram=self.tx('restore_done_RAM',lambda:self.wire.ram('restore_done_RAM',self.bound(end)));self.save('RAM-restore-DONE-paused.bin',ram)
    resident_identity(ram,self.source,terminal=True);done_mailbox(ram[0x6000:0x6020],self.baseline)
    if ram[0x6000:0x6020]!=raw:raise ValueError('Immutable native DONE changed before source capture')
    self.native_known_closed=True;self.wire.restore_done=True
    self.native_result={'state':'DONE','sectors':8192,'bytes':4194304,'CRC_expected_actual_equal':True,'known_closed':True,'source_and_SMC_verified':True,'polls':self.polls,'one_attempt':True,'fresh_remote_backup_before_write':False}
    self.save('native-restore-receipt.json',(json.dumps(self.native_result,indent=2)+'\n').encode());return
   if raw[4]not in [1,2]or raw[5]or raw[6]or raw[7]not in [0,1,2,3,4,5,6,9]:raise ValueError('Native restore failed/ambiguous; preserve first cause, no retry')
   if self.clock()>=end:raise TimeoutError('Original600s restore endpoint')
   self.sleep(min(1,max(0,end-self.clock())))
  raise TimeoutError('Finite600 native mailbox polls under original deadline')
 def _cold_cleanup(self,c):
  if self.native_may_write and not self.native_known_closed:
   # Cannot reset/overwrite a potentially active writer. Pause and retain it;
   # profile/inventory cleanup still runs independently in inherited finally.
   try:
    self.wire.control('pause','unknown_restore_cleanup_pause',self._restore_bound(self.wire.clock()+15))
    ram=self.wire.ram('unknown_restore_terminal_RAM',self._restore_bound(self.wire.clock()+15));self.save('RAM-terminal-paused.bin',ram);c['terminal_RAM_retained']=True
    c['native_FILES_known_closed']=False;c['native_restore_may_remain_paused']=True
   except BaseException as e:self._cleanup_error(c,'unknown_restore_terminal',e)
   c['errors'].append({'phase':'cleanup_reset','not_attempted':'Native writer ownership not known closed; no reset/source overwrite/retry'});return
  return super()._cold_cleanup(c)
 def run(self):
  report={'status':'failed','report_scope':'FAST_NATIVE_FILE_RECOVERY_LIBRARY','cold_exclusive_session':True,'restore_span':[0,4194304],'historical_backup_adoption':True,'fresh_remote_file_prewrite_read':False,'original_CPU_RAM_application_restored':False,'upper12MiB_access':False,'FTP':0,'native_restore_attempts':0}
  try:
   self.audit.verify();self.source_audit_before=True;self.activate()
   self.core_end=self.clock()+600
   self.capture('initial',self.core_end)
   self.restore(self.core_end)
   self.capture('final',self.core_end)
   self.stream_result={'initial_complete':True,'final_complete':True,'native_done':True,'shared_core_seconds':600}
  except BaseException as e:self.latch(e)
  finally:
   try:self.cleanup()
   except BaseException as e:self.latch(e);self.cleanup_result['orchestration_error']=repr(e)
   try:self.audit.verify();self.source_audit_after=True
   except BaseException as e:self.latch(e)
   report.update(first_error=None if self.first is None else repr(self.first),first_type=None if self.first is None else type(self.first).__name__,core_end=self.core_end,captures=self.captures,native=self.native_result,native_restore_attempts=int(self.wire.restore_start_attempted),native_may_have_written=self.native_may_write,native_FILES_known_closed=self.native_known_closed,temporary_turbo=self.turbo_result,cleanup=self.cleanup_result,source_before=self.source_audit_before,source_after=self.source_audit_after,events=self.events,raw_write_responses=self.wire.write_receipts,wire_failures=self.wire.failure_receipts)
   if self.first is None and self.stream_result and self.source_audit_before and self.source_audit_after and all(self.cleanup_result.get(k)for k in ['terminal_RAM_retained','cold_reset_ack','BASIC_ready_observed','resume_ack','settings_media_equal','turbo_restore_ack','turbo_restored_observed']):report['status']='passed'
   try:self.save('RESULT.json',(json.dumps(report,indent=2)+'\n').encode())
   except BaseException as e:self.latch(e);report.update(status='failed',first_error=repr(self.first))
   self.report=report
  if self.first is not None:raise self.first
  if report['status']!='passed':raise RuntimeError('Incomplete fast native-file recovery')
  return report
