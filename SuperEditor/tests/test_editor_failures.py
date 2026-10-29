"""Native startup refusal: missing REU and missing/corrupt private disk assets."""
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from vice_config import step,PROJECT
from vice_plan import run_plan
from run_vice import native_screen_text
r=json.loads((ROOT/'build/editor-report.json').read_text());s=r['symbols'];prg=(ROOT/'build/editor.prg').read_bytes();sample=prg[2+s['sample']-0x801:2+s['sample_end']-0x801]
b=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120);assert b.returncode==0,b.stdout+b.stderr
for case,error in [('no-reu',0x78),('missing',0x20),('bad-header',0x10)]:
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');e=ROOT/'agentsworking/evidence/M3'/f'{stamp}-editor-{case}';e.mkdir(parents=True)
 disk=e/'working.d81';shutil.copyfile(ROOT/'build/supereditor.d81',disk);shutil.copyfile(ROOT/'build/editor-report.json',e/'build-report.json')
 if case!='no-reu':
  result=subprocess.run(['c1541',str(disk),'-delete','eedit'],capture_output=True,text=True);(e/'delete-log.txt').write_text(result.stdout+result.stderr);assert result.returncode==0
  if case=='bad-header':
   damaged=bytearray((ROOT/'build/overlays/eedit.seo').read_bytes());damaged[0]^=1;(e/'damaged.seo').write_bytes(damaged)
   result=subprocess.run(['c1541',str(disk),'-write',str(e/'damaged.seo'),'eedit,s'],capture_output=True,text=True);(e/'write-log.txt').write_text(result.stdout+result.stderr);assert result.returncode==0
 canary=bytes((i*73+29)&255 for i in range(1024))
 steps=[step('launch','vice.launch',kill_stale=False),step('basic','screen.wait_contains',text='READY.',wait_timeout_s=30),step('shim_seed','memory.write',start=0xC600,bytes_hex=canary.hex(' '))]
 for n,c in [('off','resourceset "REU" "0"'),('size','resourceset "REUsize" "512"')]:steps.append(step(n,'monitor.command',command='raw: '+c))
 if case!='no-reu':steps += [step('on','monitor.command',command='raw: resourceset "REU" "1"'),step('reu_before','dump.reu',mode='full',stage_tag='reu_before')]
 steps.append(step('disk_boot','input.sequence',keys=list(b'LOAD"SUPEREDITOR",8,1\rRUN\r'),inter_key_delay_s=0.04,post_delay_s=0.15))
 for name,value in [('se_status',3),('se_e_error',error),('se_h_ready',0),('se_hot_ready',0)]:
  item=step(name,'assert.memory',start=s[name],end=s[name],equals_hex=bytes([value]).hex());item['retry']=dict(max_attempts=30,backoff_ms=30,jitter=False);steps.append(item)
 steps += [step('closed','assert.memory',start=0x98,end=0x98,equals_hex='00'),step('shim_intact','assert.memory',start=0xC600,end=0xC9FF,equals_hex=canary.hex(' ')),step('native','monitor.command',command=f'raw: screenshot "{e}/native-failure.png" 2'),step('screen','dump.memory_ranges',ranges=[dict(label='matrix',start=0x4000,end=0x43E7)])]
 if case!='no-reu':steps.append(step('reu_after','dump.reu',mode='full',stage_tag='reu_after'))
 plan=dict(version=1,kind='vice_task_plan',plan_id=f'supereditor-{case}-{stamp}',run_mode='gui_vice',global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=6580,monitor_port_span=30,retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),timeouts=dict(launch_s=30,step_s=60,read_s=2),artifact_policy=dict(capture_screen=True,capture_state=True,capture_dump=False),vice=dict(disk8=str(disk),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,true_drive=False,close_vice=True,headless=True,speed_percent=100)),steps=steps)
 artifacts,manifest=run_plan(plan,e);text=native_screen_text((artifacts/'stages/screen/matrix.bin').read_bytes());(e/'screen.txt').write_text(text+'\n');assert 'Cannot start editor.' in text and 'REU required' not in text
 untouched=None
 if case!='no-reu':
  images={}
  for index in (artifacts/'dumps').glob('*.json'):
   data=json.loads(index.read_text(encoding='utf-8-sig'))
   for item in data.get('chunks',[]):
    if item.get('source')=='vice_native_reu_image':
     key='before' if 'before' in index.name else 'after' if 'after' in index.name else None
     if key:images[key]=(index.parent/Path(item['file']).name).read_bytes()
  before,after=images['before'],images['after'];assert len(before)==len(after)==8*65536
  original_piece=bytes([1,1,0])+bytes(3)+len(sample).to_bytes(3,'little')+b'\xff'*3+bytes(4)
  allowed=[(2*65536,original_piece+bytes(1008)),(3*65536,sample)];at=0
  for offset,payload in allowed:
   assert after[at:offset]==before[at:offset] and after[offset:offset+len(payload)]==payload
   at=offset+len(payload)
  assert after[at:]==before[at:];untouched=len(after)-sum(len(v) for _,v in allowed)
 result=dict(status='passed',case=case,error=error,evidence=str(e),harness_manifest=str(manifest),prg_sha256=r['sha256'],private_disk_sha256=hashlib.sha256(disk.read_bytes()).hexdigest(),channels_closed=True,shim_bytes_verified=1024,untouched_reu_bytes_verified=untouched,history_and_hot_not_started=True,screenshot=str(e/'native-failure.png'))
 (e/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
