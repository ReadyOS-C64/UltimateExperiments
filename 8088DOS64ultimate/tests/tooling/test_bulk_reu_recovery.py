"""No-network host oracle, separate from actual native Peddle assertions."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"build_support"))
import c64u_bulk_reu_recovery as r

PRG=b"\x01\x08"+bytes(range(128))
ORIGINAL=bytes((i*37 ^ (i>>8) ^ (i>>16) ^ 0xa7)&255 for i in range(r.SIZE))

class Fake:
    def __init__(self):
        self.ram=bytearray(65536);self.reu=bytearray(ORIGINAL)+bytearray(b"\x9b"*(12*1024*1024))
        self.turbo={"Turbo Control":"Manual","CPU Speed":" 1"}
        self.machine={"C64 and Cartridge Settings":{"RAM Expansion Unit":"Enabled","REU Size":"16 MB"}}
        self.drives={"drives":[{"Drive A":{"image":"unchanged.d64","last_error":""}}]}
        self.events=[];self.loads=0;self.pending=None;self.dma=0;self.paused=False
        self.fail_snapshot=False;self.fail_restore=0;self.corrupt_compare=False
        self.fail_capture=False;self.fail_cleanup=False;self.fail_reset=False
        self.fail_final_resume=False;self.reset_seen=False
        self.drop_go=False;self.bad_descriptor=False
    def get(self, route):
        if route=="info":return {"firmware_version":"mock3.14","product":"C64 Ultimate"}
        if route=="configs/U64%20Specific%20Settings":return {"U64 Specific Settings":dict(self.turbo)}
        if route=="configs/C64%20and%20Cartridge%20Settings":return self.machine
        if route=="drives":return self.drives
        raise AssertionError(route)
    def configs(self,value):
        self.events.append("configs")
        if self.fail_cleanup:raise RuntimeError("cleanup fault")
        self.turbo.update(value["U64 Specific Settings"])
    def put(self,route):
        self.events.append(route)
        if route=="machine:pause":self.paused=True
        elif route=="machine:reset":
            self.reset_seen=True
            if self.fail_reset:raise RuntimeError("reset fault")
            self.ram[:]=bytes(65536)
        elif route=="machine:resume":
            if self.fail_final_resume and self.reset_seen:raise RuntimeError("resume fault")
            self.paused=False
            if self.pending is not None:
                self.pending=None;self.execute()
        else:raise AssertionError(route)
    def request(self,method,route,data,kind):
        self.events.append(route)
        if route=="runners:run_prg":
            self.loads+=1;self.ram[0x801:0x801+len(data)-2]=data[2:]
            self.ram[r.MAILBOX:r.MAILBOX+32]=bytes(32)
            self.ram[r.MAILBOX:r.MAILBOX+4]=b"DRS1";self.ram[r.MAILBOX+4]=r.READY
            return
        assert self.paused,"body/GO publication must be paused"
        address=int(route.split("=")[1],16)
        if address==r.MAILBOX+4 and data==bytes([r.GO]) and self.drop_go:return
        self.ram[address:address+len(data)]=data
        if address==r.MAILBOX+11 and self.bad_descriptor:self.ram[address]^=1
        if address==r.MAILBOX+4 and data==bytes([r.GO]):self.pending=True
    def read(self,address,count):
        if address==0 and count==65536:
            self.events.append("capture_ram")
            if self.fail_capture:raise RuntimeError("RAM capture fault")
        return bytes(self.ram[address:address+count])
    def execute(self):
        self.dma+=1
        box=self.ram[r.MAILBOX:r.MAILBOX+32]
        assert box[4]==r.GO
        seq=int.from_bytes(box[7:9],"little");ack=int.from_bytes(box[9:11],"little")
        assert seq==((ack+1)&65535)
        assert int.from_bytes(box[16:18],"little")==seq^65535
        direction=box[6];address=int.from_bytes(box[11:14],"little");count=int.from_bytes(box[14:16],"little")
        assert 0<=address<r.SIZE and address+count<=r.SIZE and 0<count<=r.CHUNK
        assert (address&65535)+count<=65536
        self.ram[r.MAILBOX+9:r.MAILBOX+11]=box[7:9]
        failure=(direction==1 and self.fail_snapshot) or (direction==0 and self.fail_restore>0)
        if direction==0:
            self.events.append("REU_WRITE")
            n=17 if failure else count
            self.reu[address:address+n]=self.ram[r.STAGING:r.STAGING+n]
            if failure:self.fail_restore-=1
        elif not failure:
            block=bytes(self.reu[address:address+count])
            if self.corrupt_compare and self.loads>=2:block=bytes([block[0]^1])+block[1:]
            self.ram[r.STAGING:r.STAGING+count]=block
        self.ram[r.MAILBOX+4]=r.FAIL if failure else r.DONE
        self.ram[r.MAILBOX+5]=7 if failure else 0
        self.ram[r.MAILBOX+18]=4 if failure else 0
        self.ram[r.MAILBOX+19]=0x20 if failure else 0x40

class Tests(unittest.TestCase):
    def workflow(self,fake,app=None,**kw):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        out=Path(temporary.name)/"owned"
        report=r.run_with_recovery(fake,PRG,out,app,**kw)
        return out,report
    def test_full_snapshot_application_restore_readback_uses_only_two_loads(self):
        f=Fake()
        def app(client,out):
            self.assertTrue((out/"reu-before.json").exists())
            client.reu[:r.SIZE]=b"\x55"*r.SIZE
            return {"bounded_test":"mock"}
        out,result=self.workflow(f,app)
        self.assertEqual(result["status"],"passed");self.assertTrue(result["reu_restored"])
        self.assertTrue(result["configuration_restored"]);self.assertTrue(result["reset_resumed"])
        self.assertEqual(f.loads,2);self.assertEqual(f.dma,768)
        self.assertEqual(bytes(f.reu[:r.SIZE]),ORIGINAL);self.assertEqual(f.reu[r.SIZE:],b"\x9b"*(12*1024*1024))
        self.assertEqual((out/"reu-after-1.bin").read_bytes(),ORIGINAL)
        manifest=json.loads((out/"reu-before.json").read_text())
        self.assertEqual(r.verify_backup(out/"reu-before.bin",manifest),ORIGINAL)
        self.assertEqual((out/"reu-before.bin").stat().st_mode&0o222,0)
    def test_application_failure_captures_ram_before_reset_and_still_restores(self):
        f=Fake()
        def app(client,out):
            client.reu[4]=0;client.ram[0x1234]=0x77;raise RuntimeError("application fault")
        out,result=self.workflow(f,app)
        self.assertEqual(result["status"],"failed");self.assertTrue(result["reu_restored"])
        self.assertEqual((out/"ram-failure-before-recovery.bin").read_bytes()[0x1234],0x77)
        self.assertLess(f.events.index("capture_ram"),f.events.index("machine:reset"))
    def test_snapshot_failure_never_runs_application_or_writes_reu(self):
        f=Fake();f.fail_snapshot=True
        out,result=self.workflow(f,lambda *x:self.fail("must not run"))
        self.assertEqual(result["status"],"failed");self.assertNotIn("REU_WRITE",f.events)
        self.assertFalse((out/"reu-before.json").exists());self.assertTrue(result["reset_resumed"])
    def test_partial_restore_failure_reloads_once_then_repairs_all_four_mib(self):
        f=Fake();f.fail_restore=1
        out,result=self.workflow(f,lambda client,out:client.reu.__setitem__(slice(0,r.SIZE),b"\x55"*r.SIZE))
        self.assertEqual(result["status"],"passed");self.assertEqual(result["restore_attempts"],2)
        self.assertEqual(f.loads,3);self.assertEqual(f.reu[:r.SIZE],ORIGINAL)
        self.assertTrue((out/"ram-restore-failure-1-before-reset.bin").exists())
    def test_readback_mismatch_retains_backup_and_failure_ram(self):
        f=Fake();f.corrupt_compare=True
        out,result=self.workflow(f)
        self.assertEqual(result["status"],"failed");self.assertFalse(result["reu_restored"])
        self.assertEqual((out/"reu-before.bin").read_bytes(),ORIGINAL)
        self.assertEqual(len(result["restore_errors"]),2);self.assertTrue(result["reset_resumed"])
    def test_capture_failure_still_resets_and_never_writes_reu(self):
        f=Fake();f.fail_capture=True
        out,result=self.workflow(f)
        self.assertEqual(result["status"],"failed");self.assertTrue(result["reset_resumed"])
        self.assertIn("failure_capture_errors",result);self.assertNotIn("REU_WRITE",f.events)
    def test_configuration_failure_does_not_skip_reset_resume(self):
        f=Fake();f.fail_cleanup=True
        out,result=self.workflow(f)
        self.assertEqual(result["status"],"failed");self.assertFalse(result["configuration_restored"])
        self.assertTrue(result["reset_resumed"]);self.assertTrue((out/"ram-cleanup-failure-before-reset.bin").exists())
    def test_reset_failure_is_explicit(self):
        f=Fake();f.fail_reset=True
        out,result=self.workflow(f)
        self.assertEqual(result["status"],"failed");self.assertFalse(result["reset_resumed"])
        self.assertTrue((out/"ram-before-final-reset.bin").exists())
        self.assertEqual(f.events[-1],"machine:resume")
    def test_final_resume_failure_is_explicit(self):
        f=Fake();f.fail_final_resume=True
        out,result=self.workflow(f)
        self.assertEqual(result["status"],"failed");self.assertFalse(result["reset_resumed"])
        self.assertTrue(result["reu_restored"])
    def test_changed_machine_config_forbids_restore_dma(self):
        f=Fake()
        def app(client,out):client.machine={"C64 and Cartridge Settings":{"RAM Expansion Unit":"Enabled","REU Size":"2 MB"}}
        out,result=self.workflow(f,app)
        self.assertEqual(result["status"],"failed");self.assertNotIn("REU_WRITE",f.events)
        self.assertFalse(result["configuration_restored"]);self.assertTrue(result["reset_resumed"])
    def test_tampered_local_backup_forbids_restore_dma(self):
        f=Fake()
        def app(client,out):
            p=out/"reu-before.bin";p.chmod(0o644);p.write_bytes(b"!"*r.SIZE)
        out,result=self.workflow(f,app)
        self.assertEqual(result["status"],"failed");self.assertNotIn("REU_WRITE",f.events)
    def test_journal_storage_failure_does_not_prevent_recovery(self):
        f=Fake()
        original=Path.open
        def failing(path,*args,**kw):
            if path.name=="journal.jsonl":raise OSError("journal storage fault")
            return original(path,*args,**kw)
        with patch.object(Path,"open",failing):out,result=self.workflow(f)
        self.assertEqual(result["status"],"failed");self.assertTrue(result["reu_restored"])
        self.assertTrue(result["reset_resumed"]);self.assertIn("evidence_errors",result)
    def test_invalid_existing_backup_fails_before_contacting_hardware(self):
        f=Fake()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"backup.bin";p.write_bytes(b"bad")
            with self.assertRaises(ValueError):r.run_with_recovery(f,PRG,Path(d)/"run",backup_path=p,backup_manifest={})
        self.assertEqual(f.events,[])
    def test_pre_go_staging_descriptor_and_commit_verification(self):
        for fault in ("bad_descriptor","drop_go"):
            f=Fake();setattr(f,fault,True);service=r.Service(f,PRG);service.load()
            with self.assertRaises(ValueError):service.command(1,0,r.CHUNK)
            self.assertEqual(f.dma,0)
        f=Fake();service=r.Service(f,PRG);service.load()
        for args in ((1,r.SIZE,1),(1,0,0),(2,0,1),(1,65535,2),(0,0,1)):
            with self.assertRaises(ValueError):service.command(*args)
        self.assertEqual(f.dma,0)
    def test_truncated_staging_read_is_explicit_before_comparison_zip(self):
        f=Fake();service=r.Service(f,PRG);service.load()
        original=f.read
        f.read=lambda address,count:original(address,count)[:-1] if address==r.STAGING else original(address,count)
        with self.assertRaisesRegex(ValueError,"staging read length mismatch"):service.command(1,0,r.CHUNK)
        self.assertEqual(service.sequence,1)
        # Independently guard compare even if an injected service returns short data.
        service.command=lambda *args:b"short"
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"Readback staging read length mismatch"):
                service.compare(ORIGINAL,Path(d)/"readback.bin")
    def test_unresolved_command_times_out_instead_of_reissuing(self):
        f=Fake();service=r.Service(f,PRG);service.load()
        f.execute=lambda:None
        ticks=iter(range(20));service.clock=lambda:next(ticks);service.command_seconds=3;service.sleep=lambda _:None
        with self.assertRaises(TimeoutError):service.command(1,0,1)
        self.assertEqual(f.dma,0);self.assertEqual(service.sequence,0)
    def test_existing_backup_disaster_recovery_preserves_source(self):
        f=Fake();f.reu[:r.SIZE]=b"\x55"*r.SIZE
        with tempfile.TemporaryDirectory() as d:
            backup=Path(d)/"saved.bin";backup.write_bytes(ORIGINAL)
            manifest={"schema":1,"complete":True,"reu_start":0,"length":r.SIZE,"sha256":hashlib.sha256(ORIGINAL).hexdigest()}
            result=r.run_with_recovery(f,PRG,Path(d)/"new",backup_path=backup,backup_manifest=manifest)
            self.assertEqual(result["status"],"passed");self.assertEqual(f.loads,1)
            self.assertEqual(backup.read_bytes(),ORIGINAL);self.assertEqual(f.reu[:r.SIZE],ORIGINAL)

if __name__=="__main__":unittest.main()
