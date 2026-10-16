"""Bounded A+C native application, inherited strict mailbox/resident primitives."""
import bootstrap,json,time
from pathlib import Path
from ac_contract import Registration,sha,SERVICE_SHA
from ac_script import CollectionScript
import c64u_native_shadow_identity as shadow_identity
from c64u_native_application import Application,DIAG_SIZE,STAGE_RUN,STAGE_PAUSED,STAGE_FAILED,checked_seconds,checked_observation_interval
from c64u_probe import speed_option
from c64u_bulk_reu_recovery import Journal,dump,durable_write
from game_recovery import ApplicationBudget
from c64u_native_display_application import text_oracle,FONT_NAMES
class CollectionApplication(Application):
 def __init__(self,registration,configured,patch,floppy,hd,media,service,seconds=1800,observation_interval=2.0):
  if not isinstance(registration,Registration) or sha(service)!=SERVICE_SHA:raise ValueError('Exact purpose registration/original service required')
  expected,expected_patch=registration.configure(media,floppy,hd)
  if configured!=expected or patch!=expected_patch:raise ValueError('Constructor requires exact registered A+C configuration')
  self.registration=registration;self.prg=configured;self.patch=patch;self.labels=registration.labels;self.data=floppy;self.hd_source=hd;self.media=media;self.service_prg=service
  self.seconds=checked_seconds(seconds,10,1800,'A+C application deadline');self.observation_interval=checked_observation_interval(observation_interval)
  self.clock=time.monotonic;self.sleep=time.sleep;self.base=self.labels['dos64_native_diag'];self.resident_segments=registration.segments;self.build_identity=registration.build_identity
  font_paths=[]
  for name in FONT_NAMES:
   rows=[r for r in registration.proof['execution_source_closure'] if r['executed_source'].endswith('/assets/native-text/'+name)]
   if len(rows)!=1:raise ValueError('Exact paired font source proof required')
   font_paths.append(Path(rows[0]['immutable_copy']))
  self.fonts=tuple(path.read_bytes() for path in font_paths)
  self.shadow_build_metadata=registration.shadow_metadata;self.shadow_identity=shadow_identity.prepare(registration.blobs['dos64.prg'],self.labels,self.resident_segments,self.shadow_build_metadata)
  self.script=CollectionScript();self.observations=[];self.client=None;self.output=None;self.journal=None;self.deadline=None;self.app_upload_started=False
 def screen(self):
  value=super().screen();bda=self.read_paused(0x400,256);head=int.from_bytes(bda[0x1a:0x1c],'little');tail=int.from_bytes(bda[0x1c:0x1e],'little')
  if head not in range(0x1e,0x3e,2) or tail not in range(0x1e,0x3e,2):raise ValueError('Invalid BIOS keyboard queue')
  value['ring_used']=((tail-head)%32)//2;rows=value['text'].splitlines();value['prompt']=rows[value['cursor_row']][:value['cursor_column']].endswith('C>');return value
 def can_snapshot(self):
  self.client.put('machine:pause')
  if self.client.read(self.labels['hdb_active'],1)!=b'\0' or self.client.read(self.labels['hd_state'],1)==b'\1' or self.client.read(self.labels['dos64_files_state'],1)==b'\1' or self.client.read(self.labels['dos64_uci_state'],1) not in (b'\0',b'\x09',b'\x0a'):self.client.put('machine:resume');return False
  return True
 def __call__(self,client,output):
  self.client=client;self.output=Path(output);self.journal=Journal(self.output/'application-journal.jsonl');self.started=self.clock();self.deadline=self.started+self.seconds;previous=client.client.budget;primary=None;report={'status':'running','workflow':'genuineDOS A+C VER/DIR/BASIC/SYSTEM/TPC HELLO/COPY/reopen/CHKDSK','hardware_speed_request':'PAL Manual64','no_DOS_API_shortcuts':True}
  def remember(error,scope):
   nonlocal primary
   if primary is None:primary=error
   report.update(status='failed',error=repr(primary),error_type=type(primary).__name__)
   report.setdefault('errors',[]).append({'scope':scope,'error':repr(error),'type':type(error).__name__})
  try:
   client.client.budget=ApplicationBudget(self)
   durable_write(self.output/'native-owned.prg',self.prg);dump(self.output/'native-patch.json',self.patch);dump(self.output/'AC-media-input.json',self.media);dump(self.output/'runtime-symbols.json',self.labels)
   report['preflight']=self.preflight();options=client.get('configs/U64%20Specific%20Settings/CPU%20Speed')['U64 Specific Settings']['CPU Speed']['values'];client.configs({'U64 Specific Settings':{'Turbo Control':'Manual','CPU Speed':speed_option(options,64)}})
   active=client.get('configs/U64%20Specific%20Settings')['U64 Specific Settings']
   report['actual_active_turbo']=active
   if active.get('System Mode')!='PAL' or active.get('Turbo Control')!='Manual' or str(active.get('CPU Speed')).strip()!='64':raise ValueError('Verified actual PAL/Manual64 required')
   client.put('machine:pause');self.write(self.base,bytes(DIAG_SIZE));self.app_upload_started=True;client.request('POST','runners:run_prg',self.prg,'application/octet-stream');client.put('machine:resume');last=0
   while True:
    self.bound();diag=self.diag()
    if diag[0]==STAGE_FAILED:raise RuntimeError('Native failed: '+diag.hex())
    if diag[0]==STAGE_RUN and self.clock()-last>=self.observation_interval and self.can_snapshot():
     s=self.screen();last=self.clock();words=self.script.observe(s);dump(self.output/'collection-progress.json',self.script.result())
     if self.script.stage=='done':break
     self.command(3)
     for key in words:self.command(1,key=key)
    self.sleep(.05)
   report['original_RAM_sha256']=self.capture_ram('application-ram-before-retention.bin');ram=(self.output/'application-ram-before-retention.bin').read_bytes();report['resident_identity']=self.verify_resident(ram)
   bda=self.read_paused(0x400,256);cga=self.read_paused(0xb8000,16384);screen,bitmap,matrix=text_oracle(bda,cga,*self.fonts)
   if ram[0x4400:0x4800]!=self.fonts[0] or ram[0x4800:0x5000]!=self.fonts[1] or ram[0x6000:0x7f40]!=bitmap or ram[0x4000:0x43e8]!=matrix or (screen['mode'],screen['columns'])!=(3,80):raise ValueError('Complete native80column framebuffer/font oracle differs')
   durable_write(self.output/'final-BDA.bin',bda);durable_write(self.output/'final-CGA-16k.bin',cga);dump(self.output/'final-framebuffer-proof.json',{'passed':True,'bitmap_bytes':8000,'matrix_bytes':1000,'fonts_exact':True,'columns':80,'BDA_sha256':sha(bda),'CGA_sha256':sha(cga)})
   report['complete_framebuffer_passed']=True;report['status']='passed'
  except BaseException as error:
   remember(error,'application')
   try:self.capture_ram('application-first-failure-before-retention.bin')
   except BaseException as secondary:remember(secondary,'first_failure_capture')
  finally:
   report['previous_budget_restored']=False
   for attempt in range(1,4):
    try:
     client.client.budget=previous
     if client.client.budget is not previous:raise RuntimeError('Previous budget setter did not restore identity')
     report['previous_budget_restored']=True;report['previous_budget_restore_attempts']=attempt;break
    except BaseException as error:remember(error,'previous_budget_restore')
   else:report['previous_budget_restore_attempts']=3
   for attempt in range(1,4):
    try:dump(self.output/'application-result.json',report);break
    except BaseException as error:remember(error,'application_report')
  if primary is not None:raise primary.with_traceback(primary.__traceback__)
  return report
