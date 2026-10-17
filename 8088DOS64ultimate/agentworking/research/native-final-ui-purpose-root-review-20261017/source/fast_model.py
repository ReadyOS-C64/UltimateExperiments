"""Local protocol fixture. No CPU/firmware/timing/hardware claim."""
import json,zlib
from cold_model import Firmware,Clock
from fast_transport import TEMP,RESTORE
class Model(Firmware):
 def __init__(self,streams,service,baseline,clock):
  super().__init__(streams['initial'][0],streams['initial'][1],baseline,clock)
  self.streams=streams;self.service=service;self.baseline=baseline;self.kind=None;self.reu=bytearray(baseline);self.backup=baseline;self.restores=0;self.native_reads=0;self.poll_after=2;self.polls=0;self.omit_restore=False;self.bad_done=None;self.native_failure=False
 def drf(self,done=False):
  b=bytearray(32);b[:4]=b'DRF1';b[4]=0xa5 if done else 2;b[7]=6 if done else 3;b[8]=0 if done else 1
  crc=zlib.crc32(self.backup).to_bytes(4,'little');b[16:20]=crc;b[20:24]=crc
  if done:b[28:30]=b'\0\x20';b[24:28]=(10000).to_bytes(4,'little')
  if self.native_failure:b[4]=0xe1;b[5]=7
  if done and self.bad_done:self.bad_done(b)
  return bytes(b)
 def response(self,m,path,body):
  r=path[4:]
  if r=='configs/C64%20and%20Cartridge%20Settings':return json.dumps({'errors':[],'C64 and Cartridge Settings':{'Command Interface':'Enabled','RAM Expansion Unit':'Enabled','REU Size':'16 MB','REU Preload':'Disabled'}}).encode()
  queued=r=='machine:resume'and self.ram[0xc6]==8 and self.ram[0x277:0x27f]==b'SYS2061\r'
  if m=='PUT'and r in [TEMP,RESTORE]:
   self.turbo_control='Manual'if r==TEMP else'C64U Turbo Registers';return b'{"errors":[]}'
  if self.kind in self.streams:
   self.data=bytes(self.reu)
   if self.running:self.ram[0x3e00:0x3e34]=self.header();frame=min(self.frame,128);self.ram[0x4000:0xc000]=self.data[(frame-1)*32768:frame*32768]
  if self.kind=='restore'and r=='machine:readmem?address=6000&length=32'and self.running:
   self.polls+=1
   if self.polls>=self.poll_after:
    if not self.omit_restore:self.reu[:]=self.backup
    self.ram[0x6000:0x6020]=self.drf(True);self.ram[0x12b9:0x12bb]=(0xc101).to_bytes(2,'little');self.ram[0x135f:0x1361]=(0xc67f).to_bytes(2,'little')
  out=super().response(m,path,body)
  if m=='POST'and r=='machine:writemem?address=801':
   sources={v[0][2:]:k for k,v in self.streams.items()};sources[self.service[2:]]='restore';self.kind=sources[body];self.source=b'\x01\x08'+body;self.running=False
   if self.kind in self.streams:self.nonce=self.streams[self.kind][1];self.acked=0;self.frame=1;self.cancelled=False
  if queued and self.kind=='restore':
   self.restores+=1;self.ram[0x6000:0x6020]=self.drf();self.ram[0x12b9:0x12bb]=(0xc101).to_bytes(2,'little');self.ram[0x135f:0x1361]=(0xc480).to_bytes(2,'little')
  if self.kind in self.streams and r=='machine:readmem?address=801&length=47103':
   out=bytearray(out);out[:len(self.source)-2]=self.ram[0x801:0x801+len(self.source)-2];out=bytes(out)
  return out
 def __call__(self,*a,**kw):
  conn=super().__call__(*a,**kw);old=conn.getresponse
  def response():
   r=old();r.getheaders=lambda:[('Content-Type','application/octet-stream')];return r
  conn.getresponse=response;return conn
