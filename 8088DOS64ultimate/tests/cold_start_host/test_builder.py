from pathlib import Path
import sys,os
ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True;sys.pycache_prefix=str(ROOT/'build'/('.absent-cold-host-'+str(os.getpid())))
import importlib.util,json,tempfile,unittest,unittest.mock as mock,hashlib,subprocess,shutil
s=importlib.util.spec_from_file_location('cold_tested',ROOT/'build_support/cold_start.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
R=Path(os.environ['DOS64_RUNTIME_RESULT']).resolve()
class Cold(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def altered(self,change):
  j=json.loads(R.read_text());change(j);p=self.p/'runtime.json';p.write_text(json.dumps(j));return p
 def test01_actual_source_build(self):
  j=m.build(self.p/'out',R);self.assertEqual(set(j['assets']),set(m.ASSETS));self.assertEqual({p.name for p in Path(j['bundle']).iterdir()},set(m.ASSETS));self.assertEqual(j['layout']['START_bytes'],20480);m.verify(j['source_inputs']);m.verify(j['native_products'])
  self.assertEqual(json.loads((Path(j['run'])/'RESULT.json').read_text()),json.loads((self.p/'out/RESULT.json').read_text()))
 def test02_wrong_role(self):
  with self.assertRaisesRegex(RuntimeError,'runtime-media'):m.build(self.p/'out',self.altered(lambda j:j.update(role='unit')))
 def test03_declared_input_mismatch(self):
  def change(j):j['source_inputs'][str(R)]={'sha256':'0'*64,'bytes':R.stat().st_size}
  with self.assertRaisesRegex(RuntimeError,'changed'):m.build(self.p/'out',self.altered(change))
 def test04_unused_declared_product_mismatch(self):
  def change(j):j['products']['EXTRA']={'path':str(R),'sha256':'0'*64,'bytes':R.stat().st_size}
  with self.assertRaisesRegex(RuntimeError,'product mismatch'):m.build(self.p/'out',self.altered(change))
 def test05_asset_mismatch(self):
  def change(j):j['assets']['DOS64.PRG']['bytes']+=1
  with self.assertRaisesRegex(RuntimeError,'asset identity'):m.build(self.p/'out',self.altered(change))
 def test06_explicit_bad_compiler(self):
  with mock.patch.dict(os.environ,{'DOS64_CC65':'/nonexistent/explicit-cold-cc65'}):
   with self.assertRaisesRegex(RuntimeError,'DOS64_CC65'):m.build(self.p/'out',R)
  self.assertFalse((self.p/'out/RESULT.json').exists());self.assertFalse((self.p/'out/LOCK').exists())
 def test07_interruption_preserves_pointer_first_cause(self):
  out=self.p/'out';out.mkdir();m.atomic_json(out/'OWNER.json',m.OWNER);(out/'RESULT.json').write_text('prior-exact-pointer');first=KeyboardInterrupt('first-cold-interruption');original=m.atomic_json
  def reporting(p,v):
   if p.name in ['FAILURE.json','LAST_FAILURE.json']:raise OSError('secondary-report')
   return original(p,v)
  with mock.patch.object(m,'link',side_effect=first),mock.patch.object(m,'atomic_json',side_effect=reporting):
   with self.assertRaises(KeyboardInterrupt)as caught:m.build(out,R)
  self.assertIs(caught.exception,first);self.assertEqual((out/'RESULT.json').read_text(),'prior-exact-pointer');self.assertFalse((out/'LOCK').exists())
 def test08_existing_lock_owned_elsewhere(self):
  out=self.p/'out';out.mkdir();m.atomic_json(out/'OWNER.json',m.OWNER);(out/'LOCK').write_text('other')
  with self.assertRaises(FileExistsError):m.build(out,R)
  self.assertEqual((out/'LOCK').read_text(),'other')
 def test09_hostile_compiler_environment(self):
  poison=self.p/'poison';poison.mkdir();(poison/'string.h').write_text('#error HOSTILE_CC65_INC_USED\n')
  with mock.patch.dict(os.environ,{k:str(poison)for k in ['CC65_HOME','CC65_INC','CA65_INC','LD65_LIB','LD65_CFG','PYTHONPATH','PYTHONPYCACHEPREFIX']}):j=m.build(self.p/'out',R)
  self.assertEqual(j['status'],'passed');self.assertFalse(any(str(poison)in q for q in j['source_inputs']))
 def test10_default_launcher_descriptor_unchanged(self):
  helper=m.module(ROOT/'build_support/start_launcher.py','cold_default_helper');import inspect
  self.assertIn('cold=False',str(inspect.signature(helper.build)))
  descriptor=m.module(ROOT/'build_support/start_template_descriptor.py','cold_default_desc');self.assertFalse(inspect.signature(descriptor.make).parameters['start20k'].default)
 def test11_public_make_target(self):
  r=subprocess.run([shutil.which(os.environ.get('DOS64_MAKE','make')),'-n','cold-start','RUNTIME_MEDIA_RESULT='+str(R),'DOS64_PYTHON='+sys.executable],cwd=ROOT,capture_output=True,text=True,check=True)
  self.assertIn(sys.executable+' -B build_support/cold_start.py',r.stdout)
  self.assertNotIn('agentworking',r.stdout.splitlines()[-1].split(' --runtime-result ')[0])
if __name__=='__main__':unittest.main()
