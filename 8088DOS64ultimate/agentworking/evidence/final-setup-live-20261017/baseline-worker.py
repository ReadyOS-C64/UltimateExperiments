from support import *
import sys,uuid,traceback
from urllib.parse import quote
W=Path(__file__).resolve().parent;m=json.loads((W/'MANIFEST.json').read_text());R=Path(m['run']);R.mkdir();r=Rest(R,300);result={'status':'failed','REU_writes':0,'native_FILES':False,'user_full_reboot_current_baseline':True};claimed=False;before=None;native=False;f=None
try:
 for p,h in m['inputs'].items():assert sha(Path(p).read_bytes())==h,p
 assert sha(ACTIVE.read_bytes())==m['predecessor_sha256'];a=json.loads(ACTIVE.read_text());assert not a['current_host_job_live']and a['known_FILES_quiet'];save(R/'ACTIVE-predecessor.json',a)
 state(session_id=R.name,run=str(R),purpose='CURRENT_REU_BASELINE_BEFORE_V1_INSTALL',current_host_job_live=True,owned_child_pid=os.getpid(),owned_supervisor_pid=os.getppid(),owned_terminal_window=os.environ['DOS64_TERMINAL_WINDOW'],hardware_reserved=True);claimed=True
 before=r.inventory();save(R/'inventory-before.json',before);assert before['info']['unique_id']=='DCAF71';cfg=before['configs/C64%20and%20Cartridge%20Settings']['C64 and Cartridge Settings'];assert cfg['RAM Expansion Unit']=='Enabled'and cfg['REU Size']in ['4 MB','8 MB','16 MB'];assert cfg['REU Preload']=='Disabled';r.ready('BASIC-before');save(R/'RAM-before.bin',r.ram())
 # The user's full reboot starts a new volatile baseline. It need not equal the historical ac43 snapshot.
 source=(W/'SNAPSHOT.PRG').read_bytes();nonce=bytes.fromhex(m['nonce']);remote=m['directory'];f=ftp();f.mkd(remote);putcheck(f,remote+'/SNAPSHOT.PRG',source);assert f.quit().startswith('221');f=None
 print('Snapshot helper uploaded and verified',flush=True)
 r.put('runners:load_prg?file='+quote(remote+'/SNAPSHOT.PRG',safe=''));r.ready('BASIC-loaded');assert r.read(0x801,len(source)-2)==source[2:];r.write(0x3e00,bytes(52));r.write(0x3f00,bytes(2));assert r.read(0x3e00,52)==bytes(52)and r.read(0x3f00,2)==bytes(2)
 r.put('configs/U64%20Specific%20Settings/Turbo%20Control?value=Manual');r.put('configs/U64%20Specific%20Settings/CPU%20Speed?value=64');r.sys(2061);native=True;state(possible_native_execution=True)
 sys.path.insert(0,str(W));from changed_driver import ChangedDriver
 class Wire:
  def header(self,end):return r.read(0x3e00,52)
  def full(self,end):
   a=r.read(0x801,32768);save(R/('half-%04d.bin'%r.seq),a);b=r.read(0x8801,14335);save(R/('half-%04d.bin'%r.seq),b);return a+b
  def ack(self,n,end):r.write(0x3f00,bytes([n]))
  def cancel(self,end):r.write(0x3f01,b'\1')
 result['snapshot']=ChangedDriver(source,nonce,Wire(),R/'BASELINE.REU',bytes(0x400000),whole=240).run();baseline=(R/'BASELINE.REU').read_bytes();assert len(baseline)==0x400000;print('Complete4MiB current snapshot captured',sha(baseline),flush=True)
 f=ftp();putcheck(f,remote+'/BASELINE.REU',baseline);assert f.quit().startswith('221');f=None;result['persistent_backup_verified']=True;result['persistent_backup']=remote+'/BASELINE.REU';result['sha256']=sha(baseline);os.chmod(R/'BASELINE.REU',0o444);result['status']='passed'
except BaseException as e:result.update(first_error=repr(e),traceback=traceback.format_exc());print(traceback.format_exc(),flush=True)
finally:
 if f:f.close()
 if before is not None:
  try:
   # Snapshot helper never opens native files and never writes REU. Reset is safe on success or stopped read-only helper.
   if native:r.put('machine:pause');save(R/'RAM-terminal.bin',r.ram());r.put('machine:reset')
   r.ready('BASIC-final');r.put('machine:resume');result['BASIC_resumed']=True
   original=before['configs/U64%20Specific%20Settings']['U64 Specific Settings']
   for key in ['CPU Speed','Turbo Control']:r.put('configs/U64%20Specific%20Settings/'+quote(key,safe='')+'?value='+quote(original[key],safe=''))
   after=r.inventory();save(R/'inventory-after.json',after);result['settings_media_equal']=after==before;assert after==before
  except BaseException as e:result.update(status='failed',cleanup_error=repr(e))
 save(R/'RESULT.json',result)
 if claimed:state(current_host_job_live=False,physical_result=str(R/'RESULT.json'),status='CURRENT_REU_BASELINE_SAVED_BASIC_READY'if result['status']=='passed'else'CURRENT_REU_BASELINE_FAILED',known_FILES_quiet=True,possible_native_FILES_writer=False,possible_native_execution=False,cold_BASIC_cleanup_acknowledged=result.get('BASIC_resumed',False),settings_media_equal=result.get('settings_media_equal',False),current_REU_baseline=str(R/'BASELINE.REU')if result['status']=='passed'else None,current_REU_baseline_SHA=result.get('sha256'),current_REU_baseline_persistent=result.get('persistent_backup'),first_error=result.get('first_error'))
 print(json.dumps(result,indent=2),flush=True)
sys.exit(0 if result['status']=='passed'else 1)
