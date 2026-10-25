"""Native wrap/no-wrap/pan acceptance; complete independent logical-line oracle.

Run only after parent freezes CPU-verified production assets. Fixture import uses
actual TYPE5 provider APIs; every document/view operation then follows IRQ input.
"""
from bisect import bisect_right
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from redraw_model import Screen,source40,screen_code,native_text,verify_screen
from navigation_model import visual_rows
from png_pixels import read_png
from run_vice import native_screen_text
from vice_config import PROJECT,step
from vice_plan import run_plan
NAMES=('eedit','eplay','window','text40','menu40','engine','navigate','search','block','layout')


def line_starts(source):return [0]+[i+1 for i,v in enumerate(source) if v==13]
def line_end(source,start):
    end=source.find(b'\r',start)
    return len(source) if end<0 else end

def logical_move(source,caret,delta,preferred=None):
    starts=line_starts(source);index=bisect_right(starts,caret)-1
    if preferred is None:preferred=caret-starts[index]
    target=index+delta
    if target<0:return 0,preferred
    if target>=len(starts):return len(source),preferred
    start=starts[target];return start+min(preferred,line_end(source,start)-start),preferred


def logical_screen(source,top,caret,pan,*,marked=False,anchor=0,dirty=True):
    chrome=source40(source,top,caret,marked=marked,anchor=anchor,dirty=dirty)
    matrix=bytearray(chrome.matrix);colors=bytearray(chrome.colors)
    matrix[80:960]=bytes([32])*880;colors[80:960]=bytes([1])*880
    assert top==0 or source[top-1]==13,('top is not logical start',top)
    lo,hi=sorted((anchor,caret)) if marked else (caret,caret)
    pos=top;anchors=[];cell=None
    for row in range(22):
        anchors.append(pos);end=line_end(source,pos)
        for col in range(40):
            at=(row+2)*40+col;p=pos+pan+col
            if p>end:continue
            glyph=32 if p==end else screen_code(source[p]);color=1
            if lo<=p<hi:glyph^=128;color=3
            if p==caret and cell is None:
                glyph=(32 if p==end else screen_code(source[p]))^128
                color=7 if marked else 3;cell=(row,col)
            matrix[at]=glyph;colors[at]=color
        pos=end+1 if end<len(source) else len(source)
    anchors.append(pos)
    return Screen(bytes(matrix),bytes(colors),tuple(anchors),cell)


def freeze():
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    e=ROOT/'agentsworking/evidence/M3'/(stamp+'-layout-native');e.mkdir(parents=True)
    for name in ['editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json','supereditor.d81']:
        shutil.copyfile(ROOT/'build'/name,e/name)
    r=json.loads((e/'editor-report.json').read_text());assert hashlib.sha256((e/'editor.prg').read_bytes()).hexdigest()==r['sha256']
    for name in NAMES:
        data=(ROOT/f'build/overlays/{name}.seo').read_bytes();assert data[20:36]==data[36:52]==bytes.fromhex(r['resident_binding']['digest'])
        (e/(name+'.seo')).write_bytes(data)
    for name in ['tests/test_layout_vice.py','tools/redraw_model.py','tools/navigation_model.py','tools/png_pixels.py','tools/vice_config.py','tools/vice_plan.py']:
        out=e/'sources'/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,out)
    with zipfile.ZipFile(e/'product-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for directory in ['src','cfg']:
            for p in (ROOT/directory).rglob('*'):
                if p.is_file():z.write(p,p.relative_to(ROOT))
        z.write(ROOT/'Makefile','Makefile')
    (e/'freeze.json').write_text(json.dumps(dict(prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],disk_sha256=hashlib.sha256((e/'supereditor.d81').read_bytes()).hexdigest(),assets={n:hashlib.sha256((e/(n+'.seo')).read_bytes()).hexdigest() for n in NAMES}),indent=2)+'\n')
    print('FROZEN '+str(e),flush=True);return e


def fixture():
    rows=['# SuperEditor logical lines and soft wrap','Mixed CASE, code alignment and source positions.','','```ASM',
      'entry:  lda #$2a       ; '+('0123456789ABCDEF'*18),
      '        sta $d020     ; background color, trailing comment beyond screen edge',
      '', '        ldx #$00      ; begin an idiomatic C64 loop',
      'loop:   inx           ; **literal emphasis** and *italic* source',
      '        bne loop      ; long comment stays on this one logical line',
      '        rts','```','','```BASIC',
      '10 PRINT "Mixed Case":REM '+('ABCD 0123456789 '*12),
      '20 FOR I=1 TO 40:PRINT I:NEXT I','30 GOTO 10','```','',
      '- A bullet is editable source, without a rich-formatting claim.',
      '1. Numbered source text; CR bytes terminate logical lines.','']
    for i in range(35):
        rows += [f'## Heading {i+1:02d} Mixed Case',f'{i+1:02d} aligned: LDA #$01   STA $D020   RTS   ; '+('column '+str(i)+' ')*8]
        if i%4==0:rows.append('')
    source=native_text('\r'.join(rows))+b'\r'+native_text('Native controls/graphics: ')+bytes([0,1,9,31,0x80,0x9F,0xA0,0xB0,0xC0,0xFF])+b'\r'
    return source,rows


def main(e):
    assert not (e/'run').exists(),'Use --verify for an existing native run'
    r=json.loads((e/'editor-report.json').read_text());s=r['symbols'];source,rows=fixture()
    assert hashlib.sha256((e/'editor.prg').read_bytes()).hexdigest()==r['sha256']
    freeze_id=json.loads((e/'freeze.json').read_text());assert freeze_id['assets']=={n:hashlib.sha256((e/(n+'.seo')).read_bytes()).hexdigest() for n in NAMES}
    (e/'fixture.petscii').write_bytes(source);(e/'fixture-host.txt').write_text('\n'.join(rows)+'\nRaw native controls/graphics follow.\n')
    shutil.copyfile(e/'supereditor.d81',e/'working.d81')
    steps=[];cases=[];keys=0;caret=anchor=mode=0;marked=False
    canary=bytes((i*73+29)&255 for i in range(1024))
    def write(ident,name,value,width=1):
        at=s[name] if isinstance(name,str) else name;data=value if isinstance(value,bytes) else value.to_bytes(width,'little')
        steps.append(step(ident,'memory.write',start=at,bytes_hex=data.hex(' ')))
    def memory(ident,name,value,width=1):
        at=s[name] if isinstance(name,str) else name;data=value if isinstance(value,bytes) else value.to_bytes(width,'little')
        x=step(ident,'assert.memory',start=at,end=at+len(data)-1,equals_hex=data.hex(' '));x['retry']=dict(max_attempts=50,backoff_ms=40,jitter=False);steps.append(x)
    def raw(ident,commands):
        path=e/(ident+'.mon');path.write_text('\n'.join(commands)+'\n');steps.append(step(ident,'monitor.command',command=f'raw: playback "{path}"'))
    def api(ident,name,a=0,x=0,token=False):
        code=bytes([0x20])+s[name].to_bytes(2,'little')+bytes([0x8D,0xE0,0x0E,0xA9,0,0x69,0,0x8D,0xE1,0x0E])
        if token:code+=bytes([0xA2,4,0xBD])+s['se_object_id'].to_bytes(2,'little')+bytes([0x9D])+s['se_clip_token'].to_bytes(2,'little')+bytes([0xCA,0x10,0xF7])
        stop=0x0E00+len(code);code+=bytes([0xEA,0x4C])+s['se_idle'].to_bytes(2,'little')
        raw(ident,[f'> 0e00 {code.hex(" ")}',f'registers PC=$0e00, SP=$ff, FL=$20, A=${a:02x}, X=${x:02x}',f'until ${stop:04x}']);memory(ident+'_carry',0x0EE1,0)
    def idle(ident):
        for n in ['se_e_job','se_e_error','se_hot_pending','se_n_owned','se_doc_read_locks']:memory(ident+'_'+n,n,0)
        memory(ident+'_paint','se_e_redraw',bytes([0,0]))
    def send(ident,data):
        nonlocal keys
        steps.append(step(ident,'input.sequence',keys=list(data),inter_key_delay_s=0.005,post_delay_s=0.08));keys+=len(data)
        memory(ident+'_consumed','se_key_sequence',keys,2);idle(ident)
    def f7(ident,text):send(ident,bytes([0x88])+text.encode('ascii')+b'\r')
    def menu(ident,letter):send(ident,bytes([0x85,0x56,ord(letter)]))
    def capture(ident,ui=0,pan=None,hidden=False,preferred=None):
        cases.append(dict(id=ident,caret=caret,marked=marked,anchor=anchor,mode=mode,ui=ui,pan=pan,allow_hidden=hidden,preferred=preferred))
        memory(ident+'_caret','se_hot_caret',caret,3);memory(ident+'_mode','se_l_mode',mode);memory(ident+'_ui','se_e_ui',ui)
        if pan is not None:memory(ident+'_pan','se_l_pan',pan,3)
        if preferred is not None:memory(ident+'_preferred','se_l_preferred',preferred,3)
        for n,v,w in [('se_doc_length',len(source),3),('se_doc_generation',3,2),('se_h_current',2,4),('se_h_saved',1,4),('se_h_counter',2,4),('se_h_end',84,2),('se_h_cursor',84,2)]:memory(ident+'_'+n,n,v,w)
        steps.append(step(ident+'_native','monitor.command',command=f'raw: screenshot "{e}/native-{ident}.png" 2'))
        steps.append(step(ident+'_ram','dump.memory_ranges',ranges=[dict(label='state',start=0xC000,end=0xC5FF),dict(label='view',start=0x8C00,end=0x8CFF),dict(label='metadata',start=0x9A00,end=0x9FFF),dict(label='hot',start=0x9200,end=0x99FF),dict(label='matrix',start=0x4000,end=0x43E7),dict(label='font',start=0x4800,end=0x4FFF),dict(label='colors',start=0xD800,end=0xDBE7)]))
        steps.append(step(ident+'_reu','dump.reu',mode='full',stage_tag=ident+'_reu'))
    steps += [step('launch','vice.launch',kill_stale=False),step('basic','screen.wait_contains',text='READY.',wait_timeout_s=30)]
    raw('resources',['resourceset "MachineVideoStandard" "1"','resourceset "VICIIModel" "0"','resourceset "REU" "0"','resourceset "REUsize" "512"','resourceset "REU" "1"','warp','resourceget "Drive8TrueEmulation"'])
    write('shim_seed',0xC600,canary);steps.append(step('boot','input.sequence',keys=list(b'LOAD"SUPEREDITOR",8,1\rRUN\r'),inter_key_delay_s=0.04,post_delay_s=0.15));memory('ready','se_status',1);memory('drawn','se_e_draw_sequence',1,2);idle('boot')
    api('fixture_allocate','se_object_create',5,1,True);memory('fixture_token','se_clip_token',bytes([4,1,0,1,0]))
    for i,offset in enumerate(range(0,len(source),1024)):
        chunk=source[offset:offset+1024];write(f'fixture_{i}_host',0x8000,chunk);write(f'fixture_{i}_offset','se_object_offset',offset,3);write(f'fixture_{i}_length','se_object_length',len(chunk),2);write(f'fixture_{i}_ptr','se_object_c64',0x8000,2);api(f'fixture_{i}_stash','se_object_copy')
    write('fixture_size','se_object_offset',len(source),3);api('fixture_resize','se_object_resize');write('fixture_clip_length','se_clip_length',len(source),3);write('fixture_clip_gen','se_clip_generation',2,2);write('fixture_active','se_clip_active',1);api('fixture_validate','se_clip_validate')
    f7('select_top','TOP');send('mark_fixture',bytes([0x89]));f7('select_bottom','BOTTOM');send('paste_fixture',bytes([0x16]));f7('top','TOP');capture('wrap-top',pan=0)
    send('F4_nowrap',bytes([0x8A]));mode=1;capture('nowrap-top',pan=0)
    send('open_view_menu',bytes([0x85,0x56]));capture('view-menu',ui=1,pan=0);send('close_view_menu',bytes([3]))
    menu('menu_pan_right','R');capture('menu-right-hidden',pan=20,hidden=True)
    f7('f7_pan_right','PAN RIGHT');capture('f7-right40-hidden',pan=40,hidden=True)
    f7('f7_pan_left','PAN LEFT');menu('menu_pan_left','L');capture('pan-zero',pan=0)
    f7('goto_code','GOTO 5');caret=line_starts(source)[4]
    send('jump_long_code',bytes([0x0C])*3);caret+=120;capture('auto-pan-code',pan=81)
    preferred=None
    for tag,delta,key in [('down_short',1,0x11),('down_blank',1,0x11),('up_short',-1,0x91),('up_long',-1,0x91)]:
        send(tag,bytes([key]));caret,preferred=logical_move(source,caret,delta,preferred)
        if tag in ['down_blank','up_long']:capture(tag,preferred=120)
    send('selection_lower',bytes([0x11,0x11]));caret,_=logical_move(source,caret,2,120)
    send('mark_reverse',bytes([0x89]));marked=True;anchor=caret
    send('reverse_up_two',bytes([0x91,0x91]));caret,_=logical_move(source,caret,-2,0)
    # F2 resets preferred: from blank line caret has column0; reverse uses0.
    capture('reverse-selection')
    f7('selection_pan','PAN RIGHT');capture('selected-pan-hidden',hidden=True)
    send('F6_help',bytes([0x8B]));capture('help',ui=1,hidden=True)
    send('F6_restore',bytes([0x8B]));capture('help-restored',hidden=True)
    send('unmark',bytes([3]));marked=False
    send('right_reveal',bytes([0x1D]));caret+=1;capture('normal-nav-reveal')
    send('F4_wrap',bytes([0x8A]));mode=0;capture('F4-wrapped',pan=0)
    f7('f7_wrap_on','WRAP ON');capture('explicit-wrap-on',pan=0)
    f7('f7_wrap_off','WRAP OFF');mode=1;capture('explicit-wrap-off')
    f7('f7_wrap_toggle','WRAP');mode=0;capture('f7-wrap-toggle',pan=0)
    menu('menu_wrap_toggle','W');mode=1;capture('menu-wrap-toggle')
    f7('bottom','BOTTOM');caret=len(source);capture('nowrap-EOF',pan=0)
    send('logical_page_up',bytes([0x86]));caret,_=logical_move(source,caret,-21,0);capture('nowrap-page-up',preferred=0)
    f7('final_top','TOP');caret=0;f7('left_clamp','PAN LEFT');capture('pan-left-clamped',pan=0)
    send('final_F4_wrap',bytes([0x8A]));mode=0;capture('final-wrap',pan=0)
    memory('shim_intact',0xC600,canary);memory('channels_closed',0x98,0)
    plan=dict(version=1,kind='vice_task_plan',plan_id='supereditor-layout-'+e.name,run_mode='gui_vice',global_defaults=dict(monitor_host='127.0.0.1',monitor_port_start=6580,monitor_port_span=30,retry_policy=dict(max_attempts=1,backoff_ms=100,jitter=False),timeouts=dict(launch_s=30,step_s=60,read_s=2),artifact_policy=dict(capture_screen=False,capture_state=False,capture_dump=False),vice=dict(disk8=str(e/'working.d81'),drive8_type=1581,drive9_enabled=False,autostart_enabled=False,true_drive=False,close_vice=True,headless=True,speed_percent=100)),steps=steps)
    (e/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
    b=subprocess.run(['dotnet','build',str(PROJECT),'--no-restore','--nologo'],capture_output=True,text=True,timeout=120);assert b.returncode==0,b.stdout+b.stderr
    print(f'Prepared {len(source)} bytes/{len(line_starts(source))} logical lines/{keys} native keys/{len(steps)} steps at {e}',flush=True)
    artifacts,manifest=run_plan(plan,e);verify(e,artifacts,manifest)


def verify(e,artifacts,manifest):
    r=json.loads((e/'editor-report.json').read_text());s=r['symbols'];source=(e/'fixture.petscii').read_bytes();cases=json.loads((e/'cases.json').read_text())
    images={}
    for index in (artifacts/'dumps').glob('*.json'):
        for item in json.loads(index.read_text(encoding='utf-8-sig')).get('chunks',[]):
            if item.get('source')=='vice_native_reu_image':
                ident=index.name.removeprefix('reu_').removesuffix('_reu_index.json');images[ident]=(index.parent/Path(item['file']).name).read_bytes()
    baseline=images['wrap-top'];assert len(baseline)==512*1024
    observations=[];full_screens=pixels_checked=0;hidden_count=0
    def read_object(meta,image,identity,offset,length):
        output=bytearray()
        while length:
            n=min(length,65536-(offset&65535));bank=meta[s['object_extents']-0x9A00+identity*16+(offset>>16)]
            output+=image[bank*65536+(offset&65535):bank*65536+(offset&65535)+n];offset+=n;length-=n
        return bytes(output)
    def committed_source(folder,image):
        meta=(folder/'metadata.bin').read_bytes();count=meta[s['se_doc_root_count']-0x9A00];output=bytearray();start=s['se_doc_roots']-0x9A00
        for i in range(count):
            root=meta[start+i*8:start+(i+1)*8];leaf=read_object(meta,image,0,root[0]*1024,root[1]*16)
            for j in range(root[1]):
                piece=leaf[j*16:(j+1)*16];assert piece[0]==2 and piece[1:3]==b'\x01\x00'
                output+=read_object(meta,image,piece[0],int.from_bytes(piece[3:6],'little'),int.from_bytes(piece[6:9],'little'))
        return bytes(output)
    def get(folder,name,width=1):
        at=s[name]
        for label,start,end in [('state',0xC000,0xC600),('view',0x8C00,0x8D00),('metadata',0x9A00,0xA000)]:
            if start<=at and at+width<=end:return int.from_bytes((folder/(label+'.bin')).read_bytes()[at-start:at-start+width],'little')
        raise AssertionError(('uncaptured',name,hex(at)))
    for c in cases:
        ident=c['id'];folder=artifacts/'stages'/(ident+'_ram');field=lambda n,w=1:get(folder,n,w)
        assert images[ident]==baseline,(ident,'view-only operation modified REU')
        assert committed_source(folder,images[ident])==source,(ident,'full committed source changed')
        assert field('se_doc_length',3)==len(source) and field('se_doc_generation',2)==3 and not field('se_hot_pending')
        assert field('se_h_current',4)==2 and field('se_h_saved',4)==1 and field('se_h_end',2)==84 and field('se_h_cursor',2)==84
        assert field('se_hot_caret',3)==c['caret'] and bool(field('se_sel_mark'))==c['marked']
        assert field('se_l_mode')==c['mode'] and field('se_e_ui')==c['ui'] and not field('se_e_error')
        top=field('se_v_top',3);pan=field('se_l_pan',3)
        assert c['pan'] is None or pan==c['pan']
        if c['preferred'] is not None:assert field('se_l_preferred',3)==c['preferred']
        matrix=(folder/'matrix.bin').read_bytes();colors=(folder/'colors.bin').read_bytes();font=(folder/'font.bin').read_bytes();text=native_screen_text(matrix);(e/(ident+'-screen.txt')).write_text(text+'\n')
        if not c['ui']:
            if c['mode']:oracle=logical_screen(source,top,c['caret'],pan,marked=c['marked'],anchor=c['anchor'])
            else:
                assert top in {a for a,b in visual_rows(source)},(ident,'wrapped top not global visual start')
                oracle=source40(source,top,c['caret'],marked=c['marked'],anchor=c['anchor'],dirty=True)
            verify_screen(matrix,colors,oracle,tag='native-layout '+ident);full_screens+=1
            view=(folder/'view.bin').read_bytes();start=s['se_v_rows']-0x8C00
            anchors=tuple(int.from_bytes(view[start+i*3:start+i*3+3],'little') for i in range(22))+(field('se_v_bottom',3),)
            assert anchors==oracle.anchors,(ident,'all23 anchors')
            if oracle.caret is None:
                assert c['allow_hidden'] and field('se_l_manual') and not field('se_v_seen'),(ident,'unexpected hidden caret');hidden_count+=1
            else:assert field('se_v_seen') and (field('se_v_caret_row'),field('se_v_caret_col'))==oracle.caret
        elif ident=='view-menu':assert 'Toggle soft wrap' in text and 'Pan left 20 columns' in text and 'Pan right 20 columns' in text
        else:assert 'SuperEditor keyboard' in text and 'F4' in text
        w,h,pixels=read_png(e/f'native-{ident}.png');assert(w,h)==(384,272);bg=pixels[0]
        for row in range(25):
            for col in range(40):
                for y in range(8):
                    pattern=font[matrix[row*40+col]*8+y]
                    for x in range(8):
                        assert (pixels[(35+row*8+y)*w+32+col*8+x]!=bg)==bool(pattern&(128>>x)),(ident,row,col,x,y)
                        pixels_checked+=1
        observations.append(dict(id=ident,mode=c['mode'],caret=c['caret'],top=top,pan=pan,manual=field('se_l_manual'),marked=c['marked'],ui=c['ui']))
    # Independently reconstruct source through catalog mappings and active leaves.
    folder=artifacts/'stages/wrap-top_ram';meta=(folder/'metadata.bin').read_bytes()
    def obj(identity,offset,length):
        result=bytearray()
        while length:
            n=min(length,65536-(offset&65535));bank=meta[s['object_extents']-0x9A00+16*identity+(offset>>16)]
            result+=baseline[bank*65536+(offset&65535):bank*65536+(offset&65535)+n];offset+=n;length-=n
        return bytes(result)
    rebuilt=bytearray();start=s['se_doc_roots']-0x9A00
    for i in range(get(folder,'se_doc_root_count')):
        root=meta[start+i*8:start+(i+1)*8];leaf=obj(0,root[0]*1024,root[1]*16)
        for j in range(root[1]):
            p=leaf[j*16:(j+1)*16];assert p[0]==2 and p[1:3]==b'\x01\x00';rebuilt+=obj(p[0],int.from_bytes(p[3:6],'little'),int.from_bytes(p[6:9],'little'))
    assert rebuilt==source and obj(2,0,len(source))==source and obj(4,0,len(source))==source
    prg=(e/'editor.prg').read_bytes();sample=prg[2+s['sample']-0x801:2+s['sample_end']-0x801];assert obj(1,0,len(sample))==sample
    for i,name in enumerate(NAMES):
        payload=(e/(name+'.seo')).read_bytes()[36:];assert baseline[65536+4096*i:65536+4096*i+len(payload)]==payload,(name,'stored catalog payload')
    keys=sum(len(x['params']['keys']) for x in json.loads((e/'plan.yaml').read_text())['steps'] if x['type']=='input.sequence' and x['id']!='boot')
    result=dict(status='passed',evidence=str(e),manifest=str(manifest),prg_sha256=r['sha256'],resident_binding=r['resident_binding']['digest'],asset_sha256={n:hashlib.sha256((e/(n+'.seo')).read_bytes()).hexdigest() for n in NAMES},asset_catalog={n:dict(slot=(e/(n+'.seo')).read_bytes()[5],module_id=(e/(n+'.seo')).read_bytes()[6],payload_bytes=int.from_bytes((e/(n+'.seo')).read_bytes()[8:10],'little')) for n in NAMES},fixture_bytes=len(source),fixture_logical_lines=len(line_starts(source)),native_input_bytes=keys,screenshots=len(cases),complete_screens=full_screens,native_glyph_pixels=pixels_checked,manual_hidden_caret_screens=hidden_count,full_reu_bytes_preserved_per_view=512*1024,reu_comparisons=len(cases),shim_bytes_checked=1024,source_sha256=hashlib.sha256(source).hexdigest(),captures=observations,limitations='Real ROM/D81 and IRQ-native KERNAL queue input; not physical chord/autorepeat proof. TYPE5 fixture import is monitor-assisted before UI document paste. Source40 only; literal SuperMark remains source. View-only invariance follows a committed fixture paste; pending-input flushing tested separately by CPU suite.')
    (e/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--freeze':freeze()
    elif len(sys.argv)>1 and sys.argv[1]=='--verify':
        e=Path(sys.argv[2]).resolve();verify(e,e/'run',e/'run/manifest.json')
    else:main(Path(sys.argv[1]).resolve() if len(sys.argv)>1 else freeze())
