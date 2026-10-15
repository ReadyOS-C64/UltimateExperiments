import importlib.util
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'build_support'))
from c64u_bulk_reu_recovery import SIZE,CHUNK,run_with_recovery
from c64u_delta_reu_recovery import DeltaService
from test_c64u_ftp_put_transport import BodylessServer,manifest,BLOBS,RECOVERY,module,t

class Tests(unittest.TestCase):
    def run_case(self,mutate,fail=False,server_type=BodylessServer,fail_dma=False):
        server=server_type();adapter=t.FtpPutClient(server,manifest(),BLOBS,0xeaf4)
        with tempfile.TemporaryDirectory() as d:
            def app(client,output):
                mutate(server.reu);server.fail_payload_once=fail;server.fail_restore=int(fail_dma)
            out=Path(d)/'run'
            result=run_with_recovery(adapter,RECOVERY,out,application=app,service_factory=DeltaService)
            self.assertEqual(result['status'],'passed');self.assertTrue(result['reu_restored'])
            self.assertTrue(result['configuration_restored']);self.assertTrue(result['reset_resumed'])
            self.assertEqual(bytes(server.reu[:SIZE]),module.ORIGINAL)
            self.assertEqual(server.reu[SIZE:],b'\x9b'*(12*1024*1024))
            journal=(out/'journal.jsonl').read_text()
            self.assertIn('"scope_bytes": 4194304',journal)
            return result,server,adapter,journal
    def test_no_changes_scan_every_byte_and_full_compare_without_payload_writes(self):
        result,server,adapter,journal=self.run_case(lambda reu:None)
        self.assertIn('"changed_chunks": 0',journal)
        payload=[r for r in server.transport_routes if r.startswith('machine:writemem?address=80')]
        self.assertEqual(payload,[])
    def test_first_last_and_unexpected_region_changes_are_all_detected_and_repaired(self):
        def mutate(reu):
            for address in (0,SIZE-1,0x200001):reu[address]^=0xff
        result,server,adapter,journal=self.run_case(mutate)
        self.assertIn('"changed_chunks": 3',journal)
        payload=[r for r in server.transport_routes if r.startswith('machine:writemem?address=') and 0x8000<=int(r.split('address=')[1].split('&')[0],16)<0xc000]
        self.assertEqual(len(payload),3*128)
    def test_partial_upload_failure_fresh_scan_and_retry_repairs_full_scope(self):
        result,server,adapter,journal=self.run_case(lambda reu:reu.__setitem__(SIZE-1,reu[SIZE-1]^0xff),True)
        self.assertEqual(result['restore_attempts'],2)
        self.assertEqual(journal.count('"event": "delta_scan_complete"'),2)
    def test_partial_dma_and_unexpected_alias_change_are_found_by_fresh_full_scan(self):
        class Aliasing(BodylessServer):
            def execute(self):
                fault=self.ram[module.r.MAILBOX+6]==0 and self.fail_restore>0
                super().execute()
                if fault:self.reu[0x200001]^=0xff
        result,server,adapter,journal=self.run_case(lambda reu:reu.__setitem__(SIZE-1,reu[SIZE-1]^0xff),server_type=Aliasing,fail_dma=True)
        self.assertEqual(result['restore_attempts'],2)
        self.assertIn('"changed_chunks": 1',journal)
        self.assertIn('"changed_chunks": 2',journal)
    def test_invalid_backup_or_phase_rejected_before_scan_or_writes(self):
        service=DeltaService(None,RECOVERY)
        for data,seconds in [(bytes(SIZE-1),600),(bytearray(SIZE),600),(bytes(SIZE),601),(bytes(SIZE),0)]:
            with self.assertRaises(ValueError):service.restore(data,seconds)
    def test_incomplete_scan_never_authorizes_a_write(self):
        class Short(DeltaService):
            def command(self,direction,address,count,payload=None):
                if direction==0:raise AssertionError('No writes permitted after incomplete scan')
                return bytes(count-1)
        with self.assertRaises(ValueError):Short(None,RECOVERY).restore(bytes(SIZE))
    def test_scan_deadline_expires_before_write(self):
        class Slow(DeltaService):
            now=0
            def command(self,direction,address,count,payload=None):
                if direction==0:raise AssertionError('No writes permitted after timeout')
                self.now+=1;return bytes(count)
        service=Slow(None,RECOVERY);service.clock=lambda:service.now
        with self.assertRaises(TimeoutError):service.restore(bytes(SIZE),2)

if __name__=='__main__':unittest.main()
