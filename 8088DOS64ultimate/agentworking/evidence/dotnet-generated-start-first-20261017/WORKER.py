from support import *
import sys,traceback,subprocess
W=Path(__file__).resolve().parent;m=json.loads((W/'MANIFEST.json').read_text());R=Path(m['run']);R.mkdir();r=Rest(R,600);claimed=False;quiet=False;launched=False;result={'status':'failed','scope':'DOTNET_ACTUAL_NATIVE_GENERATED_START_DOS_BOOT','guest_payload_or_UI_injected':False}
try:
 for p,h in m['inputs'].items():assert sha(Path(p).read_bytes())==h,p
 assert sha(ACTIVE.read_bytes())==m['predecessor_sha256'];a=json.loads(ACTIVE.read_text());assert not a['current_host_job_live'];save(R/'ACTIVE-predecessor.json',a);state(current_host_job_live=True,session_id=R.name,run=str(R),purpose=result['scope'],owned_child_pid=os.getpid(),owned_supervisor_pid=os.getppid(),owned_terminal_window=os.environ['DOS64_TERMINAL_WINDOW']);claimed=True
 before=r.inventory();save(R/'inventory-before.json',before);assert before['info']['unique_id']=='DCAF71';r.put('machine:pause');ram=r.ram();save(R/'SETUP-terminal-before-launch.bin',ram)
 labels={x[2].lstrip('.'):int(x[1],16)for s in Path(m['setup_labels']).read_text().splitlines()if len(x:=s.split())==3};source=Path(m['setup_prg']).read_bytes()[2:];mutable={x for n in ['uci_status_read','uci_control_write','uci_id_read','uci_command_write','uci_data_read','uci_stat_read','read','store']for x in [labels[n]+1,labels[n]+2]};assert all(ram[i+0x801]==v or i+0x801 in mutable for i,v in enumerate(source[:m['setup_data_start']-0x801]))
 assert ram[0xb01a:0xb01c]==b'\7\0'and ram[labels['_rc_retained']+180]==31
 for n,v in [('_files_handle',0),('_uci_state',9),('_uci_error',0),('_uci_recovery_failed',0)]:assert ram[labels[n]]==v,n
 result['fresh_actual_SETUP_source_and_private_closed']=True;quiet=True
 # .NET owns all reset/load/input/diagnostic operations from here; parent waits.
 r.put('machine:resume');launched=True;quiet=False;state(active_application=True,possible_native_execution=True,known_FILES_quiet=False,possible_native_FILES_writer=True,launch_manifest_sha256=sha((W/'MANIFEST.json').read_bytes()))
 with (R/'dotnet.stdout').open('wb')as out,(R/'dotnet.stderr').open('wb')as err:
  process=subprocess.Popen(['/usr/local/share/dotnet/dotnet',m['driver_dll'],str(W/'DRIVER-CONFIG.json')],stdin=subprocess.DEVNULL,stdout=out,stderr=err,cwd=Path(m['driver_dll']).parent);save(R/'dotnet-child.json',{'pid':process.pid,'parent':os.getpid(),'stdin':'/dev/null','terminal':os.environ['DOS64_TERMINAL_WINDOW']})
  try:code=process.wait(timeout=510)
  except subprocess.TimeoutExpired:
   process.terminate();process.wait(timeout=15);raise TimeoutError('Owned .NET deadline; state preserved, no reset')
 result['dotnet_exit']=code;result['dotnet']=json.loads((R/'dotnet-dos/RESULT.json').read_text());assert code==0 and result['dotnet']['status']=='passed';result['status']='passed'
except BaseException as e:result.update(first_error=repr(e),traceback=traceback.format_exc());print(traceback.format_exc(),flush=True)
finally:
 try:
  if claimed:save(R/'inventory-final.json',r.inventory())
 except BaseException as e:result['final_inventory_error']=repr(e)
 save(R/'RESULT.json',result)
 if claimed:state(current_host_job_live=False,physical_result=str(R/'RESULT.json'),status='GENERATED_START_DOS_PROMPT_VER_DIR_40_80'if result['status']=='passed'else'GENERATED_START_DOS_FAILED_RESERVED',known_FILES_quiet=quiet,possible_native_FILES_writer=launched,active_application=True,possible_native_execution=True,first_error=result.get('first_error'),human_keyboard_pending=False)
 print(json.dumps(result,indent=2),flush=True)
sys.exit(0 if result['status']=='passed'else 1)
