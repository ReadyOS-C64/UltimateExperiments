"""Purpose authority supplied by constructor; reviewed load-only mechanism unchanged."""
import bootstrap,re,time,math
from load_then_sys import LoadThenSysClient
from ac_contract import Registration,sha
class ACLoadThenSysClient(LoadThenSysClient):
 def __init__(self,delegate,registration,configured,patch,media,floppy,hd,clock=time.monotonic,sleep=time.sleep,seconds=30,journal=lambda *a,**k:None):
  if not isinstance(registration,Registration):raise ValueError('Exact constructor-bound A+C authority required')
  expected,expected_patch=registration.configure(media,floppy,hd)
  if configured!=expected or patch!=expected_patch:raise ValueError('Exact constructor-bound A+C authority required')
  if isinstance(seconds,bool) or not isinstance(seconds,(int,float)) or not math.isfinite(seconds) or not 1<=seconds<=60:raise ValueError('Bounded launch phase required')
  self.authority={'purpose':'genuineDOS33-A-plus20MiB-C-originalTP701','labels':registration.labels,'configured_sha256':sha(configured),'source_sha256':sha(registration.blobs['dos64.prg']),'sys_bytes':b'SYS2061\r','native_purpose_proof_sha256':registration.proof_sha,'floppy_sha256':registration.proof['media']['interactive_BOOT_A_sha256'],'HD_sha256':registration.proof['media']['HD_sha256']}
  self.delegate=delegate;self.configured=configured;self.clock=clock;self.sleep=sleep;self.seconds=seconds;self.journal=journal;self.events=[]
  self.path=delegate.paths.get(self.authority['configured_sha256'])
  if not isinstance(self.path,str) or not re.fullmatch(r'/usb1/DOS64_TEST/[a-z0-9][a-z0-9_-]{0,63}/NATIVE-DOS\.PRG',self.path):raise ValueError('Exact independently staged configured PRG required')
  self.load_attempted=False;self.load_returned=False;self.sys_body_written=False;self.sys_go_attempted=False;self.sys_go_verified=False;self.start_resume_attempted=False;self.awaiting_start_resume=False;self.cancel_attempted=False
