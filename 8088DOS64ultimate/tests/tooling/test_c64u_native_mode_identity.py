"""Fast explicit synthetic proof-binding tests; no guest/device execution."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'build_support'))
import c64u_native_mode_identity as p
from c64u_native_display_application import keys


class Fixture:
    def __init__(self,root):
        self.root=root;self.directory=root/'proof';self.directory.mkdir()
        names=['src/video.s','src/cpu.s','src/native_runtime.s','src/render_text.s','src/render_graphics.s','include/video.inc','assets/native-text/cp437-narrow4x8.bin','assets/native-text/cp437-unscii8.bin','tests/host/native_builtin_workflows.zig']
        files={'build/dos64.prg':'a'*64,'build/dos64-tests.prg':'b'*64}
        for name in names:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(name.encode());files[name]=p.sha(target.read_bytes())
        self.manifest={'schema':1,'files':files};self.current=json.loads(json.dumps(self.manifest))
        self.bitmaps={40:bytes([64])*8000,80:bytes([128])*8000}
        self.report={'status':'passed','linked_prg_sha256':'b'*64,'mode_lane':True,'commands':['MODE CO40\r','MODE CO80\r'],'completed_commands':2,'pending_offset':0,'no_direct_cpu_steps_or_DOS_shortcuts':True,'source_sha256':'bca98992b476dfee95667b1edc9a71c255858e588c03edece04ad7237ca6ffdb','inputs':keys('\r\rMODE CO40\rMODE CO80\r'),'observations':[{'screen':{'mode':mode,'columns':columns,'row':0,'column':2,'text':'A>'+(' '*78)+'\n'+((' '*80+'\n')*24)},'native_bitmap_sha256':p.sha(self.bitmaps[columns])} for columns,mode in [(40,1),(80,3)]]}
    def save(self):
        bodies={'build_manifest':json.dumps(self.manifest).encode(),'report':json.dumps(self.report).encode(),'bitmap40':self.bitmaps[40],'bitmap80':self.bitmaps[80]}
        proof={'schema':1,'purpose':'genuine-native-dos-mode-proof','files':{}}
        for role,body in bodies.items():
            target=self.directory/role;target.write_bytes(body);proof['files'][role]={'path':role,'sha256':p.sha(body),'bytes':len(body)}
        self.path=self.directory/'mode-proof.json';self.path.write_text(json.dumps(proof));self.digest=p.sha(self.path.read_bytes())
    def load(self):return p.load_proof(self.path,self.digest,self.current,'a'*64,self.root)


class Tests(unittest.TestCase):
    def test_explicit_generic_build_pair_no_hash_allowlist(self):
        with tempfile.TemporaryDirectory() as temp:
            f=Fixture(Path(temp));f.save();proof=f.load()
            self.assertEqual(proof['runtime_sha256'],'a'*64);self.assertEqual(proof['executed_unit_sha256'],'b'*64)
            self.assertEqual([x['columns'] for x in proof['checkpoints']],[40,80])
    def test_reviewed_proof_hash_and_every_bound_input_detect_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            f=Fixture(Path(temp));f.save();f.digest='0'*64
            with self.assertRaisesRegex(ValueError,'proof SHA256'):f.load()
            for role in ('build_manifest','report','bitmap40','bitmap80'):
                f.save();target=f.directory/role;target.write_bytes(target.read_bytes()+b'!')
                with self.assertRaisesRegex(ValueError,'input changed'):f.load()
    def test_wrong_current_runtime_or_unit_and_changed_target_source_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            f=Fixture(Path(temp));f.save()
            for role in ('build/dos64.prg','build/dos64-tests.prg'):
                old=f.current['files'][role];f.current['files'][role]='c'*64
                with self.assertRaisesRegex(ValueError,'build pair'):f.load()
                f.current['files'][role]=old
            (f.root/'src/video.s').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'source cohort changed'):f.load()
    def test_non_native_incomplete_or_other_unit_report_is_rejected(self):
        fields=[('status','failed'),('linked_prg_sha256','c'*64),('mode_lane',False),('completed_commands',1),('pending_offset',1),('no_direct_cpu_steps_or_DOS_shortcuts',False),('commands',['MODE CO80\r']),('inputs',[])]
        with tempfile.TemporaryDirectory() as temp:
            f=Fixture(Path(temp));good=json.loads(json.dumps(f.report))
            for name,value in fields:
                f.report=json.loads(json.dumps(good));f.report[name]=value;f.save()
                with self.assertRaises(ValueError):f.load()
    def test_missing_short_out_of_order_or_stale_cursor_bitmap_proof_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            f=Fixture(Path(temp));good=json.loads(json.dumps(f.report))
            f.bitmaps[40]=bytes(7999);f.save()
            with self.assertRaisesRegex(ValueError,'bitmap is incomplete'):f.load()
            f.bitmaps[40]=bytes([64])*8000
            for transform in ('reverse','missing','stale','wrong_geometry'):
                f.report=json.loads(json.dumps(good))
                if transform=='reverse':f.report['observations'].reverse()
                if transform=='missing':f.report['observations'].pop()
                if transform=='stale':f.report['observations'][0]['screen']['column']=3
                if transform=='wrong_geometry':f.report['observations'][0]['screen']['mode']=3
                f.save()
                with self.assertRaisesRegex(ValueError,'ordered coherent'):f.load()
    def test_incomplete_source_cohort_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            f=Fixture(Path(temp));del f.manifest['files']['src/cpu.s'];f.save()
            with self.assertRaisesRegex(ValueError,'cohort is incomplete'):f.load()

if __name__=='__main__':unittest.main()
