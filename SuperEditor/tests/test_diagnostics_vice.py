"""Actual ROM/D81 diagnostics UI,pending source CRC,STOP and missing-C11 error.

Run only with an exclusive native window. Fault injection changes one catalog
ID in C64 RAM; document typing and every diagnostic request use native IRQ input.
"""
from datetime import datetime,timezone
import binascii
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from cpu_editor import NAMES
from vice_config import PROJECT,step
from vice_plan import run_plan
from redraw_model import source40,verify_screen
from diagnostics_model import diagnostic_popup
from png_pixels import read_png
from run_vice import native_screen_text

r=json.loads((ROOT/'build/editor-report.json').read_text());s=r['symbols']
prg=(ROOT/'build/editor.prg').read_bytes()
sample=prg[2+s['sample']-0x801:2+s['sample_end']-0x801]
prefix=bytes([0xD8,0x59,0xDA,13]);source=prefix+sample
assets={n:(ROOT/f'build/overlays/{n}.seo').read_bytes() for n in NAMES}
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
e=ROOT/'agentsworking/evidence/M2'/(stamp+'-diagnostics-editor');e.mkdir(parents=True)
for name in ['editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json']:
    shutil.copyfile(ROOT/'build'/name,e/name)
for name,data in assets.items():(e/(name+'.seo')).write_bytes(data)
for name in ['diagnostics-editor-result.json','editor-edges-result.json','editor-test-result.json','nowrap-result.json','viewport-edges-result.json','publication-wrap-result.json']:
    if (ROOT/'build'/name).exists():shutil.copyfile(ROOT/'build'/name,e/name)
with zipfile.ZipFile(e/'sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for base in ['src','cfg','tools','tests']:
        for path in sorted((ROOT/base).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:archive.write(path,path.relative_to(ROOT))
    archive.write(ROOT/'Makefile','Makefile')
shutil.copyfile(ROOT/'build/supereditor.d81',e/'working.d81')
(e/'freeze.json').write_text(json.dumps(dict(prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],disk_sha256=hashlib.sha256((e/'working.d81').read_bytes()).hexdigest(),assets={n:hashlib.sha256(v).hexdigest() for n,v in assets.items()}),indent=2)+'\n')
b=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120)
assert b.returncode==0,b.stdout+b.stderr
steps=[];keys=0;captures=[]
canary=bytes((i*73+29)&255 for i in range(1024))
def memory(ident,name,value,width=1):
    address=s[name] if isinstance(name,str) else name
    data=value if isinstance(value,bytes) else value.to_bytes(width,'little')
    item=step(ident,'assert.memory',start=address,end=address+len(data)-1,equals_hex=data.hex(' '))
    item['retry']=dict(max_attempts=30,backoff_ms=30,jitter=False);steps.append(item)
def write(ident,name,value,width=1):
    address=s[name] if isinstance(name,str) else name
    data=value if isinstance(value,bytes) else value.to_bytes(width,'little')
    steps.append(step(ident,'memory.write',start=address,bytes_hex=data.hex(' ')))
def idle(ident,error=0,foreign=0):
    for name in ['se_e_job','se_e_draw_busy','se_e_redraw','se_diag_active','se_diag_owned','se_v_nav_busy','se_n_owned']:
        memory(ident+'_'+name,name,0)
    memory(ident+'_locks','se_doc_read_locks',foreign)
    memory(ident+'_error','se_e_error',error)
def send(ident,data,error=0,fast=False,foreign=0):
    global keys
    steps.append(step(ident,'input.sequence',keys=list(data),inter_key_delay_s=0 if fast else 0.04,post_delay_s=0.08))
    keys+=len(data);memory(ident+'_consumed','se_key_sequence',keys,2);idle(ident,error,foreign)
def capture(ident,kind='plain',error=0,foreign=0):
    captures.append(dict(id=ident,kind=kind,error=error,foreign=foreign))
    memory(ident+'_ui','se_e_ui',1 if kind in ['diag','help'] else 0)
    if kind=='diag':memory(ident+'_popup','se_e_menu',7)
    memory(ident+'_generation','se_doc_generation',2,2)
    memory(ident+'_length','se_doc_length',len(sample),3)
    steps.append(step(ident+'_native','monitor.command',command=f'raw: screenshot "{e}/native-{ident}.png" 2'))
    steps.append(step(ident+'_ram','dump.memory_ranges',ranges=[dict(label='state',start=0xC000,end=0xC5FF),dict(label='view',start=0x8C00,end=0x8CFF),dict(label='metadata',start=0x9A00,end=0x9FFF),dict(label='hot',start=0x9200,end=0x99FF),dict(label='diag',start=0x8800,end=0x887F),dict(label='matrix',start=0x4000,end=0x43E7),dict(label='font',start=0x4800,end=0x4FFF),dict(label='colors',start=0xD800,end=0xDBE7)]))

steps += [step('launch','vice.launch',kill_stale=False),step('basic','screen.wait_contains',text='READY.',wait_timeout_s=30)]
for name,command in [('reu_off','resourceset "REU" "0"'),('reu_size','resourceset "REUsize" "512"'),('reu_on','resourceset "REU" "1"')]:
    steps.append(step(name,'monitor.command',command='raw: '+command))
write('shim_seed',0xC600,canary)
steps.append(step('boot','input.sequence',keys=list(b'LOAD"SUPEREDITOR",8,1\rRUN\r'),inter_key_delay_s=0.04,post_delay_s=0.15))
memory('ready','se_status',1);memory('first_draw','se_e_draw_sequence',1,2);idle('boot')
steps.append(step('reu_before','dump.reu',mode='full',stage_tag='reu_before'))
capture('initial')
send('pending_typing',prefix);memory('pending','se_hot_pending',1);capture('pending')
send('typed_diag',bytes([0x88])+b'DIAG\r');capture('typed','diag')
send('ignored_popup_keys',bytes([0x11,0x91,0x1D,0x9D,65,13]));capture('ignored','diag')
send('close_diag',bytes([3]));capture('restored')
send('help_D_diag',bytes([0x85,72,68]));capture('help-D','diag')
send('f6_help',bytes([0x8B]));capture('help','help')
send('f6_close',bytes([0x8B]));capture('help-restored')
send('queued_STOP',bytes([0x88])+b'DIAG\r'+bytes([3]),fast=True)
memory('cancel_status',0x8806,3);capture('cancelled')
index=NAMES.index('layout');memory('catalog_C11','se_overlay_ids' if index==0 else s['se_overlay_ids']+index,11)
write('foreign_read_lease','se_doc_read_locks',1)
write('remove_C11',s['se_overlay_ids']+index,0)
send('missing_C11_diag',bytes([0x88])+b'DIAG\r',error=0x17,foreign=1)
capture('missing-C11',error=0x17,foreign=1)
write('restore_C11',s['se_overlay_ids']+index,11)
write('release_foreign_fixture_lease','se_doc_read_locks',0)
send('retry_diag',bytes([0x88])+b'DIAG\r');capture('retry','diag')
send('final_close',bytes([3]));capture('final')
memory('pending_still_private','se_hot_pending',1);memory('caret_same','se_hot_caret',4,3)
memory('history_same','se_h_current',1,4);memory('dirty_still_clean','se_h_dirty',0)
memory('shim_intact',0xC600,canary);memory('channels_closed',0x98,0)
steps.append(step('reu_after','dump.reu',mode='full',stage_tag='reu_after'))
plan=dict(version=1,kind='vice_task_plan',plan_id='supereditor-diagnostics-'+stamp,run_mode='gui_vice',global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=6580,monitor_port_span=30,retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),timeouts=dict(launch_s=30,step_s=60,read_s=2),artifact_policy=dict(capture_screen=False,capture_state=False,capture_dump=False),vice=dict(disk8=str(e/'working.d81'),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,true_drive=False,close_vice=True,headless=True,speed_percent=100)),steps=steps)
print('Frozen diagnostics native run',e,flush=True)
artifacts,manifest=run_plan(plan,e)

def get(folder,name,width=1):
    address=s[name]
    for label,start,end in [('state',0xC000,0xC600),('view',0x8C00,0x8D00),('metadata',0x9A00,0xA000)]:
        if start<=address and address+width<=end:
            return int.from_bytes((folder/(label+'.bin')).read_bytes()[address-start:address-start+width],'little')
    raise AssertionError((name,address))
pixels_checked=complete=0;initial_metadata=None;initial_diag=None
for case in captures:
    ident=case['id'];folder=artifacts/'stages'/(ident+'_ram')
    matrix=(folder/'matrix.bin').read_bytes();colors=(folder/'colors.bin').read_bytes();font=(folder/'font.bin').read_bytes()
    d=(folder/'diag.bin').read_bytes();hot=(folder/'hot.bin').read_bytes()
    current=sample if ident=='initial' else source;caret=0 if ident=='initial' else 4
    assert hot[:get(folder,'se_hot_left',2)]+hot[get(folder,'se_hot_right',2):]==current
    assert get(folder,'se_hot_base',3)==0 and get(folder,'se_hot_caret',3)==caret
    assert get(folder,'se_h_current',4)==1 and get(folder,'se_h_dirty')==0
    assert get(folder,'se_diag_owned')==get(folder,'se_diag_active')==0
    assert get(folder,'se_doc_read_locks')==case['foreign']
    metadata=(folder/'metadata.bin').read_bytes()
    stable=metadata[s['se_doc_roots']-0x9A00:s['se_doc_roots']-0x9A00+512]+metadata[s['se_doc_generation']-0x9A00:s['se_doc_generation']-0x9A00+20]
    if initial_metadata is None:initial_metadata=stable
    assert stable==initial_metadata,'diagnostics published source/history'
    expected=source40(current,get(folder,'se_v_top',3),caret,pending=ident!='initial',error=case['error'])
    if case['kind']=='diag':
        assert int.from_bytes(d[8:11],'little')==len(source)
        assert int.from_bytes(d[22:24],'little')==binascii.crc_hqx(source,0xFFFF)
        assert int.from_bytes(d[11:13],'little')==2 and int.from_bytes(d[13:16],'little')==4
        assert d[16:19]==b'\x01\x01\x00'
        assert int.from_bytes(d[24:27],'little')==len(source)
        state=(folder/'state.bin').read_bytes()
        logical=state[s['se_reu_logical_owner']-0xC000:s['se_reu_logical_owner']-0xC000+256]
        physical=state[s['se_reu_physical_owner']-0xC000:s['se_reu_physical_owner']-0xC000+256]
        assert int.from_bytes(d[40:42],'little')==sum(0<b<255 for b in logical)
        assert int.from_bytes(d[42:44],'little')==physical.count(0)
        for offset,name in [(34,'se_reu_map'),(36,'se_reu_logical_owner'),(38,'se_reu_physical_owner')]:assert int.from_bytes(d[offset:offset+2],'little')==s[name]
        expected=diagnostic_popup(expected,d)
        if ident=='typed':initial_diag=d
        if ident=='ignored':assert d==initial_diag
    if case['kind']!='help':verify_screen(matrix,colors,expected,tag='native diagnostics '+ident);complete+=1
    else:
        decoded=native_screen_text(matrix);assert 'SuperEditor keyboard' in decoded and 'Help-D diag' in decoded
    (e/(ident+'-screen.txt')).write_text(native_screen_text(matrix)+'\n')
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
assert len(images['before'])==512*1024 and images['before']==images['after']
result=dict(status='passed',prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],asset_sha256={n:hashlib.sha256(v).hexdigest() for n,v in assets.items()},evidence=str(e),manifest=str(manifest),native_input_bytes=keys,screenshots=len(captures),complete_screen_oracles=complete,native_glyph_pixels=pixels_checked,pending_merged_source_bytes=len(source),committed_source_bytes=len(sample),independent_crc='binascii.crc_hqx/CRC16-CCITT-FALSE',full_reu_bytes_unchanged=512*1024,shim_bytes=1024,queued_STOP_cancels=True,missing_C11_preserves_foreign_lease=True,limits='Native KERNAL queue/IRQ input;fault injection changes C64 catalog ID only;not physical chords,cycle bounds or M2 whole-goal closure')
(e/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
