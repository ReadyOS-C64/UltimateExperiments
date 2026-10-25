"""Actual keyboard/menu/typed indexed navigation with native VIC/source checks."""
from datetime import datetime,timezone
import binascii,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from vice_config import step,PROJECT
from vice_plan import run_plan
from run_vice import native_screen_text
from redraw_model import menu_header
from png_pixels import read_png
from navigation_model import move,visual_rows
from cpu_editor import NAMES
from overlays import HEADER
r=json.loads((ROOT/'build/editor-report.json').read_text());s=r['symbols'];prg=(ROOT/'build/editor.prg').read_bytes();sample=prg[2+s['sample']-0x801:2+s['sample_end']-0x801]
assets={n:(ROOT/f'build/overlays/{n}.seo').read_bytes() for n in NAMES}
b=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120);assert b.returncode==0,b.stdout+b.stderr
for banks in [256,8]:
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');e=ROOT/'agentsworking/evidence/M3'/f'{stamp}-navigation-{banks}';e.mkdir(parents=True);disk=e/'working.d81';shutil.copyfile(ROOT/'build/supereditor.d81',disk)
 for n in ['editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json']:shutil.copyfile(ROOT/'build'/n,e/n)
 for n,image in assets.items():(e/(n+'.seo')).write_bytes(image)
 steps=[];keys=0;caret=0;preferred=None;source=sample;captures=[];capture_sources={};capture_carets={};trace=[]
 def memory(ident,name,value,width=1):
  at=s[name] if isinstance(name,str) else name;raw=value if isinstance(value,bytes) else value.to_bytes(width,'little')
  item=step(ident,'assert.memory',start=at,end=at+len(raw)-1,equals_hex=raw.hex(' '));item['retry']=dict(max_attempts=30,backoff_ms=30,jitter=False);steps.append(item)
 def idle(ident):
  for name in ['se_e_job','se_e_error','se_n_owned','se_doc_read_locks','se_v_nav_busy']:memory(ident+'_'+name,name,0)
  memory(ident+'_draw','se_e_redraw',bytes([0,0]))
 def send(ident,data):
  global keys
  steps.append(step(ident,'input.sequence',keys=list(data),inter_key_delay_s=0.04,post_delay_s=0.08));keys+=len(data)
  memory(ident+'_consumed','se_key_sequence',keys,2);idle(ident)
 def nav(ident,data,command):
  global caret,preferred
  caret,preferred=move(command,source,caret,preferred)
  send(ident,data);memory(ident+'_caret','se_hot_caret',caret,3)
  if preferred is not None:memory(ident+'_preferred','se_n_preferred',preferred)
  trace.append(dict(name=ident,command=command,caret=caret,preferred=preferred))
 def typed(ident,text,command):
  send(ident+'_text',bytes([0x88])+text.upper().encode('ascii'));nav(ident+'_enter',bytes([13]),command)
 def capture(ident):
  capture_sources[ident]=source;capture_carets[ident]=caret
  captures.append(ident);steps.append(step(ident+'_native','monitor.command',command=f'raw: screenshot "{e}/native-{ident}.png" 2'))
  steps.append(step(ident+'_ram','dump.memory_ranges',ranges=[dict(label='matrix',start=0x4000,end=0x43E7),dict(label='font',start=0x4800,end=0x4FFF),dict(label='colors',start=0xD800,end=0xDBE7),dict(label='row_starts',start=s['se_v_rows'],end=s['se_v_rows']+65),dict(label='bottom',start=s['se_v_bottom'],end=s['se_v_bottom']+2),dict(label='top',start=s['se_v_top'],end=s['se_v_top']+2),dict(label='caret_row',start=s['se_v_caret_row'],end=s['se_v_caret_row'])]))
 canary=bytes((i*73+29)&255 for i in range(1024))
 steps += [step('launch','vice.launch',kill_stale=False),step('basic','screen.wait_contains',text='READY.',wait_timeout_s=30),step('shim_seed','memory.write',start=0xC600,bytes_hex=canary.hex(' '))]
 if banks==8:
  for name,text in [('off','resourceset "REU" "0"'),('size','resourceset "REUsize" "512"'),('on','resourceset "REU" "1"')]:steps.append(step(name,'monitor.command',command='raw: '+text))
 steps += [step('reu_before','dump.reu',mode='full',stage_tag='reu_before'),step('disk_boot','input.sequence',keys=list(b'LOAD"SUPEREDITOR",8,1\rRUN\r'),inter_key_delay_s=0.04,post_delay_s=0.15)]
 memory('ready','se_status',1);memory('first_draw','se_e_draw_sequence',1,2);idle('initial')
 send('right_eight',bytes([0x1D])*8);caret=8;preferred=None
 for i,c in enumerate([37,37,37,36,36,36]):nav('vertical_'+str(i),bytes([0x11 if c==37 else 0x91]),c)
 capture('preferred')
 nav('f5_page_down',bytes([0x87]),39);capture('page-down')
 nav('f3_page_up',bytes([0x86]),38)
 send('navigator_menu',bytes([0x85,0x4E]));memory('nav_heading','se_e_menu',4);capture('menu')
 nav('menu_down',bytes([0x44]),37)
 send('page_command',bytes([0x88])+b'PAGE DOWN');capture('command')
 nav('typed_page_enter',bytes([13]),39)
 typed('bottom','bottom',35);typed('last_line','up',36)
 insertion=caret
 send('pending_newline',bytes([13]));source=source[:caret]+b'\r'+source[caret:];caret+=1;preferred=None
 nav('flush_then_up',bytes([0x91]),36);memory('committed_generation','se_doc_generation',3,2);capture('edited')
 send('undo_newline',bytes([0x1A]));source=sample;caret=insertion;preferred=None
 memory('undo_caret','se_hot_caret',caret,3);nav('down_after_undo',bytes([0x11]),37)
 send('redo_newline',bytes([0x19]));source=sample[:insertion]+b'\r'+sample[insertion:];caret=insertion+1;preferred=None
 nav('up_after_redo',bytes([0x91]),36);capture('final')
 memory('final_generation','se_doc_generation',5,2);memory('final_length','se_doc_length',len(source),3)
 memory('current_node','se_h_current',2,4);memory('saved_node','se_h_saved',1,4);memory('journal_bytes','se_h_end',75,2)
 memory('index_ready','se_i_ready',1);memory('index_count','se_i_count',1);memory('channels_closed',0x98,0);memory('shim_intact',0xC600,canary)
 steps += [step('reu_after','dump.reu',mode='full',stage_tag='reu_after')]
 plan=dict(version=1,kind='vice_task_plan',plan_id=f'supereditor-navigation-{banks}-{stamp}',run_mode='gui_vice',global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=6580,monitor_port_span=30,retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),timeouts=dict(launch_s=30,step_s=60,read_s=2),artifact_policy=dict(capture_screen=True,capture_state=True,capture_dump=False),vice=dict(disk8=str(disk),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,true_drive=False,close_vice=True,headless=True,speed_percent=100)),steps=steps)
 artifacts,manifest=run_plan(plan,e);pixels_checked=0
 for scene in captures:
  folder=artifacts/f'stages/{scene}_ram';matrix=(folder/'matrix.bin').read_bytes();font=(folder/'font.bin').read_bytes();colors=(folder/'colors.bin').read_bytes();decoded=native_screen_text(matrix);(e/(scene+'-screen.txt')).write_text(decoded+'\n')
  starts=[a for a,b in visual_rows(capture_sources[scene])]
  top=int.from_bytes((folder/'top.bin').read_bytes(),'little');assert top in starts
  first=starts.index(top);length=len(capture_sources[scene])
  expected=(starts[first:first+22]+[length]*22)[:22]
  actual=[int.from_bytes((folder/'row_starts.bin').read_bytes()[3*i:3*i+3],'little') for i in range(22)]
  assert actual==expected,(scene,'22 source starts',actual,expected)
  expected_bottom=starts[first+22] if first+22<len(starts) else length
  assert int.from_bytes((folder/'bottom.bin').read_bytes(),'little')==expected_bottom,(scene,'separate bottom')
  row=max(i for i,v in enumerate(starts) if v<=capture_carets[scene])-first
  assert 0<=row<22 and (folder/'caret_row.bin').read_bytes()==bytes([row]),(scene,'caret row',row)
  header,header_colors=menu_header();assert matrix[:80]==header and bytes(v&15 for v in colors[:80])==header_colors
  if scene=='menu':assert 'Page up' in decoded and 'preferred column' in decoded
  if scene=='command':assert 'Command:page down' in decoded
  if scene in ['edited','final']:assert 'Modified' in decoded
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
 def ref(identity,at,length):return bytes([identity,1,0])+at.to_bytes(3,'little')+length.to_bytes(3,'little')
 def piece(identity,at,length):return ref(identity,at,length)+b'\xff'*3+bytes(4)
 old_leaf=piece(1,0,len(sample))+bytes(1008)
 new_leaf=piece(1,0,insertion)+piece(2,0,1)+piece(1,insertion,len(sample)-insertion)+bytes(976)
 header=bytearray(64);header[:5]=b'SEH1\x01';header[5]=1;header[6:8]=(75).to_bytes(2,'little');header[8:12]=(1).to_bytes(4,'little');header[12:16]=(2).to_bytes(4,'little');header[16:21]=bytes([1,1,0,1,0]);header[21:26]=bytes([2,1,0,1,0]);header[26:29]=insertion.to_bytes(3,'little');header[32]=1;header[37]=1;header[39:42]=insertion.to_bytes(3,'little');header[42:45]=(insertion+1).to_bytes(3,'little');header[45]=1
 body=ref(2,0,1)+(75).to_bytes(2,'little');header[56:58]=binascii.crc_hqx(body,0xFFFF).to_bytes(2,'little');header[58:60]=binascii.crc_hqx(header[:58]+header[60:],0xFFFF).to_bytes(2,'little');record=bytes(header)+body
 quota=16 if banks==256 else 1;app=3+quota;journal=3+2*quota
 allowed=[(65536+i*4096,assets[n][HEADER:]) for i,n in enumerate(NAMES)]+[(2*65536,old_leaf+new_leaf),(3*65536,sample),(app*65536,b'\r'),(journal*65536,record),(journal*65536+0xB000,record)]
 at=0
 for offset,payload in sorted(allowed):
  assert after[at:offset]==before[at:offset],('unowned REU',hex(offset))
  actual=after[offset:offset+len(payload)];assert actual==payload,(hex(offset),next((i for i,(a,b) in enumerate(zip(actual,payload)) if a!=b),None));at=offset+len(payload)
 assert after[at:]==before[at:]
 reconstructed=bytearray()
 for i in range(3):
  at=2*65536+1024+i*16;identity=after[at];offset=int.from_bytes(after[at+3:at+6],'little');length=int.from_bytes(after[at+6:at+9],'little');bank=3 if identity==1 else app if identity==2 else None;assert bank is not None;reconstructed.extend(after[bank*65536+offset:bank*65536+offset+length])
 assert bytes(reconstructed)==source
 result=dict(status='passed',evidence=str(e),harness_manifest=str(manifest),prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],overlay_sha256={n:hashlib.sha256(v).hexdigest() for n,v in assets.items()},reu_banks=banks,input='native-byte queue via IRQ, not physical chord proof',keys_consumed=keys,source_bytes_reconstructed=len(source),document_generation=5,current_node=2,saved_node=1,insertion_position=insertion,final_caret=caret,preferred_column=True,page_rows=21,body_rows=22,status_screen_row=24,separate_bottom_anchor=True,viewport_geometry_checks=len(captures),navigation_trace=trace,screenshots=len(captures),captured_vic_pixels_checked=pixels_checked,index_invalidation_after_undo_redo=True,index_reu_banks=0,shim_bytes_verified=1024,untouched_reu_bytes_verified=len(after)-sum(len(v) for _,v in allowed),limitations='Source40 native-byte navigation; physical chords, normal-clock timing, and other integrated modes remain separate gates.')
 (e/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
