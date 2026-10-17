"""Actual accepted wire/stream/3880/BASIC/settings callbacks for PreservedStage.
Cold BASIC-only staging. Never claims native SETUP/CONFIG keyboard acceptance.
"""
import json,time,hashlib
from pathlib import Path
from put_session import Session
from cold_session import ColdSession,basic_ready
from transport import FIELDS
from driver import Driver
from changed_driver import ChangedDriver
from protocol import Source
from bound_release import BoundRelease,Release16Protocol,publish
from put_io import PutIO
from rest_io import Intersection
from stage_transport import StageClient
from startup import Startup
from preserved_stage import PreservedStage,closed_terminal

class Backend(Session):
 def __init__(self,wire,streams,baseline,out,*,stager,assets,contracts,release,**kw):
  if type(release)is not BoundRelease:raise ValueError("Typed source-pinned release16 successor required")
  self.release=release
  release.verify(assets,stager.home)
  super().__init__(wire,streams,baseline,out,contracts=contracts,**kw)
  self.stager=stager;self.assets={k:bytes(v)for k,v in assets.items()};self.cold_index=0;self.stage_result=None;self.stage_io=None;self.protocol=None;self.stage_terminal=None;self.machine=None;self.ready_pairs={};self.callback_result=None
 def retain(self,name,value):
  if name in ['initial4MiB','changed4MiB','final4MiB']:
   # Driver has already fsync'ed the exact archive before returning bytes.
   if (self.out/(name+'.bin')).read_bytes()!=value:raise ValueError('Retained stream archive changed')
  elif isinstance(value,bytes):self.save(name+'.bin',value)
  else:self.save(name+'.json',(json.dumps(value,indent=2)+'\n').encode())
 def originals_cb(self,end):
  self.audit.verify();self.source_audit_before=True
  self.before=self.tx('inventory_before',lambda:self.wire.inventory(self.bound(end,30)))
  if any(self.before['info'].get(k)!=v for k,v in FIELDS.items()):raise ValueError('Exact known device/firmware before takeover')
  cfg=self.before['configs/C64%20and%20Cartridge%20Settings']['C64 and Cartridge Settings']
  if cfg.get('Command Interface')!='Enabled'or cfg.get('RAM Expansion Unit')!='Enabled'or cfg.get('REU Size')not in ['4 MB','8 MB','16 MB']or cfg.get('REU Preload')!='Disabled':raise ValueError('Enabled configured4MiB-plus/no preload')
  self.tx('original_pause',lambda:self.wire.control('pause','original_pause',self.bound(end)))
  self.ram_before=self.tx('original_RAM',lambda:self.wire.ram('original_RAM',self.bound(end)))
  # This concrete purpose has no live-MAIN takeover authority. Stage5 is never
  # a substitute for known C CLOSE. Fresh native main => stop before reset/load.
  self.retain('preflight-original-RAM',self.ram_before);self.retain('preflight-inventory',self.before)
  if basic_ready(self.ram_before)is None:raise ValueError('BASIC-only purpose refuses live MAIN; use source-bound C-close purpose')
  self.originals=True;return self.ram_before,self.before
 def temporary_cb(self,original,end):
  self.wire.arm_turbo(original)
  self.tx('manual64_set',lambda:self.wire.configure_turbo('temporary',self.bound(end)))
  value=self.tx('manual64_readback',lambda:self.wire.turbo_settings(self.bound(end)))
  self.retain('temporary_profile_readback',value);v=value['U64 Specific Settings'];self.turbo_result['temporary_configuration_verified']=v.get('Turbo Control')=='Manual'and v.get('CPU Speed')=='64'and v.get('System Mode')=='PAL';return v
 def paired_ready(self,role,end):
  previous=None
  for i in range(64):
   p=f'{role}_{i}';self.tx(p+'_pause',lambda:self.wire.control('pause',p+'_pause',self.bound(end)))
   raw=self.tx(p+'_RAM',lambda:self.wire.ram(p+'_RAM',self.bound(end)));current=basic_ready(raw)
   if current is not None and previous is not None and current['jiffy']!=previous[0]['jiffy']:
    self.retain(role+'-READY-first',previous[1]);self.retain(role+'-READY-second',raw);self.ready_pairs[role]=(previous[1],raw);return raw
   previous=(current,raw)if current is not None else None
   self.tx(p+'_resume',lambda:self.wire.control('resume',p+'_resume',self.bound(end)));self.sleep(min(.02,max(0,end-self.clock())))
  raise TimeoutError('Finite64 strict BASIC readiness observations')
 def ready(self,role,parent):return self.paired_ready(role,parent)
 def preserve(self,role,parent):
  # Fast.enter('restore') delegates this source/retention boundary before reset.
  self.tx(role+'_pause',lambda:self.wire.control('pause',role+'_pause',self.bound(parent)))
  raw=self.tx(role+'_RAM',lambda:self.wire.ram(role+'_RAM',self.bound(parent)));self.retain(role+'-RAM',raw)
  if self.wire.role in self.streams:
   if raw[0x801:0x801+len(self.source)-2]!=self.source[2:]or self.wire._last_full is None or raw[0x3e00:0x3e34]!=self.wire._last_full[0x3e00-0x801:0x3e34-0x801]:raise ValueError('Exact source and terminal stream header before replacement')
  elif self.wire.role=='stage':closed_terminal(raw,self.stager)
  elif self.wire.role=='restore':
   from native_file import resident_identity,done_mailbox
   resident_identity(raw,self.wire.service,True);done_mailbox(raw[0x6000:0x6020],self.baseline)
  return raw
 def start_stream(self,role,end):
  if role!='initial':self.preserve('before_'+role,end)
  self.wire.cold_begin(role);self.source,self.nonce=self.streams[role]
  key=role+'_reset';self.tx(key,lambda:self.wire.control('reset',key,self.bound(end)))
  self.ready(role,end)
  self.tx(role+'_load',lambda:self.wire.load(self.bound(end)))
  ram=self.tx(role+'_loaded_RAM',lambda:self.wire.ram(role+'_loaded_RAM',self.bound(end)));self.source_gate(ram);self.retain(role+'-cold-source',ram)
  for field in ['header_zero','mailbox_zero']:
   self.tx(role+'_'+field,lambda field=field:self.wire.write(field,self.bound(end)))
  ram=self.tx(role+'_initialized_RAM',lambda:self.wire.ram(role+'_initialized_RAM',self.bound(end)));self.source_gate(ram,mailbox=True)
  if ram[0x3e00:0x3e34]!=bytes(52):raise ValueError('Exact unready stream header')
  for field in ['SYS_body','SYS_count']:
   self.tx(role+'_'+field,lambda field=field:self.wire.write(field,self.bound(end)))
   ram=self.tx(role+'_'+field+'_RAM',lambda field=field:self.wire.ram(role+'_'+field+'_RAM',self.bound(end)));self.source_gate(ram,mailbox=True,queued=field=='SYS_count')
   if ram[0x277:0x27f]!=b'SYS2061\r':raise ValueError('Exact SYS body readback before resume')
   self.retain(role+'-'+field,ram)
  self.tx(role+'_start_resume',lambda:self.wire.control('resume',role+'_start_resume',self.bound(end)));self.wire.started()
 def snapshot_cb(self,role,end):
  self.start_stream(role,end);source,nonce=self.streams[role];path=self.out/(role+'4MiB.bin');remaining=end-self.clock()
  cls=ChangedDriver if role=='changed'else Driver
  reader=cls(source,nonce,self.wire,path,self.baseline,clock=self.clock,sleep=self.sleep,cancel=self.cancel,whole=remaining);reader.end=min(end,reader.end);reader.frame_end=reader.end
  self.captures[role]={'output':str(path),'report':None,'original_core_end':end}
  try:self.captures[role]['report']=reader.run()
  finally:
   if getattr(reader,'report',None)is not None:self.captures[role]['report']=reader.report
  self.wire.finish_stream(path);return path.read_bytes()
 def stage_cb(self,end):
  self.preserve('before_stage',end);source=self.stager
  client=StageClient(self.wire,Intersection(self.clock,end,None))
  self.stage_io=PutIO(client,source,clock=self.clock,seconds=max(1,min(600,end-self.clock())),record=lambda row:self.retain('stage-transport-%06d'%len(self.stage_io.ledger_events),row))
  # Event names are monotone, even when a recorder or request raises.
  self.stage_io.ledger_events=[]
  def record(row):
   self.stage_io.ledger_events.append(row);self.retain('stage-transport-%06d'%len(self.stage_io.ledger_events),row)
  self.stage_io.record=record;client.io=self.stage_io;self.wire.begin_stage(self.stage_io)
  try:
   self.retain('stager-startup',Startup(self.stage_io,source,clock=self.clock,event=self.event).start())
   self.protocol=Release16Protocol(self.stage_io,source,clock=self.clock,seconds=max(1,min(600,end-self.clock())),event=self.event);self.protocol.deadline=min(self.protocol.deadline,end)
   files=self.out/'actual-files';files.mkdir()
   self.stage_result=publish(self.protocol,self.release,self.assets,lambda n,b:self.writer(files/n,b));self.retain('staging-result',self.stage_result)
   return self.stage_result
  finally:self.stage_io.restore_budget()
 def terminal_cb(self,end):
  # Cleanup requests bypass the latched wire failure, but never reissue a
  # source load, GO, or writer operation; unknown ownership stops replacement.
  self.wire.cleanup_mode=True
  raw=self.preserve('stager_terminal',end);self.stage_terminal=raw;closed_terminal(raw,self.stager);self.wire.accept_stage_terminal(raw);return raw
 def restore_cb(self,end):
  self.restore(end);return(self.out/'RAM-restore-DONE-paused.bin').read_bytes()
 def basic_cb(self,allow,end):
  self.wire.cleanup_mode=True
  self.tx('cleanup_terminal_pause',lambda:self.wire.control('pause','cleanup_terminal_pause',self.bound(end)))
  raw=self.tx('cleanup_terminal_RAM',lambda:self.wire.ram('cleanup_terminal_RAM',self.bound(end)));self.retain('cleanup-terminal-RAM',raw)
  if not allow or self.wire.reset_uncertain:raise ValueError('Unknown writer/reset: retain only; no reset or helper overwrite')
  self.tx('cleanup_reset',lambda:self.wire.control('reset','cleanup_reset',self.bound(end)));self.ready('cleanup',end)
  ack=self.tx('cleanup_resume',lambda:self.wire.control('resume','cleanup_resume',self.bound(end)));a,b=self.ready_pairs['cleanup'];return a,b,ack
 def profile_cb(self,original,end):
  self.wire.cleanup_mode=True;c={'errors':[]}
  # Existing reviewed structural profile restoration uses its passed absolute
  # endpoint. Inventory remains independent of a failed restoration ACK.
  try:
   if 'turbo_temporary'in self.wire.calls:self._restore_profile(c,end)
  finally:
   after=self.wire.inventory(self._restore_bound(end,30));self.retain('inventory-after',after)
  if c['errors']:raise self.first if self.first is not None else RuntimeError(repr(c['errors']))
  return after
 def run(self):
  self.machine=PreservedStage(self.baseline,self.wire.service,self.stager,clock=self.clock,cleanup_clock=self.wire.clock)
  try:
   self.callback_result=self.machine.run(originals=self.originals_cb,set_temporary=self.temporary_cb,snapshot=self.snapshot_cb,stage=self.stage_cb,terminal_RAM=self.terminal_cb,restore=self.restore_cb,basic_cleanup=self.basic_cb,profile_restore=self.profile_cb,retain=self.retain)
  except BaseException as e:self.first=e # PreservedStage owns the exact first cause across all callbacks.
  finally:
   try:self.audit.verify();self.source_audit_after=True
   except BaseException as e:self.latch(e)
   self.report={'status':'passed'if self.first is None else'failed','scope':'RELEASE16_OWNED_FILE_STAGING_ONLY','first_error':None if self.first is None else repr(self.first),'callback_report':self.callback_result or getattr(self.first,'preserved_stage_report',None),'source_before':self.source_audit_before,'source_after':self.source_audit_after,'stage':self.stage_result,'captures':self.captures,'source_load_ledgers':self.wire.source_loads,'stager_PUT_ledger':[]if self.stage_io is None else self.stage_io.ledger,'native_restore':self.native_result,'native_may_write':self.native_may_write,'native_known_closed':self.native_known_closed,'temporary_turbo':self.turbo_result,'original_CPU_RAM_application_restored':False,'SETUP_CONFIG_UI_executed':False,'START_DOS_executed':False,'FTP':0,'upper12MiB_access':False}
   try:self.retain('RESULT',self.report)
   except BaseException as e:
    self.latch(e);self.report.update(status='failed',first_error=repr(self.first),result_record_durable=False)
  if self.first is not None:raise self.first
  return self.report
