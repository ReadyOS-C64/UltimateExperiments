"""Real D81 selection/copy/cut/paste/replacement with independent REU/journal oracle."""
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
from navigation_model import move,visual_rows
from overlays import HEADER
r=json.loads((ROOT/'build/editor-report.json').read_text());s=r['symbols'];prg=(ROOT/'build/editor.prg').read_bytes();sample=prg[2+s['sample']-0x801:2+s['sample_end']-0x801]
assets={n:(ROOT/f'build/overlays/{n}.seo').read_bytes() for n in NAMES}
b=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120);assert b.returncode==0,b.stdout+b.stderr
for banks in [256,8]:
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');e=ROOT/'agentsworking/evidence/M3'/f'{stamp}-selection-{banks}';e.mkdir(parents=True);disk=e/'working.d81';shutil.copyfile(ROOT/'build/supereditor.d81',disk)
 for n in ['editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json']:shutil.copyfile(ROOT/'build'/n,e/n)
 for n,image in assets.items():(e/(n+'.seo')).write_bytes(image)
 steps=[];keys=0;captures=[]
 def memory(ident,name,value,width=1):
  at=s[name] if isinstance(name,str) else name;raw=value if isinstance(value,bytes) else value.to_bytes(width,'little')
  item=step(ident,'assert.memory',start=at,end=at+len(raw)-1,equals_hex=raw.hex(' '));item['retry']=dict(max_attempts=30,backoff_ms=30,jitter=False);steps.append(item)
 def idle(ident):
  for name in ['se_e_job','se_e_error','se_n_owned','se_doc_read_locks','se_v_nav_busy','se_s_owned','se_s_active','se_b_phase','se_clip_busy']:memory(ident+'_'+name,name,0)
  memory(ident+'_draw','se_e_redraw',bytes([0,0]))
 def send(ident,data):
  global keys
  steps.append(step(ident,'input.sequence',keys=list(data),inter_key_delay_s=0.04,post_delay_s=0.08));keys+=len(data)
  memory(ident+'_consumed','se_key_sequence',keys,2);idle(ident)
 def typed(ident,data):send(ident,bytes([0x88])+data+bytes([13]))
 def capture(ident):
  captures.append(ident);steps.append(step(ident+'_native','monitor.command',command=f'raw: screenshot "{e}/native-{ident}.png" 2'))
  steps.append(step(ident+'_ram','dump.memory_ranges',ranges=[dict(label='matrix',start=0x4000,end=0x43E7),dict(label='font',start=0x4800,end=0x4FFF),dict(label='colors',start=0xD800,end=0xDBE7),dict(label='top',start=s['se_v_top'],end=s['se_v_top']+2)]))
 canary=bytes((i*73+29)&255 for i in range(1024))
 steps += [step('launch','vice.launch',kill_stale=False),step('basic','screen.wait_contains',text='READY.',wait_timeout_s=30),step('shim_seed','memory.write',start=0xC600,bytes_hex=canary.hex(' '))]
 if banks==8:
  for name,text in [('off','resourceset "REU" "0"'),('size','resourceset "REUsize" "512"'),('on','resourceset "REU" "1"')]:steps.append(step(name,'monitor.command',command='raw: '+text))
 steps += [step('reu_before','dump.reu',mode='full',stage_tag='reu_before'),step('disk_boot','input.sequence',keys=list(b'LOAD"SUPEREDITOR",8,1\rRUN\r'),inter_key_delay_s=0.04,post_delay_s=0.15)]
 memory('ready','se_status',1);memory('first_draw','se_e_draw_sequence',1,2);idle('initial')
 send('begin_mark',bytes([0x89]));caret=0;preferred=None
 for i in range(3):
  caret,preferred=move(37,sample,caret,preferred);send('select_down_'+str(i),bytes([0x11]));memory('select_caret_'+str(i),'se_hot_caret',caret,3)
 copied=sample[:caret];memory('mark_anchor','se_sel_anchor',0,3);capture('selected')
 send('block_menu',bytes([0x85,0x42]));memory('block_heading','se_e_menu',5);capture('block-menu');send('menu_copy',bytes([0x43]));memory('clipboard_length','se_clip_length',len(copied),3);capture('copied')
 send('stop_unmark',bytes([3]));memory('unmarked','se_sel_mark',0);typed('to_end',b'BOTTOM');send('paste_ctrl_v',bytes([0x16]));pasted=sample+copied
 memory('paste_caret','se_hot_caret',len(pasted),3);memory('paste_generation','se_doc_generation',3,2);capture('pasted')
 send('undo_paste',bytes([0x1A]));memory('undo_paste_length','se_doc_length',len(sample),3);capture('undo-paste')
 send('redo_paste',bytes([0x19]));memory('redo_paste_length','se_doc_length',len(pasted),3);capture('redo-paste')
 starts=[0]+[i+1 for i,v in enumerate(sample) if v==13];removed=starts[2]
 typed('third_line',b'GOTO 3');send('reverse_mark',bytes([0x89]));typed('reverse_top',b'TOP');memory('reverse_anchor','se_sel_anchor',removed,3);capture('reversed')
 send('cut_ctrl_x',bytes([0x18]));cut=pasted[removed:];memory('cut_length','se_doc_length',len(cut),3);memory('cut_caret','se_hot_caret',0,3);memory('cut_clipboard','se_clip_length',removed,3);capture('cut')
 send('replacement_mark',bytes([0x89]));send('replacement_span',bytes([0x1D])*5);capture('replace-range');send('type_selected_X',bytes([0xD8]));final=bytes([0xD8])+cut[5:]
 memory('replacement_length','se_doc_length',len(final),3);memory('replacement_caret','se_hot_caret',1,3);capture('replaced')
 send('undo_replacement',bytes([0x1A]));memory('undo_replacement_caret','se_hot_caret',5,3);capture('undo-replace')
 send('redo_replacement',bytes([0x19]));capture('final')
 memory('final_length','se_doc_length',len(final),3);memory('final_generation','se_doc_generation',9,2);memory('final_caret','se_hot_caret',1,3)
 memory('two_roots','se_doc_root_count',2);root_prefix=bytes([0,2])+(len(sample)-removed-4).to_bytes(3,'little')+b'\xff'*3+bytes([1,1])+len(copied).to_bytes(3,'little')+b'\xff'*3;memory('exact_roots','se_doc_roots',root_prefix)
 memory('current_node','se_h_current',4,4);memory('saved_node','se_h_saved',1,4);memory('journal_length','se_h_end',234,2);memory('no_mark','se_sel_mark',0);memory('channels_closed',0x98,0);memory('shim_intact',0xC600,canary)
 steps += [step('reu_after','dump.reu',mode='full',stage_tag='reu_after')]
 plan=dict(version=1,kind='vice_task_plan',plan_id=f'supereditor-selection-{banks}-{stamp}',run_mode='gui_vice',global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=6580,monitor_port_span=30,retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),timeouts=dict(launch_s=30,step_s=60,read_s=2),artifact_policy=dict(capture_screen=True,capture_state=True,capture_dump=False),vice=dict(disk8=str(disk),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,true_drive=False,close_vice=True,headless=True,speed_percent=100)),steps=steps)
 artifacts,manifest=run_plan(plan,e);pixels_checked=0
 for scene in captures:
  folder=artifacts/f'stages/{scene}_ram';matrix=(folder/'matrix.bin').read_bytes();font=(folder/'font.bin').read_bytes();colors=(folder/'colors.bin').read_bytes();decoded=native_screen_text(matrix);(e/(scene+'-screen.txt')).write_text(decoded+'\n')
  header,header_colors=menu_header();assert matrix[:80]==header and bytes(v&15 for v in colors[:80])==header_colors
  if scene=='block-menu':
   popup='\n'.join(decoded.splitlines()[3:9]);assert 'CTRL-C/K' in popup and 'Cut' in popup and 'not ready' not in popup
  if scene in ['selected','copied','reversed','replace-range']:assert 'Mark' in decoded
  if scene=='pasted':assert int.from_bytes((folder/'top.bin').read_bytes(),'little')<len(pasted),'EOF paste must reveal context'
  if scene in ['selected','copied']:
   top=int.from_bytes((folder/'top.bin').read_bytes(),'little');assert top==0
   for row,(a,z) in enumerate(visual_rows(sample)[:22]):
    for col,p in enumerate(range(a,min(z+1,a+40))):
     if p<len(copied):assert colors[(row+2)*40+col]&15==3 and matrix[(row+2)*40+col]&128
     elif p==len(copied):assert colors[(row+2)*40+col]&15==7 and matrix[(row+2)*40+col]&128
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
 def leaf(parts):return b''.join(piece(*p) for p in parts)+bytes(1024-16*len(parts))
 def record(node,pos,delete,insert,before_caret,after_caret,removed_refs,inserted_refs):
  body=b''.join(ref(*p) for p in removed_refs+inserted_refs);length=66+len(body);body+=length.to_bytes(2,'little');header=bytearray(64);header[:5]=b'SEH1\x01';header[6:8]=length.to_bytes(2,'little');header[8:12]=node.to_bytes(4,'little');header[12:16]=(node+1).to_bytes(4,'little');header[16:21]=bytes([1,1,0,1,0]);header[21:26]=bytes([2,1,0,1,0]);header[26:29]=pos.to_bytes(3,'little');header[29:32]=delete.to_bytes(3,'little');header[32:35]=insert.to_bytes(3,'little');header[35:37]=len(removed_refs).to_bytes(2,'little');header[37:39]=len(inserted_refs).to_bytes(2,'little');header[39:42]=before_caret.to_bytes(3,'little');header[42:45]=after_caret.to_bytes(3,'little');header[56:58]=binascii.crc_hqx(body,0xFFFF).to_bytes(2,'little');header[58:60]=binascii.crc_hqx(header[:58]+header[60:],0xFFFF).to_bytes(2,'little');return bytes(header)+body
 first=record(1,len(sample),0,len(copied),len(sample),len(pasted),[],[(2,0,len(copied))]);second=record(2,0,removed,0,0,0,[(1,0,removed)],[]);third=record(3,0,5,1,5,1,[(1,removed,5)],[(2,len(copied),1)])
 quota=16 if banks==256 else 1;app=3+quota;journal=3+2*quota;oldclip=journal+1;newclip=journal+2
 active_prefix=leaf([(2,len(copied),1),(1,removed+5,len(sample)-removed-5)]);reused_suffix=leaf([(2,0,len(copied))]);inactive_prefix=leaf([(1,removed,len(sample)-removed)])
 allowed=[(65536+i*4096,assets[n][HEADER:]) for i,n in enumerate(NAMES)]+[(2*65536,active_prefix+reused_suffix+inactive_prefix),(3*65536,sample),(app*65536,copied+bytes([0xD8])),(journal*65536,first+second+third),(journal*65536+0xB000,third),(oldclip*65536,copied),(newclip*65536,sample[:removed])];at=0
 for offset,payload in sorted(allowed):
  assert after[at:offset]==before[at:offset],('unowned REU',hex(offset))
  actual=after[offset:offset+len(payload)];assert actual==payload,(hex(offset),next((i for i,(a,b) in enumerate(zip(actual,payload)) if a!=b),None));at=offset+len(payload)
 assert after[at:]==before[at:]
 reconstructed=after[app*65536+len(copied):app*65536+len(copied)+1]+after[3*65536+removed+5:3*65536+len(sample)]+after[app*65536:app*65536+len(copied)];assert reconstructed==final
 result=dict(status='passed',evidence=str(e),harness_manifest=str(manifest),prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],overlay_sha256={n:hashlib.sha256(v).hexdigest() for n,v in assets.items()},reu_banks=banks,input='IRQ native-byte queue,not physical chord proof',keys_consumed=keys,multiline_and_reversed_selection=True,menu_copy_ctrl_x_v_cut_paste=True,selected_native_typing_undo_redo=True,selection_colors_and_cr_cells=True,paste_at_eof_reveals_context=True,source_bytes_reconstructed=len(final),document_generation=9,current_node=4,saved_node=1,journal_bytes=234,clipboard_bytes=removed,append_bytes=len(copied)+1,stale_freed_clipboard_bytes_checked=len(copied),screenshots=len(captures),captured_vic_pixels_checked=pixels_checked,shim_bytes_verified=1024,untouched_reu_bytes_verified=len(after)-sum(len(v) for _,v in allowed),limitations='Source40 editing only;dirty rows,normal timing,files/styles/folds/other integrated views and lifecycle remain open.')
 (e/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
