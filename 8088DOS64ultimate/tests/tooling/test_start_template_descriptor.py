"""Host metadata checks; native stream/entry proofs are separate Peddle tests."""
from pathlib import Path
import importlib.util
import struct
import os
import sys
import unittest
import zlib

ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.pycache_prefix=str(ROOT/'build'/('.absent-start-template-test-'+str(os.getpid())))
if Path(sys.pycache_prefix).exists():raise RuntimeError('Source-only test cache prefix must remain absent')
spec=importlib.util.spec_from_file_location('start_template_descriptor',ROOT/'build_support/start_template_descriptor.py')
codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)

class TemplateDescriptor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder=ROOT/'build/start'
        if not all((folder/n).exists() for n in ['START.PRG','START.labels','START.map']):
            raise unittest.SkipTest('Build the native START template first: make start-template')
        cls.prg=(folder/'START.PRG').read_bytes()
        cls.descriptor=codec.make(cls.prg,(folder/'START.labels').read_text(),(folder/'START.map').read_text())

    def test_patch_changes_only_initialized_control_and_retains_original(self):
        source=self.prg;facts=codec.validate(self.descriptor,source);offset=facts['control_offset']
        for base in [0xdf1c,0xde1c,0xdffc]:
            configured=codec.patch(self.descriptor,source,b'/usb1/My DOS',base)
            self.assertEqual(configured[:offset],source[:offset]);self.assertEqual(configured[offset+131:],source[offset+131:])
            self.assertEqual(configured[offset:offset+3],b'\xa5'+struct.pack('<H',base))
            self.assertEqual(configured[offset+3:offset+131],b'/usb1/My DOS'.ljust(128,b'\0'))
        self.assertEqual(source[offset:offset+131],codec.DEFAULT)

    def test_every_template_and_descriptor_byte_is_bound(self):
        for n in range(len(self.prg)):
            changed=bytearray(self.prg);changed[n]^=1
            with self.assertRaises(ValueError):codec.validate(self.descriptor,changed)
        for n in range(64):
            changed=bytearray(self.descriptor);changed[n]^=1
            with self.assertRaises(ValueError):codec.validate(changed,self.prg)

    def test_signed_bounds_defaults_and_canonical_home_refuse(self):
        for at,fmt,value in [(24,'I',0xffffffff),(28,'I',0xffffffff),(32,'H',1),(22,'H',130),(34,'B',1),(43,'B',1)]:
            changed=bytearray(self.descriptor);struct.pack_into('<'+fmt,changed,at,value);struct.pack_into('<I',changed,60,zlib.crc32(changed[:60]))
            with self.assertRaises(ValueError):codec.validate(changed,self.prg)
        for home in [b'/',b'/a/../b',b'/a//b',b'/a.',b'/a ',b'/'+b'x'*117,b'/a\0hidden']:
            with self.assertRaises(ValueError):codec.patch(self.descriptor,self.prg,home)
        configured=codec.patch(self.descriptor,self.prg,b'/'+b'x'*116)
        self.assertEqual(len(configured),len(self.prg))

if __name__=='__main__':unittest.main()
