from pathlib import Path
import sys,os
W=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.pycache_prefix=str(W/('.absent-close-binding-'+str(os.getpid())))
if Path(sys.pycache_prefix).exists():raise RuntimeError('Absent source-only cache')
import unittest,json,hashlib
import test_binding as fixtures
from close_binding import TakeoverREST,KnownCloseBackend
from close_contract import Contract,configure,HELPER_LABELS

class CloseModel:
 def __init__(self,model,configured,nonce):self.model=model;self.configured=configured;self.nonce=nonce;self.kind=None;self.closed=0;self.unknown=False;self.original_response=model.response;model.response=self.response
 def response(self,m,path,body):
  r=path[4:];queued=r=='machine:resume'and self.model.ram[0xc6]==8
  out=self.original_response(m,path,body)
  if m=='PUT'and r.startswith('machine:writemem?'):
   q=dict(v.split('=')for v in r.split('?')[1].split('&'));a=int(q['address'],16);b=bytes.fromhex(q['data'])
   if a+len(b)==0x801+len(self.configured)-2 and self.model.ram[0x801:a+len(b)]==self.configured[2:]:self.kind='close';self.model.kind='close'
  if queued and self.kind=='close':
   self.closed+=1;r=self.model.ram;r[HELPER_LABELS['entered']]=1
   for name,value in [('dos64_uci_upload_operand',0xc101),('dos64_uci_drain_operand',0xffff)]:a=HELPER_LABELS[name];r[a:a+2]=value.to_bytes(2,'little')
   d=bytearray(48);d[:5]=b'DCC1\xa5';d[8:12]=b'\0\1\1\2';d[16:32]=self.nonce;d[32]=9;d[35]=0x35;d[36]=0x24
   if self.unknown:d[8]=1;d[9]=0
   r[0x6000:0x6030]=d
  return out

class CloseTests(unittest.TestCase):
 def fixture(self):
  f=fixtures.Tests();f._cleanups=[];self.addCleanup(f.doCleanups);c,m,w,s,assets=f.lane();wire=TakeoverREST(w.host,w.streams,w.service,w._baseline,w.stager,factory=m,clock=c);wire.archive_request=lambda x:None;wire.archive_write=lambda *a:None;wire.archive_failure=lambda *a:None
  root=W/'close';main=(root/'inputs/build/dos64.prg').read_bytes();labels=(root/'inputs/build/dos64.labels').read_text();mp=(root/'inputs/build/dos64.map').read_text();ram=(root/'genuine-before-RAM.bin').read_bytes();ls={l.split()[2].lstrip('.'):int(l.split()[1],16)for l in labels.splitlines()if l.startswith('al ')};path=ram[ls['hdc_path']:].split(b'\0',1)[0]
  base=(root/'work/build/close.prg').read_bytes();cl=(root/'work/build/close.labels').read_text();nonce=bytes.fromhex('17280000000000000000000000000005');contract=Contract(main,labels,mp,path);configured=configure(base,HELPER_LABELS,nonce,contract,ram);model=CloseModel(m,configured,nonce);m.ram[:]=ram;saved={}
  backend=KnownCloseBackend(wire,main=main,labels=labels,map_text=mp,C_path=path,base=base,close_labels=cl,nonce=nonce,retained4M=s.baseline,save=lambda n,b:saved.__setitem__(n,b),clock=c,sleep=c.sleep)
  return c,m,wire,model,backend,saved
 def test_actual_wire_binding_source_before_SYS_and_terminal_close(self):
  c,m,w,cm,b,s=self.fixture();r=b.execute(60);assert r['state']=='KNOWN_CLOSED_QUIET'and cm.closed==1 and w.close_known
  assert len(s['live_MAIN_before_close.bin'])==65536 and len(s['close-cold-queued.bin'])==65536 and len(s['close-terminal.bin'])==65536
  assert b.io.ledger[0]['role']=='configured_source'and b.io.ledger[0]['ACKs']==26
  assert not any(x['method']=='POST'for x in m.calls)
  with self.assertRaises(ValueError):b.execute(60)
  assert cm.closed==1
 def test_current_BASIC_staging_wire_cannot_grant_live_close(self):
  c,m,w,cm,b,s=self.fixture();original=b.wire.__class__;assert original is TakeoverREST
  # The concrete physical constructor uses StageREST, never this derivative.
  from stage_transport import StageREST
  f=StageREST(w.host,w.streams,w.service,w._baseline,w.stager,factory=m,clock=c)
  with self.assertRaises(ValueError):KnownCloseBackend(f,main=b.main,labels=b.labels,map_text=b.map,C_path=b.path,base=b.base,close_labels=b.close_labels,nonce=b.nonce,retained4M=w._baseline,save=lambda *a:None)
 def test_unknown_terminal_never_grants_replacement(self):
  c,m,w,cm,b,s=self.fixture();cm.unknown=True
  with self.assertRaises(ValueError):b.execute(60)
  assert cm.closed==1 and not w.close_known
  with self.assertRaises(ValueError):b.takeover.verified()
 def test_fresh_MAIN_source_failure_precedes_reset_and_source_upload(self):
  c,m,w,cm,b,s=self.fixture();m.ram[0x1000]^=1
  with self.assertRaises(ValueError):b.execute(60)
  assert cm.closed==0 and not any(x['path']=='/v1/machine:reset'or'machine:writemem'in x['path']for x in m.calls)

if __name__=='__main__':unittest.main(verbosity=2)
