from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys,unittest,re
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('memory',ROOT/'build_support/verify_memory.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
spec=importlib.util.spec_from_file_location('pack',ROOT/'build_support/overlay_package.py');pack=importlib.util.module_from_spec(spec);spec.loader.exec_module(pack)
class NativeTextAssets(unittest.TestCase):
 def test_fonts_reproduce_offline_without_mutation(self):
  before={p:(p.stat().st_mtime_ns,p.read_bytes()) for p in (ROOT/'assets/native-text').iterdir() if p.is_file()}
  for name in ('native_text_font.py','narrow_font.py'):subprocess.run([sys.executable,str(ROOT/'build_support'/name),'--check'],check=True,capture_output=True)
  for p,(t,b) in before.items():self.assertEqual(t,p.stat().st_mtime_ns);self.assertEqual(b,p.read_bytes())
 def test_narrow_glyph_identity_design_and_spacing(self):
  rows=json.loads((ROOT/'assets/native-text/cp437-narrow4x8-rows.json').read_text());raw=(ROOT/'assets/native-text/cp437-narrow4x8.bin').read_bytes()
  self.assertEqual(len(raw),1024);self.assertNotEqual(rows[48],rows[79]);self.assertEqual(len({bytes(rows[ord(c)]) for c in '1Il'}),3)
  for c in range(33,127):self.assertTrue(any(rows[c]));self.assertTrue(all(v&1==0 for v in rows[c]))
  self.assertEqual(raw,bytes((r[y]<<4)|r[y+1] for r in rows for y in range(0,8,2)))
 def test_text_package_requires_both_contiguous_segments(self):
  labels=(ROOT/'build/dos64-tests.labels').read_text();payload=(ROOT/'build/dos64-tests-resident.prg.render.bin').read_bytes();pack.validate_text(payload,labels)
  for bad in (payload[:718],payload[:-1],payload+b'\x00'):
   with self.assertRaises(ValueError):pack.validate_text(bad,labels)
  changed=re.sub(r'(?m)^(al )([0-9A-F]+)( \.__DISPLAYCODE_RUN__)$',lambda x:x[1]+f'{int(x[2],16)+1:06X}'+x[3],labels)
  with self.assertRaises(ValueError):pack.validate_text(payload,changed)
 def test_loaded_fonts_and_matrix_gap_have_independent_contracts(self):
  mp=(ROOT/'build/dos64-tests.map').read_text();labels=(ROOT/'build/dos64-tests.labels').read_text();raw=(ROOT/'build/dos64-tests.prg').read_bytes()
  self.assertTrue(m.verify(mp,labels,raw)['passed'])
  for at in (0x43e8,0x43ff,0x4400,0x47ff,0x4800,0x4fff):
   b=bytearray(raw);b[at-0x801+2]^=1;self.assertFalse(m.verify(mp,labels,b)['passed'])
 def test_same_text_member_overlap_is_rejected(self):
  mp=(ROOT/'build/dos64-tests.map').read_text();labels=(ROOT/'build/dos64-tests.labels').read_text();changed=mp.replace('DISPLAYCODE           00CBCE  00CCBC','DISPLAYCODE           00CBCD  00CCBB');self.assertNotEqual(mp,changed);self.assertFalse(m.verify(changed,labels)['passed'])
 def test_manifest_includes_both_fonts_and_exact_text_payload(self):
  manifest=json.loads((ROOT/'build/manifest.json').read_text());package=json.loads((ROOT/'build/dos64-tests-overlay-package.json').read_text());self.assertEqual(package['payload_lengths'][1],957);self.assertEqual(package['text_members'],{'RENDERCODE':718,'DISPLAYCODE':239})
  for n in ('cp437-narrow4x8.bin','cp437-unscii8.bin'):
   p=Path('assets/native-text')/n;self.assertEqual(manifest['files'][str(p)],hashlib.sha256((ROOT/p).read_bytes()).hexdigest())
if __name__=='__main__':unittest.main()
