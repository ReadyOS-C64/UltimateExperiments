"""Structural unit inputs are deliberately nonbootable, never genuine DOS fixtures."""
from pathlib import Path
import copy
import importlib.util
import json
import os
import struct
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'build_support'))
from dos_disk_inspect import Volume, chs_to_lba, decode_chs, inspect, lba_to_chs, read_volume_file, sha


def synthetic(width=12, hd=False):
    geometry = (128, 2, 16) if width == 12 else (640, 4, 16)
    total = geometry[0] * geometry[1] * geometry[2] - 16 if hd else (720 if width == 12 else 5000)
    spc = (8 if width == 12 else 4) if hd else (2 if width == 12 else 1)
    roots = 512 if hd else 112
    spf = (2 if width == 12 else 40) if hd else (2 if width == 12 else 20)
    v = bytearray(total * 512)
    v[3:11] = b'UNITTEST'
    struct.pack_into('<HBHBHHBH', v, 11, 512, spc, 1, 2, roots, total, 0xf8, spf)
    struct.pack_into('<HHI', v, 24, geometry[2], geometry[1], 16 if hd else 0)
    v[510:512] = b'\x55\xaa'
    def fat_set(cluster, value):
        for sector in (1, 1 + spf):
            pos = sector * 512 + (cluster * 2 if width == 16 else cluster * 3 // 2)
            if width == 16:
                struct.pack_into('<H', v, pos, value)
            else:
                prev = struct.unpack_from('<H', v, pos)[0]
                packed = ((prev & 0xf) | (value << 4)) if cluster & 1 else ((prev & 0xf000) | value)
                struct.pack_into('<H', v, pos, packed)
    fat_set(0, 0xff8 if width == 12 else 0xfff8)
    fat_set(1, 0xfff if width == 12 else 0xffff)
    fat_set(2, 0xfff if width == 12 else 0xffff)
    root = (1 + 2 * spf) * 512
    v[root:root+11] = b'HELLO   TXT'
    v[root+11] = 0x20
    struct.pack_into('<HI', v, root+26, 2, 5)
    data = root + ((roots * 32 + 511) // 512) * 512
    v[data:data+5] = b'hello'
    if not hd:
        return v, fat_set, root, data
    raw = bytearray(16 * 512) + v
    raw[510:512] = b'\x55\xaa'
    raw[446] = 0x80
    raw[450] = 1 if width == 12 else 4
    for pos, chs in ((447, (0,1,1)), (451, lba_to_chs(total+15,geometry))):
        c,h,s = chs
        raw[pos:pos+3] = bytes((h,s|((c>>2)&0xc0),c&255))
    struct.pack_into('<II', raw, 454, 16, total)
    return raw, geometry


class DiskTests(unittest.TestCase):
    def test_fat12_and_fat16_payloads(self):
        for width in (12,16):
            raw, _, _, _ = synthetic(width)
            v = Volume(raw)
            self.assertEqual(v.width,width)
            self.assertEqual(v.payloads,{'HELLO.TXT':b'hello'})
            self.assertEqual(read_volume_file(raw,'hello.txt'),b'hello')
            self.assertIsNone(read_volume_file(raw,'missing.txt'))

    def test_real_supplied_image_readonly(self):
        actual = Path(os.environ.get('DOS64_PROJECT', PROJECT))
        paths = sorted((actual/'reference').glob('*.img'))
        self.assertEqual(len(paths),3)
        expected = ['bca98992b476dfee95667b1edc9a71c255858e588c03edece04ad7237ca6ffdb','91a624fc448c1c423d159ae21f51cc416393d8e19a73d3858afc3af92af041c2','c69238c738bab18db840b5ae72b2470c0d594832d91103573a6d8273dce300e9']
        for path,digest in zip(paths,expected):
            before=path.read_bytes(); v=Volume(before)
            self.assertEqual(v.width,12)
            self.assertGreater(len(v.files),0)
            self.assertEqual(sha(path.read_bytes()),digest)
            self.assertEqual(before,path.read_bytes())

    def test_chs_roundtrip_all_supported_fixture_sectors(self):
        for geometry in ((128,2,16),(640,4,16)):
            for lba in range(geometry[0]*geometry[1]*geometry[2]):
                self.assertEqual(chs_to_lba(*lba_to_chs(lba,geometry),geometry),lba)
        self.assertEqual(decode_chs(bytes((0,0x81,0))),(512,0,1))
        self.assertEqual(chs_to_lba(512,0,1,(640,4,16))*512,0x1000000)

    def test_invalid_chs_geometry_lba(self):
        for geometry in ((0,2,16),(1025,2,16),(1,257,16),(1,2,64),(1,2)):
            with self.assertRaises(ValueError):lba_to_chs(0,geometry)
        for chs in ((-1,0,1),(640,0,1),(0,4,1),(0,0,0),(0,0,17)):
            with self.assertRaises(ValueError):chs_to_lba(*chs,(640,4,16))
        with self.assertRaises(ValueError):lba_to_chs(40960,(640,4,16))
        with self.assertRaises(ValueError):decode_chs(b'xx')

    def test_mbr_bpb_size_and_geometry_corruptions(self):
        for width in (12,16):
            raw,g=synthetic(width,True)
            self.assertEqual(inspect(raw,g)['fat_bits'],width)
            for offset,value in ((510,0),(446,0),(450,6),(454,255),(458,255),(449,127),(8192+19,0),(8192+24,17),(8192+28,0),(462,1)):
                b=bytearray(raw);b[offset]=value
                with self.subTest(width=width,offset=offset),self.assertRaises(ValueError):inspect(b,g)
            with self.assertRaises(ValueError):inspect(raw[:-512],g)

    def test_fat_mismatch_cycle_lost_bad_and_reserved(self):
        for width in (12,16):
            raw,setfat,_,_=synthetic(width)
            raw[516]^=1
            with self.assertRaises(ValueError):Volume(raw)
            for value in (2,0,1,(0xff0 if width==12 else 0xfff0)):
                raw,setfat,_,_=synthetic(width);setfat(2,value)
                with self.subTest(width=width,value=value),self.assertRaises(ValueError):Volume(raw)
            raw,setfat,_,_=synthetic(width);setfat(3,0xfff if width==12 else 0xffff)
            with self.assertRaises(ValueError):Volume(raw)
            raw,setfat,_,_=synthetic(width);setfat(3,0xff7 if width==12 else 0xfff7)
            self.assertEqual(Volume(raw).bad_clusters,[3])
            raw,setfat,_,_=synthetic(width);setfat(0,0)
            with self.assertRaises(ValueError):Volume(raw)

    def test_zero_length_overlong_and_duplicate(self):
        for width in (12,16):
            for length in (0,4097):
                raw,_,root,_=synthetic(width);struct.pack_into('<I',raw,root+28,length)
                with self.assertRaises(ValueError):Volume(raw)
            raw,_,root,_=synthetic(width);raw[root+32:root+64]=raw[root:root+32]
            with self.assertRaises(ValueError):Volume(raw)
            raw,_,root,_=synthetic(width);raw[root+11]=0x0f
            with self.assertRaises(ValueError):Volume(raw)

    def test_subdirectory_dot_parent_and_crosslink(self):
        raw,setfat,root,data=synthetic(12)
        raw[root:root+11]=b'SUB        ';raw[root+11]=0x10
        struct.pack_into('<I',raw,root+28,0)
        raw[data:data+64]=bytes(64)
        for offset,name,cluster in ((data,b'.          ',2),(data+32,b'..         ',0)):
            raw[offset:offset+11]=name;raw[offset+11]=0x10;struct.pack_into('<H',raw,offset+26,cluster)
        raw[data+64:data+75]=b'INNER   TXT';raw[data+75]=0x20
        struct.pack_into('<HI',raw,data+90,3,3);setfat(3,0xfff)
        raw[data+1024:data+1027]=b'yes'
        self.assertEqual(Volume(raw).payloads,{'SUB/INNER.TXT':b'yes'})
        b=bytearray(raw);struct.pack_into('<H',b,data+58,2)
        with self.assertRaises(ValueError):Volume(b)
        b=bytearray(raw);struct.pack_into('<H',b,data+90,2)
        with self.assertRaises(ValueError):Volume(b)
        b=bytearray(raw);b[data]=0xe5
        with self.assertRaises(ValueError):Volume(b)


if __name__=='__main__':unittest.main(verbosity=2)
