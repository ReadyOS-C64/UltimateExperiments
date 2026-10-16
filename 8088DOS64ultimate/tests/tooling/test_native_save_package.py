"""Exact seventh-asset packaged memory and copied-code source checks."""
import copy,hashlib,importlib.util,json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('save_shadow',ROOT/'build_support/c64u_native_shadow_identity.py');shadow=importlib.util.module_from_spec(spec);spec.loader.exec_module(shadow)
class NativeSavePackage(unittest.TestCase):
 def inputs(self,stem='dos64-tests'):
  prg=(ROOT/'build'/f'{stem}.prg').read_bytes();labels={n.lstrip('.'):int(a,16)for a,n in re.findall(r'^al ([0-9A-Fa-f]+) (\S+)',(ROOT/'build'/f'{stem}.labels').read_text(),re.M)}
  segments=shadow.shadow_from_map((ROOT/'build'/f'{stem}.map').read_text());meta={'package':json.loads((ROOT/'build'/f'{stem}-overlay-package.json').read_text()),'memory':json.loads((ROOT/'build'/f'{stem}.memory.json').read_text())};return prg,labels,segments,meta
 def test_both_roles_exact_loaded_extent_and_modal_budget(self):
  for stem in ['dos64','dos64-tests']:
   prg,labels,segments,meta=self.inputs(stem);shadow.prepare(prg,labels,segments,meta);self.assertEqual(45057,len(prg));self.assertEqual(1543,labels['__SAVERCODE_SIZE__']);self.assertEqual(2866,labels['__HDBIOS_SIZE__'])
   self.assertEqual(27,meta['memory']['load']['startup_cache_phase']['cache_frames']);self.assertEqual(28,meta['memory']['load']['startup_cache_phase']['span_cache_frames']);self.assertEqual([23],meta['memory']['load']['startup_cache_phase']['gap_cache_frames'])
 def reject(self,change):
  prg,labels,segments,meta=self.inputs();prg=bytearray(prg);change(prg,labels,segments,meta);meta['package']['sha256']['packaged_prg']=hashlib.sha256(prg).hexdigest()
  with self.assertRaises(ValueError):shadow.prepare(bytes(prg),labels,segments,meta)
 def test_source_gap_nonzero_rejected(self):self.reject(lambda p,l,s,m:p.__setitem__(0xae00-0x801+2,1))
 def test_wrong_saver_header_rejected(self):self.reject(lambda p,l,s,m:p.__setitem__(0xb000-0x801+2+5,6))
 def test_wrong_saver_run_rejected(self):self.reject(lambda p,l,s,m:m['package']['saver'].__setitem__('run',0xc900))
 def test_unpaired_saver_metadata_rejected(self):self.reject(lambda p,l,s,m:m['memory']['load'].__setitem__('saver',None))
 def test_span_does_not_hide_gap_frame(self):self.reject(lambda p,l,s,m:m['package']['startup_cache_phase'].__setitem__('cache_frames',28))
 def test_payload_mutation_requires_fresh_bound_identity(self):self.reject(lambda p,l,s,m:p.__setitem__(0xb010-0x801+2+33,p[0xb010-0x801+2+33]^0x80))
 def test_missing_saver_link_symbol_rejected(self):self.reject(lambda p,l,s,m:l.__setitem__('__SAVERCODE_SIZE__',0))
if __name__=='__main__':unittest.main()
