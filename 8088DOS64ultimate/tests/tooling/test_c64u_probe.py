"""Workflow fault tests; target DMA behavior is tested separately in Peddle."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"build_support"))
from c64u_probe import restore_image, validate_probe, run_matrix, speed_option


class FakeClient:
    def __init__(self, project, fail_speed=None):
        self.project=project;self.fail_speed=fail_speed
        self.original=bytes((i*13+5)&255 for i in range(2048))
        self.reu=self.original;self.ram=bytes(2048)
        self.turbo={"Turbo Control":"C64U Turbo Registers","CPU Speed":"64"}
        self.state="original";self.actions=[]

    def get(self, route):
        if route=="info":return {"product":"owned fake"}
        if route.endswith("/Turbo%20Control"):return {"U64 Specific Settings":{"Turbo Control":{"values":["Off","Manual","C64U Turbo Registers"]}}}
        if route.endswith("/CPU%20Speed"):return {"U64 Specific Settings":{"CPU Speed":{"values":[" 1","16","64"]}}}
        if route=="configs/U64%20Specific%20Settings":return {"U64 Specific Settings":copy.deepcopy(self.turbo)}
        if route=="configs/C64%20and%20Cartridge%20Settings":return {"C64 and Cartridge Settings":{"RAM Expansion Unit":"Enabled","REU Size":"16 MB"},"errors":[]}
        if route=="drives":return {"drives":[{"a":{"image_file":"unchanged.d81","enabled":True}}],"errors":[]}
        raise AssertionError(route)

    def put(self, route):self.actions.append(route)
    def configs(self, value):
        if value["U64 Specific Settings"]["CPU Speed"] not in (" 1","16","64"):
            raise ValueError("Fake firmware rejects unadvertised/unpadded speed value")
        self.turbo.update(value["U64 Specific Settings"])
    def read(self, address, length):
        if address==0:return bytes(65536)
        if address==0x6000:
            data=self.ram[:length]
            if length==1536 and self.state=="probe" and str(self.turbo["CPU Speed"]).strip()==str(self.fail_speed):
                data=bytes([data[0]^1])+data[1:]
            return data
        raise AssertionError((address,length))

    def run(self, prg, mailbox, executable_length=None):
        self.actions.append("run")
        if prg==(self.project/"build/dos64-backup.prg").read_bytes():
            self.state="backup";self.ram=self.reu
        elif prg==(self.project/"build/dos64-cache-probe.prg").read_bytes():
            self.state="probe";self.ram=bytes((i&255)^(i>>8)^0xa7 for i in range(1536))
            self.reu=self.reu[:256]+self.ram+self.reu[1792:]
        else:
            self.state="restore";self.reu=prg[2+0x6000-0x801:];self.ram=bytes(2048)
        return bytes([1,0xa5,0,0,0,0,0,0])


class HardwareWorkflow(unittest.TestCase):
    def setUp(self):
        self.project=Path.cwd()
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)

    def test_restore_prg_keeps_code_and_places_exact_backup_at_6000(self):
        base=bytes([1,8,0x4c,1,8]);backup=bytes(range(256))*8
        image=restore_image(base,backup)
        self.assertEqual(image[:len(base)],base)
        self.assertEqual(image[2+0x6000-0x801:],backup)
        with self.assertRaises(ValueError):restore_image(base,backup[:-1])

    def test_speed_mapping_preserves_firmware_padding(self):
        self.assertEqual(speed_option([" 1","16","64"],1)," 1")
        with self.assertRaises(ValueError):speed_option(["16","64"],1)

    def test_mailbox_cannot_hide_corrupted_physical_readback(self):
        data=bytes((i&255)^(i>>8)^0xa7 for i in range(1536))
        validate_probe(data,bytes([1,0xa5,0,0,0,0,0,0]))
        with self.assertRaises(ValueError):validate_probe(b"\0"*1536,bytes([1,0xa5,0,0,0,0,0,0]))

    def test_success_restores_reu_and_prior_turbo_and_media(self):
        c=FakeClient(self.project)
        r=run_matrix(c,self.project,Path(self.temp.name))
        self.assertEqual(r["status"],"passed")
        self.assertTrue(r["reu_restored"] and r["configuration_restored"])
        self.assertEqual(c.reu,c.original)
        self.assertEqual(c.turbo["Turbo Control"],"C64U Turbo Registers")
        self.assertEqual(len(r["speeds"]),3)

    def test_failure_during_matrix_still_restores_changed_reu_and_configuration(self):
        c=FakeClient(self.project,fail_speed=16)
        r=run_matrix(c,self.project,Path(self.temp.name))
        self.assertEqual(r["status"],"failed")
        self.assertTrue(r["reu_restored"] and r["configuration_restored"])
        self.assertEqual(c.reu,c.original)
        self.assertEqual(len(r["speeds"]),1)
