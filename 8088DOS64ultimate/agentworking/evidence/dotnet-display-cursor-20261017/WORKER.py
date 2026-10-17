from support import *
import sys,traceback,subprocess
W=Path(__file__).resolve().parent;m=json.loads((W/'MANIFEST.json').read_text());R=Path(m['run']);R.mkdir();r=Rest(R,600);claimed=False;quiet=False;launched=False;result={'status':'failed','scope':'DOTNET_SAME_DOS_CRTC_DISPLAY_CAPTURE','guest_payload_or_UI_injected':False}
try:
 for p,h in m['inputs'].items():assert sha(Path(p).read_bytes())==h,p
 assert sha(ACTIVE.read_bytes())==m['predecessor_sha256'];a=json.loads(ACTIVE.read_text());assert not a['current_host_job_live'];save(R/'ACTIVE-predecessor.json',a);state(current_host_job_live=True,session_id=R.name,run=str(R),purpose=result['scope'],owned_child_pid=os.getpid(),owned_supervisor_pid=os.getppid(),owned_terminal_window=os.environ['DOS64_TERMINAL_WINDOW']);claimed=True
 before=r.inventory();save(R/'inventory-before.json',before);assert before['info']['unique_id']=='DCAF71';r.put('machine:pause');ram=r.ram();save(R/'native-RUN-before-continuation.bin',ram)
 labels={x[2].lstrip('.'):int(x[1],16)for s in Path(m['runtime_labels']).read_text().splitlines()if len(x:=s.split())==3};prg=Path(m['runtime_prg']).read_bytes();mutable={}
 for operand,buffer in [('dos64_uci_upload_operand','dos64_uci_command'),('dos64_uci_drain_operand','dos64_uci_data')]:
  at=labels[operand];value=int.from_bytes(ram[at:at+2],'little');assert value==0xffff or labels[buffer]<=value<labels[buffer]+896;mutable[at]=prg[at-0x801+2:at-0x801+4]
 import re
 block=Path(m['runtime_map']).read_text().split('Segment list:',1)[1].split('Exports list',1)[0];segments=[]
 for line in block.splitlines():
  row=re.fullmatch(r'([A-Z]+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+[0-9A-F]+',line)
  if not row or row[1] not in ['BASIC','CODE','RODATA','DEVICECODE','TESTCODE']:continue
  lo,hi,n=[int(row[i],16)for i in [2,3,4]];expected=prg[lo-0x801+2:hi-0x801+3];actual=bytearray(ram[lo:hi+1]);assert len(expected)==n
  for at,value in mutable.items():
   if lo<=at and at+2<=hi+1:actual[at-lo:at-lo+2]=value
  assert bytes(actual)==expected,(row[1],next((i+lo for i,(a,b)in enumerate(zip(actual,expected))if a!=b),None));segments.append({'name':row[1],'start':lo,'bytes':n,'match':True})
 assert {'BASIC','CODE','RODATA','DEVICECODE'}<=set(x['name']for x in segments)
 assert ram[labels['dos64_native_started']]==1 and int.from_bytes(ram[0xfffa:0xfffc],'little')==labels['dos64_native_nmi']
 d=ram[labels['dos64_native_diag']:labels['dos64_native_diag']+19];assert d[0]==4 and d[3]==0 and d[4]==0xa5,d.hex()
 result['fresh_running_native_source_and_IDLE_command_gate']=segments;quiet=False
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
