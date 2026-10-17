from pathlib import Path
import os,sys
P=Path(__file__).resolve().parent;assert Path.cwd()==P
sys.dont_write_bytecode=True;sys.pycache_prefix=str(P/('.absent-insert-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists();os.environ['DOS64_MEDIA_TEST_ROLE']='runtime'
import ctypes as C,json,zlib,unittest
from controller_fixture import initial
from fixture_base import L,symbols,labels,load,reu,resign,headers,NEW_B
from test_online_save import Machine,Regs
# Deterministic caller-owned elapsed clock; no physical elapsed/performance claim.
def call(self,n,budget=2000000):
 ret=0x02ff;self.p(0x1ff,ret>>8);self.p(0x1fe,ret&255);L.dos64_set_regs(self.m,Regs(symbols[n],0xfd,0x71,0x82,0x93,0x24,0,0));r=L.dos64_run(self.m,0x0300,budget);assert r.status==0,(n,r.status,hex(r.regs.pc));L.dos64_cia_clock_advance(self.m,1);return r
Machine.call=call
TW=labels('phase/transaction-wire.labels');MB=labels('binding/binding.labels');symbols.update(TW);symbols.update(MB)
def seed(m,a,b):L.bulk_reu_seed(m.m,a,b,len(b))
def file_seed(m,p,b):L.bulk_model_seed(m.m,p,b,len(b))
def native(m,op,drive,flags=1,crc=0):
 fq=bytearray(27);fq[0]=op;fq[1]=drive;fq[2]=flags;fq[3]=0xa5;fq[4]=4;fq[15:19]=m.get(symbols['dos64_disk_mount_generation']+4*drive,4);fq[19:23]=m.get(symbols['dos64_disk_content_generation']+4*drive,4);fq[23:27]=crc.to_bytes(4,'little');m.put('dos64_floppy_request',fq);r=m.call('dos64_overlay_floppy_control');assert not(r.regs.p&1),(op,m.g('dos64_floppy_status'));return m.get('dos64_floppy_request',27)
def prepared(t,target=1,drive=1,kind='live'):
 m,old,f=initial(t,target,drive,0x10)
 try:
  if kind=='ejected':native(m,4,drive,2)
  if kind=='empty':
   assert drive==1;m.put('dos64_disk_b_descriptor',bytes(10));old=bytearray(old);old[264:392]=bytes(128);old[524]&=~2;old[525]&=~2;old[532:536]=bytes(4);old=resign(old);file_seed(m,b'/usb1/Owned/DOS64.CFG',old)
   for at,b in [(0x3ff020,old),(0x3ff000,headers(old)[0]),(0x3ff500,headers(old)[1])]:seed(m,at,b)
   m.put(symbols['dos64_disk_binding']+4,bytes(4))
  crc=zlib.crc32(NEW_B);fq=bytearray(native(m,1,drive,3,crc));fq[3]=0xa5;m.put('dos64_floppy_request',fq);base=int.from_bytes(fq[5:8],'little');seed(m,base,NEW_B)
  snap=m.get('dos64_disk_reu_base',10)+m.get('dos64_disk_b_descriptor',32);path=b'/sd/Incoming/NEW.IMG';file_seed(m,path,NEW_B)
  new=bytearray(old);off=264 if drive else 136;new[off:off+128]=path.ljust(128,b'\0');new[524]|=1<<drive;new[525]|=1<<drive;new[528+4*drive:532+4*drive]=crc.to_bytes(4,'little');new=resign(new)
  journal=bytearray(128);journal[:7]=b'D64J\1\4\5';journal[8]=drive;journal[9]=1;journal[10:12]=b'\1\0';journal[12:54]=snap;journal[54:58]=crc.to_bytes(4,'little');journal+=old+new;jcrc=zlib.crc32(journal);journal+=jcrc.to_bytes(4,'little')
  ledger=bytearray([2,0,drive,0xa5])+path.ljust(128,b'\0')+snap+crc.to_bytes(4,'little')+b'\xa5'+jcrc.to_bytes(4,'little')+b'\1'+fq;assert len(ledger)==211
  for at,b in [(0x3e0000,old),(0x3e0300,new),(0x3e0600,journal)]:seed(m,at,b)
  m.put(0x7f00,ledger);load(m,'phase/transaction-wire.prg');m.put('__BSS_RUN__',bytes(0)) if False else None
  # Every phase entry explicitly initializes its own BSS; WIRE has no crt entry.
  m.put(0x7d00,bytes(0x16f));m.put(TW['tw_home'],b'/usb1/Owned\0'.ljust(128,b'\0'));m.wide(TW['tw_sequence'],1,2);m.p(TW['tw_mode'],4);m.wide(TW['tw_limit'],32767,2)
  return m,bytes(old),bytes(new),{'base':base,'fq':bytes(fq),'snapshot':snap,'C':m.get('dos64_files_state_start',25),'hd':m.get('hd_state_start',symbols['hd_state_end']-symbols['hd_state_start']),'ledger':bytes(ledger),'kind':kind,'drive':drive,'target':target}
 except BaseException:m.close();raise
records=[]
def wire(m,t):
 t.assertEqual(m.call('tw_begin').regs.a,1)
 for i in range(20000):
  if m.g(TW['state'])!=1:break
  m.call('tw_poll')
 diag={n:m.g(TW[n])for n in ['state','error','mode','phase','script','insert_job','verify_kind','plan_claim','context','closed']};diag['calls']=i;(P/'LAST_INSERT_WIRE.json').write_text(json.dumps(diag,indent=2)+'\n');t.assertEqual((diag['state'],diag['error'],diag['closed']),(2,0,1),diag)
def bind(m,t):
 load(m,'binding/binding.prg');load(m,'binding/insert-support.prg');m.call('_mb_fixture_init');return m.call('_mb_bind',80000000)
class Tests(unittest.TestCase):
 def test01_live_B_C1(self):
  m,old,new,f=prepared(self)
  try:
   wire(m,self);self.assertEqual(m.g(0x7fd3),0xa5);self.assertEqual(m.get('dos64_files_state_start',25),f['C']);r=bind(m,self);diag={'a':r.regs.a,'state':m.call('_mb_state').regs.a,'error':m.call('_mb_error').regs.a,'stage':m.g('dos64_native_diag'),'fstatus':m.g('dos64_floppy_status')};(P/'LAST_INSERT_BIND.json').write_text(json.dumps(diag,indent=2)+'\n');self.assertEqual((diag['a'],diag['state'],diag['error']),(1,2,0),diag);self.assertEqual(reu(m,0x3ff020,576),new);self.assertEqual(m.bytes(b'/usb1/Owned/DOS64.CFG',576),new);self.assertEqual(m.get('dos64_files_state_start',25),f['C']);self.assertEqual(m.g('dos64_floppy_stage_active'),0);self.assertEqual(m.get(symbols['dos64_disk_b_descriptor'],3),f['base'].to_bytes(3,'little'));self.assertEqual(m.get(symbols['dos64_disk_binding']+4,4),zlib.crc32(NEW_B).to_bytes(4,'little'));records.append(f|{'fq':f['fq'].hex(),'snapshot':f['snapshot'].hex(),'C':f['C'].hex(),'hd':f['hd'].hex(),'ledger':f['ledger'].hex()})
  finally:m.close()
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));(P/'INSERT_RESULT.json').write_text(json.dumps({'passed':r.wasSuccessful(),'groups':r.testsRun,'scope':'syntheticIncoming+PLANreceipt; actual WIRE/BIND/nativeCOMMIT; no fullcontroller or hardware','records':records},indent=2)+'\n');raise SystemExit(not r.wasSuccessful())
