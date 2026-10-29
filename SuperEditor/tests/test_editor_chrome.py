"""Reusable chrome: independent120cells and old/new complete editor frames.

Uses the private pre-extraction30a369 resident/R1 snapshot and emits only
build/editor-chrome. No shared make, new resident state, or VICE is involved.
"""
from pathlib import Path
import hashlib,json,random,re,shutil,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import cpu_editor,editor_fixture
from overlays import wrap,HEADER
from peddle import Machine
from redraw_model import Screen,menu_header,native_text,screen_code,source40,verify_screen

OUT=ROOT/'build/editor-chrome'
REFERENCE=OUT/'reference'
FROZEN=ROOT/'build/style-editor/20261024T224213726611Z/fixture'
PRG_SHA='30a369cbb459ff80201465a0f86a6690b3088ec897974f6bd4e7830041ee5f4c'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def labels(path):
    return {p[2].lstrip('.'):int(p[1],16) for line in path.read_text().splitlines()
            if (p:=line.split()) and p[0]=='al'}


def build():
    OUT.mkdir(exist_ok=True)
    assert sha(REFERENCE/'editor.prg')==PRG_SHA
    assert sha(FROZEN/'build/editor.prg')==PRG_SHA
    old=(REFERENCE/'editor40-before.s').read_text()
    start=old.index('chrome:\n');end=old.index('.include "overlays/render-cache.s"')
    ro=old.index('.segment "RODATA"',end)
    wanted=old[:start]+'chrome:\n    jsr tui_editor_chrome40\n    jmp cache_save\n'+old[end:ro]
    wanted=wanted.replace('.import tui_header40','.import tui_editor_chrome40')
    assert (ROOT/'src/overlays/editor40.s').read_text()==wanted,'changes escaped extraction range'
    for name,source,overlay in [('editor40','src/overlays/editor40.s',False),
                              ('chrome','src/tui/editor-chrome40.s',True),
                              ('header','src/tui/header40.s',True)]:
        args=['ca65','-g','-I',str(ROOT/'src'),'-I',str(REFERENCE)]
        if overlay:args+=['-D','EDITOR_OVERLAY=1']
        subprocess.run(args+['-o',str(OUT/(name+'.o')),
                            str(ROOT/source)],check=True)
    cfg=ROOT/'cfg/overlay-r.cfg'
    for name,objects in [('module',['chrome','header']),('renderer',['editor40','header','chrome'])]:
        subprocess.run(['ld65','-C',str(cfg),'-o',str(OUT/(name+'.bin')),
            '-m',str(OUT/(name+'.map')),'-Ln',str(OUT/(name+'.lbl')),
            *[str(OUT/(o+'.o')) for o in objects]],check=True)
    size=(OUT/'renderer.bin').stat().st_size
    assert size<=4096 and size<=4017,(size,'R1 grew')
    dump=subprocess.run(['od65','--dump-segments',str(OUT/'chrome.o')],
        check=True,capture_output=True,text=True).stdout
    segments={name:int(size) for name,size in re.findall(
        r'Name:\s+"([^"]+)"[\s\S]*?Size:\s+(\d+)',dump)}
    assert segments['BSS']==segments['DATA']==segments['ZEROPAGE']==0,segments
    report=json.loads((REFERENCE/'editor-report.json').read_text())
    binding=bytes.fromhex(report['resident_binding']['digest'])
    image=wrap((OUT/'renderer.bin').read_bytes(),0,1,
        api=(report['symbols']['se_overlay_call'],report['symbols']['se_overlay_frame']),
        binding_digest=binding)
    (OUT/'text40.seo').write_bytes(image)
    return report,dict(original_payload=4017,extracted_payload=size,
        saved_bytes=4017-size,chrome_code_bytes=segments['CODE'],
        chrome_rodata_bytes=segments['RODATA'],
        chrome_code_and_rodata=segments['CODE']+segments['RODATA'],
        module_probe_including_existing_header=(OUT/'module.bin').stat().st_size,
        added_resident_state_bytes=0,added_zero_page_bytes=0)


def oracle(state):
    header,ink=menu_header();matrix=bytearray(header+bytes([32])*40)
    colors=bytes(ink+bytes([15])*40)
    def label(text,column):
        raw=bytes(map(screen_code,native_text(text)))
        matrix[80+column:80+column+len(raw)]=raw
    if state['ui']==2:
        label('Command:',0)
        raw=state['text']
        matrix[88:88+len(raw)]=bytes(map(screen_code,raw))
        matrix[88+len(raw)]=0xA0
    else:
        error=state['error']
        hint={0x7C:'Invalid number/text / F6 Help',
              0x7D:'No such line / F6 Help',
              0x7E:'No match / CTRL-N next / F6 Help'}.get(error)
        if hint is None and state['fault']:hint='Undo fault: Edit/C clear / F6 Help'
        if hint is None and not error and state['trimmed']:hint='Undo full: oldest dropped / F6 Help'
        if hint:label(hint,1)
        elif error:
            label('Error',1);matrix[87:89]=f'{error:02X}'.encode('ascii');label('F6 Help',32)
        else:
            label('Pos:',1);matrix[86:92]=f"{state['caret']:06X}".encode('ascii')
            label('Modified' if state['pending'] or state['dirty'] else 'Clean',14)
            if state['mark']:label('Mark',23)
            label('F6 Help',32)
    return bytes(matrix),colors


def settings(machine,s,state):
    for field,value,width in [('se_e_ui',state['ui'],1),('se_e_error',state['error'],1),
        ('se_hot_caret',state['caret'],3),('se_hot_pending',state['pending'],1),
        ('se_h_dirty',state['dirty'],1),('se_sel_mark',state['mark'],1),
        ('se_h_fault',state['fault'],1),('se_h_trimmed',state['trimmed'],2),
        ('se_e_text_length',len(state['text']),1)]:
        machine.load(s[field],value.to_bytes(width,'little'))
    machine.load(s['se_e_text'],state['text']+bytes(32-len(state['text'])))


def unit(report):
    s=report['symbols'];rng=random.Random(0xC140)
    m=Machine();prg=(REFERENCE/'editor.prg').read_bytes()
    m.load(int.from_bytes(prg[:2],'little'),prg[2:])
    read=lambda a,n:bytes(m.read(a+i) for i in range(n))
    normal=dict(ui=0,error=0,caret=0,pending=0,dirty=0,mark=0,fault=0,trimmed=0,text=b'')
    states=[]
    for caret in [0,1,0xFF,0x100,0xFFFF,0x10000,0xFEDCBA,0xFFFFFF]:
        for dirty,pending,mark in [(0,0,0),(1,0,0),(0,1,1),(1,1,1)]:
            states.append(normal|dict(caret=caret,dirty=dirty,pending=pending,mark=mark))
    for error in [0,1,0x40,0x7C,0x7D,0x7E,0xFF]:
        for fault,trimmed in [(0,0),(1,0),(0,0x100),(1,1)]:
            states.append(normal|dict(error=error,fault=fault,trimmed=trimmed))
    for length in range(32):
        text=(native_text('Mixed CASE 0123456789 ££ ')+bytes([0xFF,0xA0]))*2
        states.append(normal|dict(ui=2,error=0x7C,fault=1,trimmed=1,text=text[:length]))
    for _ in range(100):
        length=rng.randrange(32)
        states.append(normal|dict(ui=rng.choice([0,1,2,3]),error=rng.randrange(256),
            caret=rng.randrange(1<<24),pending=rng.randrange(2),dirty=rng.randrange(2),
            mark=rng.randrange(2),fault=rng.randrange(2),trimmed=rng.randrange(65536),
            text=bytes(rng.choice(native_text('abcDEF 0123+-£')+bytes([0xFF,0xA0])) for _ in range(length))))
    module=(OUT/'module.bin').read_bytes();old=(REFERENCE/'text40.bin').read_bytes()
    moduleentry=labels(OUT/'module.lbl')['tui_editor_chrome40']
    oldentry=labels(REFERENCE/'text40.lbl')['chrome']
    allowed=set(range(0x100,0x200))
    allowed.update(range(0x4000,0x4050));allowed.update(range(0x4000+960,0x4000+1000))
    allowed.update(range(0xD800,0xD850));allowed.update(range(0xD800+960,0xD800+1000))
    for key,width in [('text_ptr',2),('screen_ptr',2),('se_v_col',1),('se_v_cell',1)]:
        allowed.update(range(s[key],s[key]+width))
    peak=0
    try:
        for index,state in enumerate(states):
            wanted=oracle(state);outputs=[]
            for payload,entry in [(module,moduleentry),(old,oldentry)]:
                m.load(0xA000,bytes(4096));m.load(0xA000,payload)
                m.load(0x4000,bytes([0xE6])*1024);m.load(0xD800,bytes([9])*1024)
                m.load(0xC600,bytes((i*73+29)&255 for i in range(1024)))
                m.write(s['se_ink_reverse'],0);settings(m,s,state)
                before=read(0,65536) if payload is module else None
                result,count=m.call(entry,limit=20000);peak=max(peak,count)
                actual=(read(0x4000,80)+read(0x4000+960,40),
                        read(0xD800,80)+read(0xD800+960,40))
                assert actual==wanted,(index,state,'chrome oracle')
                assert read(0x4050,880)==bytes([0xE6])*880
                assert read(0xD850,880)==bytes([9])*880
                if before is not None:
                    after=read(0,65536)
                    assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(before,after))),('new module wrote outside contract',index)
                outputs.append(actual)
            assert outputs[0]==outputs[1],('old/new chrome',index)
        return dict(cases=len(states),chrome_cells=len(states)*120,
                    whole_c64_write_guard_cases=len(states),peak_instructions=peak)
    finally:m.close()


def full_frames(report):
    identity=json.loads((FROZEN/'freeze.json').read_text())
    roots=[]
    for name in ['old-fixture','new-fixture']:
        target=OUT/name
        if target.exists():shutil.rmtree(target)
        shutil.copytree(FROZEN,target);roots.append(target)
    shutil.copy2(OUT/'text40.seo',roots[1]/'build/overlays/text40.seo')
    variant_identity=dict(identity,assets=dict(identity['assets']))
    variant_identity['assets']['text40']=sha(roots[1]/'build/overlays/text40.seo')
    (roots[1]/'freeze.json').write_text(json.dumps(variant_identity,indent=2)+'\n')
    fixtures=[];frames=[]
    data=native_text('# Mixed CASE')+b'\r'+native_text('plain text and a long line ')*5+b'\r'+bytes(range(32,64))+b'\r'
    for root in roots:
        editor_fixture.ROOT=cpu_editor.ROOT=root
        editor_fixture.NAMES=cpu_editor.NAMES=identity['names']
        f=editor_fixture.EditorFixture();f.source(data,banks=2,physical=32);fixtures.append(f)
    def paint(tag):
        output=[]
        for f in fixtures:
            f.render()
            state=dict(ui=f.get('se_e_ui',1),error=f.get('se_e_error',1),
                caret=f.get('se_hot_caret'),pending=f.get('se_hot_pending',1),
                dirty=f.get('se_h_dirty',1),mark=f.get('se_sel_mark',1),
                fault=f.get('se_h_fault',1),trimmed=f.get('se_h_trimmed',2),
                text=f.read(f.s['se_e_text'],f.get('se_e_text_length',1)))
            base=source40(data,f.get('se_v_top'),state['caret'],marked=bool(state['mark']),
                anchor=f.get('se_sel_anchor'),pending=bool(state['pending']),
                dirty=bool(state['dirty']),error=state['error'],
                history_fault=bool(state['fault']),trimmed=bool(state['trimmed']))
            matrix,colors=bytearray(base.matrix),bytearray(base.colors)
            wanted=oracle(state)
            matrix[:80],matrix[960:1000]=wanted[0][:80],wanted[0][80:]
            colors[:80],colors[960:1000]=wanted[1][:80],wanted[1][80:]
            verify_screen(f.read(0x4000,1000),f.read(0xD800,1000),
                Screen(bytes(matrix),bytes(colors),base.anchors,base.caret),tag=tag)
            assert f.document()==data and f.read(0xC600,1024)==f.shim
            cache=b''.join(f.read(f.s[n],w) for n,w in [('se_r_valid',1),
                ('se_r_saved_revision',4),('se_r_path',1),('se_r_rows',1),
                ('se_r_cells',2),('se_r_under_glyph',1),('se_r_under_color',1)])
            output.append((f.read(0x4000,1000),f.read(0xD800,1000),
                           f.read(f.s['se_v_rows'],66),f.read(f.s['se_v_bottom'],3),cache))
        assert output[0]==output[1],('old/new full frame',tag)
        frames.append(tag)
    try:
        paint('normal')
        for error,fault,trimmed,dirty in [(0,0,0,1),(0x7C,1,1,0),(0x7D,0,0,0),
            (0x7E,0,0,0),(0x55,0,0,0),(0x55,1,0,0),(0,0,0x100,0)]:
            for f in fixtures:
                for n,v,w in [('se_e_error',error,1),('se_h_fault',fault,1),
                    ('se_h_trimmed',trimmed,2),('se_h_dirty',dirty,1)]:f.put(n,v,w)
            paint(f'status-{error:02x}-{fault}-{trimmed}-{dirty}')
        for f in fixtures:
            for n,w in [('se_e_error',1),('se_h_fault',1),('se_h_trimmed',2),('se_h_dirty',1)]:f.put(n,0,w)
            f.position(15);f.command(68);f.command(2)
        paint('mark-forward')
        for f in fixtures:f.command(1);f.command(1)
        paint('mark-reversed')
        for f in fixtures:f.command(50);f.key(0x88)
        paint('command-empty')
        for count,byte in enumerate(native_text('Mixed CASE 0123456789 abcDEFghijZ')):
            for f in fixtures:f.key(byte)
            if count in [0,6,29,30]:paint(f'command-length-{count+1}')
        for f in fixtures:
            assert f.get('se_e_text_length',1)==31
            f.key(native_text('x')[0]);assert f.get('se_e_text_length',1)==31
        paint('command-max-refuses32nd')
        for f in fixtures:f.key(0x14)
        paint('command-DEL')
        for f in fixtures:f.key(3)
        paint('command-cancel')
        return dict(frames=frames,full_screen_cells=len(frames)*1000,
                    old_new_cache_and23anchors_equal=True,source_bytes=len(data),shim_bytes=1024,
                    old_r1_sha256=identity['assets']['text40'],
                    new_r1_sha256=variant_identity['assets']['text40'])
    finally:
        for f in fixtures:f.close()


def main():
    (OUT/'result.json').unlink(missing_ok=True)
    report,sizes=build()
    result=dict(status='passed',resident_sha256=PRG_SHA,placement=sizes,
        module=unit(report),renderer=full_frames(report),
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in
            [ROOT/'src/overlays/editor40.s',ROOT/'src/tui/editor-chrome40.s',
             ROOT/'src/tui/header40.s',Path(__file__)]},
        binary_sha256={n:sha(OUT/n) for n in ['module.bin','renderer.bin','text40.seo']},
        limits=['Isolated linked module/R1 CPU proof against immutable30a369 resident.',
                'No new resident layout/shared make/native video/ReadyOS claim.'])
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
