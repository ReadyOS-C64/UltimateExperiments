"""Integrated native File O/A/S acceptance, using actual ROM IEC and raw D81.

--describe is safe before production integration. --freeze/--run require the
parent's stable integrated build and exclusive VICE grant. No debugger source
replacement or modeled transport appears in this test.
"""
from datetime import datetime,timezone
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from d81_image import D81Image
from redraw_model import source40,native_text,verify_screen
from png_pixels import read_png
from run_vice import native_screen_text
from vice_config import PROJECT,step
from vice_plan import run_plan


def fixtures():
    text=native_text('# Native file UI acceptance\rMixed CASE and native bytes survive.\r\r```BASIC\r10 PRINT "Hello World"\r20 GOTO 10\r```\r\r')
    text+=native_text('\r'.join(f'Line {i:02d}: aligned source; **literal** emphasis and bullets remain source.' for i in range(18)))+b'\r'
    return {b'EDIN':text,b'EDNUL':bytes(range(256))*2+b'\0',b'EDEMPTYIN':b'',b'EDBIG':bytes((i*37+11)&255 for i in range(70001)),b'EDOLD':native_text('Original dirty-confirm target\r'),b'EDOVER':native_text('Original save-as overwrite target\r')}


def freeze():
    from cpu_editor import NAMES
    assert 'fileio' in NAMES and 'aux' in NAMES and len(NAMES)<=16,('Wait for stable integrated file/AUX build',NAMES)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');e=ROOT/'agentsworking/evidence/M4'/(stamp+'-editor-file-native');e.mkdir(parents=True)
    for name in ['editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json','supereditor.d81']:
        shutil.copyfile(ROOT/'build'/name,e/name)
    r=json.loads((e/'editor-report.json').read_text());assert hashlib.sha256((e/'editor.prg').read_bytes()).hexdigest()==r['sha256']
    for symbol in ['se_f_owner','se_f_current_name','se_f_current_len','se_f_name','se_f_name_len','se_f_device','se_f_ui_help','se_f_dos_error','se_fd_confirm','se_fd_list_names']:
        assert symbol in r['symbols'],('missing final file ABI',symbol)
    disk=D81Image((e/'supereditor.d81').read_bytes());assert disk.read(b'SUPEREDITOR',kind=2).data==(e/'editor.prg').read_bytes()
    for name in NAMES:
        data=(ROOT/f'build/overlays/{name}.seo').read_bytes();assert data[20:36]==data[36:52]==bytes.fromhex(r['resident_binding']['digest'])
        assert disk.read(name.upper().encode('ascii'),kind=1).data==data,(name,'packaged asset mismatch');(e/(name+'.seo')).write_bytes(data)
    for name in ['tests/test_editor_file_vice.py','tools/d81_image.py','tools/redraw_model.py','tools/vice_plan.py','tools/vice_config.py','tools/png_pixels.py']:
        out=e/'sources'/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,out)
    with zipfile.ZipFile(e/'product-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for folder in ['src','cfg']:
            for p in (ROOT/folder).rglob('*'):
                if p.is_file():z.write(p,p.relative_to(ROOT))
        z.write(ROOT/'Makefile','Makefile')
    (e/'freeze.json').write_text(json.dumps(dict(prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],disk_sha256=hashlib.sha256((e/'supereditor.d81').read_bytes()).hexdigest(),catalog=list(NAMES),asset_sha256={n:hashlib.sha256((e/(n+'.seo')).read_bytes()).hexdigest() for n in NAMES}),indent=2)+'\n')
    print('FROZEN '+str(e),flush=True);return e


def package(e):
    disk=e/'working.d81';shutil.copyfile(e/'supereditor.d81',disk);command=['c1541','-attach',str(disk)]
    for name,data in fixtures().items():
        path=e/(name.decode('ascii').lower()+'.petscii');path.write_bytes(data);command+=['-write',str(path),name.decode('ascii').lower()+',s']
    command+=['-list'];r=subprocess.run(command,capture_output=True,text=True);(e/'fixture-package.stdout.txt').write_text(r.stdout);(e/'fixture-package.stderr.txt').write_text(r.stderr);assert r.returncode==0
    parsed=D81Image(disk.read_bytes())
    for name,data in fixtures().items():assert parsed.read(name,kind=1).data==data,(name,'raw-sector fixture mismatch')
    shutil.copyfile(disk,e/'initial-fixtures.d81');(e/'fixture-package.json').write_text(json.dumps(dict(command=command,sha256=hashlib.sha256(disk.read_bytes()).hexdigest(),bytes={name.decode():len(data) for name,data in fixtures().items()}),indent=2)+'\n')


class NativePlan:
    def __init__(self,e,phase,report):
        self.e=e;self.out=e/phase;self.out.mkdir(exist_ok=True);assert not (self.out/'run').exists(),'Retain completed native run; use a fresh freeze';self.r=report;self.s=report['symbols'];self.steps=[];self.cases=[];self.keys=0
        self.canary=bytes((i*73+29)&255 for i in range(1024))
    def memory(self,ident,name,value,width=1):
        at=self.s[name] if isinstance(name,str) else name;data=value if isinstance(value,bytes) else value.to_bytes(width,'little')
        x=step(ident,'assert.memory',start=at,end=at+len(data)-1,equals_hex=data.hex(' '));x['retry']=dict(max_attempts=1000,backoff_ms=50,jitter=False);self.steps.append(x)
    def raw(self,ident,commands):
        path=self.out/(ident+'.mon');path.write_text('\n'.join(commands)+'\n');self.steps.append(step(ident,'monitor.command',command=f'raw: playback "{path}"'))
    def idle(self,ident,ui=0,error=0,owner=None):
        for name in ['se_e_job','se_e_draw_busy','se_e_redraw','se_doc_read_locks','se_n_owned']:
            self.memory(ident+'_'+name,name,0)
        self.memory(ident+'_ui','se_e_ui',ui)
        if error is not None:self.memory(ident+'_error','se_e_error',error)
        if owner is not None:self.memory(ident+'_owner','se_f_owner',owner)
        if ui==0:
            self.memory(ident+'_channels',0x98,0)
            # File/transport frames are a phase union and invalid after owner0.
    def send(self,ident,data,ui=0,error=0,owner=None):
        self.steps.append(step(ident,'input.sequence',keys=list(data),inter_key_delay_s=0.01,post_delay_s=0.12));self.keys+=len(data)
        self.memory(ident+'_keys','se_key_sequence',self.keys,2);self.idle(ident,ui,error,owner)
    def modal(self,ident,letter):self.send(ident,bytes([0x85,0x46,ord(letter)]),ui=3,error=None,owner=1)
    def name(self,ident,name,*,ui=0,error=0,owner=0):self.send(ident,bytes([0x14])*16+name+b'\r',ui=ui,error=error,owner=owner)
    def open(self,ident,name,choice=None,error=0):
        self.modal(ident+'_dialog','O')
        if choice:
            self.name(ident+'_requested_target',name,ui=3,owner=1)
            self.memory(ident+'_confirm','se_fd_confirm',1)
            # Choice follows the already entered OPEN target. S saves the
            # bound current file and automatically resumes this frozen request.
            self.send(ident+'_dirty_'+choice,choice.encode('ascii'),owner=0)
            return
        if error:
            self.name(ident+'_accept',name,ui=3,owner=1)
            self.memory(ident+'_file_error','se_f_error',error)
            self.memory(ident+'_dos_error','se_f_dos_error',62)
        else:self.name(ident+'_accept',name)
    def save_as(self,ident,name):self.modal(ident+'_dialog','A');self.name(ident+'_accept',name)
    def boot(self):
        self.steps += [step('launch','vice.launch',kill_stale=False),step('basic','screen.wait_contains',text='READY.',wait_timeout_s=30)]
        self.raw('resources',['resourceset "MachineVideoStandard" "1"','resourceset "VICIIModel" "0"','resourceset "REU" "0"','resourceset "REUsize" "1024"','resourceset "REU" "1"','warp','resourceget "Drive8TrueEmulation"'])
        self.steps.append(step('shim_seed','memory.write',start=0xC600,bytes_hex=self.canary.hex(' ')))
        self.steps.append(step('boot','input.sequence',keys=list(b'LOAD"SUPEREDITOR",8,1\rRUN\r'),inter_key_delay_s=0.04,post_delay_s=0.15))
        self.memory('ready','se_status',1);self.idle('boot',owner=0)
    def capture(self,ident,source,*,dirty=False,current=None,ui=0,error=0,help=False,name=None,caret=None,list_page=None,history=None):
        self.cases.append(dict(id=ident,source=source.hex(),dirty=dirty,current=current.decode('ascii') if current is not None else None,ui=ui,error=error,help=help,name=name.decode('ascii') if name is not None else None,caret=caret,list_page=list_page,history=history))
        self.memory(ident+'_length','se_doc_length',len(source),3);self.memory(ident+'_pending','se_hot_pending',0)
        if ui==0:self.memory(ident+'_dirty','se_h_dirty',int(dirty))
        self.steps.append(step(ident+'_native','monitor.command',command=f'raw: screenshot "{self.out}/native-{ident}.png" 2'))
        # RAM only, throughCFFF; avoid destructive reads of CIA/other I/O. Color
        # RAM is safe and captured separately. This accommodates resident frames
        # moving while retaining the complete1024-byte shim for comparison.
        self.steps.append(step(ident+'_ram','dump.memory_ranges',ranges=[dict(label='ram',start=0,end=0xCFFF),dict(label='colors',start=0xD800,end=0xDBE7)]))
        self.steps.append(step(ident+'_reu','dump.reu',mode='full',stage_tag=ident+'_reu'))
    def plan(self):
        self.memory('final_shim',0xC600,self.canary);self.memory('final_channels',0x98,0)
        return dict(version=1,kind='vice_task_plan',plan_id='supereditor-file-ui-'+self.e.name+'-'+self.out.name,run_mode='gui_vice',global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=6580,monitor_port_span=30,retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),timeouts=dict(launch_s=30,step_s=60,read_s=2),artifact_policy=dict(capture_screen=False,capture_state=False,capture_dump=False),vice=dict(disk8=str(self.e/'working.d81'),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,true_drive=False,close_vice=True,headless=True,speed_percent=100)),steps=self.steps)


def scenario(e,report,phase):
    n=NativePlan(e,phase,report);n.boot();f=fixtures();prg=(e/'editor.prg').read_bytes();s=report['symbols'];tutorial=prg[2+s['sample']-0x801:2+s['sample_end']-0x801]
    if phase=='restart':
        expected={b'EDNEW':bytes([0xD8,0xD9])+f[b'EDIN'],b'EDBIN':f[b'EDNUL'],b'EDEMPTY':b'',b'EDLARGE':f[b'EDBIG']}
        for name,data in expected.items():n.open('reopen_'+name.decode(),name);n.capture('reopen_'+name.decode(),data,current=name,caret=0)
        return n
    n.capture('initial',tutorial,current=b'',caret=0)
    n.modal('open_modal','O');n.capture('open-modal',tutorial,current=b'',ui=3,caret=0,list_page=0)
    n.send('choose_down',bytes([0x11]),ui=3,error=None,owner=1);n.memory('selected_index1','se_fd_list_index',1)
    n.send('choose_up',bytes([0x91]),ui=3,error=None,owner=1);n.memory('selected_index0','se_fd_list_index',0)
    n.send('directory_page',bytes([0x87]),ui=3,error=None,owner=1);n.memory('directory_page1','se_fd_page',1,2);n.capture('directory-page1',tutorial,current=b'',ui=3,caret=0,list_page=1)
    n.send('clear_name',bytes([0x14])*16,ui=3,error=None,owner=1);n.memory('empty_name','se_f_name_len',0)
    n.send('name_limit',b'1234567890ABCDEFZZ',ui=3,error=None,owner=1);n.memory('name_clamped','se_f_name_len',16);n.memory('name_exact','se_f_name',b'1234567890ABCDEF')
    n.send('modal_ignores_F1_F7',bytes([0x85,0x88]),ui=3,error=None,owner=1);n.memory('ignored_global_name','se_f_name_len',16)
    n.send('drive9',bytes([0x86]),ui=3,error=None,owner=1);n.memory('device9','se_f_device',9);n.capture('device9-modal',tutorial,current=b'',ui=3,error=None,name=b'1234567890ABCDEF',caret=0)
    n.send('drive8',bytes([0x86]),ui=3,error=None,owner=1);n.memory('device8','se_f_device',8)
    n.send('modal_help',bytes([0x8B]),ui=3,error=None,owner=1);n.memory('help_on','se_f_ui_help',1);n.capture('modal-help',tutorial,current=b'',ui=3,error=None,help=True,caret=0)
    n.send('close_modal_help',bytes([0x8B]),ui=3,error=None,owner=1);n.memory('help_off','se_f_ui_help',0)
    n.send('cancel_modal',bytes([3]),owner=0);n.capture('cancelled',tutorial,current=b'',caret=0)
    n.modal('initial_save_falls_back','S');n.send('cancel_initial_save',bytes([3]),owner=0)
    n.open('missing_open',b'EDMISSING',error=0x93);n.capture('missing-preserves',tutorial,current=b'',ui=3,error=0,caret=0)
    n.send('missing_STOP',bytes([3]),owner=0);n.capture('missing-cancelled',tutorial,current=b'',caret=0)
    n.send('selection_before_open',bytes([0x89,0x1D,0x1D]),owner=0)
    n.open('retry_missing',b'EDMISSING',error=0x93);n.memory('failed_open_caret_preserved','se_hot_caret',2,3);n.name('retry_correct_name',b'EDIN');n.memory('opened_selection_cleared','se_sel_mark',0);source=f[b'EDIN'];n.capture('opened',source,current=b'EDIN',caret=0,history=(1, 1, 0))
    n.modal('saveas_cancel','A');n.send('cancel_saveas',bytes([3]),owner=0)
    n.send('type_X',bytes([0xD8]),error=0);n.save_as('saveas_new',b'EDNEW');source=bytes([0xD8])+source;n.capture('saved-new',source,current=b'EDNEW',caret=1,history=(2, 2, 75))
    n.send('type_Y',bytes([0xD9]),error=0);n.send('save_current',bytes([0x85,0x46,0x53]),owner=0);source=source[:1]+bytes([0xD9])+source[1:];n.capture('saved-current',source,current=b'EDNEW',caret=2,history=(3, 3, 150))
    n.send('type_Z',bytes([0xDA]),error=0);source=source[:2]+bytes([0xDA])+source[2:];n.modal('dirty_cancel_dialog','O');n.name('dirty_cancel_target',b'EDOLD',ui=3,owner=1);n.memory('dirty_confirm1','se_fd_confirm',1);n.capture('dirty-confirm',source,dirty=True,current=b'EDNEW',ui=3,caret=3)
    n.send('confirm_help',bytes([0x8B]),ui=3,owner=1);n.capture('confirm-help',source,dirty=True,current=b'EDNEW',ui=3,help=True,caret=3);n.send('confirm_help_close',bytes([0x8B]),ui=3,owner=1)
    n.send('dirty_cancel_C',b'C',owner=0);n.capture('dirty-cancel',source,dirty=True,current=b'EDNEW',caret=3,history=(4, 3, 225))
    n.open('dirty_discard',b'EDOLD',choice='D');source=f[b'EDOLD'];n.capture('dirty-discard-open',source,current=b'EDOLD',caret=0,history=(1, 1, 0))
    n.send('type_Q',bytes([0xD1]),error=0);n.open('dirty_save_then_open',b'EDNUL',choice='S');source=f[b'EDNUL'];n.capture('nul-open',source,current=b'EDNUL',caret=0,history=(1, 1, 0))
    n.save_as('binary_saveas',b'EDBIN');n.capture('nul-save',source,current=b'EDBIN',caret=0,history=(1, 1, 0))
    n.save_as('overwrite_other_target',b'EDOVER');n.capture('overwrite',source,current=b'EDOVER',caret=0,history=(1, 1, 0))
    n.open('empty_open',b'EDEMPTYIN');source=b'';n.capture('empty-open',source,current=b'EDEMPTYIN',caret=0,history=(1, 1, 0))
    n.save_as('empty_save',b'EDEMPTY');n.capture('empty-save',source,current=b'EDEMPTY',caret=0,history=(1, 1, 0))
    n.open('large_open',b'EDBIG');source=f[b'EDBIG'];n.capture('large-open',source,current=b'EDBIG',caret=0,history=(1, 1, 0))
    n.save_as('large_save',b'EDLARGE');n.capture('large-save',source,current=b'EDLARGE',caret=0,history=(1, 1, 0))
    return n


def evaluate(n,artifacts,manifest):
    images={}
    for index in (artifacts/'dumps').glob('*.json'):
        for chunk in json.loads(index.read_text(encoding='utf-8-sig')).get('chunks',[]):
            if chunk.get('source')=='vice_native_reu_image':
                ident=index.name.removeprefix('reu_').removesuffix('_reu_index.json');images[ident]=(index.parent/Path(chunk['file']).name).read_bytes()
    observations=[];screens=pixels=0
    for c in n.cases:
        ident=c['id'];folder=artifacts/'stages'/(ident+'_ram');ram=(folder/'ram.bin').read_bytes();image=images[ident];assert len(ram)==0xD000 and len(image)==1024*1024
        def get(name,width=1):
            at=n.s[name];assert at+width<=len(ram),(name,hex(at));return int.from_bytes(ram[at:at+width],'little')
        def obj(identity,offset,length):
            output=bytearray()
            while length:
                count=min(length,65536-(offset&65535));bank=ram[n.s['object_extents']+identity*16+(offset>>16)]
                output+=image[bank*65536+(offset&65535):bank*65536+(offset&65535)+count];offset+=count;length-=count
            return bytes(output)
        source=bytearray();metadata=get('se_doc_meta');root=n.s['se_doc_roots']
        for i in range(get('se_doc_root_count')):
            item=ram[root+i*8:root+(i+1)*8];leaf=obj(metadata,item[0]*1024,item[1]*16)
            for j in range(item[1]):
                piece=leaf[j*16:(j+1)*16];identity=piece[0];generation=int.from_bytes(piece[1:3],'little')
                assert generation==ram[n.s['object_gen_lo']+identity]+256*ram[n.s['object_gen_hi']+identity]
                source+=obj(identity,int.from_bytes(piece[3:6],'little'),int.from_bytes(piece[6:9],'little'))
        catalog=json.loads((n.e/'freeze.json').read_text())['catalog']
        for i,name in enumerate(catalog):
            payload=(n.e/(name+'.seo')).read_bytes()[36:];assert image[65536+i*4096:65536+i*4096+len(payload)]==payload,(ident,'actualREUcatalog',name)
        expected=bytes.fromhex(c['source']);assert source==expected and len(source)==get('se_doc_length',3),(ident,'full document source')
        assert ram[0xC600:0xCA00]==n.canary,(ident,'shim')
        assert get('se_e_ui')==c['ui'] and not get('se_hot_pending')
        assert c['caret'] is None or get('se_hot_caret',3)==c['caret'],(ident,'caret moved')
        assert get('se_h_dirty')==int(c['dirty'])
        if c['history'] is not None:assert [get('se_h_current',4),get('se_h_saved',4),get('se_h_end',2)]==list(c['history']),(ident,'history/savepoint preserved')
        assert c['error'] is None or get('se_e_error')==c['error']
        if c['current'] is not None:
            name=c['current'].encode('ascii');assert get('se_f_current_len')==len(name) and ram[n.s['se_f_current_name']:n.s['se_f_current_name']+len(name)]==name,(ident,'bound filename')
            if name:assert get('se_f_current_device')==8,(ident,'bound device')
        matrix=ram[0x4000:0x43E8];font=ram[0x4800:0x5000];colors=(folder/'colors.bin').read_bytes();text=native_screen_text(matrix);(n.out/(ident+'-screen.txt')).write_text(text+'\n')
        if not c['ui']:
            assert get('se_f_owner')==0
            assert get('se_doc_read_locks')==get('se_n_owned')==get('se_e_job')==0
            assert get('se_h_dirty')==int(c['dirty'])
            if not c['dirty']:assert get('se_h_current',4)==get('se_h_saved',4)
            expected_screen=source40(expected,get('se_v_top',3),get('se_hot_caret',3),dirty=c['dirty'],error=c['error'] or 0)
            verify_screen(matrix,colors,expected_screen,tag='native file UI '+ident);screens+=1
            rows=tuple(int.from_bytes(ram[n.s['se_v_rows']+i*3:n.s['se_v_rows']+i*3+3],'little') for i in range(22))+(get('se_v_bottom',3),)
            assert rows==expected_screen.anchors
        else:
            assert get('se_f_owner')==1 and bool(get('se_f_ui_help'))==c['help']
            if c['name'] is not None:
                name=c['name'].encode('ascii');assert get('se_f_name_len')==len(name) and ram[n.s['se_f_name']:n.s['se_f_name']+len(name)]==name
            if c['list_page'] is not None:
                entries=[item.name for item in D81Image((n.e/'initial-fixtures.d81').read_bytes()).entries() if item.kind==1];wanted=entries[c['list_page']*8:c['list_page']*8+8]
                assert get('se_fd_page',2)==c['list_page'] and get('se_fd_list_count')==len(wanted)
                for i,name in enumerate(wanted):assert ram[n.s['se_fd_list_lengths']+i]==len(name) and ram[n.s['se_fd_list_names']+i*16:n.s['se_fd_list_names']+i*16+len(name)]==name,(ident,'native listing vs raw directory',i,name)
            assert 'file' in text.lower() or 'open' in text.lower() or 'save' in text.lower(),(ident,'modal content',text)
        w,h,bitmap=read_png(n.out/f'native-{ident}.png');assert(w,h)==(384,272);bg=bitmap[0]
        for row in range(25):
            for col in range(40):
                for y in range(8):
                    bits=font[matrix[row*40+col]*8+y]
                    for x in range(8):assert (bitmap[(35+row*8+y)*w+32+col*8+x]!=bg)==bool(bits&(128>>x)),(ident,row,col,x,y)
        pixels+=64000;observations.append(dict(id=ident,source_bytes=len(expected),source_sha256=hashlib.sha256(expected).hexdigest(),caret=get('se_hot_caret',3),top=get('se_v_top',3),ui=c['ui'],dirty=c['dirty']))
    result=dict(status='passed',evidence=str(n.out),manifest=str(manifest),prg_sha256=n.r['sha256'],resident_binding=n.r['resident_binding']['digest'],executed_test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),asset_count=len(json.loads((n.e/'freeze.json').read_text())['catalog']),screenshots=len(n.cases),complete_source_screens=screens,native_glyph_pixels=pixels,shim_bytes=1024,reu_kib=1024,native_input_bytes=n.keys,cases=observations,limitations='Integrated actual File menu/modal/ROM IEC path and IRQ-native bytes; no physical keyboard or power-loss proof. Initial fixture files are packaged raw SEQ, no debugger source replacement.')
    (n.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


def disk_oracle(e):
    before=D81Image((e/'initial-fixtures.d81').read_bytes());after=D81Image((e/'working.d81').read_bytes());f=fixtures()
    expected={b'EDNEW':bytes([0xD8,0xD9])+f[b'EDIN'],b'EDBIN':f[b'EDNUL'],b'EDEMPTY':b'',b'EDLARGE':f[b'EDBIG'],b'EDOLD':bytes([0xD1])+f[b'EDOLD'],b'EDOVER':f[b'EDNUL']}
    original={item.name for item in before.entries()};assert {item.name for item in after.entries()}==original|set(expected),'orphaned temp/backup or unexpected file'
    for name,data in expected.items():assert after.read(name,kind=1).data==data,(name,'byte-exact saved source')
    unchanged=0
    for name in original-set(expected):
        a,b=before.read(name),after.read(name);assert a.entry.kind==b.entry.kind and a.entry.closed==b.entry.closed and a.entry.locked==b.entry.locked and a.entry.first==b.entry.first and a.entry.blocks==b.entry.blocks
        assert a.data==b.data and a.sectors==b.sectors,(name,'unrelated file/sector chain modified');unchanged+=1
    result=dict(status='passed',expected_saved_bytes={name.decode():dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest()) for name,data in expected.items()},unrelated_files_and_sector_chains_unchanged=unchanged,empty_save_terminal_index=after.read(b'EDEMPTY',kind=1).sectors[-1][2][1],final_disk_sha256=hashlib.sha256((e/'working.d81').read_bytes()).hexdigest(),oracle='Independent raw1581 sectors, including00/01zero-byte terminal; no c1541 sequential read')
    assert result['empty_save_terminal_index']==1
    (e/'disk-result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--describe',action='store_true');parser.add_argument('--freeze',action='store_true');parser.add_argument('--prepare',type=Path);parser.add_argument('--run',type=Path);args=parser.parse_args()
    if args.describe:
        print(json.dumps(dict(fixtures={name.decode():len(data) for name,data in fixtures().items()},requires='Stable complete production catalog/ui3/job9; explicit exclusive VICE grant',coverage=['modalname16/DEL/F3/F6/STOP','clean/missingOPEN','dirtyOPEN C/D/S','saveas/new/current/overwrite','trueempty/NUL/70001bytes','actualrestart/reopen','rawD81immutable-sectororacle']),indent=2));return
    if args.freeze:freeze();return
    if not args.prepare and not args.run:parser.print_help();return
    e=(args.prepare or args.run).resolve();r=json.loads((e/'editor-report.json').read_text())
    if not (e/'initial-fixtures.d81').exists():package(e)
    for phase in ['editing','restart']:
        n=scenario(e,r,phase);plan=n.plan();(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n')
        print(f'Prepared {phase}: {len(n.steps)} steps/{n.keys} native keys/{len(n.cases)} screenshots at {n.out}',flush=True)
        if args.run:
            b=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120);assert b.returncode==0,b.stdout+b.stderr
            artifacts,manifest=run_plan(plan,n.out);evaluate(n,artifacts,manifest)
    if args.run:print(json.dumps(disk_oracle(e),indent=2))

if __name__=='__main__':main()
