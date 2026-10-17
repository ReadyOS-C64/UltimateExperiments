"""LOCAL transport-neutral strict stream consumer; no network or native command API.
Callbacks are capabilities for one exact whole snapshotGET and one ACKbyte.
Caller proves configured native cold bytes before SYS separately. No retries.
"""
from pathlib import Path
import os,struct,zlib
BASE=0x801;END=0xc000;SIZE=END-BASE;HOFF=0x3e00-BASE;POFF=0x4000-BASE
class Stream:
 def __init__(self,source,nonce,get,ack,output):
  if not 2<len(source)<=0x3e00-BASE+2 or source[:2]!=b'\x01\x08' or len(nonce)!=16 or not any(nonce):raise ValueError('Exact source/nonce')
  self.source=source[2:];self.nonce=nonce;self.get=get;self.ack=ack;self.next=1;self.failed=False;self.first_error=None;self.output=Path(output);self.fd=self.output.open('xb');self.closed=False
 def cold(self,raw):
  if bytes(raw)!=self.source:raise ValueError('Full coldsource equality required before SYS')
 def receive(self):
  if self.failed:raise self.first_error
  if self.closed:raise RuntimeError('One-shot terminal stream')
  try:
   raw=self.get(BASE,SIZE)
   if len(raw)!=SIZE or raw[:len(self.source)]!=self.source:raise ValueError('Exact GET count/native source')
   h=raw[HOFF:HOFF+52]
   if h[:8]!=b'RSF1\x01\xa5\x03\0' or h[8:24]!=self.nonce or zlib.crc32(h[:48])!=int.from_bytes(h[48:52],'little'):raise ValueError('Current readyheader identity/CRC')
   frame=int.from_bytes(h[24:26],'little');offset=int.from_bytes(h[26:30],'little');count=int.from_bytes(h[30:32],'little');payload=raw[POFF:]
   if frame!=self.next or not 1<=frame<=128 or offset!=(frame-1)*32768 or count!=32768 or int.from_bytes(h[36:40],'little')!=offset or int.from_bytes(h[44:48],'little')!=0xffffffff:raise ValueError('Private monotoneframe/offset/count')
   if len(payload)!=32768 or zlib.crc32(payload)!=int.from_bytes(h[32:36],'little'):raise ValueError('Complete payloadCRC')
   if self.fd.write(payload)!=32768:raise IOError('Durable file shortwrite')
   self.fd.flush();os.fsync(self.fd.fileno())
   self.ack(0x3f00,bytes([frame])) # never repeat ambiguous ACK
   self.next+=1
   return frame
  except BaseException as e:
   if self.first_error is None:self.first_error=e
   self.failed=True;raise
 def terminal(self):
  if self.failed:raise self.first_error
  if self.next!=129:raise RuntimeError('All128ACKs required')
  try:
   raw=self.get(BASE,SIZE)
   if len(raw)!=SIZE or raw[:len(self.source)]!=self.source:raise ValueError('Terminal source/count')
   h=raw[HOFF:HOFF+52]
   if h[:8]!=b'RSF1\x01\0\x04\0' or h[8:24]!=self.nonce or int.from_bytes(h[24:26],'little')!=128 or int.from_bytes(h[36:40],'little')!=0x400000 or zlib.crc32(h[:48])!=int.from_bytes(h[48:52],'little'):raise ValueError('Complete terminalreceipt')
   self.fd.flush();os.fsync(self.fd.fileno());self.fd.close();self.closed=True
  except BaseException as e:
   if self.first_error is None:self.first_error=e
   self.failed=True;raise
 def close(self):
  if not self.fd.closed:self.fd.close()
