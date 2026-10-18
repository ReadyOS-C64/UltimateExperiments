"""No-network tests of unshipped HD authority retention and recovery ordering."""
import importlib.util
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
PROJECT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT/'build_support'))
import c64u_bulk_reu_recovery as r
import c64u_hd_evidence as h
spec=importlib.util.spec_from_file_location('bulk_fixture',PROJECT/'tests/tooling/test_bulk_reu_recovery.py')
bulk=importlib.util.module_from_spec(spec);spec.loader.exec_module(bulk)

class FTP:
    def __init__(self,marker,image,events=None,truncate=False,extra=False,hang=False):
        self.marker=marker;self.image=image;self.events=events if events is not None else [];self.truncate=truncate;self.extra=extra;self.hang=hang
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def retrbinary(self,command,consume):
        self.events.append(command)
        if self.hang:time.sleep(20)
        data=self.marker if command.endswith('OWNER.JSON') else self.image
        if not command.endswith('OWNER.JSON'):
            if self.truncate:data=data[:-1]
            if self.extra:data+=b'x'
        for at in range(0,len(data),8192):consume(data[at:at+8192])

class Tests(unittest.TestCase):
    def fixture(self,profile=0,readonly=0,**ftpkw):
        source=bytearray((2 if profile==0 else 20)*1024*1024);source[510:512]=b'\x55\xaa';source=bytes(source)
        path='/usb1/DOS64_TEST/hd-evidence-test/DOSHD.IMG';encoded=path.encode()+b'\0'
        config=b'D64H\xa5'+bytes([0,profile,readonly,0x80,1,2,len(encoded)])+encoded+bytes(128-len(encoded))
        marker=json.dumps({'project':'8088DOS64ultimate','purpose':'owned-disposable-hd-evidence','run_id':'hd-evidence-test','nonce':'1'*32,'image_sha256':h.sha(source)},sort_keys=True).encode()
        owned={'schema':1,'project':'8088DOS64ultimate','purpose':'owned-disposable-hd-evidence','status':'verified','created_directory':True,'original_source_unchanged':True,'run_id':'hd-evidence-test','remote_directory':path.rsplit('/',1)[0],'native_path':path,'profile':profile,'readonly':readonly,'source_bytes':len(source),'source_sha256':h.sha(source),'remote_readback_bytes':len(source),'remote_readback_sha256':h.sha(source),'marker_sha256':h.sha(marker),'marker_readback_sha256':h.sha(marker),'config_sha256':h.sha(config)}
        runtime=bytearray(0x7c00-0x801+2);runtime[:2]=b'\x01\x08';runtime[0x7b2f-0x801+2:0x7b2f-0x801+142]=config
        labels=b'al 007B2F .hdc_config\nal 00EC09 .hdc_state_start\n'
        owned.update(runtime_prg_sha256=h.sha(runtime),labels_sha256=h.sha(labels))
        ftp=FTP(marker,source,**ftpkw)
        collector=h.HdEvidenceCollector(owned,marker,source,runtime,labels,lambda timeout:ftp,seconds=5)
        return collector,ftp
    def collect(self,collector,fake=None):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);out=Path(temporary.name)/'evidence'
        fake=fake or bulk.Fake();fake.ram[0xec09:0xec09+136]=collector.config[4:];fake.ram[0x1234]=0x77;fake.reu[0x350000:0x350200]=b'A'*512;fake.reu[0x352000:0x352200]=b'B'*512
        with patch.object(h,'SERVICE_SHA',r.sha(bulk.PRG)):
            report=collector.collect(fake,bulk.PRG,out,lambda *a,**k:None)
        return report,out,fake
    def test_ram_first_then_two_exact_reu_reads_and_complete_owned_image(self):
        c,ftp=self.fixture();report,out,fake=self.collect(c)
        self.assertEqual(report['status'],'passed');self.assertEqual((out/'ram-before-evidence-helper.bin').read_bytes()[0x1234],0x77)
        self.assertEqual((out/'authoritative-sector.bin').read_bytes(),b'A'*512);self.assertEqual((out/'guest-handoff.bin').read_bytes(),b'B'*512)
        self.assertEqual((out/'hd-visible.img').read_bytes(),c.source);self.assertNotIn('REU_WRITE',fake.events)
        self.assertLess(fake.events.index('capture_ram'),fake.events.index('runners:run_prg'));self.assertEqual(fake.dma,2)
        self.assertEqual(ftp.events,['RETR '+c.owned['remote_directory']+'/OWNER.JSON','RETR '+c.owned['native_path']])
    def test_large20m_exact_length_is_supported(self):
        c,_=self.fixture(profile=1);report,out,_=self.collect(c)
        self.assertEqual(report['status'],'passed');self.assertEqual((out/'hd-visible.img').stat().st_size,20*1024*1024)
    def test_ram_failure_never_uploads_helper_but_owned_image_is_retained(self):
        c,_=self.fixture();fake=bulk.Fake();fake.fail_capture=True;report,out,fake=self.collect(c,fake)
        self.assertEqual(report['status'],'failed');self.assertEqual(fake.loads,0);self.assertEqual(fake.dma,0);self.assertTrue((out/'hd-visible.img').exists())
    def test_short_and_extra_images_retain_partial_and_fail(self):
        for option in ('truncate','extra'):
            c,_=self.fixture(**{option:True});report,out,_=self.collect(c)
            self.assertEqual(report['status'],'failed');self.assertTrue((out/'hd-visible.partial.img').exists());self.assertFalse((out/'hd-visible.img').exists())
    def test_bad_remote_owner_forbids_hd_read_without_deleting_anything(self):
        c,ftp=self.fixture();ftp.marker=b'wrong';report,out,_=self.collect(c)
        self.assertEqual(report['status'],'failed');self.assertEqual(len(ftp.events),1);self.assertFalse((out/'hd-visible.partial.img').exists())
    def test_readonly_change_is_retained_but_failed(self):
        c,ftp=self.fixture(readonly=1);ftp.image=ftp.image[:-1]+b'x';report,out,_=self.collect(c)
        self.assertEqual(report['status'],'failed');self.assertTrue((out/'hd-visible.img').exists())
    def test_rw_changed_image_is_evidence_not_durability_or_trace_acceptance(self):
        c,ftp=self.fixture();ftp.image=ftp.image[:-1]+b'x';report,out,_=self.collect(c)
        self.assertEqual(report['status'],'passed');self.assertFalse(report['artifacts']['hd-visible.img']['source_equal']);self.assertIn('No physical guest AH03 trace is collected by this hook',report['limitations'])
    def test_unowned_path_profile_source_config_and_budgets_reject_before_transport(self):
        for field,value in [('created_directory',False),('native_path','/usb1/original.img'),('profile',True),('readonly',True),('source_sha256','0'*64),('marker_readback_sha256','0'*64),('config_sha256','0'*64)]:
            c,ftp=self.fixture();c.owned[field]=value
            with self.assertRaises(ValueError):c.preflight()
            self.assertEqual(ftp.events,[])
        for seconds in (0,121,True,float('nan'),float('inf')):
            c,_=self.fixture();c.seconds=seconds
            with self.assertRaises(ValueError):c.preflight()
    def test_wrong_service_fails_reu_but_preserves_ram_and_remote_image(self):
        c,_=self.fixture();temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        report=c.collect(bulk.Fake(),bulk.PRG,Path(temporary.name)/'e',lambda *a,**k:None)
        self.assertEqual(report['status'],'failed');self.assertIn('ram-before-evidence-helper.bin',report['artifacts']);self.assertIn('hd-visible.img',report['artifacts'])
    def test_isolated_blocked_ftp_is_killed_within_bound(self):
        c,_=self.fixture(hang=True);c.seconds=1
        with tempfile.TemporaryDirectory() as d,patch.object(h,'SERVICE_SHA',r.sha(bulk.PRG)):
            started=time.monotonic();result=c.run(bulk.Fake(),bulk.PRG,Path(d),lambda *a,**k:None)
            self.assertLess(time.monotonic()-started,4);self.assertTrue(result['timed_out']);self.assertEqual(result['status'],'failed')
            self.assertTrue((Path(d)/'hd-before-restore/authoritative-sector.bin').exists())
    def test_isolated_success_child_record_is_checked(self):
        c,_=self.fixture()
        with tempfile.TemporaryDirectory() as d,patch.object(h,'SERVICE_SHA',r.sha(bulk.PRG)):
            fake=bulk.Fake();fake.ram[0xec09:0xec09+136]=c.config[4:]
            result=c.run(fake,bulk.PRG,Path(d),lambda *a,**k:None)
            self.assertEqual(result['status'],'passed');self.assertFalse(result['timed_out']);self.assertTrue(result['isolated'])
    def test_hook_exception_and_failed_result_do_not_skip_full_restore(self):
        for raises in (False,True):
            class Hook:
                def preflight(self):pass
                def run(self,client,prg,out,journal):
                    self.assert_authority=bytes(client.reu[0x350000:0x350200])
                    if raises:raise OSError('retention fault')
                    return {'status':'failed'}
            hook=Hook();fake=bulk.Fake()
            def app(client,out):client.reu[0x350000:0x350200]=b'N'*512
            with tempfile.TemporaryDirectory() as d:
                result=r.run_with_recovery(fake,bulk.PRG,Path(d)/'run',app,pre_restore_evidence=hook)
            self.assertEqual(hook.assert_authority,b'N'*512);self.assertEqual(result['status'],'failed');self.assertTrue(result['reu_restored']);self.assertTrue(result['configuration_restored']);self.assertTrue(result['reset_resumed']);self.assertEqual(bytes(fake.reu[:r.SIZE]),bulk.ORIGINAL)
    def test_hook_runs_after_application_failure_ram_before_any_restore(self):
        class Hook:
            def preflight(self):pass
            def run(self,client,prg,out,journal):
                assert (out/'ram-failure-before-recovery.bin').read_bytes()[0x1234]==0x77
                assert 'REU_WRITE' not in client.events
                return {'status':'passed'}
        def app(client,out):client.ram[0x1234]=0x77;raise ValueError('guest failure')
        with tempfile.TemporaryDirectory() as d:
            result=r.run_with_recovery(bulk.Fake(),bulk.PRG,Path(d)/'r',app,pre_restore_evidence=Hook())
        self.assertEqual(result['status'],'failed');self.assertTrue(result['reu_restored'])
    def test_no_application_or_no_complete_backup_never_invokes_hook(self):
        class Hook:
            def preflight(self):pass
            def run(self,*a):raise AssertionError('unexpected evidence hook')
        for application,fail in [(None,False),(lambda *a:None,True)]:
            fake=bulk.Fake();fake.fail_snapshot=fail
            with tempfile.TemporaryDirectory() as d:
                result=r.run_with_recovery(fake,bulk.PRG,Path(d)/'r',application,pre_restore_evidence=Hook())
            self.assertNotIn('pre_restore_evidence',result)
    def test_preflight_error_before_device_or_output_directory(self):
        class Hook:
            def preflight(self):raise ValueError('invalid evidence input')
        fake=bulk.Fake()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'r'
            with self.assertRaises(ValueError):r.run_with_recovery(fake,bulk.PRG,path,pre_restore_evidence=Hook())
            self.assertFalse(path.exists());self.assertEqual(fake.events,[])
    def test_combined_real_collector_retains_new_authority_then_full_restore(self):
        for hang in (False,True):
            c,_=self.fixture(hang=hang);c.seconds=1 if hang else 5
            fake=bulk.Fake()
            def app(client,out):
                client.ram[0x1234]=0x77
                client.ram[0xec09:0xec09+136]=c.config[4:]
                client.reu[0x350000:0x350200]=b'N'*512
                client.reu[0x352000:0x352200]=b'H'*512
                raise ValueError('genuine guest failure simulated')
            with tempfile.TemporaryDirectory() as d,patch.object(h,'SERVICE_SHA',r.sha(bulk.PRG)):
                out=Path(d)/'run';started=time.monotonic()
                result=r.run_with_recovery(fake,bulk.PRG,out,app,pre_restore_evidence=c)
                self.assertLess(time.monotonic()-started,4)
                self.assertEqual((out/'hd-before-restore/authoritative-sector.bin').read_bytes(),b'N'*512)
                self.assertEqual((out/'hd-before-restore/guest-handoff.bin').read_bytes(),b'H'*512)
                self.assertEqual((out/'hd-before-restore/ram-before-evidence-helper.bin').read_bytes()[0x1234],0x77)
                self.assertEqual(result['pre_restore_evidence']['timed_out'],hang)
            self.assertEqual(result['status'],'failed');self.assertTrue(result['reu_restored'])
            self.assertTrue(result['configuration_restored']);self.assertTrue(result['reset_resumed'])
            self.assertEqual(bytes(fake.reu[:r.SIZE]),bulk.ORIGINAL)
    def test_actual_bodyless_transport_service_only_reads_two_authority_sectors(self):
        spec=importlib.util.spec_from_file_location('bodyless_fixture',PROJECT/'tests/tooling/test_c64u_ftp_put_transport.py')
        fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
        server=fixture.BodylessServer()
        adapter=fixture.t.FtpPutClient(server,fixture.manifest(),fixture.BLOBS,0xeaf4)
        c,_=self.fixture();server.ram[0xec09:0xec09+136]=c.config[4:]
        with tempfile.TemporaryDirectory() as d,patch.object(h,'SERVICE_SHA',r.sha(fixture.RECOVERY)):
            report=c.collect(adapter,fixture.RECOVERY,Path(d)/'e',lambda *a,**k:None)
        self.assertEqual(report['status'],'passed');self.assertEqual(server.dma,2)
        self.assertNotIn('REU_WRITE',server.events)
        self.assertTrue(any(route.startswith('runners:run_prg?file=') for route in server.transport_routes))
    def test_resident_config_mismatch_is_retained_failed_without_losing_sectors(self):
        c,_=self.fixture();fake=bulk.Fake()
        with tempfile.TemporaryDirectory() as d,patch.object(h,'SERVICE_SHA',r.sha(bulk.PRG)):
            report=c.collect(fake,bulk.PRG,Path(d)/'e',lambda *a,**k:None)
            self.assertEqual(report['status'],'failed');self.assertFalse(report['resident_config']['matches_planned_source'])
            self.assertIn('authoritative-sector.bin',report['artifacts']);self.assertIn('hd-visible.img',report['artifacts'])
    def test_runtime_or_labels_binding_tamper_rejects_before_device(self):
        for field in ('runtime_prg_sha256','labels_sha256'):
            c,ftp=self.fixture();c.owned[field]='0'*64
            with self.assertRaises(ValueError):c.preflight()
            self.assertEqual(ftp.events,[])

if __name__=='__main__':unittest.main()
