from pathlib import Path
import ctypes as C,struct,zlib
from test_online_save import Machine,L,symbols
from fixture_config import cfg,resign
from dos_disk_inspect import Volume
P=Path(__file__).resolve().parent
def labels(n):return{x.split()[2].lstrip('.'):int(x.split()[1],16)for x in(P/n).read_text().splitlines()if x.startswith('al ')}

def load(m,n):
 b=(P/n).read_bytes();L.dos64_load(m.m,int.from_bytes(b[:2],'little'),b[2:],len(b)-2)

def fat(text):
 b=bytearray(368640);b[:11]=b'\xeb\x3c\x90SYNTH   ';struct.pack_into('<HBHBHHBHHHI',b,11,512,2,1,2,112,720,0xfd,2,9,2,0);b[510:512]=b'\x55\xaa'
 for sector in [1,3]:b[sector*512:sector*512+6]=b'\xfd\xff\xff\xff\x0f\0'
 root=5*512;b[root:root+11]=b'HELLO   TXT';b[root+11]=32;struct.pack_into('<HI',b,root+26,2,len(text));b[12*512:12*512+len(text)]=text
 out=bytes(b);assert Volume(out).payloads['HELLO.TXT']==text;return out

def reu(m,a,n):buf=C.create_string_buffer(n);assert L.dos64_reu_read(m.m,a,buf,n);return buf.raw
def headers(old):
 r=bytearray(b'D64R\1\0\x20\0'+old[572:576]+bytes.fromhex('78563412')+old[528:536]+b'\x1c\xdf\1\2'+bytes(4));o=bytearray(b'D64O\1\0\x20\0'+old[572:576]+bytes.fromhex('78563412')+b'\x50'+bytes(15))
 for b in [r,o]:b[5]=0xa5;b[28:32]=zlib.crc32(b[:28]).to_bytes(4,'little');b[5]=0
 return bytes(r),bytes(o)
A=fat(b'ORIGINAL A\r\n');OLD_B=fat(b'ORIGINAL B\r\n');NEW_B=fat(b'B WORKING MODIFIED\r\n')
symbols.update({n:v for n,v in labels('broker/broker.labels').items()if n.startswith('modal_')})
