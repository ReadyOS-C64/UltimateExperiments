import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'build_support'))
import c64u_native_application as r
import c64u_native_application_support as support
SOURCE=ROOT/'reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img'
# Explicitly mocked fixture record; no ignored physical run is required.
MEDIA_RECORD={'status':'verified','source_sha256':support.SOURCE_SHA,'source_bytes':368640,
              'created_directory':True,'remote_readback_bytes':368640,'remote_readback_sha256':support.SOURCE_SHA,
              'original_source_unchanged':True,'source_crc32':813107767,
              'native_path':'/usb1/DOS64_TEST/mock-owned-run/DOS33A.IMG',
              'remote_directory':'/usb1/DOS64_TEST/mock-owned-run','marker_sha256':'a'*64}
PRG=b'\x01\x08'+bytes(32)+b'D64N\0\x04\x01\0\x1c\xdf\x37\x0a\x77\x30'+bytes(128)+bytes(8)
LABELS={'dos64_native_config':0x821,'dos64_native_config_end':0x821+142,'dos64_native_diag':0xea00,
        'dos64_native_diag_end':0xea13,'dos64_cpu_instructions':0xe020,'dos64_bios_waiting':0xea40}

class Clock:
    now=0
    def __call__(self):return self.now
    def sleep(self,seconds):self.now+=seconds

class Fake:
    def __init__(self):
        self.ram=bytearray(65536);self.reu=bytearray(4*1024*1024)
        self.reu[0x100000:0x100000+368640]=SOURCE.read_bytes()
        self.count=100;self.phase='date';self.line='';self.keys=[];self.events=[];self.started=False
        self.turbo={'Turbo Control':'Manual','CPU Speed':' 1'};self.truncate=False;self.fail_stage=False
        self.machine={'C64 and Cartridge Settings':{'Command Interface':'Enabled','RAM Expansion Unit':'Enabled','REU Size':'16 MB'}}
        self.oracle=support.Builtins(SOURCE.read_bytes());self.paused=False
    def get(self,route):
        if route=='configs/C64%20and%20Cartridge%20Settings':return self.machine
        if route.endswith('/CPU%20Speed'):return {'U64 Specific Settings':{'CPU Speed':{'values':[' 1','16','64']}}}
        if route=='configs/U64%20Specific%20Settings':return {'U64 Specific Settings':dict(self.turbo)}
        raise AssertionError(route)
    def configs(self,value):self.turbo.update(value['U64 Specific Settings'])
    def put(self,route):
        self.events.append(route)
        if route=='machine:pause':self.paused=True
        elif route=='machine:resume':
            self.paused=False
            if self.started and self.ram[0xea03]:self.command()
        else:raise AssertionError(route)
    def request(self,method,route,data,kind):
        if route=='runners:run_prg':
            self.ram[0x801:0x801+len(data)-2]=data[2:];self.started=True
            self.ram[0xea00]=0xe1 if self.fail_stage else 4
            self.ram[0xea01]=7 if self.fail_stage else 0
            self.paint();return
        assert self.paused
        address=int(route.split('=')[1],16);self.ram[address:address+len(data)]=data
    def read(self,address,count):
        if address==0 and count==65536:self.events.append('full_ram')
        data=bytes(self.ram[address:address+count])
        return data[:-1] if self.truncate and address==0xc100 else data
    def command(self):
        command=self.ram[0xea03]
        if command==2:self.ram[0xea00]=5
        elif command==3:self.ram[0xea00]=4
        elif command==4:
            assert self.ram[0xea00]==5
            address=int.from_bytes(self.ram[0xea0e:0xea11],'little');count=int.from_bytes(self.ram[0xea11:0xea13],'little')
            self.ram[0xc100:0xc100+count]=self.reu[address:address+count]
        elif command==1:
            assert self.ram[0xea00]==4
            key=int.from_bytes(self.ram[0xea05:0xea07],'little');self.keys.append(key);ch=chr(key&255)
            self.count+=100
            if self.phase=='date' and ch=='\r':self.phase='time'
            elif self.phase=='time' and ch=='\r':self.phase='prompt'
            elif self.phase in ('prompt','ver'):
                if ch=='\r':
                    if self.line=='VER':self.phase='ver'
                    elif self.line=='DIR /P':self.phase='first'
                    else:raise AssertionError(self.line)
                    self.line=''
                else:self.line+=ch
            elif self.phase=='first' and ch==' ':self.phase='last'
            self.paint()
        else:raise AssertionError(command)
        self.ram[0xea04]=0xa5;self.ram[0xea03]=0 # result before clear
    def paint(self):
        if self.phase=='date':lines=['Enter new date (mm-dd-yy):']
        elif self.phase=='time':lines=['Enter new time:']
        elif self.phase=='prompt':lines=['A>']
        elif self.phase=='ver':lines=['MS-DOS Version 3.30','A>']
        else:
            entries=list(self.oracle.entries.items())
            if self.phase=='first':lines=['Directory of  A:']+[name+f' {size}' for name,size in entries[:20]]+['Strike a key when ready . . . ']
            else:lines=[name+f' {size}' for name,size in entries[20:]]+[f'35 File(s) {self.oracle.expected_free} bytes free','A>']
        bda=bytearray(256);bda[0x49]=3;bda[0x4a]=80;bda[0x50]=len(lines[-1]);bda[0x51]=len(lines)-1
        video=bytearray(b' \x07'*2000)
        for row,line in enumerate(lines):
            for col,ch in enumerate(line):video[row*160+col*2]=ord(ch)
        self.reu[0x400:0x500]=bda;self.reu[0xb8000:0xb8000+4000]=video
        self.ram[0xe020:0xe024]=self.count.to_bytes(4,'little');self.ram[0xea40]=1

class Evidence:
    def __init__(self,client,*args,**kw):self.client=client
    def load(self):
        self.client.events.append('helper_load');self.client.ram[0x801]=0xfe
    def command(self,direction,address,count):
        assert direction==1
        return bytes(self.client.reu[address:address+count])

class Tests(unittest.TestCase):
    def app(self):
        clock=Clock()
        return r.Application(PRG,LABELS,dict(MEDIA_RECORD),SOURCE,b'\x01\x08dummy',support.sha(PRG),clock=clock,sleep=clock.sleep)
    def test_complete_mock_native_script_coherent_pages_then_capture_before_helper(self):
        fake=Fake();app=self.app()
        with tempfile.TemporaryDirectory() as d,patch.object(r,'Service',Evidence):
            report=app(fake,Path(d));self.assertEqual(report['status'],'passed')
            self.assertTrue(report['script_result']['accepted']);self.assertEqual(len(report['script_result']['seen_entries']),35)
            self.assertEqual(report['script_result']['pagination_keys'],1)
            self.assertEqual(len(fake.keys),14)
            self.assertTrue(report['coherent_final_guest']);self.assertTrue(report['floppy_original_unchanged'])
            self.assertLess(fake.events.index('full_ram'),fake.events.index('helper_load'))
            self.assertEqual((Path(d)/'application-ram-before-recovery.bin').read_bytes()[0x801],PRG[2])
            self.assertEqual((Path(d)/'floppy-import-after.bin').read_bytes(),SOURCE.read_bytes())
    def test_nonblocking_bios_polling_still_observes_prompts_and_feeds_keys(self):
        class PollingFake(Fake):
            def paint(self):
                super().paint()
                self.ram[0xea40]=0  # INT16 AH01 polling never raises AH00 wait.
        fake=PollingFake();app=self.app()
        with tempfile.TemporaryDirectory() as d,patch.object(r,'Service',Evidence):
            result=app(fake,Path(d))
            self.assertEqual(result['status'],'passed')
            self.assertTrue(result['script_result']['accepted'])
            self.assertEqual(len(result['script_result']['seen_entries']),35)
            self.assertEqual(len(fake.keys),14)
            self.assertGreaterEqual(result['elapsed_seconds'],0.25)
    def test_truncated_coherent_read_fails_and_retains_pre_reset_ram(self):
        fake=Fake();fake.truncate=True;app=self.app()
        with tempfile.TemporaryDirectory() as d,patch.object(r,'Service',Evidence):
            with self.assertRaisesRegex(ValueError,'Truncated native read-only staging'):app(fake,Path(d))
            result=json.loads((Path(d)/'application-result.json').read_text())
            self.assertEqual(result['status'],'failed');self.assertTrue((Path(d)/'application-failure-before-reset.bin').exists())
            self.assertNotIn('helper_load',fake.events)
    def test_native_failure_retains_diagnostic_without_loading_helper(self):
        fake=Fake();fake.fail_stage=True;app=self.app()
        with tempfile.TemporaryDirectory() as d,patch.object(r,'Service',Evidence):
            with self.assertRaisesRegex(RuntimeError,'Native startup/runtime failure'):app(fake,Path(d))
            self.assertNotIn('helper_load',fake.events)
            self.assertTrue((Path(d)/'application-failure-before-reset.bin').exists())
    def test_disabled_interface_fails_before_runtime_upload_or_turbo_change(self):
        fake=Fake();fake.machine['C64 and Cartridge Settings']['Command Interface']='Disabled';app=self.app()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'Command Interface'):app(fake,Path(d))
            self.assertFalse(fake.started);self.assertEqual(fake.turbo['CPU Speed'],' 1')
            self.assertFalse(json.loads((Path(d)/'application-preflight.json').read_text())['machine_settings_changed'])
    def test_resident_code_captured_identity_rejects_a_changed_byte(self):
        app=self.app();app.resident_segments=[{'name':'CODE','start':0x801,'length':32}]
        with tempfile.TemporaryDirectory() as d:
            app.output=Path(d);ram=bytearray(65536);ram[0x801:0x821]=PRG[2:34]
            self.assertTrue(app.verify_resident(bytes(ram))[0]['matches'])
            ram[0x810]^=1
            with self.assertRaisesRegex(ValueError,'Captured resident executable'):app.verify_resident(bytes(ram))
            evidence=json.loads((Path(d)/'captured-resident-identity.json').read_text())
            self.assertEqual(evidence[0]['first_difference_address'],0x810)
    def test_only_two_bounded_uci_operands_are_normalized(self):
        app=self.app();app.resident_segments=[{'name':'CODE','start':0x801,'length':32}]
        source=bytearray(app.prg);source[6:9]=b'\xad\xff\xff';source[12:15]=b'\x8d\xff\xff';app.prg=bytes(source)
        app.labels={**app.labels,'dos64_uci_upload_operand':0x806,'dos64_uci_drain_operand':0x80c,
                    'dos64_uci_command':0xc100,'dos64_uci_data':0xc480}
        with tempfile.TemporaryDirectory() as d:
            app.output=Path(d);ram=bytearray(65536);ram[0x801:0x821]=app.prg[2:34]
            ram[0x806:0x808]=(0xc101).to_bytes(2,'little');ram[0x80c:0x80e]=(0xc67f).to_bytes(2,'little')
            proof=app.verify_resident(bytes(ram))[0]
            self.assertTrue(proof['matches']);self.assertFalse(proof['raw_matches']);self.assertEqual(len(proof['mutable_operands']),2)
            ram[0x80c:0x80e]=(0xd000).to_bytes(2,'little')
            with self.assertRaisesRegex(ValueError,'Captured resident executable'):app.verify_resident(bytes(ram))
            ram[0x80c:0x80e]=(0xc67f).to_bytes(2,'little');ram[0x80b]=0xea
            with self.assertRaisesRegex(ValueError,'Captured resident executable'):app.verify_resident(bytes(ram))
            proof=json.loads((Path(d)/'captured-resident-identity.json').read_text())[0]
            self.assertEqual(proof['first_difference_address'],0x80b)
            ram[0x80b]=0x8d;ram[0x806:0x808]=b'\xff\xff';app.script.stage='done'
            with self.assertRaisesRegex(ValueError,'Captured resident executable'):app.verify_resident(bytes(ram))
    def test_final_source_read_failure_preserves_primary_native_failure(self):
        fake=Fake();fake.fail_stage=True;app=self.app()
        original=Path.read_bytes
        def broken(path):
            if path==SOURCE:raise OSError('final source read fault')
            return original(path)
        with tempfile.TemporaryDirectory() as d,patch.object(Path,'read_bytes',broken):
            with self.assertRaisesRegex(RuntimeError,'Native startup/runtime failure'):app(fake,Path(d))
            result=json.loads((Path(d)/'application-result.json').read_text())
            self.assertEqual(result['status'],'failed');self.assertIn('final_source_read_error',result)
            self.assertIn('Native startup/runtime failure',result['error'])
    def test_wrong_prg_identity_fails_before_any_actions(self):
        with self.assertRaises(ValueError):r.Application(PRG,LABELS,dict(MEDIA_RECORD),SOURCE,b'\x01\x08dummy','0'*64)

if __name__=='__main__':unittest.main()
