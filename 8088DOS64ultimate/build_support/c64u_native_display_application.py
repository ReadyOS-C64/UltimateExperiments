"""Genuine DOS MODE development workflow; import never contacts a device.

This is an opt-in subclass of the existing bounded native Application. DOS loads
the supplied MODE.COM. KEY is BIOS ring injection, not physical matrix input.
"""
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT/'build_support'))
from c64u_native_application import Application, STAGE_PAUSED
from c64u_bulk_reu_recovery import durable_write, dump
from c64u_native_application_support import decode_screen, sha

FONT_NAMES = ('cp437-narrow4x8.bin', 'cp437-unscii8.bin')
COLORS = (0, 6, 5, 3, 2, 4, 9, 15, 12, 14, 13, 3, 10, 4, 7, 1)
SCAN = {'M':0x32, 'O':0x18, 'D':0x20, 'E':0x12, ' ':0x39,
        'C':0x2e, '4':0x05, '0':0x0b, '8':0x09, '\r':0x1c}


def keys(text):
    return [(SCAN[c]<<8)|ord(c) for c in text]


def text_oracle(bda, cga, narrow, wide):
    """Independent complete cell/glyph oracle; SNAPSHOT makes blink visible.

    Derive geometry from the guest BDA, but reject inconsistent geometry before
    indexing. The 80-column shared cell palette comes from its left attribute.
    No renderer implementation or captured font is used as expected output.
    """
    if len(bda)!=256 or len(cga)!=16384 or len(narrow)!=1024 or len(wide)!=2048:
        raise ValueError('Exact BDA/CGA/font lengths required')
    mode=bda[0x49];columns=int.from_bytes(bda[0x4a:0x4c], 'little')
    if (mode,columns) not in ((1,40),(3,80)):
        raise ValueError('Expected genuine MODE CO40 or CO80 geometry')
    page=bda[0x62];page_size=0x800 if columns==40 else 0x1000
    offset=int.from_bytes(bda[0x4e:0x50],'little')
    if page>=16384//page_size or int.from_bytes(bda[0x4c:0x4e],'little')!=page_size or offset!=page*page_size:
        raise ValueError('Inconsistent active page/offset/size')
    video=cga[offset:offset+columns*50]
    screen=decode_screen(bda,video)
    bitmap=bytearray(8000);matrix=bytearray(1000)
    for row in range(25):
        for cell in range(40):
            left=(row*columns+cell*(1 if columns==40 else 2))*2
            ch,attr=video[left:left+2]
            matrix[row*40+cell]=(COLORS[attr&15]<<4)|COLORS[(attr>>4)&7]
            for y in range(8):
                if columns==40:bits=wide[ch*8+y]
                else:
                    right=video[left+2]
                    shift=4 if y%2==0 else 0
                    bits=(((narrow[ch*4+y//2]>>shift)&15)<<4)|((narrow[right*4+y//2]>>shift)&15)
                bitmap[row*320+cell*8+y]=bits
    return screen,bytes(bitmap),bytes(matrix)


class ModeScript:
    """Each submitted command fits the 15-key ring, checked coherently first."""
    def __init__(self,capture):
        self.stage='date';self.history=[];self.screens=[];self.initial_prompt=False
        self.completed=[];self.submitted_at=None;self.capture=capture
    def submit(self,screen,text,stage):
        used=screen['ring_used']
        if len(text)>15-used:raise ValueError('Coherent BIOS ring has insufficient capacity; no keys submitted')
        self.stage=stage;self.submitted_at=screen['guest_instructions']
        value=keys(text);self.history.extend(value);return value
    def observe(self,screen):
        self.screens.append(screen)
        text=screen['text']
        if self.stage=='date' and 'Enter new date (mm-dd-yy):' in text:
            return self.submit(screen,'\r','time')
        if self.stage=='time' and 'Enter new time:' in text:
            return self.submit(screen,'\r','initial_prompt')
        if self.stage=='initial_prompt' and screen['prompt']:
            if (screen['mode'],screen['columns'])!=(3,80):raise ValueError('Reviewed native DOS boot must begin in mode3/80 columns')
            self.initial_prompt=True
            return self.submit(screen,'MODE CO40\r','co40')
        if self.stage in ('co40','co80'):
            columns=40 if self.stage=='co40' else 80
            mode=1 if columns==40 else 3
            progressed=screen['guest_instructions']!=self.submitted_at
            if progressed and screen['prompt'] and (screen['mode'],screen['columns'])==(mode,columns):
                # Completing the capture/oracle is part of command acceptance.
                self.capture(columns)
                self.completed.append(columns)
                if columns==40:return self.submit(screen,'MODE CO80\r','co80')
                self.stage='done'
        return []
    def result(self):
        return {'accepted':self.stage=='done' and self.completed==[40,80], 'stage':self.stage,
                'initial_prompt':self.initial_prompt,'completed_columns':self.completed,
                'input_key_words':self.history,'script':'CR, CR, MODE CO40 CR, MODE CO80 CR',
                'input_kind':'native KEY to genuine BIOS ring; physical matrix untested',
                'screens':self.screens}


class DisplayApplication(Application):
    def __init__(self,*args,font_directory=None,**kw):
        super().__init__(*args,**kw)
        self.font_directory=Path(font_directory or PROJECT/'assets/native-text')
        self.fonts=tuple((self.font_directory/name).read_bytes() for name in FONT_NAMES)
        if tuple(map(len,self.fonts))!=(1024,2048):raise ValueError('Exact pinned text font assets required')
        self.script=ModeScript(self.capture_mode);self.checkpoints=[];self.current_bda=None
    def screen(self):
        result=super().screen()
        bda=self.read_paused(0x400,256)
        head=int.from_bytes(bda[0x1a:0x1c],'little');tail=int.from_bytes(bda[0x1c:0x1e],'little')
        if head not in range(0x1e,0x3e,2) or tail not in range(0x1e,0x3e,2):
            raise ValueError('Invalid coherent BIOS key ring pointers')
        result['ring_used']=((tail-head)%32)//2
        self.current_bda=bda
        return result
    def capture_mode(self,columns):
        self.bound()
        if self.diag()[0]!=STAGE_PAUSED:raise ValueError('Mode checkpoint requires coherent PAUSED runtime')
        directory=self.output/f'mode-{columns}'
        directory.mkdir(exist_ok=False)
        bda=self.read_paused(0x400,256);cga=self.read_paused(0xb8000,16384)
        durable_write(directory/'bda.bin',bda);durable_write(directory/'cga-16k.bin',cga)
        ram_sha=self.capture_ram(f'mode-{columns}/host-64k.bin')
        ram=(directory/'host-64k.bin').read_bytes()
        # Save every raw observation before any validation can fail.
        captured_count=int.from_bytes(ram[self.labels['dos64_cpu_instructions']:self.labels['dos64_cpu_instructions']+4],'little')
        if bda!=self.current_bda or captured_count!=self.script.screens[-1]['guest_instructions']:
            raise ValueError('Guest changed across coherent MODE checkpoint reads')
        identity=self.verify_resident(ram)
        dump(directory/'resident-identity.json',identity)
        narrow,wide=self.fonts
        if ram[0x4400:0x4800]!=narrow or ram[0x4800:0x5000]!=wide:
            raise ValueError('Captured native font bytes differ from pinned source assets')
        screen,bitmap,matrix=text_oracle(bda,cga,narrow,wide)
        durable_write(directory/'expected-bitmap.bin',bitmap);durable_write(directory/'expected-matrix.bin',matrix)
        actual_bitmap=ram[0x6000:0x7f40];actual_matrix=ram[0x4000:0x43e8]
        proof={'status':'checking','columns':columns,'mode':screen['mode'],
               'guest_instructions':captured_count,
               'host_ram_sha256':ram_sha,'bda_sha256':sha(bda),'cga_sha256':sha(cga),
               'bitmap_sha256':sha(actual_bitmap),'expected_bitmap_sha256':sha(bitmap),
               'matrix_sha256':sha(actual_matrix),'expected_matrix_sha256':sha(matrix),
               'compared_bitmap_bytes':8000,'compared_matrix_bytes':1000,
               'font_assets':{name:sha(body) for name,body in zip(FONT_NAMES,self.fonts)},
               'returned_prompt':screen['prompt'],'limitations':['RAM evidence; no external VIC/HDMI capture','Native BIOS keys; no physical matrix input','No physical readability approval']}
        failures=[]
        for name,expected,actual in [('bitmap',bitmap,actual_bitmap),('matrix',matrix,actual_matrix)]:
            if actual!=expected:failures.append({'name':name,'first_difference':next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b)})
        if screen['columns']!=columns or not screen['prompt']:failures.append({'name':'expected mode/prompt'})
        proof['status']='failed' if failures else 'passed';proof['failures']=failures
        dump(directory/'proof.json',proof)
        if failures:raise ValueError('Native MODE framebuffer differs from independent complete oracle: '+repr(failures))
        self.checkpoints.append(proof)
        self.journal('mode_checkpoint_accepted',columns=columns,bitmap_sha256=proof['bitmap_sha256'])
    def __call__(self,client,output):
        output=Path(output)
        extra={str(Path(__file__).resolve()):sha(Path(__file__).read_bytes())}
        extra.update({str(self.font_directory/name):sha(body) for name,body in zip(FONT_NAMES,self.fonts)})
        dump(output/'display-source-identities.json',extra)
        try:
            result=super().__call__(client,output)
            result['physical_script']='genuine DOS MODE CO40 then MODE CO80'
            result['mode_checkpoints']=self.checkpoints
            result['external_capture']='not attempted; explicit known stream ownership required'
            return result
        finally:
            path=output/'application-result.json'
            if path.exists():
                record=json.loads(path.read_text());record['physical_script']='genuine DOS MODE CO40 then MODE CO80'
                record['mode_checkpoints']=self.checkpoints
                record['external_capture']='not attempted; explicit known stream ownership required'
                dump(path,record)
