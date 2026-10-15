import ftplib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('media', ROOT/'build_support/c64u_media_fixture.py')
media = importlib.util.module_from_spec(spec)
spec.loader.exec_module(media)


class FTP:
    def __init__(self, bad=None):
        self.directories = {media.BASE}
        self.files = {}
        self.calls = []
        self.bad = bad
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def mkd(self, path):
        self.calls.append(('mkdir', path))
        if path in self.directories: raise ftplib.error_perm('550 already exists')
        if self.bad == 'permission': raise ftplib.error_perm('550 refused')
        self.directories.add(path)
    def cwd(self, path):
        if path not in self.directories: raise ftplib.error_perm('550 absent')
    def storbinary(self, command, stream):
        path = command.removeprefix('STOR ')
        self.calls.append(('store', path))
        self.files[path] = stream.read()
    def retrbinary(self, command, consume):
        path = command.removeprefix('RETR ')
        data = self.files[path]
        if self.bad == 'marker' and path.endswith(media.MARKER): data += b'!'
        if self.bad == 'image' and path.endswith(media.LEAF): data = data[:-1]
        consume(data)


class MediaFixture(unittest.TestCase):
    def fixture(self):
        directory = ROOT/'agentworking/scratch/media-fixture-tests'
        directory.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=directory)
    def source(self, root):
        path = Path(root)/'original.img'
        path.write_bytes(bytes(range(256))*1440)
        return path, media.digest(path.read_bytes())
    def test_fresh_owned_copy_is_verified_and_original_untouched(self):
        with self.fixture() as root:
            source, digest = self.source(root)
            ftp = FTP()
            result = media.prepare_media(lambda: ftp, source, 'dosboot-test', Path(root)/'out', digest)
            self.assertEqual(result['status'], 'verified')
            self.assertEqual(media.digest(source.read_bytes()), digest)
            self.assertEqual(ftp.files[result['native_path']], source.read_bytes())
            self.assertTrue(result['original_source_unchanged'])
            self.assertEqual(len([c for c in ftp.calls if c[0] == 'store']), 2)
    def test_existing_run_or_permission_failure_never_overwrites(self):
        for bad in ('existing', 'permission'):
            with self.subTest(bad=bad), self.fixture() as root:
                source, digest = self.source(root)
                ftp = FTP(bad)
                if bad == 'existing': ftp.directories.add(media.BASE+'/dosboot-test')
                ftp.files[media.BASE+'/dosboot-test/'+media.LEAF] = b'prior'
                before = dict(ftp.files)
                result = media.prepare_media(lambda: ftp, source, 'dosboot-test', Path(root)/'out', digest)
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(ftp.files, before)
                self.assertFalse(any(c[0] == 'store' for c in ftp.calls))
    def test_corrupt_marker_or_image_keeps_failure_evidence(self):
        for bad in ('marker', 'image'):
            with self.subTest(bad=bad), self.fixture() as root:
                source, digest = self.source(root)
                out = Path(root)/'out'
                result = media.prepare_media(lambda: FTP(bad), source, 'dosboot-test', out, digest)
                self.assertEqual(result['status'], 'failed')
                self.assertTrue(result['created_directory'])
                self.assertEqual(json.loads((out/'media-fixture.json').read_text())['status'], 'failed')
                self.assertEqual(media.digest(source.read_bytes()), digest)
    def test_bad_path_source_or_mixed_evidence_reject_before_connect(self):
        with self.fixture() as root:
            source, digest = self.source(root)
            def forbidden(): raise AssertionError('network attempted')
            for run_id, expected in (('../escape', digest), ('bad\r\nSTOR', digest), ('ok', '0'*64)):
                with self.subTest(run_id=run_id), self.assertRaises(ValueError):
                    media.prepare_media(forbidden, source, run_id, Path(root)/'out', expected)
            out = Path(root)/'out';out.mkdir();(out/'prior').write_text('preserve')
            with self.assertRaises(ValueError): media.prepare_media(forbidden, source, 'ok', out, digest)
