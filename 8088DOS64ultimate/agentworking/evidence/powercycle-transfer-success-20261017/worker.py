from pathlib import Path
import os,sys,json,hashlib,time,http.client,ftplib,io,traceback
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent;R=W.parents[2];m=json.loads((W/'MANIFEST.json').read_text());data=json.loads((W/'PAYLOAD.json').read_text());run=Path(m['run']);run.mkdir();active=R/'agentworking/ACTIVE_HARDWARE_SESSION.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();end=time.monotonic()+150;ftp=None;claimed=False;result={'status':'failed','scope':'NEW_FOLDER_DEVELOPMENT_PACKAGE_STAGE_ONLY','physical':True,'directory':data['directory'],'C64_CPU_control':False,'REU_access':False,'UCI_commands':False,'native_V1_gate_acceptance':False,'files':{},'FTP_221':False}
def save(n,v):
 with(run/n).open('xb')as f:f.write((json.dumps(v,indent=2)+'\n').encode());f.flush();os.fsync(f.fileno())
def state(**kw):
 a=json.loads(active.read_text());a.update(kw);q=active.with_suffix('.stage.tmp');q.write_text(json.dumps(a,indent=2)+'\n');os.replace(q,active)
def pins():
 for p,h in m['inputs'].items():assert sha(Path(p))==h,p
 for p,v in data['files'].items():assert Path(p).stat().st_size==v['bytes']and sha(Path(p))==v['sha256'],p
 for p,h in data['original_images'].items():assert sha(Path(p))==h,p
def remaining():
 n=end-time.monotonic()
 if n<=0:raise TimeoutError('One150s post-powercycle staging endpoint')
 return min(8,n)
def get(route):
 c=http.client.HTTPConnection('10.0.0.79',timeout=remaining())
 try:
  c.request('GET','/v1/'+route);r=c.getresponse();assert r.status==200;b=r.read(262145);assert len(b)<=262144;v=json.loads(b);assert v.get('errors')==[];return v
 finally:c.close()
def inventory():return {r:get(r)for r in ['info','configs/U64%20Specific%20Settings','configs/C64%20and%20Cartridge%20Settings','drives']}
try:
 pins();assert sha(active)==m['predecessor_sha256'];a=json.loads(active.read_text());assert a['hardware_owner']=='root'and a['known_FILES_quiet']and a['cold_BASIC_cleanup_acknowledged']and not a['current_host_job_live'];save('ACTIVE-predecessor.json',a)
 state(session_id=run.name,run=str(run),purpose=result['scope'],owned_child_pid=os.getpid(),owned_supervisor_pid=os.getppid(),owned_terminal_window=os.environ.get('DOS64_TERMINAL_WINDOW'),predecessor_state_file=str(run/'ACTIVE-predecessor.json'),predecessor_state_sha256=m['predecessor_sha256'],launch_manifest_sha256=sha(W/'MANIFEST.json'),current_host_job_live=True,status='V1_NEW_FOLDER_STAGING',hardware_reserved=True);claimed=True
 before=inventory();save('inventory-before.json',before)
 for k,v in {'product':'C64 Ultimate','firmware_version':'3.14','fpga_version':'121','core_version':'1.47','unique_id':'DCAF71'}.items():assert before['info'].get(k)==v
 result['matches_pre_powercycle_inventory']=before==json.loads(Path(m['original_inventory']).read_text());result['user_reported_full_reboot']=True
 ftp=ftplib.FTP();result['FTP_welcome']=ftp.connect('10.0.0.79',21,timeout=remaining());result['FTP_login']=ftp.login('anonymous','anonymous@');ftp.cwd('/usb1/DOS64_TEST');result['fresh_MKD']=ftp.mkd('v1-powercycle-20261017');ftp.cwd(data['directory']);assert ftp.pwd().rstrip('/').casefold()==data['directory'].casefold();result['fresh_directory_created']=True
 rows=sorted(data['files'].items(),key=lambda x:(x[1]['name']!='OWNER.JSON',x[1]['name']))
 for p,v in rows:
  ftp.sock.settimeout(remaining());body=Path(p).read_bytes();w=ftp.storbinary('STOR '+v['name'],io.BytesIO(body),blocksize=32768,callback=lambda b:remaining());assert w.startswith('226');parts=[];length=[0]
  def take(b):
   remaining();length[0]+=len(b);assert length[0]<=len(body);parts.append(b)
  ftp.sock.settimeout(remaining());rr=ftp.retrbinary('RETR '+v['name'],take,blocksize=32768);got=b''.join(parts);assert rr.startswith('226')and got==body
  result['files'][v['name']]={'bytes':len(got),'sha256':hashlib.sha256(got).hexdigest(),'STOR':w,'RETR':rr};save('file-%02d.json'%len(result['files']),result['files'][v['name']]);print('Verified',v['name'],len(got),flush=True)
 result['listing']=ftp.nlst();assert sorted(Path(n).name for n in result['listing'])==sorted(v['name']for v in data['files'].values());q=ftp.quit();result['FTP_quit']=q;result['FTP_221']=q.startswith('221');assert result['FTP_221'];ftp=None
 pins();result['inputs_after_exact']=True;after=inventory();save('inventory-after.json',after);result['settings_media_equal']=after==before;assert result['settings_media_equal'];result['status']='passed'
except BaseException as e:result.update(first_error=repr(e),traceback=traceback.format_exc());print(traceback.format_exc(),flush=True)
finally:
 if ftp:
  try:ftp.close();result['FTP_local_socket_closed']=True
  except BaseException as e:result['FTP_local_close_error']=repr(e)
 try:
  final=inventory();save('inventory-final.json',final);result['settings_media_equal']=final==before
 except BaseException as e:result['final_inventory_error']=repr(e)
 save('RESULT.json',result)
 if claimed:state(status='V1_PACKAGE_STAGED_BASIC_READY'if result['status']=='passed'else'V1_PACKAGE_STAGE_FAILED_RESERVED',current_host_job_live=False,physical_result=str(run/'RESULT.json'),first_error=result.get('first_error'),FTP_current_control_221_verified=result['FTP_221'],FTP_connections_this_campaign=1,known_FILES_quiet=True,possible_native_FILES_writer=False,hardware_reserved=True,staged_V1_directory=data['directory'],staged_V1_directory_verified=result['status']=='passed',staged_V1_directory_partial_or_empty=result['status']!='passed',current_settings_media_equal_verified_after_stage=result.get('settings_media_equal',False))
 print(json.dumps({k:v for k,v in result.items()if k!='files'},indent=2),flush=True)
sys.exit(0 if result['status']=='passed'else 1)
