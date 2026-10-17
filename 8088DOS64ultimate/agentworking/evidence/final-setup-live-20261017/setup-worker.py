from support import *
import traceback,sys
from urllib.parse import quote
W=Path(__file__).resolve().parent;m=json.loads((W/'MANIFEST.json').read_text());R=Path(m['run']);R.mkdir();r=Rest(R,100);result={'status':'failed','scope':'UNCHANGED_FINAL_SETUP_ACTUAL_PHYSICAL_UI_START','automated_native_UI_keys':False,'REU_baseline_before':m['baseline'],'human_selection_pending':True};claimed=False;started=False;before=None
try:
 for p,h in m['inputs'].items():assert sha(Path(p).read_bytes())==h,p
 baseline=json.loads(Path(m['baseline_result']).read_text());assert baseline['status']=='passed'and baseline['persistent_backup_verified']and baseline['settings_media_equal'];assert sha(Path(m['baseline']).read_bytes())==baseline['sha256']
 assert sha(ACTIVE.read_bytes())==m['predecessor_sha256'];a=json.loads(ACTIVE.read_text());assert not a['current_host_job_live']and a['known_FILES_quiet'];save(R/'ACTIVE-predecessor.json',a);state(session_id=R.name,run=str(R),purpose=result['scope'],current_host_job_live=True,owned_child_pid=os.getpid(),owned_supervisor_pid=os.getppid(),owned_terminal_window=os.environ['DOS64_TERMINAL_WINDOW'],hardware_reserved=True);claimed=True
 before=r.inventory();save(R/'inventory-before.json',before);assert before['info']['unique_id']=='DCAF71';r.ready('BASIC-before');save(R/'RAM-before.bin',r.ram());r.put('configs/U64%20Specific%20Settings/Turbo%20Control?value=Manual');r.put('configs/U64%20Specific%20Settings/CPU%20Speed?value=%201')
 expected=Path(m['setup_local']).read_bytes()[2:];actual=r.read(0x801,32768)+r.read(0x8801,len(expected)-32768);save(R/'SETUP-cold-readback.bin',actual);visible=0xa000-0x801;assert actual[:visible]==expected[:visible];result.update(visible_cold_source_equal=True,hidden_preSYS_verified=False,full_remote_file_byteverified=True,existing_load_adopted=True,native_bootstrap_CRC_required=True)
 r.put('configs/U64%20Specific%20Settings/CPU%20Speed?value=64');r.sys(2061);started=True;state(active_application=True,possible_native_execution=True,possible_native_FILES_writer=True,known_FILES_quiet=False,source_freeze_active=True)
 def text(raw):
  return '\n'.join(''.join(chr(c+96)if 1<=c<=26 else '@'if c==0 else chr(c)if 32<=c<=90 else '?'for c in raw[i:i+40])for i in range(0,1000,40))
 for i in range(50):
  raw=r.read(0x400,1000);t=text(raw)
  if 'DOS64 setup' in t or 'Choose the DOS64 home folder' in t:
   save(R/'SETUP-first-screen.bin',raw);save(R/'SETUP-first-screen.txt',t.encode());result['actual_native_menu_observed']=True;print(t,flush=True);break
  time.sleep(.1)
 else:save(R/'last-screen.bin',raw);save(R/'last-screen.txt',t.encode());raise RuntimeError('Final SETUP did not display menu')
 r.put('machine:pause');save(R/'RAM-UI-paused.bin',r.ram());r.put('machine:resume');result['final_resume_ACK']=True;after=r.inventory();save(R/'inventory-active.json',after);result['active_Manual64']=after['configs/U64%20Specific%20Settings']['U64 Specific Settings']['Turbo Control']=='Manual'and after['configs/U64%20Specific%20Settings']['U64 Specific Settings']['CPU Speed'].strip()=='64';assert result['active_Manual64'];result['status']='passed';result['setup_home']=m['home']
except BaseException as e:result.update(first_error=repr(e),traceback=traceback.format_exc());print(traceback.format_exc(),flush=True)
finally:
 save(R/'RESULT.json',result)
 if claimed:state(current_host_job_live=False,physical_result=str(R/'RESULT.json'),status='FINAL_SETUP_NATIVE_MENU_AWAITING_PHYSICAL_KEYS'if result['status']=='passed'else'FINAL_SETUP_LAUNCH_FAILED_RESERVED',active_application=started,possible_native_execution=started,known_FILES_quiet=not started,possible_native_FILES_writer=started,setup_home=m['home'],first_error=result.get('first_error'),human_keyboard_pending=True)
 print(json.dumps(result,indent=2),flush=True)
sys.exit(0 if result['status']=='passed'else 1)
