"""Standalone source-package build and exact artifact contracts; no device I/O."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

PROJECT=Path(__file__).resolve().parents[2]
SOURCES=['floppy_export_fixture','floppy_export','reu','uci','files']
EXPECTED='556e61c4a25264d9762446c23cd5dd29ad0300566ab8e6641b986e14a11eeb1f'

class StandaloneExportPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='dos64-floppy-export-')
        cls.root=Path(cls.temp.name)
        inputs=['build_support/build_floppy_export.py','cfg/dos64-floppy-export.cfg',*[f'src/{n}.s' for n in SOURCES],*[f'include/{n}' for n in ['abi.inc','reu.inc','uci.inc','files.inc','floppy_export.inc']]]
        for name in inputs:
            dest=cls.root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(PROJECT/name,dest)
        subprocess.run(['python3',str(cls.root/'build_support/build_floppy_export.py')],check=True,capture_output=True,text=True)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def manifest(self):return json.loads((self.root/'build/dos64-floppy-export.json').read_text())
    def test_clean_checkout_reproduces_disabled_prg(self):
        prg=(self.root/'build/dos64-floppy-export.prg').read_bytes()
        self.assertEqual(EXPECTED,hashlib.sha256(prg).hexdigest());self.assertEqual(3817,len(prg))
        self.assertEqual(b'\x01\x08',prg[:2]);self.assertEqual(b'\x4c\x0d\x08',prg[14:17])
    def test_all_manifest_inputs_and_outputs_exact(self):
        for field in ('sources','outputs'):
            for name,record in self.manifest()[field].items():
                data=(self.root/name).read_bytes();self.assertEqual(record['bytes'],len(data));self.assertEqual(record['sha256'],hashlib.sha256(data).hexdigest())
    def test_actual_linker_budget_is_standalone(self):
        text=(self.root/'build/dos64-floppy-export.map').read_text()
        self.assertIn('Size=0004F1',text);self.assertIn('Size=0000A4',text)
        self.assertIn('00EA00  00EAE6  0000E7',text);self.assertIn('000020  000023  000004',text)
    def test_deleted_product_is_rebuilt(self):
        product=self.root/'build/dos64-floppy-export.prg';product.unlink()
        subprocess.run(['python3',str(self.root/'build_support/build_floppy_export.py')],check=True,capture_output=True,text=True)
        self.assertEqual(EXPECTED,hashlib.sha256(product.read_bytes()).hexdigest())
    def test_normal_registration_and_no_scratch_dependencies(self):
        module=(PROJECT/'tests/floppy_export/build.zig').read_text()
        self.assertNotIn('standardTargetOptions',module);self.assertIn('add(b:*std.Build,target:std.Build.ResolvedTarget)',module)
        for name in ['build_support/build_floppy_export.py','build_support/floppy_export.mk','tests/floppy_export/actual_assembly.zig','tests/floppy_export/build.zig']:
            self.assertNotIn('agentworking/scratch',(PROJECT/name).read_text())
        rules=(PROJECT/'build_support/floppy_export.mk').read_text();self.assertIn('.PHONY: floppy-export test-floppy-export',rules)

if __name__=='__main__':unittest.main()
