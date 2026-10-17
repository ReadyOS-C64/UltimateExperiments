#!/usr/bin/env python3
from pathlib import Path
import sys
W=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(W/'.absent-supervisor-cache')
if Path(sys.pycache_prefix).exists():raise RuntimeError('Absent source-only cache required')
import argparse,json,hashlib,os,subprocess,time,signal
p=argparse.ArgumentParser();p.add_argument('--entry',required=True);p.add_argument('--manifest',required=True);p.add_argument('--sha',required=True);p.add_argument('--output',required=True);p.add_argument('--terminal',required=True);a=p.parse_args();mf=Path(a.manifest).resolve();body=mf.read_bytes()
if hashlib.sha256(body).hexdigest()!=a.sha:raise ValueError('Exact supervisor manifest')
m=json.loads(body);entry=Path(a.entry).resolve()
for n,h in m['files'].items():
 if hashlib.sha256(Path(n).read_bytes()).hexdigest()!=h:raise ValueError('Changed frozen source '+n)
if m['files'].get(str(entry))!=hashlib.sha256(entry.read_bytes()).hexdigest():raise ValueError('Exact child entry pin')
if not a.terminal.isdecimal()or os.isatty(0)or os.isatty(1)or os.isatty(2):raise ValueError('Owned background Terminal metadata/devnull/logs')
if m.get('schema')=='V1_NATIVE_SETUP_UI_PHYSICAL_PURPOSE_1':
 if entry!=Path(m['entry']).resolve()or Path(a.output).resolve()!=Path(m['detached']).resolve()or m['watchdog_seconds']!=900 or m['interrupt_grace_seconds']!=120:raise ValueError('Exact physical child/output/budgets')
elif m.get('schema')!='LOCAL_SUPERVISOR_TEST_1':raise ValueError('Exact physical purpose or local process-only test')
watchdog=m['watchdog_seconds'];grace=m['interrupt_grace_seconds']
if not isinstance(watchdog,(int,float))or not 0<watchdog<=900 or not isinstance(grace,(int,float))or not 0<grace<=120:raise ValueError('Finite supervisor budgets')
out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
def save(name,value):
 q=out/name;t=q.with_suffix(q.suffix+'.tmp')
 with t.open('x')as f:f.write(json.dumps(value,indent=2)+'\n');f.flush();os.fsync(f.fileno())
 os.replace(t,q)
start=time.monotonic();save('supervisor.json',{'pid':os.getpid(),'parent_pid':os.getppid(),'stdin_is_tty':os.isatty(0),'stdin':'/dev/null','terminal':a.terminal,'entry':str(entry),'manifest_sha256':a.sha,'watchdog_seconds':watchdog,'interrupt_grace_seconds':grace,'started_monotonic':start})
env=dict(os.environ,DOS64_TERMINAL_WINDOW=a.terminal);signals=[];timed_out=False
with(out/'child.log').open('xb')as log:
 child=subprocess.Popen(['/usr/bin/python3','-B',str(entry),'--manifest',str(mf),'--sha',a.sha],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True,close_fds=True)
 save('child.json',{'pid':child.pid,'supervisor_pid':os.getpid(),'terminal':a.terminal,'new_session':True,'stdin':'/dev/null','stdout_stderr':str(out/'child.log')})
 try:rc=child.wait(timeout=watchdog)
 except subprocess.TimeoutExpired:
  timed_out=True
  try:os.killpg(child.pid,signal.SIGINT);signals.append({'signal':'SIGINT','owned_process_group':child.pid,'at':time.monotonic()})
  except ProcessLookupError:pass
  try:rc=child.wait(timeout=grace)
  except subprocess.TimeoutExpired:
   try:os.killpg(child.pid,signal.SIGKILL);signals.append({'signal':'SIGKILL','owned_process_group':child.pid,'at':time.monotonic()})
   except ProcessLookupError:pass
   rc=child.wait(timeout=5)
 supervisor_rc=124 if timed_out else rc if rc>=0 else 128-rc
 save('exit.json',{'pid':child.pid,'child_exit_code':rc,'exit_code':rc,'supervisor_intended_exit_code':supervisor_rc,'wall_watchdog_triggered':timed_out,'signals':signals,'finished_monotonic':time.monotonic()})
raise SystemExit(supervisor_rc)
