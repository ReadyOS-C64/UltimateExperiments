"""One status row and native F6 help, through actual IRQ input on copied D81."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from cpu_editor import NAMES
from vice_config import PROJECT,step
from vice_plan import run_plan
from redraw_model import source40,verify_screen,native_text
from run_vice import native_screen_text
from png_pixels import read_png
r=json.loads((ROOT/'build/editor-report.json').read_text());s=r['symbols']
p=(ROOT/'build/editor.prg').read_bytes()
sample=p[2+s['sample']-0x801:2+s['sample_end']-0x801]
marker=native_text('THIS IS DOCUMENT ROW 22')
source=sample+b'\r'+marker
assets={n:(ROOT/f'build/overlays/{n}.seo').read_bytes() for n in NAMES}
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
e=ROOT/'agentsworking/evidence/M3'/(stamp+'-single-status');e.mkdir(parents=True)
for name in ['editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json']:
 shutil.copyfile(ROOT/'build'/name,e/name)
for name,data in assets.items():(e/(name+'.seo')).write_bytes(data)
shutil.copyfile(ROOT/'build/supereditor.d81',e/'working.d81')
b=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120)
assert b.returncode==0,b.stdout+b.stderr
steps=[];keys=0;captures=[]
canary=bytes((i*73+29)&255 for i in range(1024))
def memory(ident,name,value,width=1):
 at=s[name] if isinstance(name,str) else name
 data=value if isinstance(value,bytes) else value.to_bytes(width,'little')
 x=step(ident,'assert.memory',start=at,end=at+len(data)-1,equals_hex=data.hex(' '))
 x['retry']=dict(max_attempts=30,backoff_ms=30,jitter=False);steps.append(x)
def idle(ident,error=0):
 for n in ['se_e_job','se_e_draw_busy','se_e_redraw','se_doc_read_locks','se_v_nav_busy','se_n_owned','se_b_phase','se_clip_busy']:
  memory(ident+'_'+n,n,0)
 memory(ident+'_error','se_e_error',error)
def send(ident,data,error=0):
 global keys
 steps.append(step(ident,'input.sequence',keys=list(data),inter_key_delay_s=0.04,post_delay_s=0.08));keys+=len(data)
 memory(ident+'_consumed','se_key_sequence',keys,2);idle(ident,error)
def capture(ident,ui=0,error=0):
 captures.append((ident,ui,error))
 memory(ident+'_ui','se_e_ui',ui)
 steps.append(step(ident+'_native','monitor.command',command=f'raw: screenshot "{e}/native-{ident}.png" 2'))
 steps.append(step(ident+'_ram','dump.memory_ranges',ranges=[
  dict(label='state',start=0xC000,end=0xC5FF),dict(label='view',start=0x8C00,end=0x8CFF),
  dict(label='metadata',start=0x9A00,end=0x9FFF),dict(label='hot',start=0x9200,end=0x99FF),
  dict(label='matrix',start=0x4000,end=0x43E7),dict(label='font',start=0x4800,end=0x4FFF),
  dict(label='colors',start=0xD800,end=0xDBE7)]))
steps += [step('launch','vice.launch',kill_stale=False),step('basic','screen.wait_contains',text='READY.',wait_timeout_s=30),
 step('shim_seed','memory.write',start=0xC600,bytes_hex=canary.hex(' '))]
for name,text in [('reu_off','resourceset "REU" "0"'),('reu_size','resourceset "REUsize" "512"'),('reu_on','resourceset "REU" "1"')]:
 steps.append(step(name,'monitor.command',command='raw: '+text))
steps.append(step('boot','input.sequence',keys=list(b'LOAD"SUPEREDITOR",8,1\rRUN\r'),inter_key_delay_s=0.04,post_delay_s=0.15))
memory('ready','se_status',1);memory('first_draw','se_e_draw_sequence',1,2);idle('ready')
steps.append(step('reu_before','dump.reu',mode='full',stage_tag='reu_before'))
capture('initial')
send('bottom',bytes([0x88])+b'BOTTOM\r')
send('fill_last_row',b'\r'+marker)
memory('last_caret','se_hot_caret',len(source),3);memory('last_caret_row','se_v_caret_row',21)
memory('top_retained','se_v_top',0,3);memory('pending','se_hot_pending',1)
capture('last-row')
send('f6_help',bytes([0x8B]));memory('help_heading','se_e_menu',6);capture('help',1)
send('f6_close',bytes([0x8B]));capture('restored')
send('command_draft',bytes([0x88])+b'HELP');capture('command',2)
send('f6_from_command',bytes([0x8B]));capture('help-from-command',1)
send('stop_help',bytes([3]));send('unknown_control',bytes([0x1F]),0x77);capture('error',error=0x77)
send('f6_from_error',bytes([0x8B]));send('f6_final_close',bytes([0x8B]));capture('final')
memory('source_still_pending','se_hot_pending',1);memory('committed_unchanged','se_doc_length',len(sample),3)
memory('caret_preserved','se_hot_caret',len(source),3);memory('shim_intact',0xC600,canary);memory('channels_closed',0x98,0)
steps.append(step('reu_after','dump.reu',mode='full',stage_tag='reu_after'))
plan=dict(version=1,kind='vice_task_plan',plan_id='supereditor-one-status-'+stamp,run_mode='gui_vice',
 global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=6580,monitor_port_span=30,
 retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),timeouts=dict(launch_s=30,step_s=60,read_s=2),
 artifact_policy=dict(capture_screen=False,capture_state=False,capture_dump=False),
 vice=dict(disk8=str(e/'working.d81'),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,
 true_drive=False,close_vice=True,headless=True,speed_percent=100)),steps=steps)
artifacts,manifest=run_plan(plan,e)
def get(folder,name,width=1):
 at=s[name]
 for label,base,end in [('state',0xC000,0xC600),('view',0x8C00,0x8D00),('metadata',0x9A00,0xA000)]:
  if base<=at and at+width<=end:
   raw=(folder/(label+'.bin')).read_bytes()[at-base:at-base+width];assert len(raw)==width
   return int.from_bytes(raw,'little')
 raise AssertionError(('uncaptured symbol',name,hex(at)))
pixels_checked=plain_screens=0
for ident,ui,error in captures:
 folder=artifacts/'stages'/(ident+'_ram')
 matrix=(folder/'matrix.bin').read_bytes();colors=(folder/'colors.bin').read_bytes();font=(folder/'font.bin').read_bytes()
 decoded=native_screen_text(matrix);(e/(ident+'-screen.txt')).write_text(decoded+'\n')
 current=sample if ident=='initial' else source;caret=0 if ident=='initial' else len(source)
 hot=(folder/'hot.bin').read_bytes()
 visible=hot[:get(folder,'se_hot_left',2)]+hot[get(folder,'se_hot_right',2):]
 assert get(folder,'se_hot_base',3)==0 and visible==current,(ident,'source changed')
 assert get(folder,'se_doc_length',3)==len(sample) and get(folder,'se_doc_generation',2)==2
 assert get(folder,'se_hot_caret',3)==caret and get(folder,'se_v_top',3)==0
 assert get(folder,'se_e_ui')==ui and get(folder,'se_e_error')==error
 assert all((v&15)==15 for v in colors[24*40:]),ident
 assert all((v&15)==1 for v in colors[23*40:24*40]) or ident!='initial'
 if ui==0:
  expected=source40(current,0,caret,pending=ident!='initial',error=error)
  verify_screen(matrix,colors,expected,tag='native '+ident);plain_screens+=1
  anchors=tuple(int.from_bytes((folder/'view.bin').read_bytes()[s['se_v_rows']-0x8C00+i*3:s['se_v_rows']-0x8C00+i*3+3],'little') for i in range(22))
  assert anchors+(get(folder,'se_v_bottom',3),)==expected.anchors
  assert 'F6 Help' in decoded.splitlines()[24]
  if ident!='initial':assert 'THIS IS DOCUMENT ROW 22' in decoded.splitlines()[23]
 elif ui==1:
  assert 'SuperEditor keyboard' in decoded and 'F6 or RUN/STOP closes help' in decoded
 else:
  assert decoded.splitlines()[24].startswith('Command:help'),decoded.splitlines()[24]
 w,h,pixels=read_png(e/f'native-{ident}.png');assert(w,h)==(384,272)
 background=pixels[0]
 for row in range(25):
  for col in range(40):
   for y in range(8):
    pattern=font[matrix[row*40+col]*8+y]
    for x in range(8):
     assert (pixels[(35+row*8+y)*w+32+col*8+x]!=background)==bool(pattern&(128>>x)),(ident,row,col,x,y)
     pixels_checked+=1
images={}
for index in (artifacts/'dumps').glob('*.json'):
 for item in json.loads(index.read_text(encoding='utf-8-sig')).get('chunks',[]):
  if item.get('source')=='vice_native_reu_image':
   key='before' if 'before' in index.name else 'after' if 'after' in index.name else None
   if key:images[key]=(index.parent/Path(item['file']).name).read_bytes()
assert len(images['before'])==512*1024 and images['before']==images['after'],'help/status wrote REU'
result=dict(status='passed',prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],
 overlay_sha256={n:hashlib.sha256(data).hexdigest() for n,data in assets.items()},evidence=str(e),manifest=str(manifest),
 body_rows=22,status_rows=1,status_row=24,function_key='F6/native8B',
 f6_toggle_and_prompt_global=True,pending_source_preserved=len(source),committed_source_preserved=len(sample),
 bottom_body_row=23,complete_plain_screens_checked=plain_screens,native_screenshots=len(captures),
 native_vic_glyph_pixels_checked=pixels_checked,full_reu_bytes_unchanged=512*1024,shim_bytes_checked=1024,
 limitations='IRQ native-byte input, not physical chord proof. Source40 UI only; other modes remain separate.')
(e/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
