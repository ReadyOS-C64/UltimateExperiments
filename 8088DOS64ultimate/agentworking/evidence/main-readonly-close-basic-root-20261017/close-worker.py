from pathlib import Path
import os,sys,json,hashlib,time,http.client,traceback
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;R=W.parents[2];OLD=R/'agentworking/scratch/native-copy-wait76-recovery-purpose-20261017/work';sys.path.insert(0,str(OLD));from admission import Admission
from transport import INVENTORY,FIELDS
from ready_prefix import basic_ready
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
active=R/'agentworking/ACTIVE_HARDWARE_SESSION.json';m=json.loads((W/'PHYSICAL_MANIFEST.json').read_text());run=Path(m['run']);run.mkdir();seq=0;end=time.monotonic()+120;cleanup_end=None;result={'status':'failed','physical':True,'scope':'OWNED_READONLY_CLOSE2','prior_COPY20M_stays_failed':True,'REU_access':False,'known_closed':False,'BASIC_ready_verified':False};claimed=False;profile_changed=False;last_inventory=None

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
def write(a,b):
 v=tx('PUT','machine:writemem?address=%X&data=%s'%(a,b.hex()));assert v.get('address','').upper()=='%04X-%04X'%(a,a+len(b)-1)
def checkpins():
 for p,h in m['inputs'].items():assert sha(Path(p))==h,p
l={}
for line in(OLD/'copy-reader.labels').read_text().splitlines():
 x=line.split()
 if len(x)==3:l[x[2].lstrip('.')]=int(x[1],16)
ad=Admission();reference=(R/'agentworking/runs/c64u-wait76-recovery-20261017-d248cec1/session/RAM-closed-paused.bin').read_bytes()
def admit(b):
 ad.source.verify(b)
 for n,v in {'_cr_p_phase':12,'_cr_p_first':8,'_cr_p_cleanup':3,'_cr_p_copy_uncertain':0,'_cr_p_cwd_changed':0,'_cr_p_initialclosed':1,'_cr_p_raw':0,'_files_handle':2,'_files_mode':1,'_files_target':2,'_files_owned_target':2,'_files_op':3,'_files_state':3,'_uci_state':10,'_uci_error':3,'_uci_recovery_failed':0}.items():assert b[l[n]]==v,(n,b[l[n]])
 for lo,hi in [(0x200,0x230),(0x260,0x28d),(0x300,0x30b),(l['_cr_p_previous_cwd'],l['_cr_p_mismatch']+4),(l['_files_state'],l['_files_state']+25)]:assert b[lo:hi]==reference[lo:hi],(lo,hi)
 assert b[0x82e:0x831]==bytes.fromhex('4c2e08');assert b[l['sp']:l['sp']+2]==b'\xff\xcf';assert b[l['_np_mapping']:l['_np_mapping']+8]==bytes.fromhex('a5312f35d0ca0000')
try:
 checkpins();assert sha(active)==m['predecessor_sha256'];a=json.loads(active.read_text());assert a['hardware_owner']=='root'and not a['current_host_job_live'];save('ACTIVE-predecessor.json',a);save('PROCESS.json',{'pid':os.getpid(),'parent':os.getppid(),'session':os.getsid(0),'stdin_devnull_verified':os.fstat(0).st_rdev==os.stat('/dev/null').st_rdev and not os.isatty(0),'terminal':os.environ.get('DOS64_TERMINAL_WINDOW')});state(session_id=run.name,run=str(run),purpose=result['scope'],owned_child_pid=os.getpid(),owned_supervisor_pid=os.getppid(),owned_terminal_window=os.environ.get('DOS64_TERMINAL_WINDOW'),predecessor_state_sha256=m['predecessor_sha256'],predecessor_state_file=str(run/'ACTIVE-predecessor.json'),launch_manifest_sha256=sha(W/'PHYSICAL_MANIFEST.json'),current_host_job_live=True,status='READONLY_CLOSE2_PREFLIGHT');claimed=True
 before=inventory();save('inventory-before.json',before);original=json.loads(Path(m['original_inventory']).read_text());assert before==original;assert all(before['info'].get(k)==v for k,v in FIELDS.items())
 tx('PUT','machine:pause');fresh=ram('RAM-source-paused');admit(fresh);result['fresh_source_admission']=True
 # The previous purpose was one-shot and stopped. This new one-shot admission
 # grants only readonly-owned CLOSE recovery and does not revive that campaign.
 profile_changed=True;tx('PUT','configs/U64%20Specific%20Settings/CPU%20Speed?value=%201');tx('PUT','configs/U64%20Specific%20Settings/Turbo%20Control?value=Manual');p=tx('GET','configs/U64%20Specific%20Settings')['U64 Specific Settings'];assert p['CPU Speed']==' 1'and p['Turbo Control']=='Manual'
 payload=(W/'close.bin').read_bytes()
 for i in range(0,len(payload),128):write(0x402e+i,payload[i:i+128])
 assert tx('GET','machine:readmem?address=402E&length='+str(len(payload)),len(payload))==payload
 write(0x830,b'\x40');assert tx('GET','machine:readmem?address=82E&length=3',3)==bytes.fromhex('4c2e40');result['one_byte_redirection_ACK_readback']=True
 tx('PUT','machine:resume');result['native_resume_ACK']=True
 for i in range(100):
  v=tx('GET','machine:readmem?address=4500&length=16',16);save('poll-%03d.bin'%i,v)
  if v[:3]==b'CL2'and v[3]in[0xa5,0xe1]:break
  time.sleep(.25)
 else:raise TimeoutError('Bounded100 close observations')
 tx('PUT','machine:pause');closed=ram('RAM-close-paused');copy=bytearray(closed);copy[0x830]=8;ad.source.verify(copy);assert closed[0x402e:0x402e+len(payload)]==payload;assert closed[0x82e:0x831]==bytes.fromhex('4c2e40');assert closed[0x4500:0x4504]==b'CL2\xa5',closed[0x4500:0x4510].hex()
 assert closed[l['_files_handle']]==0 and closed[l['_uci_state']]==9 and closed[l['_uci_recovery_failed']]==0
 fs,fe,ft=(closed[l[n]]for n in ['_files_state','_files_error','_files_transport_error']);assert(fs,fe,ft)in[(2,0,0),(3,3,0)]
 for n in ['_cr_p_copy_uncertain','_cr_p_cwd_changed','_cr_p_raw']:assert closed[l[n]]==0
 result.update(known_closed=True,native_result=closed[0x4500:0x4510].hex(),close_state=[fs,fe,ft],target=2)
 tx('PUT','machine:reset');result['knownclosed_reset_ACK']=True;previous=None
 for i in range(32):
  time.sleep(.25);tx('PUT','machine:pause');b=tx('GET','machine:readmem?address=0&length=2048',2048);save('BASIC-%02d.bin'%i,b);current=basic_ready(b)
  if current is not None and previous is not None and current['jiffy']>previous['jiffy']:
   result.update(BASIC_ready_verified=True,BASIC_observations=[previous,current]);tx('PUT','machine:resume');result['final_resume_ACK']=True;break
  previous=current;tx('PUT','machine:resume')
 else:raise TimeoutError('Bounded BASIC READY pair')
 result['status']='passed'
except BaseException as e:
 result.update(first_error=repr(e),traceback=traceback.format_exc());print(traceback.format_exc(),flush=True)
finally:
 cleanup_end=time.monotonic()+45
 try:
  if profile_changed:
   tx('PUT','configs/U64%20Specific%20Settings/CPU%20Speed?value=64');tx('PUT','configs/U64%20Specific%20Settings/Turbo%20Control?value=C64U%20Turbo%20Registers')
  if claimed:
   last_inventory=inventory();save('inventory-after.json',last_inventory);result['original_settings_media_equal']=last_inventory==json.loads(Path(m['original_inventory']).read_text());assert result['original_settings_media_equal']
 except BaseException as e:result.update(status='failed',cleanup_error=repr(e))
 try:checkpins();result['inputs_after_exact']=True
 except BaseException as e:result.update(status='failed',source_error=repr(e))
 result['requests']=seq;save('RESULT.json',result)
 if claimed:state(status='READONLY_CLOSE2_COMPLETE_ROOT_REVIEW_PENDING'if result['status']=='passed'else'READONLY_CLOSE2_FAILED_RESERVED',current_host_job_live=False,known_FILES_quiet=result['known_closed'],possible_native_FILES_writer=not result['known_closed'],active_application=not result['BASIC_ready_verified'],possible_native_execution=not result['BASIC_ready_verified'],cold_BASIC_cleanup_acknowledged=result['BASIC_ready_verified']and result.get('final_resume_ACK',False),temporary_profile_restored_verified=result.get('original_settings_media_equal',False),settings_media_equal=result.get('original_settings_media_equal',False),physical_result=str(run/'RESULT.json'),first_error=result.get('first_error'),hardware_reserved=True,current_whole_lower4MiB_verified=False)
 print(json.dumps(result,indent=2),flush=True)
sys.exit(0 if result['status']=='passed'else 1)
