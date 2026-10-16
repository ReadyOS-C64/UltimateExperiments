"""Byte-defined D64S ABI1 template metadata; paths and offsets are host ASCII/file bytes."""
from pathlib import Path
import re,struct,zlib,json,argparse
SIZE=64;CONTROL=131;HOME=128
BASIC=b'\x01\x08\x0b\x08\x0a\x00\x9e2061\x00\x00\x00'
DEFAULT=b'\xff\x1c\xdf\xff'+bytes(127)
def labels(text):
 out={}
 for line in text.splitlines():
  if line.startswith('al '):
   _,address,name=line.split();name=name.lstrip('.');v=int(address,16)
   if name in ['sf_entered','__TRAMPOLINE_LOAD__','__TRAMPOLINE_SIZE__','_lc_control'] and name in out and out[name]!=v:raise ValueError('ambiguous export '+name)
   out[name]=v
 return out
def make(prg,labeltext,maptext):
 s=labels(labeltext);rows=re.findall(r'^DATA\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+([0-9A-F]{6})\s+',maptext,re.M)
 if len(rows)!=1:raise ValueError('exact initialized DATA map required')
 lo,hi,n=map(lambda v:int(v,16),rows[0])
 if hi+1-lo!=n or n>65535:raise ValueError('DATA span')
 if s.get('sf_entered')!=lo or s.get('__TRAMPOLINE_LOAD__')!=hi+1 or s.get('__TRAMPOLINE_SIZE__')!=112:raise ValueError('initialized DATA/trampoline closure')
 # BASIC SYS2061 and the bound complete PRG determine native entry080D.
 d=bytearray(SIZE);d[:8]=b'D64S\x01\x01\x40\0';struct.pack_into('<IIHHHHIIH',d,8,len(prg),zlib.crc32(prg),0x0801,len(prg)-2,0x080d,CONTROL,s['_lc_control']-0x0801+2,lo-0x0801+2,n)
 d[34:43]=bytes([0,1,3,128,255,255,0x1c,0xdf,0]);struct.pack_into('<I',d,60,zlib.crc32(d[:60]));validate(bytes(d),prg);return bytes(d)
def validate(d,prg):
 if len(d)!=64 or d[:8]!=b'D64S\x01\x01\x40\0' or zlib.crc32(d[:60])!=int.from_bytes(d[60:64],'little'):raise ValueError('D64S header/CRC')
 n,crc,load,payload,entry,span,control,data,datalen=struct.unpack_from('<IIHHHHIIH',d,8)
 if n!=len(prg) or n<16 or n>0x4801 or payload!=n-2 or load!=0x0801 or entry!=0x080d or prg[:14]!=BASIC or zlib.crc32(prg)!=crc:raise ValueError('complete template binding')
 if span!=131 or d[34:43]!=bytes([0,1,3,128,255,255,0x1c,0xdf,0]) or any(d[43:60]):raise ValueError('D64S field ABI/defaults')
 # Subtraction-form bounds are suitable for native32-bit arithmetic too.
 if data<14 or data>n or datalen>n-data or not datalen or control<data or control>n or span>n-control or control-data>datalen or span>datalen-(control-data):raise ValueError('bounded initialized control/DATA')
 if prg[control:control+span]!=DEFAULT:raise ValueError('unconfigured initialized control')
 return {'file_bytes':n,'crc32':crc,'load':load,'entry':entry,'control_offset':control,'control_bytes':span,'DATA_offset':data,'DATA_bytes':datalen,'owner_field':0,'base_field':1,'home_field':3,'home_bytes':128}
def home_valid(home):
 if not isinstance(home,bytes) or not 1<len(home)<=117 or home[:1]!=b'/':return False
 for c in home:
  if not 32<=c<=126 or c in b'\\:"*<>?|':return False
 for p in home[1:].split(b'/'):
  if not p or p in [b'.',b'..'] or p[-1:] in [b' ',b'.']:return False
 return True
def patch(d,prg,home,base=0xdf1c):
 v=validate(d,prg)
 if not home_valid(home) or base not in [0xdf1c,0xde1c,0xdffc]:raise ValueError('canonical owned installation folder/base')
 out=bytearray(prg);at=v['control_offset'];out[at:at+131]=b'\xa5'+struct.pack('<H',base)+home.ljust(128,b'\0')
 assert out[:at]==prg[:at] and out[at+131:]==prg[at+131:];return bytes(out)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--prg',type=Path,required=True);a.add_argument('--labels',type=Path,required=True);a.add_argument('--map',type=Path,required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args();prg=args.prg.read_bytes();d=make(prg,args.labels.read_text(),args.map.read_text());args.out.write_bytes(d);print(json.dumps(validate(d,prg),indent=2))
