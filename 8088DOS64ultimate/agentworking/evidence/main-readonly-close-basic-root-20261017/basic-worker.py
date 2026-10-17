from pathlib import Path
import os,sys,json,hashlib,time,http.client,traceback
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;R=W.parents[2];OLD=R/'agentworking/scratch/native-copy-wait76-recovery-purpose-20261017/work';sys.path.insert(0,str(OLD));from admission import Admission
from transport import INVENTORY,FIELDS
from ready_prefix import basic_ready
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
active=R/'agentworking/ACTIVE_HARDWARE_SESSION.json';m=json.loads((W/'PHYSICAL_MANIFEST.json').read_text());run=Path(m['run']);run.mkdir();seq=0;end=time.monotonic()+90;cleanup_end=None;claimed=False;result={'status':'failed','scope':'FRESH_KNOWNCLOSED_BASIC_ONLY','physical':True,'prior_COPY20M_stays_failed':True,'REU_access':False,'known_closed':False,'BASIC_ready_verified':False}
def save(n,v):
 p=run/n;b=v if isinstance(v,bytes)else(json.dumps(v,indent=2)+'\n').encode()
 with p.open('xb')as f:f.write(b);f.flush();os.fsync(f.fileno())

def state(**kw):
 a=json.loads(active.read_text());a.update(kw);tmp=active.with_suffix('.mainclose.tmp');tmp.write_text(json.dumps(a,indent=2)+'\n');os.replace(tmp,active)

def tx(method,route,count=None):
 global seq
 limit=cleanup_end if cleanup_end is not None else end;assert time.monotonic()<limit;seq+=1;assert seq<=180
 plan={'method':method,'route':route,'count':count,'index':seq,'retries':0};save('request-%03d.json'%seq,plan);c=None;parts=[]
 try:
  c=http.client.HTTPConnection(m['host'],timeout=min(5,limit-time.monotonic()));c.request(method,'/v1/'+route);resp=c.getresponse();headers=resp.getheaders();maxbytes=(count if count is not None else 262144)+1;got=0
  while True:
   left=limit-time.monotonic()
   if left<=0:raise TimeoutError('Original phase endpoint')
   sock=c.sock or getattr(getattr(getattr(resp,'fp',None),'raw',None),'_sock',None);assert sock is not None;sock.settimeout(min(5,left));b=resp.read1(min(16384,maxbytes-got))
   if not b:break
   parts.append(b);got+=len(b)
   if got>=maxbytes:break
  raw=b''.join(parts);save('response-%03d.bin'%seq,raw);save('response-%03d.json'%seq,dict(plan,status=resp.status,headers=headers,bytes=len(raw)));assert resp.status==200
  if count is not None:assert len(raw)==count;return raw
  v=json.loads(raw);assert isinstance(v,dict)and v.get('errors')==[];return v
 except BaseException as e:
  save('failure-%03d.json'%seq,dict(plan,error=repr(e),received=len(b''.join(parts))));raise
 finally:
  if c:c.close()

def inventory():return {r:tx('GET',r)for r in INVENTORY}

def ram(tag):
 b=tx('GET','machine:readmem?address=0&length=32768',32768)+tx('GET','machine:readmem?address=8000&length=32768',32768);save(tag+'.bin',b);return b

def checkpins():
 for p,h in m['inputs'].items():assert sha(Path(p))==h,p

l={}
for line in(OLD/'copy-reader.labels').read_text().splitlines():
 x=line.split()
 if len(x)==3:l[x[2].lstrip('.')]=int(x[1],16)
ad=Admission();reference=Path(m['closed_reference']).read_bytes();payload=Path(m['helper']).read_bytes()
def admit_closed(raw):
 assert isinstance(raw,bytes)and len(raw)==65536
 assert raw[0x82e:0x831]==bytes.fromhex('4c2e40')
 b=bytearray(raw);b[0x830]=8;ad.source.verify(bytes(b))
 assert raw[0x402e:0x402e+len(payload)]==payload
 assert raw[0x4500:0x4510]==bytes.fromhex('434c32a5020000000900000000000000')
 for n,v in {'_files_state':2,'_files_error':0,'_files_transport_error':0,'_files_handle':0,'_files_op':3,'_files_mode':1,'_files_target':2,'_files_owned_target':2,'_uci_state':9,'_uci_error':0,'_uci_recovery_failed':0,'_cr_p_phase':12,'_cr_p_copy_uncertain':0,'_cr_p_cwd_changed':0,'_cr_p_initialclosed':1,'_cr_p_raw':0}.items():assert raw[l[n]]==v,(n,raw[l[n]])
 assert raw[l['sp']:l['sp']+2]==b'\xff\xcf'
 for lo,hi in [(l['_cr_p_previous_cwd'],l['_cr_p_mismatch']+4),(l['_files_state'],l['_files_state']+25),(l['_uci_state'],l['_uci_state']+24)]:assert raw[lo:hi]==reference[lo:hi]
 return True

try:
 checkpins();assert sha(active)==m['predecessor_sha256'];a=json.loads(active.read_text());assert a['hardware_owner']=='root'and not a['current_host_job_live'];save('ACTIVE-predecessor.json',a)
 state(session_id=run.name,run=str(run),purpose=result['scope'],owned_child_pid=os.getpid(),owned_supervisor_pid=os.getppid(),owned_terminal_window=os.environ.get('DOS64_TERMINAL_WINDOW'),predecessor_state_sha256=m['predecessor_sha256'],predecessor_state_file=str(run/'ACTIVE-predecessor.json'),launch_manifest_sha256=sha(W/'PHYSICAL_MANIFEST.json'),current_host_job_live=True,status='KNOWNCLOSED_BASIC_PREFLIGHT');claimed=True
 before=inventory();save('inventory-before.json',before);assert before==json.loads(Path(m['original_inventory']).read_text());assert all(before['info'].get(k)==v for k,v in FIELDS.items())
 tx('PUT','machine:pause');fresh=ram('RAM-knownclosed-paused');admit_closed(fresh);result['known_closed']=True
 tx('PUT','machine:reset');result['knownclosed_reset_ACK']=True;previous=None
 for i in range(32):
  time.sleep(.25);tx('PUT','machine:pause');b=tx('GET','machine:readmem?address=0&length=2048',2048);save('BASIC-%02d.bin'%i,b);current=basic_ready(b)
  if current is not None and previous is not None and current['jiffy']>previous['jiffy']:
   result.update(BASIC_ready_verified=True,BASIC_observations=[previous,current]);tx('PUT','machine:resume');result['final_resume_ACK']=True;break
  previous=current;tx('PUT','machine:resume')
 else:raise TimeoutError('Bounded32 BASIC READY observations')
 result['status']='passed'
except BaseException as e:
 result.update(first_error=repr(e),traceback=traceback.format_exc());print(traceback.format_exc(),flush=True)
finally:
 cleanup_end=time.monotonic()+30
 try:
  if claimed:
   after=inventory();save('inventory-after.json',after);result['original_settings_media_equal']=after==json.loads(Path(m['original_inventory']).read_text());assert result['original_settings_media_equal']
 except BaseException as e:result.update(status='failed',cleanup_error=repr(e))
 try:checkpins();result['inputs_after_exact']=True
 except BaseException as e:result.update(status='failed',source_error=repr(e))
 result['requests']=seq;save('RESULT.json',result)
 if claimed:state(status='KNOWNCLOSED_BASIC_COMPLETE_ROOT_REVIEW_PENDING'if result['status']=='passed'else'KNOWNCLOSED_BASIC_FAILED_RESERVED',current_host_job_live=False,known_FILES_quiet=result['known_closed'],possible_native_FILES_writer=not result['known_closed'],active_application=not result['BASIC_ready_verified'],possible_native_execution=not result['BASIC_ready_verified'],cold_BASIC_cleanup_acknowledged=result['BASIC_ready_verified']and result.get('final_resume_ACK',False),temporary_profile_restored_verified=result.get('original_settings_media_equal',False),settings_media_equal=result.get('original_settings_media_equal',False),physical_result=str(run/'RESULT.json'),first_error=result.get('first_error'),hardware_reserved=True,current_whole_lower4MiB_verified=False)
 print(json.dumps(result,indent=2),flush=True)
sys.exit(0 if result['status']=='passed'else 1)
