"""Real D81/IRQ word,goto and native-case literal search in the source editor."""
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from vice_config import step,PROJECT
from vice_plan import run_plan
from run_vice import native_screen_text
from redraw_model import menu_header
from png_pixels import read_png
from cpu_editor import NAMES
from overlays import HEADER
r=json.loads((ROOT/'build/editor-report.json').read_text());s=r['symbols'];prg=(ROOT/'build/editor.prg').read_bytes();sample=prg[2+s['sample']-0x801:2+s['sample_end']-0x801]
assets={n:(ROOT/f'build/overlays/{n}.seo').read_bytes() for n in NAMES}
b=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120);assert b.returncode==0,b.stdout+b.stderr
for banks in [256,8]:
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');e=ROOT/'agentsworking/evidence/M3'/f'{stamp}-search-{banks}';e.mkdir(parents=True);disk=e/'working.d81';shutil.copyfile(ROOT/'build/supereditor.d81',disk)
 for n in ['editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json']:shutil.copyfile(ROOT/'build'/n,e/n)
 for n,image in assets.items():(e/(n+'.seo')).write_bytes(image)
 steps=[];keys=0;captures=[]
 def memory(ident,name,value,width=1):
  at=s[name] if isinstance(name,str) else name;raw=value if isinstance(value,bytes) else value.to_bytes(width,'little')
  item=step(ident,'assert.memory',start=at,end=at+len(raw)-1,equals_hex=raw.hex(' '));item['retry']=dict(max_attempts=30,backoff_ms=30,jitter=False);steps.append(item)
 def idle(ident,error=0):
  for name in ['se_e_job','se_n_owned','se_doc_read_locks','se_v_nav_busy','se_s_owned','se_s_active']:memory(ident+'_'+name,name,0)
  memory(ident+'_error','se_e_error',error);memory(ident+'_draw','se_e_redraw',bytes([0,0]))
 def send(ident,data,error=0):
  global keys
  steps.append(step(ident,'input.sequence',keys=list(data),inter_key_delay_s=0.04,post_delay_s=0.08));keys+=len(data)
  memory(ident+'_consumed','se_key_sequence',keys,2);idle(ident,error)
 def typed(ident,data,caret=None,error=0):
  send(ident+'_text',bytes([0x88])+data);send(ident+'_enter',bytes([13]),error)
  if caret is not None:memory(ident+'_caret','se_hot_caret',caret,3)
 def capture(ident):
  captures.append(ident);steps.append(step(ident+'_native','monitor.command',command=f'raw: screenshot "{e}/native-{ident}.png" 2'))
  steps.append(step(ident+'_ram','dump.memory_ranges',ranges=[dict(label='matrix',start=0x4000,end=0x43E7),dict(label='font',start=0x4800,end=0x4FFF),dict(label='colors',start=0xD800,end=0xDBE7)]))
 canary=bytes((i*73+29)&255 for i in range(1024))
 steps += [step('launch','vice.launch',kill_stale=False),step('basic','screen.wait_contains',text='READY.',wait_timeout_s=30),step('shim_seed','memory.write',start=0xC600,bytes_hex=canary.hex(' '))]
 if banks==8:
  for name,text in [('off','resourceset "REU" "0"'),('size','resourceset "REUsize" "512"'),('on','resourceset "REU" "1"')]:steps.append(step(name,'monitor.command',command='raw: '+text))
 steps += [step('reu_before','dump.reu',mode='full',stage_tag='reu_before'),step('disk_boot','input.sequence',keys=list(b'LOAD"SUPEREDITOR",8,1\rRUN\r'),inter_key_delay_s=0.04,post_delay_s=0.15)]
 memory('ready','se_status',1);memory('first_draw','se_e_draw_sequence',1,2);idle('initial')
 send('navigator',bytes([0x85,0x4E]));capture('menu');send('menu_word_right',bytes([0x57]));memory('word_start','se_hot_caret',2,3)
 send('ctrl_word_left',bytes([1]));memory('word_back','se_hot_caret',0,3)
 # Previous word from first word's start reaches0; next word returns2.
 send('ctrl_word_right',bytes([0x17]));memory('word_again','se_hot_caret',2,3)
 starts=[0]+[i+1 for i,v in enumerate(sample) if v==13]
 send('goto_prompt',bytes([7]));memory('goto_ui','se_e_ui',2);capture('goto-prompt')
 send('goto_line',b'8\r');memory('goto_eight','se_hot_caret',starts[7],3);capture('goto')
 found=sample.find(b'RTS',starts[7]);assert found>=0
 send('find_prompt',bytes([6]));send('find_literal_input',b'RTS\r');memory('literal_caret','se_hot_caret',found,3);capture('find')
 typed('typed_repeat',b'NEXT MATCH');found=sample.find(b'RTS');memory('wrapped_caret','se_hot_caret',found,3);memory('wrapped_flag','se_s_wrapped',1);capture('wrapped')
 send('ctrl_repeat',bytes([0x0E]));found=sample.find(b'RTS',found+1);memory('ctrl_repeat_caret','se_hot_caret',found,3)
 upper=bytes([0xD2,0xD4,0xD3]);assert sample.find(upper)<0
 typed('sensitive_miss',b'FIND '+upper,error=0x7E);memory('miss_keeps_caret','se_hot_caret',found,3);capture('not-found')
 typed('insensitive',b'FINDI '+upper,found);memory('query_native_case','se_s_pattern',upper);capture('case-insensitive')
 typed('invalid_goto',b'GOTO 0',error=0x7C);memory('bad_goto_keeps_caret','se_hot_caret',found,3);capture('invalid-line');send('cancel_argument',bytes([3]))
 typed('back_to_top',b'GOTO 1',0);capture('final')
 memory('source_length','se_doc_length',len(sample),3);memory('source_generation','se_doc_generation',2,2);memory('history_current','se_h_current',1,4);memory('history_saved','se_h_saved',1,4);memory('history_empty','se_h_end',0,2);memory('no_append','se_hot_pending',0)
 memory('channels_closed',0x98,0);memory('shim_intact',0xC600,canary)
 steps += [step('reu_after','dump.reu',mode='full',stage_tag='reu_after')]
 plan=dict(version=1,kind='vice_task_plan',plan_id=f'supereditor-search-{banks}-{stamp}',run_mode='gui_vice',global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=6580,monitor_port_span=30,retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),timeouts=dict(launch_s=30,step_s=60,read_s=2),artifact_policy=dict(capture_screen=True,capture_state=True,capture_dump=False),vice=dict(disk8=str(disk),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,true_drive=False,close_vice=True,headless=True,speed_percent=100)),steps=steps)
 artifacts,manifest=run_plan(plan,e);pixels_checked=0
 for scene in captures:
  folder=artifacts/f'stages/{scene}_ram';matrix=(folder/'matrix.bin').read_bytes();font=(folder/'font.bin').read_bytes();colors=(folder/'colors.bin').read_bytes();decoded=native_screen_text(matrix);(e/(scene+'-screen.txt')).write_text(decoded+'\n')
  header,header_colors=menu_header();assert matrix[:80]==header and bytes(v&15 for v in colors[:80])==header_colors
  if scene=='menu':assert 'Find next' in decoded and 'Go to line' in decoded
  if scene=='goto-prompt':assert 'Command:goto ' in decoded
  if scene=='not-found':assert 'No match' in decoded and 'F6 Help' in decoded
  if scene=='invalid-line':assert 'Invalid number/text' in decoded and 'F6 Help' in decoded
  w,h,pix=read_png(e/f'native-{scene}.png');assert(w,h)==(384,272);background=pix[0]
  assert all((v&15)==15 for v in colors[24*40:25*40])
  for row in range(25):
   for col in range(40):
    for gy in range(8):
     pattern=font[matrix[row*40+col]*8+gy]
     for gx in range(8):
      assert (pix[(35+row*8+gy)*w+32+col*8+gx]!=background)==bool(pattern&(128>>gx)),(scene,row,col,gx,gy)
      pixels_checked+=1
 images={}
 for index in (artifacts/'dumps').glob('*.json'):
  data=json.loads(index.read_text(encoding='utf-8-sig'))
  for item in data.get('chunks',[]):
   if item.get('source')=='vice_native_reu_image':
    key='before' if 'before' in index.name else 'after' if 'after' in index.name else None
    if key:images[key]=(index.parent/Path(item['file']).name).read_bytes()
 before,after=images['before'],images['after'];assert len(before)==len(after)==banks*65536
 leaf=bytes([1,1,0])+bytes(3)+len(sample).to_bytes(3,'little')+b'\xff'*3+bytes(4)+bytes(1008)
 allowed=[(65536+i*4096,assets[n][HEADER:]) for i,n in enumerate(NAMES)]+[(2*65536,leaf),(3*65536,sample)];at=0
 for offset,payload in sorted(allowed):
  assert after[at:offset]==before[at:offset],('unowned REU',hex(offset))
  assert after[offset:offset+len(payload)]==payload,hex(offset);at=offset+len(payload)
 assert after[at:]==before[at:]
 result=dict(status='passed',evidence=str(e),harness_manifest=str(manifest),prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],overlay_sha256={n:hashlib.sha256(v).hexdigest() for n,v in assets.items()},reu_banks=banks,input='native-byte queue via IRQ,not physical chord proof',keys_consumed=keys,source_bytes_verified=len(sample),source_unchanged=True,word_menu_and_shortcuts=True,goto_prompt_and_decimal=True,native_case_and_insensitive_search=True,find_next_wrap=True,not_found_and_bad_line_preserve_caret=True,screenshots=len(captures),captured_vic_pixels_checked=pixels_checked,shim_bytes_verified=1024,untouched_reu_bytes_verified=len(after)-sum(len(v) for _,v in allowed),limitations='Source40 commands;selection/clipboard/files/styles/other integrated modes and normal PAL/NTSC timing remain open.')
 (e/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
