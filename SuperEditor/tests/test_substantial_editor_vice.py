"""Substantial-source native IRQ acceptance on an explicitly frozen D81.

The only debugger-assisted product setup is a TYPE5 fixture import through the
real resident object API. All document changes after boot use normal editor
commands through the .NET harness's KERNAL native-byte input path.
"""
from datetime import datetime, timezone
import binascii
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
# Current final acceptance binds its complete ten-asset catalog explicitly.
NAMES=('eedit','eplay','window','text40','menu40','engine','navigate','search','block','layout')
from navigation_model import move,visual_rows
from overlays import HEADER
from png_pixels import read_png
from redraw_model import source40,verify_screen,native_text
from run_vice import native_screen_text
from vice_config import PROJECT,step
from vice_plan import run_plan


def freeze():
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    e=ROOT/'agentsworking/evidence/M3'/(stamp+'-substantial-final');e.mkdir(parents=True)
    for name in ['editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json','supereditor.d81']:
        shutil.copyfile(ROOT/'build'/name,e/name)
    r=json.loads((e/'editor-report.json').read_text());assert hashlib.sha256((e/'editor.prg').read_bytes()).hexdigest()==r['sha256']
    for name in NAMES:
        data=(ROOT/f'build/overlays/{name}.seo').read_bytes();assert data[20:36]==data[36:52]==bytes.fromhex(r['resident_binding']['digest'])
        (e/(name+'.seo')).write_bytes(data)
    with zipfile.ZipFile(e/'product-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for directory in ['src','cfg']:
            for path in (ROOT/directory).rglob('*'):
                if path.is_file():archive.write(path,path.relative_to(ROOT))
        archive.write(ROOT/'Makefile','Makefile')
    (e/'freeze.json').write_text(json.dumps(dict(prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],disk_sha256=hashlib.sha256((e/'supereditor.d81').read_bytes()).hexdigest(),assets={n:hashlib.sha256((e/(n+'.seo')).read_bytes()).hexdigest() for n in NAMES}),indent=2)+'\n')
    print('FROZEN '+str(e),flush=True);return e


def main(e=None,prepare=False):
    if e is None:e=freeze()
    e=e.resolve();assert not (e/'run').exists(),'Native run already exists: use --verify or a fresh frozen evidence directory';r=json.loads((e/'editor-report.json').read_text());s=r['symbols']
    prg=(e/'editor.prg').read_bytes();assert hashlib.sha256(prg).hexdigest()==r['sha256']
    assert json.loads((e/'freeze.json').read_text())['assets']=={name:hashlib.sha256((e/(name+'.seo')).read_bytes()).hexdigest() for name in NAMES}
    assert hashlib.sha256((e/'supereditor.d81').read_bytes()).hexdigest()==json.loads((e/'freeze.json').read_text())['disk_sha256']
    sample=prg[2+s['sample']-0x801:2+s['sample_end']-0x801]
    intro=['# SuperEditor substantial source acceptance','Mixed CASE and lower case survive PETSCII.','',
           '- A literal bullet with **bold** and *italic* source.','1. Numbered source item; no formatted-render claim.',
           '```BASIC','10 PRINT "Hello World"','20 FOR I=1 TO 40:PRINT I:NEXT I','```','',
           '```ASM','start: lda #$01','       sta $d020','       rts','```','']
    lines=intro+['LONG CODE '+('0123456789ABCDEF'*26),'']
    long_line=len(intro)+1
    for i in range(12):
        lines += [f'## Section {i+1:02d}: Mixed Case PETSCII',
          'Words wrap across forty columns while source bytes and CR boundaries stay exact.',
          '- Selection crosses pages; copied text retains every original byte.',
          '1. Undo and redo reuse append references without changing immutable text.',
          f'Code {i:02d}: LDA #$2A / STA $D020 / RTS. literal **styles** remain editable.', '']
    source_fixture=native_text('\r'.join(lines))
    source_fixture+=native_text('Native pound: ')+bytes([0x5C])+native_text(' / graphic cells: ')+bytes([0xA0,0xB0,0xC0,0xFF])+b'\r'
    assert 4096<len(source_fixture)<16384
    (e/'fixture.petscii').write_bytes(source_fixture)
    (e/'fixture-host.txt').write_text('\n'.join(lines)+'\nNative pound and graphics are raw PETSCII bytes.\n')
    shutil.copyfile(e/'supereditor.d81',e/'working.d81')
    dest=e/'sources/tests/test_substantial_editor_vice.py';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(__file__,dest)
    for name in ['redraw_model.py','navigation_model.py','vice_plan.py','vice_config.py','png_pixels.py']:
        out=e/'sources/tools'/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'tools'/name,out)
    steps=[];keys=0;captures=[];canary=bytes((i*73+29)&255 for i in range(1024))
    source=sample;caret=0;anchor=0;marked=False;pending=False;node=1;generation=2
    def write(ident,name,value,width=1):
        at=s[name] if isinstance(name,str) else name
        data=value if isinstance(value,bytes) else value.to_bytes(width,'little')
        steps.append(step(ident,'memory.write',start=at,bytes_hex=data.hex(' ')))
    def memory(ident,name,value,width=1):
        at=s[name] if isinstance(name,str) else name
        data=value if isinstance(value,bytes) else value.to_bytes(width,'little')
        item=step(ident,'assert.memory',start=at,end=at+len(data)-1,equals_hex=data.hex(' '))
        item['retry']=dict(max_attempts=50,backoff_ms=40,jitter=False);steps.append(item)
    def raw(ident,commands):
        path=e/(ident+'.mon');path.write_text('\n'.join(commands)+'\n')
        steps.append(step(ident,'monitor.command',command=f'raw: playback "{path}"'))
    def api(ident,name,a=0,x=0,copy_token=False):
        code=bytes([0x20])+s[name].to_bytes(2,'little')+bytes([0x8D,0xE0,0x0E,0xA9,0,0x69,0,0x8D,0xE1,0x0E])
        # Carry recorded before any further API; normal idle resumes afterwards.
        if copy_token:
            code+=bytes([0xA2,4,0xBD])+s['se_object_id'].to_bytes(2,'little')+bytes([0x9D])+s['se_clip_token'].to_bytes(2,'little')+bytes([0xCA,0x10,0xF7])
        stop=0x0E00+len(code);code+=bytes([0xEA,0x4C])+s['se_idle'].to_bytes(2,'little')
        raw(ident,[f'> 0e00 {code.hex(" ")}',f'registers PC=$0e00, SP=$ff, FL=$20, A=${a:02x}, X=${x:02x}',f'until ${stop:04x}'])
        memory(ident+'_carry',0x0EE1,0)
    def idle(ident):
        memory(ident+'_job','se_e_job',0)
        memory(ident+'_paint','se_e_redraw',bytes([0,0]))
        memory(ident+'_error','se_e_error',0)
    def send(ident,data):
        nonlocal keys
        steps.append(step(ident,'input.sequence',keys=list(data),inter_key_delay_s=0.005,post_delay_s=0.08));keys+=len(data)
        memory(ident+'_consumed','se_key_sequence',keys,2);idle(ident)
    def f7(ident,text):send(ident,bytes([0x88])+text.encode('ascii')+b'\r')
    def capture(ident,ui=0,require_context=False):
        captures.append(dict(id=ident,source=source.hex(),caret=caret,anchor=anchor,marked=marked,pending=pending,node=node,generation=generation,ui=ui,require_context=require_context))
        memory(ident+'_caret','se_hot_caret',caret,3);memory(ident+'_node','se_h_current',node,4)
        memory(ident+'_generation','se_doc_generation',generation,2);memory(ident+'_ui','se_e_ui',ui)
        steps.append(step(ident+'_native','monitor.command',command=f'raw: screenshot "{e}/native-{ident}.png" 2'))
        steps.append(step(ident+'_ram','dump.memory_ranges',ranges=[dict(label='state',start=0xC000,end=0xC5FF),dict(label='view',start=0x8C00,end=0x8CFF),dict(label='metadata',start=0x9A00,end=0x9FFF),dict(label='hot',start=0x9200,end=0x99FF),dict(label='matrix',start=0x4000,end=0x43E7),dict(label='font',start=0x4800,end=0x4FFF),dict(label='colors',start=0xD800,end=0xDBE7)]))
        steps.append(step(ident+'_reu','dump.reu',mode='full',stage_tag=ident+'_reu'))
    steps += [step('launch','vice.launch',kill_stale=False),step('basic','screen.wait_contains',text='READY.',wait_timeout_s=30)]
    raw('resources',['resourceset "MachineVideoStandard" "1"','resourceset "VICIIModel" "0"','resourceset "REU" "0"','resourceset "REUsize" "512"','resourceset "REU" "1"','warp','resourceget "Drive8TrueEmulation"'])
    write('shim_seed',0xC600,canary)
    steps.append(step('boot','input.sequence',keys=list(b'LOAD"SUPEREDITOR",8,1\rRUN\r'),inter_key_delay_s=0.04,post_delay_s=0.15))
    memory('ready','se_status',1);memory('first_draw','se_e_draw_sequence',1,2);idle('boot')
    steps.append(step('boot_reu','dump.reu',mode='full',stage_tag='boot_reu'))
    # Fixture publication into a private clipboard object, not a document edit.
    api('fixture_allocate','se_object_create',5,1,True)
    memory('fixture_object_id','se_clip_token',bytes([4,1,0,1,0]))
    for i,offset in enumerate(range(0,len(source_fixture),1024)):
        chunk=source_fixture[offset:offset+1024]
        write(f'fixture_{i}_host',0x8000,chunk);write(f'fixture_{i}_offset','se_object_offset',offset,3)
        write(f'fixture_{i}_length','se_object_length',len(chunk),2);write(f'fixture_{i}_hostptr','se_object_c64',0x8000,2)
        api(f'fixture_{i}_stash','se_object_copy')
    write('fixture_size','se_object_offset',len(source_fixture),3);api('fixture_resize','se_object_resize')
    write('fixture_clip_length','se_clip_length',len(source_fixture),3);write('fixture_clip_generation','se_clip_generation',2,2);write('fixture_active','se_clip_active',1)
    api('fixture_validate','se_clip_validate');memory('source_not_debugger_replaced','se_doc_length',len(sample),3)
    steps.append(step('fixture_reu','dump.reu',mode='full',stage_tag='fixture_reu'))
    # From this point every edit/navigation/clipboard/history operation is UI input.
    f7('select_top','TOP');send('start_mark',bytes([0x89]));f7('select_bottom','BOTTOM');send('paste_fixture',bytes([0x16]))
    source=source_fixture;caret=len(source);node=2;generation=3
    capture('large-paste',require_context=True)
    f7('top','TOP');caret=0;capture('top')
    send('page_down',bytes([0x87]));caret,_=move(39,source,caret);p21=caret;capture('page-down')
    send('mark_page',bytes([0x89]));anchor=caret;marked=True
    send('reverse_page',bytes([0x86]));caret,_=move(38,source,caret);capture('reverse-selection')
    send('block_menu',bytes([0x85,0x42]));capture('block-menu',1)
    send('copy_menu',b'C');clip=source[:p21]
    send('stop_mark',bytes([3]));marked=False
    f7('append_bottom','BOTTOM');caret=len(source)
    send('paste_copy',bytes([0x16]));source+=clip;caret=len(source);node=3;generation=4;capture('page-paste',require_context=True)
    send('undo_menu',bytes([0x85,0x45,0x55]));source=source_fixture;caret=len(source);node=2;generation=5;capture('paste-undo',require_context=True)
    send('redo_key',bytes([0x19]));source+=clip;caret=len(source);node=3;generation=6
    f7('cut_top','TOP');caret=0;send('cut_mark',bytes([0x89]));anchor=0;marked=True
    send('cut_two_pages',bytes([0x87,0x87]));caret,_=move(39,source,caret);caret,_=move(39,source,caret);p42=caret;cut=source[:p42]
    send('cut_key',bytes([0x18]));source=source[p42:];caret=0;marked=False;node=4;generation=7;capture('two-page-cut',require_context=True)
    send('cut_undo',bytes([0x1A]));source=source_fixture+clip;caret=p42;node=3;generation=8
    send('cut_redo',bytes([0x19]));source=source[p42:];caret=0;node=4;generation=9
    send('restore_cut_menu',bytes([0x85,0x42,0x50]));source=cut+source;caret=p42;node=5;generation=10;capture('cut-restored',require_context=True)
    f7('repeat_top','TOP');caret=0
    send('repeat_navigation',bytes([0x1D])*96+bytes([0x9D])*40);caret=56
    send('repeat_typing',bytes([0xD2])*96);source=source[:56]+bytes([0xD2])*96+source[56:];caret=152;pending=True;capture('repeat-typing')
    send('flush_home',bytes([0x13]));caret,_=move(32,source,caret);pending=False;node=6;generation=11
    f7('typing_undo','UNDO');source=source_fixture+clip;caret=56;node=5;generation=12
    f7('typing_redo','REDO');source=source[:56]+bytes([0xD2])*96+source[56:];caret=152;node=6;generation=13;capture('typing-redo',require_context=True)
    f7('goto_long_line',f'GOTO {long_line}');caret=sum(len(v)+1 for v in source.split(b'\r')[:long_line-1])
    send('jump_forty',bytes([0x0C])*3+bytes([0x0A])*2)
    for command in [41,41,41,40,40]:caret,_=move(command,source,caret)
    capture('long-line-jumps')
    f7('final_top','TOP');caret=0;capture('final-top')
    memory('shim_intact',0xC600,canary);memory('channels_closed',0x98,0)
    for name in ['se_doc_read_locks','se_hot_owned','se_clip_busy','se_b_phase','se_h_owned_lease','se_h_owned_capture','se_h_owned_splice','se_n_owned']:
        memory('released_'+name,name,0)
    plan=dict(version=1,kind='vice_task_plan',plan_id='supereditor-substantial-'+e.name,run_mode='gui_vice',global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=6580,monitor_port_span=30,retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),timeouts=dict(launch_s=30,step_s=60,read_s=2),artifact_policy=dict(capture_screen=False,capture_state=False,capture_dump=False),vice=dict(disk8=str(e/'working.d81'),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,true_drive=False,close_vice=True,headless=True,speed_percent=100)),steps=steps)
    (e/'cases.json').write_text(json.dumps(captures,indent=2)+'\n')
    if prepare:
        (e/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n')
        print(f'PREPARED ONLY {e}: {len(source_fixture)} bytes/{len(visual_rows(source_fixture))} rows/{keys} native bytes/{len(steps)} steps; no VICE launched',flush=True)
        return
    build=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120);assert build.returncode==0,build.stdout+build.stderr
    print(f'Prepared {len(source_fixture)} bytes, {len(visual_rows(source_fixture))} rows, {keys} native input bytes, {len(steps)} steps at {e}',flush=True)
    artifacts,manifest=run_plan(plan,e)
    verify(e,r,s,sample,source_fixture,clip,cut,captures,keys,artifacts,manifest)


def verify(e,r,s,sample,fixture,clip,cut,cases,keys,artifacts,manifest):
    catalog=tuple(name for name in NAMES if (e/(name+'.seo')).exists())
    assert catalog in [NAMES,NAMES[:-1]],catalog
    images={}
    for index in (artifacts/'dumps').glob('*.json'):
        for item in json.loads(index.read_text(encoding='utf-8-sig')).get('chunks',[]):
            if item.get('source')=='vice_native_reu_image':
                image=(index.parent/Path(item['file']).name).read_bytes();assert len(image)==512*1024
                matches=[c['id']+'_reu' for c in cases if index.name=='reu_'+c['id']+'_reu_index.json']+[x for x in ['boot_reu','fixture_reu'] if index.name=='reu_'+x+'_index.json']
                assert len(matches)==1,(index,matches);images[matches[0]]=image
    def field(folder,name,width=1):
        at=s[name]
        for label,base,end in [('state',0xC000,0xC600),('view',0x8C00,0x8D00),('metadata',0x9A00,0xA000)]:
            if base<=at and at+width<=end:
                data=(folder/(label+'.bin')).read_bytes()[at-base:at-base+width];assert len(data)==width
                return int.from_bytes(data,'little')
        raise AssertionError(('uncaptured symbol',name,hex(at)))
    screen_count=pixels_checked=0;observations=[]
    for case in cases:
        ident=case['id'];folder=artifacts/'stages'/(ident+'_ram');get=lambda n,w=1:field(folder,n,w)
        meta=(folder/'metadata.bin').read_bytes();image=images[ident+'_reu'];expected=bytes.fromhex(case['source'])
        # Rebuild committed document from real active roots, leaves and object extents.
        def obj(identity,offset,length):
            output=bytearray()
            while length:
                n=min(length,65536-(offset&65535));at=s['object_extents']-0x9A00+identity*16+(offset>>16)
                bank=meta[at];output+=image[bank*65536+(offset&65535):bank*65536+(offset&65535)+n];offset+=n;length-=n
            return bytes(output)
        committed=bytearray();root=s['se_doc_roots']-0x9A00
        for i in range(get('se_doc_root_count')):
            record=meta[root+i*8:root+(i+1)*8];leaf=obj(0,record[0]*1024,record[1]*16)
            for j in range(record[1]):
                p=leaf[j*16:(j+1)*16];assert p[0] in [1,2] and p[1:3]==b'\x01\x00'
                committed+=obj(p[0],int.from_bytes(p[3:6],'little'),int.from_bytes(p[6:9],'little'))
        assert len(committed)==get('se_doc_length',3)
        hot=(folder/'hot.bin').read_bytes();left=get('se_hot_left',2);right=get('se_hot_right',2);base=get('se_hot_base',3)
        if case['pending']:
            merged=bytes(committed[:base])+hot[:left]+hot[right:]+bytes(committed[base+get('se_hot_old_length',2):])
        else:merged=bytes(committed)
        assert merged==expected,(ident,'exact merged source',len(merged),len(expected))
        assert get('se_v_top',3) in {start for start,end in visual_rows(expected)},(ident,'viewport is not globally row-aligned')
        if case.get('require_context'):
            starts=[start for start,end in visual_rows(expected)];row=max(i for i,start in enumerate(starts) if start<=case['caret'])
            wanted=starts[max(0,row-21)]
            assert get('se_v_top',3)==wanted,(ident,'invalidated viewport must retain21 preceding rows',get('se_v_top',3),wanted)
        if not case['pending']:assert committed==expected
        assert get('se_hot_caret',3)==case['caret'] and get('se_h_current',4)==case['node'] and get('se_doc_generation',2)==case['generation']
        assert bool(get('se_sel_mark'))==case['marked'],(ident,'mark state')
        matrix=(folder/'matrix.bin').read_bytes();colors=(folder/'colors.bin').read_bytes();font=(folder/'font.bin').read_bytes()
        text=native_screen_text(matrix);(e/(ident+'-screen.txt')).write_text(text+'\n')
        if not case['ui']:
            oracle=source40(expected,get('se_v_top',3),case['caret'],marked=case['marked'],anchor=case['anchor'],pending=case['pending'],dirty=True)
            verify_screen(matrix,colors,oracle,tag='substantial native '+ident);screen_count+=1
            view=(folder/'view.bin').read_bytes();offset=s['se_v_rows']-0x8C00
            anchors=tuple(int.from_bytes(view[offset+3*i:offset+3*i+3],'little') for i in range(22))+(get('se_v_bottom',3),)
            assert anchors==oracle.anchors,(ident,'all22 starts and bottom')
            assert oracle.caret is not None,(ident,'caret not visible')
        else:assert 'Block' in text and 'Copy' in text and 'Paste' in text
        width,height,pixels=read_png(e/f'native-{ident}.png');assert(width,height)==(384,272);background=pixels[0]
        for row in range(25):
            for col in range(40):
                for y in range(8):
                    pattern=font[matrix[row*40+col]*8+y]
                    for x in range(8):
                        assert (pixels[(35+row*8+y)*width+32+col*8+x]!=background)==bool(pattern&(128>>x)),(ident,row,col,x,y)
                        pixels_checked+=1
        observations.append(dict(id=ident,source_bytes=len(expected),source_sha256=hashlib.sha256(expected).hexdigest(),caret=case['caret'],top=get('se_v_top',3),pending=case['pending'],generation=case['generation'],node=case['node']))
    final=images['final-top_reu'];boot=images['boot_reu'];seed=images['fixture_reu']
    append=fixture+clip+cut+bytes([0xD2])*96
    assert final[4*65536:4*65536+len(append)]==append,'append object exact complete write history'
    assert final[3*65536:4*65536]==boot[3*65536:4*65536],'original object immutable entire64KiB'
    assert final[6*65536:6*65536+len(cut)]==cut,'current cut clipboard bytes'
    assert final[6*65536+len(cut):7*65536]==seed[6*65536+len(cut):7*65536],'cut clipboard tail preserved'
    assert final[7*65536:7*65536+len(clip)]==clip,'released copy clipboard retains bytes'
    assert final[7*65536+len(clip):]==boot[7*65536+len(clip):],'unused final bank tail'
    assert final[:2*65536]==boot[:2*65536],'reserved and immutable overlay storage unchanged'
    assert final[4*65536+len(append):5*65536]==boot[4*65536+len(append):5*65536],'append tail untouched'
    def reference(identity,offset,length):return bytes([identity,1,0])+offset.to_bytes(3,'little')+length.to_bytes(3,'little')
    def record(before,after,pos,delete,insert,bcaret,acaret,removed,inserted,typing=False):
        body=b''.join(removed+inserted);length=66+len(body);body+=length.to_bytes(2,'little')
        h=bytearray(64);h[:6]=b'SEH1\x01'+bytes([int(typing)]);h[6:8]=length.to_bytes(2,'little');h[8:12]=before.to_bytes(4,'little');h[12:16]=after.to_bytes(4,'little');h[16:21]=bytes([1,1,0,1,0]);h[21:26]=bytes([2,1,0,1,0])
        for offset,value in [(26,pos),(29,delete),(32,insert),(39,bcaret),(42,acaret)]:h[offset:offset+3]=value.to_bytes(3,'little')
        h[35:37]=len(removed).to_bytes(2,'little');h[37:39]=len(inserted).to_bytes(2,'little');h[45]=int(typing)
        h[56:58]=binascii.crc_hqx(body,0xFFFF).to_bytes(2,'little');h[58:60]=binascii.crc_hqx(h[:58]+h[60:],0xFFFF).to_bytes(2,'little')
        return bytes(h)+body
    d=len(fixture);c=len(clip);p=len(cut)
    records=[record(1,2,0,len(sample),d,len(sample),d,[reference(1,0,len(sample))],[reference(2,0,d)]),record(2,3,d,0,c,d,d+c,[],[reference(2,d,c)]),record(3,4,0,p,0,p,0,[reference(2,0,p)],[]),record(4,5,0,0,p,0,p,[],[reference(2,d+c,p)]),record(5,6,56,0,96,56,152,[],[reference(2,d+c+p,96)],True)]
    journal=b''.join(records);(e/'expected-journal.bin').write_bytes(journal)
    assert final[5*65536:5*65536+len(journal)]==journal,'exact5 active journal records including CRC/carets/groups'
    stage=records[-1]+records[0][len(records[-1]):]
    assert final[5*65536+0xB000:5*65536+0xB000+len(stage)]==stage,'exact final stage and retained earlier-record tail'
    assert final[5*65536+len(journal):5*65536+0xB000]==boot[5*65536+len(journal):5*65536+0xB000],'unused journal log untouched'
    assert final[5*65536+0xB000+len(stage):6*65536]==boot[5*65536+0xB000+len(stage):6*65536],'unused stage tail untouched'
    assert final[2*65536+3*1024:3*65536]==boot[2*65536+3*1024:3*65536],'metadata pages outside three allocated leaf slots untouched'
    final_folder=artifacts/'stages/final-top_ram'
    assert field(final_folder,'se_h_end',2)==len(journal) and field(final_folder,'se_h_saved',4)==1
    assert field(final_folder,'se_clip_token',5)==int.from_bytes(bytes([4,2,0,1,0]),'little')
    assert field(final_folder,'se_clip_length',3)==len(cut) and field(final_folder,'se_clip_generation',2)==4
    # All REU bytes are either unchanged or inside these explicitly owned writes.
    owned=[(2*65536,3*1024),(4*65536,len(append)),(5*65536,len(journal)),(5*65536+0xB000,len(stage)),(6*65536,len(fixture)),(7*65536,len(clip))]
    offset=0
    for start,length in owned:
        assert final[offset:start]==boot[offset:start],('unowned REU bytes changed',hex(offset),hex(start))
        offset=start+length
    assert final[offset:]==boot[offset:],'unowned REU tail changed'
    untouched_reu_bytes=len(final)-sum(length for start,length in owned)
    for index,name in enumerate(catalog):
        payload=(e/(name+'.seo')).read_bytes()[HEADER:];assert final[65536+4096*index:65536+4096*index+len(payload)]==payload
    result=dict(status='passed',prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],overlay_sha256={name:hashlib.sha256((e/(name+'.seo')).read_bytes()).hexdigest() for name in catalog},asset_count=len(catalog),evidence=str(e),manifest=str(manifest),fixture_bytes=d,fixture_visual_rows=len(visual_rows(fixture)),final_source_bytes=d+c+96,clipboard_copy_bytes=c,clipboard_cut_bytes=p,native_input_bytes=keys,screenshots=len(cases),complete_screen_oracles=screen_count,native_glyph_pixels=pixels_checked,exact_journal_records=5,exact_journal_bytes=len(journal),exact_append_bytes=len(append),untouched_reu_bytes_checked=untouched_reu_bytes,metadata_leaf_pages_bounded=3,publication_context_checks=sum(bool(c.get('require_context')) for c in cases),shim_bytes_checked=1024,captures=observations,limitations='Fixture import uses real object-provider APIs via cold monitor probe; document edits then use native-byte KERNAL queue input, not physical keyboard chords or hardware autorepeat. Frozen exact build identity recorded above. Source40 only; markup remains literal. No full M3 completion claim.')
    (e/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--freeze':freeze()
    elif len(sys.argv)>1 and sys.argv[1]=='--prepare':main(Path(sys.argv[2]),prepare=True)
    elif len(sys.argv)>1 and sys.argv[1]=='--verify':
        e=Path(sys.argv[2]).resolve();r=json.loads((e/'editor-report.json').read_text());s=r['symbols']
        p=(e/'editor.prg').read_bytes();sample=p[2+s['sample']-0x801:2+s['sample_end']-0x801]
        cases=json.loads((e/'cases.json').read_text());fixture=(e/'fixture.petscii').read_bytes()
        page=next(c['caret'] for c in cases if c['id']=='page-down')
        restored=next(c['caret'] for c in cases if c['id']=='cut-restored')
        plan=json.loads((e/'plan.yaml').read_text());keys=sum(len(x['params']['keys']) for x in plan['steps'] if x['type']=='input.sequence' and x['id']!='boot')
        verify(e,r,s,sample,fixture,fixture[:page],fixture[:restored],cases,keys,e/'run',e/'run/manifest.json')
    else:main(Path(sys.argv[1]) if len(sys.argv)>1 else None)
