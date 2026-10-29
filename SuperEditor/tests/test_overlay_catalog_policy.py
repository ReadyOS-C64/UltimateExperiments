"""Exhaustive byte/bit mutation proof for the single catalog identity policy."""
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from overlay_catalog_policy import catalog_identity, catalog_state, CatalogPolicyError

MANAGED=dict(se_overlay_managed_verification=1,se_overlay_capacity=64,se_overlay_fixed_entry=1)


def fixture():
    # Noncontiguous publication and poisoned unpublished metadata prove that
    # the helper never assumes a packed prefix or silently clears stale bytes.
    raw=bytearray((i*73+19)&255 for i in range(384))
    raw[:64]=bytes(64)
    for i,slot in ((0,0),(2,1),(17,0),(31,1),(46,1),(63,0)):
        raw[i]=i+1;raw[64+i]=slot
    return bytes(raw)


class CatalogPolicyTests(unittest.TestCase):
    def test_every_byte_bit(self):
        raw=fixture();identity=catalog_identity(raw,MANAGED)
        accepted_verification=0;rejected_or_different=0
        for at in range(384):
            for bit in range(8):
                changed=bytearray(raw);changed[at]^=1<<bit
                permitted=(64<=at<128 and raw[at-64]!=0 and bit==7)
                try:new=catalog_identity(changed,MANAGED)
                except CatalogPolicyError:
                    self.assertFalse(permitted,(at,bit));rejected_or_different+=1
                else:
                    if permitted:self.assertEqual(new,identity,(at,bit));accepted_verification+=1
                    else:self.assertNotEqual(new,identity,(at,bit));rejected_or_different+=1
        self.assertEqual(accepted_verification,6)
        self.assertEqual(rejected_or_different,3066)
        self.assertEqual(raw,fixture(),'input changed')

    def test_bit_state_is_not_normalized_away(self):
        raw=bytearray(fixture());raw[64+2]|=128
        state=catalog_state(raw,MANAGED)
        self.assertTrue(state.verified[2]);self.assertFalse(state.verified[0])
        self.assertIsNone(state.verified[1])
        clear=bytearray(raw);clear[64+2]&=127
        self.assertNotEqual(catalog_state(clear,MANAGED).verified,state.verified)
        self.assertEqual(catalog_identity(clear,MANAGED),catalog_identity(raw,MANAGED))

    def test_strict_flag_absent_or_zero(self):
        raw=fixture()
        for symbols in ({},dict(se_overlay_managed_verification=0)):
            self.assertEqual(catalog_identity(raw,symbols),raw)
            for i in (0,2,17,31,46,63):
                bad=bytearray(raw);bad[64+i]|=128
                with self.assertRaises(CatalogPolicyError):catalog_identity(bad,symbols)

    def test_every_slot_byte(self):
        raw=fixture()
        for flag in (0,1):
            for slot in range(256):
                changed=bytearray(raw);changed[64]=slot
                allowed=slot in ((0,1,128,129)if flag else(0,1))
                try:catalog_identity(changed,dict(se_overlay_managed_verification=flag))
                except CatalogPolicyError:self.assertFalse(allowed,(flag,slot))
                else:self.assertTrue(allowed,(flag,slot))

    def test_unpublished_is_fully_preserved(self):
        raw=fixture();self.assertEqual(raw[1],0)
        for field in range(1,6):
            for value in range(256):
                changed=bytearray(raw);changed[field*64+1]=value
                self.assertEqual(catalog_identity(changed,MANAGED)[field*64+1],value)
        changed=bytearray(raw);changed[65]^=128
        self.assertNotEqual(catalog_identity(changed,MANAGED),catalog_identity(raw,MANAGED))

    def test_layout_and_buffers(self):
        raw=fixture()
        for length in (0,64,192,383,385,512):
            with self.assertRaises(CatalogPolicyError):catalog_identity(bytes(length),MANAGED)
        for policy in (2,128,-1,None,True,'1'):
            with self.assertRaises(CatalogPolicyError):catalog_identity(raw,dict(se_overlay_managed_verification=policy))
        for symbols in (dict(MANAGED,se_overlay_capacity=48),dict(MANAGED,se_overlay_fixed_entry=0)):
            with self.assertRaises(CatalogPolicyError):catalog_identity(raw,symbols)
        for data in (list(raw),'x'*384):
            with self.assertRaises(CatalogPolicyError):catalog_identity(data,MANAGED)
        self.assertIsInstance(catalog_identity(memoryview(raw),MANAGED),bytes)
        import array
        with self.assertRaises(CatalogPolicyError):
            catalog_identity(memoryview(array.array('I',[0]*384)),MANAGED)


if __name__=='__main__':unittest.main()
