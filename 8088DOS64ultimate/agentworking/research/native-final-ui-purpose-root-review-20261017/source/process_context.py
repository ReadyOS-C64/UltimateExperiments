from pathlib import Path
import os,time,stat,json,hashlib
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
_CONTEXT_TOKEN=object()
def _binding(m):return hashlib.sha256(json.dumps(m,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class ProcessContext:
 __slots__=('__physical','terminal','child','supervisor','manifest_sha','__binding')
 def __init__(self,token,physical,terminal,child,supervisor,manifest_sha,binding):
  if token is not _CONTEXT_TOKEN:raise ValueError('Context factory required')
  self.__physical=physical;self.terminal=terminal;self.child=child;self.supervisor=supervisor;self.manifest_sha=manifest_sha;self.__binding=binding
 @property
 def physical(self):return self.__physical
 def check(self,m):
  if self.__binding!=_binding(m):raise ValueError('Validated context manifest changed')

def local_context(m,sha='LOCAL_TEST_MANIFEST'):
 return ProcessContext(_CONTEXT_TOKEN,False,'LOCAL_TEST',101,100,sha,_binding(m))

def physical_context(m,msha):
 terminal=os.environ.get('DOS64_TERMINAL_WINDOW','')
 if not terminal.isdecimal()or os.getsid(0)!=os.getpid()or any(os.isatty(i)for i in [0,1,2])or not stat.S_ISCHR(os.fstat(0).st_mode)or os.fstat(0).st_rdev!=os.stat('/dev/null').st_rdev:raise ValueError('Truly detached owned child/session/devnull/logs required')
 detached=Path(m['detached']);end=time.monotonic()+2
 for _ in range(200):
  if (detached/'child.json').exists():break
  if time.monotonic()>=end:raise TimeoutError('Local supervisor metadata handshake')
  time.sleep(.01)
 if not Path(m['dispatch_claim']).is_dir()or not Path(m['supervisor_pidfile']).is_file():raise ValueError('Owned dispatch wrapper claim/PID required')
 child=json.loads((detached/'child.json').read_text());parent=json.loads((detached/'supervisor.json').read_text())
 if child.get('pid')!=os.getpid()or child.get('supervisor_pid')!=os.getppid()or parent.get('pid')!=os.getppid()or child.get('terminal')!=terminal or parent.get('terminal')!=terminal or parent.get('manifest_sha256')!=msha or parent.get('entry')!=m['entry'] or child.get('new_session')is not True or child.get('stdin')!='/dev/null':raise ValueError('Exact owned supervisor/child context')
 if int(Path(m['supervisor_pidfile']).read_text())!=os.getppid():raise ValueError('Owned dispatch supervisor PID differs')
 log=Path(child['stdout_stderr'])
 if log!=detached/'child.log':raise ValueError('Exact owned child log path')
 s=log.stat()
 if any((os.fstat(fd).st_dev,os.fstat(fd).st_ino)!=(s.st_dev,s.st_ino)for fd in [1,2]):raise ValueError('Owned redirected stdout/stderr required')
 return ProcessContext(_CONTEXT_TOKEN,True,terminal,os.getpid(),os.getppid(),msha,_binding(m))

class Ledger:
 def __init__(self,m,ctx):self.m=m;self.ctx=ctx;self.active=Path(m['active']);self.claimed=False;self.value=None
 def write(self,**fields):
  if self.claimed:
   current=json.loads(self.active.read_text())
   if current.get('session_id')!=self.m['session_id']or current.get('owned_child_pid')!=self.ctx.child:raise ValueError('Hardware ownership changed; never overwrite foreign state')
  else:
   if self.active.read_bytes()!=Path(self.m['predecessor']).read_bytes():raise ValueError('Atomic predecessor changed before ownership claim')
   self.value={'schema':1,'hardware_owner':'cia_probe_independent_review','hardware_reserved':True,'session_id':self.m['session_id'],'run':self.m['run'],'purpose':'V1_NATIVE_SETUP_UI_STAGING_AND_ONE_RESTORE','launch_manifest_sha256':self.ctx.manifest_sha,'predecessor_state_file':self.m['predecessor'],'predecessor_state_sha256':sha(self.m['predecessor']),'owned_terminal_window':self.ctx.terminal,'owned_child_pid':self.ctx.child,'owned_supervisor_pid':self.ctx.supervisor,'active_application':False,'possible_native_execution':False,'source_freeze_active':True,'original_RAM_restored':False,'original_CPU_restored':False,'original_application_resumed':False,'REU_restoration_attempts':0,'REU_WRITE_commands_confirmed':None,'FTP_connections_this_campaign':0,'inherited_FTP_remote_control_closed':'UNVERIFIED_no_221','upper12MiB_accessed':False,'upper12MiB_backed_up':False}
  self.value.update(fields);tmp=self.active.with_name(self.active.name+'.'+self.m['session_id']+'.tmp');body=(json.dumps(self.value,indent=2)+'\n').encode()
  with tmp.open('xb')as f:
   if f.write(body)!=len(body):raise OSError('ACTIVE short write')
   f.flush();os.fsync(f.fileno())
  os.replace(tmp,self.active);self.claimed=True

class EvidenceWriter:
 def __init__(self,ledger):self.ledger=ledger
 def __call__(self,path,data):
  from cold_session import durable
  durable(path,data)
  if path.name.startswith('event-')and path.suffix=='.json':
   e=json.loads(data)
   if e.get('event')=='transaction_prepared':
    key=e['key'];fields={'last_prepared_transaction':key,'status':'V1_SETUP_UI_STAGING_OR_CLEANUP_ACTIVE'}
    if key=='start_resume'or key.endswith('_start_resume'):fields.update(possible_native_execution=True,active_application=True)
    if key.startswith('cleanup_')or key=='terminal_RAM':fields['status']='V1_SETUP_UI_STAGING_CLEANUP_PENDING'
    self.ledger.write(**fields)

