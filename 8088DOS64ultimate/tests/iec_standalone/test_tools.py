"""Synthetic verifier-policy shapes are not target-execution evidence."""
import json,shutil,struct,sys,tempfile,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(PROJECT/'build_support'))
from vice_monitor import BinaryMonitor
from verify_iec_standalone import verify,pattern,seed,sha,derived
from build_iec_standalone import EXPECTED,check_build
class Socket:
 def __init__(self,data):self.data=data;self.sent=b''
 def recv(self,n):part=self.data[:min(n,3)];self.data=self.data[len(part):];return part
 def sendall(self,b):self.sent+=b
def reply(t,b=b'',i=1,e=0):return struct.pack('<BBIBBI',2,2,len(b),t,e,i)+b
class MonitorTests(unittest.TestCase):
 def test_integer(self):self.assertEqual(BinaryMonitor(Socket(reply(0x51,b'\x01\x04\0\x10\0\0'))).resource('REUsize'),4096)
 def test_events_memory(self):self.assertEqual(BinaryMonitor(Socket(reply(0x62,b'xx',0xffffffff)+reply(1,b'\x02\0\xaa\xbb'))).read(0,1,1),b'\xaa\xbb')
 def test_bad_responses(self):
  for raw in [reply(1,i=2),reply(2),reply(1,e=1),b'\3'+reply(1)[1:],struct.pack('<BBIBBI',2,2,1048577,1,0,1)]:
   with self.assertRaises(ValueError):BinaryMonitor(Socket(raw)).call(1)
 def test_truncated(self):
  with self.assertRaises(EOFError):BinaryMonitor(Socket(reply(1,b'xyz')[:-1])).call(1)
 def test_banks(self):self.assertEqual(BinaryMonitor(Socket(reply(0x82,b'\1\0\6\1\0\3ram'))).banks(),{'ram':1})
 def test_bad_banks(self):
  with self.assertRaises(ValueError):BinaryMonitor(Socket(reply(0x82,b'\1\0\6\1\0\2ram'))).banks()
 def test_short_memory(self):
  with self.assertRaises(ValueError):BinaryMonitor(Socket(reply(1,b'\2\0\xaa'))).read(0,1,1)
 def test_bad_resource(self):
  with self.assertRaises(ValueError):BinaryMonitor(Socket(reply(0x51,b'\2\0'))).resource('REU')
 def test_range(self):
  with self.assertRaises(ValueError):BinaryMonitor(Socket(b'')).read(2,1,1)
class BuildChecks(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.project=Path(self.tmp.name);manifest=json.loads((PROJECT/'build/dos64-iec-standalone.json').read_text())
  names=list(manifest['source_files'])+['build/dos64-iec-standalone.json']
  for row in manifest['outputs'].values():names.extend([row['prg'],str(Path(row['prg']).with_suffix('.labels')),str(Path(row['prg']).with_suffix('.map'))])
  for name in names:
   dest=self.project/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(PROJECT/name,dest)
 def tearDown(self):self.tmp.cleanup()
 def test_sources_complete(self):self.assertEqual(len(check_build(self.project)['outputs']),2)
 def test_changed_source_rejected(self):
  (self.project/'include/reu.inc').write_text('changed')
  with self.assertRaises(ValueError):check_build(self.project)
 def test_changed_labels_rejected(self):
  (self.project/'build/dos64-iec-standalone.labels').write_text('changed')
  with self.assertRaises(ValueError):check_build(self.project)
class VerifierTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.run=Path(self.tmp.name);self.make()
 def tearDown(self):self.tmp.cleanup()
 def make(self,case='original'):
  base=seed();payload=derived(base,case);prg=(PROJECT/'build/dos64-iec-standalone-small.prg').read_bytes();ram=bytearray(65536);start=int.from_bytes(prg[:2],'little');ram[start:start+len(prg)-2]=prg[2:]
  symbols={l.split()[2].lstrip('.'):int(l.split()[1],16) for l in (PROJECT/'build/dos64-iec-standalone-small.labels').read_text().splitlines() if l.startswith('al ')};ram[symbols['started']]=1
  ram[0xf000:0xfe00]=bytes((i&255)^0xa5 for i in range(3584));ram[0xbfff]=0xa7;ram[0xc200]=0x5a
  err={'original':0,'short':4,'long':4,'crc':6,'missing':3}[case];count=0 if case=='missing' else 511 if case=='short' else 512;chunks=int(case in ('original','crc'))
  mb=bytearray(32);mb[0]=0xe1 if err else 0xa5;mb[1]=err;mb[2]=0x42 if case=='missing' else 0 if case=='long' else 0x40;mb[3]=int(case!='missing');mb[4:7]=count.to_bytes(3,'little');mb[7:9]=chunks.to_bytes(2,'little');mb[9:13]=(0x1c613576).to_bytes(4,'little');mb[13]=int(not err);mb[14]=int(not err);mb[15]=int(case not in ('missing','long'));mb[19]=0 if err else 5;mb[20:22]=b'00';mb[16]=payload[count-1] if count else 0
  if case=='missing':ram[0x2005:0x2007]=b'62'
  ram[0x6000:0x6020]=mb;reu=bytearray(pattern());reu[0x100000:0x100000+chunks*512]=payload[:chunks*512]
  for n,raw in [('ram.bin',ram),('reu.img',reu),('input.img',payload),('container.d81',(b'SYNTHETIC TOOLING FIXTURE'+bytes(819200-25)))]:(self.run/n).write_bytes(raw)
  self.meta={'case':case,'prg_sha256':EXPECTED['small'],'source_sha256':sha(base),'source_bytes':512,'payload_sha256':sha(payload),'payload_bytes':len(payload),'mailbox_hex':mb.hex(),'d81_sha256':sha((b'SYNTHETIC TOOLING FIXTURE'+bytes(819200-25))),'resources':{'REU':1,'REUsize':4096,'Drive8Type':1581,'Drive8TrueEmulation':1,'TrapDevice8':0,'MachineVideoStandard':1}};self.save()
 def save(self):(self.run/'result.json').write_text(json.dumps(self.meta))
 def mutation(self,name,offset):raw=bytearray((self.run/name).read_bytes());raw[offset]^=1;(self.run/name).write_bytes(raw)
 def test_synthetic_shapes(self):
  for case in ['original','short','long','crc','missing']:self.make(case);self.assertEqual(verify(self.run,PROJECT)['status'],'passed')
 def test_rejects_executable(self):
  self.mutation('ram.bin',0x80d)
  with self.assertRaises(ValueError):verify(self.run,PROJECT)
 def test_rejects_outside_reu(self):
  self.mutation('reu.img',0x3fffff)
  with self.assertRaises(ValueError):verify(self.run,PROJECT)
 def test_rejects_payload(self):
  self.mutation('input.img',123)
  with self.assertRaises(ValueError):verify(self.run,PROJECT)
 def test_rejects_truncation(self):
  (self.run/'ram.bin').write_bytes(b'x')
  with self.assertRaises(ValueError):verify(self.run,PROJECT)
 def test_rejects_mailbox(self):
  self.meta['mailbox_hex']='00'*32;self.save()
  with self.assertRaises(ValueError):verify(self.run,PROJECT)
 def test_rejects_live_lfn(self):
  self.mutation('ram.bin',0x98)
  with self.assertRaises(ValueError):verify(self.run,PROJECT)
 def test_rejects_unknown_binary(self):
  self.meta['prg_sha256']='00'*32;self.save()
  with self.assertRaises(ValueError):verify(self.run,PROJECT)
 def test_rejects_wrong_config(self):
  self.meta['resources']['TrapDevice8']=1;self.save()
  with self.assertRaises(ValueError):verify(self.run,PROJECT)
 def test_rejects_d81(self):
  self.mutation('container.d81',0)
  with self.assertRaises(ValueError):verify(self.run,PROJECT)
if __name__=='__main__':unittest.main()
