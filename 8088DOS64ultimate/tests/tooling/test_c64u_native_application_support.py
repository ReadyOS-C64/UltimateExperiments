import json
from pathlib import Path
import sys
import unittest
import zlib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'build_support'))
import c64u_native_application_support as s
SOURCE=ROOT/'reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img'

class Tests(unittest.TestCase):
    def test_actual_source_and_verified_fixture_scope(self):
        record={'status':'verified','source_sha256':s.SOURCE_SHA,'source_bytes':368640,'created_directory':True,
                'remote_readback_bytes':368640,'remote_readback_sha256':s.SOURCE_SHA,'original_source_unchanged':True,
                'source_crc32':zlib.crc32(SOURCE.read_bytes()),'native_path':'/usb1/DOS64_TEST/new-run/DOS33A.IMG',
                'remote_directory':'/usb1/DOS64_TEST/new-run','marker_sha256':'a'*64}
        data,path=s.verified_media(record,SOURCE);self.assertEqual(len(data),368640)
        for field,value in [('status','mock'),('created_directory',False),('native_path','/usb1/existing.img'),('source_crc32',0),('marker_sha256','')]:
            wrong={**record,field:value}
            with self.assertRaises(ValueError):s.verified_media(wrong,SOURCE)
    def test_patch_only_owned_path_crc_enabled(self):
        fields={'size':140,'enabled':4,'path_length':7,'expected_crc':8,'path':12,'path_capacity':128}
        prg=b'\x01\x08'+b'prefix!' + b'D64N\x00\x04\x01\x00'+bytes(132)+b'trailer!'
        addr=0x801+7
        out,report=s.patch_config(prg,addr,fields,'/usb1/DOS64_TEST/new/DOS33A.IMG',12345)
        self.assertEqual(out[:2+7],prg[:2+7]);self.assertEqual(out[-8:],prg[-8:]);self.assertEqual(out[2+7+5:2+7+7],b'\x04\x01')
        self.assertEqual(len(out),len(prg));self.assertNotEqual(report['base_prg_sha256'],report['patched_prg_sha256'])
        with self.assertRaises(ValueError):s.patch_config(out,addr,fields,'x',12345)
    def test_decode_screen_needs_exact_coherent_parts(self):
        bda=bytearray(256);bda[0x49]=3;bda[0x4a]=80;bda[0x50]=2;bda[0x51]=24
        video=bytearray(b' \x07'*2000);video[24*160:24*160+4]=b'A\x07>\x07'
        screen=s.decode_screen(bytes(bda),bytes(video));self.assertTrue(screen['prompt'])
        with self.assertRaises(ValueError):s.decode_screen(bytes(bda),bytes(video[:-1]))
    def test_genuine_dir_p_script_accumulates_all_thirty_five_oracle_entries(self):
        state=s.Builtins(SOURCE.read_bytes())
        def screen(text,prompt=False):return {'text':text,'prompt':prompt,'cursor_row':len(text.splitlines())-1,'cursor_column':len(text.splitlines()[-1])}
        self.assertEqual(state.observe(screen('Enter new date (mm-dd-yy):')),[0x1c0d])
        self.assertEqual(state.observe(screen('Enter new time:')),[0x1c0d])
        self.assertEqual(len(state.observe(screen('A>',True))),4)
        self.assertEqual(len(state.observe(screen('MS-DOS Version 3.30\nA>',True))),7)
        entries=list(state.entries.items());self.assertEqual(len(entries),35)
        first='Directory of  A:\n'+'\n'.join(name+f' {size}' for name,size in entries[:20])+'\nStrike a key when ready . . . '
        self.assertEqual(state.observe(screen(first)),[0x3920]);self.assertEqual(state.observe(screen(first)),[])
        self.assertEqual(state.observe(screen(first+'\nLABEL    COM     2346')),[])
        last='\n'.join(name+f' {size}' for name,size in entries[20:])+f'\n35 File(s) {state.expected_free} bytes free\nA>'
        self.assertEqual(state.observe(screen(last,True)),[]);self.assertTrue(state.result()['accepted'])
        self.assertEqual(state.pages,1)

    def test_complete_directory_without_actual_pagination_is_not_accepted(self):
        state=s.Builtins(SOURCE.read_bytes())
        def screen(text,prompt=False):return {'text':text,'prompt':prompt,'cursor_row':len(text.splitlines())-1,'cursor_column':len(text.splitlines()[-1])}
        for text,prompt in [('Enter new date (mm-dd-yy):',False),('Enter new time:',False),('A>',True),('MS-DOS Version 3.30\nA>',True)]:
            state.observe(screen(text,prompt))
        entries=list(state.entries.items())
        state.observe(screen('Directory of  A:\n'+'\n'.join(name+f' {size}' for name,size in entries[:20])))
        state.observe(screen('\n'.join(name+f' {size}' for name,size in entries[20:])+f'\n35 File(s) {state.expected_free} bytes free\nA>',True))
        self.assertEqual(len(state.seen),35)
        self.assertTrue(state.summary)
        self.assertEqual(state.pages,0)
        self.assertFalse(state.result()['accepted'])

if __name__=='__main__':unittest.main()
