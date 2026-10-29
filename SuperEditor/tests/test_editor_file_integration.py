"""Actual editor keyboard/render/root-pump/C10/C12 CPU integration.

Only KERNAL ROM entry points are modeled. The read-only 1581 U1 sectors and
directory BASIC stream are generated from the same independent filesystem used
by modeled sequential channels. This is neither native IEC nor physical keys.
Run after the parent freezes a complete twelve-asset production build; no make.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from editor_fixture import EditorFixture
import editor_fixture
import cpu_editor
from fileio_fixture import FileIOFixture, ROM
from redraw_model import Screen, native_text, screen_code, source40, verify_screen


def logical_lines(source, top, caret, pan, dirty):
    base=source40(source,top,caret,dirty=dirty)
    matrix,colors=bytearray(base.matrix),bytearray(base.colors)
    matrix[80:960]=bytes([32])*880;colors[80:960]=bytes([1])*880
    assert top==0 or source[top-1]==13
    pos=top;anchors=[];visible=None
    for row in range(22):
        anchors.append(pos);end=source.find(b'\r',pos)
        if end<0:end=len(source)
        for col in range(40):
            p=pos+pan+col
            if p>end:continue
            glyph=32 if p==end else screen_code(source[p]);ink=1
            if p==caret and visible is None:glyph^=128;ink=3;visible=(row,col)
            matrix[(row+2)*40+col]=glyph;colors[(row+2)*40+col]=ink
        pos=end+1 if end<len(source) else len(source)
    anchors.append(pos)
    return Screen(bytes(matrix),bytes(colors),tuple(anchors),visible)


def popup(base, *, operation=1, name=b'', device=8, entries=(), selected=0,
          help=False, confirm=False, error=0, dos=0, recovery=()):
    """Independent specified popup, including every untouched source cell."""
    matrix, colors = bytearray(base.matrix), bytearray(base.colors)
    for row in range(4, 23):
        for col in range(1, 39):
            code, ink = 32, 1
            if row in (4, 22):
                code, ink = 0x40, 14
                if col == 1: code = 0x70 if row == 4 else 0x6D
                if col == 38: code = 0x6E if row == 4 else 0x7D
            elif col in (1, 38): code, ink = 0x5D, 14
            matrix[row * 40 + col], colors[row * 40 + col] = code, ink

    def text(row, col, value):
        data = bytes(map(screen_code, native_text(value)))[:40-col]
        matrix[row*40+col:row*40+col+len(data)] = data

    text(5, 3, 'Open a PETSCII document' if operation == 1 else 'Save a PETSCII document')
    colors[5*40+3:5*40+38] = bytes([7])*35
    text(6, 3, 'Device:'); matrix[6*40+10] = ord('0')+device
    text(7, 3, 'Name:')
    matrix[7*40+10:7*40+10+len(name)] = bytes(map(screen_code, name))
    matrix[7*40+10+len(name)] = 0xA0
    colors[7*40+10:7*40+11+len(name)] = bytes([3])*(len(name)+1)
    if help:
        for row, value in [(10,'Type up to 16 PETSCII characters.'),
                           (12,'RETURN accepts the name.'),
                           (14,'F3 drive F5 page DEL erase'),
                           (16,'STOP cancels; F6 help.'),
                           (18,'S Save   D Discard   C Cancel')]: text(row,3,value)
    elif confirm:
        for row, value in [(10,'Save changes before opening?'),
                           (12,'S Save   D Discard   C Cancel'),
                           (14,'STOP cancels; F6 help.')]: text(row,3,value)
    elif error == 0x9B:
        text(10,3,'Recovery: files retained.'); text(12,3,'K keeps files and closes')
        for row, value in zip((14,16),recovery):
            matrix[row*40+4:row*40+4+len(value)] = bytes(map(screen_code,value))
    else:
        for index, entry in enumerate(entries):
            assert len(entry) <= 16 and index < 8
            at = (index+9)*40+4
            matrix[at:at+len(entry)] = bytes(screen_code(v) ^ (128 if index == selected else 0) for v in entry)
            colors[at:at+len(entry)] = bytes([3 if index == selected else 1])*len(entry)
        text(18,3,'UP/DOWN choose; RETURN accepts'); text(19,3,'F3 drive 8/9  F5 page')
        if error:
            text(21,3,'Error $    DOS $')
            matrix[21*40+10:21*40+12] = f'{error:02X}'.encode()
            matrix[21*40+19:21*40+21] = f'{dos:02X}'.encode()
    text(24,0,' File dialog       F6 Help   STOP Back   ')
    return Screen(bytes(matrix),bytes(colors),base.anchors,base.caret)


class IntegratedFiles(EditorFixture):
    def __init__(self, source=b'Original source\rSecond line\r', files=None):
        self.fs = dict(files or {})
        self.channels = {}; self.trace = []; self.inject = {}
        self.selected_in = self.selected_out = None
        self.st = 0; self.dos = b'00, OK,00,00\r'; self.directory = b''
        self.actions = []; self.opens = []; self.dos_commands = []; self.service_steps = 0
        super().__init__()
        self.source(source)
        assert len(self.assets) == 12, 'Requires actual complete FILEIO/AUX catalog'

    def call(self, name, a=0):
        # Fast ordinary resident calls still use the same CPU engine. Only the
        # root's actual file service can encounter the ROM boundary below.
        if name not in ('se_editor_service','se_editor_file_pump') or (
                name == 'se_editor_service' and self.get('se_e_job',1) != 9):
            return super().call(name,a)
        m=self.m; request=self.get('se_f_request',1)
        for key,value in [('pc',self.s[name]),('a',a),('x',0),('y',0),('sp',0xFD),('p',0x24)]:
            getattr(m.lib,'zeropage_peddle_set_'+key)(m.handle,value)
        m.write(0x1FE,0xFE);m.write(0x1FF,0x02)
        start=m.regs().instructions; iterations=0; consumed=False
        while m.regs().pc != 0x02FF:
            if m.regs().pc == self.s['se_editor_file_pump']:consumed=True
            if m.regs().pc in ROM: self.rom()
            else: m.lib.zeropage_peddle_step_instruction(m.handle)
            iterations+=1
            assert iterations < 2_000_000,(name,hex(m.regs().pc),hex(request))
        used=m.regs().instructions-start; self.total_instructions+=used
        if name == 'se_editor_service': self.max_service=max(self.max_service,used)
        if request and consumed:
            assert self.get('se_f_request',1)==0, ('resident must consume action exactly once',request)
            self.actions.append((request,self.get('se_f_result',1),self.get('se_f_carry',1)))
        assert self.read(0xC600,1024)==self.shim
        return m.regs()

    def rom(self):
        m=self.m; r=m.regs()
        if r.pc == 0xFFC0:
            self.opens.append((self.filename,self.device,self.sa))
            if self.filename == b'#' and not self.inject.get(r.pc):
                # Reuse exact independent KERNAL return semantics for this
                # special raw buffer, without adding a provider bypass.
                self.fs[b'__RAW']=bytes(256)
                saved=self.filename; self.filename=b'0:__RAW,S,R'
                FileIOFixture.rom(self)
                self.filename=saved; del self.fs[b'__RAW']; return
            if self.filename.startswith(b'$'): self.directory=self.directory_stream()
        FileIOFixture.rom(self)

    def command(self, value, *args, **kwargs):
        # FileIOFixture.rom dispatches DOS commands here. No editor command is
        # replaced: keyboard and F7 routes use se_editor_input throughout.
        if isinstance(value,int): return super().command(value,*args,**kwargs)
        self.dos_commands.append(value)
        if value.startswith(b'U1:'):
            fields=value.split(); track,sector=int(fields[-2]),int(fields[-1])
            sectors=self.raw_sectors()
            assert (track,sector) in sectors,('unexpected raw sector',track,sector)
            self.channels[7]=dict(data=sectors[track,sector],pos=0)
            self.dos=b'00, OK,00,00\r'
        else: FileIOFixture.command(self,value)

    def directory_stream(self):
        stream=bytearray(b'\x01\x04')
        for name in sorted(self.fs):
            stream+=b'\x01\x01'+max(1,(len(self.fs[name])+253)//254).to_bytes(2,'little')
            stream+=b'  "'+name+b'" SEQ\0'
        return bytes(stream+b'\0\0')

    def raw_sectors(self):
        """Small valid D81 subset: directory plus exact 254-byte SEQ chains."""
        entries=sorted(self.fs); result={}; head=bytearray(256);head[:2]=bytes([40,3]);result[40,0]=bytes(head)
        free=iter((t,s) for t in range(1,81) if t!=40 for s in range(40))
        starts={}
        for name in entries:
            data=bytes(self.fs[name]); parts=[data[i:i+254] for i in range(0,len(data),254)] or [b'']
            chain=[next(free) for _ in parts];starts[name]=chain[0]
            for i,part in enumerate(parts):
                raw=bytearray(256);raw[:2]=bytes(chain[i+1]) if i+1<len(chain) else bytes([0,len(part)+1]);raw[2:2+len(part)]=part
                result[chain[i]]=bytes(raw)
        pages=max(1,(len(entries)+7)//8)
        for page in range(pages):
            raw=bytearray(256);raw[:2]=bytes([40,4+page]) if page+1<pages else bytes([0,255])
            for index,name in enumerate(entries[page*8:page*8+8]):
                at=index*32;raw[at+2]=0x81;raw[at+3:at+5]=bytes(starts[name]);raw[at+5:at+21]=name.ljust(16,b'\xA0')
            result[40,3+page]=bytes(raw)
        return result

    def settle(self,error=None,render=False):
        steps=0
        while self.get('se_e_job',1):
            self.call('se_editor_service');steps+=1;self.service_steps+=1
            assert steps<30000,('root file job stuck',self.get('se_e_job',1),self.get('se_f_phase',1),self.get('se_f_request',1))
        if error is not None: assert self.get('se_e_error',1)==error,(self.get('se_e_error',1),error)
        if render: self.render()
        return steps

    def key(self,byte,*,mods=0,error=None):
        self.put('se_e_mods',mods,1);self.put('se_e_key',byte,1)
        self.call('se_editor_input');return self.settle(error)

    def start(self,route='menu',operation='O'):
        if route=='menu':
            for byte in [0x85,ord('F'),ord(operation)]: self.key(byte)
        elif route=='f7':
            self.key(0x88)
            for byte in {'O':b'OPEN','S':b'SAVE','A':b'SAVE AS'}[operation]: self.key(byte)
            self.key(13)
        elif route=='ctrl': self.key(0x0F if operation=='O' else 0x13,mods=4)
        else: raise AssertionError(route)
        assert self.get('se_e_command',1)=={'O':80,'S':81,'A':82}[operation]

    def enter_name(self,name,accept=False):
        for _ in range(16):self.key(0x14)
        for byte in name:self.key(byte)
        assert self.read(self.s['se_f_name'],self.get('se_f_name_len',1))==name
        if accept:self.key(13)

    def stop_job(self):
        # Matches the resident scheduler's STOP lane, not an out-of-band modal
        # key call while another file action owns the CPU.
        at=self.get('se_input_tail',1)
        self.m.write(self.s['se_input_chars']+at,3);self.m.write(self.s['se_input_mods']+at,0)
        self.put('se_input_head',(at+1)&63,1);self.call('se_editor_service');self.settle()

    def catalog(self,identity,missing=True):
        if missing:
            at=next(i for i in range(12) if self.m.read(self.s['se_overlay_ids']+i)==identity)
            self.m.write(self.s['se_overlay_ids']+at,0)
            return at
        raise AssertionError('Restore the returned catalog slot explicitly')

    def until(self,predicate):
        for _ in range(2000):
            if predicate():return
            assert self.get('se_e_job',1)==9,('file job unexpectedly ended',self.get('se_e_error',1))
            self.call('se_editor_service')
        raise AssertionError('file phase did not reach requested safe point')

    def accept_async(self):
        self.put('se_e_key',13,1);self.call('se_editor_input')
        if self.get('se_fd_confirm',1):
            self.put('se_e_key',ord('D'),1);self.call('se_editor_input')

    def object_bytes(self,token,length):
        out=bytearray()
        for at in range(0,length,1024):
            count=min(1024,length-at);self.m.load(self.s['se_object_id'],token)
            self.put('se_object_offset',at);self.put('se_object_length',count,2);self.put('se_object_c64',0x8000,2)
            assert not self.call('se_object_copy',1).p&1
            out.extend(self.read(0x8000,count))
        return bytes(out)

    def seed_protected(self):
        self.key(0xC1);self.command(32)
        self.position(0);self.key(0x89);self.position(7);self.key(3,mods=4);self.key(3)
        assert self.get('se_clip_active',1) and self.get('se_h_current',4)
        self.position(3)

    def stable(self):
        return dict(source=self.document(),caret=self.get('se_hot_caret'),
                    current_name=self.read(self.s['se_f_current_name'],self.get('se_f_current_len',1)),
                    current_device=self.get('se_f_current_device',1),
                    selection=(self.get('se_sel_mark',1),self.get('se_sel_anchor')),
                    history=self.read(self.s['se_h_current'],4),saved=self.read(self.s['se_h_saved'],4),
                    journal=self.object_bytes(self.read(self.s['se_h_token'],5),self.get('se_h_end',2)),
                    clipboard_state=self.read(self.s['se_clip_token'],12),
                    clipboard=self.object_bytes(self.read(self.s['se_clip_token'],5),self.get('se_clip_length')) if self.get('se_clip_active',1) else b'',
                    shim=self.read(0xC600,1024))

    def check_stable(self,before):
        assert self.stable()==before,('source/caret/history/clipboard changed',before,self.stable())

    def check_screen(self,source,**spec):
        # No FILESTATE field is used to infer the expected name/list/help/error.
        union=self.read(0x8D00,1152)
        self.render()
        assert self.read(0x8D00,1152)==union,'source/modal painting corrupted FILESTATE'
        if self.get('se_l_mode',1):
            base=logical_lines(source,self.get('se_v_top'),self.get('se_hot_caret'),self.get('se_l_pan'),bool(self.get('se_h_dirty',1)))
        else:base=source40(source,self.get('se_v_top'),self.get('se_hot_caret'),dirty=bool(self.get('se_h_dirty',1)),
                           marked=bool(self.get('se_sel_mark',1)),anchor=self.get('se_sel_anchor'))
        expected=popup(base,**spec)
        verify_screen(self.read(0x4000,1000),self.read(0xD800,1000),expected,tag='integrated file popup')

    def idle(self,owner=0,ui=0):
        assert self.get('se_e_job',1)==0 and self.get('se_f_owner',1)==owner and self.get('se_e_ui',1)==ui
        assert not self.channels,('leaked modeled ROM channels',self.channels)
        assert self.get('se_doc_read_locks',1)==0
        assert self.read(0xC600,1024)==self.shim


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--frozen',type=Path,required=True,help='Freeze directory containing build/editor.prg, report and sidecars')
    parser.add_argument('--only',default='',help='Case-name substring for focused investigation; result is labeled partial')
    parser.add_argument('--emergency',action='store_true',help='Include final integrated unavailable-overlay/recovery gate')
    args=parser.parse_args();frozen=args.frozen.resolve()
    freeze=json.loads((frozen/'freeze.json').read_text())
    editor_fixture.ROOT=cpu_editor.ROOT=frozen
    editor_fixture.NAMES=cpu_editor.NAMES=freeze['names']
    report=json.loads((frozen/'build/editor-report.json').read_text())
    identity=report['sha256'];assert hashlib.sha256((frozen/'build/editor.prg').read_bytes()).hexdigest()==identity
    for name,digest in freeze['assets'].items():assert hashlib.sha256((frozen/f'build/overlays/{name}.seo').read_bytes()).hexdigest()==digest
    cases=[]; screen_count=0; total_actions=0; total_rom=0; max_service=0
    def run(tag,body):
        nonlocal total_actions,total_rom,max_service
        if args.only and args.only not in tag:return
        print('CASE '+tag,flush=True); f=IntegratedFiles()
        try:
            body(f);cases.append(dict(tag=tag,actions=len(f.actions),rom_calls=len(f.trace),service_steps=f.service_steps))
            total_actions+=len(f.actions);total_rom+=len(f.trace);max_service=max(max_service,f.max_service)
        finally:f.close()

    def modal(f):
        nonlocal screen_count
        names=[f'FILE{i:02}'.encode() for i in range(19)]
        f.fs={n:bytes([i]) for i,n in enumerate(names)}; old=f.stable()
        f.start();f.idle(1,3);assert f.get('se_fd_list_count',1)==8
        f.check_screen(old['source'],entries=names[:8]);screen_count+=1
        union=f.read(0x8D00,1152)
        # Every C8 operation must reject the phase union before touching it.
        assert not f.call('se_doc_read_acquire').p&1
        nav=f.read(0x9180,123)
        for operation in [1,2,3,4,5,6,7]:
            f.put('se_overlay_frame',operation,1)
            regs,_=f.m.call(f.s['se_overlay_call'],a=8,x=1)
            assert regs.p&1,('C8 accepted FILESTATE owner',operation)
            assert f.read(0x8D00,1152)==union
            assert f.read(0x9180,123)==nav and f.get('se_doc_read_locks',1)==1
        assert not f.call('se_doc_read_release').p&1
        for byte in [0x85,0x88]:f.key(byte);f.idle(1,3);assert f.read(0x8D00,1152)==union
        f.key(0x8B);f.check_screen(old['source'],entries=names[:8],help=True);screen_count+=1
        f.key(0x8B);f.key(0x87);f.key(0x91);f.key(0x11)
        assert f.get('se_fd_page',2)==1
        f.check_screen(old['source'],name=names[9],entries=names[8:16],selected=1);screen_count+=1
        f.key(0x86);assert f.get('se_f_device',1)==9 and f.get('se_fd_page',2)==0
        # All native printable classes, including Pi and graphics, are rendered
        # through the project's PETSCII conversion, never host ASCII decoding.
        native=bytes([0x20,0x3F,0x40,0x5F,0x60,0x7E,0xA0,0xBF,0xC0,0xDF,0xE0,0xFE,0xFF,0x41,0x61,0xC1])
        f.enter_name(native);f.key(ord('Q'));assert f.get('se_f_name_len',1)==16
        f.check_screen(old['source'],device=9,name=native,entries=names[:8]);screen_count+=1
        f.key(3);f.idle();f.check_stable(old)
    run('modal-list-native-filename-fullscreen-C8-union-guard',modal)

    def no_wrap(f):
        nonlocal screen_count
        data=(native_text('Long logical line with mixed CASE and native graphics: ')*3+b'\xFF\r')*28
        f.source(data);f.command(77);f.position(97);f.render()
        assert f.get('se_l_mode',1)==1 and f.get('se_l_pan')>0
        f.fs={b'NEXT':b'next'};old=f.stable();f.start();f.idle(1,3)
        f.check_screen(data,entries=[b'NEXT']);screen_count+=1
        f.key(0x8B);f.check_screen(data,entries=[b'NEXT'],help=True);screen_count+=1
        f.key(3);f.idle();f.check_stable(old)
    run('no-wrap-panned-body-C11-popup-preserves-entire-FILESTATE',no_wrap)

    for route in ['menu','f7','ctrl']:
        def opened(f,route=route):
            nonlocal screen_count
            data=bytes(range(256))*4+b'\0\xFF\r';f.fs={b'NEXT':data}
            f.position(7);f.start(route);f.enter_name(b'NEXT',True);f.idle()
            assert f.document()==data and f.get('se_hot_caret')==0
            assert f.get('se_h_dirty',1)==0 and f.read(f.s['se_f_current_name'],4)==b'NEXT'
            assert any(n==b'0:NEXT,S,R' for n,_,_ in f.opens)
            assert any(c.startswith(b'U1:') for c in f.dos_commands)
            assert any(op==0xE1 for op,_,_ in f.actions)
            f.render();verify_screen(f.read(0x4000,1000),f.read(0xD800,1000),source40(data,0,0),tag='opened source')
            screen_count+=1
        run(route+'-OPEN-actual-root-pump-binary-source',opened)

    def absent(f):
        nonlocal screen_count
        f.seed_protected();f.position(1);f.key(0x89);f.position(5)
        old=f.stable();assert old['selection']==(1,1)
        f.start();f.enter_name(b'MISSING',True)
        assert f.get('se_fd_confirm',1)==1;f.key(ord('D'));f.idle(1,3)
        assert f.get('se_f_error',1)==0x93 and f.get('se_f_dos_error',1)==62
        f.check_screen(old['source'],name=b'MISSING',error=0x93,dos=62);screen_count+=1
        f.check_stable(old);assert any((op,result,carry)==(0xC2,0x93,1) for op,result,carry in f.actions)
        f.key(3);f.idle();f.check_stable(old)
    run('missing-DOS-error-result-carry-retains-modal-source',absent)

    for size in [0,1,257,4097]:
        def roundtrip(f,size=size):
            data=bytes((i*37+11)&255 for i in range(size));f.source(data)
            f.start(operation='A');f.enter_name(b'ROUND',True);f.idle()
            assert f.fs=={b'ROUND':data} and f.document()==data
            assert any(op==0xE8 for op,_,_ in f.actions)
            f.fs[b'ROUND']=b'previous disk bytes';f.start('ctrl','S');f.idle()
            assert f.fs=={b'ROUND':data} and f.get('se_h_dirty',1)==0
            f.start('f7','O');f.enter_name(b'ROUND',True);f.idle();assert f.document()==data
        run('SAVEAS-overwrite-reopen-'+str(size),roundtrip)

    for route,operation in [('menu','S'),('f7','S'),('f7','A')]:
        def save_route(f,route=route,operation=operation):
            data=f.document();f.fs={b'OLD':b'old disk'}
            f.m.load(f.s['se_f_current_name'],b'OLD');f.put('se_f_current_len',3,1);f.put('se_f_current_device',8,1)
            f.start(route,operation)
            if operation=='A':f.enter_name(b'NEW',True)
            f.idle();assert f.fs[b'NEW' if operation=='A' else b'OLD']==data
            if operation=='A':assert f.fs[b'OLD']==b'old disk'
        run(route+'-common-command-'+operation,save_route)

    def ctrl_home(f):
        f.position(7);f.key(0x13);f.idle();assert f.get('se_hot_caret')==0 and not f.actions
        f.start('ctrl','S');f.idle(1,3);assert f.get('se_f_operation',1)==2
        f.enter_name(b'CTRLHOME',True);f.idle();assert f.fs[b'CTRLHOME']==f.document()
    run('native-HOME-versus-CTRL-S-modifier4-disambiguation',ctrl_home)

    def native_roundtrip(f):
        name=bytes([0x21,0x40,0x5F,0x60,0x7E,0xA1,0xBF,0xC0,0xDF,0xE0,0xFE,0xFF,0x41,0x61,0xC1,0xA2])
        data=f.document();f.start('f7','A');f.enter_name(name,True);f.idle()
        assert f.fs=={name:data} and f.read(f.s['se_f_current_name'],16)==name
        f.start('f7','S');f.idle();assert f.fs=={name:data}
        f.start('f7','O');f.enter_name(name,True);f.idle();assert f.document()==data
        assert any(n==b'0:'+name+b',S,R' for n,_,_ in f.opens)
    run('native-sixteen-byte-name-exact-SaveAs-overwrite-OPEN',native_roundtrip)

    def invalid(f):
        nonlocal screen_count
        f.fs={b'GOOD':b'good'};old=f.stable();f.start();opened=list(f.opens)
        f.enter_name(b'BAD:NAME',True);f.idle(1,3)
        assert f.get('se_f_error',1)==0x90 and f.opens==opened
        f.check_stable(old);f.check_screen(old['source'],name=b'BAD:NAME',entries=[b'GOOD'],error=0x90);screen_count+=1
        f.enter_name(b'GOOD',True);f.idle();assert f.document()==b'good'
    run('filename-validation-no-DOS-syntax-admission-then-retry',invalid)

    for operation in ['O','A']:
        for name in [b'\xA0HIDDEN',b'NAME\xA0SUFFIX',b'FIFTEENCHARS123\xA0']:
            def shifted_space(f,operation=operation,name=name):
                f.fs={b'NAME':b'Foreign existing file',b'GOOD':b'good'}
                f.start(operation=operation);old=f.stable();opened=list(f.opens)
                disk={n:bytes(data) for n,data in f.fs.items()};dos=list(f.dos_commands)
                f.enter_name(name,True);f.idle(1,3)
                assert f.get('se_f_error',1)==0x90 and f.get('se_f_lease',1)==0
                assert f.opens==opened and f.dos_commands==dos and f.fs==disk
                f.check_stable(old)
                f.enter_name(b'GOOD',True);f.idle()
                assert f.fs[b'GOOD']==(old['source'] if operation=='A' else b'good')
                assert f.document()==(old['source'] if operation=='A' else b'good')
            run('A0-alias-refusal-'+operation+'-'+name.hex(),shifted_space)

    for choice in ['S','D','C']:
        def dirty(f,choice=choice):
            nonlocal screen_count
            f.fs={b'NEXT':b'New source\r',b'OLD':b'Old disk'}
            f.m.load(f.s['se_f_current_name'],b'OLD');f.put('se_f_current_len',3,1);f.put('se_f_current_device',8,1)
            # A real pending native edit is flushed by OPEN before FILESTATE is
            # acquired. Capture the durable baseline after that safe point.
            f.key(0xC1);f.key(0x41);assert f.get('se_hot_pending',1)
            f.start('f7');old=f.stable();assert old['source'].startswith(b'\xC1A')
            f.enter_name(b'NEXT',True);assert f.get('se_fd_confirm',1)==1
            f.check_screen(old['source'],name=b'NEXT',entries=sorted(f.fs),confirm=True);screen_count+=1
            f.key(ord(choice));f.idle()
            if choice=='C':f.check_stable(old);assert f.fs[b'OLD']==b'Old disk'
            else:
                assert f.document()==b'New source\r' and f.get('se_hot_caret')==0
                assert f.fs[b'OLD']==(old['source'] if choice=='S' else b'Old disk')
        run('pending-flush-dirty-OPEN-'+choice,dirty)

    def unnamed(f):
        f.fs={b'NEXT':b'Next opened'};f.key(ord('x'));f.start();old=f.document()
        f.enter_name(b'NEXT',True);f.key(ord('S'));f.idle(1,3)
        assert f.get('se_f_operation',1)==3 and f.get('se_fd_resume',1)==1
        f.enter_name(b'SAVED',True);f.idle()
        assert f.fs[b'SAVED']==old and f.document()==b'Next opened'
        assert f.read(f.s['se_f_current_name'],4)==b'NEXT'
    run('unnamed-SaveAs-before-frozen-OPEN-resume',unnamed)

    def cancelled(f):
        f.fs={b'LARGE':bytes(range(256))*24};f.seed_protected();f.position(4);old=f.stable();f.start();f.enter_name(b'LARGE')
        f.accept_async()
        for _ in range(500):
            if f.get('se_f_request',1)==0xC4 and f.get('se_f_position')>0:break
            f.call('se_editor_service')
        else:raise AssertionError('did not reach partial actual C10 read')
        f.stop_job();f.idle();f.check_stable(old)
    run('scheduler-STOP-during-open-after-first-256bytes',cancelled)

    def directory_cancel(f):
        f.fs={b'NEXT':b'next'};f.seed_protected();old=f.stable()
        f.key(0x85);f.key(ord('F'));f.put('se_e_key',ord('O'),1);f.call('se_editor_input')
        assert f.get('se_f_request',1)==0xCE and f.get('se_e_job',1)==9
        f.stop_job();f.idle();f.check_stable(old)
        assert sum(op==0xCE for op,_,_ in f.actions)==1
        assert sum(op==0xCC for op,_,_ in f.actions)==1
    run('scheduler-STOP-consumes-outstanding-directory-action-once',directory_cancel)

    def read_failure(f):
        nonlocal screen_count
        f.fs={b'NEXT':b'x'*1025};f.seed_protected();f.position(3);old=f.stable();f.start();f.enter_name(b'NEXT')
        f.accept_async()
        for _ in range(500):
            if f.get('se_f_request',1)==0xC4:break
            f.call('se_editor_service')
        else:raise AssertionError('no actual read action')
        f.inject[0xFFC6]=0x20;f.settle();f.idle(1,3);f.check_stable(old)
        assert f.get('se_f_error',1)==0x92
        f.check_screen(old['source'],name=b'NEXT',entries=[b'NEXT'],error=0x92);screen_count+=1
        f.key(3);f.idle();f.check_stable(old)
    run('actual-KERNAL-CHKIN-failure-preserves-source-history-caret',read_failure)

    def recovery(f):
        nonlocal screen_count
        f.fs={b'OLD':b'Original disk bytes'};f.seed_protected();old=f.stable()
        f.start(operation='A');f.enter_name(b'OLD');f.accept_async()
        for _ in range(500):
            if f.get('se_f_request',1)==0xC6:break
            f.call('se_editor_service')
        else:raise AssertionError('no actual write action')
        f.inject[0xFFD2]=0x20;f.settle();f.idle(1,3);f.check_stable(old)
        assert f.get('se_f_error',1)==0x9B and f.get('se_io_owned_temp',1)==1
        assert f.fs[b'OLD']==b'Original disk bytes' and f.fs[b'SE~T000000000000']==b''
        f.check_screen(old['source'],operation=3,name=b'OLD',error=0x9B,recovery=[b'SE~T000000000000']);screen_count+=1
        disk={n:bytes(data) for n,data in f.fs.items()};union=f.read(0x8D00,1152)
        f.key(3);assert f.get('se_f_owner',1)==1 and f.get('se_io_owned_temp',1)==1
        assert f.fs==disk and f.read(0x8D00,1152)==union
        f.check_stable(old)
    run('uncertain-CHROUT-retains-exact-temp-and-recovery-STOP',recovery)

    if args.emergency:
        def missing_open(f):
            nonlocal screen_count
            f.fs={b'NEXT':bytes(range(256))*5};f.seed_protected();old=f.stable()
            f.start();f.enter_name(b'NEXT');f.accept_async()
            f.until(lambda:f.get('se_f_request',1)==0xC4 and f.get('se_f_position')>0)
            f.call('se_editor_service');assert f.get('se_io_mode',1)==1
            f.catalog(12);f.settle();f.idle(1,3);f.check_stable(old)
            assert f.get('se_e_error',1)==0x17 and f.get('se_f_error',1)==0x9B
            assert f.get('se_f_allocated',1)==0
            f.check_screen(old['source'],name=b'NEXT',error=0x9B);screen_count+=1
            f.key(0x8B);assert f.get('se_f_ui_help',1)==1
            f.check_screen(old['source'],name=b'NEXT',help=True);screen_count+=1
            f.key(0x8B);f.key(3);f.idle();f.check_stable(old)
        run('missing-C12-partial-OPEN-AUX-cleans-candidates-and-modal-help',missing_open)

        def missing_before_history(f):
            f.fs={b'NEXT':b'New candidate'}
            f.m.load(f.s['se_f_current_name'],b'OLD');f.put('se_f_current_len',3,1);f.put('se_f_current_device',9,1)
            f.position(7);old=f.stable()
            f.start();f.enter_name(b'NEXT');f.accept_async()
            f.until(lambda:f.get('se_f_request',1)==0xE1)
            assert f.get('se_f_committed',1)==1
            f.catalog(12);f.stop_job();f.idle(1,3);f.check_stable(old)
            assert f.get('se_e_error',1)==0x17 and f.get('se_f_error',1)==0x9B
            assert f.get('se_f_committed',1)==0 and f.get('se_f_allocated',1)==0
            f.key(ord('K'));f.idle();f.check_stable(old)
        run('missing-C12-STOP-before-H_INIT-restores-old-canonical',missing_before_history)

        def missing_after_history(f):
            nonlocal screen_count
            data=b'New acknowledged source\r'+bytes(range(32,127))
            f.fs={b'NEXT':data,b'OLD':b'Original bound disk file'}
            f.m.load(f.s['se_f_current_name'],b'OLD');f.put('se_f_current_len',3,1);f.put('se_f_current_device',8,1)
            f.position(0);f.key(0x89);f.position(7);f.key(3,mods=4);f.key(3)
            clipboard=f.read(f.s['se_clip_token'],12)
            copied=f.object_bytes(f.read(f.s['se_clip_token'],5),f.get('se_clip_length'))
            f.position(7);f.start();f.enter_name(b'NEXT');f.key(0x86)
            assert f.get('se_f_device',1)==9
            f.accept_async()
            f.until(lambda:f.get('se_f_request',1)==0xE1)
            f.call('se_editor_service')
            assert f.get('se_f_request',1)==0 and f.get('se_f_carry',1)==0 and f.get('se_f_committed',1)==1
            f.catalog(12);f.settle();f.idle(1,3)
            assert f.document()==data and f.get('se_hot_caret')==0 and f.get('se_hot_pending',1)==0
            assert f.get('se_e_error',1)==0x17 and f.get('se_f_error',1)==0x9B
            assert f.get('se_f_allocated',1)==0 and f.get('se_f_committed',1)==0
            assert f.read(f.s['se_f_current_name'],f.get('se_f_current_len',1))==b'NEXT','acknowledged OPEN retained previous filename'
            assert f.get('se_f_current_device',1)==9
            assert f.read(f.s['se_clip_token'],12)==clipboard
            assert f.object_bytes(f.read(f.s['se_clip_token'],5),f.get('se_clip_length'))==copied
            f.check_screen(data,name=b'NEXT',device=9,error=0x9B);screen_count+=1
            f.key(ord('K'));f.idle();assert f.document()==data and f.fs[b'OLD']==b'Original bound disk file'
        run('missing-C12-after-H_INIT-ack-preserves-new-source-and-resets-caret',missing_after_history)

        def refused_history(f):
            f.fs={b'NEXT':b'Next candidate',b'OLD':b'Original disk'};f.seed_protected()
            f.m.load(f.s['se_f_current_name'],b'OLD');f.put('se_f_current_len',3,1);f.put('se_f_current_device',9,1)
            old=f.stable();f.start();f.enter_name(b'NEXT');f.accept_async()
            f.until(lambda:f.get('se_f_request',1)==0xE1)
            f.catalog(4);f.settle();f.idle(1,3);f.check_stable(old)
            assert any((op,result,carry)==(0xE1,0x17,1) for op,result,carry in f.actions)
            assert f.get('se_f_error',1)==0x9B and f.get('se_e_error',1)==0x17
            f.key(ord('K'));f.idle();f.check_stable(old)
        run('H_INIT-real-EEDIT-admission-refusal-preserves-old-binding-and-history',refused_history)

        for boundary in ['acknowledged','unconsumed-STOP','refused']:
            def saved_boundary(f,boundary=boundary):
                f.fs={b'OLD':b'Old bound disk file'};f.seed_protected();source=f.document()
                f.m.load(f.s['se_f_current_name'],b'OLD');f.put('se_f_current_len',3,1);f.put('se_f_current_device',8,1)
                saved=f.read(f.s['se_h_saved'],4)
                f.start(operation='A');f.enter_name(b'NEW');f.key(0x86);f.accept_async()
                f.until(lambda:f.get('se_f_request',1)==0xE8)
                assert f.fs[b'NEW']==source and f.get('se_f_device',1)==9
                if boundary=='acknowledged':
                    f.call('se_editor_service');assert f.get('se_f_carry',1)==0
                    f.catalog(12);f.settle()
                elif boundary=='unconsumed-STOP':f.catalog(12);f.stop_job()
                else:f.catalog(4);f.settle()
                f.idle(1,3)
                expected=b'NEW' if boundary=='acknowledged' else b'OLD'
                assert f.read(f.s['se_f_current_name'],f.get('se_f_current_len',1))==expected,'H_SAVED boundary association wrong'
                assert f.get('se_f_current_device',1)==(9 if boundary=='acknowledged' else 8)
                assert f.get('se_h_dirty',1)==(0 if boundary=='acknowledged' else 1)
                assert f.read(f.s['se_h_saved'],4)==(f.read(f.s['se_h_current'],4) if boundary=='acknowledged' else saved)
                assert f.document()==source and f.fs[b'OLD']==b'Old bound disk file'
                assert f.get('se_f_error',1)==0x9B
                # A refused E8 reaches normal save-policy recovery; the modal
                # carries9B. Missing C12 itself preserves admission17 globally.
                assert f.get('se_e_error',1)==(0 if boundary=='refused' else 0x17)
                if boundary=='refused':assert (0xE8,0x17,1) in f.actions
                f.key(ord('K'));f.idle();assert f.fs[b'NEW']==source
            run('H_SAVED-'+boundary+'-SAVEAS-binding-and-savepoint',saved_boundary)

        for helper in [False,True]:
            def retirement(f,helper=helper):
                nonlocal screen_count
                data=b'New published source\r';f.fs={b'NEXT':data,b'OLD':b'Old disk'}
                f.m.load(f.s['se_f_current_name'],b'OLD');f.put('se_f_current_len',3,1);f.put('se_f_current_device',8,1)
                f.position(7);f.start();f.enter_name(b'NEXT');f.key(0x86);f.accept_async()
                f.until(lambda:f.get('se_f_request',1)==0xE1);f.call('se_editor_service')
                # Fault the saved retiring original token, never canonical
                # objects/provider tables. Actual ownership validation refuses.
                at=f.s['se_f_old']+6;f.m.write(at,f.m.read(at)^0x80)
                if helper:f.catalog(12)
                f.settle();f.idle(1,3)
                assert f.document()==data and f.get('se_hot_caret')==0
                assert f.get('se_f_error',1)==0x9B
                assert f.read(f.s['se_f_current_name'],f.get('se_f_current_len',1))==b'NEXT','retirement fault retained previous filename'
                assert f.get('se_f_current_device',1)==9
                assert f.get('se_f_allocated',1)==2,'failed old retirement capability was dropped'
                f.check_screen(data,name=b'NEXT',device=9,error=0x9B);screen_count+=1
                assert f.fs[b'OLD']==b'Old disk'
                queue=f.read(f.s['se_f_candidate'],10);disk={n:bytes(v) for n,v in f.fs.items()}
                f.key(ord('K'));assert f.get('se_f_owner',1)==1 and f.get('se_f_allocated',1)==2
                assert f.read(f.s['se_f_candidate'],10)==queue and f.fs==disk
            run(('AUX' if helper else 'C12')+'-postcommit-retirement-refusal-preserves-new-binding',retirement)

        def missing_save(f,both=False):
            nonlocal screen_count
            f.fs={b'OLD':b'Old disk'};f.seed_protected();old=f.stable()
            f.start(operation='A');f.enter_name(b'OLD');f.accept_async()
            f.until(lambda:f.get('se_f_request',1)==0xC6)
            f.call('se_editor_service');assert f.get('se_io_mode',1)==2 and f.get('se_f_lease',1)==1
            assert not f.call('se_doc_read_acquire').p&1
            assert f.get('se_doc_read_locks',1)==2
            disk={n:bytes(data) for n,data in f.fs.items()};dos=list(f.dos_commands)
            held=bytearray(f.read(0x8D00,1152))
            f.catalog(12)
            if both:f.catalog(13)
            f.settle();assert not f.channels and f.get('se_e_ui',1)==3 and f.get('se_f_owner',1)==1
            assert f.get('se_e_error',1)==0x17 and f.get('se_f_error',1)==0x9B
            assert f.fs==disk and f.dos_commands==dos
            assert f.get('se_io_owned_temp',1)==1 and f.get('se_io_mode',1)==0
            if both:
                held[f.s['se_io_mode']-0x8D00]=0
                held[f.s['se_f_error']-0x8D00]=0x9B
                assert f.read(0x8D00,1152)==held,'resident fallback altered retained FILESTATE beyond error/mode'
                assert f.get('se_f_lease',1)==1 and f.get('se_doc_read_locks',1)==2
                assert f.get('se_f_phase',1)!=0
                # Owner/frame/lease remain intentionally live when no helper
                # can establish source safety; only owned channels were closed.
                f.check_stable(old)
                return
            assert f.get('se_f_lease',1)==0 and f.get('se_doc_read_locks',1)==1
            assert not f.call('se_doc_read_release').p&1
            f.idle(1,3);f.check_stable(old)
            f.check_screen(old['source'],operation=3,name=b'OLD',error=0x9B,recovery=[b'SE~T000000000000']);screen_count+=1
            f.key(3);assert f.get('se_f_owner',1)==1 and f.fs==disk
            f.key(ord('K'));f.idle();assert f.fs==disk and f.dos_commands==dos
            f.check_stable(old)
        run('missing-C12-SAVE-releases-only-owned-lease-K-keeps-exact-files',missing_save)
        run('missing-C12-and-AUX-closes-owned-channels-retains-lease-frame',lambda f:missing_save(f,True))

        def missing_transport(f):
            f.fs={b'NEXT':b'N'*1300};f.seed_protected();old=f.stable()
            f.start();f.enter_name(b'NEXT');f.accept_async()
            f.until(lambda:f.get('se_f_request',1)==0xC4 and f.get('se_f_position')>0)
            assert f.get('se_io_mode',1)==1
            f.catalog(10);f.settle();f.idle(1,3);f.check_stable(old)
            assert f.get('se_e_error',1)==0x17 and f.get('se_f_error',1)==0x9B
            assert f.get('se_f_allocated',1)==0
            f.key(ord('K'));f.idle();f.check_stable(old)
        run('missing-C10-read-and-abort-admission-eventual-AUX-cleanup',missing_transport)

    assert hashlib.sha256((frozen/'build/editor.prg').read_bytes()).hexdigest()==identity
    output=dict(ok=True,partial=bool(args.only),admission_failure_paths=args.emergency,prg_sha256=identity,resident_binding=report['resident_binding']['digest'],
                cases=cases,complete_screen_oracles=screen_count,screen_cells=screen_count*1000,
                actual_root_actions=total_actions,modeled_KERNAL_calls=total_rom,
                max_file_service_instructions=max_service,
                frozen=str(frozen),scope='Actual twelve-asset editor/C8/C10/C11/C12/AUX CPU; KERNAL/DOS/D81 boundary modeled; not native IEC/physical keys')
    output_name='partial-result.json' if args.only else 'result.json'
    if not args.only:(ROOT/'build/editor-file-integration-result.json').write_text(json.dumps(output,indent=2)+'\n')
    (frozen/output_name).write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))


if __name__ == '__main__': main()
