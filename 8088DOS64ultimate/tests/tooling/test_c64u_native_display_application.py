import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
PROJECT=Path(__file__).resolve().parents[2]
PROPOSAL=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROPOSAL/'build_support'))
sys.path.insert(1,str(PROJECT/'build_support'))
import c64u_native_display_application as d
import c64u_native_application as base
spec=importlib.util.spec_from_file_location('base_fixture',PROJECT/'tests/tooling/test_c64u_native_application.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
NARROW=(PROJECT/'assets/native-text'/d.FONT_NAMES[0]).read_bytes()
WIDE=(PROJECT/'assets/native-text'/d.FONT_NAMES[1]).read_bytes()


def fixture(columns=40,seed=7):
    bda=bytearray(256);bda[0x49]=1 if columns==40 else 3;bda[0x4a:0x4c]=columns.to_bytes(2,'little')
    bda[0x4c:0x4e]=(2048 if columns==40 else 4096).to_bytes(2,'little')
    bda[0x1a:0x1c]=bda[0x1c:0x1e]=b'\x1e\0';bda[0x50]=2
    cga=bytearray(16384)
    for i in range(columns*25):
        cga[i*2]=(i*37+seed)%256;cga[i*2+1]=(i*13+seed)%256
    cga[:4]=b'A\x07>\x07'
    return bda,cga


def authored_expected(bda,cga):
    columns=int.from_bytes(bda[0x4a:0x4c],'little');cga=cga[int.from_bytes(bda[0x4e:0x50],'little'):];bitmap=bytearray(8000);matrix=bytearray(1000)
    # Different traversal: native character rows, pixel rows, physical cells.
    pal=[0,6,5,3,2,4,9,15,12,14,13,3,10,4,7,1]
    for y in range(200):
        row=y//8;line=y%8
        for x in range(320):
            cell=x//8;slot=row*columns+(x//8 if columns==40 else x//4)
            ch=cga[slot*2];attr=cga[(row*columns+cell*(1 if columns==40 else 2))*2+1]
            if columns==40:bit=(WIDE[ch*8+line]>>(7-x%8))&1
            else:
                packed=NARROW[ch*4+line//2]
                glyph=(packed>>4) if line%2==0 else (packed&15)
                bit=(glyph>>(3-x%4))&1
            bitmap[row*320+cell*8+line]|=bit<<(7-x%8)
            matrix[row*40+cell]=(pal[attr&15]<<4)|pal[(attr>>4)&7]
    return bytes(bitmap),bytes(matrix)


class ModeFake(f.Fake):
    def __init__(self):
        self.columns=80;self.corrupt=None
        super().__init__()
    def command(self):
        if self.ram[0xea03]!=1:return super().command()
        key=int.from_bytes(self.ram[0xea05:0xea07],'little');self.keys.append(key);ch=chr(key&255);self.count+=100
        if self.phase=='date' and ch=='\r':self.phase='time'
        elif self.phase=='time' and ch=='\r':self.phase='prompt'
        elif self.phase=='prompt':
            if ch=='\r':
                if self.line=='MODE CO40':self.columns=40
                elif self.line=='MODE CO80':self.columns=80
                else:raise AssertionError(self.line)
                self.line=''
            else:self.line+=ch
        self.paint();self.ram[0xea04]=0xa5;self.ram[0xea03]=0
    def paint(self):
        bda,cga=fixture(self.columns)
        cga[:self.columns*50]=b' \x07'*(self.columns*25)
        if self.phase=='date':line='Enter new date (mm-dd-yy):'
        elif self.phase=='time':line='Enter new time:'
        else:line='A>'+self.line
        for i,ch in enumerate(line):cga[i*2]=ord(ch)
        bda[0x50]=len(line)
        self.reu[0x400:0x500]=bda;self.reu[0xb8000:0xbc000]=cga
        bitmap,matrix=authored_expected(bda,cga)
        self.ram[0x4400:0x4800]=NARROW;self.ram[0x4800:0x5000]=WIDE
        self.ram[0x6000:0x7f40]=bitmap;self.ram[0x4000:0x43e8]=matrix
        if self.corrupt and self.columns==40:self.ram[self.corrupt]^=1
        self.ram[0xe020:0xe024]=self.count.to_bytes(4,'little');self.ram[0xea40]=0


class Tests(unittest.TestCase):
    def app(self):
        clock=f.Clock()
        return d.DisplayApplication(f.PRG,f.LABELS,dict(f.MEDIA_RECORD),f.SOURCE,b'\x01\x08dummy',f.support.sha(f.PRG),clock=clock,sleep=clock.sleep)
    def test_independent_all_cells_glyphs_attributes_and_modes(self):
        for columns in (40,80):
            for seed in (0,7,91):
                bda,cga=fixture(columns,seed)
                screen,bitmap,matrix=d.text_oracle(bytes(bda),bytes(cga),NARROW,WIDE)
                self.assertEqual((bitmap,matrix),authored_expected(bda,cga))
                self.assertEqual(screen['columns'],columns)
    def test_complete_mock_protocol_has_two_full_coherent_checkpoints_before_helper(self):
        fake=ModeFake();app=self.app()
        with tempfile.TemporaryDirectory() as temp,patch.object(base,'Service',f.Evidence):
            out=Path(temp);result=app(fake,out)
            self.assertEqual(result['status'],'passed');self.assertEqual(len(fake.keys),22)
            self.assertEqual(result['script_result']['completed_columns'],[40,80])
            self.assertEqual(len(result['mode_checkpoints']),2)
            self.assertEqual(fake.events.count('helper_load'),1)
            self.assertEqual((out/'floppy-import-after.bin').read_bytes(),f.SOURCE.read_bytes())
            for columns in (40,80):
                proof=json.loads((out/f'mode-{columns}/proof.json').read_text())
                self.assertEqual(proof['status'],'passed');self.assertEqual(proof['compared_bitmap_bytes'],8000)
                self.assertEqual((out/f'mode-{columns}/host-64k.bin').stat().st_size,65536)
                self.assertEqual((out/f'mode-{columns}/cga-16k.bin').stat().st_size,16384)
            saved=json.loads((out/'application-result.json').read_text())
            self.assertEqual(saved['physical_script'],'genuine DOS MODE CO40 then MODE CO80')
    def test_stale_prompt_and_same_count_cannot_complete_mode(self):
        captures=[];script=d.ModeScript(captures.append)
        script.stage='co40';script.submitted_at=10
        screen={'text':'A>','prompt':True,'guest_instructions':10,'mode':1,'columns':40,'ring_used':0}
        self.assertEqual(script.observe(screen),[]);self.assertEqual(captures,[])
        screen['guest_instructions']=11;screen['columns']=80;screen['mode']=3
        self.assertEqual(script.observe(screen),[]);self.assertEqual(captures,[])
    def test_ring_capacity_and_invalid_pointers_fail_before_any_key(self):
        script=d.ModeScript(lambda _:None);script.stage='initial_prompt'
        with self.assertRaisesRegex(ValueError,'insufficient capacity'):
            script.observe({'text':'A>','prompt':True,'guest_instructions':1,'ring_used':7,'mode':3,'columns':80})
        self.assertEqual(script.history,[])
        fake=ModeFake();app=self.app()
        class BadPointer(ModeFake):
            def paint(self):
                super().paint();self.reu[0x41a]=0x1f
        with tempfile.TemporaryDirectory() as temp,patch.object(base,'Service',f.Evidence):
            fake=BadPointer()
            with self.assertRaisesRegex(ValueError,'ring pointers'):app(fake,Path(temp))
            self.assertEqual(fake.keys,[])
    def test_bitmap_matrix_and_font_corruption_retain_raw_capture_and_skip_helper(self):
        for address in (0x6000,0x4000,0x4400):
            fake=ModeFake();fake.corrupt=address;app=self.app()
            with tempfile.TemporaryDirectory() as temp,patch.object(base,'Service',f.Evidence):
                out=Path(temp)
                with self.assertRaisesRegex(ValueError,'differs|differ'):app(fake,out)
                self.assertTrue((out/'mode-40/host-64k.bin').exists())
                self.assertTrue((out/'mode-40/bda.bin').exists())
                self.assertTrue((out/'application-failure-before-reset.bin').exists())
                self.assertNotIn('helper_load',fake.events)
                self.assertEqual(json.loads((out/'application-result.json').read_text())['status'],'failed')
    def test_oracle_rejects_inconsistent_mode_page_lengths_and_cursor(self):
        bda,cga=fixture(40)
        for at,value in ((0x49,3),(0x4c,1),(0x4e,1),(0x62,8),(0x50,40)):
            bad=bytearray(bda);bad[at]=value
            with self.assertRaises(ValueError):d.text_oracle(bytes(bad),bytes(cga),NARROW,WIDE)
        with self.assertRaises(ValueError):d.text_oracle(bytes(bda),bytes(cga[:-1]),NARROW,WIDE)
    def test_unexpected_initial_mode_is_not_accepted_as_a_new_mode_command(self):
        script=d.ModeScript(lambda _:None);script.stage='initial_prompt'
        with self.assertRaisesRegex(ValueError,'begin in mode3'):
            script.observe({'text':'A>','prompt':True,'guest_instructions':1,'ring_used':0,'mode':1,'columns':40})
        self.assertEqual(script.history,[])
    def test_guest_count_change_between_coherent_reads_is_rejected(self):
        class Changing(ModeFake):
            def read(self,address,count):
                if address==0 and count==65536 and self.columns==40:
                    self.ram[0xe020]^=1
                return super().read(address,count)
        fake=Changing();app=self.app()
        with tempfile.TemporaryDirectory() as temp,patch.object(base,'Service',f.Evidence):
            with self.assertRaisesRegex(ValueError,'Guest changed'):app(fake,Path(temp))
            self.assertNotIn('helper_load',fake.events)
            self.assertTrue((Path(temp)/'mode-40/host-64k.bin').exists())
    def test_last_active_page_and_cursor_local_prompt_full_oracles(self):
        for columns,page in ((40,7),(80,3)):
            bda,cga=fixture(columns);offset=page*(2048 if columns==40 else 4096)
            cga[:columns*50]=b' \x07'*(columns*25)
            shifted=bytearray(16384);shifted[offset:offset+columns*50]=cga[:columns*50]
            position=offset+24*columns*2
            shifted[position:position+4]=b'A\x07>\x07'
            bda[0x62]=page;bda[0x4e:0x50]=offset.to_bytes(2,'little')
            bda[0x50+page*2]=2;bda[0x51+page*2]=24
            screen,bitmap,matrix=d.text_oracle(bytes(bda),bytes(shifted),NARROW,WIDE)
            self.assertTrue(screen['prompt']);self.assertEqual((bitmap,matrix),authored_expected(bda,shifted))
            bda[0x50+page*2]=3
            self.assertFalse(d.text_oracle(bytes(bda),bytes(shifted),NARROW,WIDE)[0]['prompt'])
    def test_optional_shared_observer_and_application_bounds_are_forwarded(self):
        app=d.DisplayApplication(f.PRG,f.LABELS,dict(f.MEDIA_RECORD),f.SOURCE,b'\x01\x08dummy',f.support.sha(f.PRG),seconds=360,observation_interval=2.0)
        self.assertEqual(app.seconds,360);self.assertEqual(app.observation_interval,2.0)
        for kw in ({'seconds':601},{'seconds':float('nan')},{'observation_interval':2.01},{'observation_interval':float('inf')}):
            with self.assertRaises(ValueError):d.DisplayApplication(f.PRG,f.LABELS,dict(f.MEDIA_RECORD),f.SOURCE,b'\x01\x08dummy',f.support.sha(f.PRG),**kw)
    def test_default_builtin_application_is_unchanged(self):
        self.assertIsNot(base.Application,d.DisplayApplication)
        self.assertEqual(base.Application(f.PRG,f.LABELS,dict(f.MEDIA_RECORD),f.SOURCE,b'\x01\x08dummy',f.support.sha(f.PRG)).script.result()['script'],'CR, CR, VER CR, DIR /P CR, SPACE per actual DOS pagination prompt')

if __name__=='__main__':unittest.main()
