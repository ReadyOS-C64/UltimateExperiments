from support import *
import sys,traceback,subprocess,struct,zlib
from urllib.parse import quote
W=Path(__file__).resolve().parent;m=json.loads((W/'MANIFEST.json').read_text());R=Path(m['run']);R.mkdir();r=Rest(R,840);claimed=False;active_app=True;quiet=False;result={'status':'failed','scope':'DOTNET_STANDARD_BUFFER_ACTUAL_NATIVE_SETUP_INSTALL','native_UI_state_forged':False,'physical_matrix_input_claimed':False};f=None
try:
 for p,h in m['inputs'].items():assert sha(Path(p).read_bytes())==h,p
 assert sha(ACTIVE.read_bytes())==m['predecessor_sha256'];a=json.loads(ACTIVE.read_text());assert not a['current_host_job_live'];save(R/'ACTIVE-predecessor.json',a);state(current_host_job_live=True,session_id=R.name,run=str(R),purpose=result['scope'],owned_child_pid=os.getpid(),owned_supervisor_pid=os.getppid(),owned_terminal_window=os.environ['DOS64_TERMINAL_WINDOW'],human_keyboard_pending=False);claimed=True
 before=r.inventory();save(R/'inventory-before.json',before);assert before['info']['unique_id']=='DCAF71';r.put('machine:pause');ram=r.ram();save(R/'old-UI-coherent.bin',ram)
 oldlabels={x[2].lstrip('.'):int(x[1],16)for s in Path(m['old_labels']).read_text().splitlines()if len(x:=s.split())==3};source=Path(m['old_prg']).read_bytes()[2:];mutable={x for n in ['uci_status_read','uci_control_write','uci_id_read','uci_command_write','uci_data_read','uci_stat_read','read','store']for x in [oldlabels[n]+1,oldlabels[n]+2]};assert all(ram[i+0x801]==v or i+0x801 in mutable for i,v in enumerate(source[:m['old_data_start']-0x801]))
 assert ram[0xb01a:0xb01c]==b'\5\x32'and ram[oldlabels['_fd_closed']]==1
 assert ram[oldlabels['_uci_data']:oldlabels['_uci_data']+35]==b'$008000 BYTES LOADED TO REU $1A0000'
 for n,v in [('_files_handle',0),('_uci_state',9),('_uci_error',0),('_uci_recovery_failed',0)]:assert ram[oldlabels[n]]==v,n
 assert ram[oldlabels['sc_private']:oldlabels['sc_private']+6]==b'\2\0\0\2\3\0';result['prior_native_failure_source_bound_closed']=True;quiet=True
 r.put('machine:reset');active_app=False;r.ready('BASIC-after-knownclosed-reset');r.put('machine:resume');print('Prior actual native failure captured and known closed; reset to BASIC',flush=True)
 home=m['home'];payload=json.loads(Path(m['payload']).read_text());f=ftp();f.mkd(home)
 for name,item in payload.items():
  b=Path(item['path']).read_bytes();assert sha(b)==item['sha256'];putcheck(f,home+'/'+name,b);print('Verified',name,len(b),flush=True)
 assert f.quit().startswith('221');f=None;result['fresh20files_byteverified']=True
 r.ready('BASIC-before-load');r.put('configs/U64%20Specific%20Settings/Turbo%20Control?value=Manual');r.put('configs/U64%20Specific%20Settings/CPU%20Speed?value=%201');r.put('runners:load_prg?file='+quote(home+'/SETUP.PRG',safe=''));r.ready('BASIC-loaded');prg=Path(m['setup_prg']).read_bytes();assert r.read(0x801,0x9fff-0x801+1)==prg[2:2+0x9fff-0x801+1];result['visible_cold_source_exact']=True;result['hidden_preSYS_verified']=False
 r.put('configs/U64%20Specific%20Settings/CPU%20Speed?value=64');r.sys(2061);active_app=True;quiet=False;state(known_FILES_quiet=False,possible_native_FILES_writer=True,active_application=True,possible_native_execution=True,staged_V1_directory=home,staged_V1_directory_verified=True,setup_home=home)
 appout=R/'dotnet-ui';save(W/'DRIVER-CONFIG.json',{'host':HOST,'home':home,'output':str(appout)})
 with(R/'dotnet.stdout').open('wb')as out,(R/'dotnet.stderr').open('wb')as err:
  process=subprocess.Popen(['/usr/local/share/dotnet/dotnet',m['driver_dll'],str(W/'DRIVER-CONFIG.json')],stdin=subprocess.DEVNULL,stdout=out,stderr=err,cwd=Path(m['driver_dll']).parent);save(R/'dotnet-child.json',{'pid':process.pid,'parent':os.getpid(),'stdin':'/dev/null','owned_terminal':os.environ['DOS64_TERMINAL_WINDOW']});code=process.wait(timeout=540)
 result['dotnet_exit']=code;result['dotnet']=json.loads((appout/'RESULT.json').read_text());assert code==0 and result['dotnet']['status']=='passed';print('Actual .NET-driven native installation complete',flush=True)
 r.put('machine:pause');ram=r.ram();save(R/'SETUP-complete-RAM.bin',ram);labels={x[2].lstrip('.'):int(x[1],16)for s in Path(m['setup_labels']).read_text().splitlines()if len(x:=s.split())==3}
 assert ram[0xb01a:0xb01c]==b'\7\0'and ram[labels['_rc_retained']+180]==31
 for n,v in [('_files_handle',0),('_uci_state',9),('_uci_error',0),('_uci_recovery_failed',0)]:assert ram[labels[n]]==v,n
 r.put('machine:resume');quiet=True;result['native_private_done_outputmask31_handle0_UCIquiet']=True
 outputs=R/'outputs';outputs.mkdir();f=ftp()
 for name in ['A.IMG','B.IMG','C.IMG','DOS64.CFG','START.PRG','DOS64.PRG','DOS64.REL','DOS64.MNU','START.INO','START.RCV','START.RFW']:
  chunks=[];f.retrbinary('RETR '+home+'/'+name,chunks.append,blocksize=32768);b=b''.join(chunks);save(outputs/name,b);print('Captured native output',name,len(b),flush=True)
 for name,item in payload.items():
  chunks=[];f.retrbinary('RETR '+home+'/'+name,chunks.append,blocksize=32768);assert sha(b''.join(chunks))==item['sha256'],name
 assert f.quit().startswith('221');f=None;result['all20_sources_unchanged_after_install']=True
 sys.path.insert(0,str(W));from verify_outputs import verify
 result['independent_outputs']=verify(outputs,m['release_folder'],m['original_images'],home);save(R/'OUTPUT_INSPECTION.json',result['independent_outputs']);result['status']='passed'
except BaseException as e:result.update(first_error=repr(e),traceback=traceback.format_exc());print(traceback.format_exc(),flush=True)
finally:
 if f:f.close()
 # Preserve a live or uncertain writer. No unconditional reset or source retry.
 try:
  if claimed:save(R/'inventory-final.json',r.inventory())
 except BaseException as e:result['final_inventory_error']=repr(e)
 save(R/'RESULT.json',result)
 if claimed:state(current_host_job_live=False,physical_result=str(R/'RESULT.json'),status='DOTNET_NATIVE_SETUP_COMPLETE_VERIFIED'if result['status']=='passed'else'DOTNET_NATIVE_SETUP_FAILED_RESERVED',known_FILES_quiet=quiet,possible_native_FILES_writer=active_app and not quiet,active_application=active_app,possible_native_execution=active_app,first_error=result.get('first_error'),human_keyboard_pending=False)
 print(json.dumps({k:v for k,v in result.items()if k not in ['independent_outputs']},indent=2),flush=True)
sys.exit(0 if result['status']=='passed'else 1)
