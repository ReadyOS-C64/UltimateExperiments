from pathlib import Path
import sys
W=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(W/'.absent-detached-test-cache')
if Path(sys.pycache_prefix).exists():raise RuntimeError('Absent source-only cache')
import json,hashlib,subprocess,tempfile,time,os,unittest,shutil
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
CHILD='''from pathlib import Path
import sys
W=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(W/'.absent-child-cache')
if Path(sys.pycache_prefix).exists():raise RuntimeError('Absent source-only cache')
import argparse,json,hashlib,os,stat
p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--sha',required=True);a=p.parse_args()
b=Path(a.manifest).read_bytes();assert hashlib.sha256(b).hexdigest()==a.sha
m=json.loads(b);assert m['schema']=='V1_NATIVE_SETUP_UI_PHYSICAL_PURPOSE_1'
assert os.getsid(0)==os.getpid()and not any(os.isatty(fd)for fd in [0,1,2])
assert stat.S_ISCHR(os.fstat(0).st_mode)and os.fstat(0).st_rdev==os.stat('/dev/null').st_rdev
s=(W/'detached/child.log').stat();assert all((os.fstat(fd).st_dev,os.fstat(fd).st_ino)==(s.st_dev,s.st_ino)for fd in [1,2])
(W/'CONTROL_RESULT.json').write_text(json.dumps({'status':'DETACHED_SURROGATE_PASS_NO_NETWORK','pid':os.getpid(),'parent':os.getppid(),'session':os.getsid(0),'terminal':os.environ['DOS64_TERMINAL_WINDOW'],'argv':sys.argv,'device_calls':0}))
'''
class Tests(unittest.TestCase):
 def make(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);p=Path(t.name).resolve();shutil.copyfile(W/'supervisor.py',p/'supervisor.py');(p/'launch.py').write_text(CHILD)
  script=(W/'dispatch-owned.sh').read_text();assert script.count(str(W))==1;(p/'dispatch-owned.sh').write_text(script.replace(str(W),str(p)))
  m={'schema':'V1_NATIVE_SETUP_UI_PHYSICAL_PURPOSE_1','entry':str(p/'launch.py'),'detached':str(p/'detached'),'watchdog_seconds':900,'interrupt_grace_seconds':120,'files':{str(p/n):sha(p/n)for n in ['supervisor.py','launch.py','dispatch-owned.sh']}}
  (p/'LAUNCH_MANIFEST.json').write_text(json.dumps(m));(p/'LAUNCH_SHA.txt').write_text(sha(p/'LAUNCH_MANIFEST.json')+'\n');return p,m
 def supervisor(self,p,extra=None):
  args=['/usr/bin/python3','-B',str(p/'supervisor.py'),'--entry',str(p/'launch.py'),'--manifest',str(p/'LAUNCH_MANIFEST.json'),'--sha',sha(p/'LAUNCH_MANIFEST.json'),'--output',str(p/'detached'),'--terminal','999999']
  if extra:args=extra(args)
  with(p/'test-supervisor.log').open('wb')as f:return subprocess.run(args,stdin=subprocess.DEVNULL,stdout=f,stderr=f,timeout=5).returncode
 def test_actual_wrapper_detaches_real_child_with_immutable_args_and_no_second_dispatch(self):
  p,m=self.make();start=time.monotonic();r=subprocess.run(['/bin/zsh',str(p/'dispatch-owned.sh')],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=dict(os.environ,DOS64_TERMINAL_WINDOW='999999'),timeout=3)
  self.assertEqual(r.returncode,0);self.assertLess(time.monotonic()-start,3);end=time.monotonic()+5
  while not(p/'detached/exit.json').exists():
   if time.monotonic()>end:self.fail('Owned detached surrogate did not close')
   time.sleep(.01)
  e=json.loads((p/'detached/exit.json').read_text());c=json.loads((p/'detached/child.json').read_text());s=json.loads((p/'detached/supervisor.json').read_text());marker=json.loads((p/'CONTROL_RESULT.json').read_text());self.assertEqual(e['child_exit_code'],0);self.assertFalse(e['wall_watchdog_triggered']);self.assertEqual(e['signals'],[]);self.assertEqual(marker['device_calls'],0);self.assertEqual(marker['pid'],c['pid']);self.assertEqual(marker['session'],c['pid']);self.assertEqual(marker['parent'],s['pid']);self.assertEqual(c['stdin'],'/dev/null');self.assertEqual(s['entry'],m['entry']);self.assertEqual(s['manifest_sha256'],sha(p/'LAUNCH_MANIFEST.json'));self.assertEqual(int((p/'supervisor.pid').read_text()),s['pid'])
  r=subprocess.run(['/bin/zsh',str(p/'dispatch-owned.sh')],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=dict(os.environ,DOS64_TERMINAL_WINDOW='999999'),timeout=3);self.assertNotEqual(r.returncode,0);self.assertEqual(json.loads((p/'detached/child.json').read_text())['pid'],c['pid'])
  # Durable bounded record survives temporary fixture cleanup; never a live device proof.
  out=W.parent/'DETACHED_CONTROL.json';out.write_text(json.dumps({'supervisor':s,'child':c,'exit':e,'surrogate':marker,'real_supervisor_source_sha256':sha(W/'supervisor.py'),'real_wrapper_sha256':sha(W/'dispatch-owned.sh'),'only_fixture_wrapper_delta':'TASK absolute directory','device_calls':0},indent=2)+'\n')
 def test_wrong_schema_output_or_hash_refuses_before_child(self):
  for field,val in [('schema','HYBRID_RECOVERY_PHYSICAL_PURPOSE_1'),('detached','/wrong-output')]:
   p,m=self.make();m[field]=val;(p/'LAUNCH_MANIFEST.json').write_text(json.dumps(m));self.assertNotEqual(self.supervisor(p),0);self.assertFalse((p/'detached').exists());self.assertFalse((p/'CONTROL_RESULT.json').exists())
  p,m=self.make();self.assertNotEqual(self.supervisor(p,lambda a:[('0'*64 if v==sha(p/'LAUNCH_MANIFEST.json')else v)for v in a]),0);self.assertFalse((p/'detached').exists())
 def test_real_wrapper_arguments_and_only_intended_supervisor_schema_delta(self):
  old=W.parents[1]/'native-fast-file-put-recovery-runnable-20261017/work';a=(old/'supervisor.py').read_text();b=(W/'supervisor.py').read_text();self.assertEqual(a.replace("FAST_NATIVE_FILE_PUT_PHYSICAL_PURPOSE_1","V1_NATIVE_SETUP_UI_PHYSICAL_PURPOSE_1"),b)
  self.assertEqual((old/'dispatch-owned.sh').read_text().replace(str(old),str(W)),(W/'dispatch-owned.sh').read_text())
if __name__=='__main__':unittest.main()
