"""Actual editor event/command pipeline and visible source bytes (no VIC claim)."""
from pathlib import Path
import hashlib,json,random,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
from cpu_editor import startup,NAMES
from run_vice import native_screen_text
from redraw_model import menu_header
r=json.loads((ROOT/'build/editor-report.json').read_text());s=r['symbols'];assets={n:(ROOT/f'build/overlays/{n}.seo').read_bytes() for n in NAMES}
api=(ROOT/'build/editor-api.inc').read_text()
for cold_name in ['se_editor_startup','se_clear_state','se_reu_probe','se_probe_original']:
 assert cold_name+' =' not in api,cold_name
result_path=ROOT/'build/editor-test-result.json';result_path.unlink(missing_ok=True)
m=Machine();max_draw=0;max_service=0;max_input=0

def read(a,n):return bytes(m.read(a+i) for i in range(n))
def get(n,w=3):return int.from_bytes(read(s[n],w),'little')
def put(n,v,w=3):m.load(s[n],v.to_bytes(w,'little'))
def call(n,a=0):
 global max_draw,max_service,max_input
 regs,used=m.call(s[n],a=a,limit=2_000_000)
 if n=='se_editor_render':max_draw=max(max_draw,used)
 if n=='se_editor_service':max_service=max(max_service,used)
 if n=='se_editor_input':max_input=max(max_input,used)
 return regs

def settle(render=True):
 steps=0
 while get('se_e_job',1):
  call('se_editor_service');steps+=1;assert steps<3000,(get('se_e_job',1),get('se_e_error',1))
 if render:
  for _ in range(8):
   call('se_editor_render')
   if not get('se_e_job',1):break
   assert get('se_e_job',1)==7
   settle(False)
  else:raise AssertionError('layout convergence')
 assert get('se_e_error',1)==0,hex(get('se_e_error',1))
 return steps

def send(key,render=True):
 put('se_e_key',key,1);call('se_editor_input');return settle(render)
def command(value,render=True):
 call('se_editor_command',a=value);return settle(render)
def overlay_hotkey(matrix,mods=2):
 put('se_e_key',0xA0,1);put('se_e_mods',mods,1);put('se_e_matrix',matrix,1);put('se_overlay_frame',9,1)
 regs,_=m.call(s['se_overlay_call'],a=7,x=1);assert not regs.p&1
 value=get('se_e_command',1);put('se_e_mods',0,1);put('se_e_matrix',0,1);return value
def cbm_hotkey(matrix,key=0xA0,shift=False,render=True):
 put('se_e_key',key,1);put('se_e_mods',3 if shift else 2,1);put('se_e_matrix',matrix,1)
 call('se_editor_input');steps=settle(render);put('se_e_mods',0,1);put('se_e_matrix',0,1);return steps
def typed(text,render=True):
 send(0x88,False)
 for c in text.upper().encode('ascii'):send(c,False)
 send(13,render)
def span():
 return read(0x9200,get('se_hot_left',2))+read(0x9200+get('se_hot_right',2),2048-get('se_hot_right',2))
def document():
 out=bytearray();n=get('se_doc_length')
 for i in range(0,n,1024):
  count=min(1024,n-i);put('se_doc_offset',i);put('se_doc_count',count,2);put('se_doc_c64',0x8000,2)
  regs=call('se_doc_read');assert not regs.p&1;out.extend(read(0x8000,count))
 return bytes(out)
def view():
 data=document();base=get('se_hot_base');return data[:base]+span()+data[base+get('se_hot_old_length',2):]
def screen():return native_screen_text(read(0x4000,1000))
def own_source(data,banks=2):
 # Reset via actual provider/services, not fabricated roots. Reimport sidecars
 # after epoch reset. View state is cleared because this is a new test context.
 call('se_clear_state');put('se_reu_banks',256,2)
 for name,a in [('se_reu_provider_init',0),('se_object_init',0),('se_overlay_init',0),('se_doc_init',banks)]:
  assert not call(name,a).p&1
 t=read(s['se_doc_original'],5)
 for i in range(0,len(data),1024):
  part=data[i:i+1024];m.load(s['se_object_id'],t);m.load(0x8000,part);put('se_object_offset',i);put('se_object_length',len(part),2);put('se_object_c64',0x8000,2);assert not call('se_object_copy').p&1
 put('se_doc_source_length',len(data));assert not call('se_doc_adopt_original').p&1
 from overlays import HEADER
 for image in assets.values():m.load(s['se_overlay_header'],image[:HEADER]);m.load(0x5000,image[HEADER:]);assert not call('se_overlay_import').p&1
 for name in ['se_history_cold','se_hot_cold']:assert not call(name).p&1
 assert not call('se_history_call',1).p&1
 put('se_hot_position',0);assert not call('se_hot_call',1).p&1
 put('se_e_job',1,1);put('se_hot_group',1,1);settle()
try:
 shim=bytes((i*73+29)&255 for i in range(1024));m.load(0xC600,shim)
 startup(m,s,assets);settle();original=document()
 assert original.startswith(bytes([35,32,0xD3,0x55,0x50]))
 assert [overlay_hotkey(v) for v in (13,14,18,21)]==[103,114,113,112]
 assert [overlay_hotkey(2,v) for v in (2,3)]==[41,40]
 assert [overlay_hotkey(7,v) for v in (2,3)]==[39,38]
 assert overlay_hotkey(10)==0xFF
 cbm_hotkey(13);assert get('se_e_ui',1)==1 and get('se_e_menu',1)==8
 send(3);assert get('se_e_ui',1)==0
 header,header_colors=menu_header()
 assert read(0x4000,80)==header and bytes(c&15 for c in read(0xD800,80))==header_colors
 assert '# SuperEditor' in screen()
 assert get('se_hot_caret')==0 and get('se_hot_pending',1)==0
 for c in bytes([0xD8,0x59,0xDA,13]):send(c)
 expected=bytes([0xD8,0x59,0xDA,13])+original
 assert view()==expected and document()==original and 'XyZ' in screen() and 'Modified' in screen()
 send(0x9D);send(0x14);expected=bytes([0xD8,0x59,13])+original
 assert view()==expected and get('se_hot_caret')==2
 send(0x1A);assert view()==bytes([0xD8,0x59,0xDA,13])+original
 send(0x1A);assert view()==original and get('se_h_dirty',1)==0
 send(0x19);send(0x19);assert view()==expected
 typed('top');assert get('se_hot_caret')==0
 typed('end');assert get('se_hot_caret')==2
 typed('bottom');assert get('se_hot_caret')==len(expected)
 typed('home');assert get('se_hot_caret')==len(expected) #EOF follows CR
 typed('jump -40');assert get('se_hot_caret')==len(expected)
 typed('top')
 # F1 letter route and arrow/Return route select the same shared undo ID.
 send(0x85);send(ord('E'));assert get('se_e_menu',1)==2 and 'Undo' in screen()
 send(ord('U'));assert view()==bytes([0xD8,0x59,0xDA,13])+original and get('se_e_ui',1)==0
 send(0x85);send(ord('E'));send(0x11);send(13);assert view()==expected
 send(0x85);send(0x9D);assert get('se_e_menu',1)==6;send(3)
 typed('help');assert 'SuperEditor keys 1/3' in screen();send(3)
 # Typed unknown command remains editable; unavailable commands do not mutate.
 send(0x88);send(ord('Q'));put('se_e_key',13,1);call('se_editor_input');call('se_editor_render')
 assert get('se_e_error',1)==0x76 and get('se_e_ui',1)==2 and view()==expected
 send(0x14);send(3)
 send(0x89);assert get('se_sel_mark',1)==1 and view()==expected
 send(3);assert get('se_sel_mark',1)==0 and view()==expected
 print('Actual pending editing, caret, keyboard/typed/menu undo+redo and popup paths pass.',flush=True)
 # Long lines/mixed source: bounded HOME/END and exact ±40 clamped by CR;
 # later lines and bytes beyond64KiB are real immutable object reads.
 source=b'A'*700+b'\r'+b'B'*100+b'\r'+bytes((65+i%26 for i in range(69200)))
 own_source(source);command(33);assert get('se_hot_caret')==700
 command(40);assert get('se_hot_caret')==660
 command(41);assert get('se_hot_caret')==700
 command(32);assert get('se_hot_caret')==0
 command(35);assert get('se_hot_caret')==len(source)
 command(32);assert get('se_hot_caret')==802
 command(33);assert get('se_hot_caret')==len(source)
 command(40);assert get('se_hot_caret')==len(source)-40
 send(0xD8);assert view()==source[:-40]+bytes([0xD8])+source[-40:]
 typed('undo');assert view()==source
 typed('redo');assert view()==source[:-40]+bytes([0xD8])+source[-40:]
 print('Long-line scan slices, jumps, viewport changes and >64KiB input/replay pass.',flush=True)
 # Crossing a RAM window boundary recenters and retries exactly one operation.
 own_source(b'Z'*3000);command(33);assert get('se_hot_caret')==3000
 for _ in range(530):send(0x14,False)
 assert get('se_hot_caret')==2470 and view()==b'Z'*2470
 command(34);send(0x94);assert view()==b' '+b'Z'*2470
 for _ in range(2100):send(ord('A'),False)
 assert view()==b' '+b'A'*2100+b'Z'*2470
 # Pending length can make caret numerically equal the committed length
 # while original source still follows the cache. That is not visible EOF.
 own_source(b'R'*1500)
 for _ in range(1024):send(0x1D,False)
 for _ in range(476):send(ord('A'),False)
 assert get('se_hot_caret')==get('se_doc_length')==1500
 command(4);assert view()==b'R'*1024+b'A'*476+b'R'*475 and get('se_hot_caret')==1500
 print('Window-edge deletion, pending EOF mapping and full-gap retry pass.',flush=True)
 assert read(0xC600,1024)==shim
 result=dict(status='passed',engine='Peddle MOS_6510',prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],
 overlay_sha256={n:hashlib.sha256(v).hexdigest() for n,v in assets.items()},actual_command_pipeline=True,
 pending_view=True,typed_and_menu_commands=True,commodore_hotkeys=True,history_ui=True,source_bytes=len(source),long_line_bytes=69200,
 boundary_delete_count=530,full_gap_insert_count=2100,pending_eof_mapping=True,shim_bytes_verified=1024,
 max_render_instructions=max_draw,max_service_instructions=max_service,max_input_instructions=max_input,
 limitations='ROM import injected; native D81/IRQ/VIC proof separate. Vertical/page/selection/files/formatting/modes unfinished.')
 result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:m.close()
