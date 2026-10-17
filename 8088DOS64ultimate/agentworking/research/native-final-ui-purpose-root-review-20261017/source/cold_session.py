"""LOCAL cold exclusive session. Never restores an arbitrary previous program.
No device call is reachable from the hard-blocked launcher in this package.
"""
from pathlib import Path
import json,time,os,hashlib,zlib
from transport import FIELDS
from driver import Driver,Cancelled

def durable(path,data):
 with Path(path).open('xb')as f:
  if f.write(data)!=len(data):raise IOError('Durable preservation short write')
  f.flush();os.fsync(f.fileno())

def basic_ready(ram):
 # Exact conservative screen/cursor/empty keyboard predicate copied from the
 # previously reviewed LOAD/SYS adapter; raw01 is diagnostic, not bank authority.
 if len(ram)!=65536:raise ValueError('Full RAM count')
 row=ram[0xd6];column=ram[0xd3];pointer=int.from_bytes(ram[0xd1:0xd3],'little')
 if ram[0x288]!=4 or ram[0x289]!=10 or not 1<=row<=24 or column!=0 or pointer!=0x400+40*row or ram[0xc6]!=0:return None
 previous=bytes(v&0x7f for v in ram[pointer-40:pointer]);current=bytes(v&0x7f for v in ram[pointer:pointer+40])
 if previous!=bytes([18,5,1,4,25,46])+b' '*34 or current!=b' '*40:return None
 return {'jiffy':int.from_bytes(ram[0xa0:0xa3],'big'),'row':row,'port01_observation':ram[1]}

def native_contract(template,source,labels,nonce):
 if hashlib.sha256(template).hexdigest()!='dbe059f4ccdc727815eb78cdd811002789e20ca523923d5a40b5c75fba5d0e50':raise ValueError('Exact sealed native template')
 s={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in labels.splitlines()if l.startswith('al ')}
 if len(nonce)!=16 or not any(nonce):raise ValueError('Owned nonce')
 at=s['_rs_config']-0x801+2;expected=bytearray(template);expected[at:at+24]=b'\xa5RS1'+(0x400000).to_bytes(4,'little')+nonce
 rti=s['ps_rti'];i=rti-0x801+2
 if source!=expected or s['stream_entry']!=0x80d or not 2<=i<len(source)or source[i]!=0x40:raise ValueError('Only exact owner/4MiB/nonce patch and linked RTI')
 return {'entry':2061,'rti':rti,'sha256':hashlib.sha256(source).hexdigest(),'bytes':len(source),'reu_read_span':[0,0x400000],'REU_writes':0}

class FrozenSources:
 def __init__(self,files):
  self._pins=tuple(sorted((str(p),str(h))for p,h in files.items()))
  if not self._pins or any(len(h)!=64 or any(c not in '0123456789abcdef'for c in h)for p,h in self._pins):raise ValueError('Exact source pins')
 def verify(self):
  for p,h in self._pins:
   if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:raise ValueError('Frozen source/authority changed '+p)
  return len(self._pins)

class ColdSession:
 def __init__(self,wire,source,nonce,baseline,out,*,contract,audit,clock=time.monotonic,sleep=time.sleep,cancel=lambda:False,writer=durable,driver=Driver):
  if len(baseline)!=0x400000 or hashlib.sha256(baseline).hexdigest()!='ac43c06b5e23774b298011c1a97bfbc72eb8395020465c747b135a83e9cd3eb3':raise ValueError('Original ac43 complete baseline')
  if contract['sha256']!=hashlib.sha256(source).hexdigest()or contract['entry']!=2061:raise ValueError('Source-bound cold contract')
  if not isinstance(audit,FrozenSources):raise ValueError('Typed frozen source authority required')
  self.audit=audit;self.source_audit_before=False;self.source_audit_after=False
  self.wire=wire;self.source=source;self.nonce=nonce;self.baseline=baseline;self.out=Path(out);self.clock=clock;self.sleep=sleep;self.cancel=cancel;self.writer=writer;self.driver=driver;self.contract=contract;self.first=None;self.events=[];self.attempts=set();self.originals=False;self.before=None;self.ram_before=None;self.stream_result=None;self.turbo_result={'physical_CPU_frequency_measured':False};self.cleanup_result={};self.out.mkdir(exist_ok=False);self.wire.archive_failure=self.archive_wire_failure;self.wire.archive_write=self.archive_wire_write
 def archive_wire_write(self,item,body):
  name=f'HTTP-write-response-{item["index"]:03d}'
  self.save(name+'.bin',body);self.save(name+'.json',(json.dumps(dict(item,durable=True),indent=2)+'\n').encode())
 def archive_wire_failure(self,item,body):
  name=f'HTTP-failure-{item["index"]:03d}'
  self.save(name+'.bin',body);self.save(name+'.json',(json.dumps(dict(item,durable=True),indent=2)+'\n').encode())
 def save(self,name,data):self.writer(self.out/name,data)
 def event(self,name,**fields):
  item={'event':name,'time':self.clock(),**fields};self.events.append(item)
  # All events before a mutation must durably precede its attempt flag/call.
  self.save(f'event-{len(self.events):04d}.json',(json.dumps(item)+'\n').encode())
 def latch(self,e):
  if self.first is None:self.first=e
 def tx(self,key,fn):
  if not self.wire.cleanup_mode and self.cancel():raise Cancelled('Local cancellation before '+key)
  self.event('transaction_prepared',key=key)
  if key in self.attempts:raise ValueError('Transaction already attempted')
  self.attempts.add(key);return fn()
 def bound(self,parent,seconds=15):
  d=min(parent,self.clock()+seconds)
  if d<=self.clock():raise TimeoutError('Original cold-session deadline')
  return d
 def ready(self,role,parent):
  previous=None
  for i in range(64):
   d=self.bound(parent);p=f'{role}_{i}'
   self.tx(p+'_pause',lambda:self.wire.control('pause',p+'_pause',d));ram=self.tx(p+'_RAM',lambda:self.wire.ram(p+'_RAM',d));r=basic_ready(ram)
   if r is not None and previous is not None and r['jiffy']!=previous['jiffy']:
    self.save(role+'-READY-paused.bin',ram);return ram
   previous=r;self.tx(p+'_resume',lambda:self.wire.control('resume',p+'_resume',d));self.sleep(min(.02,max(0,parent-self.clock())))
  raise TimeoutError('Finite64 BASIC readiness observations')
 def source_gate(self,ram,mailbox=False,queued=False):
  if len(ram)!=65536 or ram[0x801:0x801+len(self.source)-2]!=self.source[2:]:raise ValueError('Complete cold native source equality before SYS')
  if mailbox and ram[0x3f00:0x3f02]!=b'\0\0':raise ValueError('Exact initialized ACK/cancel')
  if queued:
   if ram[0xc6]!=8 or ram[0x277:0x27f]!=b'SYS2061\r':raise ValueError('Exact count-last SYS readback')
  elif basic_ready(ram)is None:raise ValueError('Actual BASIC ready/empty queue required')
 def activate(self):
  end=self.clock()+90
  self.before=self.tx('inventory_before',lambda:self.wire.inventory(self.bound(end,30)))
  if any(self.before['info'].get(k)!=v for k,v in FIELDS.items()):raise ValueError('Identity before pause')
  initial_turbo=self.before['configs/U64%20Specific%20Settings'].get('U64 Specific Settings',{})
  if initial_turbo.get('System Mode')!='PAL'or initial_turbo.get('Turbo Control')!='C64U Turbo Registers'or initial_turbo.get('CPU Speed')!='64':raise ValueError('Exact initial PAL/register-control64 profile required before pause')
  cfg=self.before['configs/C64%20and%20Cartridge%20Settings'].get('C64 and Cartridge Settings',{})
  if cfg.get('RAM Expansion Unit')!='Enabled'or cfg.get('REU Size')not in ['4 MB','8 MB','16 MB']or cfg.get('REU Preload')!='Disabled':raise ValueError('Configured enabled4MiB-plus REU with preload disabled required; configuration is not capacity detection')
  self.save('inventory-before.json',(json.dumps(self.before,indent=2)+'\n').encode())
  self.tx('original_pause',lambda:self.wire.control('pause','original_pause',self.bound(end)))
  self.ram_before=self.tx('original_RAM',lambda:self.wire.ram('original_RAM',self.bound(end)))
  if len(self.ram_before)!=65536:raise ValueError('Exact original paused RAM')
  self.save('RAM-original-paused.bin',self.ram_before);self.originals=True
  self.event('originals_durable',RAM_sha256=hashlib.sha256(self.ram_before).hexdigest(),CPU_registers_retained=False,resumable_original=False)
  pair=self.wire.arm_turbo(self.before);self.turbo_result['captured_original']={'Turbo Control':pair[0],'CPU Speed':pair[1]}
  self.tx('manual64_set',lambda:self.wire.configure_turbo('temporary',self.bound(end)))
  active=self.tx('manual64_readback',lambda:self.wire.turbo_settings(self.bound(end)))
  v=active.get('U64 Specific Settings',{})
  self.save('turbo-temporary-readback.json',(json.dumps(active,indent=2)+'\n').encode())
  if v.get('System Mode')!='PAL'or v.get('Turbo Control')!='Manual'or v.get('CPU Speed')!='64':raise ValueError('Exact temporary PAL/Manual64 readback required')
  self.turbo_result['temporary_configuration_verified']=True

  self.tx('cold_reset',lambda:self.wire.control('reset','cold_reset',self.bound(end)));self.events.append({'event':'cold_reset_returned'})
  self.ready('cold',end)
  self.tx('load',lambda:self.wire.load(self.bound(end)))
  ram=self.tx('loaded_RAM',lambda:self.wire.ram('loaded_RAM',self.bound(end)));self.source_gate(ram);self.save('RAM-loaded-paused.bin',ram)
  self.tx('header_zero',lambda:self.wire.write('header_zero',self.bound(end)))
  self.tx('mailbox_zero',lambda:self.wire.write('mailbox_zero',self.bound(end)))
  ram=self.tx('initialized_RAM',lambda:self.wire.ram('initialized_RAM',self.bound(end)));self.source_gate(ram,mailbox=True)
  if ram[0x3e00:0x3e34]!=bytes(52):raise ValueError('Exact unready header initialization')
  self.save('RAM-initialized-paused.bin',ram)
  self.tx('SYS_body',lambda:self.wire.write('SYS_body',self.bound(end)))
  ram=self.tx('body_RAM',lambda:self.wire.ram('body_RAM',self.bound(end)));self.source_gate(ram,mailbox=True)
  if ram[0x277:0x27f]!=b'SYS2061\r':raise ValueError('SYS body readback before count')
  self.tx('SYS_count',lambda:self.wire.write('SYS_count',self.bound(end)))
  ram=self.tx('queued_RAM',lambda:self.wire.ram('queued_RAM',self.bound(end)));self.source_gate(ram,mailbox=True,queued=True);self.save('RAM-SYS-queued-paused.bin',ram)
  self.tx('start_resume',lambda:self.wire.control('resume','start_resume',self.bound(end)))
 def _cleanup_error(self,c,phase,error):
  self.latch(error);c['errors'].append({'phase':phase,'error':repr(error)})
 def _cold_cleanup(self,c):
  end=self.clock()+90
  def phase(name,fn):
   try:return self.tx(name,fn)
   except BaseException as e:self.latch(e);c['errors'].append({'phase':name,'error':repr(e)});return None
  paused=phase('cleanup_pause',lambda:self.wire.control('pause','cleanup_pause',self.bound(end)))
  if paused is not None:
   ram=phase('terminal_RAM',lambda:self.wire.ram('terminal_RAM',self.bound(end)))
   if ram is not None:
    try:
     if len(ram)!=65536:raise ValueError('Terminal RAM exact count')
     self.save('RAM-terminal-paused.bin',ram);c['terminal_RAM_retained']=True
    except BaseException as e:self.latch(e);c['errors'].append({'phase':'terminal_RAM_durable','error':repr(e)})
  # Never erase terminal evidence before capture, or retry an ambiguous first reset.
  reset_ambiguous='cold_reset'in self.attempts and not any(e['event']=='cold_reset_returned'for e in self.events)
  if c['terminal_RAM_retained']and not reset_ambiguous:
   reset=phase('cleanup_reset',lambda:self.wire.control('reset','cleanup_reset',self.bound(end)))
   if reset is not None:
    c['cold_reset_ack']=True
    ready=phase('cleanup_ready',lambda:self.ready('cleanup',end))
    if ready is not None:
     c['BASIC_ready_observed']=True
     resume=phase('cleanup_resume',lambda:self.wire.control('resume','cleanup_resume',self.bound(end)))
     c['resume_ack']=resume is not None
  elif reset_ambiguous:c['errors'].append({'phase':'cleanup_reset','not_attempted':'Original cold reset was ambiguous; no retry'})
 def _restore_bound(self,parent,seconds=15):
  # Use the transport's original timebase, independently of a failed cold
  # orchestration clock callback. All operations share this absolute endpoint.
  now=self.wire.clock();d=min(parent,now+seconds)
  if d<=now:raise TimeoutError('Original independent configuration cleanup deadline')
  return d
 def _configuration_event(self,key,**fields):
  item={'event':'transaction_prepared','time':self.wire.clock(),'key':key,**fields};self.events.append(item)
  self.save(f'event-{len(self.events):04d}.json',(json.dumps(item)+'\n').encode())
 def _restore_profile(self,c,end):
  c.update(turbo_restore_attempted=False,turbo_restore_ack=False,turbo_restored_observed=False)
  try:
   try:
    pair=self.wire._turbo_original
    self._configuration_event('cleanup_turbo_restore',captured_original={'Turbo Control':pair[0],'CPU Speed':pair[1]})
   except BaseException as e:self._cleanup_error(c,'turbo_restore_journal',e)
   try:
    self.wire.configure_turbo('restore',self._restore_bound(end));c['turbo_restore_ack']=True
   except BaseException as e:self._cleanup_error(c,'turbo_restore',e)
   finally:c['turbo_restore_attempted']='turbo_restore'in self.wire.calls
  finally:
   # Readback remains an independent attempt even if restoration or its
   # surrounding frame raises. It cannot convert an ambiguous POST to success.
   try:
    observed=self.wire.turbo_settings(self._restore_bound(end));v=observed.get('U64 Specific Settings',{});pair=self.wire._turbo_original
    self.save('turbo-restored-readback.json',(json.dumps(observed,indent=2)+'\n').encode())
    c['turbo_restored_observed']=v.get('System Mode')=='PAL'and v.get('Turbo Control')==pair[0]and v.get('CPU Speed')==pair[1]
    if not c['turbo_restored_observed']:raise ValueError('Exact captured original turbo pair not observed')
   except BaseException as e:self._cleanup_error(c,'turbo_restore_readback',e)
   self.turbo_result.update(restore_attempted=c['turbo_restore_attempted'],restore_ack=c['turbo_restore_ack'],restored_observed=c['turbo_restored_observed'])
 def _configuration_cleanup(self,c):
  # One finite endpoint, never replenished by POST/readback/inventory failure.
  end=self.wire.clock()+45
  try:
   if 'turbo_temporary'in self.wire.calls:
    try:self._restore_profile(c,end)
    except BaseException as e:self._cleanup_error(c,'turbo_restore_orchestration',e)
  finally:
   try:
    try:self._configuration_event('inventory_after')
    except BaseException as e:self._cleanup_error(c,'inventory_after_journal',e)
    after=self.wire.inventory(self._restore_bound(end,30))
    self.save('inventory-after.json',(json.dumps(after,indent=2)+'\n').encode());c['settings_media_equal']=all(after[k]==self.before[k]for k in self.before if k!='info')and all(after['info'].get(k)==v for k,v in FIELDS.items())
    if not c['settings_media_equal']:raise ValueError('Settings/media/device changed; no unreviewed repair writes')
   except BaseException as e:self._cleanup_error(c,'inventory_after',e)
 def cleanup(self):
  c={'attempted':False,'terminal_RAM_retained':False,'cold_reset_ack':False,'BASIC_ready_observed':False,'resume_ack':False,'settings_media_equal':False,'original_RAM_restored':False,'original_CPU_restored':False,'original_application_resumed':False,'errors':[]}
  self.cleanup_result=c
  if not self.originals:return
  c['attempted']=True;self.wire.cleanup_mode=True
  try:
   try:self._cold_cleanup(c)
   except BaseException as e:self._cleanup_error(c,'cold_cleanup_orchestration',e)
  finally:
   # Configuration ownership/onceflags and captured pair live on the wire,
   # independent of aborted cold-cleanup frames or public report fields.
   self.wire.cleanup_mode=True
   try:self._configuration_cleanup(c)
   except BaseException as e:self._cleanup_error(c,'configuration_cleanup_orchestration',e)
 def run(self):
  report={'status':'failed','report_scope':'COLD_READONLY_LIBRARY','cold_exclusive_session':True,'REU_writes':0,'FTP':0,'upper12MiB_access':False}
  try:
   self.audit.verify();self.source_audit_before=True
   self.activate();self.stream_result=self.driver(self.source,self.nonce,self.wire,self.out/'lower4MiB.bin',self.baseline,clock=self.clock,sleep=self.sleep,cancel=self.cancel).run()
  except BaseException as e:self.latch(e)
  finally:
   try:self.cleanup()
   except BaseException as e:self.latch(e);self.cleanup_result['orchestration_error']=repr(e)
   try:self.audit.verify();self.source_audit_after=True
   except BaseException as e:self.latch(e)
   report.update(temporary_turbo=self.turbo_result,write_response_receipts=self.wire.write_receipts,wire_failures=self.wire.failure_receipts,source_audit_before=self.source_audit_before,source_audit_after=self.source_audit_after,first_error=None if self.first is None else repr(self.first),stream=self.stream_result,cleanup=self.cleanup_result,events=self.events,attempted=sorted(self.attempts))
   if self.first is None and self.stream_result and self.stream_result.get('whole4MiB_exact')and all(self.cleanup_result.get(k)for k in ['terminal_RAM_retained','cold_reset_ack','BASIC_ready_observed','resume_ack','settings_media_equal']):report['status']='passed'
   try:self.save('RESULT.json',(json.dumps(report,indent=2)+'\n').encode())
   except BaseException as e:self.latch(e);report['status']='failed';report['first_error']=repr(self.first)
   self.report=report
  if self.first is not None:raise self.first
  if report['status']!='passed':raise RuntimeError('Incomplete cold cleanup; remains reserved')
  return report
