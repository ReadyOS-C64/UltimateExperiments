#!/usr/bin/env python3
"""Admission and cleanup proof for the read-only retained-image type check."""
import unittest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from readyfs_sd2iec_baseline import Baseline
from readyfs_sd2iec_final_hardware import FinalBaseline, retained_types

class FinalTests(unittest.TestCase):
    def fixture(self):
        names = [f'{op}-{src}d{kind}123456.{ext}' for op in ('bc','bd')
                 for src,kind,ext in [('h','s','seq'),('h','p','prg'),('h','u','usr'),
                                      ('i','s','seq'),('s','s','seq')]] + ['bf123456']
        return {'image-oracle-'+name:{'kind':'file'} for name in names}

    def test_complete_types_cover_all_native_copy_move_and_bridge_targets(self):
        result = retained_types(self.fixture())
        self.assertEqual(len(result),12)
        self.assertEqual(set(result.values()),{'10','11','12'})
        self.assertEqual(result['bc-hdp123456.prg'],'11')
        self.assertEqual(result['bd-hdu123456.usr'],'12')
        self.assertEqual(result['xu123456'],'12')

    def test_missing_target_is_not_a_partial_pass(self):
        data=self.fixture();del data['image-oracle-bd-hdu123456.usr']
        with self.assertRaises(AssertionError):retained_types(data)

    def test_wrong_extension_unknown_name_and_mixed_runs_rejected(self):
        for old,new in [('bc-hdp123456.prg','bc-hdp123456.seq'),
                        ('bc-hdp123456.prg','bc-hdp999999.prg'),
                        ('bc-hdp123456.prg','unrelated')]:
            data=self.fixture();data['image-oracle-'+new]=data.pop('image-oracle-'+old)
            with self.subTest(name=new),self.assertRaises(AssertionError):retained_types(data)

    def test_unresolved_native_state_never_reaches_recovery_prg(self):
        for idle,mounted,fat in [(False,False,True),(True,True,False),(True,False,False)]:
            suite=FinalBaseline.__new__(FinalBaseline)
            suite.idle=idle;suite.maybe_mounted=mounted;suite.fat_verified=fat
            with patch.object(Baseline,'restore') as inherited:
                with self.assertRaises(AssertionError):suite.restore()
                inherited.assert_not_called()

    def test_restored_state_allows_existing_restore(self):
        suite=FinalBaseline.__new__(FinalBaseline)
        suite.idle=True;suite.maybe_mounted=False;suite.fat_verified=True
        with patch.object(Baseline,'restore') as inherited:
            suite.restore();inherited.assert_called_once_with()

    def exercise(self, failure=None):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);prior=root/'logs/readyfs_c64u/matrix';prior.mkdir(parents=True)
            cases=['sd-image-matrix-independent-host-bytes',
                   'ultimate-contained-image-seq-prg-usr-independent-bytes-types-removal',
                   'sd-fat-to-own-image-and-back-via-explicit-intermediate']
            events=[{'case':case,'result':'PASS'} for case in cases]
            events.append({'complete':True,'restored':True,'result':'PASS'})
            (prior/'events.jsonl').write_text('\n'.join(map(json.dumps,events))+'\n')
            (prior/'continued-native-image.json').write_text(json.dumps({'scope':{
                'owner':'marker','path':'10.1:/rf123/out/i1234567890.d64'}}))
            (prior/'native-image-matrix-snapshot.json').write_text(json.dumps(self.fixture()))
            commands=[];saved={};last=['']
            def keys(value):
                if isinstance(value,str):commands.append(value);last[0]=value
            def wait(*args,**kwargs):
                if failure=='timeout' and last[0].startswith('STAT '):raise TimeoutError('pending')
            def check(name,needle):
                if failure=='type' and needle.startswith('TYPE: $'):raise AssertionError('bad type')
            suite=FinalBaseline.__new__(FinalBaseline)
            suite.sd={'marker':'marker'};suite.sd_prefix='10.1:/rf123/'
            suite.c={'ROOT':root,'save_json':lambda name,data:saved.update({name:data}),
                     'command':lambda *a,**k:None,'event':lambda **k:None,
                     'keys':keys,'wait_ready':wait,'check':check,'capture':lambda name:'screen'}
            with patch.dict(os.environ,{'READYFS_SD2IEC_IMAGE_RUN':str(prior)}), \
                 patch.object(Baseline,'run'), patch.object(Baseline,'guard'), \
                 patch('readyfs_sd2iec_final_hardware.time.sleep'):
                if failure:
                    with self.assertRaises(AssertionError):suite.run()
                else:suite.run()
            return suite,commands,saved

    def test_actual_run_checks_all_types_then_fat_bridge_and_restores(self):
        suite,commands,saved=self.exercise()
        self.assertEqual(sum(command.startswith('STAT ') for command in commands),13)
        self.assertEqual(commands[-1],'STAT 10.1:/rf123/out/br123456.prg')
        self.assertEqual(len(saved['retained-native-image-type-screens.json']),13)
        self.assertTrue(suite.idle and suite.fat_verified and not suite.maybe_mounted)

    def test_type_failure_still_returns_to_verified_fat(self):
        suite,commands,_=self.exercise('type')
        self.assertIn('DISMOUNT 10.1:/ --force',commands)
        self.assertEqual(commands[-1],'IEC 10: PARTITION 1')
        self.assertTrue(suite.idle and suite.fat_verified and not suite.maybe_mounted)

    def test_pending_stat_does_not_inject_cleanup(self):
        suite,commands,_=self.exercise('timeout')
        self.assertTrue(commands[-1].startswith('STAT '))
        self.assertFalse(any(command.startswith('DISMOUNT ') for command in commands))
        self.assertFalse(suite.idle or suite.fat_verified)
        self.assertTrue(suite.maybe_mounted)

if __name__=='__main__':unittest.main()
