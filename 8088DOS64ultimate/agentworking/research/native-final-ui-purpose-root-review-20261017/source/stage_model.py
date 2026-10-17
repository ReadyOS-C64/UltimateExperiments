"""Independent HTTP/phase fixture only; no native CPU or firmware claim."""
import json,zlib
from fast_model import Model,Clock

class StageModel(Model):
 def __init__(self,streams,service,baseline,clock,stager):
  super().__init__(streams,service,baseline,clock);self.stager=stager;self.files={};self.file=None;self.pos=0;self.stage_jobs=[];self.stage_unknown=False;self.stage_error=0;self.stage_source_bad=False;self.stage_put_fault=None;self.stage_puts=0;self.ready()
 def stage_init(self):
  s=self.stager
  for a,v in s.port_words.items():self.ram[a:a+2]=v.to_bytes(2,'little')
  for a in s.dynamic:self.ram[a:a+2]=b'\xff\xff'
  self.ram[0x2a0:0x2e0]=bytes(64);r=memoryview(self.ram)[0x2a0:0x2e0];r[:4]=b'AST1';r[4]=0x11;r[9]=3;r[34]=9
 def stage_job(self):
  q=self.ram[0x200:0x28e];op=q[1];seq=int.from_bytes(q[2:4],'little');off=int.from_bytes(q[4:8],'little');n=int.from_bytes(q[8:10],'little');leaf=q[14:142].split(b'\0')[0].decode();r=memoryview(self.ram)[0x2a0:0x2e0]
  self.ram[0x200]=0;self.stage_jobs.append((seq,op,leaf,off,n));r[4]=0xa5;r[6:8]=seq.to_bytes(2,'little');r[16:20]=bytes(4)
  if op==2:
   if leaf in self.files:self.stage_error=3
   else:self.files[leaf]=bytearray();self.file=leaf;self.pos=0;r[9]=1;r[31]=2
  elif op==3:self.reu[0x200000:0x200000+n]=self.ram[0x4000:0x4000+n];self.pos=off
  elif op==4:
   assert self.file is not None;self.files[self.file][off:off+n]=self.reu[0x200000:0x200000+n];self.pos=off+n;r[16:20]=n.to_bytes(4,'little')
  elif op==5:self.file=None;r[9]=3;r[31]=0
  elif op==6:self.file=leaf;self.pos=0;r[9]=1;r[31]=2
  elif op==7:r[20:24]=len(self.files[self.file]).to_bytes(4,'little')
  elif op==8:
   b=bytes(self.files[self.file][off:off+n]);self.reu[0x200000:0x200000+n]=b;self.ram[0x4000:0x4000+n]=b;self.pos=off+n;r[16:20]=len(b).to_bytes(4,'little')
  elif op==9:
   assert self.pos==len(self.files[self.file]);r[36]=1;a=self.stager.at('_st_eof_wire');r[38:40]=a.to_bytes(2,'little');self.ram[a:a+40]=b'$000000 BYTES LOADED TO REU $20000000,OK'
  elif op==10:r[32]=1
  r[12:16]=self.pos.to_bytes(4,'little')
  if self.stage_error:r[4]=0xff;r[8]=self.stage_error;r[32]=1;self.file=None;r[31]=0;r[9]=3
  if self.stage_unknown:r[31]=2;r[9]=1
  if self.stage_source_bad:self.ram[self.stager.low+32]^=1
 def response(self,m,path,body):
  r=path[4:];queued=r=='machine:resume'and self.ram[0xc6]==8
  if self.kind=='stage'and self.running and not self.paused and r.startswith('machine:readmem?')and self.ram[0x200]==0x22:self.stage_job()
  out=super().response(m,path,body)
  if r=='machine:reset':self.kind=None
  if m=='PUT'and r.startswith('machine:writemem?'):
   q=dict(x.split('=')for x in r.split('?')[1].split('&'));a=int(q['address'],16);part=bytes.fromhex(q['data']);assert 1<=len(part)<=128
   for role,src in list((k,v[0])for k,v in self.streams.items())+[('restore',self.service),('stage',self.stager.configured)]:
    if a+len(part)==0x801+len(src)-2 and self.ram[0x801:0x801+len(src)-2]==src[2:]:
     self.kind=role;self.source=src;self.running=False
     if role in self.streams:self.nonce=self.streams[role][1];self.frame=1;self.acked=0;self.cancelled=False
   if self.kind=='stage':
    self.stage_puts+=1
    if self.stage_put_fault==self.stage_puts:raise self.error
  if queued and self.kind=='stage':self.stage_init()
  return out
