"""Independent local/captured identity adversaries; no device contact."""
import copy
import contextlib
import io
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'build_support'))
import c64u_native_application as app
import c64u_native_shadow_identity as shadow
PROJECT=next(p for p in Path(__file__).resolve().parents if (p/'reference').is_dir())
# Optional private frozen inputs; default normal build remains the production gate.
import os
BUILD=Path(os.environ.get('DOS64_SHADOW_TEST_BUILD',str(PROJECT/'build')))
SOURCE=PROJECT/'reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img'
MEDIA={'status':'verified','source_sha256':app.SOURCE_SHA,'source_bytes':368640,
       'created_directory':True,'remote_readback_bytes':368640,'remote_readback_sha256':app.SOURCE_SHA,
       'original_source_unchanged':True,'source_crc32':813107767,
       'native_path':'/usb1/DOS64_TEST/mock-owned-shadow/DOS33A.IMG',
       'remote_directory':'/usb1/DOS64_TEST/mock-owned-shadow','marker_sha256':'a'*64}

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prg=(BUILD/'dos64-tests.prg').read_bytes()
        cls.labels=app.labels_from(BUILD/'dos64-tests.labels')
        cls.map=(BUILD/'dos64-tests.map').read_text()
        cls.segments=app.resident_from_map(BUILD/'dos64-tests.map')
        cls.metadata={'package':json.loads((BUILD/'dos64-tests-overlay-package.json').read_text()),
                      'memory':json.loads((BUILD/'dos64-tests.memory.json').read_text())}
    def make(self,prg=None,labels=None,segments=None,metadata=None):
        return app.Application(self.prg if prg is None else prg,self.labels if labels is None else labels,MEDIA,SOURCE,
                               b'\x01\x08dummy',shadow.sha(self.prg if prg is None else prg),
                               resident_segments=self.segments if segments is None else segments,
                               shadow_metadata=self.metadata if metadata is None else metadata)
    def ram(self,application):
        r=bytearray(65536);r[0x801:0x801+len(application.prg)-2]=application.prg[2:]
        c=application.shadow_identity;r[0xf000:0xfe00]=c['expected'];r[c['loaded_guard_address']]=0xa5;r[0:2]=b'\x2f\xf5'
        for operand,buffer in [('dos64_uci_upload_operand','dos64_uci_command'),('dos64_uci_drain_operand','dos64_uci_data')]:
            a=application.labels[operand];r[a:a+2]=application.labels[buffer].to_bytes(2,'little')
        return r
    def check(self,a,ram):
        with tempfile.TemporaryDirectory(dir=PROJECT/'agentworking/scratch') as directory:
            a.output=Path(directory)
            return a.verify_resident(bytes(ram))
    def test_real_normal_artifacts_constructor_and_complete_source_to_run_proof(self):
        a=self.make();r=self.ram(a);proof=self.check(a,r)[-1]
        self.assertEqual(proof['name'],'HDBIOS');self.assertTrue(proof['matches'])
        self.assertEqual(proof['length'],3584);self.assertEqual(proof['zero_tail_bytes'],43)
        self.assertEqual(proof['normalizations'],[]);self.assertFalse(proof['bank']['live_cpu_port_verified'])
    def test_every_code_and_zero_tail_byte_rejected(self):
        a=self.make();r=self.ram(a);c=a.shadow_identity
        for offset in range(3584):
            r[0xf000+offset]^=1
            proof=shadow.verify(c,r)
            self.assertFalse(proof['matches']);self.assertEqual(proof['first_difference_address'],0xf000+offset)
            r[0xf000+offset]^=1
    def test_live_source_alias_is_never_expected_and_FE_vectors_are_excluded(self):
        a=self.make();r=self.ram(a);r[0xa000:0xae00]=b'\x5a'*3584;r[0xfe00:]=b'\x37'*512
        self.assertTrue(self.check(a,r)[-1]['matches'])
        r[0xf000]=r[0xa000]
        with self.assertRaisesRegex(ValueError,'Captured resident executable'):self.check(a,r)
    def test_guard_and_bank_require_ram_under_KERNAL_with_IO(self):
        a=self.make();r=self.ram(a);g=a.shadow_identity['loaded_guard_address']
        for value in [0,1,0xa4,0xff]:
            r[g]=value;self.assertFalse(shadow.verify(a.shadow_identity,r)['matches'])
        r[g]=0xa5
        for ddr,data in [(0x2f,0x37),(0x2f,0x34),(0,0x35),(0x2f,0x30)]:
            r[:2]=bytes([ddr,data]);self.assertFalse(shadow.verify(a.shadow_identity,r,cpu_port_snapshot=bytes([ddr,data]))['matches'])
        for data in [0x35,0xf5]:
            r[:2]=bytes([0x2f,data]);self.assertTrue(shadow.verify(a.shadow_identity,r,cpu_port_snapshot=bytes(r[:2]))['matches'])
        r[:2]=b'\0\1'
        self.assertTrue(shadow.verify(a.shadow_identity,r)['matches'])
        self.assertFalse(shadow.verify(a.shadow_identity,r)['bank']['live_cpu_port_verified'])
        for bad in [b'',b'\0',b'\0\1\2',[0x2f,0x35]]:
            with self.assertRaises(ValueError):shadow.verify(a.shadow_identity,r,cpu_port_snapshot=bad)
    def test_map_pair_range_size_and_duplicate_rejected(self):
        for text in [re.sub(r'^HDBIOS.*\n','',self.map,flags=re.M),
                     re.sub(r'^(HDBIOS\s+)00F000',r'\g<1>00F001',self.map,flags=re.M),
                     re.sub(r'^(HDBIOS\s+\S+\s+\S+\s+)\S+',r'\g<1>000861',self.map,flags=re.M)]:
            with self.assertRaises(ValueError):shadow.shadow_from_map(text)
        block=re.search(r'^HDBIOS.*$',self.map,re.M)[0]
        with self.assertRaises(ValueError):shadow.shadow_from_map(self.map.replace(block,block+'\n'+block))
    def test_constructor_refuses_missing_map_guard_or_metadata_before_media_access(self):
        variants=[{'segments':[s for s in self.segments if s['name']!='HDBIOS']},
                  {'metadata':{}},{'labels':{k:v for k,v in self.labels.items()if k!='hdb_extension_ready'}}]
        for kw in variants:
            with patch.object(app,'verified_media',side_effect=AssertionError('media reached')):
                with self.assertRaises(ValueError):self.make(**kw)
        with patch.object(app,'verified_media',side_effect=AssertionError('media reached')):
            with self.assertRaises(ValueError):
                app.Application(self.prg,self.labels,MEDIA,SOURCE,b'',shadow.sha(self.prg),resident_segments=self.segments)
    def test_all_shadow_symbol_metadata_and_load_contract_fields_are_strict(self):
        for key in ['__HDEXT_START__','__HDEXT_SIZE__','__HDEXT_FILEOFFS__','__HDEXT_LAST__','__HDBIOS_LOAD__','__HDBIOS_RUN__','__HDBIOS_SIZE__','__NATIVESTATE_LOAD__','__NATIVESTATE_RUN__','__NATIVESTATE_SIZE__','hdb_boot_drive','hdb_extension_ready','__HDCODE_LOAD__','__HDCODE_RUN__','__HDCODE_SIZE__']:
            labels=dict(self.labels);labels[key]+=1
            with self.subTest(symbol=key),self.assertRaises(ValueError):self.make(labels=labels)
        paths=[('package','version'),('package','shadow','ownership'),('memory','load','shadow','ownership'),('memory','load','shadow','excludes'),('package','shadow','source'),('package','shadow','run'),('package','shadow','window_bytes'),('package','shadow','linked_bytes'),('package','shadow','tail_zero_bytes'),('package','shadow','sha256'),('package','sha256','packaged_prg'),('memory','passed'),('memory','load','start'),('memory','load','end_exclusive'),('memory','load','prg_bytes'),('memory','load','payload_checked'),('memory','load','shadow','payload_checked'),('memory','load','shadow','source'),('memory','load','shadow','run'),('memory','load','shadow','window_bytes'),('memory','load','shadow','linked_bytes')]
        for path in paths:
            meta=copy.deepcopy(self.metadata);node=meta
            for key in path[:-1]:node=node[key]
            old=node[path[-1]];node[path[-1]]=False if type(old) is bool else old+1 if type(old) is int else 'bad'
            with self.subTest(metadata=path),self.assertRaises(ValueError):self.make(metadata=meta)
    def test_packaged_source_tail_slot_and_guard_corruption_rejected(self):
        guard=self.labels['hdb_extension_ready']
        for address in [0xa000,0xa85f,0xa860,0xadff,0x9800,0x9810+self.labels['__HDCODE_SIZE__'],guard]:
            prg=bytearray(self.prg);prg[address-0x801+2]^=1
            meta=copy.deepcopy(self.metadata);meta['package']['sha256']['packaged_prg']=shadow.sha(prg)
            with self.subTest(address=hex(address)),self.assertRaises(ValueError):self.make(prg=bytes(prg),metadata=meta)
        for raw in [self.prg[:-1],self.prg+b'\0',b'\x00\x08'+self.prg[2:]]:
            with self.assertRaises(ValueError):self.make(prg=raw)
    def test_metadata_artifacts_must_be_paired_and_pinned(self):
        p=BUILD/'dos64-tests-overlay-package.json';m=BUILD/'dos64-tests.memory.json'
        pins={shadow.sha(p.read_bytes()),shadow.sha(m.read_bytes())}
        self.assertEqual(shadow.metadata_from_paths(p,m,pins),self.metadata)
        for a,b,c in [(p,None,pins),(None,m,pins),(p,m,set())]:
            with self.assertRaises(ValueError):shadow.metadata_from_paths(a,b,c)
        self.assertIsNone(shadow.metadata_from_paths(None,None,set()))
    def test_all_three_cli_paths_forward_pinned_shadow_metadata_before_device_contact(self):
        artifacts={'prg':BUILD/'dos64-tests.prg','labels':BUILD/'dos64-tests.labels','map':BUILD/'dos64-tests.map',
                   'shadow-package':BUILD/'dos64-tests-overlay-package.json','shadow-memory':BUILD/'dos64-tests.memory.json'}
        with tempfile.TemporaryDirectory(dir=PROJECT/'agentworking/scratch') as directory:
            directory=Path(directory);identity={'pins':[shadow.sha(p.read_bytes()) for p in artifacts.values()]}
            (directory/'identity').write_text(json.dumps(identity));(directory/'media').write_text(json.dumps(MEDIA))
            (directory/'service').write_bytes(b'\x01\x08dummy');(directory/'staging').write_text('{}')
            common=['--host','no-device','--build-manifest',str(directory/'identity'),'--media-manifest',str(directory/'media'),
                    '--source',str(SOURCE),'--service',str(directory/'service'),'--expected-prg-sha256',shadow.sha(self.prg)]
            for option,path in artifacts.items():common.extend(['--'+option,str(path)])
            for name in ['c64u_native_application.py','c64u_native_ftp_put_runner.py','c64u_native_file_runner.py']:
                spec=importlib.util.spec_from_file_location('shadow_cli_'+name[:-3],ROOT/'build_support'/name)
                runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
                output=ROOT/'agentworking/runs/shadow-forwarding-no-device'
                args=common+['--output',str(output)]
                if name=='c64u_native_ftp_put_runner.py':args+=['--transport','ftp-put','--prepare-only']
                if name=='c64u_native_file_runner.py':args+=['--recovery','native-file','--validate-only','--staging-manifest',str(directory/'staging'),'--pal-clock-evidence','unused']
                kwargs={}
                if name=='c64u_native_file_runner.py':
                    kwargs={'base_prg':patch.object(runner.h,'base_prg',return_value=b'base'),
                            'clock':patch.object(runner,'clock_evidence',return_value={}),
                            'identities':patch.object(runner,'identities',return_value={})}
                with contextlib.ExitStack() as stack:
                    for item in kwargs.values():stack.enter_context(item)
                    stack.enter_context(patch.object(sys,'argv',[name,*args]))
                    constructor=stack.enter_context(patch.object(runner,'Application',side_effect=RuntimeError('local constructor stop')))
                    if hasattr(runner,'Client'):
                        client=stack.enter_context(patch.object(runner,'Client',side_effect=AssertionError('device contact')))
                    else:
                        client=stack.enter_context(patch.object(runner.h,'DeadlineClient',side_effect=AssertionError('device contact')))
                    with self.subTest(cli=name),self.assertRaisesRegex(RuntimeError,'local constructor stop'):
                        runner.main()
                    self.assertEqual(constructor.call_args.kwargs['shadow_metadata'],self.metadata)
                    client.assert_not_called()
    def test_unchanged_five_overlay_descriptor_does_not_require_shadow_artifacts(self):
        self.assertEqual(shadow.shadow_from_map(re.sub(r'^(HDBIOS|HDCODE)\s.*\n','',self.map,flags=re.M)),[])
        labels={k:v for k,v in self.labels.items() if not k.startswith('__HDB') and not k.startswith('__HDEXT') and k!='hdb_extension_ready'}
        labels={k:v for k,v in labels.items()if k!='__HDCODE_RUN__'}
        self.assertIsNone(shadow.prepare(b'\x01\x08',labels,[],None))
        with self.assertRaises(ValueError):shadow.prepare(self.prg,{},[],None)

if __name__=='__main__':unittest.main()
