"""Visible VICE keyboard-matrix lane, separate from PETSCII queue tests.

Uses existing .NET host.key only when no other x64sc process exists, so its
process-name focus cannot target an unrelated user's VICE. Warp is disabled
for OS keyboard delivery to avoid artificial repeats at unbounded host speed.
"""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from run_vice import step,PROJECT
from vice_plan import run_plan

existing=subprocess.run(['pgrep','-x','x64sc'],capture_output=True,text=True)
assert existing.returncode==1, 'Physical-key test requires no other x64sc instance; none will be killed'
symbols=json.loads((ROOT/'build/display-probe-report.json').read_text())['symbols']
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
evidence=ROOT/'agentsworking/evidence/M1'/f'{stamp}-keyboard'
evidence.mkdir(parents=True)
disk=evidence/'working.d81'
shutil.copyfile(ROOT/'build/supereditor.d81',disk)
steps=[step('launch','vice.launch',kill_stale=False),
       step('basic','screen.wait_contains',text='READY.',wait_timeout_s=30),
       step('disk_boot','input.sequence',keys=list(b'LOAD"DISPLAYPROBE",8,1\rRUN\r'),inter_key_delay_s=0.04)]
ready=step('ready','assert.memory',start=symbols['p_render_seq'],end=symbols['p_render_seq']+1,equals_hex='01 00')
ready['retry']=dict(max_attempts=12,backoff_ms=40,jitter=False)
steps += [ready,step('native_speed','warp.set',enabled=False,capture_after=False)]
cases=[('lower-b',11,[],0x42,0),('upper-B',11,['shift'],0xC2,1),
       ('ctrl-s',1,['control'],19,4),('home',115,[],19,0),
       ('ctrl-i',34,['control'],9,4),('pound',42,[],0x5C,0),
       ('colon',41,['shift'],0x3A,None),('at-sign',19,['shift'],0x40,None),
       ('asterisk',28,['shift'],0x2A,None),('function-f8',100,[],0x8C,1)]
for name,key,mods,char,flags in cases:
    steps.append(step(name,'host.key',key_code=key,modifiers=mods,post_delay_s=0.15))
    check=step(name+'-byte','assert.memory',start=symbols['se_last_key'],end=symbols['se_last_key'],equals_hex=f'{char:02x}')
    check['retry']=dict(max_attempts=8,backoff_ms=30,jitter=False)
    steps.append(check)
    if flags is not None:
        steps.append(step(name+'-mods','assert.memory',start=symbols['se_last_modifiers'],end=symbols['se_last_modifiers'],equals_hex=f'{flags:02x}'))
    steps.append(step(name+'-state','dump.memory_ranges',ranges=[
        dict(label='key',start=symbols['se_last_key'],end=symbols['se_last_key']+2),
        dict(label='mods-matrix',start=symbols['se_last_modifiers'],end=symbols['se_last_matrix'])]))
steps += [step('physical_mode_change','assert.memory',start=symbols['se_mode'],end=symbols['se_mode'],equals_hex='01'),
          step('physical_capture','screen.capture',label='physical-keyboard')]
plan=dict(version=1,kind='vice_task_plan',plan_id='supereditor-keyboard-'+stamp,run_mode='gui_vice',
    global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=6580,monitor_port_span=30,
        retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),
        timeouts=dict(launch_s=30,step_s=60,read_s=2),
        artifact_policy=dict(capture_screen=True,capture_state=True,capture_dump=False),
        vice=dict(disk8=str(disk),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,
                  true_drive=False,close_vice=True,headless=False,speed_percent=100)),steps=steps)
build=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120)
assert build.returncode==0,build.stdout+build.stderr
artifacts,manifest=run_plan(plan,evidence)
result=dict(status='passed',cases=len(cases),input='macOS host.key → owned visible VICE → C64 CIA matrix',
            limitations='Emulated C64 keyboard, not physical Ultimate hardware',
            evidence=str(evidence),harness_manifest=str(manifest))
(evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
