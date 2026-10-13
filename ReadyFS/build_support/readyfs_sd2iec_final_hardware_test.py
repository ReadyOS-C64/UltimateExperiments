#!/usr/bin/env python3
"""Admission and cleanup proof for the read-only retained-image type check."""
import unittest
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

if __name__=='__main__':unittest.main()
