"""Independent packaging regressions. Actual sockets are localhost-only test children."""
import json,shutil,socket,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
PROJECT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(PROJECT/'build_support'))
from vice_process_owner import accepted_owner,ChildMonitorOwner,OwnedBinaryMonitor,lsof_tool
from build_iec_standalone import EXPECTED,check_build
import vice_iec_standalone as app
class OwnershipParsing(unittest.TestCase):
 def test_requires_pid_accepted_state_and_exact_four_tuple(self):
  good='p123\nf7\nn127.0.0.1:45678->127.0.0.1:56789\nTST=ESTABLISHED\n'
  self.assertTrue(accepted_owner(good,123,('127.0.0.1',45678),('127.0.0.1',56789)))
  for bad in [good.replace('p123','p999'),good.replace('56789','56788'),good.replace('ESTABLISHED','LISTEN'),good.replace('->127.0.0.1:56789',''),good+good]:self.assertFalse(accepted_owner(bad,123,('127.0.0.1',45678),('127.0.0.1',56789)))
 def test_no_command_after_losing_proved_ownership(self):
  class Owner:
   calls=0
   def require(self,**kw):
    self.calls+=1
    if self.calls>2:raise ValueError('ownership lost')
  class Sock:
   sent=[];incoming=b'\x02\x02\0\0\0\0\xaa\0\1\0\0\0'
   def sendall(self,b):self.sent.append(b)
   def recv(self,n):b=self.incoming[:n];self.incoming=self.incoming[n:];return b
  sock=Sock();monitor=OwnedBinaryMonitor(sock,Owner());monitor.call(0xaa)
  with self.assertRaises(ValueError):monitor.call(0xbb)
  self.assertEqual([packet[10] for packet in sock.sent],[0xaa])
 def test_collision_live_child_never_controls_foreign_monitor(self):
  commands=[];children=[]
  class Sock:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def bind(self,address):pass
   def getsockname(self):return ('127.0.0.1',56789)
   def getpeername(self):return ('127.0.0.1',56789)
   def settimeout(self,n):pass
   def close(self):pass
   def sendall(self,b):commands.append(b)
  class ForeignSock(Sock):
   def getsockname(self):return ('127.0.0.1',45678)
  class Child:
   pid=123;returncode=0
   def __init__(self,*a,**kw):self.alive=True;children.append(self)
   def poll(self):return None if self.alive else 0
   def wait(self,**kw):self.alive=False;return 0
   def kill(self):self.alive=False
  ticks=[0.0]
  def clock():ticks[0]+=.1;return ticks[0]
  def tool(argv,**kw):
   if 'd81' in argv:
    Path(argv[argv.index('d81')+1]).write_bytes(bytes(819200));return type('Prep',(),{'stdout':b'fixture','stderr':b''})()
   self.assertTrue(children[0].alive)
   return type('Inspect',(),{'returncode':0,'stdout':'p123\nf5\nn127.0.0.1:56788\nTST=LISTEN\n'})()
  with tempfile.TemporaryDirectory() as tmp:
   # Keep runtime inputs/build/source pins real; redirect only owned run output.
   local=Path(tmp);(local/'agentworking/runs').mkdir(parents=True)
   for folder in ['build','src','include','cfg','build_support']:
    shutil.copytree(PROJECT/folder,local/folder,ignore=shutil.ignore_patterns('*cache*','__pycache__'))
   with patch.object(app.socket,'socket',return_value=Sock()),patch.object(app.socket,'create_connection',return_value=ForeignSock()),patch.object(app.subprocess,'Popen',Child),patch.object(app.subprocess,'run',tool),patch.object(app.shutil,'which',return_value='/usr/bin/true'),patch.object(app.time,'monotonic',side_effect=clock),patch.object(app.time,'sleep',return_value=None):
    with self.assertRaises(ValueError):app.run(local,serial=True)
  self.assertEqual(commands,[]);self.assertFalse(children[0].alive)
class LauncherCleanup(unittest.TestCase):
 def test_proved_then_lost_connection_is_never_quit_during_cleanup(self):
  import struct
  packets=[]
  def response(typ,body,ident):return struct.pack('<BBIBBI',2,2,len(body),typ,0,ident)+body
  class Sock:
   incoming=response(0x82,b'\1\0\6\1\0\3ram',1)+response(0xaa,b'',2)
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def bind(self,address):pass
   def getsockname(self):return ('127.0.0.1',45678)
   def settimeout(self,n):pass
   def close(self):pass
   def sendall(self,b):packets.append(b[10])
   def recv(self,n):b=self.incoming[:n];self.incoming=self.incoming[n:];return b
  class Child:
   pid=123;alive=True
   def __init__(self,*a,**kw):pass
   def poll(self):return None if self.alive else 0
   def wait(self,**kw):self.alive=False;return 0
   def kill(self):self.alive=False
  class Owner:
   proof={'child_pid':123};count=0
   def __init__(self,*a,**kw):pass
   def require(self,**kw):
    self.count+=1
    if self.count>=4:raise ValueError('ownership lost during run')
    return self.proof
  def prep(argv,**kw):Path(argv[argv.index('d81')+1]).write_bytes(bytes(819200));return type('Prep',(),{'stdout':b'fixture','stderr':b''})()
  with tempfile.TemporaryDirectory() as tmp:
   local=Path(tmp)
   for folder in ['build','src','include','cfg','build_support']:shutil.copytree(PROJECT/folder,local/folder,ignore=shutil.ignore_patterns('*cache*','__pycache__'))
   with patch.object(app.socket,'socket',return_value=Sock()),patch.object(app.socket,'create_connection',return_value=Sock()),patch.object(app,'ChildMonitorOwner',Owner),patch.object(app.subprocess,'Popen',Child),patch.object(app.subprocess,'run',prep),patch.object(app.shutil,'which',return_value='/usr/bin/true'),patch.object(app.time,'sleep',return_value=None):
    with self.assertRaisesRegex(ValueError,'ownership lost'):app.run(local,serial=True)
  self.assertEqual(packets,[0x82,0xaa])

class ActualOwnership(unittest.TestCase):
 def start_server(self):
  script="import socket; s=socket.socket(); s.bind(('127.0.0.1',0)); s.listen(1); print(s.getsockname()[1],flush=True); c,p=s.accept(); print('accepted',flush=True); b=c.recv(1); print(len(b),flush=True); c.close();s.close()"
  child=subprocess.Popen([sys.executable,'-u','-c',script],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  self.addCleanup(self.finish,child);port=int(child.stdout.readline());sock=socket.create_connection(('127.0.0.1',port),timeout=2);self.addCleanup(sock.close);self.assertEqual(child.stdout.readline().strip(),'accepted');return child,sock
 @staticmethod
 def finish(child):
  if child.poll() is None:child.kill()
  child.communicate(timeout=3)
 def setUp(self):
  try:lsof_tool()
  except ValueError:self.skipTest('OS ownership lane requires lsof; launcher fails closed without it')
 def test_real_accepted_socket_belongs_to_exact_live_child(self):
  child,sock=self.start_server();owner=ChildMonitorOwner(child,sock,time.monotonic()+5);proof=owner.require(wait=True);self.assertEqual(proof['child_pid'],child.pid);self.assertEqual(tuple(proof['client']),sock.getsockname());self.assertEqual(tuple(proof['server']),sock.getpeername());sock.sendall(b'x');self.assertEqual(child.stdout.readline().strip(),'1')
 def test_real_foreign_socket_rejected_despite_live_unrelated_child(self):
  server,sock=self.start_server();unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);self.addCleanup(self.finish,unrelated)
  owner=ChildMonitorOwner(unrelated,sock,time.monotonic()+5)
  with self.assertRaises(ValueError):owner.require()
  self.assertIsNone(unrelated.poll());sock.shutdown(socket.SHUT_WR);self.assertEqual(server.stdout.readline().strip(),'0')
class MakeRecovery(unittest.TestCase):
 def test_actual_make_recovers_each_missing_product_with_json_stamp_retained(self):
  with tempfile.TemporaryDirectory() as tmp:
   project=Path(tmp)
   for n in ['Makefile','build_support/iec_standalone.mk','build_support/build_iec_standalone.py','src/iec_standalone.s','src/reu.s','include/abi.inc','include/reu.inc','cfg/dos64-iec-standalone.cfg']:
    path=project/n;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(PROJECT/n,path)
   def make():
    r=subprocess.run(['make','iec-standalone','DOS64_PYTHON='+sys.executable],cwd=project,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stdout+r.stderr);check_build(project)
   make();products=[project/'build/dos64-iec-standalone.json']
   for stem in ['dos64-iec-standalone','dos64-iec-standalone-small']:
    products.extend(project/'build'/(stem+'.'+suffix) for suffix in ['prg','map','labels'])
   rows=[]
   for product in products:
    product.unlink();stamp_retained=(project/'build/dos64-iec-standalone.json').exists();make();self.assertTrue(product.is_file(),str(product));self.assertTrue(all(p.is_file() for p in products));rows.append({'deleted_product':str(product.relative_to(project)),'json_stamp_retained_before_make':stamp_retained,'rebuilt':product.is_file(),'all_generated_products_present':all(p.is_file() for p in products),'full_prg_sha256':check_build(project)['outputs']['full']['sha256'],'small_prg_sha256':check_build(project)['outputs']['small']['sha256']})
   stamp=project/'build/dos64-iec-standalone.json';record=json.loads(stamp.read_text());record['outputs']={};stamp.write_text(json.dumps(record));make()
   before={str(p):p.stat().st_mtime_ns for p in products};make();self.assertEqual(before,{str(p):p.stat().st_mtime_ns for p in products})
   (PROJECT/'build/iec-make-recovery.json').write_text(json.dumps({'status':'passed','actual_make_invocations':10,'missing_products':rows,'incomplete_stamp_rebuilt':True,'valid_products_not_rebuilt':True},indent=2)+'\n')
if __name__=='__main__':unittest.main()
