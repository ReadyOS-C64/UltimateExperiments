"""Retain all new authority before outer REU restoration; never hide first failure."""
import bootstrap,os
from pathlib import Path
from ac_contract import sha
from ac_filesystem import verify_collection
from ac_helper import HelperSession
from c64u_bulk_reu_recovery import SIZE,CHUNK,dump,durable_write
from c64u_native_file_recovery import Budget
from game_recovery import DeadlineDeltaService

def read_ftp(ftp,path,limit,budget):
 b=bytearray()
 def chunk(block):
  budget.remaining()
  if len(b)+len(block)>limit:raise ValueError('FTP exceeds exact bound')
  b.extend(block)
  if getattr(ftp,'sock',None):ftp.sock.settimeout(min(5,budget.remaining()))
 ftp.retrbinary('RETR '+path,chunk);budget.remaining();return bytes(b)
def ftp_snapshot(connect,media,floppy,output,budget):
 with connect(min(5,budget.remaining())) as ftp:
  owner=read_ftp(ftp,media['remote_directory']+'/OWNER.JSON',4096,budget)
  if sha(owner)!=media['marker_sha256']:raise ValueError('Owned dual-media marker changed')
  a=read_ftp(ftp,media['files']['floppy']['native_path'],len(floppy)+1,budget)
  if a!=floppy:raise ValueError('Read-only A source changed')
  raw=read_ftp(ftp,media['files']['hd']['native_path'],20*1024*1024+1,budget)
  if len(raw)!=20*1024*1024:raise ValueError('HD snapshot truncated')
 durable_write(Path(output),raw);return raw

def verify_overlay_sources(app,changed):
 package=app.shadow_build_metadata['package'];slot=package['slot_size'];sources=package['startup_sources'];base=package['reu_assets']
 if slot!=2048 or len(sources)!=7 or base!=0x340000 or len(changed)!=SIZE:raise ValueError('Seven complete immutable REU slots required')
 rows=[]
 for index,source in enumerate(sources):
  expected=app.prg[source-0x801+2:source-0x801+2+slot];at=base+index*slot
  if len(expected)!=slot or changed[at:at+slot]!=expected:raise ValueError('PostENTRY REU source differs slot'+str(index))
  rows.append({'slot':index,'source':source,'reu':at,'bytes':slot,'sha256':sha(expected),'complete_header_payload_tail':True})
 return {'passed':True,'slots':rows}
class ACRetention:
 def __init__(self,app,connect,helper_prg,helper_labels):self.app=app;self.connect=connect;self.helper_prg=helper_prg;self.helper_labels=helper_labels;self.used=False;self.interruption=None;self.final_HD=None
 def preflight(self):
  if self.used:raise ValueError('Retention cannot be reused')
 def run(self,client,prg,output,journal):
  self.used=True;out=Path(output);report={'status':'failed','original_RAM_retained':False,'full_changed_REU_retained':False,'full_changed_HD_retained':False,'native_target2_final_closed':False};primary=None;previous=client.client.budget;budget=Budget(self.app.clock,600);raw=None;changed=None;helper=None
  def remember(error,scope):
   nonlocal primary
   if primary is None:primary=error
   if self.interruption is None and isinstance(error,(KeyboardInterrupt,SystemExit)):self.interruption=error
   report.setdefault('errors',[]).append({'scope':scope,'error':repr(error),'type':type(error).__name__})
  try:
   client.client.budget=budget
   try:
    client.put('machine:pause');raw=client.read(0,65536)
    if len(raw)!=65536:raise ValueError('Complete original RAM required before first destructive helper')
    durable_write(out/'original-before-retention.bin',raw);report['original_RAM_retained']=True
    if self.app.app_upload_started:report['resident_identity']=self.app.verify_resident(raw)
    h=self.app.labels['hdc_config']-0x801+2;at=self.app.labels['hdc_state_start']
    if raw[at:at+136]!=self.app.prg[h+4:h+140]:raise ValueError('Resident enabled D64H path/geometry/readonly differs')
    report['resident_HD_config_exact']=True
   except BaseException as error:remember(error,'original_RAM')
   # Capture complete visible changed HD independently even on failed native execution.
   try:
    pre=ftp_snapshot(self.connect,self.app.media,self.app.data,out/'HD-before-native-close.img',budget);report['full_preclose_HD_retained']=True;report['preclose_HD_sha256']=sha(pre)
   except BaseException as error:remember(error,'FTP_preclose')
   if raw is not None and len(raw)==65536:
    try:
     service=DeadlineDeltaService(client,prg,journal,clock=self.app.clock,sleep=self.app.sleep);service.load();changed=bytearray(SIZE)
     partial=out/'reu-changed-before-restoration.partial.bin';ranges=[]
     with partial.open('xb') as stream:
      for address in range(0,SIZE,CHUNK):
       budget.remaining();block=service.command(1,address,CHUNK)
       if len(block)!=CHUNK:raise ValueError('Changed REU block incomplete')
       changed[address:address+CHUNK]=block;stream.write(block);stream.flush();os.fsync(stream.fileno());ranges.append({'address':address,'bytes':len(block),'sha256':sha(block)})
       dump(out/'reu-partial-valid-ranges.json',{'complete':False,'ranges':ranges})
     service.check_code()
     if partial.read_bytes()!=bytes(changed):raise ValueError('Complete retained REU local readback differs')
     partial.rename(out/'reu-changed-before-restoration.bin');dump(out/'reu-partial-valid-ranges.json',{'complete':True,'ranges':ranges});report['full_changed_REU_retained']=True;report['changed_REU_sha256']=sha(changed)
     floppy=bytes(changed[0x100000:0x100000+368640]);durable_write(out/'A-changed-before-restoration.img',floppy)
     if floppy!=self.app.data:raise ValueError('Guest REU A changed unexpectedly')
     if self.app.app_upload_started:report['all_seven_sources']=verify_overlay_sources(self.app,changed)
    except BaseException as error:remember(error,'full_REU')
   else:report['destructive_helpers_skipped_for_missing_original_RAM']=True
   if report['full_changed_REU_retained'] and report['original_RAM_retained']:
    try:
     helper=HelperSession(client,self.helper_prg,self.helper_labels,clock=self.app.clock,sleep=self.app.sleep);report['native_close_reopen']=helper.load()
     latest=ftp_snapshot(self.connect,self.app.media,self.app.data,out/'HD-after-native-close-reopen.img',budget);report['full_changed_HD_retained']=True;self.final_HD=latest
     fs=verify_collection(self.app.hd_source,latest,complete=self.app.script.stage=='done');report['filesystem']=fs
     sectors=set(fs['changed_sectors'])|{0,1,16,80,0x1000000//512,len(latest)//512-1};receipts=[]
     for sector in sorted(sectors):
      budget.remaining();offset=sector*512;actual=helper.command(1,offset,512)
      if actual!=latest[offset:offset+512]:raise ValueError('Native reopened selected sector differs: '+str(sector))
      receipts.append({'sector':sector,'bytes':len(actual),'sha256':sha(actual)})
     for offset,count in [(len(latest)-1,2),(len(latest),2)]:
      actual=helper.command(1,offset,count)
      if actual!=latest[offset:offset+count]:raise ValueError('Exact20MiB short/EOF boundary differs')
     report['native_readback']={'passed':True,'all_changed_sectors_plus_boundary_sectors':receipts,'exact_20MiB_short_and_EOF':True,'not_full20MiB_native_byte_comparison':True}
     helper.command(2);report['native_target2_final_closed']=True
    except BaseException as error:remember(error,'native_CLOSE_reopen_readback')
    finally:
     if helper is not None:
      try:
       client.put('machine:pause');box=helper.mailbox()
       if not report['native_target2_final_closed'] and box[4] in (0x11,0xa5) and box[31]!=0xa5:helper.command(2);report['native_target2_final_closed']=True
       elif box[4]==0xe1 and box[8]==0:report['native_target2_final_closed']=True;report['helper_failed_but_cleanup_known_closed']=True
       durable_write(out/'HD-helper-final-mailbox.bin',helper.mailbox());durable_write(out/'HD-helper-final-RAM.bin',client.read(0,65536))
      except BaseException as error:remember(error,'helper_bounded_final_close')
   try:
    closed=ftp_snapshot(self.connect,self.app.media,self.app.data,out/'HD-final-before-outer-restoration.img',budget)
    if self.final_HD is None or closed!=self.final_HD:raise ValueError('Full independent FTP snapshot changed after readonly native reopened reads/finalCLOSE')
    report['independent_FTP_after_native_final_close_exact']=True
   except BaseException as error:remember(error,'FTP_after_final_close')
  except BaseException as error:remember(error,'retention_unexpected_or_budget_install')
  finally:
   # Local property restoration has a finite independent bound. Never retry a
   # remote command here or let a later interruption replace the first error.
   report['previous_budget_restored']=False
   for attempt in range(1,4):
    try:
     client.client.budget=previous
     if client.client.budget is not previous:raise RuntimeError('Previous budget setter did not restore identity')
     report['previous_budget_restored']=True;report['previous_budget_restore_attempts']=attempt;break
    except BaseException as error:remember(error,'previous_budget_restore')
   else:report['previous_budget_restore_attempts']=3
   if hasattr(client,'helper'):
    try:
     launch=client.helper;dump(out/'HD-helper-load-SYS-handoff.json',{'authority':{k:v.hex() if isinstance(v,bytes) else v for k,v in launch.authority.items() if k!='labels'},'events':launch.events,'load_returned':launch.load_returned,'SYS_count_verified':launch.sys_go_verified,'start_resume_attempted':launch.start_resume_attempted,'load_attempted':launch.load_attempted,'entire_visible_helper_verified_preSYS':any(e.get('event')=='actual_BASIC_ready_confirmed' and e.get('loaded_source',{}).get('all_helper_bytes_exact') is True for e in launch.events),'original_RAM_and_full_REU_retained_before_attempt':report['original_RAM_retained'] and report['full_changed_REU_retained']})
    except BaseException as error:remember(error,'helper_load_SYS_evidence')
   required=['original_RAM_retained','full_changed_REU_retained','full_changed_HD_retained','native_target2_final_closed','independent_FTP_after_native_final_close_exact','resident_HD_config_exact','previous_budget_restored']
   report['status']='passed' if primary is None and all(report.get(k) for k in required) and report.get('all_seven_sources',{}).get('passed') and self.app.script.stage=='done' else 'failed'
   if self.interruption is not None:report['cancelled']=True
   for attempt in range(1,4):
    try:
     dump(out/'AC-retention-result.json',report);break
    except BaseException as error:
     remember(error,'retention_report');report['status']='failed'
     if self.interruption is not None:report['cancelled']=True
  if primary is not None:raise primary.with_traceback(primary.__traceback__)
  return report
