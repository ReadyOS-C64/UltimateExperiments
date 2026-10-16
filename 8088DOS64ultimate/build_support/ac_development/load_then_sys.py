"""Narrow development startup adapter; no CLI, network or mutation on import."""
import hashlib,math,re,time
from urllib.parse import quote

ARTIFACTS={
 'original-split256':('d883c6789ea63345939008fe12e1c32782a51932603ac5e78f9d7453dbb20e98','17fac64117826615ef0ebd848b0f8f8d7f2f1f2d401674922613f6fa70136a6d'),
 'UID1-instrumentation':('4e2241d099d823c6326b2cfe4167930269f8d8f62f146b09bcc2596bca68de4d','f2b966494d2bcd7f46af1eb6a16261ce69a0b79a54d0c18b4f8f110768926c4f'),
}
def sha(b):return hashlib.sha256(b).hexdigest()
def contract(base,configured,labels_blob,purpose):
 if purpose not in ARTIFACTS or not all(isinstance(b,bytes)for b in [base,configured,labels_blob]):raise ValueError('Explicit immutable original or UID1 native contract required')
 if (sha(base),sha(labels_blob))!=ARTIFACTS[purpose] or (len(base),len(configured))!=(45057,45057):raise ValueError('Exact paired base native source/labels identity required')
 if len(base)!=45057 or len(configured)!=45057:raise ValueError('Complete configured native PRG required')
 labels={n:int(a,16)for a,n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)',labels_blob.decode(),re.M)}
 if labels['dos64_entry']!=2061 or base[:14]!=b'\x01\x08\x0b\x08\x0a\x00\x9e2061\x00\x00\x00':raise ValueError('Original BASIC SYS2061 source entry required')
 at=labels['dos64_native_config']-0x801+2;end=labels['dos64_native_config_end']-0x801+2
 if end-at!=142 or base[at:at+5]!=b'D64N\0' or configured[at:at+5]!=b'D64N\xa5':raise ValueError('Exact native cold configuration required')
 allowed={at+4,at+7}|set(range(at+10,at+142))
 if any(a!=b and i not in allowed for i,(a,b)in enumerate(zip(base,configured))):raise ValueError('Configured PRG changed outside reviewed original fixture patch')
 path_length=configured[at+7];raw=configured[at+14:at+142]
 if not 2<=path_length<=128 or raw[path_length-1]!=0 or any(raw[path_length:]):raise ValueError('Exact bounded NUL-terminated cold source path required')
 if not re.fullmatch(rb'/usb1/DOS64_TEST/[a-z0-9][a-z0-9_-]{0,63}/DOS33A\.IMG\0',raw[:path_length]):raise ValueError('Fresh owned original DOS source path required')
 if configured[at+10:at+14]!=(813107767).to_bytes(4,'little') or configured[at+5:at+7]!=b'\x04\x01' or configured[at+8:at+10]!=b'\x1c\xdf':raise ValueError('Reviewed original360KiB/4MiB/target1/DF1C cold fixture required')
 for name,want in [('dos64_cold_open',0xa5),('dos64_native_started',0)]:
  index=labels[name]-0x801+2
  if not 2<=index<len(configured) or configured[index]!=want:raise ValueError('Packaged cold/not-started guard differs')
 return {'purpose':purpose,'labels':labels,'configured_sha256':sha(configured),'source_sha256':sha(base),'sys_bytes':b'SYS2061\r'}

def basic_ready(ram):
 """Conservative actual KERNAL/BASIC screen+cursor+empty-buffer observation."""
 if not isinstance(ram,bytes) or len(ram)!=65536:raise ValueError('Full paused original RAM required')
 row=ram[0xd6];column=ram[0xd3];pointer=int.from_bytes(ram[0xd1:0xd3],'little')
 if ram[0x288]!=4 or ram[0x289]!=10 or not 1<=row<=24 or column!=0 or pointer!=0x400+40*row:return None
 if ram[0xc6]!=0:return None
 previous=bytes(v&0x7f for v in ram[pointer-40:pointer]);current=bytes(v&0x7f for v in ram[pointer:pointer+40])
 if previous[:6]!=bytes([18,5,1,4,25,46]) or previous[6:]!=b' '*34 or current!=b' '*40:return None
 return {'cursor_row':row,'cursor_column':column,'screen_row_pointer':pointer,'keyboard_count':0,'jiffy':int.from_bytes(ram[0xa0:0xa3],'big'),'ready_row_screen_codes':previous.hex(),'current_row_screen_codes':current.hex()}

class PhaseBudget:
 def __init__(self,clock,seconds,parent):self.clock=clock;self.deadline=clock()+seconds;self.parent=parent
 def remaining(self):
  left=self.deadline-self.clock()
  if self.parent is not None:left=min(left,self.parent.remaining())
  if left<=0:raise TimeoutError('Native load/BASIC-ready phase deadline; no fallback or retry')
  return left

class LoadThenSysClient:
 """Wrap a reviewed SaveClient; change only its exact application PRG launch.

 Recovery/service requests are delegated unchanged. The future full host must
 independently bind source/peer/staging and the repaired recovery orchestrator.
 This reusable mechanism is deliberately not a launchable hardware runner.
 """
 def __init__(self,delegate,base,configured,labels_blob,purpose,clock=time.monotonic,sleep=time.sleep,seconds=30,journal=lambda *a,**k:None):
  if isinstance(seconds,bool) or not isinstance(seconds,(int,float)) or not math.isfinite(seconds) or not 1<=seconds<=60:raise ValueError('Native launch phase must be finite1..60seconds')
  self.authority=contract(base,configured,labels_blob,purpose);self.delegate=delegate;self.configured=configured;self.clock=clock;self.sleep=sleep;self.seconds=seconds;self.journal=journal;self.events=[]
  self.path=delegate.paths.get(self.authority['configured_sha256'])
  if not isinstance(self.path,str) or not re.fullmatch(r'/usb1/DOS64_TEST/[a-z0-9][a-z0-9_-]{0,63}/NATIVE-DOS\.PRG',self.path):raise ValueError('Exact independently staged owned application PRG registry required')
  self.load_attempted=False;self.load_returned=False;self.sys_body_written=False;self.sys_go_attempted=False;self.sys_go_verified=False;self.start_resume_attempted=False;self.awaiting_start_resume=False;self.cancel_attempted=False
 def __getattr__(self,name):return getattr(self.delegate,name)
 def event(self,name,**fields):
  self.events.append({'event':name,**fields});self.journal(name,**fields)
 def put(self,route):
  if route=='machine:resume' and self.awaiting_start_resume:
   try:
    self.event('owned_SYS_resume_prepared',entry=2061)
    self.events.append({'event':'owned_SYS_resume_attempted','entry':2061})
   except BaseException as primary:
    try:self.cancel_unresumed_SYS()
    except BaseException as cleanup:
     try:self.event('owned_unresumed_SYS_cancel_failed',error=repr(cleanup))
     except BaseException:pass
    raise primary.with_traceback(primary.__traceback__)
   # No journal callback may fail between recording the attempt and dispatch.
   self.start_resume_attempted=True;self.awaiting_start_resume=False
  return self.delegate.put(route)
 def verify_loaded(self,ram):
  if not isinstance(ram,bytes) or len(ram)!=65536 or ram[0x801:0xa000]!=self.configured[2:0xa000-0x801+2]:raise ValueError('Visible loaded application PRG differs before any SYS')
  labels=self.authority['labels']
  if ram[labels['dos64_native_started']]!=0 or ram[labels['dos64_cold_open']]!=0xa5:raise ValueError('Application already started or cold guard is not live')
  # Conservatively exclude BASIC/KERNAL-hidden ranges at pre-SYS. Actual REST
  # mapping can be platform-dependent; a whole read does not prove hidden RAM.
  return {'visible_start':0x801,'visible_end_exclusive':0xa000,'visible_bytes_exact':0xa000-0x801,'visible_sha256':sha(ram[0x801:0xa000]),'cold_open_A5':True,'native_started_zero':True,'hidden_PRG_range':[0xa000,0xb800],'hidden_PRG_verified':False,'native_diag_preSYS_verified':False,'postENTRY_resident_shadow_SAVER_REU_closure_required':True}
 def write_SYS(self,address,data,budget):
  if not(address==0x277 and data==self.authority['sys_bytes'] or address==0xc6 and data in [b'\0',bytes([len(self.authority['sys_bytes'])])]):raise ValueError('Only exact owned SYS body/count writes are permitted')
  budget.remaining();result=self.delegate.client.put(f'machine:writemem?address={address:X}&data='+data.hex().upper());budget.remaining();return result
 def cancel_unresumed_SYS(self):
  if not self.sys_go_attempted or self.start_resume_attempted or self.cancel_attempted:return {'attempted':False}
  self.cancel_attempted=True
  previous=self.delegate.client.budget;budget=PhaseBudget(self.clock,30,None);self.delegate.client.budget=budget
  try:
   self.delegate.put('machine:pause');ram=self.delegate.read(0,65536);self.verify_loaded(ram)
   body=self.authority['sys_bytes'];count=ram[0xc6]
   if ram[0x277:0x277+len(body)]!=body or count not in [0,len(body)]:raise ValueError('Ambiguous SYS queue ownership; do not replace it')
   if count:
    self.write_SYS(0xc6,b'\0',budget)
    if self.delegate.read(0xc6,1)!=b'\0':raise ValueError('Owned SYS cancellation readback differs; no retry')
   self.awaiting_start_resume=False
   return {'attempted':bool(count),'owned_count_cleared':True,'native_was_not_resumed':True}
  finally:self.delegate.client.budget=previous
 def request(self,method,route,data=None,content_type=None):
  if method!='POST' or route!='runners:run_prg' or data!=self.configured:return self.delegate.request(method,route,data,content_type)
  if content_type!='application/octet-stream' or not isinstance(data,bytes):raise ValueError('Exact immutable application launch body required')
  if self.load_attempted:raise ValueError('Application load was already attempted; no retry')
  self.load_attempted=True;previous=self.delegate.client.budget;budget=PhaseBudget(self.clock,self.seconds,previous);self.delegate.client.budget=budget;primary=None
  try:
   budget.remaining();self.event('owned_application_load_attempted',path=self.path,sha256=self.authority['configured_sha256'],purpose=self.authority['purpose'])
   # The synchronous response is the completion boundary; no fixed delay.
   result=self.delegate.client.put('runners:load_prg?file='+quote(self.path,safe=''));budget.remaining()
   if not isinstance(result,dict) or result.get('errors')!=[]:raise ValueError('Explicit successful JSON errors=[] LOAD acknowledgement required; no SYS')
   self.load_returned=True
   self.event('owned_application_load_returned',autostart=False)
   previous_ready=None
   while True:
    budget.remaining();self.delegate.put('machine:pause');ram=self.delegate.read(0,65536);loaded=self.verify_loaded(ram);ready=basic_ready(ram)
    if ready is not None and previous_ready is not None and ready['jiffy']!=previous_ready['jiffy']:
     self.event('actual_BASIC_ready_confirmed',first=previous_ready,second=ready,loaded_source=loaded);break
    previous_ready=ready
    self.delegate.put('machine:resume');self.sleep(min(0.02,budget.remaining()))
   body=self.authority['sys_bytes'];self.write_SYS(0x277,body,budget);self.sys_body_written=True
   if self.delegate.read(0x277,len(body))!=body:raise ValueError('SYS body readback differs before count publication')
   if self.delegate.read(0xc6,1)!=b'\0':raise ValueError('BASIC keyboard buffer changed before owned count publication')
   self.sys_go_attempted=True;self.write_SYS(0xc6,bytes([len(body)]),budget)
   if self.delegate.read(0xc6,1)!=bytes([len(body)]) or self.delegate.read(0x277,len(body))!=body:raise ValueError('SYS count/body publication differs; never retry')
   self.sys_go_verified=True;self.awaiting_start_resume=True;self.event('owned_SYS_queued_while_paused',bytes=body.hex(),entry=2061)
   return result
  except BaseException as error:
   primary=error
   try:self.event('owned_application_load_failed',error=repr(error),load_returned=self.load_returned,sys_GO_attempted=self.sys_go_attempted)
   except BaseException:pass
   if self.sys_go_attempted and not self.start_resume_attempted:
    try:self.event('owned_unresumed_SYS_cancel',**self.cancel_unresumed_SYS())
    except BaseException as cleanup:
     try:self.event('owned_unresumed_SYS_cancel_failed',error=repr(cleanup))
     except BaseException:pass
   raise primary.with_traceback(primary.__traceback__)
  finally:self.delegate.client.budget=previous
