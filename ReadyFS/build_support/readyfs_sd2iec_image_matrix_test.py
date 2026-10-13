#!/usr/bin/env python3
"""Safety gates must reject cleanup before any recovery PRG can run."""
import unittest
from unittest.mock import patch
from readyfs_sd2iec_baseline import Baseline
from readyfs_sd2iec_image_matrix import NativeImageMatrix

class CleanupTests(unittest.TestCase):
    def test_no_recovery_prg_while_command_or_mount_is_unresolved(self):
        for idle,mounted,fat in [(False,True,False),(False,False,True),(True,True,False),(True,False,False)]:
            with self.subTest(idle=idle,mounted=mounted,fat=fat):
                suite=NativeImageMatrix.__new__(NativeImageMatrix)
                suite.idle=idle;suite.maybe_mounted=mounted;suite.fat_verified=fat
                with patch.object(Baseline,'restore') as inherited:
                    with self.assertRaises(AssertionError):suite.restore()
                    inherited.assert_not_called()

    def test_confirmed_native_cleanup_allows_softwareiec_restoration(self):
        suite=NativeImageMatrix.__new__(NativeImageMatrix)
        suite.idle=True;suite.maybe_mounted=False;suite.fat_verified=True
        with patch.object(Baseline,'restore') as inherited:
            suite.restore();inherited.assert_called_once_with()

    def test_other_native_partitions_are_rejected_before_hardware_calls(self):
        suite=NativeImageMatrix.__new__(NativeImageMatrix)
        suite.c={};suite.sd={'root':'owned'};suite.sd_prefix='10.2:/owned/'
        with self.assertRaisesRegex(AssertionError,'partition1'):suite.run()

if __name__=='__main__':unittest.main()
