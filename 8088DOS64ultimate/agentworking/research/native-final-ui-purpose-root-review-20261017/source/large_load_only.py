"""Registered staged-file LOAD-only gate. No SYS/keyboard write capability.
Visible pre-SYS source cannot establish BASIC-hidden RAM: that remains an
explicit later native startup/CRC gate, not inferred from a full REST read.
"""
import time,math
from urllib.parse import quote
from bound_release import BoundRelease,Release16Protocol
from preserved_stage import closed_terminal
from basic_ready import basic_ready
class RegisteredLoadOnly:
 def __init__(self,protocol,release,assets,terminal,leaf,*,api,read_ram,record,clock=time.monotonic,sleep=time.sleep):
  if type(protocol)is not Release16Protocol or type(release)is not BoundRelease or protocol.first is not None or protocol.sequence!=380 or len(protocol.records)!=380 or protocol.records[-1]['op']!=10:raise ValueError('Actual typed release16 native STOP receipt required')
  if not all(callable(v)for v in [api,read_ram,record])or leaf not in ['SETUP.PRG','CONFIG.PRG']:raise ValueError('Exact staged product and bounded same-engine callbacks')
  files=release.verify(assets,protocol.source.home);closed_terminal(terminal,protocol.source)
  r=terminal[0x2a0:0x2e0]
  if not r[32]or r.hex()!=protocol.records[-1]['result']:raise ValueError('Fresh source-bound last STOP result must agree with native record')
  body=files[leaf]
  if body[:14]!=b'\x01\x08\x0b\x08\x0a\x00\x9e2061\x00\x00\x00'or not 0xa000<0x801+len(body)-2<0xb800:raise ValueError('Exact large SYS2061 source layout')
  self.record_sha=release.record_sha;self.body=bytes(body);self.leaf=leaf;self.path=protocol.source.home.decode()+'/'+leaf;self.api=api;self.read_ram=read_ram;self.record=record;self.clock=clock;self.sleep=sleep;self.attempted=False;self.first=None
 def run(self,parent_end,seconds=30):
  if self.attempted:raise ValueError('No repeated registered LOAD')
  self.attempted=True
  if type(seconds)not in[int,float]or not math.isfinite(seconds)or not 1<=seconds<=60:raise ValueError('Finite load-only endpoint')
  if type(parent_end)not in[int,float]or not math.isfinite(parent_end)or not self.clock()<parent_end<=self.clock()+600:raise ValueError('Original finite shared parent endpoint')
  end=min(parent_end,self.clock()+seconds)
  def check():
   if self.clock()>=end:raise TimeoutError('Original bounded load-only endpoint')
  def control(route):
   check();self.record({'event':'before_control','method':'PUT','route':route,'deadline':end,'attempts':1});v=self.api('PUT',route,end);self.record({'event':'control_response','route':route,'parsed':v});check()
   if type(v)is not dict or v.get('errors')!=[]:raise ValueError('Exact successful LOAD/control response required')
   return v
  try:
   route='runners:load_prg?file='+quote(self.path,safe='');control(route);previous=None
   for i in range(64):
    control('machine:pause');check();ram=self.read_ram(end);check()
    if type(ram)is not bytes or len(ram)!=65536 or ram[0x801:0xa000]!=self.body[2:0xa000-0x801+2]:raise ValueError('Whole paused RAM and exact visible loaded source before any SYS')
    self.record({'event':'visible_source','observation':i,'visible_start':0x801,'visible_end':0xa000,'hidden_preSYS_verified':False,'SYS_emitted':False})
    ready=basic_ready(ram)
    if ready is not None and previous is not None and ready['jiffy']!=previous['jiffy']:
     return {'status':'REGISTERED_LOAD_ONLY_VISIBLE_VERIFIED','leaf':self.leaf,'source_record_sha256':self.record_sha,'visible_bytes_exact':0xa000-0x801,'hidden_range':[0xa000,0x801+len(self.body)-2],'hidden_preSYS_verified':False,'native_startup_verified':False,'SYS_emitted':False,'CIA_UI_verified':False,'paired_BASIC_READY':True,'paused':True}
    previous=ready;control('machine:resume');self.sleep(min(.02,max(0,end-self.clock())))
   raise TimeoutError('Finite64 load-only READY observations')
  except BaseException as e:
   if self.first is None:self.first=e
   raise self.first
