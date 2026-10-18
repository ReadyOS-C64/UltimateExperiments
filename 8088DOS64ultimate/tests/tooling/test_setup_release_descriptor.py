import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CACHE=ROOT/'agentworking/scratch'/('setup-release-source-cache-'+str(os.getpid()))
if CACHE.exists():raise RuntimeError('Source-only cache path must remain absent before project import')
sys.dont_write_bytecode=True;sys.pycache_prefix=str(CACHE)
sys.path.insert(0,str(ROOT/'build_support'))
from setup_release_descriptor import descriptor


def fixture():
    # Synthetic metadata fixture; none of this is executed as the emulator.
    image=bytearray(0xb801);image[:2]=b'\x01\x08'
    symbols={'dos64_native_start':0x3000,'dos64_native_loop':0x3003,
             'dos64_native_idle':0x3006,'dos64_native_nmi':0x5882,
             'dos64_native_config':0x7000,'dos64_native_config_end':0x708e,
             'hdc_config':0x7200,'hdc_config_end':0x728c,
             'dos64_loader_required':0x3fe0}
    for name,data in [('dos64_native_nmi',b'\x40'),('dos64_native_config',b'D64N\0'),('hdc_config',b'D64H\0')]:
        at=symbols[name]-0x0801+2;image[at:at+len(data)]=data
    labels=''.join(f'al {at:06X} .{name}\n' for name,at in symbols.items())
    return bytes(image),labels


class SetupReleaseDescriptor(unittest.TestCase):
    def test_exact_release_and_descriptor_checksums(self):
        image,labels=fixture();out=descriptor(image,labels)
        self.assertEqual(len(out),64);self.assertEqual(out[:8],b'D64L\x01\x01\x40\0')
        self.assertEqual(struct.unpack_from('<II',out,8),(len(image),zlib.crc32(image)))
        self.assertEqual(struct.unpack_from('<I',out,60)[0],zlib.crc32(out[:60]))
        self.assertEqual(struct.unpack_from('<III',out,28),(0x6801,0x6a01,0x37e1))

    def test_required_exports_and_private_label_scopes(self):
        image,labels=fixture()
        self.assertEqual(descriptor(image,labels+'al 001000 .@same\nal 002000 .@same\n'),descriptor(image,labels))
        with self.assertRaisesRegex(ValueError,'missing native handoff'):
            descriptor(image,'\n'.join(l for l in labels.splitlines() if 'dos64_loader_required' not in l))
        with self.assertRaisesRegex(ValueError,'conflicting symbol'):
            descriptor(image,labels+'al 003001 .dos64_native_start\n')

    def test_wrong_payload_template_and_symbol_bounds(self):
        image,labels=fixture()
        for at in [0,0x5882-0x0801+2,0x7000-0x0801+2+4,0x7200-0x0801+2+4,0x3fe0-0x0801+2]:
            bad=bytearray(image);bad[at]^=1
            with self.assertRaises(ValueError):descriptor(bytes(bad),labels)
        for old,new in [('003000 .dos64_native_start','004000 .dos64_native_start'),
                        ('00728C .hdc_config_end','00728B .hdc_config_end'),
                        ('007200 .hdc_config','007000 .hdc_config')]:
            with self.assertRaises(ValueError):descriptor(image,labels.replace(old,new))
        with self.assertRaises(ValueError):descriptor(image+b'\0',labels)

    def test_rejected_CLI_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'main.prg').write_bytes(b'bad');(p/'main.labels').write_text('');(p/'DOS64.REL').write_bytes(b'previous')
            r=subprocess.run([sys.executable,str(ROOT/'build_support/setup_release_descriptor.py'),
                '--prg',str(p/'main.prg'),'--labels',str(p/'main.labels'),'--output',str(p/'DOS64.REL')],capture_output=True)
            self.assertNotEqual(r.returncode,0);self.assertEqual((p/'DOS64.REL').read_bytes(),b'previous')


if __name__=='__main__':unittest.main()
