"""Owned standalone D81, actual KERNAL IEC, .NET VICE warp/traps probe.
Run only after the root grants the shared monitor/emulator window.
"""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from vice_config import step,PROJECT
from vice_plan import run_plan

s={}
for line in (ROOT/'build/fileio/native.lbl').read_text().splitlines():
    _,value,name=line.split();s[name.lstrip('.')]=int(value,16)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
evidence=ROOT/'agentsworking/evidence/M4'/f'{stamp}-fileio-native'
evidence.mkdir(parents=True)
disk=evidence/'working.d81'
original=evidence/'original.seq';original.write_bytes(b'OLD NATIVE DOCUMENT\r')
command=['c1541','-format','fileio,se','d81',str(disk),
         '-write',str(ROOT/'build/fileio/native.prg'),'fileioprobe',
         '-write',str(original),'original,s','-list']
p=subprocess.run(command,capture_output=True,text=True)
(evidence/'package.txt').write_text(p.stdout+p.stderr);p.check_returncode()
shutil.copyfile(disk,evidence/'initial.d81')
shutil.copyfile(ROOT/'build/fileio/native.prg',evidence/'native.prg')
shutil.copyfile(ROOT/'build/fileio/native.lbl',evidence/'native.lbl')
canary=bytes((i*73+29)&255 for i in range(1024))
ready=step('result','assert.memory',start=s['fio_native_result'],end=s['fio_native_result'],equals_hex='01')
ready['retry']=dict(max_attempts=20,backoff_ms=100,jitter=False)
steps=[step('launch','vice.launch',kill_stale=False),
       step('ready','screen.wait_contains',text='READY.',wait_timeout_s=30),
       step('shim_seed','memory.write',start=0xC600,bytes_hex=canary.hex(' ')),
       step('boot','input.sequence',keys=list(b'LOAD"FILEIOPROBE",8,1\rRUN\r'),inter_key_delay_s=0.04),
       ready,
       step('channels','assert.memory',start=0x98,end=0x98,equals_hex='00'),
       step('shim','assert.memory',start=0xC600,end=0xC9FF,equals_hex=canary.hex(' ')),
       step('probe','dump.memory_ranges',ranges=[dict(label='state',start=0xC000,end=s['__BSS_RUN__']+s['__BSS_SIZE__']-1)]),
       step('capture','monitor.command',command=f'raw: screenshot "{evidence}/native-fileio.png" 2')]
plan=dict(version=1,kind='vice_task_plan',plan_id=f'supereditor-fileio-{stamp}',run_mode='gui_vice',
 global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=6580,monitor_port_span=30,
  retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),
  timeouts=dict(launch_s=30,step_s=60,read_s=2),artifact_policy=dict(capture_screen=True,capture_state=True,capture_dump=False),
  vice=dict(disk8=str(disk),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,true_drive=False,
            close_vice=True,headless=True,speed_percent=100)),steps=steps)
b=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120)
(evidence/'harness-build.txt').write_text(b.stdout+b.stderr);b.check_returncode()
artifacts,manifest=run_plan(plan,evidence)
state=(artifacts/'stages/probe/state.bin').read_bytes()
get=lambda name,n=1:state[s[name]-0xC000:s[name]-0xC000+n]
assert get('fio_native_stage')==b'\x07'
assert get('se_io_owned_temp')==b'\0' and get('se_io_owned_backup')==b'\0'
extracted=evidence/'roundtrip.seq'
p=subprocess.run(['c1541','-attach',str(disk),'-read','original,s',str(extracted),'-list'],capture_output=True,text=True)
(evidence/'disk-after.txt').write_text(p.stdout+p.stderr);p.check_returncode()
expected=bytes(range(256))+bytes(range(17))
assert extracted.read_bytes()==expected
result=dict(status='passed',evidence=str(evidence),manifest=str(manifest),
 provider_prg_sha256=hashlib.sha256((evidence/'native.prg').read_bytes()).hexdigest(),
 binary_bytes=273,channels_closed=True,shim_bytes_checked=1024,
 empty_seq_write_refused=get('fio_native_empty_byte')[0]==0x98,
 screenshot=str(evidence/'native-fileio.png'),screenshot_review='pending',
 limitations='Standalone provider probe; no file dialog/editor integration or disk-full/write-protect/restart recovery gate')
(evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
