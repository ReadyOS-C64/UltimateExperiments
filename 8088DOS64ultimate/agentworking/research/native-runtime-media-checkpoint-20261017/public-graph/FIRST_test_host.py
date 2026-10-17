from pathlib import Path
import sys,os
P=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-host-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import unittest,unittest.mock as mock,json,importlib.util,shutil,tempfile,hashlib
spec=importlib.util.spec_from_file_location('native_runtime_wrapper',P/'project/build_support/runtime_media.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
GOOD=json.loads((P/'build-native/RESULT.json').read_text());W=Path(GOOD['work']);records=[]
class Host(unittest.TestCase):
 def out(self,name):
  p=P/'host-controls'/name;p.mkdir(parents=True);m.atomic_json(p/'OWNER.json',m.OWNER);m.atomic_json(p/'RESULT.json',GOOD);return p,(p/'RESULT.json').read_bytes()
 def unchanged(self,p,old):
  self.assertEqual((p/'RESULT.json').read_bytes(),old)
  for x in GOOD['products'].values():self.assertEqual(m.digest(x['path']),{k:x[k]for k in ['sha256','bytes']})
 def fake_native(self,*args,**kw):
  # Host publication fault controls only. Native compilation is separately real.
  shutil.copytree(W,kw['cwd'],dirs_exist_ok=True);return None
 def test01_safe_inventory_paths(self):
  for s in ['/tmp/escape','../escape','x/../escape','x\\escape','x//b','']:
   with self.assertRaises(RuntimeError):m.safe(s)
  self.assertEqual(str(m.safe('tools/native_media/ui/panel.c')),'tools/native_media/ui/panel.c')
 def test02_actual_missing_make_include_rejects(self):
  q=P/'host-controls/missing-project';shutil.copytree(P/'project',q);inv=q/'build_support/runtime_media_sources.json';j=json.loads(inv.read_text());j['core'].remove('build_support/runtime_media.mk');inv.write_text(json.dumps(j));run=P/'host-controls/missing-run';run.mkdir()
  with mock.patch.object(m,'ROOT',q):
   with self.assertRaisesRegex(RuntimeError,'Missing Make include'):m.stage(run,{})
 def test03_mkdir_failure_preserves_prior_and_unlocks(self):
  p,old=self.out('mkdir');first=OSError('exact mkdir first')
  with mock.patch.object(m.tempfile,'mkdtemp',side_effect=first):
   try:m.build(p)
   except BaseException as caught:self.assertIs(caught,first)
   else:self.fail('missing exception')
  self.unchanged(p,old);self.assertFalse((p/'LOCK').exists())
 def test04_product_copy_interrupt_preserves_prior(self):
  p,old=self.out('copy');first=KeyboardInterrupt('exact product first');copy=shutil.copyfile
  def fail(s,d,*a,**k):
   if Path(d).parent.name=='products':raise first
   return copy(s,d,*a,**k)
  with mock.patch.object(m.subprocess,'run',side_effect=self.fake_native),mock.patch.object(m.shutil,'copyfile',side_effect=fail):
   try:m.build(p)
   except BaseException as caught:self.assertIs(caught,first)
   else:self.fail('missing exception')
  self.unchanged(p,old);self.assertFalse((p/'LOCK').exists())
 def test05_atomic_pointer_interrupt_preserves_prior(self):
  p,old=self.out('pointer');first=KeyboardInterrupt('exact pointer first');atomic=m.atomic_json
  def fail(q,v):
   if q==p/'RESULT.json':raise first
   return atomic(q,v)
  with mock.patch.object(m.subprocess,'run',side_effect=self.fake_native),mock.patch.object(m,'atomic_json',side_effect=fail):
   try:m.build(p)
   except BaseException as caught:self.assertIs(caught,first)
   else:self.fail('missing exception')
  self.unchanged(p,old);self.assertFalse((p/'LOCK').exists());runs=list(p.glob('run-*'));self.assertTrue((runs[0]/'RESULT.json').is_file())
 def test06_two_cleanup_errors_cannot_replace_first(self):
  p,old=self.out('cleanup');first=KeyboardInterrupt('exact primary');atomic=m.atomic_json;unlink=Path.unlink
  def fail(q,v):
   if q.name in ['FAILURE.json','LAST_FAILURE.json']:raise OSError('report second')
   return atomic(q,v)
  def badunlink(q,*a,**k):
   if q==p/'LOCK':raise OSError('unlink third')
   return unlink(q,*a,**k)
  with mock.patch.object(m.tempfile,'mkdtemp',side_effect=first),mock.patch.object(m,'atomic_json',side_effect=fail),mock.patch.object(Path,'unlink',badunlink):
   try:m.build(p)
   except BaseException as caught:self.assertIs(caught,first)
   else:self.fail('missing exception')
  self.unchanged(p,old);self.assertTrue((p/'LOCK').exists())
 def test07_distinct_owner_and_lock_refuse(self):
  p=P/'host-controls/foreign';p.mkdir();(p/'not-owned').write_text('KEEP')
  with self.assertRaises(RuntimeError):m.build(p)
  p,old=self.out('locked');(p/'LOCK').write_text('KEEP')
  with self.assertRaises(FileExistsError):m.build(p)
  self.unchanged(p,old);self.assertEqual((p/'LOCK').read_text(),'KEEP')
 def test08_source_package_has_no_private_or_vendor_dependencies(self):
  j=json.loads((P/'project/build_support/runtime_media_sources.json').read_text());self.assertEqual(j['schema'],1)
  for s in j['core']+list(j['media'].values()):
   m.safe(s);self.assertNotIn('agentworking',s);self.assertNotIn('third_party',s);self.assertNotIn('tests/',s);self.assertNotIn('model',s);self.assertFalse(s.upper().endswith(('.IMG','.EXE','.COM','.PRG','.MNU','.REL','.DLL','.DYLIB','.O')))
  self.assertFalse(any((P/'project/tools/native_media').rglob('*.prg')))
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Host));(P/'HOST_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'scope':'actual wrapper code host fault controls; publication controls use explicitly mocked native subprocess copied from separately real closed native build'},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
