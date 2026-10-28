"""Actual editor menu-header native screenshots, isolated disk/port7100 plus text7200/PID."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from vice_config import PROJECT,step
from vice_plan import run_plan
from d81_image import D81Image
from redraw_model import native_text,screen_code,source40
from png_pixels import read_png
from cpu_editor import NAMES
r=json.loads((ROOT/'build/editor-report.json').read_text());s=r['symbols']
e=ROOT/'agentsworking/evidence/M3'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-menu-header');e.mkdir(parents=True)
for n in ['editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','supereditor.d81']:shutil.copy2(ROOT/'build'/n,e/n)
for n in NAMES:shutil.copy2(ROOT/f'build/overlays/{n}.seo',e/(n+'.seo'))
with zipfile.ZipFile(e/'product-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
 for folder in ['src','cfg']:
  for p in (ROOT/folder).rglob('*'):
   if p.is_file():z.write(p,p.relative_to(ROOT))
 z.write(ROOT/'Makefile','Makefile')
shutil.copy2(__file__,e/'test_menu_header_vice.py')
data=native_text('# SuperEditor: diverse source\rMixed Case and PETSCII @ £ arrows.\r\r## Notes and ideas\r**Strong words** and *emphasis*.\rInline @@lda #$01@@ stays native.\r\r- First bullet\r- Second bullet\r1. Numbered item\r2. Another item\r\r:::basic\r10 PRINT "Hello, C64!"\r20 FOR I=1 TO 5:PRINT I:NEXT\r30 GOTO 10\r:::\r\r:::asm\rstart: lda #$00\r       sta $d020 ; border\r       rts\r:::\r\r:::region Details\rExpandable region, source preserved.\r:::end\r')
# Host pound transcription is explicitly nativePETSCII5C.
data=data.replace(bytes([0xA3]),b'\\')
(e/'diverse.bin').write_bytes(data);disk=e/'working.d81';shutil.copy2(e/'supereditor.d81',disk)
p=subprocess.run(['c1541','-attach',str(disk),'-write',str(e/'diverse.bin'),'diverse,s'],capture_output=True,text=True);assert p.returncode==0,p.stdout+p.stderr
assert D81Image(disk.read_bytes()).read(b'DIVERSE',kind=1).data==data
steps=[]
def mem(tag,name,value,width=1):
 at=s[name] if isinstance(name,str) else name;b=value if isinstance(value,bytes) else value.to_bytes(width,'little')
 item=step(tag,'assert.memory',start=at,end=at+len(b)-1,equals_hex=b.hex(' '));item['retry']=dict(max_attempts=100,backoff_ms=30,jitter=False);steps.append(item)
def idle(tag):
 mem(tag+'job','se_e_job',0);mem(tag+'draw','se_e_redraw',bytes([0,0]))
def send(tag,b):steps.append(step('key-'+tag,'input.sequence',keys=list(b),inter_key_delay_s=0.02,post_delay_s=0.12));idle('key-'+tag)
def capture(tag):
 steps.append(step(tag,'monitor.command',command=f'raw: screenshot "{e}/native-{tag}.png" 2'))
 steps.append(step(tag+'ram','dump.memory_ranges',ranges=[dict(label='matrix',start=0x4000,end=0x43E7),dict(label='colors',start=0xD800,end=0xDBE7),dict(label='font',start=0x4800,end=0x4FFF)]))
canary=bytes((i*73+29)&255 for i in range(1024))
steps += [step('launch','vice.launch',kill_stale=False),step('ready','screen.wait_contains',text='READY.',wait_timeout_s=30),step('shim','memory.write',start=0xC600,bytes_hex=canary.hex(' ')),step('boot','input.sequence',keys=list(b'LOAD"SUPEREDITOR",8,1\rRUN\r'),inter_key_delay_s=0.03,post_delay_s=0.2)]
mem('booted','se_status',1);idle('boot');capture('header')
send('open',bytes([0x85,0x46,0x4F]));mem('modal','se_e_ui',3);send('name',b'DIVERSE\r');mem('opened','se_e_ui',0);mem('length','se_doc_length',len(data),3);capture('diverse')
send('file-menu',bytes([0x85,0x46]));mem('file-selected','se_e_menu',1);capture('file-menu')
send('close',bytes([3]));send('help',bytes([0x8B]));capture('help')
mem('shim-intact',0xC600,canary)
plan=dict(version=1,kind='vice_task_plan',plan_id='supereditor-menu-header-'+e.name,run_mode='gui_vice',global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=7100,monitor_port_span=1,retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),timeouts=dict(launch_s=30,step_s=60,read_s=2),artifact_policy=dict(capture_screen=True,capture_state=True,capture_dump=False),vice=dict(disk8=str(disk),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,true_drive=False,close_vice=True,headless=True,speed_percent=100)),steps=steps)
print(e,flush=True)
p=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True);assert p.returncode==0,p.stdout+p.stderr
artifacts,manifest=run_plan(plan,e);pixels_checked=0
expected=source40(data,0,0)
for tag in ['header','diverse','file-menu','help']:
 out=artifacts/f'stages/{tag}ram';matrix=(out/'matrix.bin').read_bytes();colors=(out/'colors.bin').read_bytes();font=(out/'font.bin').read_bytes()
 assert matrix[:40]==expected.matrix[:40] and bytes(v&15 for v in colors[:40])==expected.colors[:40]
 if tag!='file-menu':
  assert matrix[40:80]==expected.matrix[40:80] and bytes(v&15 for v in colors[40:80])==expected.colors[40:80]
 if tag=='file-menu':
  assert matrix[40]==0x6B and matrix[79]==0x73
  assert matrix[200]==0x6D and matrix[239]==0x7D
  border=[40+c for c in range(40)]+[200+c for c in range(40)]+[80,119,120,159,160,199]
  assert all((colors[at]&15)==7 for at in border)
  assert (colors[82]&15)==7 and all(matrix[82+c]&0x80 for c in range(len('O  Open...       CTRL-O')))
  assert (colors[122]&15)==3 and (colors[162]&15)==3
 if tag=='help':
  for row,label in [(4,'SuperEditor keys 1/3'),(8,'CBM-S settings; F8 modes'),
                    (11,'CBM-F toggle region'),(12,'CBM-D collapse; CBM-E expand')]:
   raw=bytes(screen_code(v) for v in native_text(label));assert matrix[row*40+3:row*40+3+len(raw)]==raw
 assert bytes(v&15 for v in colors[960:])==bytes([15])*40
 w,h,pixels=read_png(e/f'native-{tag}.png');assert(w,h)==(384,272);bg=pixels[0]
 for row in range(25):
  for col in range(40):
   code=matrix[row*40+col]
   for gy in range(8):
    bits=font[code*8+gy]
    for gx in range(8):
     assert bool(bits&(128>>gx))==(pixels[(35+row*8+gy)*w+32+col*8+gx]!=bg),(tag,row,col,gx,gy)
     pixels_checked+=1
result=dict(status='passed',evidence=str(e),prg_sha256=r['sha256'],catalog_capacity=s['se_overlay_capacity'],screenshots=4,native_pixels_checked=pixels_checked,shim_bytes=1024,source_bytes=len(data),attached_menu=True,mnemonic_colors=True,scope='Actual40 editor newheader/open/menu/help; nativeIRQbytes, no physicalchord or additionalmodeeditingclaim')
(e/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
