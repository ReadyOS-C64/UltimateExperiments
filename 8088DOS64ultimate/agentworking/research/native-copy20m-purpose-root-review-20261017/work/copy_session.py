"""Single fresh baseline→fixed freshdir→COPY/fullread→fresh baseline lifecycle.
Cold-exclusive; no REUwrite/restore or previous CPU/application restoration.
"""
from pathlib import Path
import json,time,hashlib
from cold_session import ColdSession,basic_ready
from hybrid import Hybrid
from driver import Driver as StreamDriver
from copy_reader_host import Driver as FileDriver
class ReaderIO:
 def __init__(self,session,end):self.s=session;self.w=session.wire;self.end=end;self.paused=False;self.terminal=False;self.last=None;self.full_frames=set()
 def _bound(self):return self.s.bound(self.end,15)
 def _wait(self,terminal):
  n=self.w.reader_next;delay=.02
  for i in range(64):
   if self.w.header_polls>=8192:raise TimeoutError('Finite8192 fileheader observations')
   self.w.header_polls+=1;raw=self.s.tx('file_header_'+str(self.w.header_polls),lambda:self.w.read(0x200,141,self._bound()));self.s.save(f'file-poll-{self.w.header_polls:04d}.bin',raw)
   r=raw[0x70:0x8d];h=raw[:48]
   if r[:4]==b'CCR1'and r[5]:raise RuntimeError('Published native file firstcause '+str(r[5]))
   wanted=False
   if h[5]in[2,4]:
    v=self.w.reader.header(h)
    if terminal:wanted=v['state']==4 and v['frame']==640 and v['count']==0 and v['read']==20971520
    else:wanted=v['state']==2 and v['frame']==n and v['offset']==(n-1)*32768 and v['count']==32768 and v['read']==n*32768
    if not wanted and h!=self.last:raise ValueError('Stale/forged/interleaved fileheader')
   elif h!=bytes(48)and(h[:5]!=b'CFR1\1'or h[5]!=1):raise ValueError('Unknown filepublication state')
   if wanted:
    if terminal:
     stack=self.s.tx('file_terminal_stack_'+str(i),lambda:self.w.read(self.w.reader.at('sp'),2,self._bound()))
     if stack!=b'\xff\xcf':continue
    key='file_terminal_pause'if terminal else'file_frame_pause_'+str(n)
    self.s.tx(key,lambda:self.w.control('pause',key,self._bound()));self.paused=True;self.w.reader_polled=h;return
   self.s.sleep(min(delay,max(0,self.end-self.s.clock())));delay=min(.5,delay*2)
  raise TimeoutError('Finite64 fileheader observations for one frame')
 def ready(self,end):self._wait(False)
 def done(self,end):self.terminal=True;self._wait(True)
 def read(self,a,n):
  if not self.paused:raise ValueError('Paused file RAM/ACK readback only')
  if(a,n)==(0,65536):
   key='file_terminal_RAM'if self.terminal else'file_frame_RAM_'+str(self.w.reader_next);raw=self.s.tx(key,lambda:self.w.ram(key,self._bound()))
   if raw[0x200:0x230]!=self.w.reader_polled:raise ValueError('Immutable fileframe changed before fullGET')
   if not self.terminal:
    number=self.w.reader_next
    if number in self.full_frames:raise ValueError('No repeated ambiguous fullframeGET')
    self.full_frames.add(number);b=self.w.reader.frame(raw,number)
    if b!=self.w.expected[(number-1)*32768:number*32768]:raise ValueError('Independent wholefile source bytes mismatch')
    self.w.reader_frames.add(number);self.w.reader_full=raw
    if number in[1,512,513,640]:self.s.save(f'RAM-file-frame-{number:03d}.bin',raw)
    row={'frame':number,'offset':(number-1)*32768,'count':32768,'header':raw[0x200:0x230].hex(),'result':raw[0x270:0x28d].hex(),'source_span_sha256':hashlib.sha256(raw[self.w.reader.low:self.w.reader.high]).hexdigest(),'payload_sha256':hashlib.sha256(b).hexdigest(),'source_private_gate':True}
    self.s.save(f'file-frame-{number:03d}.json',(json.dumps(row,indent=2)+'\n').encode())
   else:self.s.save('RAM-file-terminal-paused.bin',raw);self.w.reader_full=raw
   return raw
  if(a,n)not in[(0x260,4),(0x263,1)]:raise ValueError('Only exact paused frame ACK fields')
  return self.w.read(a,n,self._bound())
 def write(self,a,b):return self.w.reader_write(a,b,self._bound())
 def resume(self):
  if not self.paused or self.terminal:raise ValueError('Only same pending fileframe resume')
  n=self.w.reader_next;self.last=self.w.reader_polled;v=self.s.tx('file_frame_resume_'+str(n),lambda:self.w.control('resume','file_frame_resume_'+str(n),self._bound()));self.paused=False;self.w.reader_next+=1;return v
class CopySession(Hybrid):
 def __init__(self,*args,entry,**kw):
  self.entry=entry;self.entry_fact=None;self.core_end=None;self.file_result=None;self.directory_result=None;super().__init__(*args,**kw);self.wire._baseline=self.baseline;self.wire.archive_request=lambda v:self.save(f'HTTP-request-plan-{v["index"]:05d}.json',(json.dumps(v,indent=2)+'\n').encode())
 def save(self,name,data):
  super().save(name,data)
  if name=='RAM-original-paused.bin':
   self.entry_fact=self.entry.admit(data);super().save('cold-entry-admission.json',(json.dumps(self.entry_fact,indent=2)+'\n').encode())
 def ready(self,role,end):return ColdSession.ready(self,role,end)
 def source_gate(self,ram,mailbox=False,queued=False):
  if self.wire.role in self.streams:return Hybrid.source_gate(self,ram,mailbox,queued)
  if len(ram)!=65536 or ram[0x801:0x801+len(self.source)-2]!=self.source[2:]:raise ValueError('Exact cold configured native source')
  if mailbox and ram[0x260:0x264]!=bytes(4):raise ValueError('Cold cancellation/ACK fields must be zero')
  if queued:
   if ram[0xc6]!=8 or ram[0x277:0x27f]!=b'SYS2061\r':raise ValueError('Count-last SYS readback')
  elif basic_ready(ram)is None:raise ValueError('Strict BASIC empty queue before SYS')
 def preserve(self,role,end):
  self.tx(role+'_pause',lambda:self.wire.control('pause',role+'_pause',self.bound(end)));raw=self.tx(role+'_RAM',lambda:self.wire.ram(role+'_RAM',self.bound(end)));self.save('RAM-'+role+'-paused.bin',raw)
  if self.wire.role in self.streams:
   if raw[0x801:0x801+len(self.source)-2]!=self.source[2:]or self.wire._last_full is None or raw[0x3e00:0x3e34]!=self.wire._last_full[0x3e00-0x801:0x3e34-0x801]:raise ValueError('Previous exact terminal snapshot/source before replacement')
  elif self.wire.role=='directory':self.wire.directory.receipt(raw)
  elif self.wire.role=='reader':self.wire.reader.terminal(raw)
 def enter(self,role,end):
  self.audit.verify();self.preserve('before_'+role,end);self.wire.cold_begin(role);self.source=self.wire.source
  self.tx(role+'_reset',lambda:self.wire.control('reset',role+'_reset',self.bound(end)));self.ready(role,end)
  self.tx(role+'_load',lambda:self.wire.load(self.bound(end)))
  raw=self.tx(role+'_loaded_RAM',lambda:self.wire.ram(role+'_loaded_RAM',self.bound(end)));self.source_gate(raw);self.save('RAM-'+role+'-loaded.bin',raw)
  for field in ['header_zero','mailbox_zero']:self.tx(role+'_'+field,lambda field=field:self.wire.write(field,self.bound(end)))
  raw=self.tx(role+'_initialized_RAM',lambda:self.wire.ram(role+'_initialized_RAM',self.bound(end)));self.source_gate(raw,mailbox=True)
  lo,n=(0x3e00,52)if role in self.streams else(0x200,84 if role=='directory'else 48)
  if raw[lo:lo+n]!=bytes(n):raise ValueError('Exact unready header zero readback')
  self.save('RAM-'+role+'-initialized.bin',raw)
  self.tx(role+'_SYS_body',lambda:self.wire.write('SYS_body',self.bound(end)));raw=self.tx(role+'_SYS_body_RAM',lambda:self.wire.ram(role+'_SYS_body_RAM',self.bound(end)));self.source_gate(raw,mailbox=True)
  if raw[0x277:0x27f]!=b'SYS2061\r':raise ValueError('SYS body readback before count')
  self.tx(role+'_SYS_count',lambda:self.wire.write('SYS_count',self.bound(end)));raw=self.tx(role+'_queued_RAM',lambda:self.wire.ram(role+'_queued_RAM',self.bound(end)));self.source_gate(raw,mailbox=True,queued=True);self.save('RAM-'+role+'-queued.bin',raw)
  self.tx(role+'_start_resume',lambda:self.wire.control('resume',role+'_start_resume',self.bound(end)));self.wire.started()
 def directory(self):
  self.enter('directory',self.core_end);end=min(self.core_end,self.clock()+45)
  for i in range(128):
   raw=self.tx('directory_poll_'+str(i),lambda:self.wire.read(0x200,84,self.bound(end)));self.save(f'directory-poll-{i:03d}.bin',raw)
   if raw[:4]==b'DPR1'and raw[5]:raise RuntimeError('Native directory firstcause '+str(raw[5]))
   if raw[:5]==b'DPR1\4':
    stack=self.tx('directory_stack_'+str(i),lambda:self.wire.read(self.wire.directory.at('sp'),2,self.bound(end)))
    if stack!=b'\xff\xcf':continue
    self.tx('directory_done_pause',lambda:self.wire.control('pause','directory_done_pause',self.bound(end)));ram=self.tx('directory_done_RAM',lambda:self.wire.ram('directory_done_RAM',self.bound(end)));self.save('RAM-directory-DONE.bin',ram);self.directory_result=self.wire.directory_done(ram);self.save('directory-receipt.json',(json.dumps(self.directory_result,indent=2)+'\n').encode());return
   self.sleep(min(.05,max(0,end-self.clock())))
  raise TimeoutError('Finite directory receipt observations')
 def read_file(self):
  if self.core_end-self.clock()<=180:raise TimeoutError('Required180s before fixed fileCOPY with120s finalcapture reserve')
  self.enter('reader',self.core_end)
  end=self.core_end-120
  if end<=self.clock():raise TimeoutError('Original file phase bound')
  io=ReaderIO(self,end);target=self.out/'DOSHD-independent20MiB.img';out=target.open('xb')
  def retain(n,b):
   if out.write(b)!=len(b):raise OSError('Durable complete file chunk shortwrite')
   out.flush();import os;os.fsync(out.fileno())
  try:self.file_result=FileDriver(io,self.wire.reader,clock=self.clock,seconds=min(600,end-self.clock())).run(retain,self.wire.expected)
  finally:out.close()
  self.wire.reader_done(self.wire.reader_full,target);self.save('file-receipt.json',(json.dumps(self.file_result,indent=2)+'\n').encode())
 def _cold_cleanup(self,c):
  # ONE absolute endpoint includes owner retention/cancel, reset and BASIC.
  # Configuration finally remains independently bounded by the inherited45s.
  end=self.wire.clock()+90;c['cold_cleanup_absolute_endpoint']=end
  def phase(name,fn):
   try:return self.tx(name,fn)
   except BaseException as e:self._cleanup_error(c,name,e);return None
  paused=phase('cleanup_pause',lambda:self.wire.control('pause','cleanup_pause',self._restore_bound(end)))
  ram=None
  if paused is not None:
   ram=phase('terminal_RAM',lambda:self.wire.ram('terminal_RAM',self._restore_bound(end)))
   if ram is not None:
    try:
     if len(ram)!=65536:raise ValueError('Complete terminal RAM before reset')
     self.save('RAM-terminal-paused.bin',ram);c['terminal_RAM_retained']=True
    except BaseException as e:self._cleanup_error(c,'terminal_RAM_durable',e);ram=None
  if not self.wire.files_quiet and ram is not None:
   try:
    if self.wire.role=='reader':
     try:self.wire.reader_failed_quiet(ram)
     except ValueError:
      # Only a fresh exact healthy WAIT frame grants one cancellation. Unknown
      # COPY/CLOSE/CWD or published-failed BUSY state grants no replacement.
      self.wire.reader_cancel(ram,self._restore_bound(end));self.tx('owned_cancel_resume',lambda:self.wire.control('resume','owned_cancel_resume',self._restore_bound(end)))
      for i in range(64):
       raw=self.tx('owned_cancel_poll_'+str(i),lambda:self.wire.read(0x200,141,self._restore_bound(end)))
       if raw[0x70:0x75]==b'CCR1\xff':
        stack=self.tx('owned_cancel_stack_'+str(i),lambda:self.wire.read(self.wire.reader.at('sp'),2,self._restore_bound(end)))
        if stack==b'\xff\xcf':break
       self.sleep(min(.02,max(0,end-self.wire.clock())))
      else:raise TimeoutError('Finite64 owned cancel observations')
      self.tx('owned_cancel_pause',lambda:self.wire.control('pause','owned_cancel_pause',self._restore_bound(end)));ram=self.tx('owned_cancel_terminal_RAM',lambda:self.wire.ram('owned_cancel_terminal_RAM',self._restore_bound(end)));self.save('RAM-owned-cancel-terminal.bin',ram);self.wire.reader_failed_quiet(ram)
    elif self.wire.role=='directory':self.wire.directory_done(ram)
   except BaseException as e:self._cleanup_error(c,'native_owner_retention_or_cancel',e)
  c['native_FILES_known_quiet']=self.wire.files_quiet
  if not self.wire.files_quiet:
   c['errors'].append({'phase':'cleanup_reset','not_attempted':'FILES/create/COPY/CLOSE/CWD ownership not proven quiet; no reset/loader/retry'});return
  if self.wire.reset_uncertain:
   c['errors'].append({'phase':'cleanup_reset','not_attempted':'Prior reset ambiguous; no retry'});return
  if c['terminal_RAM_retained']:
   reset=phase('cleanup_reset',lambda:self.wire.control('reset','cleanup_reset',self._restore_bound(end)))
   if reset is not None:
    c['cold_reset_ack']=True
    ready=phase('cleanup_ready',lambda:self.ready('cleanup',end))
    if ready is not None:
     c['BASIC_ready_observed']=True;c['resume_ack']=phase('cleanup_resume',lambda:self.wire.control('resume','cleanup_resume',self._restore_bound(end)))is not None
 def run(self):
  report={'status':'failed','scope':'OWNED_COPY20M_READONLY_VERIFICATION','REU_write_operations':0,'upper12MiB_access':False,'upper12MiB_byte_equality':False,'original_CPU_RAM_application_restored':False,'FTP':0,'guest_execution':False,'copy_content_authority':False}
  try:
   self.audit.verify();self.source_audit_before=True;self.activate();self.core_end=self.clock()+600;self.capture('initial',self.core_end);self.directory();self.read_file();self.capture('final',self.core_end);self.stream_result={'initial_complete':True,'final_complete':True}
  except BaseException as e:self.latch(e)
  finally:
   try:self.cleanup()
   except BaseException as e:self.latch(e);self.cleanup_result['orchestration_error']=repr(e)
   try:self.audit.verify();self.source_audit_after=True
   except BaseException as e:self.latch(e)
   report.update(first_error=None if self.first is None else repr(self.first),first_type=None if self.first is None else type(self.first).__name__,captures=self.captures,directory=self.directory_result,file=self.file_result,files_quiet=self.wire.files_quiet,core_end=self.core_end,temporary_turbo=self.turbo_result,cleanup=self.cleanup_result,source_before=self.source_audit_before,source_after=self.source_audit_after,events=self.events)
   needed=['terminal_RAM_retained','cold_reset_ack','BASIC_ready_observed','resume_ack','settings_media_equal','turbo_restore_ack','turbo_restored_observed']
   if self.first is None and self.stream_result and self.wire.reader_receipt and self.source_audit_before and self.source_audit_after and all(self.cleanup_result.get(k)for k in needed):report.update(status='passed',copy_content_authority=True,whole_lower4MiB_equal_before_after=True)
   try:self.save('RESULT.json',(json.dumps(report,indent=2)+'\n').encode())
   except BaseException as e:self.latch(e);report.update(status='failed',first_error=repr(self.first),copy_content_authority=False)
   self.report=report
  if self.first is not None:raise self.first
  if report['status']!='passed':raise RuntimeError('Incomplete ownedcopy/read/closure remains reserved')
  return report
