from pathlib import Path
import os,sys
sys.dont_write_bytecode=True;sys.pycache_prefix=str(Path(__file__).resolve().parent/('.absent-real-pub-'+str(os.getpid())));assert not Path(sys.pycache_prefix).exists()
import ctypes as C,struct,zlib,json,hashlib
from test_coordinator import Coordinator,L
from test_source_load import PATHS
from dos_disk_inspect import Volume,inspect
P=Path(__file__).resolve().parent.parent
INPUT=[(P/'inputs'/n).read_bytes()for n in ['disk1.img','disk2.img','disk3.img','START.TPL','START.REL']]
class Context(Coordinator):
 def seed(self):
  for path,data in zip(PATHS,INPUT):L.bulk_model_seed(self.f.m,path,data,len(data))
 def select2m(self):
  self.ui();self.ready();self.key(0,1);self.key(0,4);self.key(0,1);self.key(0,7);self.key(0,1);self.key(0,7);self.key(0,7);self.key(0,1);self.key(0,4);self.key(0,1);self.key(0,1)
 def raw_call(self,name,budget=50_000_000_000):return self.f.call(name,budget=budget)
 def leave(self):
  f=self.f;ticket=self.call('_so_fat_ticket')+(f.last_regs.x<<8);f.write('_so_ticket',struct.pack('<H',ticket));assert self.call('_so_leave')==1
 def enterPub(self):
  data=Path('build/SETUP.PUB').read_bytes();L.bulk_model_seed(self.f.m,b'/Home/SETUP.PUB',data,len(data));self.f.write('_so_phase_request',b'\3');self.f.write('_so_now',self.f.read('_ps_ticks',2));assert self.call('_so_begin')==1
  for _ in range(3000):
   L.dos64_cia_clock_advance(self.f.m,1024);assert self.call('_ps_clock_poll')==1;self.f.write('_so_now',self.f.read('_ps_ticks',2));self.call('_so_poll')
   if self.call('_so_state')!=1:break
  assert self.call('_so_state')==2 and self.call('_so_enter')==1;g=bytearray(self.f.guard);at=self.f.labels['__PUBBSS_RUN__'];n=self.f.labels['__PUBBSS_SIZE__'];g[at:at+n]=b'\1'*n;self.f.guard=bytes(g)
 def file(self,path,n):
  L.bulk_model_read.argtypes=[C.c_void_p,C.c_char_p,C.c_void_p,C.c_uint32];L.bulk_model_read.restype=C.c_uint8;b=C.create_string_buffer(n);assert L.bulk_model_read(self.f.m,path,b,n)==1;return b.raw
 def facts(self):return self.f.read('_rc_retained',183)
if __name__=='__main__':
 u=Context()
 try:
  u.select2m();assert u.finish()==4;f=u.f;assert u.call('_rc_source_ready')==1;r=u.facts();assert r[178]==0 and r[179]==31 and r[180]==0 and r[181]==1;assert struct.unpack_from('<5I',r,134)==tuple(zlib.crc32(x)for x in INPUT)
  out={'source5actual':True,'native':hashlib.sha256(Path('build/setup.prg').read_bytes()).hexdigest(),'source_crc':list(struct.unpack_from('<5I',r,134)),'source_sizes':list(map(len,INPUT)),'full_FW_PW':False}
  if os.environ.get('SOURCE_ONLY')!='1':
   assert '_fw_run' in f.labels,'real FW object required, no friend injection permitted';assert u.raw_call('_fw_run')==1;assert f.read('_fw_internal',6)[0]==2 and f.read('_fw_internal',6)[5]==1 and u.facts()[180]==3;u.leave();u.enterPub();assert u.raw_call('_pw_run')==1;assert u.call('_pw_state')==2 and u.call('_pw_error')==0 and u.call('_pw_stage')==5 and u.facts()[180]==31;assert u.call('_pw_closed_quiet')==1
   r=u.facts();c=u.file(b'/Home/C.IMG',2097152);b=u.file(b'/Home/B.IMG',368640);a=u.file(b'/Home/A.IMG',368640);cfg=u.file(b'/Home/DOS64.CFG',576);start=u.file(b'/Home/START.PRG',18432)
   assert struct.unpack_from('<6I',r,154)==(len(c),zlib.crc32(c),len(b),zlib.crc32(b),len(a),zlib.crc32(a));assert zlib.crc32(cfg)==0x2144df1c and zlib.crc32(cfg[:572])==struct.unpack_from('<I',cfg,572)[0]
   full_c=inspect(c,(128,2,16));volumes=[Volume(c[8192:]),Volume(b),Volume(a)];reports=[full_c]+[v.report()for v in volumes[1:]];assert not volumes[1].payloads
   for i,img in enumerate(INPUT[:3]):
    v=Volume(img)
    for name,data in v.payloads.items():assert volumes[0].payloads['DOS/DISK%d/'%(i+1)+name]==data,(i,name)
   original=Volume(INPUT[0]);
   for name in ['IO.SYS','MSDOS.SYS','COMMAND.COM']:
    if name in original.payloads:assert volumes[2].payloads[name]==original.payloads[name]
   assert volumes[2].payloads['AUTOEXEC.BAT'].startswith(b'@ECHO OFF\r\n') and b'C:\\DOS' in volumes[2].payloads['AUTOEXEC.BAT'];assert volumes[2].payloads['CONFIG.SYS']==b'FILES=20\r\nBUFFERS=10\r\n'
   d=P/'full-output';d.mkdir(exist_ok=True)
   for name,blob in [('C.IMG',c),('B.IMG',b),('A.IMG',a),('DOS64.CFG',cfg),('START.PRG',start)]: (d/name).write_bytes(blob)
   out.update({'full_FW_PW':True,'private_mask':r[180],'reports':reports,'files':{n:{'bytes':len(x),'sha256':hashlib.sha256(x).hexdigest(),'crc':zlib.crc32(x)}for n,x in [('A',a),('B',b),('C',c),('CFG',cfg),('START',start)]}})
  (P/'REAL_PHASE_FLOW.json').write_text(json.dumps(out,indent=2,default=str)+'\n');print(out['full_FW_PW'])
 finally:u.close()
