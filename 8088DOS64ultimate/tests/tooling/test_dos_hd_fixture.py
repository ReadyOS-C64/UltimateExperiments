"""Fresh-owned-output and optional tool diagnostics; no external process creation."""
from pathlib import Path
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'build_support'))
import dos_hd_fixture as fixture


class FixtureSafetyTests(unittest.TestCase):
    def setUp(self):
        self.project=Path(os.environ.get('DOS64_PROJECT',PROJECT)).resolve()
        (self.project/'agentworking/runs').mkdir(parents=True,exist_ok=True)

    def rejected(self,*extra,tools=True):
        args=['dos_hd_fixture.py','--project',str(self.project),'--profile','small',*extra]
        with patch.object(sys,'argv',args),patch('shutil.which',return_value='/usr/bin/true' if tools else None):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                fixture.main()
        self.assertEqual(caught.exception.code,2)

    def test_no_tool_installation_required_clear_diagnostic(self):
        self.rejected(tools=False)

    def test_refuse_existing_output(self):
        self.rejected('--output',str(self.project/'agentworking/runs'))
        # Root itself and any existing child are rejected before process creation.
        with tempfile.TemporaryDirectory(prefix='fixture-safety-',dir=self.project/'agentworking/runs') as existing:
            self.rejected('--output',existing)

    def test_refuse_output_outside_owned_runs(self):
        self.rejected('--output',str(self.project/'build/new-fixture'))
        self.rejected('--output',str(self.project/'agentworking/runs/../outside'))

    def test_cross16_requires_large_profile(self):
        self.rejected('--cross16')

    def test_finite_stage_bounds(self):
        for value in ('0','181','nan','inf'):
            self.rejected('--timeout',value)

    def test_bad_project(self):
        self.rejected('--project',str(self.project/'build'))

    def test_reject_config_path_injection(self):
        self.rejected('--output',str(self.project/'agentworking/runs/bad\"name'))
        self.rejected('--output',str(self.project/'agentworking/runs/bad\nname'))

    def test_chkdsk_evidence_capacity(self):
        report={'bpb':{'sectors_per_cluster':8},'data_clusters':505}
        fixture.verify_chkdsk(b'  2068480 bytes total disk space\r\n  1970176 bytes available on disk\r\n',report)
        for text in (b'Bad command',b'1 bytes total disk space\r\n0 bytes available on disk\r\n',b'2068480 bytes total disk space\r\n1 bytes available on disk\r\n'):
            with self.assertRaises(ValueError):fixture.verify_chkdsk(text,report)

    def test_console_helpers_target_original_cpu(self):
        for name in ('keyfeed.asm','cross16.asm'):
            source=(fixture.BASE/'dos_fixture_assets'/name).read_text()
            self.assertTrue(source.startswith('cpu 8086\nbits 16\n'))
        self.assertNotIn('int 13h',(fixture.BASE/'dos_fixture_assets/keyfeed.asm').read_text().lower())


if __name__=='__main__':unittest.main(verbosity=2)
