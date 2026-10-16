from pathlib import Path
import re,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"build_support"))
from verify_memory import verify
from overlay_package import append_shadow
class HDMemoryContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  p=Path("build");cls.mp=(p/"dos64-tests.map").read_text();cls.labels=(p/"dos64-tests.labels").read_text();cls.prg=(p/"dos64-tests.prg").read_bytes();cls.shadow=(p/"dos64-tests-resident.prg.hdb.bin").read_bytes();cls.cold=(p/"dos64-tests-resident.prg.import.bin").read_bytes();cls.payloads={name:(p/("dos64-tests-resident.prg."+leaf+".bin")).read_bytes()for name,leaf in [("FILECODE","files"),("RENDERCODE","render"),("INPUTCODE","input"),("IRQMAIN","pit"),("GFXCODE","gfx"),("HDCODE","hd"),("DISKCODE","disk")]}
 def check(self,**kw):
  args=dict(map_text=self.mp,labels_text=self.labels,prg=self.prg,overlay_payloads=self.payloads,import_payload=self.cold,shadow_payload=self.shadow,saver_payload=Path("build/dos64-tests-resident.prg.saver.bin").read_bytes());args.update(kw);return verify(**args)
 def changed_symbol(self,name):
  changed=re.sub(r"^(al )([0-9A-F]+)( \."+name+r")$",lambda m:m[1]+f"{int(m[2],16)+1:06X}"+m[3],self.labels,flags=re.M);self.assertNotEqual(changed,self.labels);return changed
 def test_real_six_payloads_shadow_and_excluded_vector_extent(self):
  r=self.check();self.assertTrue(r["passed"],r["errors"]);self.assertEqual(r["load"]["prg_bytes"],47105);self.assertEqual(r["load"]["startup_overlay_bytes"],16384);self.assertEqual(r["load"]["shadow"]["run"],0xf000);self.assertEqual(r["load"]["shadow"]["window_bytes"],3584)
 def test_every_shadow_source_byte_and_tail_byte_is_checked(self):
  for i in range(3584):
   b=bytearray(self.prg);b[0xa000-0x801+2+i]^=1;self.assertFalse(self.check(prg=b)["passed"],i)
 def test_every_HD_slot_payload_and_tail_byte_is_checked(self):
  for i in range(2048):
   b=bytearray(self.prg);b[0x9800-0x801+2+i]^=1;self.assertFalse(self.check(prg=b)["passed"],i)
 def test_every_shadow_and_HD_metadata_field_is_required(self):
  for area in ["HDEXT","HD"]:
   for suffix in ["START","SIZE","FILEOFFS","LAST"]:self.assertFalse(self.check(labels_text=self.changed_symbol("__"+area+"_"+suffix+"__"))["passed"])
  for area in ["HDBIOS","HDCODE"]:
   for suffix in ["LOAD","RUN","SIZE"]:self.assertFalse(self.check(labels_text=self.changed_symbol("__"+area+"_"+suffix+"__"))["passed"])
 def test_all_resident_guard_bytes_and_positions_are_checked(self):
  at=int(re.search(r"^al ([0-9A-F]+) \.dos64_cold_open$",self.labels,re.M)[1],16)
  for i in range(5):
   b=bytearray(self.prg);b[at-0x801+2+i]^=1;self.assertFalse(self.check(prg=b)["passed"])
  for name in ["hdb_boot_drive","hdb_extension_ready"]:self.assertFalse(self.check(labels_text=self.changed_symbol(name))["passed"])
 def test_missing_unpaired_or_corrupt_exact_shadow_cannot_verify(self):
  self.assertFalse(self.check(shadow_payload=None)["passed"])
  for shadow in [self.shadow[:-1],self.shadow+b"\0",bytes(len(self.shadow))]:self.assertFalse(self.check(shadow_payload=shadow)["passed"])
  for name in ["HDCODE","HDBIOS"]:self.assertFalse(self.check(map_text=re.sub("^"+name+r"\s.*\n","",self.mp,flags=re.M))["passed"])
 def test_packer_shadow_refuses_wrong_extent_length_and_every_metadata_change(self):
  base=self.prg[:0xa000-0x801+2];self.assertEqual(append_shadow(base,self.shadow,self.labels),self.prg[:0xae00-0x801+2])
  for b,s,l in [(base[:-1],self.shadow,self.labels),(base+b"\0",self.shadow,self.labels),(base,b"",self.labels),(base,bytes(3585),self.labels),(base,self.shadow[:-1],self.labels)]:
   with self.assertRaises(ValueError):append_shadow(b,s,l)
  for name in ["__HDEXT_START__","__HDEXT_SIZE__","__HDEXT_FILEOFFS__","__HDEXT_LAST__","__HDBIOS_LOAD__","__HDBIOS_RUN__","__HDBIOS_SIZE__"]:
   with self.assertRaises(ValueError):append_shadow(base,self.shadow,self.changed_symbol(name))
 def test_legacy_five_overlay_contract_remains_supported(self):
  mp=re.sub(r"^(HDCODE|HDBIOS|SAVERCODE|DISKCODE)\s.*\n","",self.mp,flags=re.M);mp=re.sub(r"^(NATIVESTATE\s+)([0-9A-F]{6})(\s+)[0-9A-F]{6}(\s+)[0-9A-F]{6}",lambda m:m[1]+m[2]+m[3]+f"{int(m[2],16)+2:06X}"+m[4]+"000003",mp,flags=re.M)
  labels=re.sub(r"^(al )([0-9A-F]+)( \.__MAIN_LAST__)$",lambda m:m[1]+f"{int(m[2],16)-2:06X}"+m[3],self.labels,flags=re.M)
  r=verify(mp,labels,self.prg[:0x9800-0x801+2],{k:v for k,v in self.payloads.items()if k not in ("HDCODE","DISKCODE")},self.cold);self.assertTrue(r["passed"],r["errors"]);self.assertEqual(r["load"]["startup_overlay_bytes"],10240);self.assertIsNone(r["load"]["shadow"])
if __name__=="__main__":unittest.main()
