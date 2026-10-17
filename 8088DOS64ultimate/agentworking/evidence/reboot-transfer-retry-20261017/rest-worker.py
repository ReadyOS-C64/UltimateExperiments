from pathlib import Path
import os,sys,json,hashlib,time,http.client,traceback
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;R=W.parents[2];sys.path.insert(0,str(R/'agentworking/scratch/native-copy-wait76-recovery-purpose-20261017/work'));from ready_prefix import basic_ready
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((W/'MANIFEST.json').read_text());run=Path(m['run']);run.mkdir();active=R/'agentworking/ACTIVE_HARDWARE_SESSION.json';end=time.monotonic()+75;cleanup_end=None;seq=0;claimed=False;post_attempted=False;restore_attempted=False;baseline=None;marker=bytes.fromhex(m['marker_hex']);result={'status':'failed','scope':'NAMED_MULTIPART_32BYTE_PROBE','physical':True,'REU_access':False,'native_UCI':False,'CPU_reset':False,'FTP':False,'CPU_RAM32_restored':False,'known_FILES_quiet':True,'temp_name':m['temp_name']}
def save(n,v):
 with(run/n).open('xb')as f:f.write(v if isinstance(v,bytes)else(json.dumps(v,indent=2)+'\n').encode());f.flush();os.fsync(f.fileno())
def state(**kw):
 a=json.loads(active.read_text());a.update(kw);q=active.with_suffix('.probe.tmp');q.write_text(json.dumps(a,indent=2)+'\n');os.replace(q,active)
def pins():
 for p,h in m['inputs'].items():assert sha(Path(p))==h,p
def tx(key,method,route,count=None,body=None,typ=None,notfound=False):
 global seq
 limit=cleanup_end if cleanup_end else end;left=limit-time.monotonic();assert left>0;seq+=1;assert seq<=150;plan={'key':key,'method':method,'route':route,'body_bytes':len(body or b''),'body_sha256':hashlib.sha256(body).hexdigest()if body else None,'retries':0};save('request-%03d.json'%seq,plan);c=None;pieces=[]
 try:
  c=http.client.HTTPConnection('10.0.0.79',timeout=min(8,left));headers={}if body is None else{'Content-Type':typ,'Content-Length':str(len(body))};c.request(method,'/v1/'+route,body=body,headers=headers);resp=c.getresponse();status=resp.status
  maximum=(count if count is not None else 262144)+1;got=0
  while True:
   left=limit-time.monotonic();assert left>0;sock=c.sock or getattr(getattr(getattr(resp,'fp',None),'raw',None),'_sock',None);assert sock is not None;sock.settimeout(min(8,left));b=resp.read1(min(16384,maximum-got))
   if not b:break
   pieces.append(b);got+=len(b)
   if got>=maximum:break
  raw=b''.join(pieces);save('response-%03d.bin'%seq,raw);save('response-%03d.json'%seq,dict(plan,status=status,bytes=len(raw),headers=resp.getheaders()))
  if notfound:
   j=json.loads(raw);assert status==404 and j.get('errors')==["FILE DOESN'T EXIST"];return j
  if method=='POST'and status==404 and json.loads(raw).get('errors')==['Could not read data from attachment']:result['POST_rejected_before_DMA']=True
  assert status==200
  if count is not None:assert len(raw)==count;return raw
  j=json.loads(raw);assert isinstance(j,dict)and j.get('errors')==[];return j
 except BaseException as e:save('failure-%03d.json'%seq,dict(plan,error=repr(e),received=len(b''.join(pieces))));raise
 finally:
  if c:c.close()
def inventory(tag):return {r:tx(tag+str(i),'GET',r)for i,r in enumerate(['info','configs/U64%20Specific%20Settings','configs/C64%20and%20Cartridge%20Settings','drives'])}
try:
 pins();assert sha(active)==m['predecessor_sha256'];a=json.loads(active.read_text());assert a['hardware_owner']=='root'and not a['current_host_job_live']and a['known_FILES_quiet'];save('ACTIVE-predecessor.json',a);state(status='MULTIPART_PROBE_IN_PROGRESS',session_id=run.name,run=str(run),purpose=result['scope'],owned_child_pid=os.getpid(),owned_supervisor_pid=os.getppid(),owned_terminal_window=os.environ.get('DOS64_TERMINAL_WINDOW'),launch_manifest_sha256=sha(W/'MANIFEST.json'),current_host_job_live=True,predecessor_state_file=str(run/'ACTIVE-predecessor.json'),predecessor_state_sha256=m['predecessor_sha256']);claimed=True
 before=inventory('before');save('inventory-before.json',before);assert before==json.loads(Path(m['original_inventory']).read_text());assert before['info']['unique_id']=='DCAF71'
 previous=None
 for i in range(16):
  tx('pause'+str(i),'PUT','machine:pause');raw=tx('BASIC'+str(i),'GET','machine:readmem?address=0&length=2048',2048);save('BASIC-before-%02d.bin'%i,raw);v=basic_ready(raw)
  if v and previous and v['jiffy']>previous['jiffy']:result['fresh_BASIC_pair']=[previous,v];break
  previous=v;tx('resume'+str(i),'PUT','machine:resume');time.sleep(.15)
 else:raise ValueError('Actual advancing BASIC READY required')
 baseline=tx('original32','GET','machine:readmem?address=4000&length=32',32);assert baseline!=marker;save('original32.bin',baseline)
 tx('temp_absent','GET','files/Temp/'+m['temp_name']+':info',notfound=True);result['fresh_named_temp_absent']=True
 post_attempted=True;reply=tx('one_named_multipart','POST','machine:writemem?address=4000',body=(W/'request.body').read_bytes(),typ=m['content_type']);assert reply.get('address','').upper()=='4000-401F';result['POST_ACK']=True
 actual=tx('marker32','GET','machine:readmem?address=4000&length=32',32);save('marker32.bin',actual);assert actual==marker;result['marker32_exact']=True
 info=tx('temp_info','GET','files/Temp/'+m['temp_name']+':info');save('temp-info.json',info);assert info['files']['filename']==m['temp_name']and info['files']['size']==32;result['named_temp_size_path_verified']=True;result['status']='passed'
except BaseException as e:result.update(first_error=repr(e),traceback=traceback.format_exc());print(traceback.format_exc(),flush=True)
finally:
 cleanup_end=time.monotonic()+30
 try:
  if claimed and baseline is not None:
   b=tx('cleanup_observe32','GET','machine:readmem?address=4000&length=32',32)
   if b==marker:
    restore_attempted=True;j=tx('restore_original32','PUT','machine:writemem?address=4000&data='+baseline.hex());assert j.get('address','').upper()=='4000-401F';assert tx('restore_readback32','GET','machine:readmem?address=4000&length=32',32)==baseline;result['CPU_RAM32_restored']=True
   elif b==baseline and(not post_attempted or result.get('POST_rejected_before_DMA',False)):result['CPU_RAM32_restored']=True;result['RAM32_unchanged_without_restore_write']=True
   else:raise ValueError('No restoration authority for incomplete/unknown multipart32 observation')
  if claimed and(result['CPU_RAM32_restored']or not post_attempted):
   raw=tx('final_BASIC','GET','machine:readmem?address=0&length=2048',2048);save('BASIC-final-paused.bin',raw);assert basic_ready(raw);tx('final_resume','PUT','machine:resume');result['final_resume_ACK']=True
  if claimed:
   after=inventory('after');save('inventory-after.json',after);result['settings_media_equal']=after==json.loads(Path(m['original_inventory']).read_text());assert result['settings_media_equal']
 except BaseException as e:result.update(status='failed',cleanup_error=repr(e))
 try:pins();result['inputs_after_exact']=True
 except BaseException as e:result.update(status='failed',source_error=repr(e))
 result.update(requests=seq,POST_attempted=post_attempted,restore_attempted=restore_attempted);save('RESULT.json',result)
 if claimed:state(status='MULTIPART_PROBE_PASSED_BASIC_READY'if result['status']=='passed'else'MULTIPART_PROBE_FAILED_RESERVED',current_host_job_live=False,physical_result=str(run/'RESULT.json'),first_error=result.get('first_error'),known_FILES_quiet=True,possible_native_FILES_writer=False,cold_BASIC_cleanup_acknowledged=result.get('final_resume_ACK',False),settings_media_equal=result.get('settings_media_equal',False),hardware_reserved=True)
 print(json.dumps(result,indent=2),flush=True)
sys.exit(0 if result['status']=='passed'else 1)
