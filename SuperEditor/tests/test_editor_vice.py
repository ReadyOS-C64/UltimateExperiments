"""Real SUPEREDITOR D81/ROM/IRQ input, pending text, menus and journal replay."""
from datetime import datetime,timezone
import binascii,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from vice_config import step,PROJECT
from vice_plan import run_plan
from run_vice import native_screen_text
from redraw_model import menu_header
from png_pixels import read_png
from cpu_editor import NAMES
r=json.loads((ROOT/'build/editor-report.json').read_text());s=r['symbols'];prg=(ROOT/'build/editor.prg').read_bytes()
assets={n:(ROOT/f'build/overlays/{n}.seo').read_bytes() for n in NAMES}
from overlays import HEADER
sample=prg[2+s['sample']-0x801:2+s['sample_end']-0x801]
assert sample.startswith(bytes([35,32,0xD3])) and 0<len(sample)<=512
b=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120)
assert b.returncode==0,b.stdout+b.stderr
for banks in [256,8]:
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');e=ROOT/'agentsworking/evidence/M3'/f'{stamp}-editor-{banks}';e.mkdir(parents=True)
 disk=e/'working.d81';shutil.copyfile(ROOT/'build/supereditor.d81',disk)
 for n in ['editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json']:shutil.copyfile(ROOT/'build'/n,e/n)
 for n,data in assets.items():(e/(n+'.seo')).write_bytes(data)
 canary=bytes((i*73+29)&255 for i in range(1024));steps=[];keys=0
 def memory(ident,name,value,width=1):
  at=s[name] if isinstance(name,str) else name;data=value if isinstance(value,bytes) else value.to_bytes(width,'little')
  item=step(ident,'assert.memory',start=at,end=at+len(data)-1,equals_hex=data.hex(' '));item['retry']=dict(max_attempts=30,backoff_ms=30,jitter=False);steps.append(item)
 def idle(ident):
  memory(ident+'_job','se_e_job',0);memory(ident+'_error','se_e_error',0)
  memory(ident+'_draw','se_e_redraw',bytes([0,0]))
 def send(ident,data):
  global keys
  steps.append(step(ident,'input.sequence',keys=list(data),inter_key_delay_s=0.04,post_delay_s=0.08));keys+=len(data)
  memory(ident+'_consumed','se_key_sequence',keys,2);idle(ident)
 def capture(ident):
  steps.append(step(ident+'_native','monitor.command',command=f'raw: screenshot "{e}/native-{ident}.png" 2'))
  steps.append(step(ident+'_ram','dump.memory_ranges',ranges=[dict(label='matrix',start=0x4000,end=0x43E7),dict(label='colors',start=0xD800,end=0xDBE7),dict(label='font',start=0x4800,end=0x4FFF)]))
 steps += [step('launch','vice.launch',kill_stale=False),step('basic','screen.wait_contains',text='READY.',wait_timeout_s=30),step('shim_seed','memory.write',start=0xC600,bytes_hex=canary.hex(' '))]
 if banks==8:
  for n,c in [('off','resourceset "REU" "0"'),('size','resourceset "REUsize" "512"'),('on','resourceset "REU" "1"')]:steps.append(step(n,'monitor.command',command='raw: '+c))
 steps += [step('reu_before','dump.reu',mode='full',stage_tag='reu_before'),step('disk_boot','input.sequence',keys=list(b'LOAD"SUPEREDITOR",8,1\rRUN\r'),inter_key_delay_s=0.04,post_delay_s=0.15)]
 memory('ready','se_status',1);memory('first_draw','se_e_draw_sequence',1,2);idle('initial');capture('initial')
 send('typing',bytes([0xD8,0x59,0xDA,13]));memory('pending','se_hot_pending',1);memory('pending_does_not_publish','se_doc_length',len(sample),3);capture('pending')
 send('left',bytes([0x9D]));send('delete',bytes([0x14]));memory('caret_after_delete','se_hot_caret',2,3)
 send('undo_delete',bytes([0x1A]));send('undo_typing',bytes([0x1A]));memory('clean_after_undo','se_h_dirty',0);capture('undo')
 send('redo_typing',bytes([0x19]));send('redo_delete',bytes([0x19]));memory('two_records','se_h_end',150,2)
 send('menu',bytes([0x85,0x45]));memory('edit_menu','se_e_menu',2);capture('menu')
 send('menu_undo',bytes([0x55]));memory('menu_closes','se_e_ui',0)
 send('command_line',bytes([0x88,0x52,0x45,0x44,0x4F]));memory('command_active','se_e_ui',2);capture('command')
 send('typed_redo',bytes([13]));memory('final_length','se_doc_length',len(sample)+3,3);memory('final_caret','se_hot_caret',2,3)
 memory('final_generation','se_doc_generation',10,2);memory('nodes','se_h_current',(3).to_bytes(4,'little')+(1).to_bytes(4,'little')+(3).to_bytes(4,'little'))
 memory('history_idle','se_h_phase',bytes([0,1,0]));memory('source_unlocked','se_doc_read_locks',0);memory('channels_closed',0x98,0);memory('shim_intact',0xC600,canary)
 capture('final')
 steps += [step('metadata','dump.memory_ranges',ranges=[dict(label='state',start=0x9A00,end=0x9FFF)]),step('reu_after','dump.reu',mode='full',stage_tag='reu_after')]
 plan=dict(version=1,kind='vice_task_plan',plan_id=f'supereditor-editor-{banks}-{stamp}',run_mode='gui_vice',global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=6580,monitor_port_span=30,retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),timeouts=dict(launch_s=30,step_s=60,read_s=2),artifact_policy=dict(capture_screen=True,capture_state=True,capture_dump=False),vice=dict(disk8=str(disk),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,true_drive=False,close_vice=True,headless=True,speed_percent=100)),steps=steps)
 artifacts,manifest=run_plan(plan,e)
 # Matrix/font/color dumps plus independent glyph bit lookup verify complete
 # native VIC frames. Existing native PAL viewport is32,35 inside384x272.
 pixel_checks=0
 for name in ['initial','pending','undo','menu','command','final']:
  folder=artifacts/f'stages/{name}_ram';matrix=(folder/'matrix.bin').read_bytes();font=(folder/'font.bin').read_bytes();colors=(folder/'colors.bin').read_bytes()
  decoded=native_screen_text(matrix);(e/(name+'-screen.txt')).write_text(decoded+'\n')
  header,header_colors=menu_header();assert matrix[:80]==header and bytes(v&15 for v in colors[:80])==header_colors
  assert all((v&15)==15 for v in colors[24*40:25*40])
  if name=='pending':assert 'XyZ' in decoded and 'Modified' in decoded
  if name=='undo':assert 'Clean' in decoded and '# SuperEditor' in decoded
  if name=='menu':assert 'Undo' in decoded and 'Redo' in decoded
  if name=='command':assert 'Command:redo' in decoded
  w,h,pixels=read_png(e/f'native-{name}.png');assert(w,h)==(384,272);bg=pixels[0]
  for row in range(25):
   for col in range(40):
    code=matrix[row*40+col]
    for gy in range(8):
     pattern=font[code*8+gy]
     for gx in range(8):
      expected=bool(pattern&(128>>gx));actual=pixels[(35+row*8+gy)*w+32+col*8+gx]!=bg
      assert actual==expected,(name,row,col,code,gx,gy,'native VIC pixel')
      pixel_checks+=1
 images={}
 for index in (artifacts/'dumps').glob('*.json'):
  data=json.loads(index.read_text(encoding='utf-8-sig'))
  for item in data.get('chunks',[]):
   if item.get('source')=='vice_native_reu_image':
    key='before' if 'before' in index.name else 'after' if 'after' in index.name else None
    if key:images[key]=(index.parent/Path(item['file']).name).read_bytes()
 before,after=images['before'],images['after'];assert len(before)==len(after)==banks*65536
 def ref(identity,offset,length):return bytes([identity,1,0])+offset.to_bytes(3,'little')+length.to_bytes(3,'little')
 def piece(identity,offset,length):return ref(identity,offset,length)+b'\xff'*3+bytes(4)
 def record(before_node,after_node,pos,removed,inserted,before_caret,after_caret,source_offset,typing):
  head=bytearray(64);head[:5]=b'SEH1\x01';head[5]=int(typing);head[6:8]=(75).to_bytes(2,'little');head[8:12]=before_node.to_bytes(4,'little');head[12:16]=after_node.to_bytes(4,'little')
  head[16:21]=bytes([1,1,0,1,0]);head[21:26]=bytes([2,1,0,1,0]);head[26:29]=pos.to_bytes(3,'little');head[29:32]=removed.to_bytes(3,'little');head[32:35]=inserted.to_bytes(3,'little');head[35]=int(bool(removed));head[37]=int(bool(inserted));head[39:42]=before_caret.to_bytes(3,'little');head[42:45]=after_caret.to_bytes(3,'little');head[45]=int(typing)
  body=ref(2,source_offset,removed or inserted)+(75).to_bytes(2,'little');head[56:58]=binascii.crc_hqx(body,0xFFFF).to_bytes(2,'little');head[58:60]=binascii.crc_hqx(head[:58]+head[60:],0xFFFF).to_bytes(2,'little');return bytes(head)+body
 first=record(1,2,0,0,4,0,4,0,True);second=record(2,3,2,1,0,3,2,2,False)
 data_banks=16 if banks==256 else 1;app_bank=3+data_banks;journal_bank=3+2*data_banks
 full_leaf=piece(2,0,4)+piece(1,0,len(sample))+bytes(992)
 final_leaf=piece(2,0,2)+piece(2,3,1)+piece(1,0,len(sample))+bytes(976)
 allowed=[(65536+i*4096,assets[n][HEADER:]) for i,n in enumerate(NAMES)]
 allowed += [(2*65536,final_leaf+full_leaf),(3*65536,sample),(app_bank*65536,bytes([0xD8,0x59,0xDA,13])),(journal_bank*65536,first+second),(journal_bank*65536+0xB000,second)]
 cursor=0
 for offset,payload in sorted(allowed):
  assert after[cursor:offset]==before[cursor:offset],f'unowned REU changed before{offset:x}'
  actual=after[offset:offset+len(payload)]
  assert actual==payload,(hex(offset),next((i for i,(a,b) in enumerate(zip(actual,payload)) if a!=b),None))
  cursor=offset+len(payload)
 assert after[cursor:]==before[cursor:]
 # Independently reconstruct final published source from actual REU descriptors.
 actual=bytearray()
 for i in range(3):
  at=2*65536+i*16;identity=after[at];offset=int.from_bytes(after[at+3:at+6],'little');length=int.from_bytes(after[at+6:at+9],'little');physical=3 if identity==1 else app_bank if identity==2 else None
  assert physical is not None;actual.extend(after[physical*65536+offset:physical*65536+offset+length])
 assert bytes(actual)==bytes([0xD8,0x59,13])+sample
 result=dict(status='passed',evidence=str(e),harness_manifest=str(manifest),prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],overlay_sha256={n:hashlib.sha256(v).hexdigest() for n,v in assets.items()},reu_banks=banks,actual_rom_disk_transport=True,input='KERNAL native-byte queue, not physical chord proof',keys_consumed=keys,screenshots=6,captured_vic_pixels_checked=pixel_checks,source_bytes_reconstructed=len(actual),document_generation=10,current_node=3,saved_node=1,journal_records=2,append_bytes=4,shim_bytes_verified=1024,untouched_reu_bytes_verified=len(after)-sum(len(data) for _,data in allowed),limitations='First source-edit UI. Vertical/page/selection/files/formatting/modes and PAL/NTSC performance remain open.')
 (e/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
