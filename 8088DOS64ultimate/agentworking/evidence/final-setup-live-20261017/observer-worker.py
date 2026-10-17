from support import *
import sys,traceback
W=Path(__file__).resolve().parent;m=json.loads((W/'MANIFEST.json').read_text());R=Path(m['run']);R.mkdir();r=Rest(R,420);result={'status':'awaiting_physical_keyboard','native_UI_input_injected':False,'reset_or_new_program':False,'file_writes':False};claimed=False
try:
 for p,h in m['inputs'].items():assert sha(Path(p).read_bytes())==h,p
 assert sha(ACTIVE.read_bytes())==m['predecessor_sha256'];a=json.loads(ACTIVE.read_text());assert not a['current_host_job_live']and a['active_application'];save(R/'ACTIVE-predecessor.json',a);state(session_id=R.name,run=str(R),purpose='READ_ONLY_OBSERVE_FINAL_SETUP_PHYSICAL_KEYS',current_host_job_live=True,owned_child_pid=os.getpid(),owned_supervisor_pid=os.getppid(),owned_terminal_window=os.environ['DOS64_TERMINAL_WINDOW']);claimed=True
 last=None;end=time.monotonic()+300
 while time.monotonic()<end:
  raw=r.read(0x400,1000);rc=r.read(0xb01a,2)
  text='\n'.join(''.join(chr(c+96)if 1<=c<=26 else '@'if c==0 else chr(c)if 32<=c<=90 else '?'for c in raw[i:i+40])for i in range(0,1000,40));key=(sha(raw),rc.hex())
  if key!=last:
   save(R/('screen-%04d.bin'%r.seq),raw);save(R/('screen-%04d.txt'%r.seq),text.encode());save(R/('LATEST-'+str(r.seq)+'.json'),{'rc_state':rc[0],'rc_error':rc[1]});print('STATE',rc.hex(),text[:160].replace('\n',' | '),flush=True);last=key
  if rc[0]in [5,7]:
   r.put('machine:pause');ram=r.ram();save(R/'RAM-terminal.bin',ram);save(R/'terminal-screen.txt',text.encode());r.put('machine:resume');result.update(rc_state=rc[0],rc_error=rc[1],terminal_capture=True,final_resume_ACK=True);result['status']='native_setup_complete'if rc==b'\7\0'else'native_setup_failed';break
  time.sleep(1)
 save(R/'RESULT.json',result)
except BaseException as e:result.update(status='observer_failed',first_error=repr(e),traceback=traceback.format_exc());save(R/'FAILURE.json',result);print(traceback.format_exc(),flush=True)
finally:
 if not (R/'RESULT.json').exists():save(R/'RESULT.json',result)
 if claimed:state(current_host_job_live=False,physical_result=str(R/'RESULT.json'),status=result['status'].upper(),first_error=result.get('first_error'),human_keyboard_pending=result['status']=='awaiting_physical_keyboard')
 print(json.dumps(result,indent=2),flush=True)
sys.exit(1 if result['status']in ['observer_failed','native_setup_failed']else 0)
