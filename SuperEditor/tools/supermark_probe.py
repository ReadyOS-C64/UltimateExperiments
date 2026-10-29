"""Peddle driver for the separately linked SuperMark modules; no VIC claims."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from peddle import Machine
class SuperMark:
 def __init__(self):
  self.symbols={p[2].lstrip('.'):int(p[1],16) for line in (ROOT/'build/supermark/probe.lbl').read_text().splitlines() if (p:=line.split()) and p[0]=='al'}
  self.m=Machine();self.m.load(0x8000,(ROOT/'build/supermark/probe.bin').read_bytes())
  self.instructions={};self.peak={}
  self.shim=bytes((i*73+29)&255 for i in range(1024));self.m.load(0xC600,self.shim)
 def close(self):self.m.close()
 def get(self,name,n=1):return int.from_bytes(bytes(self.m.read(self.symbols[name]+i) for i in range(n)),'little')
 def put(self,name,value,n=1):self.m.load(self.symbols[name],value.to_bytes(n,'little'))
 def call(self,name,a=0,x=0,y=0):
  regs,count=self.m.call(self.symbols[name],a=a,x=x,y=y)
  self.instructions[name]=self.instructions.get(name,0)+count
  self.peak[name]=max(self.peak.get(name,0),count)
  return regs
 def safe(self):assert bytes(self.m.read(0xC600+i) for i in range(1024))==self.shim
 def blocks(self,data,start=0,chunks=None):
  self.call('se_sm_init');self.put('se_sm_pos',start,3)
  self.call('se_sm_at_line')
  out=[]
  def event():
   if self.get('se_sm_ready'):
    out.append({key:self.get('se_sm_'+key,n) for key,n in [('kind',1),('start',3),('end',3),('body',3),('level',1),('language',1),('fence',1),('regions',1)]})
  for part in chunks or [data]:
   for byte in part:self.call('se_sm_feed',byte);event()
  self.call('se_sm_finish');event();self.safe();return out
 def inline(self,data,start=0,chunks=None,body_column=None):
  self.call('se_si_init');self.put('se_si_pos',start,3);out=[]
  if body_column is not None:self.call('se_si_at_body',body_column&255,x=(body_column>>8)&255,y=(body_column>>16)&255)
  def event():
   if self.get('se_si_ready'):out.append(tuple(self.get('se_si_'+key,n) for key,n in [('kind',1),('style',1),('width',1),('open',3),('close',3)]))
  for part in chunks or [data]:
   for byte in part:self.call('se_si_feed',byte);event()
  self.call('se_si_finish');event();self.safe();return out
 def lex(self,data,language,start=0,chunks=None):
  self.call('se_sl_init',language);self.put('se_sl_pos',start,3);out=[]
  def drain():
   while self.get('se_sl_count'):
    regs=self.call('se_sl_next');assert not regs.p&1
    out.append(tuple(self.get('se_sl_'+key,n) for key,n in [('start',3),('end',3),('style',1)]))
  for part in chunks or [data]:
   for byte in part:
    regs=self.call('se_sl_feed',byte);assert not regs.p&1;drain()
  regs=self.call('se_sl_finish');assert not regs.p&1;drain();self.safe();return out

def petscii(text):
 """Host-readable transcription, deliberately not ASCII-byte encoding."""
 out=bytearray()
 for c in text:
  if 'a'<=c<='z':out.append(ord(c)-32)
  elif 'A'<=c<='Z':out.append(ord(c)+128)
  elif c=='£':out.append(0x5C)
  elif c=='\n':out.append(13)
  else:
   v=ord(c)
   if v>127:raise ValueError(c)
   out.append(v)
 return bytes(out)
