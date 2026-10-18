"""Private no-network tests; mocks are independent of the real native service."""
import ftplib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import unquote
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build_support'))
import c64u_ftp_put_transport as t
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'build_support'))
from c64u_bulk_reu_recovery import Service,run_with_recovery
RECOVERY=b'\x01\x08'+bytes(range(128))
NATIVE=b'\x01\x08'+b'new-current-native'*20
BLOBS={'recovery':RECOVERY,'native':NATIVE}


def manifest():
    directory=t.BASE+'/fresh-run'
    return {'schema':1,'project':'8088DOS64ultimate','purpose':'owned-native-development-prgs','status':'verified',
            'run_id':'fresh-run','remote_directory':directory,'created_directory':True,'source_files_unchanged':True,
            'marker_sha256':'a'*64,'marker_readback_sha256':'a'*64,'marker_bytes':512,
            'files':{role:{'sha256':t.sha(body),'bytes':len(body),'remote_path':directory+'/'+t.LEAVES[role],
                           'remote_readback_sha256':t.sha(body),'remote_readback_bytes':len(body)} for role,body in BLOBS.items()}}

class Ftp:
    def __init__(self):self.files={};self.events=[];self.existing=False;self.corrupt=None;self.extra=False
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def mkd(self,path):
        self.events.append(('MKD',path))
        if self.existing and path!=t.BASE:raise ftplib.error_perm('Directory already exists')
    def cwd(self,path):self.events.append(('CWD',path))
    def storbinary(self,command,file,callback):
        self.events.append(('STOR',command));body=file.read();self.files[command[5:]]=body;callback(body)
    def retrbinary(self,command,callback):
        self.events.append(('RETR',command));body=self.files[command[5:]]
        if self.corrupt and self.corrupt in command:body=body[:-1]
        if self.extra:body+=b'!'
        callback(body)

class Rest:
    def __init__(self):self.events=[];self.ram=bytearray(65536);self.fail_at=None;self.tick=None
    def put(self,route):
        self.events.append(route)
        if self.tick:self.tick()
        if self.fail_at and len(self.events)==self.fail_at:raise RuntimeError('Ambiguous PUT transport failure')
        if route.startswith('machine:writemem?'):
            address,data=route.split('?',1)[1].split('&data=');address=int(address.split('=')[1],16);body=bytes.fromhex(data)
            self.ram[address:address+len(body)]=body
        return {'errors':[]}
    def get(self,route):return {'route':route}
    def read(self,address,length):return bytes(self.ram[address:address+length])
    def request(self,*args,**kw):raise AssertionError('No body/POST request is permitted')

class Clock:
    def __init__(self):self.now=0
    def __call__(self):return self.now
    def advance(self):self.now+=1

class Tests(unittest.TestCase):
    def adapter(self,server=None,record=None,**kw):return t.FtpPutClient(server or Rest(),record or manifest(),BLOBS,0xeaf4,**kw)
    def inputs(self,root):
        result={}
        for role,body in BLOBS.items():
            path=Path(root)/(role+'.prg');path.write_bytes(body);result[role]={'path':path,'sha256':t.sha(body)}
        return result
    def test_fresh_owned_two_prgs_marker_and_full_byte_readback(self):
        ftp=Ftp()
        with tempfile.TemporaryDirectory() as d:
            inputs=self.inputs(d);record=t.prepare_prgs(lambda:ftp,inputs,'fresh-run',Path(d)/'evidence')
            self.assertEqual(record['status'],'verified');self.assertEqual(len(ftp.files),3)
            self.assertTrue(record['created_directory']);self.assertTrue(record['source_files_unchanged'])
            self.adapter(record=record)
            self.assertFalse(any(event[0] in ('DELE','RMD') for event in ftp.events))
    def test_existing_remote_run_is_never_reused_or_written(self):
        ftp=Ftp();ftp.existing=True
        with tempfile.TemporaryDirectory() as d:
            record=t.prepare_prgs(lambda:ftp,self.inputs(d),'fresh-run',Path(d)/'evidence')
            self.assertEqual(record['status'],'failed');self.assertFalse(ftp.files)
    def test_bad_local_sha_fails_before_ftp_contact(self):
        with tempfile.TemporaryDirectory() as d:
            inputs=self.inputs(d);inputs['native']['sha256']='0'*64
            with self.assertRaises(ValueError):t.prepare_prgs(lambda:self.fail('No FTP'),inputs,'fresh-run',Path(d)/'evidence')
    def test_truncated_and_extra_remote_readback_never_verify(self):
        for fault in ('truncated','extra'):
            ftp=Ftp();ftp.corrupt='NATIVE-DOS' if fault=='truncated' else None;ftp.extra=fault=='extra'
            with tempfile.TemporaryDirectory() as d:
                record=t.prepare_prgs(lambda:ftp,self.inputs(d),'fresh-run',Path(d)/'evidence')
                self.assertEqual(record['status'],'failed')
                with self.assertRaises(ValueError):self.adapter(record=record)
    def test_ftp_phase_deadline_is_bounded_and_retained(self):
        clock=Clock();ftp=Ftp()
        def factory():clock.now=10;return ftp
        with tempfile.TemporaryDirectory() as d:
            record=t.prepare_prgs(factory,self.inputs(d),'fresh-run',Path(d)/'evidence',clock=clock,phase_seconds=1)
            self.assertEqual(record['status'],'failed');self.assertIn('TimeoutError',record['error']);self.assertFalse(ftp.files)
    def test_prg_launch_is_bodyless_owned_file_and_unknown_bytes_rejected(self):
        server=Rest();adapter=self.adapter(server)
        adapter.request('POST','runners:run_prg',NATIVE,'application/octet-stream')
        self.assertEqual(server.events,['runners:run_prg?file=%2Fusb1%2FDOS64_TEST%2Ffresh-run%2FNATIVE-DOS.PRG'])
        with self.assertRaises(ValueError):adapter.request('POST','runners:run_prg',NATIVE+b'old','application/octet-stream')
        self.assertEqual(len(server.events),1)
    def test_registry_rejects_unverified_or_unowned_or_mismatched_sources(self):
        for alter in (lambda m:m.update(status='running'),lambda m:m.update(created_directory=False),
                      lambda m:m.update(source_files_unchanged=False),lambda m:m.update(marker_readback_sha256='b'*64),
                      lambda m:m['files']['native'].update(remote_path='/Temp/unrelated'),
                      lambda m:m['files']['native'].update(remote_readback_bytes=0)):
            record=manifest();alter(record)
            with self.assertRaises(ValueError):self.adapter(record=record)
    def test_memory_chunks_are_at_most128_bytes_and_cover_exact16k(self):
        server=Rest();adapter=self.adapter(server);body=bytes(range(256))*64
        adapter.request('POST','machine:writemem?address=8000',body,'application/octet-stream')
        self.assertEqual(server.ram[0x8000:0xc000],body);self.assertEqual(len(server.events),128)
        for index,route in enumerate(server.events):
            self.assertTrue(route.startswith(f'machine:writemem?address={0x8000+index*128:X}&data='))
            self.assertEqual(len(route.split('&data=')[1]),256)
    def test_small_owned_mailboxes_and_descriptor_fields_are_allowed(self):
        server=Rest();adapter=self.adapter(server)
        for address,body in ((0x6004,b'G'),(0x6006,b'123'),(0x600b,b'1234567'),(0xeaf4,bytes(19))):
            adapter.request('POST',f'machine:writemem?address={address:X}',body,'application/octet-stream')
        self.assertEqual(len(server.events),4)
    def test_invalid_memory_ranges_query_injection_and_unknown_body_fail_before_put(self):
        server=Rest();adapter=self.adapter(server)
        for route,body in (('machine:writemem?address=7FFF',b'xx'),('machine:writemem?address=BFFF',b'xx'),
                           ('machine:writemem?address=6009',b'xx'),('machine:writemem?address=D000',b'x'),
                           ('machine:writemem?address=FFFF',b'xx'),('machine:writemem?address=8000&data=00',b'x'),
                           ('machine:writemem?address=8000',b''),('machine:writemem?address=8000',bytes(0x4001))):
            with self.assertRaises(ValueError):adapter.request('POST',route,body,'application/octet-stream')
        self.assertEqual(server.events,[])
        with self.assertRaises(ValueError):adapter.request('POST','configs',b'{}','application/json')
    def test_partial_staging_transport_error_is_not_retried_and_never_publishes_go(self):
        server=Rest();server.fail_at=3;adapter=self.adapter(server)
        with self.assertRaises(RuntimeError):adapter.request('POST','machine:writemem?address=8000',bytes(0x4000),'application/octet-stream')
        self.assertEqual(len(server.events),3);self.assertFalse(any('address=6004' in event for event in server.events))
    def test_memory_upload_wall_deadline_stops_without_retry(self):
        clock=Clock();server=Rest();server.tick=clock.advance;adapter=self.adapter(server,clock=clock,write_seconds=2)
        with self.assertRaises(TimeoutError):adapter.request('POST','machine:writemem?address=8000',bytes(0x4000),'application/octet-stream')
        self.assertEqual(len(server.events),2)
    def test_config_exact_strings_encoded_and_only_two_allowed_keys(self):
        server=Rest();adapter=self.adapter(server)
        adapter.configs({'U64 Specific Settings':{'Turbo Control':'C64U Turbo Registers','CPU Speed':' 1'}})
        self.assertEqual(server.events,['configs/U64%20Specific%20Settings/Turbo%20Control?value=C64U%20Turbo%20Registers',
                                        'configs/U64%20Specific%20Settings/CPU%20Speed?value=%201'])
        for value in ({'C64 and Cartridge Settings':{'REU Size':'4 MB'}},{'U64 Specific Settings':{'CPU Speed':'64','Unknown':'x'}},
                      {'U64 Specific Settings':{'CPU Speed':'64\n'}}):
            with self.assertRaises(ValueError):adapter.configs(value)
        self.assertEqual(len(server.events),2)
    def test_control_allowlist_and_exact_read_lengths(self):
        server=Rest();adapter=self.adapter(server)
        for route in ('machine:pause','machine:resume','machine:reset'):adapter.put(route)
        with self.assertRaises(ValueError):adapter.put('machine:reboot')
        with self.assertRaises(ValueError):adapter.put('runners:run_prg?file=/Temp/a')
        with self.assertRaises(ValueError):adapter.get('machine:menu_screen')
        self.assertEqual(len(adapter.read(0,65536)),65536)
        with self.assertRaises(ValueError):adapter.read(65535,2)
        server.read=lambda *args:b''
        with self.assertRaises(ValueError):adapter.read(0,1)

# Import only the existing independent functional host fixture. This does not
# replace/rebuild the actual native service, already covered by4 Peddle tests.
spec=importlib.util.spec_from_file_location('existing_bulk_host_mock',ROOT/'tests/tooling/test_bulk_reu_recovery.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class BodylessServer(module.Fake):
    def __init__(self):super().__init__();self.transport_routes=[];self.fail_launch=False;self.fail_payload_once=False
    def request(self,*args,**kwargs):raise AssertionError('Network body/POST is forbidden')
    def put(self,route):
        self.transport_routes.append(route)
        if route.startswith('machine:writemem?'):
            if self.fail_payload_once and route.startswith('machine:writemem?address=8080&'):
                self.fail_payload_once=False;raise RuntimeError('One ambiguous payload PUT failure')
            query=route.split('?',1)[1];address,data=query.split('&data=')
            return module.Fake.request(self,'POST','machine:writemem?'+address,bytes.fromhex(data),'application/octet-stream')
        if route.startswith('runners:run_prg?file='):
            if self.fail_launch:raise RuntimeError('File-based PRG launch failed before execution')
            path=unquote(route.split('=',1)[1]);role=next(role for role,name in t.LEAVES.items() if path.endswith('/'+name))
            return module.Fake.request(self,'POST','runners:run_prg',BLOBS[role],'application/octet-stream')
        if route.startswith('configs/'):
            path,value=route.split('?value=');_,category,key=path.split('/')
            return module.Fake.configs(self,{unquote(category):{unquote(key):unquote(value)}})
        return module.Fake.put(self,route)

class Integration(unittest.TestCase):
    def test_unchanged_recovery_full4m_snapshot_restore_compare_with_only_put_transport(self):
        server=BodylessServer();adapter=t.FtpPutClient(server,manifest(),BLOBS,0xeaf4)
        with tempfile.TemporaryDirectory() as d:
            def app(client,output):server.reu[:4194304]=b'\x55'*4194304
            result=run_with_recovery(adapter,RECOVERY,Path(d)/'run',application=app)
            self.assertEqual(result['status'],'passed');self.assertTrue(result['reu_restored'])
            self.assertTrue(result['configuration_restored']);self.assertTrue(result['reset_resumed'])
            self.assertEqual(server.loads,2);self.assertEqual(bytes(server.reu[:4194304]),module.ORIGINAL)
            self.assertEqual(server.reu[4194304:],b'\x9b'*(12*1024*1024))
            self.assertEqual(adapter.stats['put_memory_requests'],35074) #3commands*768 plus32768payload and2initialstatewrites
            self.assertEqual(adapter.stats['put_prg_launches'],2);self.assertEqual(adapter.stats['put_config_requests'],2)
            self.assertEqual(len([x for x in server.transport_routes if x.startswith('runners:')]),2)

    def test_first_file_launch_failure_still_restores_config_resets_and_retains_ram(self):
        server=BodylessServer();server.fail_launch=True;adapter=t.FtpPutClient(server,manifest(),BLOBS,0xeaf4)
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'run';result=run_with_recovery(adapter,RECOVERY,out)
            self.assertEqual(result['status'],'failed');self.assertTrue(result['configuration_restored'])
            self.assertTrue(result['reset_resumed']);self.assertEqual(server.loads,0)
            self.assertTrue((out/'ram-failure-before-recovery.bin').exists())
            self.assertEqual(bytes(server.reu[:4194304]),module.ORIGINAL)
    def test_partial_payload_put_failure_retains_ram_then_fresh_whole_restore_repairs(self):
        server=BodylessServer();adapter=t.FtpPutClient(server,manifest(),BLOBS,0xeaf4)
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'run'
            def app(client,output):
                server.reu[:4194304]=b'\x55'*4194304;server.fail_payload_once=True
            result=run_with_recovery(adapter,RECOVERY,out,application=app)
            self.assertEqual(result['status'],'passed');self.assertEqual(result['restore_attempts'],2)
            self.assertEqual(server.loads,3);self.assertTrue((out/'ram-restore-failure-1-before-reset.bin').exists())
            self.assertEqual(bytes(server.reu[:4194304]),module.ORIGINAL)

if __name__=='__main__':unittest.main()
