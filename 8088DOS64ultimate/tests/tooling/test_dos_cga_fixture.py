from pathlib import Path
import sys,unittest,tempfile
from unittest.mock import patch
PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'build_support'))
from dos_cga_fixture import derive,SOURCE_SHA
from dos_disk_inspect import Volume,sha
from dos_cga_oracle import expected,verify
class CgaFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.original=(PROJECT/'reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img').read_bytes()
    def test_new_file_and_every_original_payload(self):
        raw,report=derive(self.original,b'\xcd\x20')
        self.assertEqual(sha(self.original),SOURCE_SHA)
        a,b=Volume(self.original),Volume(raw)
        self.assertEqual(b.payloads['CGAPROBE.COM'],b'\xcd\x20')
        self.assertEqual({n:b.payloads[n] for n in a.payloads},a.payloads)
        self.assertEqual(raw[:512],self.original[:512]);self.assertEqual(len(raw),368640)
        self.assertEqual(report['changed_sectors'],[1,3,7,574,575])
    def test_maximum_program_fills_one_cluster_and_mirrors(self):
        program=bytes(range(256))*5
        with self.assertRaises(ValueError):derive(self.original,program)
        program=bytes(range(256))*4
        raw,report=derive(self.original,program)
        self.assertEqual(Volume(raw).payloads['CGAPROBE.COM'],program)
        self.assertEqual(len(report['clusters']),1)
        self.assertEqual(raw[512:1536],raw[1536:2560])
    def test_source_and_size_rejection(self):
        for source,program in ((self.original[:-1],b'X'),(self.original,b''),(self.original,b'X'*1025)):
            with self.assertRaises(ValueError):derive(source,program)
    def test_all_foreground_pair_combinations_and_distinct_modes(self):
        for mode in (4,5,6):
            raw,bitmap,matrix,color,pairs=expected(mode)
            self.assertEqual((len(raw),len(bitmap),len(matrix)),(16384,8000,1000))
            self.assertEqual(len(pairs),4 if mode==6 else 16)
        self.assertNotEqual(expected(4)[1],expected(5)[1])
        self.assertNotEqual(expected(4)[2],expected(5)[2])
class CaptureOracleBdaTests(unittest.TestCase):
    """Host-verifier regression fixture; native identity is separately tested.

    Synthetic captures isolate the real verify() BDA checks. Only code_identity
    is substituted here; no target execution or target proof is claimed.
    """
    def setUp(self):
        scratch=PROJECT/'agentworking/scratch';scratch.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=scratch,prefix='cga-oracle-test-')
        self.addCleanup(self.temp.cleanup);self.directory=Path(self.temp.name)
        self.mock=patch('dos_cga_oracle.code_identity',return_value={'synthetic_unit_identity':True})
        self.mock.start();self.addCleanup(self.mock.stop)
        for mode in (4,5,6):
            raw,bitmap,matrix,colors,_=expected(mode)
            bda=bytearray(256);bda[0x49]=mode
            bda[0x4a:0x4c]=(80 if mode==6 else 40).to_bytes(2,'little')
            bda[0x4c:0x4e]=(0x4000).to_bytes(2,'little')
            bda[0x66]=0x3f if mode==6 else 0x30
            host=bytearray(65536);host[0x6000:0x7f40]=bitmap;host[0x4000:0x43e8]=matrix
            for name,data in (('cga',raw),('bitmap',bitmap),('matrix',matrix),('colors',colors or bytes(1000)),('bda',bda),('host',host)):
                (self.directory/f'cga-{mode}-{name}.bin').write_bytes(data)
    def rejects(self,offsets):
        for mode in (4,5,6):
            p=self.directory/f'cga-{mode}-bda.bin';original=p.read_bytes()
            for at in offsets:
                with self.subTest(mode=mode,offset=hex(at)):
                    bad=bytearray(original);bad[at]^=1;p.write_bytes(bad)
                    with self.assertRaisesRegex(ValueError,'BDA'):verify(self.directory)
                    p.write_bytes(original)
        self.assertEqual(verify(self.directory)['status'],'passed')
    def test_valid_complete_bda_contract_all_three_modes(self):
        self.assertEqual(verify(self.directory)['status'],'passed')
    def test_both_page_size_bytes_reject_all_modes(self):self.rejects((0x4c,0x4d))
    def test_both_display_offset_bytes_reject_all_modes(self):self.rejects((0x4e,0x4f))
    def test_palette_shadow_reject_all_modes(self):self.rejects((0x66,))
if __name__=='__main__':unittest.main()

