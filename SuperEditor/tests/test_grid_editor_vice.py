"""Native actual40/60/80 editor acceptance; safe --describe/--model-check first.

--freeze/--run are only for parent's explicitly stable production/VICE window.
No editor build, debugger source replacement, physical keyboard claim or global
VICE config writes. Private monitor7500/text7600..7639, owned disk/PID/output.
"""
from datetime import datetime,timezone
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from bindings import verify as verify_binding
from d81_image import D81Image
from redraw_model import native_text,screen_code,source40
from png_pixels import read_png
from vice_config import PROJECT,step
from vice_plan import run_plan
from test_editor_file_vice import NativePlan
from test_style_editor import semantic_plan
from supermark_model import blocks,inline,lex
WIDE_PALETTE=[1,3,7,10,14,1,1,7,13,5,15,7,3,1]
from test_narrow_rows import oracle as narrow_oracle
NAMES=['eedit','eplay','window','text40','menu40','engine','navigate','search','block','layout','fileio','aux','styler','viewsource','lexical','gridedit','grid80','grid60']
REU_BYTES=16*1024*1024


def fixture():
    data=native_text('# SuperEditor: diverse source\rMixed Case and PETSCII @ £ arrows.\r\r## Notes and ideas\r**Strong words** and *emphasis*.\rInline @@lda #$01@@ stays native.\r\r- First bullet\r- Second bullet\r1. Numbered item\r2. Another item\r\r:::basic\r10 PRINT "Hello, C64!"\r20 FOR I=1 TO 5:PRINT I:NEXT\r30 GOTO 10\r:::\r\r:::asm\rstart: lda #$00\r       sta $d020 ; border\r       rts\r:::\r\r:::region Details\rExpandable region, source preserved.\r:::end\r')
    data=data.replace(bytes([0xA3]),b'\\');assert len(data)==422;return data


def anchors(data,top,width):
    rows=[top]
    for _ in range(22):
        p=rows[-1]
        for _ in range(width):
            if p==len(data):break
            value=data[p];p+=1
            if value==13:break
        rows.append(p)
    return tuple(rows)


class UI:
    """Independent physical40-column chrome/ReadyOS popup cell specification."""
    def __init__(self,base):self.matrix=bytearray(base.matrix);self.colors=bytearray(base.colors);self.cells={(r,c) for r in [0,1,24] for c in range(40)}
    def put(self,row,col,text,color=None,inverse=False,raw=False):
        values=text if raw else bytes(screen_code(v) for v in native_text(text))
        assert all(v==32 for v in values[40-col:]),'visible UI text exceeds physical40 columns'
        values=values[:40-col]
        for n,value in enumerate(values):
            at=row*40+col+n;self.matrix[at]=value^(128 if inverse else 0)
            if color is not None:self.colors[at]=color
    def box(self,x,y,w,h):
        for row in range(y,y+h):
            for col in range(x,x+w):
                top,bottom,left,right=row==y,row==y+h-1,col==x,col==x+w-1
                code=0x70 if top and left else 0x6E if top and right else 0x6D if bottom and left else 0x7D if bottom and right else 0x40 if top or bottom else 0x5D if left or right else 32
                self.put(row,col,bytes([code]),14 if top or bottom or left or right else 1,raw=True);self.cells.add((row,col))
    def file_menu(self):
        self.box(1,3,35,5)
        for i,label in enumerate(['O  Open...       CTRL-O','S  Save          CTRL-S','A  Save as...']):self.put(4+i,3,label,3 if i==0 else 1,inverse=i==0)
    def help(self,template=None,cache=False):
        self.box(1,3,38,16)
        for row,label in [(4,'SuperEditor keyboard'),(6,'Type / Return / DEL / cursors'),(7,'F1 menus / F6 keyboard help'),(8,'F3/F5 pages; F4 wrap; arrows move'),(10,'CTRL-Z undo / CTRL-Y redo'),(11,'HOME/CTRL-E line; F2 mark/unmark'),(12,'CTRL-C/K copy CTRL-X/V cut/paste'),(14,'F7 top/bottom/diag; Help-D diag'),(15,'F8/CTRL-F8 modes; F7 wrap/pan' if cache else 'F7: wrap on/off, pan left/right'),(17,'F6 or RUN/STOP closes help')]:self.put(row,3,label)
    def file_dialog(self,device,name,listing,index=0,help=False):
        self.box(1,4,38,19);self.put(5,3,'Open a PETSCII document')
        self.colors[5*40+3:5*40+38]=bytes([7])*35
        self.put(6,3,'Device:');self.put(6,10,str(device));self.put(7,3,'Name:')
        self.put(7,10,bytes(screen_code(v) for v in name),3,raw=True);self.put(7,10+len(name),b'\xA0',3,raw=True)
        if help:
            for row,label in [(10,'Type up to 16 PETSCII characters.'),(12,'RETURN accepts the name.'),(14,'F3 drive F5 page DEL erase'),(16,'STOP cancels; F6 help.'),(18,'S Save   D Discard   C Cancel')]:self.put(row,3,label)
        else:
            for i,value in enumerate(listing):self.put(9+i,4,bytes(screen_code(v) for v in value),3 if i==index else 1,inverse=i==index,raw=True)
            self.put(18,3,'UP/DOWN choose; RETURN accepts');self.put(19,3,'F3 drive 8/9  F5 page')
        self.put(24,0,' File dialog       F6 Help   STOP Back   ')


def paint_native(bits,attrs,ui,font):
    for row,col in ui.cells:
        at=row*40+col;code=ui.matrix[at];bits[row*320+col*8:row*320+col*8+8]=bytes(v^(255 if code&128 else 0) for v in font[(code&127)*8:(code&127)*8+8]);attrs[at]=((ui.colors[at]&15)<<4)|6


def wide_semantics(source,rows,width):
    """Whole-source independent parser/lexer spans projected onto wider rows."""
    styles=bytearray(len(source))
    for event in blocks(source):
        kind=event['kind'];a,b=event['start'],event['end'];base=0x82 if kind==2 else 4 if kind==5 else 10 if kind in (4,6,7,8) else 0
        styles[a:b]=bytes([base])*(b-a)
        if kind==5:
            for start,end,role in lex(source[event['body']:b],event['language'],start=event['body']):styles[start:end]=bytes([{7:7,8:8,9:9,10:10,11:7,12:12,13:0}[role]])*(end-start)
        if kind in (4,5,6):continue
        origin=event['body']
        for token,style,delimiter,start,end in inline(source[origin:b],origin,body_column=(origin-a) or None):
            if token!=1:continue
            for pos in range(start+delimiter,end):
                mask=(styles[pos]&0xF0)|(style<<4);styles[pos]=mask|(4 if mask&64 else [0,1,2,3][(mask>>4)&3])
    plan=bytearray(width*22)
    for row,(a,b) in enumerate(zip(rows,rows[1:])):
        for col in range(width):
            pos=a+col
            if pos<min(b,len(source)) and source[pos]!=13:plan[row*width+col]=styles[pos]
    return bytes(plan)


def role_for(style):
    return style&15


def body_model(data,top,caret,width,mark,anchor,font,plan=None):
    rows=anchors(data,top,width);bits=bytearray(8000);attrs=bytearray([0x16])*1000;seen=False;lo,hi=sorted((caret,anchor)) if mark else (0,0)
    for row,(start,stop) in enumerate(zip(rows,rows[1:])):
        end=stop-1 if stop>start and data[stop-1]==13 else stop;chars=[];flags=[];roles=[]
        for col in range(width):
            p=start+col;chars.append(data[p] if p<end else 32);style=plan[row*width+col] if plan is not None and p<end else 0;roles.append(role_for(style));flag=1 if style&128 else 0
            if p<=end:
                if mark and lo<=p<hi:flag|=2
                if p==caret and not seen:flag|=4;seen=True
            flags.append(flag)
        b,a=narrow_oracle(width,chars,roles,flags,WIDE_PALETTE if plan is not None else [1]*14,6,0,font);bits[(row+2)*320:(row+3)*320]=b;attrs[(row+2)*40:(row+3)*40]=a
    return bits,attrs,rows


def freeze(build,product_sources,wide_colors=False,capture_smoke=False):
    build=Path(build);product_sources=Path(product_sources);assert product_sources.is_file(),'Exact immutable product source ZIP is required'
    r=json.loads((build/'editor-report.json').read_text());s=r['symbols'];seal=verify_binding(build/'editor.prg',build/'editor.lbl');assert seal['resident_sha256']==r['sha256'] and seal['digest']==r['resident_binding']['digest']
    for name in ['se_mode','se_v_columns','se_n_view_columns','se_overlay_asset_second','se_f_owner']:assert name in s,name
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');e=ROOT/'agentsworking/evidence/M6'/(stamp+'-grid-editor-native');e.mkdir(parents=True)
    for name in ['editor.prg','editor-report.json','editor-bindings.json','editor.map','editor.lbl','disk-manifest.json','supereditor.d81']:shutil.copy2(build/name,e/name)
    disk=D81Image((e/'supereditor.d81').read_bytes());assert disk.read(b'SUPEREDITOR',kind=2).data==(e/'editor.prg').read_bytes()
    for name in NAMES:
        path=build/'overlays'/(name+'.seo');data=path.read_bytes();assert data[20:36]==data[36:52]==bytes.fromhex(seal['digest']);assert disk.read(name.upper().encode(),kind=1).data==data,name;shutil.copy2(path,e/path.name)
    shutil.copy2(product_sources,e/'product-sources.zip');shutil.copy2(__file__,e/'test_grid_editor_vice.py')
    (e/'freeze.json').write_text(json.dumps(dict(prg_sha256=r['sha256'],resident_binding=seal['digest'],catalog=NAMES,wide_colors=wide_colors,row_cache='se_gc_handle' in s,capture_smoke=capture_smoke,product_sources_sha256=hashlib.sha256(product_sources.read_bytes()).hexdigest(),disk_sha256=hashlib.sha256((e/'supereditor.d81').read_bytes()).hexdigest(),asset_sha256={n:hashlib.sha256((e/(n+'.seo')).read_bytes()).hexdigest() for n in NAMES}),indent=2)+'\n');print('FROZEN',e);return e


def package(e):
    (e/'diverse.bin').write_bytes(fixture());shutil.copy2(e/'supereditor.d81',e/'working.d81');p=subprocess.run(['c1541','-attach',str(e/'working.d81'),'-write',str(e/'diverse.bin'),'diverse,s'],capture_output=True,text=True);(e/'package.stdout').write_text(p.stdout);(e/'package.stderr').write_text(p.stderr);assert p.returncode==0,p.stdout+p.stderr
    assert D81Image((e/'working.d81').read_bytes()).read(b'DIVERSE',kind=1).data==fixture();shutil.copy2(e/'working.d81',e/'initial-fixtures.d81')


class GridPlan(NativePlan):
    def __init__(self,e,report):
        super().__init__(e,'editing',report);self.mode=0;self.mode_serial=0;self.wide_colors=json.loads((e/'freeze.json').read_text()).get('wide_colors',False)
        prg=(e/'editor.prg').read_bytes();load=int.from_bytes(prg[:2],'little');le=lambda n:self.s[n].to_bytes(2,'little')
        pattern=b'\xAD'+le('se_e_redraw')+b'\xF0\x06\x20'+le('se_editor_render')+b'\x4C'+le('se_idle')+b'\xAD'+le('se_e_ui')
        at=prg.find(pattern);assert at>=2 and prg.find(pattern,at+1)<0,'unrecognized actual idle boundary'
        self.idle_pc=load+at-2+11
        self.row_cache=json.loads((e/'freeze.json').read_text()).get('row_cache',False)
    def idle(self,ident,ui=0,error=0,owner=None):
        super().idle(ident,ui,error,owner)
        self.memory(ident+'_atomic_draw','se_e_redraw',b'\0\0')
    def boot(self):
        super().boot();resource=self.out/'resources.mon';text=resource.read_text().replace('"REUsize" "1024"','"REUsize" "16384"');resource.write_text(text)
    def typed(self,ident,text):self.send(ident,bytes([0x88])+native_text(text)+b'\r')
    def mode_to(self,mode):
        self.mode_serial+=1;tag='mode_'+str(mode)+'_'+str(self.mode_serial);self.typed(tag,'mode '+str([40,60,80][mode]));self.mode=mode;self.memory(tag+'_published','se_mode',mode);self.memory(tag+'_width','se_v_columns',[0,60,80][mode])
    def capture_grid(self,ident,source,*,ui=0,variant='body',caret=0,mark=False,clipboard=None,stable=None,dirty=False):
        if (self.mode==0 or self.wide_colors) and ui==0:
            for n,v in [('se_st_valid',1),('se_st_request',0),('se_f_owner',0)]:self.memory(ident+'_'+n,n,v)
        self.cases.append(dict(id=ident,source=source.hex(),ui=ui,dirty=dirty,current='DIVERSE',caret=caret,mode=self.mode,variant=variant,mark=mark,clipboard=clipboard.hex() if clipboard is not None else None,stable=stable))
        self.memory(ident+'_mode','se_mode',self.mode);self.memory(ident+'_columns','se_v_columns',[0,60,80][self.mode]);self.memory(ident+'_length','se_doc_length',len(source),3);self.memory(ident+'_pending','se_hot_pending',0)
        # All three observations share one stopped monitor session. Running to
        # this real foreground boundary completes dispatch, queued work and
        # drawing; genuine instruction stepping gives VIC complete freshframes.
        captures=self.out/'captures';captures.mkdir(exist_ok=True)
        if self.row_cache:
            # A body-idle PC may still own optional background style work.
            # Both stops test the SAME atomic state, resuming the real scheduler
            # until ready; the intervening genuine instructions refresh VIC.
            # Checkpoints are local to this owned emulator and are removed before
            # stepping/capture. No source/register/PC state is written.
            expected=[('se_e_ui',ui),('se_e_job',0),('se_e_redraw',0),('se_e_draw_busy',0),('se_doc_read_locks',0),('se_n_owned',0),('se_st_valid',1),('se_st_request',0),('se_f_owner',1 if ui==3 else 0),('se_input_nmi_pending',0)]
            condition=' && '.join(f'(@cpu:${self.s[k]:04x} == ${v:02x})' for k,v in expected)
            condition+=f' && (@cpu:${self.s["se_input_head"]:04x} == @cpu:${self.s["se_input_tail"]:04x}) && (@cpu:$00c6 == $00)'
            stop=[f'break exec ${self.idle_pc:04x} if {condition}','x','delete']
            commands=['delete',*stop,'step $10000',*stop]
        else:commands=[f'until ${self.idle_pc:04x}','step $10000',f'until ${self.idle_pc:04x}']
        self.raw(ident+'_coherent',commands+[f'screenshot "{self.out}/native-{ident}.png" 2',f'bsave "{captures}/{ident}-ram.bin" 0 $0000 $cfff',f'bsave "{captures}/{ident}-colors.bin" 0 $d800 $dbe7'])
        self.steps.append(step(ident+'_reu','dump.reu',mode='full',stage_tag=ident+'_reu'))
    def plan(self):
        p=super().plan();p['global_defaults']['monitor_port_start']=7500;p['global_defaults']['monitor_port_span']=1;return p


def scenario(e,report):
    n=GridPlan(e,report);data=fixture();n.boot();n.open('open_diverse',b'DIVERSE');n.memory('open422','se_doc_length',422,3)
    if json.loads((e/'freeze.json').read_text()).get('capture_smoke',False):
        n.mode_to(2);n.capture_grid('body80',data);n.send('select5',b'\x89'+bytes([0x1D])*5);n.typed('copy','copy');n.send('unmark',b'\x03');n.typed('bottom','bottom');n.typed('paste','paste');n.capture_grid('pasted80',data+data[:5],caret=427,clipboard=data[:5],dirty=True);return n
    if n.wide_colors:
        n.mode_to(2);n.capture_grid('early_color80',data)
        if n.row_cache:
            n.typed('early_warm_top80','top');n.capture_grid('warm80',data,stable='warm80')
            n.typed('warm_top80_again','top');n.capture_grid('warm80_again',data,stable='warm80')
        n.mode_to(0)
    for mode in [0,1,2]:
        if mode:n.mode_to(mode)
        tag=str([40,60,80][mode]);n.capture_grid('body'+tag,data)
        if n.row_cache and mode:
            n.typed('warm_top'+tag,'top');n.capture_grid('warm'+tag+'_mode',data)
        n.send('filemenu'+tag,bytes([0x85,0x46]),ui=1);n.capture_grid('filemenu'+tag,data,ui=1,variant='file-menu')
        n.send('menuclose'+tag,b'\x03');n.send('help'+tag,b'\x8B',ui=1);n.capture_grid('help'+tag,data,ui=1,variant='help');n.send('helpclose'+tag,b'\x8B')
        n.modal('dialog'+tag,'O');n.capture_grid('dialog'+tag,data,ui=3,variant='file-dialog');n.send('dialogcancel'+tag,b'\x03')
        n.send('selection'+tag,b'\x89'+bytes([0x1D])*5);n.capture_grid('selection'+tag,data,caret=5,mark=True)
        if mode<2:n.send('unmark'+tag,b'\x03');n.typed('top'+tag,'top')
    clip=data[:5];n.typed('copy','copy');n.capture_grid('copied80',data,caret=5,mark=True,clipboard=clip)
    n.send('unmark80',b'\x03');n.typed('bottom','bottom');n.typed('paste','paste');n.capture_grid('pasted80',data+clip,caret=len(data)+5,clipboard=clip,dirty=True)
    n.typed('undo','undo');n.capture_grid('undo80',data,caret=len(data),clipboard=clip)
    n.typed('top_after_undo','top');n.capture_grid('cycle_base80',data,clipboard=clip,stable='cycle')
    for mode in [0,1,2]:
        n.send('F8_'+str(mode),b'\x8C');n.mode=mode;n.capture_grid('F8_mode'+str([40,60,80][mode]),data,clipboard=clip,stable='cycle')
    # Save via actual80-column FileUI after source/undo/mode roundtrip. No fake
    # bytes are injected into product source, history or clipboard frames.
    n.save_as('save_after_modes',b'GRIDOUT');n.capture_grid('saved80',data,clipboard=clip);n.cases[-1]['current']='GRIDOUT'
    return n


def reu_images(artifacts):
    result={}
    for index in (artifacts/'dumps').glob('*.json'):
        for c in json.loads(index.read_text(encoding='utf-8-sig')).get('chunks',[]):
            if c.get('source')=='vice_native_reu_image':result[index.name.removeprefix('reu_').removesuffix('_reu_index.json')]=(index.parent/Path(c['file']).name).read_bytes()
    return result


def cache_reu_hash(reu,ram,s,enabled):
    if not enabled:return hashlib.sha256(reu).hexdigest()
    handle=ram[s['se_gc_handle']];assert handle,'missing declared cache allocation'
    physical=ram[s['se_reu_map']+handle]
    assert physical and ram[s['se_reu_logical_owner']+handle]==ram[s['se_reu_physical_owner']+physical]==0xFE
    # Only5280 derived packet bytes may differ. The rest of this owned64KiB
    # bank, every foreign/source/history/clip/catalog bank remain exact.
    at=physical*65536
    return hashlib.sha256(reu[:at]+bytes(5280)+reu[at+5280:]).hexdigest()


def verify_cache(case,data,top,caret,anchor,plan,ram,reu,s):
    def get(n,w=1):return int.from_bytes(ram[s[n]:s[n]+w],'little')
    h=get('se_gc_handle');ph=ram[s['se_reu_map']+h];assert h and ph
    assert ram[s['se_reu_logical_owner']+h]==ram[s['se_reu_physical_owner']+ph]==0xFE,(case['id'],'cache owner')
    assert get('se_gc_epoch',2)==get('se_reu_epoch',2) and not get('se_reu_retired'),(case['id'],'cache epoch')
    assert sum(v==0xFE for v in ram[s['se_reu_logical_owner']:s['se_reu_logical_owner']+256])==1
    assert sum(v==0xFE for v in ram[s['se_reu_physical_owner']:s['se_reu_physical_owner']+256])==1
    valid=get('se_gc_valid',3);record=dict(handle=h,physical=ph,epoch=get('se_gc_epoch',2),width=get('se_gc_width'),valid=valid,previous_ui=get('se_gc_previous_ui'),current_ui=get('se_gc_current_ui'),payload_sha256=hashlib.sha256(reu[ph*65536:ph*65536+5280]).hexdigest())
    if not case['mode']:
        assert valid==0,(case['id'],'40mode must invalidate narrow output')
        return record
    width=[40,60,80][case['mode']];assert get('se_gc_width')==width and valid==0x3FFFFF,(case['id'],'incomplete cache publication')
    popup=int(case['ui'] in [1,3]);assert get('se_gc_previous_ui')==get('se_gc_current_ui')==popup,(case['id'],'UI publication')
    rows=anchors(data,top,width);seen=False;lo,hi=sorted((caret,anchor)) if case['mark'] else (0,0)
    for row,(start,stop) in enumerate(zip(rows,rows[1:])):
        end=stop-1 if stop>start and data[stop-1]==13 else stop;chars=[];flags=[];roles=[]
        for col in range(width):
            pos=start+col;chars.append(data[pos] if pos<end else 32);style=plan[row*width+col] if plan is not None and pos<end else 0;roles.append(role_for(style));flag=1 if style&128 else 0
            if pos<=end:
                if case['mark'] and lo<=pos<hi:flag|=2
                if pos==caret and not seen:flag|=4;seen=True
            flags.append(flag)
        actual=reu[ph*65536+row*240:ph*65536+(row+1)*240]
        for offset,values in [(0,chars),(80,roles),(160,flags)]:
            assert actual[offset:offset+width]==bytes(values),(case['id'],'cache exact active packet',row,offset)
        # In60mode twenty unused bytes in each80Barray are inert. The renderer
        # leaves them unchanged across rows; compare against final live packet
        # suffix and require all cached rows to agree, without assigning them
        # semantic meaning or allowing any extra REU range to change.
        for offset in [0,80,160]:
            if width==60:assert actual[offset+60:offset+80]==ram[0x88C4+offset+60:0x88C4+offset+80],(case['id'],'unused60 cache suffix')
    return record


def evaluate(n,artifacts,manifest):
    images=reu_images(artifacts);freeze_record=json.loads((n.e/'freeze.json').read_text());wide_colors=freeze_record.get('wide_colors',False);row_cache=freeze_record.get('row_cache',False);capture_smoke=freeze_record.get('capture_smoke',False);catalog=freeze_record['catalog'];directory=[x.name for x in D81Image((n.e/'initial-fixtures.d81').read_bytes()).entries() if x.kind==1][:8];palette={};help_template=None;stable={};tail=None;rows_checked=pixels_checked=semantic_cells=0;observed=[]
    native=(n.e/'grid80.seo').read_bytes()[36+0xC00:36+0x1000];assert len(native)==1024
    for c in n.cases:
        ident=c['id'];folder=artifacts/'stages'/(ident+'_ram');coherent=n.out/'captures';ram=(coherent/(ident+'-ram.bin')).read_bytes() if (coherent/(ident+'-ram.bin')).exists() else (folder/'ram.bin').read_bytes();colors=(coherent/(ident+'-colors.bin')).read_bytes() if (coherent/(ident+'-colors.bin')).exists() else (folder/'colors.bin').read_bytes();reu=images[ident];assert len(ram)==0xD000 and len(reu)==REU_BYTES
        def get(name,width=1):return int.from_bytes(ram[n.s[name]:n.s[name]+width],'little')
        def obj(identity,offset,length):
            out=bytearray()
            while length:
                count=min(length,65536-(offset&65535));handle=ram[n.s['object_extents']+identity*16+(offset>>16)];physical=ram[n.s['se_reu_map']+handle];at=physical*65536+(offset&65535);out+=reu[at:at+count];offset+=count;length-=count
            return bytes(out)
        source=bytearray();metadata=get('se_doc_meta')
        for i in range(get('se_doc_root_count')):
            root=ram[n.s['se_doc_roots']+i*8:n.s['se_doc_roots']+(i+1)*8];leaf=obj(metadata,root[0]*1024,root[1]*16)
            for j in range(root[1]):
                piece=leaf[j*16:(j+1)*16];identity=piece[0];generation=int.from_bytes(piece[1:3],'little');assert generation==ram[n.s['object_gen_lo']+identity]+256*ram[n.s['object_gen_hi']+identity];source+=obj(identity,int.from_bytes(piece[3:6],'little'),int.from_bytes(piece[6:9],'little'))
        expected=bytes.fromhex(c['source']);assert source==expected and len(source)==get('se_doc_length',3),(ident,'byteexact canonical source');assert not get('se_hot_pending')
        assert get('se_mode')==c['mode'] and get('se_v_columns')==[0,60,80][c['mode']] and get('se_hot_caret',3)==c['caret'] and get('se_sel_mark')==int(c['mark'])
        assert ram[0xC600:0xCA00]==n.canary and get('se_doc_read_locks')==get('se_n_owned')==get('se_e_job')==0,(ident,'shim or source/nav/job notquiescent')
        if row_cache:assert get('se_st_valid')==1 and get('se_st_request')==0 and get('se_f_owner')==(1 if c['ui']==3 else 0) and get('se_input_head')==get('se_input_tail') and not get('se_input_nmi_pending') and ram[0xC6]==0,(ident,'atomic style/input capture guard')
        assert get('se_e_draw_busy')==get('se_e_redraw')==0,(ident,'torn capture')
        assert get('se_e_ui')==c['ui'] and get('se_h_dirty')==int(c['dirty'])
        if c['clipboard'] is not None:
            clip=bytes.fromhex(c['clipboard']);token=ram[n.s['se_clip_token']:n.s['se_clip_token']+5];identity=token[0];assert ram[n.s['object_owner']+identity]==5;assert token[1:3]==bytes([ram[n.s['object_gen_lo']+identity],ram[n.s['object_gen_hi']+identity]]) and token[3:5]==ram[n.s['se_doc_epoch']:n.s['se_doc_epoch']+2]
            assert get('se_clip_active') and get('se_clip_length',3)==len(clip);assert obj(identity,0,len(clip))==clip
        else:assert not get('se_clip_active'),(ident,'unexpected clipboard before firstcopy')
        assert (get('se_h_current',4)!=get('se_h_saved',4))==bool(c['dirty']),(ident,'history/savepoint mismatch')
        if ident=='undo80':assert get('se_h_cursor',2)<get('se_h_end',2),'undo must retain redo record'
        if c['current'] is not None:
            current=c['current'].encode();assert get('se_f_current_len')==len(current) and ram[n.s['se_f_current_name']:n.s['se_f_current_name']+len(current)]==current
        for i,name in enumerate(catalog):
            handle=get('se_overlay_asset' if i<16 else 'se_overlay_asset_second');physical=ram[n.s['se_reu_map']+handle];at=physical*65536+(i%16)*4096;payload=(n.e/(name+'.seo')).read_bytes()[36:];assert reu[at:at+len(payload)]==payload,(ident,'catalog bytes',name)
        actual_tail=ram[0x7F40:0x8000]
        if tail is None:tail=actual_tail
        assert actual_tail==tail,(ident,'192-byte catalog tail')
        if c['stable']:
            history={name:ram[n.s[name]:n.s[name]+width].hex() for name,width in [('se_h_current',4),('se_h_saved',4),('se_h_end',2),('se_h_cursor',2),('se_h_counter',4)]};canonical={name:ram[n.s[name]:n.s[name]+width].hex() for name,width in [('se_doc_meta',5),('se_doc_original',5),('se_doc_append',5),('se_doc_generation',2),('se_doc_root_count',1),('se_doc_roots',256),('se_clip_token',5),('se_clip_length',3),('se_clip_epoch',2),('se_h_token',5)]};snapshot=dict(history=history,canonical=canonical,reu_sha256=cache_reu_hash(reu,ram,n.s,row_cache),source=expected.hex(),clipboard=c['clipboard'])
            if c['stable'] not in stable:stable[c['stable']]=snapshot
            assert snapshot==stable[c['stable']],(ident,'mode changed source/history/REU/clipboard')
        top=get('se_v_top',3);caret=get('se_hot_caret',3);mark=bool(c['mark']);anchor=get('se_sel_anchor',3)
        base=source40(expected,top,caret,marked=mark,anchor=anchor,dirty=c['dirty']);ui=UI(base)
        if c['variant']=='file-menu':ui.file_menu()
        elif c['variant']=='help':ui.help(cache=row_cache)
        elif c['variant']=='file-dialog':
            assert get('se_f_owner')==1 and get('se_fd_list_count')==len(directory) and not get('se_fd_page',2)
            for i,name in enumerate(directory):assert ram[n.s['se_fd_list_lengths']+i]==len(name) and ram[n.s['se_fd_list_names']+i*16:n.s['se_fd_list_names']+i*16+len(name)]==name
            name=ram[n.s['se_f_name']:n.s['se_f_name']+get('se_f_name_len')];assert name==b'DIVERSE';ui.file_dialog(get('se_f_device'),name,directory,get('se_fd_list_index'))
        if c['mode']==0:
            cells=bytearray(base.matrix);ink=bytearray(base.colors)
            if get('se_st_valid'):
                plan=semantic_plan(expected,anchors(expected,top,40),False,0,lexical=True)
                assert ram[0x4400:0x4400+880]==plan,(ident,'source40 semantic plan');semantic_cells+=880
                for cell,style in enumerate(plan):
                    cells[80+cell]^=style&128
                    p=80+cell
                    if ink[p]==1:ink[p]=WIDE_PALETTE[style&15]
            # Popup cells replace all underlying source semantics.
            for row,col in ui.cells:at=row*40+col;cells[at]=ui.matrix[at];ink[at]=ui.colors[at]
            assert ram[0x4000:0x43E8]==cells and bytes(v&15 for v in colors)==ink,(ident,'independent40 cells/colors')
            bits=bytearray(8000);attrs=bytearray(1000)
            for row in range(25):
                for col in range(40):
                    at=row*40+col;code=cells[at];bits[row*320+col*8:row*320+col*8+8]=bytes(v^(255 if code&128 else 0) for v in native[(code&127)*8:(code&127)*8+8]);attrs[at]=ink[at]<<4|6
            rowmap=base.anchors
        else:
            width=[40,60,80][c['mode']];font=(n.e/('grid60.seo' if width==60 else 'grid80.seo')).read_bytes()[36+0x800:36+0xC00];plan=None
            if wide_colors:
                assert get('se_st_valid') and not get('se_st_request'),(ident,'wide styles notpublished')
                plan=wide_semantics(expected,anchors(expected,top,width),width);assert ram[0x4800:0x4800+len(plan)]==plan,(ident,'independent wide semantic plan');semantic_cells+=len(plan)
            bits,attrs,rowmap=body_model(expected,top,caret,width,mark,anchor,font,plan);paint_native(bits,attrs,ui,native)
            if ram[0x6000:0x7F40]!=bits or ram[0x4000:0x43E8]!=attrs:
                actual_bits=ram[0x6000:0x7F40];actual_attrs=ram[0x4000:0x43E8];bd=[(i//320, (i%320)//8, i%8,a,b) for i,(a,b) in enumerate(zip(actual_bits,bits)) if a!=b];ad=[(i//40,i%40,a,b) for i,(a,b) in enumerate(zip(actual_attrs,attrs)) if a!=b];(n.out/(ident+'-expected-bitmap.bin')).write_bytes(bits);(n.out/(ident+'-expected-attributes.bin')).write_bytes(attrs);raise AssertionError((ident,'independent narrow bitmap/attributes','bitmapdiff',bd[:30],len(bd),'attrdiff',ad[:30],len(ad)))
        cache_record=verify_cache(c,expected,top,caret,anchor,plan if c['mode'] else None,ram,reu,n.s) if row_cache else None
        actualrows=tuple(int.from_bytes(ram[n.s['se_v_rows']+3*i:n.s['se_v_rows']+3*i+3],'little') for i in range(22))+(get('se_v_bottom',3),);assert actualrows==rowmap,(ident,'all23 source anchors');rows_checked+=23
        w,h,png=read_png(n.out/f'native-{ident}.png');assert(w,h)==(384,272);palette.setdefault(6,png[0]);assert palette[6]==png[0]
        for y in range(200):
            row,gy=divmod(y,8)
            for x in range(320):
                col,gx=divmod(x,8);at=row*40+col;bit=bits[row*320+col*8+gy]&(128>>gx);color=(attrs[at]>>4) if bit else attrs[at]&15;actual=png[(35+y)*w+32+x]
                assert actual==palette.setdefault(color,actual),(ident,'native pixel/color',x,y,color);pixels_checked+=1
        assert len(set(palette.values()))==len(palette),'palette roles alias'
        observed.append(dict(id=ident,mode=c['mode'],cache=cache_record,source_sha256=hashlib.sha256(expected).hexdigest(),source_bytes=len(expected),caret=caret,top=top,styled40=bool(get('se_st_valid')),history_current=get('se_h_current',4),history_saved=get('se_h_saved',4),history_end=get('se_h_end',2),history_cursor=get('se_h_cursor',2)))
    if not capture_smoke:
        before=D81Image((n.e/'initial-fixtures.d81').read_bytes());after=D81Image((n.e/'working.d81').read_bytes());assert after.read(b'GRIDOUT',kind=1).data==fixture()
        assert {x.name for x in after.entries()}=={x.name for x in before.entries()}|{b'GRIDOUT'},'unexpected temp/backup/foreign diskentry'
        for entry in before.entries():assert before.read(entry.name).entry.raw[2:]==after.read(entry.name).entry.raw[2:] and before.read(entry.name).sectors==after.read(entry.name).sectors and before.read(entry.name).data==after.read(entry.name).data,(entry.name,'unrelated disk bytes')
    result=dict(status='passed',executed_harness_sha256=hashlib.sha256((n.e/'test_grid_editor_vice.py').read_bytes()).hexdigest(),verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),prg_sha256=n.r['sha256'],resident_binding=n.r['resident_binding']['digest'],wide_colors=wide_colors,row_cache=row_cache,cache_content_bytes_checked=sum(5280 for c in n.cases if row_cache and c['mode']),cache_ownership_frames=len(n.cases) if row_cache else 0,modecycle_REU_allowance='Only5280 derived bytes in exclusively owned FE logical/physical bank' if row_cache else 'No changed REU bytes',semantic_cells_checked=semantic_cells,screenshots=len(n.cases),native_pixels_checked=pixels_checked,anchors_checked=rows_checked,source_bytes=422,clipboard_bytes=5,catalog_tail_preserved_bytes=192,REU_profile_bytes=REU_BYTES,native_IRQ_bytes=n.keys,source_saved_raw_D81=not capture_smoke,capture_smoke=capture_smoke,cases=observed,limits='Actual IRQ-byte disk/editor/native VIC proof; no physical keyboard chord or timing guarantee. UI chrome, menu, help and file labels/geometry/colors are specified independently; actual native font bytes come from sealed display assets.')
    (n.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


def synchronous_project(out):
    """Private copy: serialize VICE and recover capture after an idle stop.

    The installed .NET runner remains untouched. Existing Ultimate assembly is
    copied as a read-only reference, so its neighboring project is never built.
    """
    target=out/'synchronous-dotnet';target.mkdir(exist_ok=True)
    original=PROJECT.parent/'Program.cs';text=original.read_text(encoding='utf-8-sig')
    old='''    public static async Task<int> Main(string[] args)
    {
        try
        {
            return await Cli.RunAsync(args);'''
    new='''    public static async Task<int> Main(string[] args)
    {
        try
        {
            // Stopwatch scripts use a text-monitor breakpoint followed by an
            // atomic capture.  Concurrent VICE instances can steal the fixed
            // monitor pair or delay playback continuation, so own this lane.
            FileStream? viceLock = null;
            var lockDeadline = Stopwatch.StartNew();
            var lockPath = Path.Combine(Path.GetTempPath(), "supereditor-vice-stopwatch.lock");
            while (viceLock is null && lockDeadline.Elapsed < TimeSpan.FromMinutes(3))
            {
                try
                {
                    viceLock = new FileStream(lockPath, FileMode.OpenOrCreate,
                        FileAccess.ReadWrite, FileShare.None);
                }
                catch (IOException)
                {
                    await Task.Delay(100);
                }
            }
            if (viceLock is null)
                throw new AutomationException("E_VICE_LOCK_TIMEOUT",
                    "another owned SuperEditor VICE stopwatch run held the global lock for 180 seconds");
            using (viceLock)
                return await Cli.RunAsync(args);'''
    assert text.count(old)==1;text=text.replace(old,new)
    old='            var cmd = command.EndsWith(\'\\n\') ? command : command + "\\n";'
    new='            string? captureComplete = null;\n            string? captureLog = null;\n            string[] captureTail = Array.Empty<string>();\n            if (command.StartsWith("playback ", StringComparison.OrdinalIgnoreCase) &&\n                command.Contains("_coherent.mon", StringComparison.Ordinal))\n            {\n                var script = command.Substring(9).Trim().Trim(\'"\');\n                var scriptLines = File.ReadAllLines(script);\n                var lastRun = Array.FindLastIndex(scriptLines, line =>\n                    line.Trim().Equals("x", StringComparison.OrdinalIgnoreCase));\n                var lastSave = scriptLines.Last(line => line.StartsWith("bsave ", StringComparison.Ordinal));\n                captureComplete = lastSave.Split(\'"\')[1];\n                var logName = scriptLines.Take(lastRun).LastOrDefault(line =>\n                    line.StartsWith("logname ", StringComparison.Ordinal));\n                if (logName is not null)\n                    captureLog = logName.Split(\'"\')[1];\n                // VICE can stop playback at the measured breakpoint instead of\n                // continuing the commands after x.  Keep that post-stop tail\n                // ready as a fresh monitor transaction.  Coherent scripts with\n                // no x execute their bsave immediately and need no recovery.\n                captureTail = scriptLines.Skip(lastRun + 1)\n                    .Where(line => !line.Trim().Equals("log off", StringComparison.OrdinalIgnoreCase))\n                    .Concat(new[] { "log off" }).ToArray();\n                if (File.Exists(captureComplete))\n                    throw new AutomationException("E_CAPTURE_NOT_FRESH", "capture completion file already exists");\n            }\n            var cmd = command.EndsWith(\'\\n\') ? command : command + "\\n";'
    assert text.count(old)==1;text=text.replace(old,new)
    old='            return Drain();\n        }\n\n        public byte[] ReadBytes'
    new='            var reply = Drain();\n            if (captureComplete is not null)\n            {\n                var deadline = Stopwatch.StartNew();\n                var tailSent = false;\n                while (!File.Exists(captureComplete) || new FileInfo(captureComplete).Length != 1000)\n                {\n                    if (!tailSent && deadline.Elapsed > TimeSpan.FromMilliseconds(500) &&\n                        captureLog is not null && File.Exists(captureLog))\n                    {\n                        var stopped = false;\n                        try\n                        {\n                            stopped = File.ReadAllText(captureLog).Contains("Stop on",\n                                StringComparison.OrdinalIgnoreCase);\n                        }\n                        catch (IOException)\n                        {\n                            // VICE is still appending the trace; retry below.\n                        }\n                        if (stopped)\n                        {\n                            var tail = string.Join("\\n", captureTail) + "\\n";\n                            var tailBytes = Encoding.ASCII.GetBytes(tail);\n                            _stream.Write(tailBytes, 0, tailBytes.Length);\n                            _stream.Flush();\n                            tailSent = true;\n                            Thread.Sleep(100);\n                        }\n                    }\n                    if (deadline.Elapsed > TimeSpan.FromSeconds(120))\n                        throw new AutomationException("E_CAPTURE_COMPLETION_TIMEOUT",\n                            "atomic final colors capture did not finish in 120 seconds; post-stop tail sent=" + tailSent);\n                    reply += Drain();\n                    Thread.Sleep(20);\n                }\n                reply += Drain();\n            }\n            return reply;\n        }\n\n        public byte[] ReadBytes'
    assert text.count(old)==1;patched=text.replace(old,new)
    # Two owned emulators can launch within the same second. Their monitor
    # ports alone do not isolate the runner's REU backing file and dump paths.
    old_run='Path.Combine("logs", "vice_auto_" + TimeEx.TsForPath())'
    new_run='Path.Combine("logs", "vice_auto_" + TimeEx.TsForPath() + "_" + Guid.NewGuid().ToString("N")[..12])'
    assert patched.count(old_run)==1
    patched=patched.replace(old_run,new_run)
    (target/'Program.cs').write_text(patched)
    project=PROJECT.read_text(encoding='utf-8-sig');oldref='<ProjectReference Include="..\\ViceTasks.Ultimate\\ViceTasks.Ultimate.csproj" />'
    assert oldref in project
    project=project.replace(oldref,'<Reference Include="ViceTasks.Ultimate"><HintPath>ViceTasks.Ultimate.dll</HintPath></Reference>')
    (target/'SynchronousVice.csproj').write_text(project)
    ultimate=PROJECT.parent.parent/'ViceTasks.Ultimate/bin/Debug/net8.0/ViceTasks.Ultimate.dll';shutil.copy2(ultimate,target/ultimate.name)
    (target/'provenance.json').write_text(json.dumps(dict(original_program=str(original),original_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),private_program_sha256=hashlib.sha256(patched.encode()).hexdigest(),change='Serialize owned stopwatch VICE runs; wait bounded120s for final1000B colors capture; if playback stops at the measured breakpoint, issue the post-stop capture tail as a fresh monitor transaction with log-off after the sentinel; append GUID to runtime directories. Product/PC/source untouched.',referenced_ultimate_sha256=hashlib.sha256(ultimate.read_bytes()).hexdigest()),indent=2)+'\n')
    return target/'SynchronousVice.csproj'


def main():
    p=argparse.ArgumentParser();p.add_argument('--describe',action='store_true');p.add_argument('--model-check',action='store_true');p.add_argument('--freeze',action='store_true');p.add_argument('--wide-colors',action='store_true');p.add_argument('--capture-smoke',action='store_true');p.add_argument('--build',type=Path,default=ROOT/'build');p.add_argument('--product-sources',type=Path);p.add_argument('--prepare',type=Path);p.add_argument('--run',type=Path);p.add_argument('--verify-evidence',type=Path);a=p.parse_args()
    if a.describe:print(json.dumps(dict(status='prepared; no product or emulator invoked',source_bytes=len(fixture()),modes=[40,60,80],catalog=NAMES,binary_monitor=7500,text_monitor_block='7600..7639',REU_profile_bytes=REU_BYTES,required='Explicit parent stable build hash and VICE grant before freeze/run',coverage=['same422B FileOpen','body/menu/help/dialog/selection per mode','native copy5/paste/undo','F8 cycle with canonical/history/clipboard/REU hash preservation','80-column SaveAs/rawD81 byte oracle','full320x200 pixels and23anchors/frame','1024shim and192catalog tail']),indent=2));return
    if a.model_check:
        data=fixture();assert len(anchors(data,0,60))==23
        for mode in [60,80]:
            font=(ROOT/f'assets/fonts/generated/narrow{5 if mode==60 else 4}.bin').read_bytes();bits,attrs,rows=body_model(data,0,0,mode,False,0,font);assert len(bits)==8000 and len(attrs)==1000 and len(rows)==23
        print('Offline independent model shapes/fixture PASS; no product/emulator invoked');return
    if a.verify_evidence:
        from types import SimpleNamespace
        e=a.verify_evidence.resolve();r=json.loads((e/'editor-report.json').read_text());out=e/'editing';plan=json.loads((out/'plan.yaml').read_text());keys=max(int.from_bytes(bytes.fromhex(x['params']['equals_hex']),'little') for x in plan['steps'] if x['type']=='assert.memory' and x['params']['start']==r['symbols']['se_key_sequence'])
        n=SimpleNamespace(e=e,r=r,s=r['symbols'],out=out,cases=json.loads((out/'cases.json').read_text()),keys=keys,canary=bytes((i*73+29)&255 for i in range(1024)))
        evaluate(n,out/'run',out/'run/manifest.json');return
    if a.freeze:
        assert a.product_sources,'--product-sources exact immutable ZIP required';freeze(a.build,a.product_sources,a.wide_colors,a.capture_smoke);return
    if not a.prepare and not a.run:p.print_help();return
    e=(a.prepare or a.run).resolve();report=json.loads((e/'editor-report.json').read_text())
    if not (e/'initial-fixtures.d81').exists():package(e)
    n=scenario(e,report);plan=n.plan();ids=[x['id'] for x in plan['steps']];assert len(ids)==len(set(ids)),'duplicate private plan ids';(n.out/'plan.yaml').write_text(json.dumps(plan,indent=2)+'\n');(n.out/'cases.json').write_text(json.dumps(n.cases,indent=2)+'\n');print(f'PREPARED {len(n.steps)}steps/{n.keys}IRQbytes/{len(n.cases)}screens at{n.out}',flush=True)
    if a.run:
        project=synchronous_project(n.out) if n.row_cache else PROJECT
        if n.row_cache:
            import vice_plan
            vice_plan.PROJECT=project
        done=subprocess.run(['dotnet','build',str(project),*([] if n.row_cache else ['--no-restore']),'--nologo'],capture_output=True,text=True,timeout=120);assert done.returncode==0,done.stdout+done.stderr
        artifacts,manifest=run_plan(plan,n.out);evaluate(n,artifacts,manifest)

if __name__=='__main__':main()
